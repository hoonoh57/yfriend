"""AI 어시스턴트 바 v0.2"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ui.icons import icon_ai


class AIAssistantBar(QWidget):
    command_submitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(42)
        self.setStyleSheet("background: #161b22; border-top: 1px solid #30363d; border-bottom: 1px solid #30363d;")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_ai().pixmap(22, 22))
        layout.addWidget(icon_lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            'AI: "배경음악 잔잔하게", "3번 장면 야경으로 재생성", "자막 크기 키워줘", "전체 영상 새로 만들어"...'
        )
        self._input.setFont(QFont("Malgun Gothic", 10))
        self._input.setStyleSheet("border: 1px solid #30363d; border-radius: 16px; padding: 4px 12px;")
        self._input.returnPressed.connect(self._submit)
        layout.addWidget(self._input, 1)

        self._quick = QComboBox()
        self._quick.addItems([
            "Quick...",
            "Generate Full Video",
            "Regenerate All Images",
            "Add Background Music",
            "Change Subtitle Style",
            "Adjust Voice Speed",
            "Export 1080p",
        ])
        self._quick.setFixedWidth(160)
        self._quick.currentIndexChanged.connect(self._on_quick)
        layout.addWidget(self._quick)

        self._btn = QPushButton("Run")
        self._btn.setFixedWidth(70)
        self._btn.clicked.connect(self._submit)
        layout.addWidget(self._btn)

    def _submit(self):
        t = self._input.text().strip()
        if t:
            self.command_submitted.emit(t)
            self._input.clear()

    def _on_quick(self, idx):
        if idx > 0:
            self._input.setText(self._quick.itemText(idx))
            self._quick.setCurrentIndex(0)
