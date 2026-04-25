"""
text_ai.py - LLM 文本生成
用于场景划分等 AI 推理任务
支持多 LLM 提供商切换
"""

from openai import OpenAI
from config import LLM_PROVIDERS, DEFAULT_LLM, LLM_API_KEY, LLM_API_BASE, LLM_MODEL


def text_ai(in_put: str, system_prompt: str = "You are a helpful assistant.",
            provider: str = None) -> str:
    """
    调用 LLM 生成文本

    Args:
        in_put: 用户输入内容
        system_prompt: 系统提示词
        provider: LLM 提供商名称（对应 LLM_PROVIDERS 的 key），None 则用默认

    Returns:
        AI 生成的文本
    """
    if provider and provider in LLM_PROVIDERS:
        cfg = LLM_PROVIDERS[provider]
        api_key = cfg["api_key"]
        api_base = cfg["api_base"]
        model = cfg["model"]
    else:
        api_key = LLM_API_KEY
        api_base = LLM_API_BASE
        model = LLM_MODEL

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
    )

    # ModelScope 的 Qwen3 系列和 GLM 系列默认开启 thinking，需要关掉
    # 注意：MiniMax 系列不是 Qwen/GLM，不需要也不能传 enable_thinking
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
            {"role": "user", "content": in_put}
        ],
        max_tokens=16384,
        stream=False,
        extra_body=extra_body if extra_body else None,
    )

    # 防御：choices 为空或 None
    if not response.choices:
        # 尝试从 response 对象提取有用信息
        resp_dict = response.model_dump() if hasattr(response, "model_dump") else {}
        error_msg = resp_dict.get("error", {})
        if isinstance(error_msg, dict):
            err_text = error_msg.get("message", str(error_msg))
        else:
            err_text = str(resp_dict)
        raise ValueError(
            f"模型 '{model}' 返回了空的 choices。\n"
            f"响应内容: {err_text}\n"
            f"可能是模型暂时不可用或请求被拒绝。"
        )

    msg = response.choices[0].message
    content = msg.content

    # 检测输出是否被截断
    finish = response.choices[0].finish_reason
    if finish == "length":
        print(f"[WARN] LLM output truncated (finish_reason=length), max_tokens may be too small")

    if content is None:
        # fallback：尝试多种字段名（不同 API 叫法不同）
        for attr in ("thinking_content", "reasoning_content", "text", "output"):
            fallback = getattr(msg, attr, None)
            if fallback:
                content = fallback
                break

    if content is None:
        # 最后一搏：尝试把 message 对象当 dict 看
        try:
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else vars(msg)
            for v in msg_dict.values():
                if isinstance(v, str) and v.strip():
                    content = v
                    break
        except Exception:
            pass

    if content is None:
        finish = response.choices[0].finish_reason
        raise ValueError(
            f"模型 '{model}' 返回内容为空（content=None），"
            f"finish_reason={finish}。\n"
            f"如果使用 MiniMax 系列，请改用 Qwen3.5-35B (ModelScope 免费) 或其他 Qwen 模型。"
        )
    return content


if __name__ == "__main__":
    result = text_ai("Hello, say hi in one sentence.")
    print(result)
