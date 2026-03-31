"""비디오 프리뷰 위젯 - 이미지/동영상 프리뷰, 재생 컨트롤"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QPixmap, QImage, QFont
import subprocess, tempfile


class PreviewWidget(QWidget):
    """프리뷰 패널 - 현재 플레이헤드 위치의 프레임을 표시"""

    time_changed = Signal(float)  # 현재 시간(초) 변경 시

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_time = 0.0
        self._total_duration = 0.0
        self._playing = False
        self._timer = QTimer(self)
        self._timer.setInterval(40)  # ~25fps
        self._timer.timeout.connect(self._tick)
        self._project = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 프리뷰 화면
        self._canvas = QLabel()
        self._canvas.setAlignment(Qt.AlignCenter)
        self._canvas.setMinimumSize(480, 270)
        self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._canvas.setStyleSheet("background-color: #000; border-radius: 8px;")
        layout.addWidget(self._canvas)

        # 타임코드
        self._timecode = QLabel("00:00.00 / 00:00.00")
        self._timecode.setAlignment(Qt.AlignCenter)
        self._timecode.setFont(QFont("Consolas", 11))
        self._timecode.setStyleSheet("color: #7ec8e3;")
        layout.addWidget(self._timecode)

        # 재생 컨트롤
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        self._btn_prev = QPushButton("⏮")
        self._btn_prev.setFixedSize(36, 36)
        self._btn_prev.clicked.connect(self._go_prev)

        self._btn_play = QPushButton("▶")
        self._btn_play.setFixedSize(48, 36)
        self._btn_play.clicked.connect(self._toggle_play)

        self._btn_next = QPushButton("⏭")
        self._btn_next.setFixedSize(36, 36)
        self._btn_next.clicked.connect(self._go_next)

        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 10000)
        self._seek_slider.sliderMoved.connect(self._on_seek)

        ctrl_layout.addWidget(self._btn_prev)
        ctrl_layout.addWidget(self._btn_play)
        ctrl_layout.addWidget(self._btn_next)
        ctrl_layout.addWidget(self._seek_slider)
        layout.addLayout(ctrl_layout)

    def set_project(self, project):
        self._project = project
        self._total_duration = project.total_duration if project else 0
        self._current_time = 0
        self._update_display()

    def set_time(self, t: float):
        self._current_time = max(0, min(t, self._total_duration))
        self._update_display()

    def _toggle_play(self):
        if self._playing:
            self._playing = False
            self._timer.stop()
            self._btn_play.setText("▶")
        else:
            self._playing = True
            self._timer.start()
            self._btn_play.setText("⏸")

    def _tick(self):
        self._current_time += 0.04
        if self._current_time >= self._total_duration:
            self._current_time = 0
            self._playing = False
            self._timer.stop()
            self._btn_play.setText("▶")
        self.time_changed.emit(self._current_time)
        self._update_display()

    def _go_prev(self):
        self.set_time(self._current_time - 5.0)
        self.time_changed.emit(self._current_time)

    def _go_next(self):
        self.set_time(self._current_time + 5.0)
        self.time_changed.emit(self._current_time)

    def _on_seek(self, value):
        if self._total_duration > 0:
            t = (value / 10000.0) * self._total_duration
            self.set_time(t)
            self.time_changed.emit(self._current_time)

    def _update_display(self):
        # 타임코드 갱신
        cur = self._format_time(self._current_time)
        tot = self._format_time(self._total_duration)
        self._timecode.setText(f"{cur} / {tot}")

        # 슬라이더 갱신
        if self._total_duration > 0:
            pos = int((self._current_time / self._total_duration) * 10000)
            self._seek_slider.blockSignals(True)
            self._seek_slider.setValue(pos)
            self._seek_slider.blockSignals(False)

        # 현재 시간에 해당하는 이미지 표시
        if self._project:
            self._show_frame_at(self._current_time)

    def _show_frame_at(self, t: float):
        """프로젝트에서 현재 시간의 최상위 비디오/이미지 클립을 찾아 표시"""
        for track in self._project.tracks:
            if track.track_type not in ("video",) or not track.visible:
                continue
            for clip in track.clips:
                if clip.start_frame <= t < clip.start_frame + clip.duration:
                    self._show_image(clip.file_path)
                    return
        # 이미지 없으면 검은 화면
        self._canvas.setPixmap(QPixmap())

    def _show_image(self, path: str):
        p = Path(path)
        if p.exists() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            pixmap = QPixmap(str(p))
            scaled = pixmap.scaled(
                self._canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._canvas.setPixmap(scaled)

    @staticmethod
    def _format_time(seconds: float) -> str:
        m = int(seconds) // 60
        s = seconds - m * 60
        return f"{m:02d}:{s:05.2f}"
