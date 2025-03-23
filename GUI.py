# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
import core
from io import BytesIO
import os
from PIL import Image, ImageTk
import threading
import time
import sys

# 为了支持拖放功能，添加TkinterDnD库
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    # 如果未安装tkinterdnd2，则显示提示并禁用拖放功能
    DND_FILES = None
    TkinterDnD = tk.Tk
    print("请安装tkinterdnd2以启用拖放功能: pip install tkinterdnd2")

class PicMergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PicMerge")
        self.root.geometry("800x600")
        
        # 设置最小窗口尺寸，确保所有元素都能显示
        self.root.minsize(700, 500)
        
        # 应用Sun Valley主题（亮色）
        sv_ttk.set_theme("light")
        
        # 全局变量
        self.direction = "竖直排列"
        self.picNumOfDirection = 1
        self.TargetResolution = [2560, 1440]
        self.TargetResolutionNum = self.TargetResolution[1]
        self.outputPath = os.path.join(os.path.expanduser("~"), "output")
        self.needTrim = False
        self.quality = 92
        self.uploaded_files = []
        self.needSort = True
        self.enableAdvanced = False
        
        # 创建全局滚动条变量
        self.tab1_scrollbar = None
        
        # 配置Grid布局
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)  # 底部栏固定高度
        
        # 创建主内容区域框架
        main_frame = ttk.Frame(root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # 创建标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        
        # 创建两个标签页
        self.tab1 = ttk.Frame(self.notebook)
        self.tab3 = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab1, text="基本")
        self.notebook.add(self.tab3, text="高级")
        
        # 初始化各个标签页
        self.init_tab1()
        self.init_tab3()
        
        # 底部的生成按钮和进度条框架
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        self.bottom_frame.grid_columnconfigure(1, weight=1)  # 进度条可伸缩
        
        self.status_label = ttk.Label(self.bottom_frame, text="")
        self.status_label.grid(row=0, column=0, padx=5)
        
        self.progress = ttk.Progressbar(self.bottom_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.generate_btn = ttk.Button(self.bottom_frame, text="生成", command=self.generate)
        self.generate_btn.grid(row=0, column=2, padx=5)
        
        # 监听窗口大小变化，更新滚动条状态
        self.root.bind("<Configure>", self.on_window_resize)
        
    def init_tab1(self):
        # 基本标签页内容
        self.tab1.grid_columnconfigure(0, weight=1)
        self.tab1.grid_rowconfigure(0, weight=1)
        
        # 创建全局滚动区域
        self.tab1_canvas = tk.Canvas(self.tab1, highlightthickness=0, bd=0)  # 移除边框
        self.tab1_canvas.grid(row=0, column=0, sticky="nsew")
        
        # 初始时创建全局滚动条，但不一定显示
        self.tab1_scrollbar = ttk.Scrollbar(self.tab1, orient="vertical", command=self.tab1_canvas.yview)
        
        self.tab1_canvas.configure(yscrollcommand=self.tab1_scrollbar.set)
        
        # 创建内容框架并确保没有额外边距
        tab1_inner_frame = ttk.Frame(self.tab1_canvas)
        self.tab1_canvas.create_window((0, 0), window=tab1_inner_frame, anchor="nw")
        
        # 确保画布宽度调整时内容框架也随之调整
        def _configure_tab1_inner_frame(event):
            # 更新内容框架宽度
            canvas_width = event.width
            self.tab1_canvas.itemconfig(self.tab1_canvas.find_withtag("all")[0], width=canvas_width)
            
            # 更新滚动区域（轻微延迟确保内容已更新）
            self.root.after(10, self.check_tab1_scrollbar)
        
        # 只保留一个Configure事件绑定
        self.tab1_canvas.bind('<Configure>', _configure_tab1_inner_frame)
        
        # 添加鼠标滚轮支持 - 确保这些绑定不被覆盖
        self.tab1_canvas.bind("<MouseWheel>", self.on_mousewheel)        # Windows
        self.tab1_canvas.bind("<Button-4>", self.on_mousewheel)          # Linux 向上滚动
        self.tab1_canvas.bind("<Button-5>", self.on_mousewheel)          # Linux 向下滚动
        
        # 绑定所有子控件也接收鼠标滚轮事件
        def _bind_mousewheel_to_children(widget):
            # 递归绑定鼠标滚轮事件到所有子控件
            for child in widget.winfo_children():
                # 预览区域单独处理，它有自己的滚动事件
                if child == self.preview_frame or child == self.preview_canvas:
                    continue
                    
                child.bind("<MouseWheel>", self.on_mousewheel)
                child.bind("<Button-4>", self.on_mousewheel)
                child.bind("<Button-5>", self.on_mousewheel)
                self._bind_mousewheel_to_children(child)
        
        tab1_inner_frame.grid_columnconfigure(0, weight=1)
        
        # 图片选择框架
        frame = ttk.LabelFrame(tab1_inner_frame, text="选择图片")
        frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)  # 预览区域可伸缩
        
        # 文件选择区域
        self.files_frame = ttk.Frame(frame)
        self.files_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.files_frame.grid_columnconfigure(0, weight=1)
        
        self.files_label = ttk.Label(self.files_frame, text="已选择0个文件")
        self.files_label.grid(row=0, column=0, sticky="w", pady=5)
        
        # 文件预览和控制区域
        self.preview_frame = ttk.Frame(frame)
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)
        
        # 滚动区域
        self.preview_canvas = tk.Canvas(self.preview_frame)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        
        self.preview_scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical", command=self.preview_canvas.yview)
        
        self.preview_canvas.configure(yscrollcommand=self.preview_scrollbar.set)
        self.preview_canvas.bind('<Configure>', self.check_preview_scrollbar)
        
        self.preview_inner_frame = ttk.Frame(self.preview_canvas)
        self.preview_canvas.create_window((0, 0), window=self.preview_inner_frame, anchor="nw")
        
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.browse_btn = ttk.Button(btn_frame, text="浏览文件", command=self.browse_files)
        self.browse_btn.grid(row=0, column=0, padx=5)
        
        self.clear_btn = ttk.Button(btn_frame, text="清除所有", command=self.clear_files)
        self.clear_btn.grid(row=0, column=1, padx=5)
        
        self.sort_var = tk.BooleanVar(value=True)
        self.sort_check = ttk.Checkbutton(btn_frame, text="自动排序", variable=self.sort_var,
                                         command=self.update_sort)
        self.sort_check.grid(row=0, column=2, padx=5)
        
        # 配置选择区域
        config_frame = ttk.LabelFrame(tab1_inner_frame, text="排列配置")
        config_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        config_frame.grid_columnconfigure(0, weight=1)
        
        ttk.Label(config_frame, text="选择配置:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.config_var = tk.StringVar(value="竖直单列")
        config_options = ["竖直单列", "水平单列", "自定义"]
        
        for i, option in enumerate(config_options):
            ttk.Radiobutton(config_frame, text=option, variable=self.config_var, value=option,
                            command=self.update_config).grid(row=i+1, column=0, sticky="w", padx=20, pady=2)
        
        # 自定义排列方式子框架
        self.custom_frame = ttk.Frame(config_frame)
        self.custom_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        
        self.custom_frame.grid_columnconfigure(0, weight=1)
        
        self.direction_var = tk.StringVar(value="竖直排列")
        ttk.Radiobutton(self.custom_frame, text="竖直排列", variable=self.direction_var, value="竖直排列",
                        command=self.update_direction).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Radiobutton(self.custom_frame, text="水平排列", variable=self.direction_var, value="水平排列",
                        command=self.update_direction).grid(row=1, column=0, sticky="w", pady=2)
        
        self.num_frame = ttk.Frame(self.custom_frame)
        self.num_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        self.num_frame.grid_columnconfigure(1, weight=1)
        
        self.num_label = ttk.Label(self.num_frame, text="排几列:")
        self.num_label.grid(row=0, column=0, padx=5)
        
        self.num_var = tk.IntVar(value=2)
        self.num_scale = ttk.Scale(self.num_frame, from_=1, to=9, orient=tk.HORIZONTAL,
                                  variable=self.num_var, command=self.update_num)
        self.num_scale.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.num_value_label = ttk.Label(self.num_frame, text="2")
        self.num_value_label.grid(row=0, column=2, padx=5)
        
        # 初始状态下隐藏自定义选项
        self.custom_frame.grid_remove()
        
        # 设置初始参数
        self.set_param("竖直排列", 1)
        
        # 初始更新，显示排序状态
        self.update_sort()
        
        # 启用拖放功能
        self.preview_frame.drop_target_register('DND_Files')
        self.preview_frame.dnd_bind('<<Drop>>', self.drop_files)
        
        # 为预览区域添加鼠标滚轮支持
        self.preview_canvas.bind("<MouseWheel>", self.on_preview_mousewheel)
        self.preview_canvas.bind("<Button-4>", self.on_preview_mousewheel)
        self.preview_canvas.bind("<Button-5>", self.on_preview_mousewheel)
        
        # 绑定子控件的鼠标滚轮事件，但排除预览区域
        self._bind_mousewheel_to_children(tab1_inner_frame)
        
        # 最后检查是否需要滚动条
        self.root.update_idletasks()
        self.check_tab1_scrollbar()
        
    def init_tab3(self):
        # 高级选项标签页内容
        self.tab3.grid_columnconfigure(0, weight=1)
        
        frame = ttk.Frame(self.tab3)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        frame.grid_columnconfigure(0, weight=1)
        
        # 输出目录
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=0, column=0, sticky="ew", pady=10)
        
        path_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(path_frame, text="输出目录:").grid(row=0, column=0, padx=5)
        
        self.path_var = tk.StringVar(value=self.outputPath)
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        path_entry.grid(row=0, column=1, sticky="ew", padx=5)
        
        # 修改按钮（选择新目录）
        modify_path_btn = ttk.Button(path_frame, text="修改", command=self.browse_output_path)
        modify_path_btn.grid(row=0, column=2, padx=5)
        
        # 浏览按钮（打开当前输出目录）
        browse_path_btn = ttk.Button(path_frame, text="浏览", command=self.open_output_path)
        browse_path_btn.grid(row=0, column=3, padx=5)
        
        # 图片分辨率 - 下拉框
        res_frame = ttk.Frame(frame)
        res_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        ttk.Label(res_frame, text="图片分辨率:").grid(row=0, column=0, padx=5)
        
        self.res_var = tk.StringVar(value="2.7K")
        res_combobox = ttk.Combobox(res_frame, textvariable=self.res_var, 
                                   values=["4K", "2.7K", "1080P"], 
                                   state="readonly", width=10)
        res_combobox.grid(row=0, column=1, padx=5)
        res_combobox.bind("<<ComboboxSelected>>", lambda e: self.update_resolution())
        
        # 使用裁切
        self.trim_var = tk.BooleanVar(value=False)
        self.trim_check = ttk.Checkbutton(frame, text="使用裁切为正方形", variable=self.trim_var,
                                        command=self.update_trim)
        self.trim_check.grid(row=2, column=0, sticky="w", padx=10, pady=10)
        
        # 质量滑块
        quality_frame = ttk.Frame(frame)
        quality_frame.grid(row=3, column=0, sticky="ew", pady=10)
        
        quality_frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(quality_frame, text="质量:").grid(row=0, column=0, padx=5)
        
        self.quality_var = tk.IntVar(value=92)
        quality_scale = ttk.Scale(quality_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                variable=self.quality_var, command=self.update_quality)
        quality_scale.grid(row=0, column=1, sticky="ew", padx=5)
        
        self.quality_value = ttk.Label(quality_frame, text="92")
        self.quality_value.grid(row=0, column=2, padx=5)
        
        # 初始化分辨率
        self.update_resolution()
        
    def set_param(self, setdirection, setpicNumOfDirection):
        self.direction = setdirection
        self.picNumOfDirection = setpicNumOfDirection
        self.TargetResolutionNum = self.TargetResolution[1]

    def browse_files(self):
        files = filedialog.askopenfilenames(
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.ico *.tga *.tiff")]
        )
        if files:
            for file in files:
                self.uploaded_files.append(file)
            self.update_file_list()
            
    def clear_files(self):
        self.uploaded_files = []
        self.update_file_list()
        
        # 立即重置预览和全局滚动区域
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()
        
        # 强制检查两个滚动条
        self.preview_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.check_preview_scrollbar()
        
        self.tab1_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.tab1_canvas.yview_moveto(0)  # 重置滚动位置
        self.check_tab1_scrollbar()
        
    def update_file_list(self):
        # 清除现有的预览
        for widget in self.preview_inner_frame.winfo_children():
            widget.destroy()
        
        # 根据需要排序
        if self.needSort:
            self.uploaded_files = sorted(self.uploaded_files)
        
        # 更新文件计数
        self.files_label.config(text=f"已选择{len(self.uploaded_files)}个文件")
        
        # 如果没有文件，则重置滚动区域并返回
        if not self.uploaded_files:
            self.preview_canvas.configure(scrollregion=(0, 0, 0, 0))
            self.check_preview_scrollbar()
            self.check_tab1_scrollbar()
            return
        
        # 创建文件预览和控制
        for i, file_path in enumerate(self.uploaded_files):
            frame = ttk.Frame(self.preview_inner_frame)
            frame.pack(fill=tk.X, pady=2)  # 依然使用pack布局，因为这是在canvas内部
            
            frame.grid_columnconfigure(1, weight=1)
            
            # 图片预览
            try:
                img = Image.open(file_path)
                img.thumbnail((80, 80))  # 调整预览大小
                photo = ImageTk.PhotoImage(img)
                
                img_label = ttk.Label(frame, image=photo)
                img_label.image = photo  # 保持引用以防止垃圾回收
                img_label.pack(side=tk.LEFT, padx=5)
            except Exception as e:
                img_label = ttk.Label(frame, text="无法预览")
                img_label.pack(side=tk.LEFT, padx=5)
                
            # 文件名和控制按钮
            info_frame = ttk.Frame(frame)
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            ttk.Label(info_frame, text=f"{i+1}. {os.path.basename(file_path)}").pack(anchor=tk.W)
            
            # 只有非自动排序时才显示控制按钮
            if not self.needSort:
                btn_frame = ttk.Frame(info_frame)
                btn_frame.pack(fill=tk.X, pady=2)
                
                if i > 0:
                    up_btn = ttk.Button(btn_frame, text="上移", 
                                      command=lambda idx=i: self.move_file_up(idx))
                    up_btn.pack(side=tk.LEFT, padx=2)
                    
                if i < len(self.uploaded_files) - 1:
                    down_btn = ttk.Button(btn_frame, text="下移", 
                                        command=lambda idx=i: self.move_file_down(idx))
                    down_btn.pack(side=tk.LEFT, padx=2)
                    
                delete_btn = ttk.Button(btn_frame, text="删除", 
                                      command=lambda idx=i: self.delete_file(idx))
                delete_btn.pack(side=tk.LEFT, padx=2)
            
        # 确保画布更新后才检查滚动条
        self.root.update_idletasks()
        
        # 更新后检查滚动条
        self.check_preview_scrollbar()
        # 检查全局滚动条
        self.check_tab1_scrollbar()
        
    def move_file_up(self, index):
        if index > 0:
            self.uploaded_files[index], self.uploaded_files[index-1] = self.uploaded_files[index-1], self.uploaded_files[index]
            self.update_file_list()
            
    def move_file_down(self, index):
        if index < len(self.uploaded_files) - 1:
            self.uploaded_files[index], self.uploaded_files[index+1] = self.uploaded_files[index+1], self.uploaded_files[index]
            self.update_file_list()
            
    def delete_file(self, index):
        if 0 <= index < len(self.uploaded_files):
            del self.uploaded_files[index]
            self.update_file_list()
            
    def browse_output_path(self):
        directory = filedialog.askdirectory()
        if directory:
            self.outputPath = directory
            self.path_var.set(directory)
            
    def open_output_path(self):
        if not os.path.exists(self.outputPath):
            try:
                os.makedirs(self.outputPath)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
        
        # 使用系统默认程序打开文件夹
        try:
            import subprocess
            if os.name == 'nt':  # Windows
                os.startfile(self.outputPath)
            elif os.name == 'posix':  # macOS, Linux
                if 'darwin' in sys.platform:  # macOS
                    subprocess.call(['open', self.outputPath])
                else:  # Linux
                    subprocess.call(['xdg-open', self.outputPath])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开输出目录: {str(e)}")
        
    def update_resolution(self):
        res = self.res_var.get()
        if res == "4K":
            self.TargetResolution = [3840, 2160]
        elif res == "2.7K":
            self.TargetResolution = [2560, 1440]
        elif res == "1080P":
            self.TargetResolution = [1920, 1080]
        
        self.TargetResolutionNum = self.TargetResolution[1]
        
    def update_trim(self):
        self.needTrim = self.trim_var.get()
        
    def update_quality(self, event=None):
        self.quality = self.quality_var.get()
        self.quality_value.config(text=str(self.quality))
        
    def update_progress(self, value, text="处理中"):
        self.progress["value"] = value
        self.status_label.config(text=text)
        self.root.update_idletasks()
        
    def generate(self):
        if not self.uploaded_files:
            messagebox.showwarning("警告", "请先选择图片文件")
            return
            
        self.update_progress(0, "准备中...")
        
        # 确保输出目录存在
        if not os.path.exists(self.outputPath):
            try:
                os.makedirs(self.outputPath)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {str(e)}")
                return
        
        # 创建BytesIO对象的列表
        files_bytes = []
        for file_path in self.uploaded_files:
            try:
                with open(file_path, 'rb') as f:
                    files_bytes.append(BytesIO(f.read()))
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败: {file_path}\n{str(e)}")
                return
        
        # 创建进度条适配器对象
        class ProgressBarAdapter:
            def __init__(self, app):
                self.app = app
            
            def progress(self, value, text="处理中"):
                self.app.root.after(0, lambda: self.app.update_progress(value, text))
        
        progress_adapter = ProgressBarAdapter(self)
        
        # 在后台线程中运行处理
        def processing_thread():
            try:
                result = core.main(
                    files_bytes, 
                    self.direction, 
                    self.picNumOfDirection,
                    self.TargetResolutionNum, 
                    self.outputPath, 
                    self.quality, 
                    progress_adapter,  # 使用适配器对象而不是回调函数
                    self.needTrim
                )
                
                # 处理完成后更新UI
                self.root.after(0, lambda: self.show_result(result))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"处理失败: {str(e)}"))
        
        # 启动后台线程
        threading.Thread(target=processing_thread, daemon=True).start()
    
    def show_result(self, result):
        self.update_progress(100, "完成")
        # 移除完成弹框
        # messagebox.showinfo("完成", result)
        self.status_label.config(text=result)
        # 3秒后清除状态
        self.root.after(3000, lambda: self.update_progress(0, ""))

    def update_sort(self):
        self.needSort = self.sort_var.get()
        self.update_file_list()

    def update_config(self):
        config = self.config_var.get()
        if config == "竖直单列":
            self.set_param("竖直排列", 1)
            self.custom_frame.grid_remove()
        elif config == "水平单列":
            self.set_param("水平排列", 1)
            self.custom_frame.grid_remove()
        elif config == "自定义":
            self.custom_frame.grid()
            self.update_direction()
            
    def update_direction(self):
        self.direction = self.direction_var.get()
        if self.direction == "竖直排列":
            self.num_label.config(text="排几列:")
        else:
            self.num_label.config(text="排几行:")
        self.set_param(self.direction, self.num_var.get())
        
    def update_num(self, event=None):
        num = int(self.num_var.get())
        self.num_value_label.config(text=str(num))
        self.set_param(self.direction, num)
        
    def toggle_advanced(self):
        pass  # 不再需要此功能，保留方法以避免错误
        
    def update_preview(self):
        pass  # 已被update_file_list取代

    def drop_files(self, event):
        # 获取拖放的文件路径
        data = event.data
        
        if isinstance(data, str):
            # 处理字符串格式的路径
            if data.startswith('{') and data.endswith('}'):
                # Windows风格的路径列表 {path1} {path2}
                paths = []
                # 移除首尾的大括号
                data = data[1:-1]
                # 分割并处理可能带有空格和大括号的路径
                paths_raw = data.split('} {')
                for p in paths_raw:
                    if p.startswith('{'):
                        p = p[1:]
                    if p.endswith('}'):
                        p = p[:-1]
                    paths.append(p)
            else:
                # 单个文件路径或Unix风格的路径列表
                paths = data.split()
        else:
            # 处理列表格式的路径
            paths = data
        
        # 过滤支持的图片文件类型
        valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.ico', '.tga', '.tiff']
        count = 0
        
        for path in paths:
            path = path.strip('"\'')  # 移除可能的引号
            ext = os.path.splitext(path)[1].lower()
            if ext in valid_extensions and os.path.isfile(path):
                self.uploaded_files.append(path)
                count += 1
        
        if count > 0:
            self.update_file_list()

    def check_preview_scrollbar(self, event=None):
        # 更新画布的滚动区域
        self.preview_canvas.update_idletasks()
        self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox("all"))
        
        # 判断是否需要滚动条
        preview_height = self.preview_inner_frame.winfo_reqheight()
        canvas_height = self.preview_canvas.winfo_height()
        
        if preview_height <= canvas_height:
            # 不需要滚动条
            if self.preview_scrollbar.winfo_ismapped():
                self.preview_scrollbar.grid_forget()
        else:
            # 需要滚动条
            if not self.preview_scrollbar.winfo_ismapped():
                self.preview_scrollbar.grid(row=0, column=1, sticky="ns")

    def check_tab1_scrollbar(self, event=None):
        # 更新画布的滚动区域
        self.tab1_canvas.update_idletasks()
        
        # 获取内容的实际大小
        bbox = self.tab1_canvas.bbox("all")
        if not bbox:
            # 没有内容，不需要滚动条
            if self.tab1_scrollbar.winfo_ismapped():
                self.tab1_scrollbar.grid_forget()
                # 重置滚动位置
                self.tab1_canvas.yview_moveto(0)
            self.tab1_canvas.configure(scrollregion=(0, 0, 0, 0))
            return
        
        # 设置滚动区域，多加一点底部间距防止内容紧贴底部
        self.tab1_canvas.configure(scrollregion=(0, 0, bbox[2], bbox[3] + 10))
        
        # 判断是否需要滚动条
        content_height = bbox[3]
        canvas_height = self.tab1_canvas.winfo_height()
        
        if content_height <= canvas_height:
            # 不需要滚动条
            if self.tab1_scrollbar.winfo_ismapped():
                self.tab1_scrollbar.grid_forget()
                # 重置滚动位置防止出现空白
                self.tab1_canvas.yview_moveto(0)
        else:
            # 需要滚动条
            if not self.tab1_scrollbar.winfo_ismapped():
                self.tab1_scrollbar.grid(row=0, column=1, sticky="ns")

    def on_mousewheel(self, event):
        # 处理鼠标滚轮事件
        # 首先检查鼠标是否在预览区域
        x, y = self.root.winfo_pointerxy()
        preview_widget = self.preview_canvas.winfo_containing(x, y)
        
        # 如果鼠标在预览区域且预览区域需要滚动
        if preview_widget and self.preview_scrollbar.winfo_ismapped():
            return self.on_preview_mousewheel(event)
        
        # 否则处理全局滚动
        delta = 0
        
        # 统一不同平台的滚动增量
        if event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
        else:
            delta = event.delta
        
        # 滚动幅度调整
        scroll_speed = 1
        units = int((-1 * delta) / 120 * scroll_speed)
        
        # 执行滚动
        self.tab1_canvas.yview_scroll(units, "units")
        
        # 防止事件继续传播
        return "break"

    def on_preview_mousewheel(self, event):
        # 获取鼠标位置
        x, y = self.root.winfo_pointerxy()
        preview_widget = self.preview_canvas.winfo_containing(x, y)
        
        # 如果鼠标在预览区域内且预览滚动条可见
        if preview_widget and self.preview_scrollbar.winfo_ismapped():
            delta = 0
            
            # 统一不同平台的滚动增量
            if event.num == 4:
                delta = 120
            elif event.num == 5:
                delta = -120
            else:
                delta = event.delta
                
            # 滚动幅度调整
            scroll_speed = 1
            units = int((-1 * delta) / 120 * scroll_speed)
            
            # 执行滚动
            self.preview_canvas.yview_scroll(units, "units")
            
            # 防止事件继续传播
            return "break"
        else:
            # 如果不在预览区域或预览不需要滚动，交给全局滚动处理
            return self.on_mousewheel(event)

    def _bind_mousewheel_to_children(self, widget):
        # 递归绑定鼠标滚轮事件到所有子控件
        for child in widget.winfo_children():
            # 预览区域单独处理，它有自己的滚动事件
            if child == self.preview_frame or child == self.preview_canvas:
                continue
            
            child.bind("<MouseWheel>", self.on_mousewheel)
            child.bind("<Button-4>", self.on_mousewheel)
            child.bind("<Button-5>", self.on_mousewheel)
            self._bind_mousewheel_to_children(child)

    # 添加窗口大小变化处理方法
    def on_window_resize(self, event):
        # 只对整个窗口大小变化做响应，忽略子控件事件
        if event.widget == self.root:
            # 延迟检查滚动条，确保界面已重绘
            self.root.after(50, self.check_tab1_scrollbar)
            self.root.after(50, self.check_preview_scrollbar)

if __name__ == "__main__":
    # 设置DPI感知以防止文字模糊
    try:
        from ctypes import windll
        # windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass  # 如果不是Windows或缺少DPI API，就忽略
        
    # 使用TkinterDnD.Tk代替tk.Tk以支持拖放
    if DND_FILES:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    # 强制底部框架总是可见
    root.minsize(600, 400)  # 设置最小窗口大小
    app = PicMergeApp(root)
    root.mainloop() 