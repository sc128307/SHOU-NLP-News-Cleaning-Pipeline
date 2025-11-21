import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import sys
import os

# ================= 【新增】修复 Windows 高分屏缩放问题 =================
try:
    import ctypes

    # 告诉 Windows："我是高分屏程序，别乱缩放我"
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass  # 非 Windows 系统或调用失败则忽略
# ====================================================================


# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
except ImportError:
    import tkinter.ttk as ttk

from pipeline_backend import CorpusPipeline


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("NLP 智能语料清洗工具 (Team Version)")

        # 1. 设定目标宽高达稍微大一点，视觉更舒适
        window_width = 1000
        window_height = 750

        # 2. 获取屏幕分辨率
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 3. 计算居中坐标
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)

        # 4. 应用设置 (格式: 宽x高+左边距+上边距)
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")

        # (可选) 设置最小尺寸，防止用户把窗口拖得太小导致排版错乱
        self.root.minsize(800, 600)

        # 默认路径设置 (相对路径)
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()

        # 默认模型路径指向当前目录下的文件夹
        default_model = "gysgzyh/news-body-classifier"
        self.model_path = tk.StringVar(value=default_model)

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        lbl_title = ttk.Label(
            main_frame,
            text="NLP Corpus Cleaning Pipeline",
            font=("Helvetica", 16, "bold"),
        )
        lbl_title.pack(pady=(0, 20))

        # 1. 输入目录
        self.create_file_entry(
            main_frame, "1. 输入目录 (RTF Source Folder):", self.input_dir, True
        )

        # 2. 输出目录
        self.create_file_entry(
            main_frame, "2. 输出目录 (Output Folder):", self.output_dir, True
        )

        # 3. 模型目录
        self.create_file_entry(
            main_frame, "3. 模型路径 (AI Model Folder):", self.model_path, True
        )

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress.pack(fill=X, pady=20)

        self.status_lbl = ttk.Label(
            main_frame, text="等待开始...", bootstyle="secondary"
        )
        self.status_lbl.pack()

        # 说明文本
        info_text = "说明: 此工具将读取 RTF，自动提取 Title/Date/Source，并使用 AI 清洗正文。\n结果将生成 TXT 文件、CSV 进度表和 Label Studio 校验文件。"
        lbl_info = ttk.Label(
            main_frame, text=info_text, font=("Arial", 9), bootstyle="info"
        )
        lbl_info.pack(pady=10)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        self.btn_run = ttk.Button(
            btn_frame,
            text="🚀 开始处理 (Start)",
            command=self.start_thread,
            bootstyle="success",
        )
        self.btn_run.pack(side=LEFT, padx=10)

        btn_exit = ttk.Button(
            btn_frame, text="退出 (Exit)", command=self.root.quit, bootstyle="danger"
        )
        btn_exit.pack(side=LEFT, padx=10)

    def create_file_entry(self, parent, label_text, variable, is_dir=True):
        frame = ttk.Frame(parent)
        frame.pack(fill=X, pady=5)
        lbl = ttk.Label(frame, text=label_text, width=30)
        lbl.pack(side=LEFT)
        entry = ttk.Entry(frame, textvariable=variable)
        entry.pack(side=LEFT, fill=X, expand=True, padx=5)

        def browse():
            path = (
                filedialog.askdirectory(initialdir=CURRENT_DIR)
                if is_dir
                else filedialog.askopenfilename(initialdir=CURRENT_DIR)
            )
            if path:
                variable.set(path)

        btn = ttk.Button(frame, text="浏览", command=browse, width=8)
        btn.pack(side=LEFT)

    def update_progress(self, current, total, message):
        # 在主线程更新 GUI
        self.progress_var.set((current / total) * 100)
        self.status_lbl.config(text=f"[{current}/{total}] {message}")
        self.root.update_idletasks()

    def run_process(self):
        in_dir = self.input_dir.get()
        out_dir = self.output_dir.get()
        model = self.model_path.get()

        if not in_dir or not out_dir or not model:
            messagebox.showerror("错误", "请确保所有路径都已选择！")
            self.btn_run.config(state=NORMAL)
            return

        if not os.path.exists(model):
            messagebox.showerror(
                "错误",
                f"找不到模型文件夹:\n{model}\n请确保 body-classifier-model 在此路径下。",
            )
            self.btn_run.config(state=NORMAL)
            return

        try:
            pipeline = CorpusPipeline(model)
            pipeline.process_folder(in_dir, out_dir, self.update_progress)

            messagebox.showinfo(
                "完成",
                f"🎉 处理完成！\n\n结果已保存在: {out_dir}\n\n请查看生成的 TXT 和 progress_log.csv。",
            )
        except Exception as e:
            messagebox.showerror("运行时错误", f"发生错误:\n{str(e)}")
        finally:
            self.btn_run.config(state=NORMAL)
            self.status_lbl.config(text="任务完成")

    def start_thread(self):
        self.btn_run.config(state=DISABLED)
        t = threading.Thread(target=self.run_process)
        t.start()


if __name__ == "__main__":
    root = tk.Tk()
    if "ttkbootstrap" in sys.modules:
        style = ttk.Style(theme="cosmo")
    app = App(root)
    root.mainloop()
