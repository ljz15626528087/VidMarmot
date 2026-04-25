# Videoer

**AI-powered video generation pipeline** — 从文章到视频的一站式工具。

给定一篇英文文章（文本）和对应的朗读音频，自动完成：

```
文章文本 + 朗读音频 → AI 场景划分 → 逐场景生成配图 → ASR 时间对齐 → 合成视频（含字幕）
```

## Preview

![Pipeline Overview](docs/pipeline.png)

## Features

- **AI Scene Planning** — 基于 LLM（Qwen / GLM）智能划分场景，提取角色、画面描述
- **AI Image Generation** — 支持 Kolors / Qwen-Image 文生图模型，逐张生成场景配图
- **Interactive Review** — 逐张审查、确认/重新生成场景图
- **Forced Alignment** — 基于 Qwen3-ForcedAligner 的语音-文本时间对齐
- **Video Synthesis** — MoviePy 合成最终视频，自动添加字幕

## Architecture

```
release1/
├── gui.py            # PyQt6 GUI (main entry)
├── scene_plan.py     # LLM scene planning + prompt engineering
├── image_gen.py      # Text-to-image API calls
├── asr.py            # ASR forced alignment
├── make_video.py     # Video synthesis + subtitle rendering
├── text_ai.py        # Shared LLM API client
├── config.py         # Model paths, API keys, defaults
├── run.bat           # Windows launcher
└── qwen_download.py  # One-time model download script
```

## Workflow

```
1. Select workspace (folder with article.txt + voice.mp3)
2. AI Scene Planning   → scene_plan.json
3. Image Generation    → scene_01.png, scene_02.png, ...
4. ASR Alignment       → result.json + timestamps into scene_plan
5. Video Synthesis     → output_video.mp4
```

## Quick Start

### Prerequisites

- Python 3.12+
- Conda (recommended)
- NVIDIA GPU (for local ASR model)

### Setup

```bash
# Create conda environment
conda create -n Videoer python=3.12 -y
conda activate Videoer

# Install dependencies
pip install PyQt6 moviepy Pillow requests openai
pip install funasr modelscope torch torchaudio

# Download ASR model
python qwen_download.py
```

### Configuration

Edit `config.py` to set your API keys:

```python
# LLM providers (scene planning)
LLM_PROVIDERS = {
    "Qwen3.5-35B (ModelScope)": {
        "api_key": "YOUR_KEY",
        ...
    },
    ...
}

# Image generation
SILICONFLOW_API_KEY = "YOUR_KEY"
MODELSCOPE_API_KEY = "YOUR_KEY"
```

> **Tip**: ModelScope and SiliconFlow both offer free-tier API keys.

### Run

```bash
# GUI mode (recommended)
python gui.py

# Or on Windows
run.bat
```

### Workspace Structure

Each video project lives in a workspace folder:

```
workspace/my_project/
├── article.txt          # Source article text
├── voice.mp3            # Narration audio
├── scene_plan.json      # Generated scene plan (auto)
├── result.json          # ASR alignment result (auto)
├── scene_01.png         # Generated images (auto)
├── scene_02.png
├── ...
└── output_video.mp4     # Final output (auto)
```

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 | GUI framework |
| moviepy | Video composition |
| Pillow | Image processing / subtitle rendering |
| requests | HTTP API calls |
| openai | Compatible LLM client (OpenAI API format) |
| funasr | ASR forced alignment |
| modelscope | Model loading |
| torch / torchaudio | GPU inference backend |

## License

MIT
