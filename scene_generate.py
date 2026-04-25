"""
scene_generate.py - 场景图生成模块（简化版）
读取 scene_plan.json，对每个 pending 场景用文生图直接生成
不再需要角色元素图、Panel 拼图、img2img

支持断点续传：已生成的自动跳过，失败的可重试
"""

import json
import os
from datetime import datetime

# ========== 路径配置 ==========
WORKSPACE = "workspace/1"  # 运行时会被 gui.py 覆盖
PLAN_PATH = os.path.join(WORKSPACE, "scene_plan.json")
SCENE_IMG_DIR = os.path.join(WORKSPACE, "scene")


def load_plan() -> dict:
    with open(PLAN_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan: dict):
    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def generate_single_scene(
    scene: dict,
    idx: int,
    total: int,
    model_name: str,
    on_image_generated=None,
) -> dict:
    """
    生成单个场景的图片

    Args:
        scene: 场景信息 dict
        idx: 当前索引
        total: 总场景数
        model_name: 文生图模型名称
        on_image_generated: 回调函数 (scene, filepath)，用于 GUI 审查

    Returns:
        更新后的 scene dict
    """
    scene_id = scene["scene_id"]
    visual_prompt = scene["visual_prompt"]

    print(f"\n[场景 {scene_id}] [{idx+1}/{total}]")
    print(f"  Prompt: {visual_prompt[:80]}...")

    os.makedirs(SCENE_IMG_DIR, exist_ok=True)
    scene_filename = f"scene_{scene_id:03d}.png"
    filepath = os.path.join(SCENE_IMG_DIR, scene_filename)

    try:
        from image_gen import image_generate

        result = image_generate(
            prompt=visual_prompt,
            save_dir=SCENE_IMG_DIR,
            model_name=model_name,
            filename=scene_filename,
        )

        filepath = result["filepath"]
        scene["status"] = "generated"
        scene["filepath"] = filepath
        print(f"  [完成] {os.path.basename(filepath)}")

        # 如果有回调（GUI 审查），调用它
        if on_image_generated:
            on_image_generated(scene, filepath)

        return scene

    except Exception as e:
        scene["status"] = "failed"
        scene["error"] = str(e)
        print(f"  [失败] {e}")
        return scene


def main(workspace: str = None, model_name: str = "Kolors（便宜快速）"):
    """主流程：生成所有 pending 场景"""
    global WORKSPACE, PLAN_PATH, SCENE_IMG_DIR

    if workspace:
        WORKSPACE = workspace
    PLAN_PATH = os.path.join(WORKSPACE, "scene_plan.json")
    SCENE_IMG_DIR = os.path.join(WORKSPACE, "scene")

    if not os.path.exists(PLAN_PATH):
        raise FileNotFoundError(f"未找到 {PLAN_PATH}，请先运行场景划分")

    plan = load_plan()
    scenes = plan["scenes"]
    total = len(scenes)

    done = [s for s in scenes if s.get("status") == "generated"]
    failed = [s for s in scenes if s.get("status") == "failed"]
    pending = [s for s in scenes if s.get("status") == "pending"]
    print(f"总场景: {total} | 已完成: {len(done)} | 失败: {len(failed)} | 待生成: {len(pending)}")

    for idx, scene in enumerate(scenes):
        status = scene.get("status")
        if status == "generated":
            print(f"[{idx+1}/{total}] 场景 {scene['scene_id']} 已完成，跳过")
            continue

        updated = generate_single_scene(scene, idx, total, model_name)
        scenes[idx] = updated
        save_plan(plan)

        if updated["status"] == "failed":
            print(f"[停止] 场景 {scene['scene_id']} 生成失败，再次运行可续传")
            break

        print(f"进度: {sum(1 for s in scenes if s.get('status') == 'generated')}/{total}")

    done_count = sum(1 for s in scenes if s.get("status") == "generated")
    print(f"\n========== 完成 ==========")
    print(f"已完成: {done_count}/{total}")
    if done_count == total:
        print("[全部完成] 所有场景图已生成！")
    else:
        remaining = [s["scene_id"] for s in scenes if s.get("status") != "generated"]
        print(f"剩余: {remaining}")


if __name__ == "__main__":
    main()
