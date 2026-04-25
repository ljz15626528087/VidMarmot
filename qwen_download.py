
from modelscope import snapshot_download
import os

# 1. 定义模型 ID
model_id = 'qwen/Qwen3-ForcedAligner-0.6B'

# 2. 在当前目录下创建 models 文件夹
save_dir = os.path.join(os.path.dirname(__file__), 'models')

# 创建目录（如果不存在）
os.makedirs(save_dir, exist_ok=True)

print(f"下载中... 保存至: {save_dir}")

try:
    model_dir = snapshot_download(model_id, cache_dir=save_dir)
    print(f"下载完成: {model_dir}")
except Exception as e:
    print(f"失败: {e}")
