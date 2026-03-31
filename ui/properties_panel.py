"""속성 패널 - 선택된 클립의 속성을 편집"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QComboBox, QTextEdit, QGroupBox, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal


class PropertiesPanel(QWidget):
    clip_updated = Signal(str, dict)  # clip_id, changed_fields

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip = None
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        # 클립 정보 그룹
        info_group = QGroupBox("Clip Info")
        info_form = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Clip Name")
        self._type_label = QLabel("-")
        self._path_label = QLabel("-")
        self._path_label.setWordWrap(True)
        info_form.addRow("Name:", self._name_edit)
        info_form.addRow("Type:", self._type_label)
        info_form.addRow("File:", self._path_label)
        info_group.setLayout(info_form)
        self._layout.addWidget(info_group)

        # 타이밍
        time_group = QGroupBox("Timing")
        time_form = QFormLayout()
        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(0, 9999)
        self._start_spin.setDecimals(2)
        self._start_spin.setSuffix(" s")
        self._dur_spin = QDoubleSpinBox()
        self._dur_spin.setRange(0.1, 9999)
        self._dur_spin.setDecimals(2)
        self._dur_spin.setSuffix(" s")
        time_form.addRow("Start:", self._start_spin)
        time_form.addRow("Duration:", self._dur_spin)
        time_group.setLayout(time_form)
        self._layout.addWidget(time_group)

        # 볼륨/투명도
        av_group = QGroupBox("Audio / Visual")
        av_form = QFormLayout()
        self._volume_spin = QDoubleSpinBox()
        self._volume_spin.setRange(0, 2.0)
        self._volume_spin.setDecimals(2)
        self._volume_spin.setSingleStep(0.05)
        self._opacity_spin = QDoubleSpinBox()
        self._opacity_spin.setRange(0, 1.0)
        self._opacity_spin.setDecimals(2)
        self._opacity_spin.setSingleStep(0.05)
        av_form.addRow("Volume:", self._volume_spin)
        av_form.addRow("Opacity:", self._opacity_spin)
        av_group.setLayout(av_form)
        self._layout.addWidget(av_group)

        # 텍스트 편집 (자막용)
        text_group = QGroupBox("Text / Subtitle")
        text_form = QVBoxLayout()
        self._text_edit = QTextEdit()
        self._text_edit.setMaximumHeight(100)
        self._text_edit.setPlaceholderText("자막 텍스트를 입력하세요...")
        text_form.addWidget(self._text_edit)
        text_group.setLayout(text_form)
        self._layout.addWidget(text_group)

        # 효과
        fx_group = QGroupBox("Effects")
        fx_form = QFormLayout()
        self._fx_combo = QComboBox()
        self._fx_combo.addItems(["None", "Fade In", "Fade Out", "Ken Burns", "Zoom In", "Zoom Out"])
        self._btn_add_fx = QPushButton("+ Add Effect")
        fx_form.addRow("Effect:", self._fx_combo)
        fx_form.addRow(self._btn_add_fx)
        fx_group.setLayout(fx_form)
        self._layout.addWidget(fx_group)

        # 적용 버튼
        self._btn_apply = QPushButton("Apply Changes")
        self._btn_apply.clicked.connect(self._apply)
        self._layout.addWidget(self._btn_apply)

        self._layout.addStretch()

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def set_clip(self, clip):
        self._clip = clip
        if not clip:
            return
        self._name_edit.setText(clip.name)
        self._type_label.setText(clip.clip_type)
        self._path_label.setText(clip.file_path or "(none)")
        self._start_spin.setValue(clip.start_frame)
        self._dur_spin.setValue(clip.duration)
        self._volume_spin.setValue(clip.volume)
        self._opacity_spin.setValue(clip.opacity)
        self._text_edit.setPlainText(clip.text_content)

    def _apply(self):
        if not self._clip:
            return
        changes = {
            "name": self._name_edit.text(),
            "start_frame": self._start_spin.value(),
            "duration": self._dur_spin.value(),
            "volume": self._volume_spin.value(),
            "opacity": self._opacity_spin.value(),
            "text_content": self._text_edit.toPlainText(),
        }
        self.clip_updated.emit(self._clip.clip_id, changes)
