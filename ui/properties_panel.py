"""속성 패널 v0.2 — 클립 속성 + 효과 + 키프레임 목록"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QComboBox, QTextEdit, QGroupBox, QScrollArea,
    QPushButton, QHBoxLayout, QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class PropertiesPanel(QWidget):
    clip_updated = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip = None
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        self._form = QVBoxLayout(container)
        self._form.setContentsMargins(8, 8, 8, 8)
        self._form.setSpacing(6)

        # ─── 헤더 ───
        self._header = QLabel("No clip selected")
        self._header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self._header.setStyleSheet("color: #e6edf3; padding: 4px 0;")
        self._form.addWidget(self._header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #30363d;")
        self._form.addWidget(sep)

        # ─── Info ───
        info = QGroupBox("Info")
        il = QFormLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Clip name")
        self._type_lbl = QLabel("-")
        self._file_lbl = QLabel("-")
        self._file_lbl.setWordWrap(True)
        self._file_lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        il.addRow("Name:", self._name_edit)
        il.addRow("Type:", self._type_lbl)
        il.addRow("File:", self._file_lbl)
        info.setLayout(il)
        self._form.addWidget(info)

        # ─── Timing ───
        timing = QGroupBox("Timing")
        tl = QFormLayout()
        self._start = QDoubleSpinBox()
        self._start.setRange(0, 99999); self._start.setDecimals(2); self._start.setSuffix(" s")
        self._dur = QDoubleSpinBox()
        self._dur.setRange(0.1, 99999); self._dur.setDecimals(2); self._dur.setSuffix(" s")
        tl.addRow("Start:", self._start)
        tl.addRow("Duration:", self._dur)
        timing.setLayout(tl)
        self._form.addWidget(timing)

        # ─── Audio / Visual ───
        av = QGroupBox("Audio / Visual")
        al = QFormLayout()
        self._vol = QDoubleSpinBox()
        self._vol.setRange(0, 3.0); self._vol.setDecimals(2); self._vol.setSingleStep(0.05)
        self._opa = QDoubleSpinBox()
        self._opa.setRange(0, 1.0); self._opa.setDecimals(2); self._opa.setSingleStep(0.05)
        al.addRow("Volume:", self._vol)
        al.addRow("Opacity:", self._opa)
        av.setLayout(al)
        self._form.addWidget(av)

        # ─── Text ───
        txt = QGroupBox("Subtitle / Text")
        txtl = QVBoxLayout()
        self._text = QTextEdit()
        self._text.setMaximumHeight(80)
        self._text.setPlaceholderText("Subtitle text...")
        self._font_size = QDoubleSpinBox()
        self._font_size.setRange(8, 200); self._font_size.setValue(42); self._font_size.setPrefix("Size: ")
        self._font_color = QComboBox()
        self._font_color.addItems(["White", "Yellow", "Cyan", "Green", "Red"])
        row = QHBoxLayout()
        row.addWidget(self._font_size)
        row.addWidget(self._font_color)
        txtl.addWidget(self._text)
        txtl.addLayout(row)
        txt.setLayout(txtl)
        self._form.addWidget(txt)

        # ─── Effects ───
        fx = QGroupBox("Effects")
        fxl = QVBoxLayout()
        self._fx_combo = QComboBox()
        self._fx_combo.addItems([
            "None", "Fade In (0.5s)", "Fade Out (0.5s)", "Cross Dissolve",
            "Ken Burns - Zoom In", "Ken Burns - Zoom Out",
            "Ken Burns - Pan Left", "Ken Burns - Pan Right",
            "Blur", "Color Filter - Warm", "Color Filter - Cool",
            "Vignette", "Black & White",
        ])
        self._btn_add_fx = QPushButton("+ Add Effect")
        self._btn_add_fx.setObjectName("flatBtn")
        self._fx_list = QListWidget()
        self._fx_list.setMaximumHeight(80)
        fxl.addWidget(self._fx_combo)
        fxl.addWidget(self._btn_add_fx)
        fxl.addWidget(QLabel("Applied:"))
        fxl.addWidget(self._fx_list)
        fx.setLayout(fxl)
        self._form.addWidget(fx)

        # ─── Keyframes ───
        kf = QGroupBox("Keyframes")
        kfl = QVBoxLayout()
        self._kf_list = QListWidget()
        self._kf_list.setMaximumHeight(60)
        kfl.addWidget(self._kf_list)
        kf.setLayout(kfl)
        self._form.addWidget(kf)

        # ─── Apply ───
        self._btn_apply = QPushButton("Apply Changes")
        self._btn_apply.clicked.connect(self._apply)
        self._form.addWidget(self._btn_apply)

        self._form.addStretch()

        # ─── 다크 테마 강제 적용 ───
        self.setStyleSheet("""
            QGroupBox { color: #8b949e; border: 1px solid #30363d; border-radius: 6px; 
                        margin-top: 10px; padding-top: 14px; font-size: 11px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; padding: 2px 8px; color: #8b949e; }
            QLabel { color: #e6edf3; }
            QLineEdit, QTextEdit, QDoubleSpinBox, QComboBox { 
                background: #0d1117; color: #e6edf3; border: 1px solid #30363d; 
                border-radius: 4px; padding: 4px; }
            QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus { border-color: #4361ee; }
            QPushButton { background: #4361ee; color: #fff; border: none; border-radius: 5px; 
                         padding: 6px 12px; font-weight: 600; }
            QPushButton:hover { background: #5a7bff; }
            QPushButton#flatBtn { background: transparent; color: #8b949e; border: 1px solid #30363d; }
            QPushButton#flatBtn:hover { background: #21262d; color: #e6edf3; }
            QListWidget { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; }
        """)

        scroll.setWidget(container)
        scroll.setStyleSheet("QScrollArea { background: #0d1117; border: none; }")
        container.setStyleSheet("background: #0d1117;")
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

    def set_clip(self, clip):
        self._clip = clip
        if not clip:
            self._header.setText("No clip selected")
            return
        self._header.setText(f"{clip.name}")
        self._name_edit.setText(clip.name)
        self._type_lbl.setText(clip.clip_type.upper())
        self._file_lbl.setText(clip.file_path[-60:] if clip.file_path else "(none)")
        self._start.setValue(clip.start_frame)
        self._dur.setValue(clip.duration)
        self._vol.setValue(clip.volume)
        self._opa.setValue(clip.opacity)
        self._text.setPlainText(clip.text_content)
        self._font_size.setValue(clip.text_style.get("size", 42))

        # 이펙트
        self._fx_list.clear()
        for fx in clip.effects:
            self._fx_list.addItem(fx.effect_type)

        # 키프레임
        self._kf_list.clear()
        for kf in clip.metadata.get("keyframes", []):
            self._kf_list.addItem(f"@ {kf['time']:.2f}s")

    def _apply(self):
        if not self._clip:
            return
        self.clip_updated.emit(self._clip.clip_id, {
            "name": self._name_edit.text(),
            "start_frame": self._start.value(),
            "duration": self._dur.value(),
            "volume": self._vol.value(),
            "opacity": self._opa.value(),
            "text_content": self._text.toPlainText(),
        })
