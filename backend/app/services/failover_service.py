import logging
import re
from typing import Optional, Dict, Tuple, Any, List
from fastapi import HTTPException, status
import litellm
from litellm.exceptions import (
    RateLimitError,
    InternalServerError,
    BadGatewayError,
    ServiceUnavailableError,
    APIConnectionError,
    Timeout,
    APIError,
)

from app.config import settings
from app.services.cache_service import cache_service

logger = logging.getLogger("failover_service")

class FailoverService:
    """
    Manages key pool iteration, failure simulation (X-Simulate-Failure),
    and automatic failover across multiple API keys.
    """
    SUPPORTED_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self):
        pass

    def sanitize_error(self, error: Any, keys: Optional[List[str]] = None) -> str:
        """
        Redacts API keys and secrets from exception strings or payloads.
        """
        if error is None:
            return ""
        msg = str(error)
        if keys:
            for k in keys:
                if k and len(k) > 4:
                    msg = msg.replace(k, "[REDACTED_API_KEY]")
        msg = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_API_KEY]', msg)
        msg = re.sub(r'AQ\.[0-9A-Za-z-_]+', '[REDACTED_API_KEY]', msg)
        msg = re.sub(r'key=[0-9A-Za-z-_]+', 'key=[REDACTED_API_KEY]', msg)
        msg = re.sub(r'x-goog-api-key["\']?\s*:\s*["\']?[0-9A-Za-z-_]+', 'x-goog-api-key: [REDACTED_API_KEY]', msg)
        return msg

    def parse_simulation_header(self, header_value: Optional[str]) -> Dict[str, int]:
        """
        Parses X-Simulate-Failure header into a dictionary of {key_id: status_code}.
        Supported formats:
          - key_1=429
          - key_1=429,key_2=500
          - *=429
        """
        if not header_value or not settings.ENABLE_FAILURE_SIMULATION:
            return {}

        simulations: Dict[str, int] = {}
        for part in header_value.split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if v.isdigit():
                    status_code = int(v)
                    if status_code in self.SUPPORTED_STATUSES:
                        simulations[k] = status_code
        return simulations

    def is_failover_error(self, error: Exception) -> bool:
        """
        Determines if an exception qualifies for automatic failover
        (HTTP 429, 500, 502, 503, 504, quota exhaustion, or temporary server errors).
        """
        status_code = getattr(error, "status_code", None)
        if status_code in self.SUPPORTED_STATUSES:
            return True

        if isinstance(error, (
            RateLimitError,
            InternalServerError,
            BadGatewayError,
            ServiceUnavailableError,
            APIConnectionError,
            Timeout,
        )):
            return True

        err_str = str(error).lower()
        failover_keywords = [
            "429", "500", "502", "503", "504",
            "quota", "rate limit", "rate_limit",
            "resource has been exhausted", "resource_exhausted", "overloaded",
            "service unavailable", "bad gateway", "gateway timeout",
            "timed out", "timeout", "temporarily unavailable",
            "connection error", "connection reset"
        ]
        return any(keyword in err_str for keyword in failover_keywords)

    def execute_completion(
        self,
        messages: List[Dict[str, str]],
        simulate_failure_header: Optional[str] = None
    ) -> Tuple[Any, Optional[str], int]:
        """
        Executes completion across the configured key pool.
        Returns: (model_response, successful_key_id, fallback_attempts)
        """
        simulations = self.parse_simulation_header(simulate_failure_header)
        is_simulation_active = bool(simulations)

        # When failure simulation is active, bypass reading from/writing to cache
        caching_enabled = not is_simulation_active
        cache_kwargs = None
        if not caching_enabled:
            cache_kwargs = {"no-store": True, "no-cache": True}

        # Build key pool with identifiers: key_1, key_2, ...
        configured_keys = settings.key_pool
        if not configured_keys:
            configured_keys = ["placeholder_key_1", "placeholder_key_2"]

        key_entries = [(f"key_{i+1}", key_val) for i, key_val in enumerate(configured_keys)]

        fallback_attempts = 0
        last_exception = None

        for key_id, key_val in key_entries:
            # 1. Check for simulated failure
            simulated_status = simulations.get(key_id) or simulations.get("*")
            if simulated_status:
                logger.warning(
                    f"Simulated failure {simulated_status} triggered for key identifier {key_id}"
                )
                fallback_attempts += 1
                continue

            # 2. Attempt call with current key
            try:
                # Check if in development/mock mode (or placeholder keys)
                is_mock_mode = (
                    settings.MOCK_LLM
                    or key_val.startswith("placeholder")
                    or key_val.lower() == "mock"
                )

                call_kwargs = {
                    "model": settings.LLM_MODEL,
                    "messages": messages,
                    "api_key": key_val,
                    "caching": caching_enabled,
                }
                if cache_kwargs:
                    call_kwargs["cache"] = cache_kwargs

                if is_mock_mode:
                    # Provide deterministic mock response that flows through LiteLLM's caching & token tracking
                    last_msg = messages[-1]["content"] if messages else ""
                    call_kwargs["mock_response"] = f"Response from {key_id}: {last_msg}"

                response = litellm.completion(**call_kwargs)

                # Check if response was returned from cache
                if cache_service.is_cache_hit(response):
                    # Cache hits report key_id=None and fallback_attempts=0 per requirement
                    return response, None, 0

                # Live inference succeeded
                logger.info(f"Request resolved via {key_id} (fallback_attempts={fallback_attempts})")
                return response, key_id, fallback_attempts

            except Exception as e:
                status_code = getattr(e, "status_code", None)
                sanitized_msg = self.sanitize_error(e, configured_keys)
                if self.is_failover_error(e):
                    logger.warning(
                        f"Key {key_id} encountered retryable failover error: "
                        f"{type(e).__name__} (status={status_code}): {sanitized_msg}"
                    )
                    fallback_attempts += 1
                    last_exception = e
                    continue
                else:
                    logger.error(
                        f"Key {key_id} encountered non-failover error: "
                        f"{type(e).__name__} (status={status_code}): {sanitized_msg}"
                    )
                    raise

        # If every key in the pool failed or was simulated to fail
        last_err_msg = self.sanitize_error(last_exception, configured_keys) if last_exception else "no prior exception"
        logger.error(
            f"All {len(key_entries)} providers failed after {fallback_attempts} fallback attempts. "
            f"Last error: {last_err_msg}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="all providers unavailable"
        )

failover_service = FailoverService()
