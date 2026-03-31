"""미디어 브라우저 v0.2 — 파일 필터링, 드래그 지원"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


# 표시할 확장자
MEDIA_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".ogg", ".mp4", ".avi", ".mkv"}
SKIP_NAMES = {"concat_list.txt", ".gitkeep"}


class MediaBrowser(QWidget):
    file_selected = Signal(str)
    file_double_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_dir = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()

        # Project
        self._proj_tree = QTreeWidget()
        self._proj_tree.setHeaderLabels(["Name", "Type"])
        self._proj_tree.setAlternatingRowColors(True)
        self._proj_tree.setColumnWidth(0, 160)
        self._proj_tree.itemClicked.connect(lambda i, c: self._emit(i, "clicked"))
        self._proj_tree.itemDoubleClicked.connect(lambda i, c: self._emit(i, "dbl"))
        self._tabs.addTab(self._proj_tree, "Project")

        # Assets
        self._asset_tree = QTreeWidget()
        self._asset_tree.setHeaderLabels(["Name", "Type"])
        self._asset_tree.setAlternatingRowColors(True)
        self._asset_tree.itemDoubleClicked.connect(lambda i, c: self._emit(i, "dbl"))
        self._tabs.addTab(self._asset_tree, "Assets")

        # BGM
        self._bgm_tree = QTreeWidget()
        self._bgm_tree.setHeaderLabels(["Name", "Genre"])
        self._bgm_tree.setAlternatingRowColors(True)
        self._bgm_tree.itemDoubleClicked.connect(lambda i, c: self._emit(i, "dbl"))
        self._tabs.addTab(self._bgm_tree, "BGM")

        layout.addWidget(self._tabs)

        # 하단
        btns = QHBoxLayout()
        btns.setContentsMargins(4, 4, 4, 4)
        imp = QPushButton("+ Import")
        imp.setObjectName("flatBtn")
        imp.clicked.connect(self._import)
        ref = QPushButton("Refresh")
        ref.setObjectName("flatBtn")
        ref.clicked.connect(self._refresh)
        btns.addWidget(imp)
        btns.addWidget(ref)
        layout.addLayout(btns)

    def set_project_dir(self, d: Path):
        self._project_dir = d
        self._refresh()

    def _refresh(self):
        if not self._project_dir:
            return
        pd = Path(self._project_dir)
        self._proj_tree.clear()

        # 주요 미디어 폴더만 표시
        folders = {
            "Images": pd / "02_visual",
            "Narration": pd / "03_voice",
            "Final": pd / "06_assembly",
        }
        for label, folder in folders.items():
            if not folder.exists():
                continue
            parent = QTreeWidgetItem([label, ""])
            parent.setForeground(0, QColor("#8b949e"))
            count = 0
            for f in sorted(folder.iterdir()):
                if not f.is_file() or f.name in SKIP_NAMES:
                    continue
                ext = f.suffix.lower()
                if ext not in MEDIA_EXTS and ext != ".json":
                    continue
                ftype = "image" if ext in (".png",".jpg",".jpeg",".webp") else \
                        "audio" if ext in (".mp3",".wav",".ogg") else \
                        "video" if ext in (".mp4",".avi",".mkv") else "data"
                item = QTreeWidgetItem([f.name, ftype])
                item.setData(0, Qt.UserRole, str(f))
                # 타입별 색상
                colors = {"image":"#4361ee","audio":"#2ecc71","video":"#9b59b6","data":"#8b949e"}
                item.setForeground(1, QColor(colors.get(ftype, "#888")))
                parent.addChild(item)
                count += 1
            parent.setText(0, f"{label} ({count})")
            self._proj_tree.addTopLevelItem(parent)

        self._proj_tree.expandAll()

        # BGM
        self._bgm_tree.clear()
        bgm_dir = pd.parent.parent / "assets" / "bgm" if pd.parent.parent.exists() else None
        if bgm_dir and bgm_dir.exists():
            for f in sorted(bgm_dir.glob("*.mp3")):
                genre = f.stem.rsplit("_", 1)[0] if "_" in f.stem else "misc"
                item = QTreeWidgetItem([f.stem, genre])
                item.setData(0, Qt.UserRole, str(f))
                self._bgm_tree.addTopLevelItem(item)

    def _import(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import", "", "Media (*.png *.jpg *.mp3 *.wav *.mp4);;All (*)")
        for f in files:
            self.file_double_clicked.emit(f)

    def _emit(self, item, kind):
        path = item.data(0, Qt.UserRole)
        if path:
            if kind == "dbl":
                self.file_double_clicked.emit(path)
            else:
                self.file_selected.emit(path)
