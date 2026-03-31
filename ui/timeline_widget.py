"""멀티트랙 타임라인 위젯 (자체 구현, PySide6 QGraphicsScene 기반)
  - QtEditorialTimelineWidget 컨셉을 참고하되, PySide6만 의존
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsScene, QGraphicsView,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsItem, QLabel, QSlider, QPushButton, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QWheelEvent, QContextMenuEvent
)
from core.project_model import Track, Clip
import math


# 색상 팔레트
COLORS = {
    "video": "#4361ee",
    "image": "#4361ee",
    "audio": "#2ecc71",
    "text":  "#f39c12",
    "bgm":   "#9b59b6",
    "selected": "#e74c3c",
    "playhead": "#ff6b6b",
    "ruler_bg": "#16213e",
    "lane_bg1": "#0f1a2e",
    "lane_bg2": "#121f33",
    "header_bg": "#1a1a2e",
    "grid": "#1a2a3e",
}

TRACK_HEIGHT = 50
HEADER_WIDTH = 100
RULER_HEIGHT = 30
PIXELS_PER_SECOND = 80  # 기본 줌


class ClipItem(QGraphicsRectItem):
    """타임라인에 표시되는 개별 클립"""

    def __init__(self, clip: Clip, track_index: int, pps: float, parent=None):
        self.clip = clip
        self.track_index = track_index
        self.pps = pps
        x = HEADER_WIDTH + clip.start_frame * pps
        y = RULER_HEIGHT + track_index * TRACK_HEIGHT + 2
        w = max(clip.duration * pps, 4)
        h = TRACK_HEIGHT - 4
        super().__init__(x, y, w, h, parent)

        color = COLORS.get(clip.clip_type, "#666")
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(QColor("#111"), 1))
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)

        # 클립 이름
        self._label = QGraphicsTextItem(clip.name, self)
        self._label.setDefaultTextColor(QColor("#fff"))
        self._label.setFont(QFont("Malgun Gothic", 8))
        self._label.setPos(4, 2)

    def update_geometry(self, pps: float):
        self.pps = pps
        x = HEADER_WIDTH + self.clip.start_frame * pps
        y = RULER_HEIGHT + self.track_index * TRACK_HEIGHT + 2
        w = max(self.clip.duration * pps, 4)
        h = TRACK_HEIGHT - 4
        self.setRect(x, y, w, h)
        self._label.setPos(x + 4, y + 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value:
                self.setPen(QPen(QColor(COLORS["selected"]), 2))
            else:
                self.setPen(QPen(QColor("#111"), 1))
        return super().itemChange(change, value)


class TimelineWidget(QWidget):
    clip_selected = Signal(str)     # clip_id
    time_changed = Signal(float)    # 플레이헤드 시간

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project = None
        self._pps = PIXELS_PER_SECOND
        self._playhead_time = 0.0
        self._clip_items: list[ClipItem] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 툴바
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)

        for icon, tip, cb in [
            ("✂", "Split", self._split_clip),
            ("🗑", "Delete", self._delete_clip),
            ("◀", "Zoom Out", self._zoom_out),
            ("▶", "Zoom In", self._zoom_in),
        ]:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setFixedSize(32, 28)
            btn.clicked.connect(cb)
            toolbar.addWidget(btn)

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(20, 400)
        self._zoom_slider.setValue(int(self._pps))
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        toolbar.addWidget(QLabel("Zoom:"))
        toolbar.addWidget(self._zoom_slider)
        toolbar.addStretch()

        self._time_label = QLabel("00:00.00")
        self._time_label.setFont(QFont("Consolas", 10))
        self._time_label.setStyleSheet("color: #7ec8e3;")
        toolbar.addWidget(self._time_label)

        layout.addLayout(toolbar)

        # 그래픽스 뷰
        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setDragMode(QGraphicsView.RubberBandDrag)
        self._view.setStyleSheet("background-color: #0a0a1a; border: none;")
        self._view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._view)

        # 플레이헤드 라인
        self._playhead_line = None

    def set_project(self, project):
        self._project = project
        self._rebuild()

    def set_playhead(self, t: float):
        self._playhead_time = t
        self._update_playhead()
        m = int(t) // 60
        s = t - m * 60
        self._time_label.setText(f"{m:02d}:{s:05.2f}")

    def _rebuild(self):
        self._scene.clear()
        self._clip_items.clear()
        if not self._project:
            return

        total_dur = max(self._project.total_duration + 5, 30)
        scene_width = HEADER_WIDTH + total_dur * self._pps + 100
        num_tracks = len(self._project.tracks)
        scene_height = RULER_HEIGHT + num_tracks * TRACK_HEIGHT + 20

        self._scene.setSceneRect(0, 0, scene_width, scene_height)

        # 룰러 배경
        self._scene.addRect(
            0, 0, scene_width, RULER_HEIGHT,
            QPen(Qt.NoPen), QBrush(QColor(COLORS["ruler_bg"]))
        )

        # 룰러 눈금
        for sec in range(int(total_dur) + 1):
            x = HEADER_WIDTH + sec * self._pps
            if sec % 5 == 0:
                line = self._scene.addLine(x, 0, x, RULER_HEIGHT, QPen(QColor("#7ec8e3"), 1))
                txt = self._scene.addText(f"{sec // 60}:{sec % 60:02d}", QFont("Consolas", 7))
                txt.setDefaultTextColor(QColor("#7ec8e3"))
                txt.setPos(x + 2, 2)
            else:
                self._scene.addLine(x, RULER_HEIGHT - 8, x, RULER_HEIGHT, QPen(QColor("#4a6fa5"), 1))

        # 트랙 배경 및 헤더
        for i, track in enumerate(self._project.tracks):
            y = RULER_HEIGHT + i * TRACK_HEIGHT

            # 레인 배경
            bg_color = COLORS["lane_bg1"] if i % 2 == 0 else COLORS["lane_bg2"]
            self._scene.addRect(
                HEADER_WIDTH, y, scene_width - HEADER_WIDTH, TRACK_HEIGHT,
                QPen(Qt.NoPen), QBrush(QColor(bg_color))
            )

            # 헤더
            self._scene.addRect(
                0, y, HEADER_WIDTH, TRACK_HEIGHT,
                QPen(QColor("#333"), 1), QBrush(QColor(COLORS["header_bg"]))
            )
            header_text = self._scene.addText(track.name, QFont("Malgun Gothic", 9))
            header_text.setDefaultTextColor(QColor("#ccc"))
            header_text.setPos(8, y + (TRACK_HEIGHT - 16) / 2)

            # 클립들
            for clip in track.clips:
                ci = ClipItem(clip, i, self._pps)
                self._scene.addItem(ci)
                self._clip_items.append(ci)

        # 플레이헤드
        self._update_playhead()

        # 선택 이벤트 연결
        self._scene.selectionChanged.connect(self._on_selection)

    def _update_playhead(self):
        if self._playhead_line:
            self._scene.removeItem(self._playhead_line)
        x = HEADER_WIDTH + self._playhead_time * self._pps
        num_tracks = len(self._project.tracks) if self._project else 1
        h = RULER_HEIGHT + num_tracks * TRACK_HEIGHT
        pen = QPen(QColor(COLORS["playhead"]), 2)
        self._playhead_line = self._scene.addLine(x, 0, x, h, pen)

    def _on_selection(self):
        items = self._scene.selectedItems()
        for item in items:
            if isinstance(item, ClipItem):
                self.clip_selected.emit(item.clip.clip_id)
                return

    def _on_zoom(self, value):
        self._pps = value
        self._rebuild()

    def _zoom_in(self):
        self._zoom_slider.setValue(min(self._pps + 20, 400))

    def _zoom_out(self):
        self._zoom_slider.setValue(max(self._pps - 20, 20))

    def _split_clip(self):
        items = self._scene.selectedItems()
        if not items or not self._project:
            return
        for item in items:
            if isinstance(item, ClipItem):
                clip = item.clip
                t = self._playhead_time
                if clip.start_frame < t < clip.start_frame + clip.duration:
                    # 현재 클립 자르기
                    new_dur = t - clip.start_frame
                    remaining = clip.duration - new_dur

                    # 원본 수정
                    clip.duration = new_dur

                    # 새 클립 생성
                    import uuid
                    new_clip = Clip(
                        clip_id=uuid.uuid4().hex[:8],
                        name=clip.name + "_B",
                        file_path=clip.file_path,
                        start_frame=t,
                        duration=remaining,
                        clip_type=clip.clip_type,
                        volume=clip.volume,
                        opacity=clip.opacity,
                        text_content=clip.text_content,
                        text_style=clip.text_style.copy(),
                        metadata=clip.metadata.copy(),
                    )
                    track = self._project.get_track(clip.track_id)
                    if track:
                        track.add_clip(new_clip)
                    self._rebuild()
                    return

    def _delete_clip(self):
        items = self._scene.selectedItems()
        if not items or not self._project:
            return
        for item in items:
            if isinstance(item, ClipItem):
                for track in self._project.tracks:
                    track.remove_clip(item.clip.clip_id)
        self._rebuild()
