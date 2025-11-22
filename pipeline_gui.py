import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import sys
import os
import time

# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# ================= 修复 Windows 高分屏缩放问题 =================
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
# ============================================================

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    # 修复 ToolTip 导入路径
    from ttkbootstrap.widgets import ToolTip
except ImportError:
    import tkinter.ttk as ttk
    # 定义常量防止报错
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    INFO = "info"
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    X = "x"
    Y = "y"
    class ToolTip:
        def __init__(self, *args, **kwargs): pass

from pipeline_backend import CorpusPipeline

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("NLP 智能语料清洗工具 (Team Version)")
        
        # 1. 设定大尺寸窗口并居中
        window_width = 1100
        window_height = 750
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.minsize(900, 650)

        # 变量初始化
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        
        # 默认模型路径
        default_model = "YourUsername/news-body-classifier" 
        # 优先检查本地是否有离线包
        local_model_path = os.path.join(CURRENT_DIR, "news-body-classifier")
        if os.path.exists(local_model_path):
            default_model = local_model_path
            
        self.model_path = tk.StringVar(value=default_model)
        self.auto_output_var = tk.BooleanVar(value=False)

        self.create_modern_ui()

    def create_modern_ui(self):
        # === 整体布局 ===
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=BOTH, expand=True)

        # --- 左侧边栏 ---
        sidebar = ttk.Frame(main_container, width=250, bootstyle=SECONDARY)
        sidebar.pack(side=LEFT, fill=Y)
        
        # 侧边栏内容
        ttk.Label(sidebar, text="🛠️ 工具箱", font=("Helvetica", 16, "bold"), bootstyle="inverse-secondary").pack(pady=30, padx=20)
        
        self.create_sidebar_btn(sidebar, "📄 使用说明", self.show_help)
        self.create_sidebar_btn(sidebar, "📦 关于软件", self.show_about)
        
        # Separator 不支持 inverse 样式，改为普通 secondary
        ttk.Separator(sidebar, orient=HORIZONTAL, bootstyle="secondary").pack(fill=X, padx=20, pady=20)
        
        ttk.Label(sidebar, text="状态:", font=("Arial", 10), bootstyle="inverse-secondary").pack(anchor="w", padx=20)
        self.status_indicator = ttk.Label(sidebar, text="● 就绪", font=("Arial", 10, "bold"), foreground="#4caf50", bootstyle="inverse-secondary")
        self.status_indicator.pack(anchor="w", padx=20, pady=5)

        # --- 右侧主内容区 ---
        content_frame = ttk.Frame(main_container, padding=40)
        content_frame.pack(side=LEFT, fill=BOTH, expand=True)

        # 标题头
        header_frame = ttk.Frame(content_frame)
        header_frame.pack(fill=X, pady=(0, 30))
        ttk.Label(header_frame, text="NLP 语料清洗管线", font=("Helvetica", 24, "bold"), bootstyle=PRIMARY).pack(side=LEFT)
        
        # 【修复点】去掉了 rely=0.1，改用 anchor 或 pady 来对齐
        # pack 不支持 rely 参数，这导致了之前的崩溃
        ttk.Label(header_frame, text="v2.0", font=("Arial", 12), bootstyle=SECONDARY).pack(side=LEFT, padx=10, anchor='s', pady=(0, 5))

        # === 核心配置卡片 ===
        card_frame = ttk.Labelframe(content_frame, text=" ⚙️ 核心配置 ", padding=25, bootstyle="info")
        card_frame.pack(fill=X, expand=False)

        # 1. 输入目录
        self.create_file_entry(card_frame, "📂 输入目录 (RTF 源文件):", self.input_dir, True, 
                               tooltip="请选择包含 .rtf 文件的文件夹，支持递归扫描子目录。")

        # 2. 输出目录
        out_frame = ttk.Frame(card_frame)
        out_frame.pack(fill=X, pady=15)
        
        out_header = ttk.Frame(out_frame)
        out_header.pack(fill=X)
        ttk.Label(out_header, text="💾 输出目录 (结果保存):", font=("Arial", 10, "bold")).pack(side=LEFT)
        
        self.chk_auto_out = ttk.Checkbutton(
            out_header, 
            text="自动在输入目录下创建 'Output' 文件夹", 
            variable=self.auto_output_var,
            command=self.toggle_output_entry,
            bootstyle="round-toggle"
        )
        self.chk_auto_out.pack(side=LEFT, padx=20)
        
        out_input_frame = ttk.Frame(out_frame)
        out_input_frame.pack(fill=X, pady=5)
        
        self.entry_output = ttk.Entry(out_input_frame, textvariable=self.output_dir, font=("Consolas", 10))
        self.entry_output.pack(side=LEFT, fill=X, expand=True, padx=(0, 10), ipady=5)
        
        self.btn_browse_output = ttk.Button(out_input_frame, text="浏览...", command=lambda: self.browse_path(self.output_dir, True), bootstyle="outline-primary")
        self.btn_browse_output.pack(side=LEFT)

        # 3. 模型路径
        self.create_file_entry(card_frame, "🧠 AI 模型路径 (本地文件夹 / HF ID):", self.model_path, True,
                               tooltip="如果是离线使用，请选择 'news-body-classifier' 文件夹。")

        # === 控制区 ===
        control_frame = ttk.Frame(content_frame, padding=(0, 30))
        control_frame.pack(fill=X)

        self.btn_run = ttk.Button(
            control_frame, 
            text="🚀 开始全自动处理", 
            command=self.start_thread, 
            bootstyle="success-outline", 
            width=25,
            cursor="hand2"
        )
        self.btn_run.pack(side=LEFT)
        
        # 进度条
        progress_frame = ttk.Frame(content_frame)
        progress_frame.pack(fill=X, pady=10)
        
        self.lbl_progress_text = ttk.Label(progress_frame, text="等待任务...", font=("Arial", 9), bootstyle=SECONDARY)
        self.lbl_progress_text.pack(anchor="w", pady=(0, 5))
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, bootstyle="success-striped")
        self.progress.pack(fill=X, ipady=5)

        # 版权
        ttk.Label(content_frame, text="© 2025 NLP Team | Powered by DistilBERT & Regex", font=("Arial", 8), bootstyle=SECONDARY).pack(side=BOTTOM, pady=20)

    def create_sidebar_btn(self, parent, text, command):
        btn = ttk.Button(parent, text=text, command=command, bootstyle="secondary", width=20)
        btn.pack(pady=5, padx=20)

    def create_file_entry(self, parent, label_text, variable, is_dir=True, tooltip=""):
        frame = ttk.Frame(parent)
        frame.pack(fill=X, pady=10)
        
        lbl = ttk.Label(frame, text=label_text, font=("Arial", 10, "bold"))
        lbl.pack(anchor="w")
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=X, pady=5)
        
        entry = ttk.Entry(input_frame, textvariable=variable, font=("Consolas", 10))
        entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10), ipady=5)
        
        if tooltip and 'ttkbootstrap' in sys.modules:
            ToolTip(entry, text=tooltip, bootstyle=(INFO, INVERSE))
        
        btn = ttk.Button(input_frame, text="浏览...", command=lambda: self.browse_path(variable, is_dir), bootstyle="outline-primary")
        btn.pack(side=LEFT)

    def browse_path(self, variable, is_dir):
        path = filedialog.askdirectory(initialdir=CURRENT_DIR) if is_dir else filedialog.askopenfilename(initialdir=CURRENT_DIR)
        if path: 
            variable.set(path)
            if variable == self.input_dir and self.auto_output_var.get():
                self.update_auto_output_path()

    def toggle_output_entry(self):
        if self.auto_output_var.get():
            self.entry_output.config(state="disabled")
            self.btn_browse_output.config(state="disabled")
            self.update_auto_output_path()
        else:
            self.entry_output.config(state="normal")
            self.btn_browse_output.config(state="normal")

    def update_auto_output_path(self):
        in_dir = self.input_dir.get()
        if in_dir:
            auto_path = os.path.join(in_dir, "Output")
            self.output_dir.set(auto_path)

    def run_process(self):
        in_dir = self.input_dir.get()
        model = self.model_path.get()
        
        if self.auto_output_var.get() and in_dir:
            out_dir = os.path.join(in_dir, "Output")
            self.output_dir.set(out_dir)
        else:
            out_dir = self.output_dir.get()

        if not in_dir or not out_dir or not model:
            messagebox.showerror("错误", "请确保所有路径都已填写完整！")
            self.reset_ui_state()
            return
            
        if not os.path.exists(model) and "/" not in model:
             messagebox.showwarning("警告", f"本地找不到模型文件夹:\n{model}\n\n程序将尝试从 Hugging Face 下载 (需要联网)。")

        try:
            self.status_indicator.config(text="● 运行中...", foreground="#ff9800")
            self.progress.start(10)
            
            pipeline = CorpusPipeline(model)
            
            self.progress.stop()
            pipeline.process_folder(in_dir, out_dir, self.update_progress)
            
            self.status_indicator.config(text="● 完成", foreground="#4caf50")
            messagebox.showinfo("任务完成", f"🎉 处理成功！\n\n结果已保存在:\n{out_dir}")
            
            try:
                os.startfile(out_dir)
            except: pass
            
        except Exception as e:
            self.status_indicator.config(text="● 出错", foreground="#f44336")
            self.progress.stop()
            messagebox.showerror("运行时错误", f"发生错误:\n{str(e)}")
        finally:
            self.reset_ui_state()

    def update_progress(self, current, total, message):
        percent = (current / total) * 100
        self.progress_var.set(percent)
        self.lbl_progress_text.config(text=f"[{current}/{total}] {message}")
        self.root.update_idletasks()

    def start_thread(self):
        self.btn_run.config(state=DISABLED, text="⏳ 处理中...")
        t = threading.Thread(target=self.run_process)
        t.start()
        
    def reset_ui_state(self):
        self.btn_run.config(state=NORMAL, text="🚀 开始全自动处理")
        self.progress_var.set(0)
        self.lbl_progress_text.config(text="等待任务...")

    def show_help(self):
        msg = "1. 选择输入目录 (RTF文件夹)\n2. 设置输出目录\n3. 点击开始处理"
        messagebox.showinfo("帮助", msg)

    def show_about(self):
        messagebox.showinfo("关于", "NLP Cleaning Tool v2.0")

if __name__ == "__main__":
    root = tk.Tk()
    if 'ttkbootstrap' in sys.modules:
        style = ttk.Style(theme="cosmo")
    app = App(root)
    root.mainloop()