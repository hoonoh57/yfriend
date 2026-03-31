"""yFriend Video Editor v0.2 — 메인 윈도우"""
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QSplitter, QWidget, QVBoxLayout,
    QFileDialog, QMessageBox, QToolBar, QStatusBar, QLabel
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont, QKeySequence

from ui.theme import MAIN_QSS
from ui.icons import (
    icon_select, icon_cut, icon_trim, icon_ripple, icon_delete, icon_copy,
    icon_magnet, icon_group, icon_keyframe, icon_zoom_in, icon_zoom_out,
    icon_undo, icon_redo, icon_play, icon_export, icon_ai
)
from ui.timeline_widget import TimelineWidget
from ui.preview_widget import PreviewWidget
from ui.media_browser import MediaBrowser
from ui.properties_panel import PropertiesPanel
from ui.ai_assistant_bar import AIAssistantBar
from ui.export_dialog import ExportDialog
from core.project_model import ProjectModel, Track, Clip


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._project: ProjectModel | None = None
        self.setWindowTitle("yFriend Video Editor")
        self.setMinimumSize(1200, 700)
        self.resize(1600, 960)
        self.setStyleSheet(MAIN_QSS)
        self._init_menus()
        self._init_panels()
        self._init_connections()
        self._init_statusbar()
        self._init_shortcuts()

    def _init_menus(self):
        mb = self.menuBar()

        file_m = mb.addMenu("&File")
        file_m.addAction(self._act("&New Project", self._new_project, "Ctrl+N"))
        file_m.addAction(self._act("&Open Project...", self._open_project, "Ctrl+O"))
        file_m.addAction(self._act("Open yFriend &Output...", self._open_yfriend))
        file_m.addSeparator()
        file_m.addAction(self._act("&Save", self._save, "Ctrl+S"))
        file_m.addAction(self._act("Save &As...", self._save_as, "Ctrl+Shift+S"))
        file_m.addSeparator()
        file_m.addAction(self._act("&Export...", self._export, "Ctrl+E"))
        file_m.addSeparator()
        file_m.addAction(self._act("E&xit", self.close, "Ctrl+Q"))

        edit_m = mb.addMenu("&Edit")
        edit_m.addAction(self._act("&Undo", lambda: None, "Ctrl+Z"))
        edit_m.addAction(self._act("&Redo", lambda: None, "Ctrl+Y"))
        edit_m.addSeparator()
        edit_m.addAction(self._act("&Split Clip", lambda: self._timeline.split_clip(), "Ctrl+B"))
        edit_m.addAction(self._act("&Delete Clip", lambda: self._timeline.delete_clip(), "Delete"))
        edit_m.addAction(self._act("D&uplicate", lambda: self._timeline._duplicate_selected(), "Ctrl+D"))
        edit_m.addAction(self._act("&Group", lambda: self._timeline._group_selected(), "Ctrl+G"))

        view_m = mb.addMenu("&View")
        self._act_guides = self._act("Show &Guides", self._toggle_guides)
        self._act_guides.setCheckable(True)
        self._act_safe = self._act("Show &Safe Area", self._toggle_safe)
        self._act_safe.setCheckable(True)
        view_m.addAction(self._act_guides)
        view_m.addAction(self._act_safe)
        view_m.addSeparator()
        view_m.addAction(self._act("Toggle &Media Browser", self._toggle_media))
        view_m.addAction(self._act("Toggle &Properties", self._toggle_props))

        ai_m = mb.addMenu("&AI")
        ai_m.addAction(self._act("Generate Full &Video...", self._ai_full))
        ai_m.addAction(self._act("Regenerate &Images", self._ai_images))
        ai_m.addAction(self._act("Regenerate &Narration", self._ai_narr))
        ai_m.addAction(self._act("Add &BGM", self._ai_bgm))

        help_m = mb.addMenu("&Help")
        help_m.addAction(self._act("&About", self._about))
        help_m.addAction(self._act("&Keyboard Shortcuts", self._show_shortcuts))

    def _init_panels(self):
        root = QSplitter(Qt.Vertical)

        # 상단: 미디어 | 프리뷰 | 속성
        top = QSplitter(Qt.Horizontal)

        self._media = MediaBrowser()
        self._media.setMinimumWidth(180)
        self._media.setMaximumWidth(300)
        top.addWidget(self._media)

        self._preview = PreviewWidget()
        self._preview.setMinimumSize(400, 250)
        top.addWidget(self._preview)

        self._props = PropertiesPanel()
        self._props.setMinimumWidth(240)
        self._props.setMaximumWidth(320)
        top.addWidget(self._props)

        top.setStretchFactor(0, 1)
        top.setStretchFactor(1, 4)
        top.setStretchFactor(2, 1)
        root.addWidget(top)

        # AI 바
        self._ai_bar = AIAssistantBar()
        root.addWidget(self._ai_bar)

        # 타임라인
        self._timeline = TimelineWidget()
        self._timeline.setMinimumHeight(180)
        root.addWidget(self._timeline)

        root.setStretchFactor(0, 3)
        root.setStretchFactor(1, 0)
        root.setStretchFactor(2, 2)
        self.setCentralWidget(root)

    def _init_connections(self):
        self._timeline.clip_selected.connect(self._on_clip_sel)
        self._timeline.time_changed.connect(self._preview.set_time)
        self._preview.time_changed.connect(self._timeline.set_playhead)
        self._props.clip_updated.connect(self._on_clip_upd)
        self._ai_bar.command_submitted.connect(self._on_ai_cmd)
        self._media.file_selected.connect(lambda p: self._status(f"Selected: {Path(p).name}"))
        self._media.file_double_clicked.connect(self._on_media_add)

    def _init_statusbar(self):
        self._sb = QStatusBar()
        self.setStatusBar(self._sb)
        self._sb.showMessage("Ready")

    def _init_shortcuts(self):
        """키보드 단축키 — 전문 에디터 표준"""
        pass  # 메뉴에서 이미 등록됨

    # ─── Utility ───
    def _act(self, text, cb, shortcut=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(cb)
        return a

    def _status(self, msg):
        self._sb.showMessage(msg, 5000)

    # ─── File ───
    def _new_project(self):
        self._project = ProjectModel(name="New Project")
        self._project.add_track(Track(name="Video 1", track_type="video"))
        self._project.add_track(Track(name="Subtitles", track_type="text"))
        self._project.add_track(Track(name="Narration", track_type="audio"))
        self._project.add_track(Track(name="BGM", track_type="bgm"))
        self._apply()
        self._status("New project created")

    def _open_project(self):
        p, _ = QFileDialog.getOpenFileName(self, "Open", "", "yFriend Project (*.yfp);;JSON (*.json)")
        if p:
            self._project = ProjectModel.load(Path(p))
            self._apply()

    def _open_yfriend(self):
        f = QFileDialog.getExistingDirectory(self, "Select yFriend Output")
        if f:
            try:
                self._project = ProjectModel.from_yfriend_project(Path(f))
                self._apply()
                self._media.set_project_dir(Path(f))
                self._status(f"Loaded: {Path(f).name}")
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _save(self):
        if not self._project or not self._project.project_dir:
            self._save_as()
            return
        p = Path(self._project.project_dir) / "project.yfp"
        self._project.save(p)
        self._status(f"Saved: {p}")

    def _save_as(self):
        if not self._project:
            return
        p, _ = QFileDialog.getSaveFileName(self, "Save As", "", "yFriend Project (*.yfp)")
        if p:
            self._project.save(Path(p))
            self._status(f"Saved: {p}")

    def _export(self):
        dlg = ExportDialog(self)
        dlg.export_requested.connect(lambda s: self._status(f"Exporting: {s}"))
        dlg.exec()

    # ─── View ───
    def _toggle_guides(self):
        self._preview._canvas.set_guides(self._act_guides.isChecked())

    def _toggle_safe(self):
        self._preview._canvas.set_safe_area(self._act_safe.isChecked())

    def _toggle_media(self):
        self._media.setVisible(not self._media.isVisible())

    def _toggle_props(self):
        self._props.setVisible(not self._props.isVisible())

    # ─── AI ───
    def _ai_full(self): self._status("AI: Generating full video...")
    def _ai_images(self): self._status("AI: Regenerating images...")
    def _ai_narr(self): self._status("AI: Regenerating narration...")
    def _ai_bgm(self): self._status("AI: Adding BGM...")

    def _on_ai_cmd(self, cmd):
        self._status(f"AI: {cmd}")

    # ─── Clip ───
    def _on_clip_sel(self, clip_id):
        if self._project:
            c = self._project.get_clip(clip_id)
            if c:
                self._props.set_clip(c)

    def _on_clip_upd(self, clip_id, changes):
        if not self._project:
            return
        c = self._project.get_clip(clip_id)
        if c:
            for k, v in changes.items():
                if hasattr(c, k):
                    setattr(c, k, v)
            self._timeline._rebuild()
            self._status(f"Updated: {c.name}")

    def _on_media_add(self, path):
        self._status(f"Add: {Path(path).name}")

    # ─── Apply ───
    def _apply(self):
        if not self._project:
            return
        self._timeline.set_project(self._project)
        self._preview.set_project(self._project)
        self.setWindowTitle(f"yFriend Video Editor — {self._project.name}")

    # ─── Help ───
    def _about(self):
        QMessageBox.about(self, "About",
            "yFriend Video Editor v0.2\n\n"
            "AI-powered video creation & editing\n"
            "Multi-track NLE with natural language control\n\n"
            "UI: PySide6 (LGPL) | License: MIT")

    def _show_shortcuts(self):
        QMessageBox.information(self, "Shortcuts",
            "V — Select tool\n"
            "B — Blade / Split tool\n"
            "T — Trim tool\n"
            "R — Ripple edit tool\n"
            "S — Toggle snap\n"
            "K — Add keyframe\n"
            "Del — Delete clip\n"
            "Ctrl+D — Duplicate\n"
            "Ctrl+G — Group\n"
            "Ctrl+B — Split at playhead\n"
            "Ctrl+Z / Y — Undo / Redo\n"
            "Ctrl+E — Export\n"
            "Ctrl+Mouse Wheel — Timeline zoom")
