"""
image_gen.py - Unified text-to-image interface.

Providers:
  - SiliconFlow (Kolors) — sync API
  - ModelScope (Qwen-Image) — async polling API
"""

import requests
import os
import time
from datetime import datetime
from config import IMAGE_MODELS, NEGATIVE_PROMPT


def _generate_siliconflow(prompt, model_id, size, guidance, neg, save_dir, filename, api_key, api_base):
    """SiliconFlow sync API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "prompt": prompt,
        "image_size": size,
        "n": 1,
        "num_inference_steps": 20,
        "guidance_scale": guidance,
        "negative_prompt": neg,
    }

    print(f"  [SiliconFlow] {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

    for attempt in range(6):
        resp = requests.post(api_base, headers=headers, json=payload, timeout=120)
        print(f"    HTTP {resp.status_code}: {resp.text[:300]}")

        if resp.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"    [!] Rate limited, waiting {wait}s ({attempt+1}/5)...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            raise Exception(f"SiliconFlow error ({resp.status_code}): {resp.text[:300]}")
        break
    else:
        raise Exception("SiliconFlow rate limit, retried 5 times.")

    result = resp.json()
    images = result.get("images", [])
    if not images:
        raise Exception(f"SiliconFlow returned no images: {result}")

    img_url = images[0].get("url")
    if not img_url:
        raise Exception(f"Empty image URL: {result}")

    img_data = requests.get(img_url, timeout=60).content

    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"kolors_{ts}.png"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(img_data)

    print(f"    [OK] {filename}")
    return {"url": img_url, "filepath": filepath}


def _generate_modelscope(prompt, model_id, size, guidance, neg, save_dir, filename, api_key, api_base):
    """ModelScope async polling API"""
    submit_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }
    payload = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "guidance_scale": guidance,
        "negative_prompt": neg,
    }

    print(f"  [ModelScope] {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    resp = requests.post(api_base, headers=submit_headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"ModelScope submit failed ({resp.status_code}): {resp.text[:300]}")

    result = resp.json()
    task_id = result.get("task_id")
    if not task_id:
        raise Exception(f"No task_id: {result}")
    print(f"    task_id: {task_id}")

    query_headers = {
        "Authorization": f"Bearer {api_key}",
        "X-ModelScope-Task-Type": "image_generation",
    }
    status_url = f"https://api-inference.modelscope.cn/v1/tasks/{task_id}"
    poll_interval = IMAGE_MODELS["Qwen-Image (ModelScope)"].get("poll_interval", 3)
    max_wait = IMAGE_MODELS["Qwen-Image (ModelScope)"].get("max_wait", 180)
    start = time.time()

    for attempt in range(100):
        if attempt > 0:
            time.sleep(poll_interval)
        elapsed = int(time.time() - start)
        if elapsed > max_wait:
            raise Exception(f"ModelScope timeout ({max_wait}s)")

        qresp = requests.get(status_url, headers=query_headers, timeout=30)
        if qresp.status_code != 200:
            continue

        qresult = qresp.json()
        task_status = qresult.get("task_status", "")
        if attempt % 5 == 0 or task_status in ("SUCCEED", "FAILED"):
            print(f"    [{elapsed}s] {task_status}")

        if task_status == "SUCCEED":
            output_images = (
                qresult.get("output_images")
                or qresult.get("outputs", {}).get("output_images")
                or []
            )
            if not output_images:
                raise Exception(f"SUCCEED but no images: {qresult}")
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
            raise Exception(f"ModelScope task failed: {qresult.get('errors', qresult)}")

    raise Exception(f"ModelScope timeout ({max_wait}s)")


def image_generate(
    prompt: str,
    save_dir: str = "./generated_images",
    model_name: str = None,
    filename: str = None,
    image_size: str = None,
    guidance_scale: float = None,
    negative_prompt: str = None,
) -> dict:
    """Unified text-to-image interface.

    Args:
        prompt: generation prompt
        save_dir: output directory
        model_name: model name (key in IMAGE_MODELS), None = default
        filename: output filename, None = auto
        image_size: image size, None = model default
    Returns:
        {"url": str, "filepath": str}
    """
    from config import DEFAULT_IMAGE_MODEL

    if model_name is None:
        model_name = DEFAULT_IMAGE_MODEL

    model_config = IMAGE_MODELS.get(model_name)
    if not model_config:
        raise ValueError(f"Unknown model: {model_name}, available: {list(IMAGE_MODELS.keys())}")

    api_key = model_config.get("api_key", "")
    if not api_key:
        raise ValueError(
            f"API key not configured for '{model_name}'. "
            f"Edit config.py and fill in the api_key field."
        )

    model_id = model_config["model"]
    size = image_size or model_config["default_size"]
    guidance = guidance_scale if guidance_scale is not None else model_config["guidance_scale"]
    neg = negative_prompt or NEGATIVE_PROMPT
    provider = model_config["provider"]
    api_base = model_config.get("api_base", "")

    os.makedirs(save_dir, exist_ok=True)

    if provider == "siliconflow":
        return _generate_siliconflow(prompt, model_id, size, guidance, neg, save_dir, filename, api_key, api_base)
    elif provider == "modelscope":
        return _generate_modelscope(prompt, model_id, size, guidance, neg, save_dir, filename, api_key, api_base)
    else:
        raise ValueError(f"Unknown provider: {provider}")


if __name__ == "__main__":
    for name in list(IMAGE_MODELS.keys()):
        print(f"\nTesting: {name}")
        result = image_generate("A cute cat sitting on a desk, 16:9", model_name=name)
        print(f"  Path: {result['filepath']}")
