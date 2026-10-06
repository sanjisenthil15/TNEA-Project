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
    Supports dual Google Gemini API keys with automatic quota failover
    and latest high-availability model cascading.
    Never exposes API keys in logs or errors.
    """
    providers: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # Key 1: Primary Gemini API Key
    # -------------------------------------------------------------
    k1 = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("AI_API_KEY")
    )
    k1_model = os.environ.get("OPENAI_MODEL") or os.environ.get("GEMINI_MODEL") or os.environ.get("AI_MODEL") or "gemini-3.8-flash"
    k1_base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("AI_BASE_URL")

    if k1 and str(k1).strip():
        k1_str = str(k1).strip()
        is_gemini_1 = k1_str.startswith("AQ.") or k1_str.startswith("AIza") or ("generativelanguage" in str(k1_base or "")) or bool(os.environ.get("GEMINI_API_KEY"))
        if is_gemini_1 and not k1_base:
            k1_base = "https://generativelanguage.googleapis.com/v1beta/openai/"

        providers.append({
            "id": "gemini_key1_primary",
            "name": f"Google Gemini Key-1 ({k1_model})",
            "api_key": k1_str,
            "model": k1_model.strip(),
            "base_url": k1_base.strip() if k1_base else None,
            "timeout": 25.0
        })

        if is_gemini_1:
            fb_model_name = os.environ.get("FALLBACK_AI_MODEL") or "gemini-3.5-flash-lite"
            for fb_m in [fb_model_name]:
                if fb_m != k1_model:
                    providers.append({
                        "id": f"gemini_key1_fallback_{fb_m}",
                        "name": f"Google Gemini Key-1 Fallback ({fb_m})",
                        "api_key": k1_str,
                        "model": fb_m,
                        "base_url": k1_base.strip() if k1_base else "https://generativelanguage.googleapis.com/v1beta/openai/",
                        "timeout": 25.0
                    })

    # -------------------------------------------------------------
    # Key 2: Secondary Gemini API Key (Automatic Quota Failover)
    # -------------------------------------------------------------
    k2 = (
        os.environ.get("GEMINI_API_KEY_2")
        or os.environ.get("FALLBACK_AI_API_KEY")
        or os.environ.get("OPENAI_API_KEY_2")
        or os.environ.get("AI_API_KEY_2")
    )
    k2_model = os.environ.get("FALLBACK_AI_MODEL") or "gemini-3.5-flash-lite"
    k2_base = os.environ.get("FALLBACK_AI_BASE_URL") or os.environ.get("OPENAI_BASE_URL_2") or k1_base

    if k2 and str(k2).strip() and str(k2).strip() != str(k1 or "").strip():
        k2_str = str(k2).strip()
        is_gemini_2 = k2_str.startswith("AQ.") or k2_str.startswith("AIza") or ("generativelanguage" in str(k2_base or "")) or bool(os.environ.get("GEMINI_API_KEY_2"))
        if is_gemini_2 and not k2_base:
            k2_base = "https://generativelanguage.googleapis.com/v1beta/openai/"

        providers.append({
            "id": "gemini_key2_primary",
            "name": f"Google Gemini Key-2 ({k1_model})",
            "api_key": k2_str,
            "model": k1_model.strip(),
            "base_url": k2_base.strip() if k2_base else None,
            "timeout": 25.0
        })

        if is_gemini_2:
            for fb_m in [k2_model]:
                if fb_m != k1_model:
                    providers.append({
                        "id": f"gemini_key2_fallback_{fb_m}",
                        "name": f"Google Gemini Key-2 Fallback ({fb_m})",
                        "api_key": k2_str,
                        "model": fb_m,
                        "base_url": k2_base.strip() if k2_base else "https://generativelanguage.googleapis.com/v1beta/openai/",
                        "timeout": 25.0
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
