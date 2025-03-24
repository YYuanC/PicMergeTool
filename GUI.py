# -*- coding: utf-8 -*-
import sys
import os
import threading
from io import BytesIO
from PIL import Image, ImageQt

from PySide6.QtCore import Qt, QSize, Signal, QThread, QMimeData, QUrl, QEvent, QObject, QTimer
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                              QHBoxLayout, QFileDialog, QMessageBox, 
                              QButtonGroup, QFrame)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor

from qfluentwidgets import (FluentWindow, NavigationInterface, NavigationItemPosition, 
                           ScrollArea, FluentIcon, setTheme, Theme, PrimaryPushButton, 
                           StrongBodyLabel, BodyLabel, CheckBox, RadioButton, Slider, 
                           PushButton, ProgressBar, ComboBox, LineEdit, setThemeColor,
                           SmoothScrollArea, TitleLabel, SubtitleLabel, CardWidget)
import core.core

class ProgressBarWorker(QThread):
    """处理后台任务的工作线程"""
    progress_update = Signal(int, str)
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, files_bytes, direction, pic_num, target_resolution, 
                 output_path, quality, need_trim):
        super().__init__()
        self.files_bytes = files_bytes
        self.direction = direction
        self.pic_num = pic_num
        self.target_resolution = target_resolution
        self.output_path = output_path
        self.quality = quality
        self.need_trim = need_trim

    def run(self):
        try:
            class ProgressBarAdapter:
                def __init__(self, worker):
                    self.worker = worker
                
                def progress(self, value, text="处理中"):
                    self.worker.progress_update.emit(value, text)
            
            progress_adapter = ProgressBarAdapter(self)
            
            # 调用核心处理函数
            result = core.main(
                self.files_bytes,
                self.direction,
                self.pic_num,
                self.target_resolution,
                self.output_path,
                self.quality,
                progress_adapter,
                self.need_trim
            )
            
            self.completed.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FilePreviewItem(CardWidget):
    """文件预览项组件"""
    def __init__(self, file_path, index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.parent_widget = parent
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        
        # 图片预览
        try:
            img = Image.open(file_path)
            img.thumbnail((120, 120)) 
            q_img = ImageQt.ImageQt(img)
            pixmap = QPixmap.fromImage(q_img)
            
            self.img_label = QLabel()
            self.img_label.setPixmap(pixmap)
            self.img_label.setFixedSize(120, 120)
            layout.addWidget(self.img_label)
        except Exception:
            self.img_label = QLabel("无法预览")
            self.img_label.setFixedSize(120, 120)
            self.img_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.img_label)
        
        # 文件信息容器
        info_container = QWidget()
        info_vlayout = QVBoxLayout(info_container)
        info_vlayout.setContentsMargins(0, 0, 0, 0)
        info_vlayout.setSpacing(0)
        
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10) 
        
        self.filename_label = BodyLabel(os.path.basename(file_path))
        self.filename_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_layout.addWidget(self.filename_label, 1)
        
        # 控制按钮容器 - 使用两列布局
        self.btn_container = QWidget()
        self.btn_layout = QHBoxLayout(self.btn_container)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_layout.setSpacing(8) 
        
        self.move_column = QWidget()
        self.move_layout = QVBoxLayout(self.move_column)
        self.move_layout.setContentsMargins(0, 0, 0, 0)
        self.move_layout.setSpacing(2)
        self.move_layout.setAlignment(Qt.AlignVCenter) 
        
        self.delete_column = QWidget()
        self.delete_layout = QVBoxLayout(self.delete_column)
        self.delete_layout.setContentsMargins(0, 0, 0, 0)
        self.delete_layout.setSpacing(0)
        self.delete_layout.setAlignment(Qt.AlignVCenter)
        
        self.btn_layout.addWidget(self.move_column)
        self.btn_layout.addWidget(self.delete_column)
        
        info_layout.addWidget(self.btn_container)
        
        info_vlayout.addLayout(info_layout)
        
        layout.addWidget(info_container, 1)
    
    def set_controls_visible(self, visible):
        """设置控制按钮是否可见"""
        # 清除现有按钮
        while self.move_layout.count():
            item = self.move_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        while self.delete_layout.count():
            item = self.delete_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        if visible:
            btn_height = 30
            btn_width = 60
            
            move_buttons = []
            if self.index > 0:
                up_btn = PushButton("上移")
                up_btn.clicked.connect(lambda: self.parent_widget.move_file_up(self.index))
                move_buttons.append(up_btn)
            
            if self.index < len(self.parent_widget.uploaded_files) - 1:
                down_btn = PushButton("下移")
                down_btn.clicked.connect(lambda: self.parent_widget.move_file_down(self.index))
                move_buttons.append(down_btn)
            
            if move_buttons:
                for btn in move_buttons:
                    btn.setFixedHeight(btn_height)
                    btn.setFixedWidth(btn_width)
                    self.move_layout.addWidget(btn)
            
            # 删除按钮到
            delete_btn = PushButton("删除")
            delete_btn.setFixedHeight(btn_height)
            delete_btn.setFixedWidth(btn_width)
            delete_btn.clicked.connect(lambda: self.parent_widget.delete_file(self.index))
            self.delete_layout.addWidget(delete_btn)


class BasicPage(ScrollArea):
    """基本设置页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setObjectName("BasicPage")
        
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.scroll_content = QWidget()
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        
        self.vBoxLayout = QVBoxLayout(self.scroll_content)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.title = TitleLabel("图片合并工具")
        self.title.setObjectName("Title")
        self.vBoxLayout.addWidget(self.title)
        
        self.init_file_selection()
        
        self.init_layout_config()
        
        self.vBoxLayout.addStretch(1)
        
        main_layout.addWidget(self.scroll_area, 1)
        
        self.init_bottom_controls()
        
        self.setWidget(self.main_container)
        self.setWidgetResizable(True)
    
    def init_file_selection(self):
        """初始化文件选择区域"""
        files_card = CardWidget()
        files_layout = QVBoxLayout(files_card)
        
        title_layout = QHBoxLayout()
        title_layout.addWidget(SubtitleLabel("选择图片"))
        files_layout.addLayout(title_layout)
        
        self.files_label = BodyLabel("已选择0个文件")
        files_layout.addWidget(self.files_label)
        
        # 文件预览区域
        self.preview_scroll = SmoothScrollArea()
        self.preview_scroll.setMinimumHeight(350)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_content = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_content)
        self.preview_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.preview_layout.setSpacing(4)
        self.preview_scroll.setWidget(self.preview_content)
        files_layout.addWidget(self.preview_scroll)
        
        btn_layout = QHBoxLayout()
        
        self.sort_check = CheckBox("自动排序")
        self.sort_check.setChecked(True)
        self.sort_check.clicked.connect(self.parent_app.update_sort)
        btn_layout.addWidget(self.sort_check)
        
        btn_layout.addStretch(1)
        
        clear_btn = PushButton("清除所有")
        clear_btn.setFixedHeight(32)
        clear_btn.clicked.connect(self.parent_app.clear_files)
        btn_layout.addWidget(clear_btn)
        
        browse_btn = PushButton("添加文件")
        browse_btn.setFixedHeight(32)
        browse_btn.clicked.connect(self.parent_app.browse_files)
        btn_layout.addWidget(browse_btn)
        
        files_layout.addLayout(btn_layout)
        
        self.vBoxLayout.addWidget(files_card)
    
    def init_layout_config(self):
        """初始化排列配置区域"""
        config_card = CardWidget()
        config_layout = QVBoxLayout(config_card)
        
        # 配置标题
        config_layout.addWidget(SubtitleLabel("排列配置"))
        
        # 排列选项
        self.config_radio_group = QButtonGroup(self)
        
        vertical_single_radio = RadioButton("竖直单列")
        vertical_single_radio.setChecked(True)
        vertical_single_radio.clicked.connect(lambda: self.parent_app.update_config("竖直单列"))
        config_layout.addWidget(vertical_single_radio)
        self.config_radio_group.addButton(vertical_single_radio)
        
        horizontal_single_radio = RadioButton("水平单列")
        horizontal_single_radio.clicked.connect(lambda: self.parent_app.update_config("水平单列"))
        config_layout.addWidget(horizontal_single_radio)
        self.config_radio_group.addButton(horizontal_single_radio)
        
        custom_radio = RadioButton("自定义")
        custom_radio.clicked.connect(lambda: self.parent_app.update_config("自定义"))
        config_layout.addWidget(custom_radio)
        self.config_radio_group.addButton(custom_radio)
        
        # 自定义配置子区域
        self.custom_config = QWidget()
        custom_config_layout = QVBoxLayout(self.custom_config)
        custom_config_layout.setContentsMargins(20, 0, 0, 0)
        
        # 方向选择
        self.direction_radio_group = QButtonGroup(self)
        
        vertical_radio = RadioButton("竖直排列")
        vertical_radio.setChecked(True)
        vertical_radio.clicked.connect(lambda: self.parent_app.update_direction("竖直排列"))
        custom_config_layout.addWidget(vertical_radio)
        self.direction_radio_group.addButton(vertical_radio)
        
        horizontal_radio = RadioButton("水平排列")
        horizontal_radio.clicked.connect(lambda: self.parent_app.update_direction("水平排列"))
        custom_config_layout.addWidget(horizontal_radio)
        self.direction_radio_group.addButton(horizontal_radio)
        
        # 数量选择
        num_layout = QHBoxLayout()
        self.num_label = BodyLabel("排几列:")
        num_layout.addWidget(self.num_label)
        
        self.num_slider = Slider(Qt.Horizontal)
        self.num_slider.setRange(1, 9)
        self.num_slider.setValue(2)
        self.num_slider.valueChanged.connect(self.parent_app.update_num)
        num_layout.addWidget(self.num_slider, 1)
        
        self.num_value_label = BodyLabel("2")
        num_layout.addWidget(self.num_value_label)
        
        custom_config_layout.addLayout(num_layout)
        
        # 默认隐藏自定义配置
        self.custom_config.setVisible(False)
        config_layout.addWidget(self.custom_config)
        
        self.vBoxLayout.addWidget(config_card)
        
        # 在排列配置之后添加输出目录设置
        self.init_output_path()
    
    def init_output_path(self):
        """初始化输出目录设置"""
        path_card = CardWidget()
        path_layout = QVBoxLayout(path_card)
        
        # 输出目录标题
        path_layout.addWidget(SubtitleLabel("输出目录"))
        
        # 输出目录控件
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(BodyLabel("输出目录:"))
        
        self.path_edit = LineEdit()
        self.path_edit.setText(self.parent_app.outputPath)
        dir_layout.addWidget(self.path_edit, 1)
        
        # 修改目录按钮
        modify_path_btn = PushButton("修改")
        modify_path_btn.setFixedHeight(32)  # 增加高度
        modify_path_btn.clicked.connect(self.parent_app.browse_output_path)
        dir_layout.addWidget(modify_path_btn)
        
        # 浏览目录按钮
        browse_path_btn = PushButton("浏览")
        browse_path_btn.setFixedHeight(32)  # 增加高度
        browse_path_btn.clicked.connect(self.parent_app.open_output_path)
        dir_layout.addWidget(browse_path_btn)
        
        path_layout.addLayout(dir_layout)
        self.vBoxLayout.addWidget(path_card)
    
    def init_bottom_controls(self):
        """初始化底部控制区域（固定在底部）"""
        bottom_container = QWidget()
        bottom_container.setObjectName("BottomContainer")
        bottom_container.setStyleSheet("#BottomContainer{background-color: #f5f5f5; border-top: 1px solid #e0e0e0;}")
        
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        
        self.status_label = BodyLabel("")
        bottom_layout.addWidget(self.status_label)
        
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar, 1)
        
        bottom_layout.addSpacing(35)
        
        self.generate_button = PrimaryPushButton("生成")
        self.generate_button.setFixedHeight(36)
        self.generate_button.clicked.connect(self.parent_app.generate)
        bottom_layout.addWidget(self.generate_button)
        
        self.main_container.layout().addWidget(bottom_container)


class AdvancedPage(ScrollArea):
    """高级设置页面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setObjectName("AdvancedPage")
        
        # 创建主控件和布局
        self.widget = QWidget()
        self.setWidget(self.widget)
        self.setWidgetResizable(True)
        
        self.vBoxLayout = QVBoxLayout(self.widget)
        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题
        self.title = TitleLabel("高级设置")
        self.title.setObjectName("Title")
        self.vBoxLayout.addWidget(self.title)
        
        # 高级设置卡片
        settings_card = CardWidget()
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setSpacing(15)
        
        # 图片分辨率
        res_layout = QHBoxLayout()
        res_layout.addWidget(BodyLabel("目标分辨率:"))
        
        self.res_combo = ComboBox()
        self.res_combo.addItems(["4K", "2.7K", "1080P"])
        self.res_combo.setCurrentText("2.7K")
        self.res_combo.currentTextChanged.connect(self.parent_app.update_resolution)
        res_layout.addWidget(self.res_combo)
        res_layout.addStretch(1)
        
        settings_layout.addLayout(res_layout)
        
        # 使用裁切选项
        self.trim_check = CheckBox("使用裁切为正方形")
        self.trim_check.clicked.connect(self.parent_app.update_trim)
        settings_layout.addWidget(self.trim_check)
        
        # 质量滑块
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(BodyLabel("质量:"))
        
        self.quality_slider = Slider(Qt.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(92)
        self.quality_slider.valueChanged.connect(self.parent_app.update_quality)
        quality_layout.addWidget(self.quality_slider, 1)
        
        self.quality_value_label = BodyLabel("92")
        quality_layout.addWidget(self.quality_value_label)
        
        settings_layout.addLayout(quality_layout)
        
        self.vBoxLayout.addWidget(settings_card)
        
        # 添加弹性空间
        self.vBoxLayout.addStretch(1)


class PicMergeApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PicMerge")
        
        self.resize(1200, 800)
        
        setTheme(Theme.LIGHT)
        setThemeColor(QColor(0, 120, 212))
        
        self.direction = "竖直排列"
        self.picNumOfDirection = 1
        self.TargetResolution = [2560, 1440]
        self.TargetResolutionNum = self.TargetResolution[1]
        self.outputPath = os.path.join(os.path.expanduser("~"), "Pictures\PicMergeOutput")
        self.needTrim = False
        self.quality = 92
        self.uploaded_files = []
        self.needSort = True
        
        self.basic_page = BasicPage(self)
        self.advanced_page = AdvancedPage(self)
        
        self.init_navigation()
        
        self.setAcceptDrops(True)
        
        self.center_window()
    
    def center_window(self):
        """将窗口居中显示在屏幕上"""
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def init_navigation(self):
        """初始化导航栏"""
        self.addSubInterface(
            self.basic_page,
            FluentIcon.HOME,
            "基本设置",
            position=NavigationItemPosition.TOP
        )
        
        self.addSubInterface(
            self.advanced_page,
            FluentIcon.SETTING,
            "高级设置",
            position=NavigationItemPosition.TOP
        )
        
        self.navigationInterface.setCurrentItem("基本设置")
    
    def set_param(self, setdirection, setpicNumOfDirection):
        """设置排列参数"""
        self.direction = setdirection
        self.picNumOfDirection = setpicNumOfDirection
        self.TargetResolutionNum = self.TargetResolution[1]
    
    def browse_files(self):
        """浏览并选择文件"""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "选择图片",
                "",
                "图片文件 (*.png *.jpg *.jpeg *.bmp *.ico *.tga *.tiff)"
            )
            if files:
                for file_path in files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        self.uploaded_files.append(file_path)
                    else:
                        QMessageBox.warning(self, "警告", f"无法访问文件: {file_path}")
                self.update_file_list()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择文件时出错: {str(e)}")
    
    def clear_files(self):
        """清除所有已选文件"""
        self.uploaded_files = []
        self.update_file_list()
    
    def update_file_list(self):
        """更新文件列表显示"""
        while self.basic_page.preview_layout.count():
            item = self.basic_page.preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        
        if self.needSort:
            self.uploaded_files = sorted(self.uploaded_files)
        
        self.basic_page.files_label.setText(f"已选择{len(self.uploaded_files)}个文件")
        
        for i, file_path in enumerate(self.uploaded_files):
            preview_item = FilePreviewItem(file_path, i, self)
            preview_item.set_controls_visible(not self.needSort)
            self.basic_page.preview_layout.addWidget(preview_item)
        
        if self.uploaded_files:
            self.basic_page.preview_layout.addStretch(1)
    
    def move_file_up(self, index):
        """上移文件"""
        if index > 0:
            self.uploaded_files[index], self.uploaded_files[index-1] = self.uploaded_files[index-1], self.uploaded_files[index]
            self.update_file_list()
    
    def move_file_down(self, index):
        """下移文件"""
        if index < len(self.uploaded_files) - 1:
            self.uploaded_files[index], self.uploaded_files[index+1] = self.uploaded_files[index+1], self.uploaded_files[index]
            self.update_file_list()
    
    def delete_file(self, index):
        """删除文件"""
        if 0 <= index < len(self.uploaded_files):
            del self.uploaded_files[index]
            self.update_file_list()
    
    def browse_output_path(self):
        """选择输出目录"""
        try:
            directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
            if directory:
                self.outputPath = directory
                self.basic_page.path_edit.setText(directory)
                if hasattr(self.advanced_page, 'path_edit'):
                    self.advanced_page.path_edit.setText(directory)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择输出目录时出错: {str(e)}")
    
    def open_output_path(self):
        """打开输出目录"""
        try:
            if not os.path.exists(self.outputPath):
                os.makedirs(self.outputPath)
            
            import subprocess
            if os.name == 'nt':  # Windows
                os.startfile(self.outputPath)
            elif os.name == 'posix':  # macOS, Linux
                if 'darwin' in sys.platform:  # macOS
                    subprocess.call(['open', self.outputPath])
                else:  # Linux
                    subprocess.call(['xdg-open', self.outputPath])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开输出目录: {str(e)}")
    
    def update_resolution(self):
        """更新分辨率设置"""
        try:
            res = self.advanced_page.res_combo.currentText()
            if res == "4K":
                self.TargetResolution = [3840, 2160]
            elif res == "2.7K":
                self.TargetResolution = [2560, 1440]
            elif res == "1080P":
                self.TargetResolution = [1920, 1080]
            
            self.TargetResolutionNum = self.TargetResolution[1]
        except Exception as e:
            QMessageBox.warning(self, "警告", f"更新分辨率设置失败: {str(e)}")
    
    def update_trim(self):
        """更新裁切设置"""
        self.needTrim = self.advanced_page.trim_check.isChecked()
    
    def update_quality(self):
        """更新质量设置"""
        self.quality = self.advanced_page.quality_slider.value()
        self.advanced_page.quality_value_label.setText(str(self.quality))
    
    def update_sort(self):
        """更新排序设置"""
        self.needSort = self.basic_page.sort_check.isChecked()
        self.update_file_list()
    
    def update_config(self, config):
        """更新配置设置"""
        try:
            if config == "竖直单列":
                self.set_param("竖直排列", 1)
                self.basic_page.custom_config.setVisible(False)
            elif config == "水平单列":
                self.set_param("水平排列", 1)
                self.basic_page.custom_config.setVisible(False)
            elif config == "自定义":
                self.basic_page.custom_config.setVisible(True)
                self.update_direction(self.direction)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"更新配置失败: {str(e)}")
    
    def update_direction(self, direction):
        """更新方向设置"""
        try:
            self.direction = direction
            if direction == "竖直排列":
                self.basic_page.num_label.setText("排几列:")
            else:
                self.basic_page.num_label.setText("排几行:")
            self.set_param(direction, self.basic_page.num_slider.value())
        except Exception as e:
            QMessageBox.warning(self, "警告", f"更新方向设置失败: {str(e)}")
    
    def update_num(self):
        """更新数量设置"""
        try:
            num = self.basic_page.num_slider.value()
            self.basic_page.num_value_label.setText(str(num))
            self.set_param(self.direction, num)
        except Exception as e:
            QMessageBox.warning(self, "警告", f"更新数量设置失败: {str(e)}")
    
    def update_progress(self, value, text="处理中"):
        """更新进度条"""
        self.basic_page.progress_bar.setValue(value)
        self.basic_page.status_label.setText(text)
    
    def generate(self):
        """生成合并图片"""
        if not self.uploaded_files:
            QMessageBox.warning(self, "警告", "请先选择图片文件")
            return
        
        self.update_progress(0, "准备中...")
        
        if not os.path.exists(self.outputPath):
            try:
                os.makedirs(self.outputPath)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建输出目录: {str(e)}")
                return
        
        files_bytes = []
        for file_path in self.uploaded_files:
            try:
                with open(file_path, 'rb') as f:
                    files_bytes.append(BytesIO(f.read()))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件失败: {file_path}\n{str(e)}")
                return
        
        self.worker = ProgressBarWorker(
            files_bytes,
            self.direction,
            self.picNumOfDirection,
            self.TargetResolutionNum,
            self.outputPath,
            self.quality,
            self.needTrim
        )
        
        self.worker.progress_update.connect(self.update_progress)
        self.worker.completed.connect(self.show_result)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, "错误", f"处理失败: {e}"))
        
        self.basic_page.generate_button.setEnabled(False)
        
        self.worker.start()
    
    def show_result(self, result):
        """显示处理结果"""
        self.update_progress(100, "完成")
        self.basic_page.status_label.setText(result)
        self.basic_page.generate_button.setEnabled(True)
        QTimer.singleShot(3000, lambda: self.update_progress(0, ""))
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖放事件"""
        try:
            mime_data = event.mimeData()
            
            if mime_data.hasUrls():
                urls = mime_data.urls()
                valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.ico', '.tga', '.tiff']
                count = 0
                
                for url in urls:
                    if url.isLocalFile():
                        file_path = url.toLocalFile()
                        ext = os.path.splitext(file_path)[1].lower()
                        if ext in valid_extensions and os.path.isfile(file_path):
                            self.uploaded_files.append(file_path)
                            count += 1
                
                if count > 0:
                    self.update_file_list()
                    event.acceptProposedAction()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"处理拖放文件时出错: {str(e)}")


if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    window = PicMergeApp()
    window.show()
    sys.exit(app.exec()) 