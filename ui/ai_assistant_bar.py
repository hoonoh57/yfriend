"""AI 어시스턴트 바 - 자연어로 편집 명령을 입력"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class AIAssistantBar(QWidget):
    command_submitted = Signal(str)  # 자연어 명령

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        icon_label = QLabel("AI")
        icon_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        icon_label.setStyleSheet(
            "color: #4361ee; background-color: #4361ee22; "
            "border-radius: 12px; padding: 4px 10px;"
        )
        layout.addWidget(icon_label)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            '자연어 명령: "배경음악을 잔잔하게 바꿔줘", "3번 장면 이미지를 야경으로 재생성", "전체 자막 크기 키워줘"...'
        )
        self._input.setFont(QFont("Malgun Gothic", 11))
        self._input.returnPressed.connect(self._submit)
        layout.addWidget(self._input, 1)

        # 빠른 명령
        self._quick = QComboBox()
        self._quick.addItems([
            "Quick Commands...",
            "전체 영상 새로 생성",
            "배경음악 추가",
            "자막 스타일 변경",
            "이미지 전체 재생성",
            "음성 속도 조절",
            "내보내기 (1080p)",
        ])
        self._quick.currentIndexChanged.connect(self._on_quick)
        self._quick.setFixedWidth(180)
        layout.addWidget(self._quick)

        self._btn_run = QPushButton("Execute")
        self._btn_run.setFixedWidth(90)
        self._btn_run.clicked.connect(self._submit)
        layout.addWidget(self._btn_run)

    def _submit(self):
        text = self._input.text().strip()
        if text:
            self.command_submitted.emit(text)
            self._input.clear()

    def _on_quick(self, idx):
        if idx > 0:
            self._input.setText(self._quick.itemText(idx))
            self._quick.setCurrentIndex(0)
