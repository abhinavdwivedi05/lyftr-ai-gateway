import os
from typing import Any, Optional, List, Dict

# Prevent LiteLLM from attempting external network calls for model pricing
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import litellm
from litellm.caching.caching import Cache

class CacheService:
    """
    Manages LiteLLM's built-in caching mechanism.
    Configured with an in-memory/local cache.
    """
    def __init__(self):
        litellm.suppress_debug_info = True
        self.cache = Cache(type="local")
        litellm.cache = self.cache
        litellm.enable_cache()

    @property
    def is_enabled(self) -> bool:
        return litellm.cache is not None

    def is_cache_hit(self, response: Any) -> bool:
        """
        Inspects the response object for LiteLLM's cache_hit indicator.
        Supported for installed LiteLLM versions via _hidden_params['cache_hit'].
        """
        hidden = getattr(response, "_hidden_params", {})
        if isinstance(hidden, dict):
            return bool(hidden.get("cache_hit"))
        return False

    def get_cache_key(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Computes the deterministic cache key for a model and message sequence."""
        if self.cache:
            try:
                return self.cache.get_cache_key(model=model, messages=messages)
            except Exception:
                return ""
        return ""

cache_service = CacheService()
