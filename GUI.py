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
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor, QKeySequence, QClipboard, QImage, QKeyEvent

from qfluentwidgets import (FluentWindow, NavigationInterface, NavigationItemPosition, 
                           ScrollArea, FluentIcon, setTheme, Theme, PrimaryPushButton, 
                           StrongBodyLabel, BodyLabel, CheckBox, RadioButton, Slider, 
                           PushButton, ProgressBar, ComboBox, LineEdit, setThemeColor,
                           SmoothScrollArea, TitleLabel, SubtitleLabel, CardWidget)
from core import core

class ProgressBarWorker(QThread):
    """处理后台任务的工作线程"""
    progress_update = Signal(int, str)
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, files_bytes, direction, pic_num, target_resolution, 
                 output_path, quality, need_trim, need_gap=False, 
                 gap_color=(255,255,255), gap_width=10, need_border=False,
                 border_color=(255,255,255), h_border_width=0, v_border_width=0):
        super().__init__()
        self.files_bytes = files_bytes
        self.direction = direction
        self.pic_num = pic_num
        self.target_resolution = target_resolution
        self.output_path = output_path
        self.quality = quality
        self.need_trim = need_trim
        self.need_gap = need_gap
        self.gap_color = gap_color
        self.gap_width = gap_width
        self.need_border = need_border
        self.border_color = border_color
        self.h_border_width = h_border_width
        self.v_border_width = v_border_width
    
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
                self.need_trim,
                self.need_gap,
                self.gap_color,
                self.gap_width,
                self.need_border,
                self.border_color,
                self.h_border_width,
                self.v_border_width
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
            
            # 删除按钮
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
        
        self.title = TitleLabel("图片合并")
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
        
        self.sort_check = CheckBox("手动排序")
        self.sort_check.setChecked(False)
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
        self.num_slider.setFixedWidth(300)
        self.num_slider.valueChanged.connect(self.parent_app.update_num)
        num_layout.addWidget(self.num_slider)

        self.num_value_label = BodyLabel("2")
        num_layout.addWidget(self.num_value_label)

        num_layout.addStretch(1)  # 添加弹性空间推动所有元素靠左

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
        
        # ===== 图像质量设置卡片 =====
        image_quality_card = CardWidget()
        quality_layout = QVBoxLayout(image_quality_card)
        quality_layout.setSpacing(15)
        quality_layout.setContentsMargins(20, 15, 20, 15)
        
        quality_title = SubtitleLabel("图像质量")
        quality_title.setObjectName("CardTitle")
        quality_layout.addWidget(quality_title)
        
        # 图片分辨率
        res_layout = QHBoxLayout()
        res_layout.setSpacing(10)
        res_layout.setAlignment(Qt.AlignVCenter)
        
        res_label = BodyLabel("目标分辨率:")
        res_label.setAlignment(Qt.AlignVCenter)
        res_layout.addWidget(res_label)
        
        self.res_combo = ComboBox()
        self.res_combo.addItems(["8K", "4K", "2.7K", "1080P"])
        self.res_combo.setCurrentText("2.7K")
        self.res_combo.setFixedWidth(120)
        self.res_combo.setToolTip("选择输出图像的目标分辨率")
        self.res_combo.currentTextChanged.connect(self.parent_app.update_resolution)
        res_layout.addWidget(self.res_combo)
        res_layout.addStretch(1)
        
        quality_layout.addLayout(res_layout)
        
        # 质量滑块
        quality_slider_layout = QHBoxLayout()
        quality_slider_layout.setSpacing(10)
        quality_slider_layout.setAlignment(Qt.AlignVCenter)
        
        quality_label = BodyLabel("质量:")
        quality_label.setAlignment(Qt.AlignVCenter)
        quality_slider_layout.addWidget(quality_label)
        
        self.quality_slider = Slider(Qt.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(92)
        self.quality_slider.setFixedWidth(300)
        self.quality_slider.setToolTip("调整输出图像的压缩质量，越高质量越好但文件也越大")
        self.quality_slider.valueChanged.connect(self.parent_app.update_quality)
        quality_slider_layout.addWidget(self.quality_slider)
        
        self.quality_value_label = BodyLabel("92")
        self.quality_value_label.setAlignment(Qt.AlignVCenter)
        quality_slider_layout.addWidget(self.quality_value_label)
        quality_slider_layout.addStretch(1)
        
        quality_layout.addLayout(quality_slider_layout)
        
        self.vBoxLayout.addWidget(image_quality_card)
        
        # ===== 裁切设置卡片 =====
        trim_card = CardWidget()
        trim_layout = QVBoxLayout(trim_card)
        trim_layout.setSpacing(15)
        trim_layout.setContentsMargins(20, 15, 20, 15)
        
        trim_title = SubtitleLabel("裁切")
        trim_title.setObjectName("CardTitle")
        trim_layout.addWidget(trim_title)
        
        # 使用裁切选项
        self.trim_check = CheckBox("使用裁切为正方形")
        self.trim_check.setToolTip("将每张图片裁切为正方形再进行拼接")
        self.trim_check.clicked.connect(self.parent_app.update_trim)
        trim_layout.addWidget(self.trim_check)
        
        self.vBoxLayout.addWidget(trim_card)
        
        # ===== 间隔设置卡片 =====
        gap_card = CardWidget()
        gap_layout = QVBoxLayout(gap_card)
        gap_layout.setSpacing(15)
        gap_layout.setContentsMargins(20, 15, 20, 15)
        
        gap_title = SubtitleLabel("间隔")
        gap_title.setObjectName("CardTitle")
        gap_layout.addWidget(gap_title)
        
        # 间隔设置
        gap_check_layout = QHBoxLayout()
        self.gap_check = CheckBox("添加间隔")
        self.gap_check.setToolTip("在图片之间添加间隔")
        self.gap_check.clicked.connect(self.parent_app.update_gap)
        gap_check_layout.addWidget(self.gap_check)
        
        # 间隔颜色选择
        self.gap_color_combo = ComboBox()
        self.gap_color_combo.addItems(["白边", "黑边"])
        self.gap_color_combo.setCurrentText("白边")
        self.gap_color_combo.setFixedWidth(80)
        self.gap_color_combo.setEnabled(False)
        self.gap_color_combo.setToolTip("选择间隔的颜色")
        self.gap_color_combo.currentTextChanged.connect(self.parent_app.update_gap_color)
        gap_check_layout.addWidget(self.gap_color_combo)
        
        gap_check_layout.addStretch(1)
        gap_layout.addLayout(gap_check_layout)
        
        # 间隔宽度滑块
        gap_width_layout = QHBoxLayout()
        gap_width_layout.setSpacing(10)
        gap_width_layout.setAlignment(Qt.AlignVCenter)
        
        gap_width_label = BodyLabel("间隔宽度:")
        gap_width_label.setAlignment(Qt.AlignVCenter)
        gap_width_layout.addWidget(gap_width_label)
        
        self.gap_width_slider = Slider(Qt.Horizontal)
        self.gap_width_slider.setRange(0, 50)
        self.gap_width_slider.setValue(0)
        self.gap_width_slider.setEnabled(False)
        self.gap_width_slider.setFixedWidth(300)
        self.gap_width_slider.setToolTip("调整图片之间的间隔宽度")
        self.gap_width_slider.valueChanged.connect(self.parent_app.update_gap_width)
        gap_width_layout.addWidget(self.gap_width_slider)
        
        self.gap_width_value_label = BodyLabel("0")
        self.gap_width_value_label.setAlignment(Qt.AlignVCenter)
        gap_width_layout.addWidget(self.gap_width_value_label)
        gap_width_layout.addStretch(1)
        
        gap_layout.addLayout(gap_width_layout)
        
        self.vBoxLayout.addWidget(gap_card)
        
        # ===== 边框设置卡片 =====
        border_card = CardWidget()
        border_layout = QVBoxLayout(border_card)
        border_layout.setSpacing(15)
        border_layout.setContentsMargins(20, 15, 20, 15)
        
        border_title = SubtitleLabel("边框")
        border_title.setObjectName("CardTitle")
        border_layout.addWidget(border_title)
        
        # 添加边框设置
        border_check_layout = QHBoxLayout()
        self.border_check = CheckBox("添加边框")
        self.border_check.setToolTip("在合成图片外围添加边框")
        self.border_check.clicked.connect(self.parent_app.update_border)
        border_check_layout.addWidget(self.border_check)
        
        # 边框颜色选择
        self.border_color_combo = ComboBox()
        self.border_color_combo.addItems(["白边", "黑边"])
        self.border_color_combo.setCurrentText("白边")
        self.border_color_combo.setFixedWidth(80)
        self.border_color_combo.setEnabled(False)
        self.border_color_combo.setToolTip("选择边框的颜色")
        self.border_color_combo.currentTextChanged.connect(self.parent_app.update_border_color)
        border_check_layout.addWidget(self.border_color_combo)
        
        border_check_layout.addStretch(1)
        border_layout.addLayout(border_check_layout)
        
        # 水平边框宽度滑块
        h_border_width_layout = QHBoxLayout()
        h_border_width_layout.setSpacing(10)
        h_border_width_layout.setAlignment(Qt.AlignVCenter)
        
        h_border_width_label = BodyLabel("左右边框宽度:")
        h_border_width_label.setAlignment(Qt.AlignVCenter)
        h_border_width_layout.addWidget(h_border_width_label)
        
        self.h_border_width_slider = Slider(Qt.Horizontal)
        self.h_border_width_slider.setRange(0, 100)
        self.h_border_width_slider.setValue(0)
        self.h_border_width_slider.setEnabled(False)
        self.h_border_width_slider.setFixedWidth(300)
        self.h_border_width_slider.setToolTip("调整合成图片左右两侧的边框宽度")
        self.h_border_width_slider.valueChanged.connect(self.parent_app.update_h_border_width)
        h_border_width_layout.addWidget(self.h_border_width_slider)
        
        self.h_border_width_value_label = BodyLabel("0")
        self.h_border_width_value_label.setAlignment(Qt.AlignVCenter)
        h_border_width_layout.addWidget(self.h_border_width_value_label)
        h_border_width_layout.addStretch(1)
        
        border_layout.addLayout(h_border_width_layout)
        
        # 垂直边框宽度滑块
        v_border_width_layout = QHBoxLayout()
        v_border_width_layout.setSpacing(10)
        v_border_width_layout.setAlignment(Qt.AlignVCenter)
        
        v_border_width_label = BodyLabel("上下边框宽度:")
        v_border_width_label.setAlignment(Qt.AlignVCenter)
        v_border_width_layout.addWidget(v_border_width_label)
        
        self.v_border_width_slider = Slider(Qt.Horizontal)
        self.v_border_width_slider.setRange(0, 100)
        self.v_border_width_slider.setValue(0)
        self.v_border_width_slider.setEnabled(False)
        self.v_border_width_slider.setFixedWidth(300)
        self.v_border_width_slider.setToolTip("调整合成图片上下两侧的边框宽度")
        self.v_border_width_slider.valueChanged.connect(self.parent_app.update_v_border_width)
        v_border_width_layout.addWidget(self.v_border_width_slider)
        
        self.v_border_width_value_label = BodyLabel("0")
        self.v_border_width_value_label.setAlignment(Qt.AlignVCenter)
        v_border_width_layout.addWidget(self.v_border_width_value_label)
        v_border_width_layout.addStretch(1)
        
        border_layout.addLayout(v_border_width_layout)
        
        self.vBoxLayout.addWidget(border_card)
        
        # 添加弹性空间
        self.vBoxLayout.addStretch(1)


class PicMergeApp(FluentWindow):
    """主应用程序窗口"""
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
        self.needGap = False
        self.gapColor = (255, 255, 255)
        self.gapWidth = 10
        self.needBorder = False
        self.borderColor = (255, 255, 255)
        self.h_borderWidth = 0
        self.v_borderWidth = 0
        
        # 设置临时目录路径
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = os.path.join(self.script_dir, "temp")
        
        self.basic_page = BasicPage(self)
        self.advanced_page = AdvancedPage(self)
        
        self.init_navigation()
        
        self.setAcceptDrops(True)
        
        # 安装事件过滤器以捕获键盘事件
        self.installEventFilter(self)
        
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
        # 保存当前滚动位置
        current_scroll_value = self.basic_page.preview_scroll.verticalScrollBar().value()
        
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
        
        # 使用QTimer延迟恢复滚动位置，确保UI已更新
        QTimer.singleShot(10, lambda: self.basic_page.preview_scroll.verticalScrollBar().setValue(current_scroll_value))
    
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
            if res == "8K":
                self.TargetResolution = [7680, 4320]
            elif res == "4K":
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
        self.needSort = not self.basic_page.sort_check.isChecked()
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
    
    def update_gap(self):
        """更新间隔设置"""
        self.needGap = self.advanced_page.gap_check.isChecked()
        # 同时更新颜色选择和宽度滑块的启用状态
        self.advanced_page.gap_color_combo.setEnabled(self.needGap)
        self.advanced_page.gap_width_slider.setEnabled(self.needGap)
        self.advanced_page.gap_width_value_label.setEnabled(self.needGap)
        
        # 设置滑动条禁用状态的样式
        if not self.needGap:
            self.advanced_page.gap_width_slider.setProperty('disabled', True)
        else:
            self.advanced_page.gap_width_slider.setProperty('disabled', False)
        
        # 强制更新样式
        self.advanced_page.gap_width_slider.style().unpolish(self.advanced_page.gap_width_slider)
        self.advanced_page.gap_width_slider.style().polish(self.advanced_page.gap_width_slider)
    
    def update_gap_color(self):
        """更新间隙颜色"""
        color = self.advanced_page.gap_color_combo.currentText()
        self.gapColor = (255, 255, 255) if color == "白边" else (0, 0, 0)
    
    def update_gap_width(self):
        """更新间隙宽度"""
        self.gapWidth = self.advanced_page.gap_width_slider.value()
        self.advanced_page.gap_width_value_label.setText(str(self.gapWidth))
    
    def update_border(self):
        """更新边框设置"""
        self.needBorder = self.advanced_page.border_check.isChecked()
        # 同时更新颜色选择和宽度滑块的启用状态
        self.advanced_page.border_color_combo.setEnabled(self.needBorder)
        self.advanced_page.h_border_width_slider.setEnabled(self.needBorder)
        self.advanced_page.h_border_width_value_label.setEnabled(self.needBorder)
        self.advanced_page.v_border_width_slider.setEnabled(self.needBorder)
        self.advanced_page.v_border_width_value_label.setEnabled(self.needBorder)
        
        # 设置滑动条禁用状态的样式
        if not self.needBorder:
            self.advanced_page.h_border_width_slider.setProperty('disabled', True)
            self.advanced_page.v_border_width_slider.setProperty('disabled', True)
        else:
            self.advanced_page.h_border_width_slider.setProperty('disabled', False)
            self.advanced_page.v_border_width_slider.setProperty('disabled', False)
        
        # 强制更新样式
        self.advanced_page.h_border_width_slider.style().unpolish(self.advanced_page.h_border_width_slider)
        self.advanced_page.h_border_width_slider.style().polish(self.advanced_page.h_border_width_slider)
        self.advanced_page.v_border_width_slider.style().unpolish(self.advanced_page.v_border_width_slider)
        self.advanced_page.v_border_width_slider.style().polish(self.advanced_page.v_border_width_slider)
    
    def update_border_color(self):
        """更新边框颜色"""
        color = self.advanced_page.border_color_combo.currentText()
        self.borderColor = (255, 255, 255) if color == "白边" else (0, 0, 0)
    
    def update_h_border_width(self):
        """更新水平边框宽度"""
        self.h_borderWidth = self.advanced_page.h_border_width_slider.value()
        self.advanced_page.h_border_width_value_label.setText(str(self.h_borderWidth))
    
    def update_v_border_width(self):
        """更新垂直边框宽度"""
        self.v_borderWidth = self.advanced_page.v_border_width_slider.value()
        self.advanced_page.v_border_width_value_label.setText(str(self.v_borderWidth))
    
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
            self.needTrim,
            self.needGap, 
            self.gapColor,
            self.gapWidth,
            self.needBorder,
            self.borderColor,
            self.h_borderWidth,
            self.v_borderWidth
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
        
        self.basic_page.generate_button.setText("浏览")
        self.basic_page.generate_button.setEnabled(True)
        # 正确地断开信号连接
        try:
            self.basic_page.generate_button.clicked.disconnect(self.generate)
        except:
            pass
        self.basic_page.generate_button.clicked.connect(self.open_output_path)
        
        # 5秒后恢复按钮状态
        QTimer.singleShot(5000, self.reset_generate_button)
    
    def reset_generate_button(self):
        """恢复生成按钮状态"""
        self.update_progress(0, "")
        self.basic_page.generate_button.setText("生成")
        # 正确地断开信号连接
        try:
            self.basic_page.generate_button.clicked.disconnect(self.open_output_path)
        except:
            pass
        self.basic_page.generate_button.clicked.connect(self.generate)
    
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


    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获键盘事件"""
        if event.type() == QEvent.KeyPress:
            key_event = event
            # 检测Ctrl+V组合键
            if key_event.key() == Qt.Key_V and key_event.modifiers() == Qt.ControlModifier:
                self.paste_from_clipboard()
                return True
        return super().eventFilter(obj, event)
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴图片"""
        try:
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            # 检查剪贴板是否包含图片
            if mime_data.hasImage():
                image = clipboard.image()
                if not image.isNull():
                    # 创建临时文件保存图片
                    if not os.path.exists(self.temp_dir):
                        os.makedirs(self.temp_dir)
                    
                    # 生成唯一文件名
                    import time
                    temp_file = os.path.join(self.temp_dir, f"clipboard_{int(time.time())}.png")
                    
                    # 保存图片
                    image.save(temp_file, "PNG")
                    
                    # 添加到文件列表
                    self.uploaded_files.append(temp_file)
                    self.update_file_list()
                    return
            
            # 检查剪贴板是否包含文件URL
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
                    return
            
            QMessageBox.information(self, "提示", "粘贴失败，剪贴板中没有可用的图片数据")
        except Exception as e:
            QMessageBox.warning(self, "警告", f"粘贴图片时出错: {str(e)}")

    def cleanup_temp_directory(self):
        """清理剪贴板创建的临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                # 删除目录中的所有文件
                for file_name in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file_name)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"删除临时文件失败: {file_path}, 错误: {e}")
                
                # 删除空目录
                try:
                    os.rmdir(self.temp_dir)
                except Exception as e:
                    print(f"删除临时目录失败: {self.temp_dir}, 错误: {e}")
        except Exception as e:
            print(f"清理临时目录时出错: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.cleanup_temp_directory()
        super().closeEvent(event)

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    
    window = PicMergeApp()
    window.show()
    sys.exit(app.exec())
