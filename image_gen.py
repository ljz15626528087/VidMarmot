"""
image_gen.py - 统一文生图接口
支持两个模型：
  - Kolors（便宜快速）→ SiliconFlow API（同步）
  - Qwen-Image（高质量）→ ModelScope API（异步轮询）
"""

import requests
import os
import time
from datetime import datetime
from config import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_API_BASE,
    MODELSCOPE_API_KEY,
    MODELSCOPE_API_BASE,
    MODELSCOPE_POLL_INTERVAL,
    MODELSCOPE_MAX_WAIT,
    IMAGE_MODELS,
    NEGATIVE_PROMPT,
)


def _generate_siliconflow(prompt, model_id, size, guidance, neg, save_dir, filename):
    """SiliconFlow 同步 API（Kolors）"""
    payload = {
        "model": model_id,
        "prompt": prompt,
        "image_size": size,
        "n": 1,
        "num_inference_steps": 20,
        "guidance_scale": guidance,
        "negative_prompt": neg,
    }

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }

    print(f"  [SiliconFlow] 提交: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

    for attempt in range(6):  # 最多重试 5 次
        resp = requests.post(SILICONFLOW_API_BASE, headers=headers, json=payload, timeout=120)
        print(f"    HTTP {resp.status_code}: {resp.text[:300]}")

        if resp.status_code == 429:
            wait = 15 * (attempt + 1)  # 15s, 30s, 45s, 60s, 75s
            print(f"    [!] 限频，等待 {wait}s 后重试 ({attempt+1}/5)...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            raise Exception(f"SiliconFlow 生成失败 ({resp.status_code}): {resp.text[:300]}")
        break
    else:
        raise Exception("SiliconFlow 持续限频，已重试 5 次，请稍后再试或切换模型")

    result = resp.json()
    images = result.get("images", [])
    if not images:
        raise Exception(f"SiliconFlow 返回无图片: {result}")

    img_url = images[0].get("url")
    if not img_url:
        raise Exception(f"返回图片 URL 为空: {result}")

    img_data = requests.get(img_url, timeout=60).content

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kolors_{ts}.png"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(img_data)

    print(f"    [OK] {filename}")
    return {"url": img_url, "filepath": filepath}


def _generate_modelscope(prompt, model_id, size, guidance, neg, save_dir, filename):
    """ModelScope 异步轮询 API（Qwen-Image）"""
    submit_headers = {
        "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true"
    }
    payload = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "guidance_scale": guidance,
        "negative_prompt": neg,
    }

    print(f"  [ModelScope] 提交: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    resp = requests.post(MODELSCOPE_API_BASE, headers=submit_headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"ModelScope 提交失败 ({resp.status_code}): {resp.text[:300]}")

    result = resp.json()
    task_id = result.get("task_id")
    if not task_id:
        raise Exception(f"未找到 task_id: {result}")
    print(f"    task_id: {task_id}")

    # 轮询结果
    query_headers = {
        "Authorization": f"Bearer {MODELSCOPE_API_KEY}",
        "X-ModelScope-Task-Type": "image_generation"
    }
    status_url = f"https://api-inference.modelscope.cn/v1/tasks/{task_id}"
    start = time.time()

    for attempt in range(100):
        if attempt > 0:
            time.sleep(MODELSCOPE_POLL_INTERVAL)
        elapsed = int(time.time() - start)
        if elapsed > MODELSCOPE_MAX_WAIT:
            raise Exception(f"ModelScope 超时（{MODELSCOPE_MAX_WAIT}s）")

        qresp = requests.get(status_url, headers=query_headers, timeout=30)
        if qresp.status_code != 200:
            continue

        qresult = qresp.json()
        task_status = qresult.get("task_status", "")
        if attempt % 5 == 0 or task_status in ("SUCCEED", "FAILED"):
            print(f"    [{elapsed}s] {task_status}")

        if task_status == "SUCCEED":
            output_images = (qresult.get("output_images")
                             or qresult.get("outputs", {}).get("output_images")
                             or [])
            if not output_images:
                raise Exception(f"SUCCEED 但无图片: {qresult}")
            url = output_images[0]
            img_data = requests.get(url, timeout=180).content

            if filename is None:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"qwen_{ts}.png"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(img_data)

            print(f"    [OK] {filename} ({elapsed}s)")
            return {"url": url, "filepath": filepath}

        elif task_status == "FAILED":
            raise Exception(f"ModelScope 任务失败: {qresult.get('errors', qresult)}")

    raise Exception(f"ModelScope 超时（{MODELSCOPE_MAX_WAIT}s）")


def image_generate(
    prompt: str,
    save_dir: str = "./generated_images",
    model_name: str = None,
    n: int = 1,
    seed: int = None,
    num_inference_steps: int = 20,
    guidance_scale: float = None,
    negative_prompt: str = None,
    filename: str = None,
    image_size: str = None,
) -> dict:
    """
    统一文生图接口

    Args:
        prompt: 生成提示词
        save_dir: 保存目录
        model_name: 模型名称（IMAGE_MODELS 的 key），默认用 config 中的 DEFAULT_IMAGE_MODEL
        image_size: 图片尺寸，默认 1280x720（16:9）

    Returns:
        dict: {"url": str, "filepath": str}
    """
    from config import DEFAULT_IMAGE_MODEL

    if model_name is None:
        model_name = DEFAULT_IMAGE_MODEL

    model_config = IMAGE_MODELS.get(model_name)
    if not model_config:
        raise ValueError(f"未知模型: {model_name}，可选: {list(IMAGE_MODELS.keys())}")

    model_id = model_config["model"]
    size = image_size or model_config["default_size"]
    guidance = guidance_scale if guidance_scale is not None else model_config["guidance_scale"]
    neg = negative_prompt or NEGATIVE_PROMPT

    os.makedirs(save_dir, exist_ok=True)

    provider = model_config["provider"]
    if provider == "siliconflow":
        return _generate_siliconflow(prompt, model_id, size, guidance, neg, save_dir, filename)
    elif provider == "modelscope":
        return _generate_modelscope(prompt, model_id, size, guidance, neg, save_dir, filename)
    else:
        raise ValueError(f"未知 provider: {provider}")


def get_available_models() -> list[str]:
    """返回可用的文生图模型名称列表"""
    return list(IMAGE_MODELS.keys())


if __name__ == "__main__":
    for name in get_available_models():
        print(f"\n测试模型: {name}")
        result = image_generate("A cute cat sitting on a desk, 16:9 aspect ratio", model_name=name)
        print(f"  路径: {result['filepath']}")
