"""
release1 配置文件
集中管理所有模型路径、API Key、默认参数
"""

import os

# ========== 基础路径 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PROJECT_DIR = os.path.dirname(BASE_DIR)  # 上级 video/ 目录

# ========== ASR 模型（绝对路径指向 video/models/）==========
ASR_MODEL_DIR = os.path.join(
    r'C:\pythonproject\video', 'models', 'qwen', 'Qwen3-ForcedAligner-0.6B'
).replace('\\', '/')

# ========== LLM 提供商（划分场景/角色提取用）==========
LLM_PROVIDERS = {
    "Qwen3.5-35B (ModelScope 免费)": {
        "api_key": "ms-38de567b-cf88-4523-bac2-ff63d8f1e0f6",
        "api_base": "https://api-inference.modelscope.cn/v1/",
        "model": "Qwen/Qwen3.5-35B-A3B",
    },
    "GLM-4-9B (硅基流动 免费)": {
        "api_key": "sk-mjqgwknbttvqnrjjfnxemtjgdivogjaqsftbvoifwjvruwsq",
        "api_base": "https://api.siliconflow.cn/v1/",
        "model": "THUDM/glm-4-9b-chat",
    },
    "Qwen3-32B (硅基流动 付费)": {
        "api_key": "sk-mjqgwknbttvqnrjjfnxemtjgdivogjaqsftbvoifwjvruwsq",
        "api_base": "https://api.siliconflow.cn/v1/",
        "model": "Qwen/Qwen3-32B",
    },
    "GLM-5 (ModelScope 免费)": {
        "api_key": "ms-38de567b-cf88-4523-bac2-ff63d8f1e0f6",
        "api_base": "https://api-inference.modelscope.cn/v1/",
        "model": "ZhipuAI/GLM-5",
    },
}

# 默认 LLM（兼容旧代码）
DEFAULT_LLM = "Qwen3.5-35B (ModelScope 免费)"
LLM_API_KEY = LLM_PROVIDERS[DEFAULT_LLM]["api_key"]
LLM_API_BASE = LLM_PROVIDERS[DEFAULT_LLM]["api_base"]
LLM_MODEL = LLM_PROVIDERS[DEFAULT_LLM]["model"]

# ========== SiliconFlow API（Kolors 文生图）==========
SILICONFLOW_API_KEY = "sk-mjqgwknbttvqnrjjfnxemtjgdivogjaqsftbvoifwjvruwsq"
SILICONFLOW_API_BASE = "https://api.siliconflow.cn/v1/images/generations"

# ========== ModelScope API（Qwen 文生图）==========
MODELSCOPE_API_KEY = "ms-38de567b-cf88-4523-bac2-ff63d8f1e0f6"
MODELSCOPE_API_BASE = "https://api-inference.modelscope.cn/v1/images/generations"
MODELSCOPE_POLL_INTERVAL = 3  # 轮询间隔（秒）
MODELSCOPE_MAX_WAIT = 180     # 最大等待时间（秒）

# ========== 文生图模型 ==========
IMAGE_MODELS = {
    "Kolors（便宜快速）": {
        "provider": "siliconflow",
        "model": "Kwai-Kolors/Kolors",
        "default_size": "1280x720",
        "guidance_scale": 7.5,
    },
    "Qwen-Image（高质量）": {
        "provider": "modelscope",
        "model": "Qwen/Qwen-Image-2512",
        "default_size": "1280x720",
        "guidance_scale": 7.5,
    },
}

# 默认文生图模型
DEFAULT_IMAGE_MODEL = "Kolors（便宜快速）"

# ========== 默认参数 ==========
DEFAULT_FPS = 24
DEFAULT_VIDEO_SIZE = "1280x720"

# ========== 通用 negative prompt ==========
NEGATIVE_PROMPT = "blurry, low quality, deformed, text, letters, words, subtitle, logo, watermark, caption, label, number"
