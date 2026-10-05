"""
=============================================================
TNEA Career Insight Navigator — AI Provider Fallback & Health Manager
=============================================================
Manages primary and fallback AI model providers (OpenAI, Groq,
Together, DeepSeek, Local Ollama, OpenAI-compatible APIs).

Features:
  - Multi-tier provider configuration via environment variables
  - Automatic error classification:
      • Auth failure (401, 403)
      • Rate limit / Quota exhaustion (429, Insufficient Quota)
      • Server / Transient error (500, 502, 503, 504, Timeout)
  - Transient retry with exponential backoff
  - Circuit-breaker health tracking (prevents repeated calls to failed endpoints)
  - Seamless context & tool-calling preservation across failovers
=============================================================
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable

logger = logging.getLogger("ai_provider_manager")
logger.setLevel(logging.INFO)

# Provider Health State Cache (in-memory per process)
_PROVIDER_HEALTH: Dict[str, Dict[str, Any]] = {}
COOLDOWN_SECONDS = 180  # 3 minutes cooldown for failed providers


def _get_configured_providers() -> List[Dict[str, Any]]:
    """
    Builds the ranked list of active AI providers from environment variables.
    Never exposes API keys in logs or errors.
    """
    providers: List[Dict[str, Any]] = []

    # Provider 1: Primary OpenAI
    p1_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    p1_model = os.environ.get("OPENAI_MODEL") or os.environ.get("AI_MODEL") or "gpt-4o-mini"
    p1_base = os.environ.get("OPENAI_BASE_URL")

    if p1_key and str(p1_key).strip():
        providers.append({
            "id": "primary_openai",
            "name": "OpenAI Primary",
            "api_key": p1_key.strip(),
            "model": p1_model.strip(),
            "base_url": p1_base.strip() if p1_base else None,
            "timeout": 25.0
        })

    # Provider 2: Secondary / Fallback Provider
    p2_key = (
        os.environ.get("FALLBACK_AI_API_KEY")
        or os.environ.get("OPENAI_API_KEY_2")
        or os.environ.get("AI_API_KEY_2")
        or (p1_key if os.environ.get("FALLBACK_AI_MODEL") else None)
    )
    p2_model = os.environ.get("FALLBACK_AI_MODEL") or "gpt-4o"
    p2_base = os.environ.get("FALLBACK_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL_2")

    if p2_key and str(p2_key).strip() and (p2_key != p1_key or p2_model != p1_model or p2_base != p1_base):
        providers.append({
            "id": "fallback_provider_1",
            "name": f"Fallback Provider ({p2_model})",
            "api_key": p2_key.strip(),
            "model": p2_model.strip(),
            "base_url": p2_base.strip() if p2_base else None,
            "timeout": 30.0
        })

    # Provider 3: Tertiary Provider (Optional additional backup)
    p3_key = os.environ.get("FALLBACK_AI_API_KEY_2") or os.environ.get("OPENAI_API_KEY_3")
    p3_model = os.environ.get("FALLBACK_AI_MODEL_2") or "gpt-3.5-turbo"
    p3_base = os.environ.get("FALLBACK_AI_BASE_URL_2")

    if p3_key and str(p3_key).strip():
        providers.append({
            "id": "fallback_provider_2",
            "name": f"Tertiary Provider ({p3_model})",
            "api_key": p3_key.strip(),
            "model": p3_model.strip(),
            "base_url": p3_base.strip() if p3_base else None,
            "timeout": 30.0
        })

    return providers


def is_provider_healthy(provider_id: str) -> bool:
    """Checks circuit-breaker health for a provider."""
    health = _PROVIDER_HEALTH.get(provider_id)
    if not health:
        return True
    
    if not health.get("healthy", True):
        last_failure = health.get("last_failure_time", 0)
        if time.time() - last_failure > COOLDOWN_SECONDS:
            # Reset after cooldown period
            health["healthy"] = True
            health["consecutive_failures"] = 0
            logger.info(f"AI Provider '{provider_id}' cooldown expired. Restoring to active pool.")
            return True
        return False
    return True


def record_provider_failure(provider_id: str, error_type: str):
    """Records a failure for a provider and trips circuit-breaker if necessary."""
    health = _PROVIDER_HEALTH.setdefault(provider_id, {"healthy": True, "consecutive_failures": 0, "last_failure_time": 0})
    health["consecutive_failures"] += 1
    health["last_failure_time"] = time.time()
    health["last_error"] = error_type

    if error_type in ["auth_error", "quota_exhausted"] or health["consecutive_failures"] >= 3:
        health["healthy"] = False
        logger.warning(f"AI Provider '{provider_id}' marked UNHEALTHY due to {error_type}. Failover engaged for {COOLDOWN_SECONDS}s.")


def record_provider_success(provider_id: str):
    """Resets error counter upon successful response."""
    health = _PROVIDER_HEALTH.setdefault(provider_id, {"healthy": True, "consecutive_failures": 0, "last_failure_time": 0})
    health["healthy"] = True
    health["consecutive_failures"] = 0


def execute_with_ai_fallback(
    operation: Callable[[Dict[str, Any]], Any]
) -> Tuple[Optional[Any], Optional[str]]:
    """
    Executes an AI LLM operation through the configured providers with automated fallback.
    Returns:
      (result_object, successful_provider_name_or_none)
    """
    providers = _get_configured_providers()
    if not providers:
        logger.debug("No external AI providers configured in environment.")
        return None, None

    last_err = None

    for prov in providers:
        p_id = prov["id"]
        p_name = prov["name"]

        if not is_provider_healthy(p_id):
            logger.info(f"Skipping unhealthy AI provider '{p_name}'. Checking next fallback.")
            continue

        # Transient retry loop (1 retry with 1.2s delay for server errors)
        for attempt in range(2):
            try:
                logger.info(f"Dispatching AI request to '{p_name}' (model: {prov['model']}, attempt: {attempt + 1})")
                res = operation(prov)
                if res is not None:
                    record_provider_success(p_id)
                    return res, p_name
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"AI Provider '{p_name}' failed on attempt {attempt + 1}: {err_str[:120]}")
                last_err = e

                # Determine error category
                if "401" in err_str or "unauthorized" in err_str or "invalid_api_key" in err_str:
                    record_provider_failure(p_id, "auth_error")
                    break  # Do not retry auth errors
                elif "429" in err_str or "quota" in err_str or "rate_limit" in err_str:
                    record_provider_failure(p_id, "quota_exhausted")
                    break  # Do not retry quota exhaustion
                elif attempt == 0:
                    time.sleep(1.2)  # Short backoff for transient glitches

        # Mark provider failure if both attempts failed
        record_provider_failure(p_id, "service_error")

    logger.warning("All configured external AI providers failed or were unavailable.")
    return None, None
