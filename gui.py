#!/usr/bin/env python3
"""
gui.py - 视频制作流水线 GUI（release1）
唯一入口，PyQt6 暗色主题

流程：选工作区 → 划分场景 → 逐张生成+审查 → ASR → 合成视频
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime

# 强制确保工作目录和模块搜索路径都是 gui.py 所在目录
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SCRIPT_DIR)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# 全局异常日志文件
_LOG_PATH = os.path.join(_SCRIPT_DIR, "crash.log")

def _write_crash(msg):
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n{datetime.now().isoformat()}\n{msg}\n{'='*60}\n")

# 捕获所有未处理异常
sys.excepthook = lambda exc_type, exc_val, exc_tb: _write_crash("".join(traceback.format_exception(exc_type, exc_val, exc_tb)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QListWidget,
    QListWidgetItem, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QSplitter, QProgressBar, QSizePolicy, QDialog,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QWaitCondition, QTimer
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QIcon


from config import IMAGE_MODELS, DEFAULT_IMAGE_MODEL, DEFAULT_FPS, DEFAULT_VIDEO_SIZE, LLM_PROVIDERS, DEFAULT_LLM


# ============================================================
# 暗色主题样式表
# ============================================================
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    font-weight: bold;
    font-size: 14px;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QPushButton {
    background-color: #45475a;
    color: #cdd6f4;
    border: 1px solid #585b70;
    border-radius: 5px;
    padding: 7px 18px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #585b70;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QPushButton:disabled {
    background-color: #313244;
    color: #6c7086;
    border-color: #313244;
}

QPushButton#btnConfirm {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    padding: 10px 24px;
}
QPushButton#btnConfirm:hover {
    background-color: #94e2d5;
}
QPushButton#btnConfirm:disabled {
    background-color: #313244;
    color: #6c7086;
}

QPushButton#btnRegenerate {
    background-color: #f9e2af;
    color: #1e1e2e;
    font-weight: bold;
    padding: 10px 24px;
}
QPushButton#btnRegenerate:hover {
    background-color: #f5c2e7;
}

QPushButton#btnSkip {
    background-color: #fab387;
    color: #1e1e2e;
    font-weight: bold;
    padding: 10px 24px;
}
QPushButton#btnSkip:hover {
    background-color: #f38ba8;
}

QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 22px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
    border: 1px solid #45475a;
}

QCheckBox {
    spacing: 6px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #585b70;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QTextEdit, QListWidget {
    background-color: #181825;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 4px;
}
QTextEdit:focus, QListWidget:focus {
    border-color: #89b4fa;
}

QListWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #313244;
}
QListWidget::item:selected {
    background-color: #45475a;
    color: #89b4fa;
}
QListWidget::item:hover {
    background-color: #313244;
}

QProgressBar {
    border: 1px solid #45475a;
    border-radius: 4px;
    text-align: center;
    background-color: #313244;
    color: #cdd6f4;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #cba6f7;
    padding: 4px;
}

QLabel#sectionLabel {
    font-size: 13px;
    color: #a6adc8;
}

QLabel#sceneInfo {
    font-size: 12px;
    color: #a6adc8;
    padding: 4px 0px;
}

QSplitter::handle {
    background-color: #45475a;
    width: 2px;
}

QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


# ============================================================
# 备注对话框
# ============================================================
class NoteDialog(QDialog):
    """在发送消息给AI之前添加备注的对话框"""
    
    def __init__(self, parent=None, title="添加备注", message=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 说明标签
        info_label = QLabel("您可以在下方添加额外的说明、上下文或特殊要求，这些信息将一并发送给AI：")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #6c7086; font-size: 13px;")
        layout.addWidget(info_label)
        
        # 主要消息显示（只读）
        if message:
            msg_group = QGroupBox("主要消息")
            msg_layout = QVBoxLayout(msg_group)
            self.message_display = QTextEdit()
            self.message_display.setPlainText(message)
            self.message_display.setReadOnly(True)
            self.message_display.setMaximumHeight(100)
            self.message_display.setStyleSheet("""
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px;
            """)
            msg_layout.addWidget(self.message_display)
            layout.addWidget(msg_group)
        
        # 备注输入框
        note_group = QGroupBox("给AI的备注（可选）")
        note_layout = QVBoxLayout(note_group)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText(
            "例如：\n"
            "- 请多划分一些场景，我想要更细致的节奏\n"
            "- 这篇文章是抒情散文，请用更诗意的视觉语言\n"
            "- 场景提示词要特别详细，包含更多光影和构图细节\n"
            "- 这是科技类文章，多用现代、简洁的视觉元素"
        )
        self.note_input.setMaximumHeight(150)
        self.note_input.setStyleSheet("""
            background-color: #181825;
            border: 1px solid #45475a;
            border-radius: 4px;
            padding: 8px;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        """)
        note_layout.addWidget(self.note_input)
        
        # 字符计数
        self.char_count_label = QLabel("0/500")
        self.char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.char_count_label.setStyleSheet("font-size: 11px; color: #6c7086;")
        note_layout.addWidget(self.char_count_label)
        
        layout.addWidget(note_group)
        
        # 快速模板按钮
        template_group = QGroupBox("快速模板")
        template_layout = QHBoxLayout(template_group)
        template_layout.setSpacing(8)
        
        templates = [
            ("更多场景", "请将场景划分得更细致一些，每个场景控制在5-8秒，适合快节奏视频"),
            ("更少场景", "请合并相关场景，每个场景可以稍长一些（10-15秒），减少场景总数"),
            ("强调视觉", "请特别注重视觉描述的详细程度，提供丰富的画面细节和光影效果"),
            ("中文提示词", "请确保所有视觉提示词都使用中文，包括场景描述、光影、构图等"),
        ]
        
        for btn_text, template_text in templates:
            btn = QPushButton(btn_text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45475a;
                    border-color: #89b4fa;
                }
            """)
            btn.clicked.connect(lambda checked, t=template_text: self._apply_template(t))
            template_layout.addWidget(btn)
        
        layout.addWidget(template_group)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Ok
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("发送")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
        """)
        
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #45475a;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
        """)
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # 连接字符计数
        self.note_input.textChanged.connect(self._update_char_count)
        
        # 聚焦到备注输入框
        self.note_input.setFocus()
    
    def _apply_template(self, template_text: str):
        """应用快速模板"""
        self.note_input.setPlainText(template_text)
        self._update_char_count()
    
    def _update_char_count(self):
        """更新字符计数"""
        count = len(self.note_input.toPlainText())
        self.char_count_label.setText(f"{count}/500")
        
        if count > 450:
            self.char_count_label.setStyleSheet("font-size: 11px; color: #f38ba8;")
        elif count > 400:
            self.char_count_label.setStyleSheet("font-size: 11px; color: #f9e2af;")
        else:
            self.char_count_label.setStyleSheet("font-size: 11px; color: #6c7086;")
    
    def get_note(self) -> str:
        """获取用户输入的备注"""
        return self.note_input.toPlainText().strip()


# ============================================================
# Stream 重定向器（模块级，用于捕获子进程 stdout/stderr）
# ============================================================
import io as _io

class _StreamRedirector(_io.TextIOBase):
    """将 tqdm 的 \\r 更新转为日志行发送到 GUI"""
    def __init__(self, callback):
        self._callback = callback
        self._buf = ""

    def write(self, s):
        if not s:
            return 0
        self._buf += s
        while "\r" in self._buf:
            before, self._buf = self._buf.split("\r", 1)
            if before.strip():
                self._callback(before.rstrip())
        while "\n" in self._buf:
            before, self._buf = self._buf.split("\n", 1)
            if before.strip():
                self._callback(before.rstrip())
        return len(s)

    def flush(self):
        if self._buf.strip():
            self._callback(self._buf.rstrip())
            self._buf = ""


# ============================================================
# Worker 线程（QThread，用于一次性任务）
# ============================================================
class Worker(QThread):
    """通用后台工作线程"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished_signal.emit(result)
        except Exception as e:
            _write_crash(f"Worker.run() error:\n{traceback.format_exc()}")
            self.error_signal.emit(str(e))


# ============================================================
# 生成线程（QThread，用于逐张生成+审查流程）
# ============================================================
class GenerationWorker(QThread):
    """场景图生成工作线程 - 逐张生成，通过信号与 GUI 交互"""
    # 信号定义
    log_signal = pyqtSignal(str)              # 日志
    progress_signal = pyqtSignal(int, int)    # (current, total)
    show_scene_signal = pyqtSignal(int)       # 切换到指定场景
    display_image_signal = pyqtSignal(str)    # 显示图片路径
    update_list_item_signal = pyqtSignal(int, str, str)  # (index, text, color)
    review_ready_signal = pyqtSignal(int)     # 图片已生成，等待审查 (scene_index)
    generation_done_signal = pyqtSignal(int, int)  # (done_count, total)
    error_on_scene_signal = pyqtSignal(int, str)  # (scene_index, error_msg)

    def __init__(self, scenes, workspace, model_name):
        super().__init__()
        self.scenes = scenes
        self.workspace = workspace
        self.model_name = model_name
        
        # 线程同步原语：替代忙等待
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._user_action = None  # None / "confirm" / "regenerate" / "skip"

    def set_user_action(self, action: str):
        """由 GUI 调用，设置用户操作并唤醒线程"""
        self._mutex.lock()
        try:
            self._user_action = action
            self._wait_condition.wakeAll()
        finally:
            self._mutex.unlock()

    def run(self):
        from image_gen import image_generate

        try:
            total = len(self.scenes)
            done = 0
            i = 0

            while i < total:
                scene = self.scenes[i]
                status = scene.get("status", "pending")

                # 跳过已完成的
                if status in ("generated", "skipped"):
                    if status == "generated":
                        done += 1
                    i += 1
                    continue

                scene_id = scene.get("scene_id", i + 1)
                self.progress_signal.emit(i, total)

                # 切换 GUI 到当前场景
                self.show_scene_signal.emit(i)
                self.log_signal.emit(f"[*] 生成场景 {scene_id}/{total}...")

                scene_dir = os.path.join(self.workspace, "scene")
                os.makedirs(scene_dir, exist_ok=True)
                img_path = os.path.join(scene_dir, f"scene_{scene_id:03d}.png")

                try:
                    result = image_generate(
                        prompt=scene["visual_prompt"],
                        save_dir=scene_dir,
                        model_name=self.model_name,
                        filename=f"scene_{scene_id:03d}.png",
                    )

                    img_path = result["filepath"]
                    scene["status"] = "generated"
                    scene["filepath"] = img_path
                    done += 1

                    self.log_signal.emit(f"[OK] 场景 {scene_id} 生成成功")

                    # 显示图片
                    self.display_image_signal.emit(img_path)
                    self.update_list_item_signal.emit(
                        i,
                        f"[OK] #{scene_id:2d} | {scene['visual_prompt'][:40]}...",
                        "#a6e3a1"
                    )

                    # 保存
                    self._save_plan()

                    # 等待用户审查（事件驱动，非忙等待）
                    self.review_ready_signal.emit(i)
                    action = self._wait_for_user_action()

                    if action == "regenerate":
                        # 标记为 pending，重新生成
                        scene["status"] = "pending"
                        if "filepath" in scene:
                            del scene["filepath"]
                        self._save_plan()
                        self.log_signal.emit(f"[>>] 场景 {scene_id} 重新生成")
                        self.update_list_item_signal.emit(
                            i,
                            f"[ ] #{scene_id:2d} | {scene['visual_prompt'][:40]}...",
                            "#cdd6f4"
                        )
                        continue  # 不 i++，重新循环
                    elif action == "skip":
                        scene["status"] = "skipped"
                        done -= 1  # 之前 +1 了，跳过不算
                        self._save_plan()
                        self.log_signal.emit(f"[>>] 场景 {scene_id} 已跳过")
                        self.update_list_item_signal.emit(
                            i,
                            f"[>>] #{scene_id:2d} | {scene['visual_prompt'][:40]}...",
                            "#f9e2af"
                        )
                    else:
                        # confirm - 保持 generated 状态
                        self.log_signal.emit(f"[OK] 场景 {scene_id} 已确认")

                    i += 1

                except Exception as e:
                    scene["status"] = "failed"
                    scene["error"] = str(e)
                    self._save_plan()
                    self.log_signal.emit(f"[X] 场景 {scene_id} 生成失败: {e}")
                    self.error_on_scene_signal.emit(i, str(e))
                    self.update_list_item_signal.emit(
                        i,
                        f"[X] #{scene_id:2d} | {scene['visual_prompt'][:40]}...",
                        "#f38ba8"
                    )
                    i += 1  # 跳过失败的继续

            self.generation_done_signal.emit(done, total)

        except Exception as e:
            _write_crash(f"GenerationWorker.run() error:\n{traceback.format_exc()}")
            self.error_on_scene_signal.emit(-1, str(e))

    def _wait_for_user_action(self) -> str:
        """阻塞等待用户操作（使用 QWaitCondition，不占用 CPU）"""
        self._mutex.lock()
        try:
            # 等待直到 _user_action 被设置（由 set_user_action 唤醒）
            while self._user_action is None:
                self._wait_condition.wait(self._mutex)
            
            action = self._user_action
            self._user_action = None
            return action
        finally:
            self._mutex.unlock()

    def _save_plan(self):
        """保存 scene_plan（通过信号让主线程做，但这里直接写文件也行，因为不涉及 UI）"""
        plan_path = os.path.join(self.workspace, "scene_plan.json")
        try:
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump({"scenes": self.scenes}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ============================================================
# 主窗口
# ============================================================
class VideoPipelineGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频制作流水线 - Release 1")
        self.setGeometry(80, 80, 1280, 820)

        # 状态
        self.workspace = None
        self.scene_plan = None
        self.scenes = []
        self.current_scene_idx = -1
        self.gen_worker = None  # GenerationWorker
        self._worker = None  # 通用 Worker（防止 GC 回收）
        
        # 审查按钮的槽函数（避免 lambda 导致的信号连接问题）
        self._confirm_slot = lambda: None
        self._regen_slot = lambda: None
        self._skip_slot = lambda: None

        # debounce：编辑字段时延迟 500ms 再写盘，避免每个按键都触发 I/O
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._save_plan)

        self._build_ui()

    # ============================================================
    # UI 构建
    # ============================================================
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- 标题 ---
        title = QLabel("视频制作流水线")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # --- 顶部控制栏 ---
        top_bar = QHBoxLayout()

        # 选工作区
        top_bar.addWidget(QLabel("工作区:"))
        self.workspace_label = QLabel("未选择")
        self.workspace_label.setStyleSheet("color: #f9e2af; font-weight: bold;")
        self.workspace_label.setMinimumWidth(200)
        top_bar.addWidget(self.workspace_label)
        self.btn_select_ws = QPushButton("选择文件夹")
        self.btn_select_ws.clicked.connect(self.select_workspace)
        top_bar.addWidget(self.btn_select_ws)

        top_bar.addSpacing(20)

        # LLM 模型选择（场景划分用）
        top_bar.addWidget(QLabel("语言模型:"))
        self.llm_combo = QComboBox()
        self.llm_combo.addItems(LLM_PROVIDERS.keys())
        idx = list(LLM_PROVIDERS.keys()).index(DEFAULT_LLM)
        self.llm_combo.setCurrentIndex(idx)
        top_bar.addWidget(self.llm_combo)

        top_bar.addSpacing(20)

        # 文生图模型选择
        top_bar.addWidget(QLabel("文生图模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(IMAGE_MODELS.keys())
        idx = list(IMAGE_MODELS.keys()).index(DEFAULT_IMAGE_MODEL)
        self.model_combo.setCurrentIndex(idx)
        top_bar.addWidget(self.model_combo)

        top_bar.addSpacing(20)

        # 字幕开关
        self.subtitle_cb = QCheckBox("添加字幕")
        self.subtitle_cb.setChecked(True)
        top_bar.addWidget(self.subtitle_cb)

        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # --- 步骤按钮栏 ---
        steps_bar = QHBoxLayout()
        steps_bar.setSpacing(12)

        self.btn_plan = QPushButton("1. 划分场景")
        self.btn_plan.clicked.connect(self.run_scene_plan)
        self.btn_plan.setEnabled(False)
        steps_bar.addWidget(self.btn_plan)

        self.btn_generate = QPushButton("2. 生成场景图")
        self.btn_generate.clicked.connect(self.start_generation)
        self.btn_generate.setEnabled(False)
        steps_bar.addWidget(self.btn_generate)

        self.btn_asr = QPushButton("3. ASR 对齐")
        self.btn_asr.clicked.connect(self.run_asr)
        self.btn_asr.setEnabled(False)
        steps_bar.addWidget(self.btn_asr)

        self.btn_video = QPushButton("4. 合成视频")
        self.btn_video.clicked.connect(self.make_video)
        self.btn_video.setEnabled(False)
        steps_bar.addWidget(self.btn_video)

        steps_bar.addStretch()

        # 进度条
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setMaximumWidth(250)
        steps_bar.addWidget(self.progress)

        main_layout.addLayout(steps_bar)

        # --- 主体分割（左：列表+日志 / 右：预览） ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ---- 左侧面板 ----
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # 场景列表
        scene_group = QGroupBox("场景列表")
        sg_layout = QVBoxLayout(scene_group)

        # 增删按钮
        scene_btn_bar = QHBoxLayout()
        self.btn_add_scene = QPushButton("+ 添加场景")
        self.btn_add_scene.setObjectName("btnSmall")
        self.btn_add_scene.clicked.connect(self.add_scene)
        self.btn_add_scene.setEnabled(False)
        scene_btn_bar.addWidget(self.btn_add_scene)

        self.btn_del_scene = QPushButton("- 删除场景")
        self.btn_del_scene.setObjectName("btnSmall")
        self.btn_del_scene.clicked.connect(self.delete_scene)
        self.btn_del_scene.setEnabled(False)
        scene_btn_bar.addWidget(self.btn_del_scene)

        scene_btn_bar.addStretch()
        sg_layout.addLayout(scene_btn_bar)

        self.scene_list = QListWidget()
        self.scene_list.currentRowChanged.connect(self.on_scene_list_clicked)
        sg_layout.addWidget(self.scene_list)
        self.scene_count_label = QLabel("共 0 个场景")
        self.scene_count_label.setObjectName("sectionLabel")
        sg_layout.addWidget(self.scene_count_label)
        left_layout.addWidget(scene_group)

        # 日志
        log_group = QGroupBox("日志")
        lg_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        lg_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group)

        splitter.addWidget(left_panel)

        # ---- 右侧面板（预览 + 审查） ----
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        # 场景信息
        self.scene_info_label = QLabel("场景: - / -")
        self.scene_info_label.setObjectName("sceneInfo")
        right_layout.addWidget(self.scene_info_label)

        # 图片预览
        self.image_label = QLabel("请先选择工作区并划分场景")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 400)
        self.image_label.setStyleSheet("""
            background-color: #181825;
            border: 2px solid #45475a;
            border-radius: 8px;
            font-size: 14px;
            color: #6c7086;
        """)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.image_label, stretch=1)

        # Prompt 显示（可编辑）
        prompt_group = QGroupBox("Visual Prompt")
        pg_layout = QVBoxLayout(prompt_group)
        self.prompt_text = QTextEdit()
        self.prompt_text.setMaximumHeight(80)
        self.prompt_text.textChanged.connect(self.on_prompt_changed)
        pg_layout.addWidget(self.prompt_text)
        right_layout.addWidget(prompt_group)

        # 原文片段（可编辑）
        text_group = QGroupBox("原文片段 (Text)")
        tg_layout = QVBoxLayout(text_group)
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(60)
        self.text_edit.textChanged.connect(self.on_scene_field_changed)
        tg_layout.addWidget(self.text_edit)
        right_layout.addWidget(text_group)

        # 场景描述（可编辑）
        bg_group = QGroupBox("场景描述 (Background)")
        bg_layout = QVBoxLayout(bg_group)
        self.bg_edit = QTextEdit()
        self.bg_edit.setMaximumHeight(60)
        self.bg_edit.textChanged.connect(self.on_scene_field_changed)
        bg_layout.addWidget(self.bg_edit)
        right_layout.addWidget(bg_group)

        # 审查控制按钮
        review_bar = QHBoxLayout()
        review_bar.addStretch()

        self.btn_confirm = QPushButton("确认")
        self.btn_confirm.setObjectName("btnConfirm")
        self.btn_confirm.setEnabled(False)
        review_bar.addWidget(self.btn_confirm)

        self.btn_regen = QPushButton("重新生成")
        self.btn_regen.setObjectName("btnRegenerate")
        self.btn_regen.setEnabled(False)
        review_bar.addWidget(self.btn_regen)

        self.btn_skip = QPushButton("跳过")
        self.btn_skip.setObjectName("btnSkip")
        self.btn_skip.setEnabled(False)
        review_bar.addWidget(self.btn_skip)

        review_bar.addStretch()
        right_layout.addLayout(review_bar)

        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([300, 900])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)

        # 初始日志
        self.log("视频制作流水线 v1.0 已启动")
        self.log("请先选择一个工作区文件夹（包含 article.txt）")

    # ============================================================
    # 工具方法
    # ============================================================
    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")
        # 自动滚动到底部
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_buttons_enabled(self, **kwargs):
        """批量设置按钮启用状态"""
        if 'plan' in kwargs:
            self.btn_plan.setEnabled(kwargs['plan'])
        if 'generate' in kwargs:
            self.btn_generate.setEnabled(kwargs['generate'])
        if 'asr' in kwargs:
            self.btn_asr.setEnabled(kwargs['asr'])
        if 'video' in kwargs:
            self.btn_video.setEnabled(kwargs['video'])

    def set_review_buttons(self, enabled: bool):
        self.btn_confirm.setEnabled(enabled)
        self.btn_regen.setEnabled(enabled)
        self.btn_skip.setEnabled(enabled)

    def display_image(self, image_path: str):
        """在预览区域显示图片"""
        if not os.path.exists(image_path):
            self.image_label.setText("图片不存在")
            return
        pixmap = QPixmap(image_path)
        # 缩放以适应区域，保持比例
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def resizeEvent(self, event):
        """窗口大小变化时重新缩放图片"""
        super().resizeEvent(event)
        if hasattr(self, '_current_img_path') and self._current_img_path:
            self.display_image(self._current_img_path)
        self._current_img_path = getattr(self, '_current_img_path', None)

    def closeEvent(self, event):
        """关闭窗口时等待后台线程结束"""
        if self.gen_worker is not None and self.gen_worker.isRunning():
            self.gen_worker.set_user_action("skip")  # 唤醒线程使其退出
            self.gen_worker.quit()
            self.gen_worker.wait(3000)
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        event.accept()

    def update_scene_list(self):
        """刷新场景列表"""
        self.scene_list.clear()
        for i, scene in enumerate(self.scenes):
            status = scene.get("status", "pending")
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("visual_prompt", "")[:40]

            # 状态图标
            icon_map = {
                "pending": "[ ]",
                "generated": "[OK]",
                "failed": "[X]",
                "skipped": "[>>]",
            }
            icon = icon_map.get(status, "[ ]")

            # 时间信息
            time_str = ""
            if "start_time" in scene and "end_time" in scene:
                dur = scene["end_time"] - scene["start_time"]
                time_str = f" | {dur:.1f}s"

            text = f"{icon} #{int(scene_id):2d}{time_str} | {prompt}..."
            item = QListWidgetItem(text)
            self.scene_list.addItem(item)

            # 颜色标记
            if status == "generated":
                item.setForeground(QColor("#a6e3a1"))
            elif status == "failed":
                item.setForeground(QColor("#f38ba8"))
            elif status == "skipped":
                item.setForeground(QColor("#f9e2af"))

        self.scene_count_label.setText(f"共 {len(self.scenes)} 个场景")

    def show_scene(self, idx: int):
        """显示指定场景的图片和信息"""
        if idx < 0 or idx >= len(self.scenes):
            return

        self.current_scene_idx = idx
        scene = self.scenes[idx]
        scene_id = scene.get("scene_id", idx + 1)
        status = scene.get("status", "pending")

        self.scene_info_label.setText(
            f"场景: {scene_id} / {len(self.scenes)} | 状态: {status}"
            + (f" | {scene['end_time'] - scene['start_time']:.1f}s"
               if "start_time" in scene and "end_time" in scene else "")
        )
        self.prompt_text.setPlainText(scene.get("visual_prompt", ""))
        self.text_edit.setPlainText(scene.get("text", ""))
        self.bg_edit.setPlainText(scene.get("background", ""))

        # 尝试显示图片：优先读 filepath（生成时写入的精确路径），fallback 到规则构造
        img_path = scene.get("filepath")
        if not img_path or not os.path.exists(img_path):
            scene_dir = os.path.join(self.workspace, "scene")
            img_path = os.path.join(scene_dir, f"scene_{scene_id:03d}.png")
        if img_path and os.path.exists(img_path):
            self._current_img_path = img_path
            self.display_image(img_path)
        else:
            self._current_img_path = None
            self.image_label.setText(f"场景 {scene_id} 图片未生成")

        # 高亮列表
        self.scene_list.setCurrentRow(idx)

    # ============================================================
    # 工作区选择
    # ============================================================
    def select_workspace(self):
        path = QFileDialog.getExistingDirectory(self, "选择工作区目录（包含 article.txt）")
        if not path:
            return

        self.workspace = path
        self.workspace_label.setText(path)
        self.log(f"工作区: {path}")

        # 禁用按钮，防止用户在加载期间操作
        self.btn_select_ws.setEnabled(False)
        self.btn_plan.setEnabled(False)

        # 异步加载工作区文件，避免主线程 I/O 阻塞
        def load_workspace():
            result = {"path": path, "has_article": False, "has_audio": False, "scene_plan": None}
            article_path = os.path.join(path, "article.txt")
            if os.path.exists(article_path):
                with open(article_path, 'r', encoding='utf-8') as f:
                    article = f.read().strip()
                result["has_article"] = True
                result["article_len"] = len(article)
            audio_path = os.path.join(path, "voice.mp3")
            result["has_audio"] = os.path.exists(audio_path)
            plan_path = os.path.join(path, "scene_plan.json")
            if os.path.exists(plan_path):
                with open(plan_path, 'r', encoding='utf-8') as f:
                    result["scene_plan"] = json.load(f)
            return result

        self._worker = Worker(load_workspace)
        self._worker.finished_signal.connect(self._on_workspace_loaded)
        self._worker.error_signal.connect(self._on_workspace_load_error)
        self._worker.start()

    def _on_workspace_loaded(self, result):
        """异步加载工作区完成"""
        path = result["path"]
        self.btn_select_ws.setEnabled(True)

        if not result["has_article"]:
            QMessageBox.warning(self, "文件缺失", f"未找到 article.txt")
            return

        self.log(f"找到 article.txt（{result['article_len']} 字符）")
        self.btn_plan.setEnabled(True)

        if result["has_audio"]:
            self.log("找到 voice.mp3")
        else:
            self.log("未找到 voice.mp3，ASR 和视频合成将不可用")

        scene_plan = result.get("scene_plan")
        if scene_plan:
            self.scene_plan = scene_plan
            self.scenes = self.scene_plan.get("scenes", [])
            self.update_scene_list()
            self.log(f"找到已有场景计划（{len(self.scenes)} 个场景）")
            self.btn_generate.setEnabled(True)
            self.btn_add_scene.setEnabled(True)
            self.btn_del_scene.setEnabled(True)
            if result["has_audio"]:
                self.btn_asr.setEnabled(True)
            self.btn_video.setEnabled(True)
            if self.scenes:
                self.show_scene(0)

    def _on_workspace_load_error(self, error_msg):
        self.btn_select_ws.setEnabled(True)
        self.log(f"[X] 工作区加载失败: {error_msg}")

    # ============================================================
    # 场景列表点击
    # ============================================================
    def on_scene_list_clicked(self, row: int):
        if 0 <= row < len(self.scenes):
            self.show_scene(row)

    # ============================================================
    # 步骤 1：划分场景
    # ============================================================
    def run_scene_plan(self):
        if not self.workspace:
            QMessageBox.warning(self, "错误", "请先选择工作区")
            return

        # 防止重复触发
        if self._worker is not None and self._worker.isRunning():
            self.log("[!] 上一个任务仍在运行，请稍候...")
            return

        # 弹出备注对话框
        dialog = NoteDialog(
            parent=self,
            title="划分场景 - 添加备注",
            message="即将开始分析 article.txt 并划分场景"
        )
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            # 用户取消了
            return
        
        user_note = dialog.get_note()
        
        self.btn_plan.setEnabled(False)
        self.log("=" * 40)
        self.log("开始划分场景...")
        if user_note:
            self.log(f"[备注] {user_note}")

        # 捕获当前 provider 和 workspace，避免闭包延迟求值
        provider = self.llm_combo.currentText()
        workspace = self.workspace

        def task():
            import scene_plan as _sp
            return _sp.main(workspace=workspace, provider=provider, user_note=user_note)

        self._worker = Worker(task)
        self._worker.log_signal.connect(self.log)
        self._worker.finished_signal.connect(self.on_plan_done)
        self._worker.error_signal.connect(self.on_plan_error)
        self._worker.start()

    def on_plan_done(self, result):
        # 读取 scene_plan.json
        plan_path = os.path.join(self.workspace, "scene_plan.json")
        if os.path.exists(plan_path):
            with open(plan_path, 'r', encoding='utf-8') as f:
                self.scene_plan = json.load(f)
            self.scenes = self.scene_plan.get("scenes", [])
            self.update_scene_list()
            self.log(f"场景划分完成，共 {len(self.scenes)} 个场景")

            self.btn_generate.setEnabled(True)
            self.btn_add_scene.setEnabled(True)
            self.btn_del_scene.setEnabled(True)
            # 检查音频
            if os.path.exists(os.path.join(self.workspace, "voice.mp3")):
                self.btn_asr.setEnabled(True)
            self.btn_video.setEnabled(True)

            if self.scenes:
                self.show_scene(0)
        self.btn_plan.setEnabled(True)

    def on_plan_error(self, error_msg):
        self.log(f"[X] 场景划分失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"场景划分失败:\n{error_msg}")
        self.btn_plan.setEnabled(True)

    # ============================================================
    # 步骤 2：生成场景图（逐张审查，QThread + 信号）
    # ============================================================
    def start_generation(self):
        if not self.scenes:
            QMessageBox.error(self, "错误", "请先划分场景")
            return

        # 检查是否有待生成的场景
        has_pending = any(s.get("status") in ("pending", "failed") for s in self.scenes)
        if not has_pending:
            QMessageBox.information(self, "完成", "所有场景已生成或跳过！")
            return

        self.btn_generate.setEnabled(False)
        self.btn_plan.setEnabled(False)
        self.set_review_buttons(False)
        self.log("=" * 40)
        self.log("开始生成场景图（逐张审查模式）...")

        model_name = self.model_combo.currentText()

        # 创建并启动 GenerationWorker
        self.gen_worker = GenerationWorker(self.scenes, self.workspace, model_name)

        # 连接信号 → 全部在主线程执行
        self.gen_worker.log_signal.connect(self.log)
        self.gen_worker.progress_signal.connect(
            lambda cur, total: self.progress.setValue(int((cur / total) * 100) if total > 0 else 0)
        )
        self.gen_worker.show_scene_signal.connect(self.show_scene)
        self.gen_worker.display_image_signal.connect(self._on_display_image)
        self.gen_worker.update_list_item_signal.connect(self._on_update_list_item)
        self.gen_worker.review_ready_signal.connect(self._on_review_ready)
        self.gen_worker.generation_done_signal.connect(self._on_generation_done)
        self.gen_worker.error_on_scene_signal.connect(self._on_scene_error)

        # 设置审查按钮的槽函数（使用实例变量避免信号连接泄漏）
        worker_ref = self.gen_worker
        self._confirm_slot = lambda: worker_ref.set_user_action("confirm")
        self._regen_slot = lambda: worker_ref.set_user_action("regenerate")
        self._skip_slot = lambda: worker_ref.set_user_action("skip")
        
        self.btn_confirm.clicked.connect(self._confirm_slot)
        self.btn_regen.clicked.connect(self._regen_slot)
        self.btn_skip.clicked.connect(self._skip_slot)

        self.gen_worker.start()

    def _on_display_image(self, img_path: str):
        """主线程：显示图片"""
        self._current_img_path = img_path
        self.display_image(img_path)

    def _on_update_list_item(self, index: int, text: str, color: str):
        """主线程：更新列表项"""
        item = self.scene_list.item(index)
        if item:
            item.setText(text)
            item.setForeground(QColor(color))

    def _on_review_ready(self, scene_idx: int):
        """主线程：图片已生成，启用审查按钮"""
        self.set_review_buttons(True)

    def _on_scene_error(self, scene_idx: int, error_msg: str):
        """主线程：某场景生成失败"""
        # 失败的不需要审查，继续下一个
        pass

    def _on_generation_done(self, done_count: int, total: int):
        """主线程：生成全部完成"""
        self.progress.setValue(100)
        self.set_review_buttons(False)
        self.btn_generate.setEnabled(True)
        self.btn_plan.setEnabled(True)

        # 刷新场景列表
        self.update_scene_list()

        # 同步 scenes 回 scene_plan
        if self.scene_plan:
            self.scene_plan["scenes"] = self.scenes

        self.log(f"[*] 生成流程结束，已完成 {done_count}/{total}")
        QMessageBox.information(self, "完成", f"场景图生成完成\n已生成: {done_count}/{total}")

        # 断开生成模式的槽函数，恢复默认行为
        self.btn_confirm.clicked.disconnect(self._confirm_slot)
        self.btn_regen.clicked.disconnect(self._regen_slot)
        self.btn_skip.clicked.disconnect(self._skip_slot)
        
        # 重置槽函数引用
        self._confirm_slot = lambda: None
        self._regen_slot = lambda: None
        self._skip_slot = lambda: None
        
        self.gen_worker = None

    def _renumber_scene_ids(self):
        """重新编号所有场景的 scene_id"""
        for i, scene in enumerate(self.scenes):
            scene["scene_id"] = i + 1

    def on_prompt_changed(self):
        """visual_prompt 编辑后延迟写盘（debounce 500ms）"""
        if self.current_scene_idx < 0 or self.current_scene_idx >= len(self.scenes):
            return
        self.scenes[self.current_scene_idx]["visual_prompt"] = self.prompt_text.toPlainText()
        # 刷新列表中对应的条目
        self._refresh_list_item(self.current_scene_idx)
        self._save_timer.start()  # 重置并重新计时

    def on_scene_field_changed(self):
        """text / background 编辑后延迟写盘（debounce 500ms）"""
        if self.current_scene_idx < 0 or self.current_scene_idx >= len(self.scenes):
            return
        self.scenes[self.current_scene_idx]["text"] = self.text_edit.toPlainText()
        self.scenes[self.current_scene_idx]["background"] = self.bg_edit.toPlainText()
        self._save_timer.start()  # 重置并重新计时

    def add_scene(self):
        """在当前选中场景后面插入一个新场景"""
        if not self.scenes:
            idx = 0
        else:
            idx = self.current_scene_idx + 1 if self.current_scene_idx >= 0 else len(self.scenes)

        new_scene = {
            "scene_id": 0,  # 临时值，稍后 renumber
            "text": "",
            "background": "",
            "visual_prompt": "",
            "status": "pending"
        }
        self.scenes.insert(idx, new_scene)
        self._renumber_scene_ids()
        self.scene_plan["scenes"] = self.scenes
        self._save_plan()
        self.update_scene_list()
        self.show_scene(idx)
        self.log(f"[+] 已在位置 {idx + 1} 添加新场景")

    def delete_scene(self):
        """删除当前选中的场景"""
        if self.current_scene_idx < 0 or self.current_scene_idx >= len(self.scenes):
            return
        idx = self.current_scene_idx
        del self.scenes[idx]
        self._renumber_scene_ids()
        self.scene_plan["scenes"] = self.scenes
        self._save_plan()
        self.update_scene_list()
        # 显示相邻场景
        show_idx = min(idx, len(self.scenes) - 1)
        if show_idx >= 0:
            self.show_scene(show_idx)
        self.log(f"[-] 已删除场景（剩余 {len(self.scenes)} 个）")

    def _refresh_list_item(self, idx: int):
        """刷新场景列表中指定条目的文字"""
        if idx < 0 or idx >= len(self.scenes):
            return
        scene = self.scenes[idx]
        status = scene.get("status", "pending")
        scene_id = scene.get("scene_id", idx + 1)
        prompt = scene.get("visual_prompt", "")[:40]
        icon_map = {
            "pending": "[ ]",
            "generated": "[OK]",
            "failed": "[X]",
            "skipped": "[>>]",
        }
        icon = icon_map.get(status, "[ ]")
        time_str = ""
        if "start_time" in scene and "end_time" in scene:
            dur = scene["end_time"] - scene["start_time"]
            time_str = f" | {dur:.1f}s"
        text = f"{icon} #{int(scene_id):2d}{time_str} | {prompt}..."
        item = self.scene_list.item(idx)
        if item:
            item.setText(text)

    def _save_plan(self):
        """保存 scene_plan.json"""
        if self.scene_plan and self.workspace:
            plan_path = os.path.join(self.workspace, "scene_plan.json")
            with open(plan_path, 'w', encoding='utf-8') as f:
                json.dump(self.scene_plan, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 步骤 3：ASR 对齐
    # ============================================================
    def run_asr(self):
        if not self.workspace:
            return

        if self._worker is not None and self._worker.isRunning():
            self.log("[!] 上一个任务仍在运行，请稍候...")
            return

        audio_path = os.path.join(self.workspace, "voice.mp3")
        if not os.path.exists(audio_path):
            QMessageBox.warning(self, "文件缺失", "未找到 voice.mp3")
            return

        self.btn_asr.setEnabled(False)
        self.log("=" * 40)
        self.log("开始 ASR 对齐（模型加载可能需要较长时间）...")

        def task():
            import asr
            asr.run_asr(self.workspace)
            return asr.match_scenes_to_audio(self.workspace)

        self._worker = Worker(task)
        self._worker.log_signal.connect(self.log)
        self._worker.finished_signal.connect(self.on_asr_done)
        self._worker.error_signal.connect(self.on_asr_error)
        self._worker.start()

    def on_asr_done(self, result):
        # 刷新 scene_plan（已包含时间信息）
        plan_path = os.path.join(self.workspace, "scene_plan.json")
        if os.path.exists(plan_path):
            with open(plan_path, 'r', encoding='utf-8') as f:
                self.scene_plan = json.load(f)
            self.scenes = self.scene_plan.get("scenes", [])
            self.update_scene_list()

        scene_count = len(self.scenes)
        matched = sum(1 for s in self.scenes if "start_time" in s)
        self.log(f"[OK] ASR + 场景匹配完成，{matched}/{scene_count} 个场景已分配时间")
        QMessageBox.information(self, "完成",
            f"ASR 对齐完成，场景匹配成功\n{matched}/{scene_count} 个场景已分配时间")
        self.btn_asr.setEnabled(True)

    def on_asr_error(self, error_msg):
        self.log(f"[X] ASR 失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"ASR 对齐失败:\n{error_msg}")
        self.btn_asr.setEnabled(True)

    # ============================================================
    # 步骤 4：合成视频
    # ============================================================
    def make_video(self):
        if not self.workspace:
            return

        if self._worker is not None and self._worker.isRunning():
            self.log("[!] 上一个任务仍在运行，请稍候...")
            return

        self.btn_video.setEnabled(False)
        self.log("=" * 40)
        self.log("开始合成视频...")

        self._worker = Worker(self._make_video_task)
        self._worker.log_signal.connect(self.log)
        self._worker.finished_signal.connect(self.on_video_done)
        self._worker.error_signal.connect(self.on_video_error)
        self._worker.start()

    def _make_video_task(self):
        """视频合成任务 - 通过 stdout 重定向捕获 tqdm 进度到日志"""
        import sys
        import io

        worker = self._worker
        redirector = _StreamRedirector(lambda msg: worker.log_signal.emit(msg))

        import make_video
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = redirector
        sys.stderr = redirector

        try:
            video_path = make_video.main(
                workspace=self.workspace,
                fps=DEFAULT_FPS,
                size=DEFAULT_VIDEO_SIZE,
                subtitle=self.subtitle_cb.isChecked(),
            )
            return video_path
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def on_video_done(self, result):
        self.log(f"[OK] 视频合成完成: {result}")
        QMessageBox.information(self, "完成", f"视频已生成:\n{result}")
        self.btn_video.setEnabled(True)

    def on_video_error(self, error_msg):
        self.log(f"[X] 视频合成失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"视频合成失败:\n{error_msg}")
        self.btn_video.setEnabled(True)


# ============================================================
# 入口
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = VideoPipelineGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
