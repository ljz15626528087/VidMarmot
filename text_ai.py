"""
text_ai.py - LLM text generation client.

Supports multiple providers defined in config.py.
"""

from openai import OpenAI
from config import LLM_PROVIDERS


def text_ai(in_put: str, system_prompt: str = "You are a helpful assistant.",
            provider: str = None) -> str:
    """Call LLM to generate text.

    Args:
        in_put: user message
        system_prompt: system prompt
        provider: provider name (key in LLM_PROVIDERS), None = first in dict
    Returns:
        generated text
    """
    if provider and provider in LLM_PROVIDERS:
        cfg = LLM_PROVIDERS[provider]
    else:
        # Default to first provider in dict
        cfg = next(iter(LLM_PROVIDERS.values()))
        provider = next(iter(LLM_PROVIDERS))

    api_key = cfg["api_key"]
    api_base = cfg["api_base"]
    model = cfg["model"]

    if not api_key:
        raise ValueError(
            f"API key not configured for '{provider}'. "
            f"Edit config.py and fill in the api_key field."
        )

    client = OpenAI(api_key=api_key, base_url=api_base)

    # ModelScope Qwen3/GLM default to thinking mode, disable it
    extra_body = {}
    is_modelscope = "modelscope" in api_base.lower()
    is_qwen = "qwen" in model.lower()
    is_glm = "glm" in model.lower() or "zhipuai" in model.lower()
    if is_modelscope and (is_qwen or is_glm):
        extra_body["enable_thinking"] = False

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": in_put},
        ],
        max_tokens=16384,
        stream=False,
        extra_body=extra_body or None,
    )

    if not response.choices:
        resp_dict = response.model_dump() if hasattr(response, "model_dump") else {}
        error_msg = resp_dict.get("error", {})
        err_text = error_msg.get("message", str(error_msg)) if isinstance(error_msg, dict) else str(resp_dict)
        raise ValueError(
            f"Model '{model}' returned empty choices.\n"
            f"Response: {err_text}\n"
            f"Model may be unavailable or request was rejected."
        )

    msg = response.choices[0].message
    content = msg.content

    if response.choices[0].finish_reason == "length":
        print(f"[WARN] LLM output truncated (finish_reason=length)")

    if content is None:
        # Fallback: try alternate field names
        for attr in ("thinking_content", "reasoning_content", "text", "output"):
            fallback = getattr(msg, attr, None)
            if fallback:
                content = fallback
                break

    if content is None:
        try:
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else vars(msg)
            for v in msg_dict.values():
                if isinstance(v, str) and v.strip():
                    content = v
                    break
        except Exception:
            pass

    if content is None:
        raise ValueError(
            f"Model '{model}' returned None content (finish_reason={response.choices[0].finish_reason})."
        )
    return content


if __name__ == "__main__":
    result = text_ai("Hello, say hi in one sentence.")
    print(result)
