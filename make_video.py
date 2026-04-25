"""
make_video.py - 场景图 + ASR 时间戳 + 音频 → 视频

流程：
1. 读取 voice.mp3 获取总时长
2. 读取 scene_plan.json 获取场景列表
3. 如果有 result.json（ASR 对齐），按对齐结果分配时间；否则平均分配
4. 用 moviepy 将场景图在对应时段显示，配上音频生成视频
"""

import os
import json
import math
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)


def load_scene_plan(workspace: str) -> dict:
    """读取 scene_plan.json"""
    path = os.path.join(workspace, 'scene_plan.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_asr_result(workspace: str) -> dict:
    """读取 result.json（ASR 对齐结果），如果不存在返回 None"""
    path = os.path.join(workspace, "result.json")
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def build_scene_timeline(scene_plan: dict, asr_result: dict, audio_duration: float,
                         workspace: str = None) -> list:
    """
    构建场景时间线。优先使用 scene 中已有的 start_time/end_time（ASR 步骤写入），
    没有则根据 ASR 文本匹配分配，再没有则平均分配。
    """
    scenes = scene_plan["scenes"]
    num_scenes = len(scenes)

    # --- 策略 1：直接使用 scene 已有的时间戳（ASR 步骤写入的） ---
    if all("start_time" in s and "end_time" in s for s in scenes):
        timeline = []
        for scene in scenes:
            timeline.append({
                "scene_id": scene["scene_id"],
                "start": scene["start_time"],
                "end": scene["end_time"],
                "has_match": True,
            })
        # 确保最后一个场景延伸到音频结尾
        if timeline:
            timeline[-1]["end"] = audio_duration
        return timeline

    # --- 策略 2：部分有时间戳，部分没有 ---
    has_timestamp = [s for s in scenes if "start_time" in s and "end_time" in s]
    if has_timestamp and len(has_timestamp) < num_scenes:
        timeline = []
        matched_end = 0.0
        for scene in scenes:
            if "start_time" in scene and "end_time" in scene:
                timeline.append({
                    "scene_id": scene["scene_id"],
                    "start": scene["start_time"],
                    "end": scene["end_time"],
                })
                matched_end = max(matched_end, scene["end_time"])
            else:
                timeline.append({
                    "scene_id": scene["scene_id"],
                    "start": None,
                    "end": None,
                })

        # 未匹配的场景按剩余时间平均分配
        unmatched_indices = [i for i, item in enumerate(timeline) if item["start"] is None]
        if unmatched_indices:
            remaining = audio_duration - matched_end
            if remaining > 0:
                seg_dur = remaining / len(unmatched_indices)
                t = matched_end
                for idx in unmatched_indices:
                    timeline[idx]["start"] = t
                    timeline[idx]["end"] = t + seg_dur
                    t += seg_dur
            else:
                for idx in unmatched_indices:
                    timeline[idx]["start"] = matched_end
                    timeline[idx]["end"] = matched_end + 2.0

        if timeline:
            timeline[-1]["end"] = audio_duration
        return timeline

    # --- 策略 3：没有任何时间戳，用 ASR 文本匹配或平均分配 ---
    if asr_result is not None:
        # 准备匹配用的文本
        scenes_for_match = []
        for scene in scenes:
            s = dict(scene)
            text_val = s.get("text", "")
            lines_val = s.get("lines", "")
            raw = text_val or lines_val or ""
            if isinstance(raw, str) and raw:
                s["lines"] = [x.strip() for x in raw.split("。") if x.strip()]
            elif isinstance(raw, list):
                s["lines"] = raw
            else:
                s["lines"] = []
            scenes_for_match.append(s)

        asr_segments = asr_result.get("segments", [])
        timeline = assign_scenes_to_segments(scenes_for_match, asr_segments, audio_duration)
    else:
        # 平均分配
        duration_per_scene = audio_duration / num_scenes
        timeline = []
        current_time = 0.0
        for scene in scenes:
            start = current_time
            end = min(current_time + duration_per_scene, audio_duration)
            timeline.append({
                "scene_id": scene["scene_id"],
                "start": start,
                "end": end,
            })
            current_time = end

    return timeline


def _normalize_text(text: str) -> str:
    """清理文本：去除标点、空格、转小写，用于相似度比较"""
    if not text:
        return ""
    # 去除所有非字母数字和非中文字符
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    return text.lower()


def _longest_common_substring_ratio(s1: str, s2: str) -> float:
    """
    计算两个字符串的最长公共子串比例
    
    使用动态规划，但为了性能优化：
    - 如果字符串太长，使用简化的滑动窗口方法
    """
    if not s1 or not s2:
        return 0.0
    
    # 对于短字符串，使用精确的 DP 算法
    if len(s1) * len(s2) < 100000:  # 乘积小于 10万
        m, n = len(s1), len(s2)
        # 优化空间复杂度：只用两行
        prev = [0] * (n + 1)
        curr = [0] * (n + 1)
        max_len = 0
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    curr[j] = prev[j-1] + 1
                    max_len = max(max_len, curr[j])
                else:
                    curr[j] = 0
            prev, curr = curr, [0] * (n + 1)
        
        return max_len / max(len(s1), len(s2))
    
    # 对于长字符串，使用简化的滑动窗口
    return _sliding_window_similarity(s1, s2)


def _sliding_window_similarity(s1: str, s2: str, window_size: int = 20) -> float:
    """
    滑动窗口相似度（用于长字符串的快速估算）
    
    将 s1 分成多个窗口，在 s2 中查找最佳匹配
    """
    if len(s1) <= window_size:
        # 如果 s1 本身很短，直接检查是否在 s2 中
        if s1 in s2:
            return 1.0
        # 否则检查每个字符的出现
        common = sum(1 for c in s1 if c in s2)
        return common / len(s1) if s1 else 0.0
    
    # 分窗口检查
    total_score = 0.0
    num_windows = 0
    
    for i in range(0, len(s1) - window_size + 1, window_size // 2):
        window = s1[i:i+window_size]
        if window in s2:
            total_score += 1.0
        else:
            # 部分匹配
            common = sum(1 for c in window if c in s2)
            total_score += common / window_size
        num_windows += 1
    
    return total_score / num_windows if num_windows > 0 else 0.0


def assign_scenes_to_segments(scenes: list, asr_segments: list, audio_duration: float) -> list:
    """
    基于文本相似度的精确匹配
    
    策略：
    1. 每个 scene 有 text 字段（原文片段）
    2. 在 ASR segments 中搜索这段文本的出现位置
    3. 使用最长公共子串相似度容忍 ASR 识别错误
    4. 阈值 60%，避免误匹配
    """
    SIMILARITY_THRESHOLD = 0.5  # 相似度阈值
    MAX_WINDOW_SIZE = 20  # 最多合并 20 个 ASR segments（长句需要更多）
    
    # 预处理：清理 ASR segments 的文本
    asr_cleaned = []
    for seg in asr_segments:
        text = seg.get('text', '').strip()
        if text:
            asr_cleaned.append({
                'text': text,
                'text_normalized': _normalize_text(text),
                'start': seg['start'],
                'end': seg['end']
            })
    
    def find_best_match(scene_text: str, start_seg_idx: int):
        """
        找到 scene_text 在 ASR segments 中的最佳匹配位置
        
        使用滑动窗口尝试不同长度的 segment 组合
        """
        if not scene_text or not scene_text.strip():
            return None
        
        scene_normalized = _normalize_text(scene_text)
        
        best_score = 0.0
        best_match = None
        
        # 滑动窗口：尝试不同数量的 segment 组合
        for window_size in range(1, min(MAX_WINDOW_SIZE + 1, len(asr_cleaned) - start_seg_idx + 1)):
            for i in range(start_seg_idx, len(asr_cleaned) - window_size + 1):
                # 合并多个 segments 的文本
                combined_text = ''.join(
                    seg['text_normalized'] for seg in asr_cleaned[i:i+window_size]
                )
                
                # 计算相似度
                similarity = _longest_common_substring_ratio(scene_normalized, combined_text)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = {
                        'start': asr_cleaned[i]['start'],
                        'end': asr_cleaned[i + window_size - 1]['end'],
                        'start_idx': i,
                        'end_idx': i + window_size - 1,
                        'similarity': similarity
                    }
                
                # 如果已经达到很高相似度，提前返回
                if similarity >= 0.90:
                    return best_match
        
        # 只有达到阈值才算匹配成功
        if best_score >= SIMILARITY_THRESHOLD:
            return best_match
        
        return None
    
    # 主匹配循环
    timeline_raw = []
    last_end_idx = 0  # 记录上一个匹配结束的位置
    
    for scene in scenes:
        # 优先使用 text 字段，兼容旧 lines 字段
        scene_text = scene.get('text', '') or scene.get('lines', '')
        if isinstance(scene_text, list):
            scene_text = ''.join(scene_text)
        
        match = find_best_match(scene_text, last_end_idx)
        
        if match:
            timeline_raw.append({
                'scene_id': scene['scene_id'],
                'start': match['start'],
                'end': match['end'],
                'has_match': True,
                'similarity': match['similarity']
            })
            # 下一个场景从当前匹配结束后开始
            last_end_idx = match['end_idx'] + 1
        else:
            timeline_raw.append({
                'scene_id': scene['scene_id'],
                'start': None,
                'end': None,
                'has_match': False,
                'similarity': 0.0
            })
    
    # 处理未匹配的场景：按剩余音频时间平均分配
    unmatched_indices = [i for i, item in enumerate(timeline_raw) if not item['has_match']]
    if unmatched_indices:
        # 找到已匹配场景的最大结束时间
        matched_end = 0.0
        for item in timeline_raw:
            if item['has_match'] and item['end']:
                matched_end = max(matched_end, item['end'])
        
        remaining_duration = audio_duration - matched_end
        if remaining_duration > 0 and len(unmatched_indices) > 0:
            seg_dur = remaining_duration / len(unmatched_indices)
            current_t = matched_end
            
            for idx in unmatched_indices:
                timeline_raw[idx]['start'] = current_t
                timeline_raw[idx]['end'] = current_t + seg_dur
                timeline_raw[idx]['has_match'] = True
                current_t += seg_dur
        else:
            # 如果没有剩余时间，给一个默认时长
            for idx in unmatched_indices:
                timeline_raw[idx]['start'] = matched_end
                timeline_raw[idx]['end'] = matched_end + 2.0
                timeline_raw[idx]['has_match'] = True
    
    # 确保每个场景至少有 0.5 秒
    for item in timeline_raw:
        if item['end'] is None or item['end'] <= item['start']:
            item['end'] = item['start'] + 0.5
    
    # 消除间隙：确保时间连续
    for i in range(len(timeline_raw) - 1):
        curr = timeline_raw[i]
        nxt = timeline_raw[i + 1]
        gap = nxt['start'] - curr['end']
        if gap > 0.01:  # 允许 10ms 的微小间隙
            curr['end'] = nxt['start']
    
    # 最后一个场景延伸到音频结尾
    if timeline_raw:
        timeline_raw[-1]['end'] = audio_duration
    
    # 合并极短的场景（< 1秒）到下一个场景
    merged = []
    skip_next = False
    for i in range(len(timeline_raw)):
        if skip_next:
            skip_next = False
            continue
        
        item = dict(timeline_raw[i])
        duration = item['end'] - item['start']
        
        # 如果当前场景太短且不是最后一个，合并到下一个
        if duration < 1.0 and i < len(timeline_raw) - 1:
            item['end'] = timeline_raw[i + 1]['end']
            merged.append(item)
            skip_next = True
        else:
            merged.append(item)
    
    return merged


def find_scene_image(workspace: str, scene_id: int) -> str:
    """查找场景图"""
    candidates = [
        os.path.join(workspace, "scene", f"scene_{scene_id:03d}.png"),
        os.path.join(workspace, "scene", f"scene_{scene_id}.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def create_video(workspace: str, timeline: list, audio_path: str, output_path: str,
                 fps: int = 24, img_size: tuple = (1280, 720),
                 subtitle: bool = True, log_fn=None):
    """
    用 moviepy 创建视频

    Args:
        workspace: 工作区路径
        timeline: 场景时间线
        audio_path: 音频文件路径
        output_path: 输出视频路径
        fps: 帧率
        img_size: 视频尺寸 (w, h)
        subtitle: 是否添加字幕
        log_fn: 日志回调函数
    """
    def log(msg):
        if log_fn:
            log_fn(msg)
        else:
            print(msg)

    clips = []
    for item in timeline:
        scene_id = item["scene_id"]
        start = item["start"]
        end = item["end"]
        duration = end - start

        if duration <= 0:
            continue

        img_path = find_scene_image(workspace, scene_id)
        if img_path:
            img_clip = ImageClip(img_path).with_duration(duration)
            img_clip = img_clip.resized(new_size=img_size)
        else:
            log(f"  [警告] scene_{scene_id} 无图片，使用纯色背景")
            img_clip = ColorClip(size=img_size, color=(50, 50, 50)).with_duration(duration)

        img_clip = img_clip.with_start(start)
        clips.append(img_clip)

    # 字幕
    if subtitle:
        asr_path = os.path.join(workspace, "result.json")
        if os.path.exists(asr_path):
            with open(asr_path, encoding="utf-8") as f:
                asr_result = json.load(f)
            segments = asr_result.get("segments", [])
            log(f"[*] 原始 ASR 片段: {len(segments)} 条")

            # 将 ASR segments 按时间分组（每段 3-5 秒，避免字幕堆满屏幕）
            def group_segments_into_sentences(segments: list) -> list:
                """
                将短的 ASR segments 合并成合理的字幕组。
                支持中文（字级）和英文（词级）ASR 输出。
                限制条件：
                - 每组最多 4 秒时长
                - 每组最多 40 个字符（中文）/ 60 个字符（英文，含空格）
                - 遇到句号等结束标点时提前分组
                """
                if not segments:
                    return []

                sentence_endings = set('。！？.!?…\n')
                MAX_CHARS = 60   # 字符上限（英文含空格时会更长）
                MAX_DURATION = 4.0

                def flush(text, start, end):
                    if text and start is not None:
                        grouped.append({"text": text.strip(), "start": start, "end": end})

                grouped = []
                current_words = []   # 词/字列表
                current_start = None
                current_end = None

                for seg in segments:
                    text = seg.get("text", "").strip()
                    if not text:
                        continue

                    seg_start = seg.get("start", 0)
                    seg_end = seg.get("end", 0)

                    if current_start is None:
                        current_start = seg_start

                    # 判断加入当前词后是否超限
                    # 用空格拼英文，中文直接拼（中文 seg 通常每个词自带空格或无需加）
                    preview_words = current_words + [text]
                    # 根据是否含非 ASCII 字符判断是中文还是英文
                    is_ascii_word = all(ord(c) < 128 for c in text)
                    if is_ascii_word:
                        preview_text = " ".join(preview_words)
                    else:
                        preview_text = "".join(preview_words)

                    preview_duration = seg_end - current_start

                    # 先检查：加入后是否超限 → 如果是，先 flush 旧组，再开新组
                    overflow = (
                        len(preview_text) > MAX_CHARS or
                        preview_duration > MAX_DURATION
                    )

                    if overflow and current_words:
                        # flush 当前组（不含新词）
                        if is_ascii_word:
                            flush(" ".join(current_words), current_start, current_end)
                        else:
                            flush("".join(current_words), current_start, current_end)
                        current_words = [text]
                        current_start = seg_start
                        current_end = seg_end
                    else:
                        current_words.append(text)
                        current_end = seg_end

                    # 如果当前词是句尾标点，立刻 flush
                    if text and text[-1] in sentence_endings:
                        if is_ascii_word:
                            flush(" ".join(current_words), current_start, current_end)
                        else:
                            flush("".join(current_words), current_start, current_end)
                        current_words = []
                        current_start = None
                        current_end = None

                # flush 剩余
                if current_words:
                    if all(ord(c) < 128 for c in current_words[0]):
                        flush(" ".join(current_words), current_start or 0, current_end or 0)
                    else:
                        flush("".join(current_words), current_start or 0, current_end or 0)

                return grouped
            
            # 按句子分组
            sentence_groups = group_segments_into_sentences(segments)
            log(f"[*] 添加字幕，共 {len(sentence_groups)} 个句子（从 {len(segments)} 个片段合并）")
            
            w, h = img_size
            font_size = max(int(h * 0.045), 20)
            margin_bottom = int(h * 0.10)
            max_chars_per_line = max(int(w / (font_size * 0.85)), 15)

            # 字体：优先黑体，fallback arial
            font_path = "C:/Windows/Fonts/simhei.ttf"
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/arial.ttf"

            try:
                pil_font = ImageFont.truetype(font_path, font_size)
            except Exception:
                pil_font = ImageFont.load_default()

            # 字体度量
            tmp_img = Image.new("RGBA", (1, 1))
            tmp_draw = ImageDraw.Draw(tmp_img)
            metrics = tmp_draw.textbbox((0, 0), "gypj8q", font=pil_font)
            font_full_height = metrics[3] - metrics[1]

            def wrap_text(text: str, max_chars: int) -> list:
                """按字符数拆分多行，优先在标点处断行"""
                if len(text) <= max_chars:
                    return [text]
                lines = []
                while len(text) > max_chars:
                    cut = max_chars
                    for i in range(max_chars, max(max_chars - 5, 0), -1):
                        if text[i] in "，。！？、；：\u201c\u201d\u2018\u2019\u2026\u2014,.!?;: ":
                            cut = i + 1
                            break
                    lines.append(text[:cut])
                    text = text[cut:]
                if text:
                    lines.append(text)
                return lines

            def render_subtitle_pil(text_lines: list) -> np.ndarray:
                """用 PIL 渲染多行字幕，返回 RGBA numpy 数组"""
                line_spacing = int(font_size * 0.35)
                line_height = font_full_height + line_spacing

                line_widths = []
                for line in text_lines:
                    bbox = tmp_draw.textbbox((0, 0), line, font=pil_font)
                    line_widths.append(bbox[2] - bbox[0])

                img_w = max(line_widths) + 6
                img_h = len(text_lines) * line_height + int(font_size * 0.3)

                img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)

                for idx, line in enumerate(text_lines):
                    x = (img_w - line_widths[idx]) // 2
                    y = idx * line_height
                    for dx in (-2, -1, 0, 1, 2):
                        for dy in (-2, -1, 0, 1, 2):
                            if dx == 0 and dy == 0:
                                continue
                            draw.text((x + dx, y + dy), line, fill=(0, 0, 0, 255), font=pil_font)
                    draw.text((x, y), line, fill=(255, 255, 255, 255), font=pil_font)

                return np.array(img)

            # 按句子显示字幕（而不是逐个片段）
            for sentence in sentence_groups:
                text = sentence["text"].strip()
                if not text:
                    continue
                seg_start = sentence["start"]
                seg_end = sentence["end"]
                seg_dur = seg_end - seg_start
                if seg_dur <= 0:
                    continue

                lines = wrap_text(text, max_chars_per_line)
                rgba = render_subtitle_pil(lines)

                txt_clip = ImageClip(rgba)
                txt_clip = txt_clip.with_position(("center", h - margin_bottom - rgba.shape[0]))
                txt_clip = txt_clip.with_duration(seg_dur).with_start(seg_start)
                clips.append(txt_clip)
        else:
            log("[提示] 未找到 result.json，跳过字幕")

    if not clips:
        raise ValueError("没有可用的场景片段！")

    # 加载音频
    audio = AudioFileClip(audio_path)

    # 合成视频
    video = CompositeVideoClip(clips, size=img_size)
    video = video.with_audio(audio)
    video = video.with_duration(audio.duration)

    # 导出
    video.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        audio_codec='aac',
        bitrate='8000k',
    )
    video.close()

    log(f"[OK] 视频已保存: {output_path}")


def main(workspace: str = None, fps: int = 24, size: str = "1280x720",
         subtitle: bool = True, log_fn=None):
    """
    主入口

    Args:
        workspace: 工作区路径
        fps: 帧率
        size: 视频尺寸 "WxH"
        subtitle: 是否添加字幕
        log_fn: 日志回调
    """
    from config import DEFAULT_VIDEO_SIZE

    if workspace is None:
        workspace = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workspace", "1")
    w, h = map(int, (size or DEFAULT_VIDEO_SIZE).split("x"))
    img_size = (w, h)

    def log(msg):
        if log_fn:
            log_fn(msg)
        else:
            print(msg)

    log(f"[视频合成] 工作区: {workspace}")
    log(f"[视频合成] 尺寸: {img_size}, FPS: {fps}")

    # 1. 加载 scene_plan
    scene_plan = load_scene_plan(workspace)
    num_scenes = len(scene_plan["scenes"])
    log(f"[视频合成] 共 {num_scenes} 个场景")

    # 2. 加载音频
    audio_path = os.path.join(workspace, "voice.mp3")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    # 使用 try-finally 确保音频资源正确释放
    audio = AudioFileClip(audio_path)
    try:
        audio_duration = audio.duration
        log(f"[视频合成] 音频时长: {audio_duration:.2f} 秒")
    finally:
        audio.close()

    # 3. 读取 ASR 结果
    asr_result = load_asr_result(workspace)
    if asr_result:
        seg_count = len(asr_result.get("segments", []))
        log(f"[视频合成] ASR: {seg_count} 个片段")
    else:
        log("[视频合成] 无 ASR 结果，按平均分配")

    # 4. 构建时间线
    timeline = build_scene_timeline(scene_plan, asr_result, audio_duration, workspace=workspace)

    log("[视频合成] 场景时间分配：")
    matched_count = 0
    unmatched_count = 0
    for item in timeline:
        dur = item['end'] - item['start']

        # 显示匹配质量
        similarity = item.get('similarity', 0.0)
        if similarity > 0:
            quality = f"[{similarity:.0%}]"
            matched_count += 1
        elif item.get('has_match', False):
            quality = "[OK]"
            matched_count += 1
        else:
            quality = "[兜底]"
            unmatched_count += 1

        log(f"  Scene {item['scene_id']:2d}: {item['start']:6.2f}s - {item['end']:6.2f}s ({dur:.2f}s) {quality}")
    
    if unmatched_count > 0:
        log(f"[警告] {unmatched_count}/{len(timeline)} 个场景未精确匹配，使用兜底分配")
    else:
        log(f"[OK] 所有场景均成功匹配")

    # 5. 生成视频
    has_image = sum(1 for item in timeline if find_scene_image(workspace, item["scene_id"]) is not None)
    log(f"[视频合成] 有图片场景: {has_image}/{len(timeline)}")

    if has_image == 0:
        log("[警告] 所有场景都没有图片，视频将使用纯色背景！")

    output_path = os.path.join(workspace, "output_video.mp4")
    create_video(workspace, timeline, audio_path, output_path, fps=fps, img_size=img_size,
                 subtitle=subtitle, log_fn=log_fn)
    log(f"[完成] 视频: {output_path}")
    return output_path


if __name__ == "__main__":
    main()
