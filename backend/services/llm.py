import os
import time
import json
from typing import Any, Dict, Optional, Type
from config import settings

class LLMError(Exception): pass
class ApiKeyError(LLMError): pass
class RateLimitError(LLMError): pass
class TimeoutError(LLMError): pass

GROQ_FALLBACK_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
]

def generate(system_prompt: str, user_prompt: str, json_mode: bool = False, max_tokens: int = 2000) -> str:
    if getattr(settings, "DEMO_MODE", False):
        if json_mode:
            return json.dumps({
                "answer": "This response was generated using local policy text analysis.",
                "verdict": "covered",
                "supported": True,
                "citations": [],
                "follow_up_suggestions": ["What are the exclusions?", "What is the deductible?"]
            })
        return "Local policy text analysis complete."
        
    if not getattr(settings, "api_key_configured", False):
        raise ApiKeyError("Groq API key is not configured. Please ensure GROQ_API_KEY is saved in backend/.env.")

    provider = getattr(settings, "LLM_PROVIDER", "groq").lower()
    
    retries = 2
    for attempt in range(retries + 1):
        try:
            if provider == "groq":
                try:
                    import groq
                    client = groq.Groq(api_key=settings.GROQ_API_KEY)
                except ImportError:
                    import openai
                    client = openai.OpenAI(
                        api_key=settings.GROQ_API_KEY,
                        base_url="https://api.groq.com/openai/v1"
                    )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # Try active model or fallback models if model not found
                target_model = settings.active_model
                candidate_models = [target_model] + [m for m in GROQ_FALLBACK_MODELS if m != target_model]
                
                last_model_err = None
                for mod in candidate_models:
                    try:
                        kwargs = {
                            "model": mod,
                            "messages": messages,
                            "max_tokens": max_tokens
                        }
                        if json_mode:
                            kwargs["response_format"] = {"type": "json_object"}

                        response = client.chat.completions.create(**kwargs)
                        return response.choices[0].message.content
                    except Exception as model_err:
                        err_str = str(model_err).lower()
                        if any(k in err_str for k in ["does not exist", "model_not_found", "404", "rate_limit", "429", "rate limit", "tokens per day", "tpd", "decommissioned"]):
                            last_model_err = model_err
                            continue
                        raise model_err
                        
                if last_model_err:
                    raise last_model_err

            elif provider == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                messages = [{"role": "user", "content": user_prompt}]
                response = client.messages.create(
                    model=settings.ANTHROPIC_MODEL,
                    system=system_prompt,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.content[0].text

            elif provider == "openai":
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                kwargs = {
                    "model": settings.OPENAI_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                    
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            else:
                raise LLMError(f"Unknown LLM provider: {provider}")

        except Exception as e:
            err_msg = str(e).lower()
            if "api key" in err_msg or "unauthorized" in err_msg or "401" in err_msg:
                raise ApiKeyError(str(e))
            if "rate limit" in err_msg or "429" in err_msg:
                if attempt == retries:
                    raise RateLimitError(str(e))
                time.sleep(2 ** attempt)
                continue
            if "timeout" in err_msg:
                if attempt == retries:
                    raise TimeoutError(str(e))
                time.sleep(2 ** attempt)
                continue
            if attempt == retries:
                raise LLMError(str(e))
            time.sleep(2 ** attempt)

def generate_json(system_prompt: str, user_prompt: str, response_model: Optional[Type] = None, max_retries: int = 2) -> Dict[str, Any]:
    for attempt in range(max_retries + 1):
        try:
            res_str = generate(system_prompt, user_prompt, json_mode=True)
            res_json = json.loads(res_str)
            if response_model:
                return response_model(**res_json).dict()
            return res_json
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == max_retries:
                raise LLMError(f"Failed to parse JSON: {str(e)}")
            time.sleep(1)
