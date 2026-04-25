"""
asr.py - ASR 强制对齐模块（简化版）
使用 Qwen3-ForcedAligner 对齐音频和文本
模型路径通过 config.py 中的绝对路径指向
"""

import os
import json
import re


def _detect_language(text: str) -> str:
    """根据文本字符分布自动检测语言"""
    if not text:
        return "English"
    # 统计非 ASCII 字符（中文等）
    non_ascii = sum(1 for c in text if ord(c) >= 0x4e00)
    ratio = non_ascii / len(text)
    return "Chinese" if ratio > 0.1 else "English"


def run_asr(workspace: str, language: str = None) -> dict:
    """
    执行 ASR 强制对齐

    Args:
        workspace: 工作区路径（含 article.txt 和 voice.mp3）

    Returns:
        dict: {"audio": str, "text": str, "segments": list}
    """
    from config import ASR_MODEL_DIR
    from qwen_asr import Qwen3ForcedAligner

    audio_path = os.path.join(workspace, "voice.mp3")
    text_path = os.path.join(workspace, "article.txt")
    output_path = os.path.join(workspace, "result.json")

    # 验证路径
    if not os.path.exists(ASR_MODEL_DIR):
        raise FileNotFoundError(f"ASR 模型路径不存在: {ASR_MODEL_DIR}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    if not os.path.exists(text_path):
        raise FileNotFoundError(f"文本文件不存在: {text_path}")

    # 读取文本
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    print(f"[ASR] 文本长度: {len(text)} 字符")
    print(f"[ASR] 音频文件: {audio_path}")
    print(f"[ASR] 模型路径: {ASR_MODEL_DIR}")

    # 加载模型
    print("[ASR] 正在加载模型...")
    aligner = Qwen3ForcedAligner.from_pretrained(
        ASR_MODEL_DIR,
        local_files_only=True,
        device_map="cpu"
    )
    print("[ASR] 模型加载成功")

    # 自动检测语言（如果未指定）
    if language is None:
        language = _detect_language(text)
    print(f"[ASR] 检测语言: {language}")

    # 运行对齐
    print("[ASR] 正在对齐...")
    results = aligner.align(
        audio=audio_path,
        text=text,
        language=language
    )

    # 整理结果
    segments = []
    for result in results:
        for item in result.items:
            segments.append({
                "text": item.text,
                "start": round(item.start_time, 3),
                "end": round(item.end_time, 3)
            })

    output_data = {
        "audio": audio_path,
        "text": text,
        "segments": segments
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[ASR] 完成，共 {len(segments)} 个片段，保存到 {output_path}")
    return output_data


def match_scenes_to_audio(workspace: str) -> dict:
    """
    将 ASR segments 与 scene_plan 的 scenes 做文本匹配，
    给每个 scene 写入 start_time / end_time，并更新 scene_plan.json。

    Returns:
        dict: 更新后的 scene_plan（带时间信息）
    """
    from make_video import load_scene_plan, load_asr_result, assign_scenes_to_segments
    from scene_plan import _get_audio_duration

    plan_path = os.path.join(workspace, "scene_plan.json")
    result_path = os.path.join(workspace, "result.json")
    audio_path = os.path.join(workspace, "voice.mp3")

    if not os.path.exists(plan_path):
        raise FileNotFoundError(f"scene_plan.json 不存在: {plan_path}")
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"result.json 不存在: {result_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"voice.mp3 不存在: {audio_path}")

    scene_plan = load_scene_plan(workspace)
    asr_result = load_asr_result(workspace)

    audio_duration = _get_audio_duration(audio_path)
    if audio_duration is None:
        raise RuntimeError(f"无法获取音频时长: {audio_path}")

    # 恢复每个场景的文本用于 ASR 匹配
    # 优先用 text 字段（原文片段），兼容旧 lines 字段
    for scene in scene_plan["scenes"]:
        text_val = scene.get("text", "")
        lines_val = scene.get("lines", "")
        raw = text_val or lines_val or ""
        if isinstance(raw, str) and raw:
            # 按句号分句供匹配
            scene["lines"] = [s.strip() for s in raw.split("。") if s.strip()]
        else:
            scene["lines"] = []

    # 复用 make_video 的匹配逻辑
    timeline = assign_scenes_to_segments(
        scene_plan["scenes"], asr_result.get("segments", []), audio_duration
    )

    # 写回 scene_plan
    for item in timeline:
        scene_id = item["scene_id"]
        for scene in scene_plan["scenes"]:
            if scene["scene_id"] == scene_id:
                scene["start_time"] = round(item["start"], 3)
                scene["end_time"] = round(item["end"], 3)
                break

    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(scene_plan, f, ensure_ascii=False, indent=2)

    print(f"[匹配] 完成，已将时间信息写入 {plan_path}")
    for item in timeline:
        dur = item["end"] - item["start"]
        print(f"  Scene {item['scene_id']:2d}: {item['start']:6.2f}s - {item['end']:6.2f}s ({dur:.2f}s)")

    return scene_plan


if __name__ == "__main__":
    run_asr(os.path.join(os.path.dirname(__file__), "workspace", "1"))
