import time
from typing import Optional, List, Dict, Tuple
from app.config import settings
from app.schemas import ChatMetadata
from app.services.cache_service import cache_service
from app.services.failover_service import failover_service

class LLMService:
    """
    Core LLM Service integrating LiteLLM completion,
    multi-key failover, response caching, and failure simulation.
    """
    def __init__(self):
        pass

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        simulate_failure_header: Optional[str] = None
    ) -> Tuple[str, ChatMetadata]:
        start_time = time.time()

        # Execute through failover service
        response, key_id, fallback_attempts = failover_service.execute_completion(
            messages=messages,
            simulate_failure_header=simulate_failure_header
        )

        latency_ms = max(1, int((time.time() - start_time) * 1000))

        # Check cache hit
        is_cached = cache_service.is_cache_hit(response)
        resolution_source = "LLM_CACHE" if is_cached else "LIVE_INFERENCE"

        # Requirements: on LLM_CACHE, key_id must be null and fallback_attempts must be 0
        if is_cached:
            key_id = None
            fallback_attempts = 0

        # Extract reply text
        reply = ""
        if hasattr(response, "choices") and response.choices:
            first_choice = response.choices[0]
            if hasattr(first_choice, "message"):
                reply = getattr(first_choice.message, "content", "") or ""

        # Extract tokens from provider response
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

        # Ensure integers >= 1
        if input_tokens == 0:
            prompt_chars = sum(len(m.get("content", "")) for m in messages)
            input_tokens = max(1, prompt_chars // 4)
        if output_tokens == 0:
            output_tokens = max(1, len(reply) // 4)

        metadata = ChatMetadata(
            resolution_source=resolution_source,
            model=settings.LLM_MODEL,
            latency_ms=latency_ms,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            key_id=key_id,
            fallback_attempts=int(fallback_attempts)
        )

        return reply, metadata

llm_service = LLMService()
