"""
config.py - All configuration for VidMarmot.

API keys, model paths, default parameters — everything lives here.
Edit this file directly to configure your setup.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ========== ASR Model ==========
# Default: project_dir/models/qwen/Qwen3-ForcedAligner-0.6B
# Override via env var VIDMARMOT_ASR_MODEL_DIR
ASR_MODEL_DIR = os.path.join(BASE_DIR, "models", "qwen", "Qwen3-ForcedAligner-0.6B").replace("\\", "/")


# ========== LLM Providers (scene planning / text generation) ==========
# Fill in your API keys below. Only providers with keys will be usable.
LLM_PROVIDERS = {
    "Qwen3.5-35B (ModelScope)": {
        "api_key": "",  # ← put your ModelScope API key here
        "api_base": "https://api-inference.modelscope.cn/v1/",
        "model": "Qwen/Qwen3.5-35B-A3B",
    },
    "GLM-4-9B (SiliconFlow)": {
        "api_key": "",  # ← put your SiliconFlow API key here
        "api_base": "https://api.siliconflow.cn/v1/",
        "model": "THUDM/glm-4-9b-chat",
    },
    "Qwen3-32B (SiliconFlow)": {
        "api_key": "",  # ← put your SiliconFlow API key here
        "api_base": "https://api.siliconflow.cn/v1/",
        "model": "Qwen/Qwen3-32B",
    },
    "GLM-5 (ModelScope)": {
        "api_key": "",  # ← put your ModelScope API key here
        "api_base": "https://api-inference.modelscope.cn/v1/",
        "model": "ZhipuAI/GLM-5",
    },
    "Qwen3-235B-A22B (Aliyun)": {
        "api_key": "",  # ← put your Aliyun DashScope API key here
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
        "model": "qwen3-235b-a22b",
    },
    "DeepSeek-V3": {
        "api_key": "",  # ← put your DeepSeek API key here
        "api_base": "https://api.deepseek.com/v1/",
        "model": "deepseek-chat",
    },
    "DeepSeek-R1": {
        "api_key": "",  # ← put your DeepSeek API key here
        "api_base": "https://api.deepseek.com/v1/",
        "model": "deepseek-reasoner",
    },
    "OpenAI (Custom Router)": {
        "api_key": "",  # ← put your OpenAI-compatible API key here
        "api_base": "https://api.openai.com/v1/",  # change if using a custom router
        "model": "gpt-4o",
    },
}


# ========== Text-to-Image Models ==========
# Fill in your API keys below.
IMAGE_MODELS = {
    "Kolors (SiliconFlow)": {
        "provider": "siliconflow",
        "api_key": "",  # ← put your SiliconFlow API key here
        "api_base": "https://api.siliconflow.cn/v1/images/generations",
        "model": "Kwai-Kolors/Kolors",
        "default_size": "1280x720",
        "guidance_scale": 7.5,
    },
    "Qwen-Image (ModelScope)": {
        "provider": "modelscope",
        "api_key": "",  # ← put your ModelScope API key here
        "api_base": "https://api-inference.modelscope.cn/v1/images/generations",
        "poll_interval": 3,
        "max_wait": 180,
        "model": "Qwen/Qwen-Image-2512",
        "default_size": "1280x720",
        "guidance_scale": 7.5,
    },
}

DEFAULT_IMAGE_MODEL = "Kolors (SiliconFlow)"


# ========== Defaults ==========
DEFAULT_FPS = 24
DEFAULT_VIDEO_SIZE = "1280x720"

# Negative prompt for image generation
NEGATIVE_PROMPT = "blurry, low quality, deformed, text, letters, words, subtitle, logo, watermark, caption, label, number"
