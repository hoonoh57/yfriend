"""프리뷰 위젯 v0.3 — 오디오 싱크 재생, 자막 WYSIWYG, 가이드라인"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton,
    QSlider, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QSize
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QBrush
from ui.icons import icon_play, icon_pause, icon_stop, icon_skip_back, icon_skip_forward
from ui.audio_player import AudioMixer


class PreviewCanvas(QLabel):
    """16:9 비율 캔버스"""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background: #000; border-radius: 4px;")
        self._pixmap = None
        self._show_guides = False
        self._show_safe = False
        self._overlays = []

    def set_image(self, pix: QPixmap):
        self._pixmap = pix
        self.update()

    def set_guides(self, v): self._show_guides = v; self.update()
    def set_safe_area(self, v): self._show_safe = v; self.update()
    def set_overlay_texts(self, t): self._overlays = t; self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.Antialiasing)
            p.fillRect(self.rect(), QColor("#000"))
            if self._pixmap and not self._pixmap.isNull():
                t = self._fit()
                tx, ty, tw, th = int(t.x()), int(t.y()), int(t.width()), int(t.height())
                p.drawPixmap(tx, ty, tw, th, self._pixmap)
                if self._show_guides:
                    p.setPen(QPen(QColor("#ffffff55"), 1, Qt.DashLine))
                    for i in range(1, 3):
                        p.drawLine(tx + tw*i//3, ty, tx + tw*i//3, ty+th)
                        p.drawLine(tx, ty + th*i//3, tx+tw, ty + th*i//3)
                if self._show_safe:
                    for r, c in [(0.9,"#ffffff33"),(0.8,"#ffffff22")]:
                        p.setPen(QPen(QColor(c), 1, Qt.DashDotLine))
                        rw, rh = int(tw*r), int(th*r)
                        p.drawRect(tx+(tw-rw)//2, ty+(th-rh)//2, rw, rh)
                for o in self._overlays:
                    fs = o.get("font_size", 14)
                    p.setFont(QFont("Malgun Gothic", fs, QFont.Bold))
                    fm = p.fontMetrics()
                    txt = o.get("text","")
                    ow = fm.horizontalAdvance(txt)+20
                    oh = fm.height()+10
                    ox = tx + int(tw * o.get("x",0.5)) - ow//2
                    oy = ty + int(th * o.get("y",0.88)) - oh//2
                    p.setPen(Qt.NoPen); p.setBrush(QColor("#000000bb"))
                    p.drawRoundedRect(ox, oy, ow, oh, 6, 6)
                    p.setPen(QColor(o.get("color","#fff")))
                    p.drawText(ox, oy, ow, oh, Qt.AlignCenter, txt)
            else:
                p.setPen(QColor("#484f58")); p.setFont(QFont("Segoe UI",14))
                p.drawText(self.rect(), Qt.AlignCenter, "No Preview")
        finally:
            p.end()

    def _fit(self):
        w, h = self.width(), self.height()
        ar = 16/9
        if w/h > ar:
            nw = int(h*ar)
            return QRectF((w-nw)/2, 0, nw, h)
        else:
            nh = int(w/ar)
            return QRectF(0, (h-nh)/2, w, nh)


class PreviewWidget(QWidget):
    time_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = 0.0
        self._dur = 0.0
        self._playing = False
        self._seeking = False  # ← 추가
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._project = None
        self._mixer = AudioMixer(self)
        self._init_ui()


    def _init_ui(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        self._canvas = PreviewCanvas()
        lo.addWidget(self._canvas, 1)

        ctrl = QFrame()
        ctrl.setStyleSheet("background:#161b22; border-top:1px solid #30363d;")
        ctrl.setFixedHeight(60)
        cl = QVBoxLayout(ctrl); cl.setContentsMargins(8,2,8,2); cl.setSpacing(1)

        self._seek = QSlider(Qt.Horizontal)
        self._seek.setRange(0, 10000)
        self._seek.sliderPressed.connect(self._seek_start)
        self._seek.sliderMoved.connect(self._on_seek)
        self._seek.sliderReleased.connect(self._seek_end)
        self._seek.setFixedHeight(14)
        cl.addWidget(self._seek)

        row = QHBoxLayout(); row.setSpacing(4)
        self._bbk = self._tb(icon_skip_back(), "5s Back", self._go_bk)
        self._bpl = self._tb(icon_play(), "Play", self._toggle)
        self._bst = self._tb(icon_stop(), "Stop", self._stop)
        self._bfw = self._tb(icon_skip_forward(), "5s Fwd", self._go_fw)
        self._tc = QLabel("00:00.00 / 00:00.00")
        self._tc.setStyleSheet("color:#7ec8e3; font:11px Consolas;")
        row.addStretch()
        for b in [self._bbk, self._bpl, self._bst, self._bfw]: row.addWidget(b)
        row.addStretch(); row.addWidget(self._tc)
        cl.addLayout(row)
        lo.addWidget(ctrl)

    def _tb(self, icon, tip, cb):
        b = QToolButton(); b.setIcon(icon); b.setIconSize(QSize(20,20))
        b.setToolTip(tip); b.clicked.connect(cb); return b

    def set_project(self, proj):
        self._project = proj
        self._dur = proj.total_duration if proj else 0
        self._t = 0
        self._build_audio()
        self._refresh()

    def _build_audio(self):
        """프로젝트의 audio/bgm 트랙에서 오디오 플레이어 구성"""
        self._mixer.clear()
        if not self._project:
            return
        for track in self._project.tracks:
            if track.track_type in ("audio", "bgm"):
                for clip in track.clips:
                    if clip.file_path and Path(clip.file_path).exists():
                        self._mixer.add_track(
                            clip.file_path, clip.start_frame, clip.volume
                        )

    def set_time(self, t):
        self._t = max(0, min(t, self._dur))
        self._mixer.seek(self._t)
        self._refresh()

    def _toggle(self):
        if self._playing:
            self._playing = False
            self._timer.stop()
            self._mixer.pause()
            self._bpl.setIcon(icon_play())
        else:
            self._playing = True
            self._timer.start()
            self._mixer.play_from(self._t)
            self._bpl.setIcon(icon_pause())

    def _stop(self):
        self._playing = False
        self._timer.stop()
        self._mixer.stop()
        self._bpl.setIcon(icon_play())
        self._t = 0
        self.time_changed.emit(0)
        self._refresh()

    def _tick(self):
        self._t += 0.04
        if self._t >= self._dur:
            self._stop(); return
        self.time_changed.emit(self._t)
        self._refresh()

    def _go_bk(self):
        self.set_time(self._t - 5); self.time_changed.emit(self._t)
    def _go_fw(self):
        self.set_time(self._t + 5); self.time_changed.emit(self._t)

    # def _seeking = False
    def _seek_start(self): self._seeking = True
    def _seek_end(self): self._seeking = False
    def _on_seek(self, v):
        if self._dur > 0:
            self.set_time((v/10000)*self._dur)
            self.time_changed.emit(self._t)

    def _refresh(self):
        self._tc.setText(f"{self._fmt(self._t)} / {self._fmt(self._dur)}")
        if self._dur > 0 and not getattr(self, '_seeking', False):
            self._seek.blockSignals(True)
            self._seek.setValue(int((self._t/self._dur)*10000))
            self._seek.blockSignals(False)
        if self._project:
            self._show_frame()

    def _show_frame(self):
        t = self._t
        found = False
        for track in self._project.tracks:
            if track.track_type != "video": continue
            for clip in reversed(track.clips):
                if clip.start_frame <= t < clip.start_frame + clip.duration:
                    p = Path(clip.file_path) if clip.file_path else None
                    if p and p.exists() and p.suffix.lower() in (".png",".jpg",".jpeg",".webp"):
                        pix = QPixmap(str(p))
                        if not pix.isNull():
                            self._canvas.set_image(pix); found = True; break
            if found: break
        if not found:
            self._canvas.set_image(QPixmap())
        self._show_subs(t)

    def _show_subs(self, t):
        txts = []
        for track in self._project.tracks:
            if track.track_type != "text": continue
            for c in track.clips:
                if c.start_frame <= t < c.start_frame + c.duration:
                    txts.append({
                        "text": c.text_content[:80], "x":0.5, "y":0.88,
                        "font_size": c.text_style.get("size",42)//3,
                        "color": c.text_style.get("color","#fff"),
                    })
        self._canvas.set_overlay_texts(txts)

    @staticmethod
    def _fmt(s):
        m = int(s)//60; return f"{m:02d}:{s-m*60:05.2f}"
