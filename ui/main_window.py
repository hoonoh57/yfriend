"""yFriend Video Editor - 메인 윈도우"""
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QDockWidget, QFileDialog,
    QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox,
    QSplitter, QWidget, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont, QIcon

from ui.theme import DARK_THEME, MAIN_DARK_QSS
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
        self.setMinimumSize(1280, 800)
        self.resize(1600, 960)
        self.setStyleSheet(MAIN_DARK_QSS)

        self._init_menus()
        self._init_toolbars()
        self._init_panels()
        self._init_connections()
        self._init_statusbar()

    # ─── 메뉴 ───
    def _init_menus(self):
        menu_bar = self.menuBar()

        # File
        file_menu = menu_bar.addMenu("File")
        file_menu.addAction(self._make_action("New Project", self._new_project, "Ctrl+N"))
        file_menu.addAction(self._make_action("Open Project...", self._open_project, "Ctrl+O"))
        file_menu.addAction(self._make_action("Open yFriend Output...", self._open_yfriend_output))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Save Project", self._save_project, "Ctrl+S"))
        file_menu.addAction(self._make_action("Save As...", self._save_project_as, "Ctrl+Shift+S"))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Export Video...", self._export_video, "Ctrl+E"))
        file_menu.addSeparator()
        file_menu.addAction(self._make_action("Exit", self.close, "Ctrl+Q"))

        # Edit
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction(self._make_action("Undo", lambda: None, "Ctrl+Z"))
        edit_menu.addAction(self._make_action("Redo", lambda: None, "Ctrl+Y"))
        edit_menu.addSeparator()
        edit_menu.addAction(self._make_action("Split Clip", self._timeline.split_clip if hasattr(self, '_timeline') else lambda: None, "Ctrl+B"))
        edit_menu.addAction(self._make_action("Delete Clip", self._timeline.delete_clip if hasattr(self, '_timeline') else lambda: None, "Delete"))

        # View
        view_menu = menu_bar.addMenu("View")
        view_menu.addAction(self._make_action("Toggle Media Browser", self._toggle_media))
        view_menu.addAction(self._make_action("Toggle Properties", self._toggle_properties))

        # AI
        ai_menu = menu_bar.addMenu("AI")
        ai_menu.addAction(self._make_action("Generate Full Video...", self._ai_generate_full))
        ai_menu.addAction(self._make_action("Regenerate Images", self._ai_regen_images))
        ai_menu.addAction(self._make_action("Regenerate Narration", self._ai_regen_narration))
        ai_menu.addAction(self._make_action("Add BGM", self._ai_add_bgm))

        # Help
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction(self._make_action("About", self._show_about))

    # ─── 툴바 ───
    def _init_toolbars(self):
        pass  # 향후 아이콘 기반 툴바 추가

    # ─── 패널 구성 ───
    def _init_panels(self):
        # 중앙: 프리뷰 + 속성 (가로 분할)
        central_splitter = QSplitter(Qt.Vertical)

        # 상단: 미디어 브라우저 | 프리뷰 | 속성
        top_splitter = QSplitter(Qt.Horizontal)

        self._media_browser = MediaBrowser()
        self._media_browser.setMinimumWidth(200)
        top_splitter.addWidget(self._media_browser)

        self._preview = PreviewWidget()
        self._preview.setMinimumSize(480, 300)
        top_splitter.addWidget(self._preview)

        self._properties = PropertiesPanel()
        self._properties.setMinimumWidth(250)
        self._properties.setMaximumWidth(350)
        top_splitter.addWidget(self._properties)

        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 3)
        top_splitter.setStretchFactor(2, 1)

        central_splitter.addWidget(top_splitter)

        # AI 어시스턴트 바
        self._ai_bar = AIAssistantBar()
        central_splitter.addWidget(self._ai_bar)

        # 타임라인
        self._timeline = TimelineWidget()
        self._timeline.setMinimumHeight(200)
        central_splitter.addWidget(self._timeline)

        central_splitter.setStretchFactor(0, 3)
        central_splitter.setStretchFactor(1, 0)
        central_splitter.setStretchFactor(2, 2)

        self.setCentralWidget(central_splitter)

    # ─── 시그널 연결 ───
    def _init_connections(self):
        self._timeline.clip_selected.connect(self._on_clip_selected)
        self._timeline.time_changed.connect(self._preview.set_time)
        self._preview.time_changed.connect(self._timeline.set_playhead)
        self._properties.clip_updated.connect(self._on_clip_updated)
        self._ai_bar.command_submitted.connect(self._on_ai_command)
        self._media_browser.file_double_clicked.connect(self._on_media_add)

    # ─── 상태 바 ───
    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready — Open a project or create a new one")

    # ─── 유틸리티 ───
    def _make_action(self, text, callback, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        return action

    # ─── File Actions ───
    def _new_project(self):
        self._project = ProjectModel(name="New Project")
        # 기본 트랙 생성
        self._project.add_track(Track(name="Video 1", track_type="video"))
        self._project.add_track(Track(name="Subtitles", track_type="text"))
        self._project.add_track(Track(name="Narration", track_type="audio"))
        self._project.add_track(Track(name="BGM", track_type="bgm"))
        self._apply_project()
        self._statusbar.showMessage("New project created")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "yFriend Project (*.yfp);;JSON (*.json)"
        )
        if path:
            self._project = ProjectModel.load(Path(path))
            self._apply_project()
            self._statusbar.showMessage(f"Opened: {path}")

    def _open_yfriend_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select yFriend Output Folder")
        if folder:
            try:
                self._project = ProjectModel.from_yfriend_project(Path(folder))
                self._apply_project()
                self._media_browser.set_project_dir(Path(folder))
                self._statusbar.showMessage(f"Loaded yFriend output: {folder}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load: {e}")

    def _save_project(self):
        if not self._project:
            return
        if not self._project.project_dir:
            self._save_project_as()
            return
        path = Path(self._project.project_dir) / "project.yfp"
        self._project.save(path)
        self._statusbar.showMessage(f"Saved: {path}")

    def _save_project_as(self):
        if not self._project:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "yFriend Project (*.yfp)")
        if path:
            self._project.save(Path(path))
            self._statusbar.showMessage(f"Saved: {path}")

    def _export_video(self):
        dlg = ExportDialog(self)
        dlg.export_requested.connect(self._do_export)
        dlg.exec()

    def _do_export(self, settings: dict):
        self._statusbar.showMessage(f"Exporting: {settings}")
        # TODO: FFmpeg 렌더링 로직 연결

    # ─── View Toggles ───
    def _toggle_media(self):
        self._media_browser.setVisible(not self._media_browser.isVisible())

    def _toggle_properties(self):
        self._properties.setVisible(not self._properties.isVisible())

    # ─── AI Actions ───
    def _ai_generate_full(self):
        self._statusbar.showMessage("AI: Generating full video...")

    def _ai_regen_images(self):
        self._statusbar.showMessage("AI: Regenerating images...")

    def _ai_regen_narration(self):
        self._statusbar.showMessage("AI: Regenerating narration...")

    def _ai_add_bgm(self):
        self._statusbar.showMessage("AI: Adding background music...")

    def _on_ai_command(self, command: str):
        self._statusbar.showMessage(f"AI Command: {command}")
        # TODO: core/ai_command_parser.py로 파싱 후 실행

    # ─── Clip Selection ───
    def _on_clip_selected(self, clip_id: str):
        if not self._project:
            return
        clip = self._project.get_clip(clip_id)
        if clip:
            self._properties.set_clip(clip)

    def _on_clip_updated(self, clip_id: str, changes: dict):
        if not self._project:
            return
        clip = self._project.get_clip(clip_id)
        if clip:
            for k, v in changes.items():
                if hasattr(clip, k):
                    setattr(clip, k, v)
            self._timeline._rebuild()
            self._statusbar.showMessage(f"Clip {clip_id} updated")

    def _on_media_add(self, path: str):
        self._statusbar.showMessage(f"Add to timeline: {path}")
        # TODO: 파일 타입 감지 → 적절한 트랙에 클립 추가

    # ─── 프로젝트 적용 ───
    def _apply_project(self):
        if not self._project:
            return
        self._timeline.set_project(self._project)
        self._preview.set_project(self._project)
        self.setWindowTitle(f"yFriend Video Editor — {self._project.name}")

    # ─── About ───
    def _show_about(self):
        QMessageBox.about(
            self,
            "About yFriend Video Editor",
            "yFriend Video Editor v0.1\n\n"
            "AI-powered video creation & editing\n"
            "Multi-track timeline editor with natural language control\n\n"
            "License: MIT\n"
            "UI: PySide6 (LGPL)\n"
        )
