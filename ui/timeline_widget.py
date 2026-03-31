"""멀티트랙 타임라인 v0.2 — 전문 NLE 기능 (드래그/리사이즈/스냅/리플/그루핑/키프레임)"""
from __future__ import annotations
import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsScene, QGraphicsView,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsItem,
    QLabel, QSlider, QToolButton, QToolBar, QMenu, QSizePolicy, QGraphicsPolygonItem
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QLineF, QTimer
from PySide6.QtGui import (
    QBrush, QPen, QColor, QFont, QPainter, QPainterPath, QPolygonF,
    QCursor, QWheelEvent, QAction
)
from core.project_model import Track, Clip, ProjectModel
from ui.icons import (
    icon_select, icon_cut, icon_trim, icon_ripple, icon_delete,
    icon_copy, icon_magnet, icon_group, icon_keyframe,
    icon_zoom_in, icon_zoom_out, icon_undo, icon_redo
)
from PySide6.QtCore import QSize

# ─── Constants ───
TRACK_H = 52
HEADER_W = 110
RULER_H = 28
MIN_PPS = 15
MAX_PPS = 500
DEFAULT_PPS = 80
SNAP_PX = 8  # 스냅 임계 픽셀

CLIP_COLORS = {
    "video": "#4361ee", "image": "#4361ee", "audio": "#2ecc71",
    "text": "#f39c12", "bgm": "#9b59b6",
}
CLIP_SELECTED_BORDER = "#ff6b6b"
PLAYHEAD_COLOR = "#ff6b6b"


# ─── Clip Graphics Item ───
class ClipItem(QGraphicsRectItem):
    """드래그 이동 + 양쪽 핸들로 리사이즈 가능한 클립"""

    HANDLE_W = 6  # 리사이즈 핸들 폭(px)

    def __init__(self, clip: Clip, track_idx: int, pps: float):
        super().__init__()
        self.clip = clip
        self.track_idx = track_idx
        self.pps = pps
        self.group_id: str | None = None
        self._dragging = False
        self._resize_edge = None  # "left" | "right" | None
        self._drag_start_x = 0.0
        self._orig_start = 0.0
        self._orig_dur = 0.0

        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.OpenHandCursor)

        self._update_rect()

        # 색상
        c = CLIP_COLORS.get(clip.clip_type, "#666")
        self.setBrush(QBrush(QColor(c)))
        self.setPen(QPen(QColor("#0d1117"), 1))
        self.setOpacity(0.9)

        # 라벨
        self._label = QGraphicsTextItem(self)
        self._label.setDefaultTextColor(QColor("#fff"))
        self._label.setFont(QFont("Segoe UI", 8))
        self._update_label()

        # 키프레임 다이아몬드 (표시용)
        self._kf_diamonds: list[QGraphicsPolygonItem] = []

    def _update_rect(self):
        x = HEADER_W + self.clip.start_frame * self.pps
        y = RULER_H + self.track_idx * TRACK_H + 2
        w = max(self.clip.duration * self.pps, 6)
        h = TRACK_H - 4
        self.setRect(x, y, w, h)

    def _update_label(self):
        r = self.rect()
        self._label.setPlainText(self.clip.name)
        self._label.setPos(r.x() + 6, r.y() + 2)
        # 클립이 너무 좁으면 라벨 숨김
        self._label.setVisible(r.width() > 40)

    def refresh(self, pps: float):
        self.pps = pps
        self._update_rect()
        self._update_label()

    # ─── 마우스 상호작용 ───
    def hoverMoveEvent(self, e):
        r = self.rect()
        local_x = e.pos().x()
        if local_x < r.x() + self.HANDLE_W:
            self.setCursor(Qt.SizeHorCursor)
        elif local_x > r.x() + r.width() - self.HANDLE_W:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.OpenHandCursor)
        super().hoverMoveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            r = self.rect()
            local_x = e.pos().x()
            self._drag_start_x = e.scenePos().x()
            self._orig_start = self.clip.start_frame
            self._orig_dur = self.clip.duration

            if local_x < r.x() + self.HANDLE_W:
                self._resize_edge = "left"
                self.setCursor(Qt.SizeHorCursor)
            elif local_x > r.x() + r.width() - self.HANDLE_W:
                self._resize_edge = "right"
                self.setCursor(Qt.SizeHorCursor)
            else:
                self._resize_edge = None
                self._dragging = True
                self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        dx_px = e.scenePos().x() - self._drag_start_x
        dt = dx_px / self.pps if self.pps > 0 else 0

        if self._resize_edge == "left":
            new_start = max(0, self._orig_start + dt)
            shrink = new_start - self._orig_start
            new_dur = max(0.2, self._orig_dur - shrink)
            self.clip.start_frame = new_start
            self.clip.duration = new_dur
        elif self._resize_edge == "right":
            new_dur = max(0.2, self._orig_dur + dt)
            self.clip.duration = new_dur
        elif self._dragging:
            new_start = max(0, self._orig_start + dt)
            self.clip.start_frame = new_start

        self._update_rect()
        self._update_label()
        # 이벤트 소비 — 부모 드래그 방지
        e.accept()

    def mouseReleaseEvent(self, e):
        self._dragging = False
        self._resize_edge = None
        self.setCursor(Qt.OpenHandCursor)
        # 스냅 처리는 scene 레벨에서
        scene = self.scene()
        if scene and hasattr(scene, '_owner'):
            scene._owner._snap_clip(self)
        super().mouseReleaseEvent(e)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if value:
                self.setPen(QPen(QColor(CLIP_SELECTED_BORDER), 2))
                self.setOpacity(1.0)
            else:
                self.setPen(QPen(QColor("#0d1117"), 1))
                self.setOpacity(0.9)
        return super().itemChange(change, value)

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#161b22;color:#e6edf3;border:1px solid #30363d;} QMenu::item:selected{background:#4361ee;}")
        menu.addAction("Split at Playhead", lambda: self.scene()._owner._split_at_playhead(self))
        menu.addAction("Duplicate", lambda: self.scene()._owner._duplicate_clip(self))
        menu.addAction("Delete", lambda: self.scene()._owner._delete_clip_item(self))
        menu.addSeparator()
        menu.addAction("Ripple Delete", lambda: self.scene()._owner._ripple_delete(self))
        menu.addSeparator()
        group_menu = menu.addMenu("Group")
        group_menu.addAction("Group Selected", lambda: self.scene()._owner._group_selected())
        group_menu.addAction("Ungroup", lambda: self.scene()._owner._ungroup(self))
        menu.addSeparator()
        menu.addAction("Add Keyframe", lambda: self.scene()._owner._add_keyframe_to_clip(self))
        menu.exec(e.screenPos())


# ─── Track Header ───
class TrackHeader(QGraphicsRectItem):
    """트랙 헤더 — 이름 + 뮤트/솔로/잠금/보기 버튼 + 타입 색상 바
    
    핵심: 자식 아이템은 부모 로컬 좌표를 사용해야 합니다.
    부모 rect이 (0, scene_y, W, H)이면 자식의 (0,0)은 부모의 좌상단입니다.
    """
    def __init__(self, track: Track, idx: int, scene_width: float, owner=None):
        y = RULER_H + idx * TRACK_H
        super().__init__(0, y, HEADER_W, TRACK_H)
        self.track = track
        self.idx = idx
        self._owner = owner
        self.setBrush(QBrush(QColor("#161b22")))
        self.setPen(QPen(QColor("#30363d"), 1))
        self.setZValue(20)

        # 타입 색상 바 (왼쪽 3px) — setParentItem 명시 호출
        bar = QGraphicsRectItem(0, y, 3, TRACK_H)
        bar.setParentItem(self)
        bar.setBrush(QBrush(QColor(CLIP_COLORS.get(track.track_type, "#666"))))
        bar.setPen(Qt.NoPen)

        # 트랙 이름 — PySide6에서 QGraphicsTextItem(parent)이 작동 안 함
        name = QGraphicsTextItem("")
        name.setParentItem(self)
        name.setPlainText(track.name)
        name.setDefaultTextColor(QColor("#e6edf3"))
        name.setFont(QFont("Segoe UI", 8, QFont.Bold))
        name.setPos(8, y + 3)

        # 뮤트(M) / 솔로(S) / 잠금(L) / 보기(V)
        btn_y_local = y + TRACK_H - 18
        btn_font = QFont("Consolas", 7, QFont.Bold)
        btn_x = 8
        for label, color, attr in [
            ("M", "#e74c3c", "muted"),
            ("S", "#f39c12", "_solo"),
            ("L", "#7ec8e3", "locked"),
            ("V", "#2ecc71", "visible"),
        ]:
            txt = QGraphicsTextItem("")
            txt.setParentItem(self)
            txt.setPlainText(label)
            active = getattr(track, attr, True) if attr != "_solo" else False
            if attr == "visible":
                active = track.visible
            c = color if active else "#484f58"
            txt.setDefaultTextColor(QColor(c))
            txt.setFont(btn_font)
            txt.setPos(btn_x, btn_y_local)
            btn_x += 18

    def contextMenuEvent(self, e):
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#161b22;color:#e6edf3;border:1px solid #30363d;}QMenu::item:selected{background:#4361ee;}")
        menu.addAction(f"Rename '{self.track.name}'", lambda: None)
        menu.addSeparator()
        menu.addAction("Toggle Mute", lambda: self._toggle("muted"))
        menu.addAction("Toggle Lock", lambda: self._toggle("locked"))
        menu.addAction("Toggle Visible", lambda: self._toggle("visible"))
        menu.addSeparator()
        menu.addAction("Insert Track Above", lambda: self._insert("above"))
        menu.addAction("Insert Track Below", lambda: self._insert("below"))
        menu.addAction("Delete Track", lambda: self._delete())
        menu.addSeparator()
        menu.addAction("Move Up", lambda: self._move(-1))
        menu.addAction("Move Down", lambda: self._move(1))
        menu.exec(e.screenPos())

    def _toggle(self, attr):
        setattr(self.track, attr, not getattr(self.track, attr))
        if self._owner:
            self._owner._rebuild()

    def _insert(self, where):
        if not self._owner or not self._owner._project:
            return
        new_track = Track(name=f"Track {len(self._owner._project.tracks)+1}", track_type="video")
        idx = self.idx if where == "above" else self.idx + 1
        self._owner._project.tracks.insert(idx, new_track)
        self._owner._rebuild()

    def _delete(self):
        if not self._owner or not self._owner._project:
            return
        if len(self._owner._project.tracks) <= 1:
            return  # 최소 1트랙 유지
        self._owner._project.tracks.pop(self.idx)
        self._owner._rebuild()

    def _move(self, direction):
        if not self._owner or not self._owner._project:
            return
        tracks = self._owner._project.tracks
        new_idx = self.idx + direction
        if 0 <= new_idx < len(tracks):
            tracks[self.idx], tracks[new_idx] = tracks[new_idx], tracks[self.idx]
            self._owner._rebuild()



# ─── Timeline Widget ───
class TimelineWidget(QWidget):
    clip_selected = Signal(str)
    time_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project: ProjectModel | None = None
        self._pps = DEFAULT_PPS
        self._playhead_time = 0.0
        self._clip_items: list[ClipItem] = []
        self._snap_enabled = True
        self._tool = "select"  # select, cut, trim, ripple
        self._groups: dict[str, list[str]] = {}  # group_id -> [clip_ids]
        self._playhead_line = None
        self._playhead_tri = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─── 툴바 ───
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.setStyleSheet("QToolBar{background:#161b22;border-bottom:1px solid #30363d;padding:1px 4px;}")

        def add_btn(icon, tip, cb, checkable=False, checked=False):
            b = QToolButton()
            b.setIcon(icon)
            b.setToolTip(tip)
            b.setCheckable(checkable)
            b.setChecked(checked)
            b.clicked.connect(cb)
            tb.addWidget(b)
            return b

        # 편집 도구
        self._btn_select = add_btn(icon_select(), "Select (V)", lambda: self._set_tool("select"), True, True)
        self._btn_cut = add_btn(icon_cut(), "Blade / Split (B)", lambda: self._set_tool("cut"), True)
        self._btn_trim = add_btn(icon_trim(), "Trim (T)", lambda: self._set_tool("trim"), True)
        self._btn_ripple = add_btn(icon_ripple(), "Ripple Edit (R)", lambda: self._set_tool("ripple"), True)
        self._tool_buttons = [self._btn_select, self._btn_cut, self._btn_trim, self._btn_ripple]

        tb.addSeparator()

        add_btn(icon_delete(), "Delete (Del)", self._delete_selected)
        add_btn(icon_copy(), "Duplicate (Ctrl+D)", self._duplicate_selected)
        add_btn(icon_group(), "Group (Ctrl+G)", self._group_selected)
        add_btn(icon_keyframe(), "Add Keyframe (K)", self._add_keyframe)

        tb.addSeparator()

        self._btn_snap = add_btn(icon_magnet(), "Snap (S)", self._toggle_snap, True, True)

        tb.addSeparator()

        add_btn(icon_undo(), "Undo (Ctrl+Z)", lambda: None)
        add_btn(icon_redo(), "Redo (Ctrl+Y)", lambda: None)

        # 오른쪽: 줌
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        add_btn(icon_zoom_out(), "Zoom Out (-)", self._zoom_out)
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(MIN_PPS, MAX_PPS)
        self._zoom_slider.setValue(self._pps)
        self._zoom_slider.setFixedWidth(120)
        self._zoom_slider.valueChanged.connect(self._on_zoom)
        tb.addWidget(self._zoom_slider)
        add_btn(icon_zoom_in(), "Zoom In (+)", self._zoom_in)

        self._time_label = QLabel("00:00.00")
        self._time_label.setStyleSheet("color:#7ec8e3; font:11px Consolas; padding:0 8px;")
        tb.addWidget(self._time_label)

        layout.addWidget(tb)

        # ─── 그래픽스 ───
        self._scene = QGraphicsScene(self)
        self._scene._owner = self  # 클립에서 접근용
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.Antialiasing)
        self._view.setRenderHint(QPainter.SmoothPixmapTransform)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._view.setStyleSheet("QGraphicsView{background:#0d1117;border:none;}")
        self._view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._view.setDragMode(QGraphicsView.NoDrag)
        self._view.mousePressEvent = self._view_mouse_press
        self._view.wheelEvent = self._view_wheel

        layout.addWidget(self._view)

    # ─── Project ───
    def set_project(self, project):
        self._project = project
        self._rebuild()

    def set_playhead(self, t: float):
        self._playhead_time = max(0, t)
        self._draw_playhead()
        m = int(t) // 60
        s = t - m * 60
        self._time_label.setText(f"{m:02d}:{s:05.2f}")

    # ─── Rebuild Scene ───
    def _rebuild(self):
        self._scene.clear()
        self._clip_items.clear()
        self._playhead_line = None
        self._playhead_tri = None
        if not self._project:
            return

        total = max(self._project.total_duration + 10, 30)
        n_tracks = max(len(self._project.tracks), 1)
        sw = HEADER_W + total * self._pps + 200
        sh = RULER_H + n_tracks * TRACK_H + 20
        self._scene.setSceneRect(0, 0, sw, sh)

        # 룰러
        self._scene.addRect(0, 0, sw, RULER_H, Qt.NoPen, QBrush(QColor("#161b22")))
        for sec in range(int(total) + 1):
            x = HEADER_W + sec * self._pps
            if sec % 10 == 0:
                self._scene.addLine(x, 0, x, RULER_H, QPen(QColor("#7ec8e3"), 1))
                t = self._scene.addText(f"{sec//60}:{sec%60:02d}", QFont("Consolas", 7))
                t.setDefaultTextColor(QColor("#7ec8e3"))
                t.setPos(x + 2, 1)
            elif sec % 5 == 0:
                self._scene.addLine(x, RULER_H - 12, x, RULER_H, QPen(QColor("#4a6fa5"), 1))
                t = self._scene.addText(f"{sec//60}:{sec%60:02d}", QFont("Consolas", 6))
                t.setDefaultTextColor(QColor("#4a6fa5"))
                t.setPos(x + 2, 6)
            else:
                self._scene.addLine(x, RULER_H - 6, x, RULER_H, QPen(QColor("#30363d"), 1))

        # 트랙 레인 + 헤더
        for i, track in enumerate(self._project.tracks):
            y = RULER_H + i * TRACK_H
            bg = "#0d1117" if i % 2 == 0 else "#111820"
            self._scene.addRect(HEADER_W, y, sw - HEADER_W, TRACK_H, Qt.NoPen, QBrush(QColor(bg)))
            # 그리드 라인
            self._scene.addLine(HEADER_W, y + TRACK_H, sw, y + TRACK_H, QPen(QColor("#1a2233"), 1))
            # 헤더
            hdr = TrackHeader(track, i, sw, owner=self)
            self._scene.addItem(hdr)

            # 클립
            for clip in track.clips:
                ci = ClipItem(clip, i, self._pps)
                self._scene.addItem(ci)
                self._clip_items.append(ci)

        self._draw_playhead()
        # selectionChanged 중복 방지 (disconnect 후 재연결)
        try:
            self._scene.selectionChanged.disconnect(self._on_selection)
        except RuntimeError:
            pass
        self._scene.selectionChanged.connect(self._on_selection)
        # 뷰가 헤더 영역을 보여주도록 왼쪽으로 스크롤
        from PySide6.QtCore import QTimer as _QT; _QT.singleShot(50, lambda: self._view.horizontalScrollBar().setValue(0))

    def _draw_playhead(self):
        if self._playhead_line:
            self._scene.removeItem(self._playhead_line)
        if self._playhead_tri:
            self._scene.removeItem(self._playhead_tri)

        x = HEADER_W + self._playhead_time * self._pps
        n = len(self._project.tracks) if self._project else 1
        h = RULER_H + n * TRACK_H

        self._playhead_line = self._scene.addLine(x, RULER_H, x, h, QPen(QColor(PLAYHEAD_COLOR), 2))
        self._playhead_line.setZValue(100)

        # 삼각형
        tri = QPolygonF([QPointF(x - 6, 0), QPointF(x + 6, 0), QPointF(x, RULER_H - 2)])
        self._playhead_tri = self._scene.addPolygon(tri, Qt.NoPen, QBrush(QColor(PLAYHEAD_COLOR)))
        self._playhead_tri.setZValue(100)

    # ─── Tool Management ───
    def _set_tool(self, tool):
        self._tool = tool
        for btn in self._tool_buttons:
            btn.setChecked(False)
        {"select": self._btn_select, "cut": self._btn_cut,
         "trim": self._btn_trim, "ripple": self._btn_ripple}[tool].setChecked(True)

    def _toggle_snap(self):
        self._snap_enabled = self._btn_snap.isChecked()

    # ─── Mouse on View (클릭→플레이헤드 이동, Blade 도구) ───
    def _view_mouse_press(self, e):
        pos = self._view.mapToScene(e.pos())
        if pos.y() < RULER_H and pos.x() >= HEADER_W:
            # 룰러 클릭 → 플레이헤드 이동
            t = (pos.x() - HEADER_W) / self._pps
            self.set_playhead(max(0, t))
            self.time_changed.emit(self._playhead_time)
            return

        if self._tool == "cut":
            # Blade 도구: 클릭 위치에서 클립 분할
            item = self._scene.itemAt(pos, self._view.transform())
            if isinstance(item, ClipItem):
                t = (pos.x() - HEADER_W) / self._pps
                self._split_clip_at(item, t)
                return
            elif isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), ClipItem):
                t = (pos.x() - HEADER_W) / self._pps
                self._split_clip_at(item.parentItem(), t)
                return

        # 기본: 선택 모드
        QGraphicsView.mousePressEvent(self._view, e)

    def _view_wheel(self, e: QWheelEvent):
        if e.modifiers() & Qt.ControlModifier:
            delta = e.angleDelta().y()
            new_pps = self._pps + (5 if delta > 0 else -5)
            new_pps = max(MIN_PPS, min(MAX_PPS, new_pps))
            self._zoom_slider.setValue(new_pps)
        else:
            QGraphicsView.wheelEvent(self._view, e)

    # ─── Snap ───
    def _snap_clip(self, ci: ClipItem):
        if not self._snap_enabled:
            return
        edges = [ci.clip.start_frame, ci.clip.start_frame + ci.clip.duration]
        targets = []
        for other in self._clip_items:
            if other is ci:
                continue
            targets.append(other.clip.start_frame)
            targets.append(other.clip.start_frame + other.clip.duration)
        targets.append(self._playhead_time)

        for edge_idx, edge in enumerate(edges):
            for tgt in targets:
                if abs(edge - tgt) * self._pps < SNAP_PX:
                    delta = tgt - edge
                    ci.clip.start_frame += delta
                    ci.refresh(self._pps)
                    return

    # ─── Split ───
    def _split_clip_at(self, ci: ClipItem, t: float):
        clip = ci.clip
        if not (clip.start_frame < t < clip.start_frame + clip.duration):
            return
        new_dur = t - clip.start_frame
        remaining = clip.duration - new_dur
        clip.duration = new_dur

        new_clip = Clip(
            clip_id=uuid.uuid4().hex[:8], name=clip.name + "_B",
            file_path=clip.file_path, start_frame=t, duration=remaining,
            clip_type=clip.clip_type, volume=clip.volume, opacity=clip.opacity,
            text_content=clip.text_content, text_style=clip.text_style.copy(),
            metadata=clip.metadata.copy(),
        )
        if self._project:
            track = self._project.get_track(clip.track_id)
            if track:
                track.add_clip(new_clip)
        self._rebuild()

    def _split_at_playhead(self, ci: ClipItem):
        self._split_clip_at(ci, self._playhead_time)

    # ─── Duplicate ───
    def _duplicate_clip(self, ci: ClipItem):
        clip = ci.clip
        new_clip = Clip(
            clip_id=uuid.uuid4().hex[:8], name=clip.name + "_copy",
            file_path=clip.file_path,
            start_frame=clip.start_frame + clip.duration + 0.1,
            duration=clip.duration, clip_type=clip.clip_type,
            volume=clip.volume, opacity=clip.opacity,
            text_content=clip.text_content, text_style=clip.text_style.copy(),
            metadata=clip.metadata.copy(),
        )
        if self._project:
            track = self._project.get_track(clip.track_id)
            if track:
                track.add_clip(new_clip)
        self._rebuild()

    def _duplicate_selected(self):
        for item in self._scene.selectedItems():
            if isinstance(item, ClipItem):
                self._duplicate_clip(item)
                return

    # ─── Delete ───
    def _delete_clip_item(self, ci: ClipItem):
        if self._project:
            for track in self._project.tracks:
                track.remove_clip(ci.clip.clip_id)
        self._rebuild()

    def _delete_selected(self):
        items = [i for i in self._scene.selectedItems() if isinstance(i, ClipItem)]
        if not items or not self._project:
            return
        for ci in items:
            for track in self._project.tracks:
                track.remove_clip(ci.clip.clip_id)
        self._rebuild()

    # ─── Ripple Delete ───
    def _ripple_delete(self, ci: ClipItem):
        clip = ci.clip
        gap_start = clip.start_frame
        gap_dur = clip.duration
        track_id = clip.track_id

        if self._project:
            track = self._project.get_track(track_id)
            if track:
                track.remove_clip(clip.clip_id)
                for c in track.clips:
                    if c.start_frame >= gap_start:
                        c.start_frame = max(0, c.start_frame - gap_dur)
        self._rebuild()

    # ─── Group ───
    def _group_selected(self):
        items = [i for i in self._scene.selectedItems() if isinstance(i, ClipItem)]
        if len(items) < 2:
            return
        gid = uuid.uuid4().hex[:6]
        cids = [ci.clip.clip_id for ci in items]
        self._groups[gid] = cids
        for ci in items:
            ci.group_id = gid
            # 그룹 표시 — 테두리 점선
            ci.setPen(QPen(QColor("#2ecc71"), 2, Qt.DashLine))

    def _ungroup(self, ci: ClipItem):
        if ci.group_id and ci.group_id in self._groups:
            del self._groups[ci.group_id]
            for item in self._clip_items:
                if item.group_id == ci.group_id:
                    item.group_id = None
                    item.setPen(QPen(QColor("#0d1117"), 1))

    # ─── Keyframe ───
    def _add_keyframe_to_clip(self, ci: ClipItem):
        # 플레이헤드 위치에 키프레임 마커 추가
        t = self._playhead_time
        clip = ci.clip
        if clip.start_frame <= t <= clip.start_frame + clip.duration:
            kf_x = HEADER_W + t * self._pps
            kf_y = RULER_H + ci.track_idx * TRACK_H + TRACK_H - 10
            diamond = QPolygonF([
                QPointF(kf_x, kf_y - 5), QPointF(kf_x + 5, kf_y),
                QPointF(kf_x, kf_y + 5), QPointF(kf_x - 5, kf_y),
            ])
            item = self._scene.addPolygon(diamond, Qt.NoPen, QBrush(QColor("#f1c40f")))
            item.setZValue(50)
            ci._kf_diamonds.append(item)
            # 메타데이터에도 기록
            kfs = clip.metadata.get("keyframes", [])
            kfs.append({"time": t - clip.start_frame, "type": "user"})
            clip.metadata["keyframes"] = kfs

    def _add_keyframe(self):
        for item in self._scene.selectedItems():
            if isinstance(item, ClipItem):
                self._add_keyframe_to_clip(item)
                return

    # ─── Zoom ───
    def _on_zoom(self, val):
        self._pps = val
        self._rebuild()

    def _zoom_in(self):
        self._zoom_slider.setValue(min(self._pps + 20, MAX_PPS))

    def _zoom_out(self):
        self._zoom_slider.setValue(max(self._pps - 20, MIN_PPS))

    # ─── Selection ───
    def _on_selection(self):
        for item in self._scene.selectedItems():
            if isinstance(item, ClipItem):
                self.clip_selected.emit(item.clip.clip_id)
                return

    # ─── Public API (menu에서 호출) ───
    def split_clip(self):
        for item in self._scene.selectedItems():
            if isinstance(item, ClipItem):
                self._split_at_playhead(item)
                return

    def delete_clip(self):
        self._delete_selected()
