"""
scene_plan.py - 场景划分模块
AI 读取 article.txt → 划分场景（用于 ASR 对齐）
输出 scene_plan.json
"""

import json
import os
import re
import subprocess
import textwrap
from text_ai import text_ai

# 默认工作区（仅用于独立运行时的测试）
_DEFAULT_WORKSPACE = "workspace/1"


# ========== 场景划分 ==========
PLANNER_SYSTEM = """You are an expert cinematic storyboard director and visual prompt engineer. Your task is to transform written articles into detailed, production-ready visual scenes for AI image generation.

## YOUR MISSION
Create richly detailed, cinematic visual prompts that bring the article to life through compelling imagery. Each scene should be a complete visual blueprint that an AI image generator can use to create stunning, professional-quality images.

---

## STEP 1 — ANALYZE THE ARTICLE TYPE

Classify the article into ONE of these categories:

**NARRATIVE** (stories, novels, scripts, personal anecdotes)
- Has characters with dialogue, emotional arcs, plot progression
- Requires character consistency across scenes

**KNOWLEDGE** (essays, science explainers, book reviews, historical analysis, philosophy)
- Abstract concepts, theories, ideas without specific characters
- Needs metaphorical and symbolic visualization

**TUTORIAL** (how-to guides, technical instructions, step-by-step processes)
- Procedural content with clear steps
- Focus on demonstrations and UI/screen elements

---

## STEP 2 — SCENE GRANULARITY STRATEGY

### FOR NARRATIVE ARTICLES:
Create **fine-grained scenes** (5-15 seconds each):
- One scene per meaningful action beat or emotional shift
- Dialogue exchanges: new scene when speaker changes or mood shifts
- Camera changes: close-up → wide shot = separate scenes
- Time/location jumps = new scene

### FOR KNOWLEDGE ARTICLES:
Create **moderate scenes** (8-20 seconds each):
- One scene per key concept or paragraph
- Don't over-merge: each distinct visual idea gets its own scene
- Use varied visualization techniques (see below)

### FOR TUTORIAL ARTICLES:
Create **step-based scenes** (5-12 seconds each):
- One scene per instruction step or sub-step
- Include before/after states if applicable

---

## STEP 3 — VISUAL PROMPT ENGINEERING (CRITICAL)

Your visual_prompt must be **DETAILED, SPECIFIC, and PRODUCTION-READY**. Follow this structure:

### MANDATORY ELEMENTS (in order):

**1. SHOT TYPE & CAMERA ANGLE** (choose specifically):
   - Extreme Close-Up (ECU): eyes, hands, small objects
   - Close-Up (CU): face, upper body
   - Medium Shot (MS): waist up, two people conversing
   - Full Shot (FS): entire body, room context
   - Wide Shot (WS): landscape, establishing shot
   - Bird's Eye View: overhead perspective
   - Dutch Angle: tilted camera for tension
   
**2. SUBJECT DESCRIPTION** (be extremely specific):
   
   FOR HUMANS (NEVER use names, always descriptive labels):
   - Age range: "a woman in her late 20s"
   - Ethnicity/Skin tone: "with warm olive skin" / "fair-skinned" / "deep brown skin"
   - Hair: "shoulder-length wavy black hair with subtle highlights"
   - Build: "slender build" / "athletic frame"
   - Clothing (specific): "wearing a cream-colored cashmere turtleneck sweater"
   - Expression: "with a contemplative, slightly melancholic expression"
   - Pose/Action: "gazing thoughtfully out a rain-streaked window"
   
   FIRST APPEARANCE: Define ALL physical traits completely
   SUBSEQUENT APPEARANCES: Reuse EXACT same description for consistency
   
   FOR OBJECTS/SETTINGS:
   - Material: "polished mahogany desk" / "weathered stone walls"
   - Condition: "vintage leather-bound books with gold embossing"
   - Arrangement: "arranged in neat stacks" / "scattered haphazardly"

**3. ENVIRONMENT/BACKGROUND** (layer the details):
   - Immediate setting: "in a cozy study room"
   - Background elements: "floor-to-ceiling bookshelves filled with ancient tomes"
   - Depth cues: "soft-focus background showing a fireplace with flickering flames"
   - Weather/Time: "on a misty autumn morning" / "during golden hour sunset"

**4. LIGHTING & ATMOSPHERE** (create mood):
   - Light source: "warm lamplight casting long shadows"
   - Quality: "soft diffused natural light from a large window"
   - Color temperature: "cool blue moonlight" / "warm amber candlelight"
   - Atmospheric effects: "dust motes dancing in sunbeams" / "gentle fog rolling across the scene"
   - Mood keywords: "serene and contemplative" / "tense and dramatic" / "nostalgic and dreamy"

**5. COMPOSITION & STYLE** (guide the aesthetic):
   - Rule of thirds: "subject positioned off-center following rule of thirds"
   - Leading lines: "perspective lines converging toward the subject"
   - Color palette: "muted earth tones with pops of burgundy" / "monochromatic blues"
   - Artistic style reference: "cinematic photography style reminiscent of Roger Deakins" / "painterly quality inspired by Edward Hopper" / "clean minimalist aesthetic"
   - Depth of field: "shallow depth of field with creamy bokeh" / "deep focus throughout"

**6. TECHNICAL QUALITIES** (ensure image quality):
   - Resolution hint: "ultra-high detail, 8k quality"
   - Texture emphasis: "rich textures visible in fabric and wood grain"
   - Sharpness: "razor-sharp focus on subject's eyes"

---

## VISUALIZATION TECHNIQUES FOR ABSTRACT CONCEPTS (Knowledge Articles)

When the text discusses abstract ideas, use these strategies:

**METAPHORICAL IMAGERY:**
- "Cultural bridge" → "an elegant stone bridge spanning a misty valley, connecting two distinct architectural styles, symbolizing East meets West"
- "Knowledge expansion" → "an open ancient book radiating golden light, with luminous particles forming constellations above it"

**HISTORICAL RECONSTRUCTION:**
- "ancient Chinese philosophy" → "a wise scholar in flowing Han dynasty robes sitting cross-legged on a bamboo mat, surrounded by scrolls, soft morning light filtering through paper windows"

**SYMBOLIC COMPOSITIONS:**
- "technological progress" → "a vintage pocket watch gradually transforming into a sleek smartwatch, gears and circuits merging, dramatic side lighting"

**PERSONIFICATION:**
- "artificial intelligence" → "a humanoid figure made of translucent glass and glowing neural networks, standing in a futuristic laboratory, blue and purple ambient lighting"

**DATA VISUALIZATION AS ART:**
- "statistical trends" → "elegant 3D bar charts rising like crystal structures from a reflective surface, bathed in gradient lighting from blue to orange"

---

## STEP 4 — CRITICAL RULES

1. **COMPLETE COVERAGE**: Every sentence in the article must appear in exactly one scene. No skipping.

2. **EXACT TEXT EXCERPTS**: The "text" field must contain VERBATIM quotes from the article. Do NOT paraphrase or summarize.

3. **LANGUAGE CONSISTENCY**: 
   - If article is in Chinese → write background AND visual_prompt in Chinese
   - If article is in English → write both in English
   - Maintain the article's language throughout

4. **PROMPT LENGTH & DETAIL**:
   - Minimum: 60 words
   - Ideal: 80-150 words
   - Maximum: 200 words
   - More detail = better image generation results

5. **AVOID THESE MISTAKES**:
   ❌ Vague: "a person thinking"
   ✅ Specific: "a young Asian woman with shoulder-length dark hair, wearing glasses and a white blouse, resting her chin on her hand while gazing thoughtfully at a laptop screen, soft afternoon light from a nearby window"
   
   ❌ Generic: "a beautiful landscape"
   ✅ Specific: "a sweeping mountain vista at sunrise, snow-capped peaks glowing pink and orange in the first light, wispy clouds drifting through valleys below, crisp alpine air suggested by sharp clarity"

6. **UNIQUENESS**: Each scene's text excerpt must be unique. No overlaps or duplicates.

7. **NEGATIVE PROMPT AVOIDANCE**: Do NOT include in visual_prompt:
   - Text, letters, words, captions, labels, watermarks, logos
   - Blurry, low quality, deformed elements
   - Multiple conflicting perspectives in one scene

---

## OUTPUT FORMAT

Return ONLY valid JSON. No markdown formatting. No explanations. No code blocks.

{
  "scenes": [
    {
      "scene_id": 1,
      "text": "Exact quote from the article covering this scene...",
      "background": "Detailed description of the setting, environment, and context in the article's language...",
      "visual_prompt": "[SHOT TYPE] + [SUBJECT] + [ENVIRONMENT] + [LIGHTING] + [COMPOSITION] + [STYLE]. Rich, detailed, production-ready prompt in the article's language, 80-150 words...",
      "status": "pending"
    },
    {
      "scene_id": 2,
      ...
    }
  ]
}

---

## EXAMPLES OF HIGH-QUALITY VISUAL PROMPTS

### Example 1 (Narrative - Chinese):
"visual_prompt": "中景镜头。一位三十岁左右的亚洲女性，皮肤白皙，留着齐肩的黑色直发，穿着米色羊绒毛衣和深灰色长裤，坐在咖啡馆靠窗的位置。她双手捧着一杯冒着热气的拿铁咖啡，眼神略带忧郁地凝视着窗外淅沥的雨滴。背景是模糊的咖啡馆内部，暖黄色的吊灯和木质桌椅营造出温馨的氛围。柔和的自然光透过布满雨珠的玻璃窗洒入，在她的侧脸投下温柔的阴影。电影感摄影风格，浅景深，温暖的色调，充满沉思和怀旧的情绪。"

### Example 2 (Knowledge - English):
"visual_prompt": "Wide establishing shot. An ancient library interior with towering floor-to-ceiling oak bookshelves filled with leather-bound volumes dating back centuries. A grand wooden reading table sits in the center, illuminated by a single ornate brass lamp casting warm golden light. Dust motes dance in the atmospheric light beams streaming through tall arched windows. The perspective uses leading lines from the bookshelf aisles converging toward a distant figure of a scholar in Renaissance-era robes. Cinematic photography with deep shadows and rich amber tones, reminiscent of classical paintings by Rembrandt. Ultra-detailed, showcasing intricate wood carvings and the texture of aged parchment."

### Example 3 (Tutorial - Chinese):
"visual_prompt": "特写镜头。一双修长的手正在操作一台银色的笔记本电脑，屏幕上显示着Python代码编辑器界面，代码清晰可见。手指悬停在键盘上方，准备敲击回车键。桌面整洁，旁边放着一杯绿茶和一个打开的笔记本，上面有手写的流程图。明亮的白色台灯光线从左侧照射，营造专注的工作氛围。现代简约风格，高清晰度，强调屏幕上的代码细节和手指的动作瞬间。冷色调为主，点缀温暖的木质桌面纹理。"

---

NOW, analyze the provided article and create your detailed scene breakdown. Remember: MORE DETAIL = BETTER IMAGES. Be specific, be cinematic, be creative.
"""


def _fix_json_text(text: str) -> str:
    """尝试修复 LLM 返回的常见 JSON 格式问题"""
    # 找第一个 { 到最后一个 } 之间的内容
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return text
    text = text[start:end+1]

    # 修复：中文引号 "" '' 替换为转义
    text = text.replace("\u201c", '\\"').replace("\u201d", '\\"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")

    # 修复：把 \n 换行符字面文本变成真正的换行（LLM 有时输出 \\n）
    text = text.replace("\\n", "\n")

    # 修复：控制字符（除了换行和制表）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    return text


def _extract_scenes_fallback(text: str) -> list:
    """
    主力解析方案：逐个提取 scene 块。
    先尝试 json.loads，失败就用正则暴力提取。
    """
    scenes = []
    # 匹配 "scene_id" 字段所在的 { } 块，兼容多余引号如 "scene_id": 23"
    pattern = r'\{\s*"scene_id"\s*:\s*"?(\d+)"?\s*[,\s]'
    pos = 0
    while True:
        m = re.search(pattern, text[pos:])
        if not m:
            break
        block_start = pos + m.start()
        # 从这个 { 开始找匹配的 }
        depth = 0
        i = block_start
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    block = text[block_start:i+1]
                    # 清理控制字符
                    block = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', block)
                    # 先尝试 json.loads
                    try:
                        scene = json.loads(block)
                        if isinstance(scene, dict) and "scene_id" in scene:
                            scenes.append(scene)
                    except json.JSONDecodeError:
                        # json.loads 失败，暴力提取
                        scene = _brute_extract_scene(block)
                        if scene:
                            scenes.append(scene)
                    break
            i += 1
        pos = block_start + 1
    return scenes


def _brute_extract_scene(block: str) -> dict | None:
    """暴力从一段文本中提取 scene 字段，不依赖 json.loads"""
    scene = {}

    # scene_id：兼容多余引号
    m_id = re.search(r'"scene_id"\s*:\s*"?(\d+)"?', block)
    if m_id:
        scene["scene_id"] = int(m_id.group(1))
    else:
        return None

    # text：可能有中文内容，匹配到下一个字段前
    m_text = re.search(r'"text"\s*:\s*"(.+?)"\s*(?:,|\})', block, re.DOTALL)
    if m_text:
        scene["text"] = m_text.group(1).strip()

    # 兼容旧字段 lines
    if "text" not in scene:
        m_lines = re.search(r'"lines"\s*:\s*"(.+?)"\s*(?:,|\})', block, re.DOTALL)
        if m_lines:
            scene["text"] = m_lines.group(1).strip()

    # background：可能有中文引号 "" 嵌套
    m_bg = re.search(r'"background"\s*:\s*"(.+?)"\s*,\s*"visual_prompt"', block, re.DOTALL)
    if m_bg:
        scene["background"] = m_bg.group(1).strip()
    else:
        # 兜底：匹配到最后一个 " 之前
        m_bg2 = re.search(r'"background"\s*:\s*"(.+?)"\s*(?:,|\})', block, re.DOTALL)
        if m_bg2:
            scene["background"] = m_bg2.group(1).strip()

    # visual_prompt
    m_prompt = re.search(r'"visual_prompt"\s*:\s*"(.+?)"\s*,\s*"status"', block, re.DOTALL)
    if m_prompt:
        scene["visual_prompt"] = m_prompt.group(1).strip()
    else:
        m_prompt = re.search(r'"visual_prompt"\s*:\s*"(.+)"\s*\}', block, re.DOTALL)
        if m_prompt:
            scene["visual_prompt"] = m_prompt.group(1).strip()
        else:
            scene["visual_prompt"] = "No visual prompt"

    if "text" not in scene:
        scene["text"] = ""
    scene["status"] = "pending"
    return scene


def _get_audio_duration(audio_path: str) -> float | None:
    """Get audio duration in seconds. Tries ffprobe first, falls back to mutagen."""
    if not audio_path or not os.path.exists(audio_path):
        print(f"[DEBUG] audio not found: {audio_path}")
        return None

    # Method 1: ffprobe
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_path],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        raw = result.stdout.strip()
        if raw:
            return float(raw)
    except FileNotFoundError:
        print("[DEBUG] ffprobe not found, trying mutagen...")
    except Exception as e:
        print(f"[DEBUG] ffprobe error: {e}")

    # Method 2: mutagen (pure Python, no external binary)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except ImportError:
        print("[DEBUG] mutagen not installed. Run: pip install mutagen")
    except Exception as e:
        print(f"[DEBUG] mutagen error: {e}")

    return None


def plan_scenes(article_text: str, workspace: str = None, provider: str = None, user_note: str = None) -> dict:
    """
    调用 AI 划分场景
    
    Args:
        article_text: 文章文本
        workspace: 工作区路径（包含 article.txt 和 voice.mp3）
        provider: LLM 提供商名称
        user_note: 用户添加的备注（可选）
    """
    if workspace is None:
        workspace = _DEFAULT_WORKSPACE
    
    # 获取音频时长
    audio_path = os.path.join(workspace, "voice.mp3")
    duration = _get_audio_duration(audio_path)
    duration_hint = ""
    if duration and duration > 0:
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        min_scenes = max(5, int(duration / 60 * 5))   # ~5 scenes/min
        max_scenes = int(duration / 60 * 16)            # ~16 scenes/min
        duration_hint = f"""
IMPORTANT — AUDIO DURATION CONSTRAINT:
The voiceover audio is exactly {minutes}m {seconds}s ({int(duration)} seconds).
Recommended scene count: {min_scenes} to {max_scenes} (each scene ~5-15 seconds).
This is a recommendation for pacing. You may adjust based on the article's content."""

    # 构建用户备注部分
    user_note_section = ""
    if user_note and user_note.strip():
        user_note_section = f"""
---

## USER'S SPECIAL INSTRUCTIONS

Please pay attention to the following special requirements from the user:

{user_note.strip()}

Incorporate these instructions into your scene planning and visual prompt generation.

---
"""

    prompt = f"""## ARTICLE TO CONVERT

Here is the complete article text that you need to divide into visual scenes:

{textwrap.dedent(article_text)}

---

## YOUR TASK

Analyze this article thoroughly and create a detailed scene-by-scene visual breakdown following the guidelines in the system prompt.

**Key Requirements:**
1. **Cover every sentence** - Do not skip any content
2. **Be extremely detailed** in visual prompts (80-150 words each)
3. **Use cinematic language** - shot types, lighting, composition, mood
4. **Maintain consistency** - characters look the same across scenes
5. **Match the article's language** - if Chinese, write prompts in Chinese

{duration_hint}
{user_note_section}
**Remember:** Your visual prompts will be used directly by AI image generators. The more specific and detailed you are, the better the final images will be. Think like a film director planning each shot.

Now, create your scene breakdown with rich, production-ready visual prompts.
"""

    print("=" * 60)
    print(f"[PROMPT] system prompt: {len(PLANNER_SYSTEM)} chars")
    print(f"[PROMPT] user prompt: {len(prompt)} chars")
    print("=" * 60)

    response = text_ai(prompt, PLANNER_SYSTEM, provider=provider)

    if response is None:
        raise ValueError("text_ai 返回了 None，请检查 LLM 配置和网络连接")

    # 保存原始 LLM 返回供调试
    plan_path = os.path.join(workspace, "scene_plan.json")
    debug_path = os.path.join(workspace, "_debug_response.txt")
    try:
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(f"[DEBUG] 原始返回已保存到 {debug_path}")
    except Exception:
        pass

    print(f"[DEBUG] LLM response length: {len(response)} chars")

    # 清理可能的 markdown 包裹
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("```")
        text = lines[1] if len(lines) > 1 else lines[0]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    # 解析 JSON：先尝试 json.loads（快速通道），失败就暴力提取（主力方案）
    data = None
    scenes = None

    for attempt, raw in enumerate([text, _fix_json_text(text)]):
        try:
            data = json.loads(raw)
            break
        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON parse attempt {attempt+1} failed: {e.msg} at line {e.lineno} col {e.colno}")

    if data is None:
        # 暴力逐块提取
        scenes = _extract_scenes_fallback(text)
        if scenes:
            print(f"[RECOVERY] JSON 整体解析失败，暴力提取到 {len(scenes)} 个场景")

    # 从解析结果中提取 scenes 列表
    if scenes is not None:
        pass  # 已经有 scenes 了
    elif data is not None:
        if isinstance(data, list):
            scenes = data
        elif "scenes" in data:
            scenes = data["scenes"]
        else:
            for v in data.values():
                if isinstance(v, list) and v and "scene_id" in v[0]:
                    scenes = v
                    break

    if not scenes:
        raise ValueError("AI 返回内容无法解析为场景数据。请查看工作区下的 _debug_response.txt")

    return {"scenes": scenes}


def main(workspace: str = None, provider: str = None, user_note: str = None):
    """
    执行场景划分
    
    Args:
        workspace: 工作区路径（包含 article.txt）
        provider: LLM 提供商名称
        user_note: 用户添加的备注（可选）
    """
    if workspace is None:
        workspace = _DEFAULT_WORKSPACE
    
    plan_path = os.path.join(workspace, "scene_plan.json")
    article_path = os.path.join(workspace, "article.txt")

    print("[场景划分] 开始...")
    print(f"  工作区: {workspace}")

    # 1. 读取 article（原文，不编号）
    with open(article_path, encoding="utf-8") as f:
        article_raw = f.read().strip()
    # 过滤无意义行
    article_lines = [l.strip() for l in article_raw.split("\n") if l.strip() and l.strip() != "Identifying the speaker"]
    article_text = "\n".join(article_lines)
    print(f"  Article 长度: {len(article_text)} 字符")

    # 2. AI 划分场景
    plan = plan_scenes(article_text, workspace=workspace, provider=provider, user_note=user_note)
    scenes = plan["scenes"]

    # 3. 确保每个 scene 有必要字段
    for i, scene in enumerate(scenes):
        if "status" not in scene:
            scene["status"] = "pending"
        if "scene_id" not in scene:
            scene["scene_id"] = i + 1
        else:
            scene["scene_id"] = int(scene["scene_id"])
        if "visual_prompt" not in scene:
            scene["visual_prompt"] = scene.get("background") or scene.get("description") or "No visual prompt"
        if "text" not in scene:
            # 兼容旧字段 lines
            scene["text"] = scene.get("lines", "")
        if "background" not in scene:
            scene["background"] = ""
        # 清理旧字段
        scene.pop("lines", None)

    # 4. 保存计划
    output = {
        "total_scenes": len(scenes),
        "scenes": scenes
    }
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[场景划分] 完成，共 {len(scenes)} 个场景，已保存到 {plan_path}")
    print("\n" + "="*80)
    for s in scenes:
        scene_id = s['scene_id']
        text_preview = (s.get("text", "") or "").replace('\n', ' ')[:50]
        prompt_preview = s.get('visual_prompt', '')[:80]
        bg_preview = s.get('background', '')[:50]
        
        print(f"[SCENE {scene_id:2d}]")
        print(f"   TEXT: {text_preview}...")
        print(f"   PROMPT: {prompt_preview}...")
        print(f"   BG: {bg_preview}...")
    print("\n" + "="*80)
    
    # 统计信息
    total_prompt_words = sum(len(s.get('visual_prompt', '').split()) for s in scenes)
    avg_prompt_len = total_prompt_words / len(scenes) if scenes else 0
    print(f"\n[STATS]")
    print(f"   AVG PROMPT LENGTH: {avg_prompt_len:.0f} words/scene")
    print(f"   TOTAL SCENES: {len(scenes)}")

    if avg_prompt_len < 50:
        print(f"   [WARN] Prompts are short, consider more detail for better image quality")
    elif avg_prompt_len >= 80:
        print(f"   [OK] Prompt detail level is good")

    return plan


if __name__ == "__main__":
    main()
