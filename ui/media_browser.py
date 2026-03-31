"""미디어 브라우저 - 프로젝트 파일 및 에셋 탐색"""
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont


class MediaBrowser(QWidget):
    file_selected = Signal(str)       # 파일 경로
    file_double_clicked = Signal(str)  # 파일 더블클릭 → 타임라인에 추가

    def __init__(self, parent=None):
        super().__init__(parent)
        self._project_dir = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 탭: 프로젝트 파일 / 에셋 / BGM
        self._tabs = QTabWidget()

        # 프로젝트 파일 탭
        self._project_tree = QTreeWidget()
        self._project_tree.setHeaderLabels(["Name", "Type", "Duration"])
        self._project_tree.setAlternatingRowColors(True)
        self._project_tree.itemClicked.connect(self._on_item_clicked)
        self._project_tree.itemDoubleClicked.connect(self._on_item_dbl_clicked)
        self._tabs.addTab(self._project_tree, "Project")

        # 에셋 탭
        self._asset_tree = QTreeWidget()
        self._asset_tree.setHeaderLabels(["Name", "Type"])
        self._asset_tree.setAlternatingRowColors(True)
        self._asset_tree.itemDoubleClicked.connect(self._on_item_dbl_clicked)
        self._tabs.addTab(self._asset_tree, "Assets")

        # BGM 탭
        self._bgm_tree = QTreeWidget()
        self._bgm_tree.setHeaderLabels(["Name", "Genre"])
        self._bgm_tree.setAlternatingRowColors(True)
        self._bgm_tree.itemDoubleClicked.connect(self._on_item_dbl_clicked)
        self._tabs.addTab(self._bgm_tree, "BGM")

        layout.addWidget(self._tabs)

        # 하단 버튼
        btn_layout = QHBoxLayout()
        self._btn_import = QPushButton("+ Import")
        self._btn_import.clicked.connect(self._import_files)
        self._btn_refresh = QPushButton("Refresh")
        self._btn_refresh.clicked.connect(self._refresh)
        btn_layout.addWidget(self._btn_import)
        btn_layout.addWidget(self._btn_refresh)
        layout.addLayout(btn_layout)

    def set_project_dir(self, project_dir: Path):
        self._project_dir = project_dir
        self._refresh()

    def _refresh(self):
        if not self._project_dir:
            return
        self._project_tree.clear()
        pd = Path(self._project_dir)

        # 스크립트
        self._add_folder(self._project_tree, pd / "01_script", "Scripts")
        self._add_folder(self._project_tree, pd / "02_visual", "Images")
        self._add_folder(self._project_tree, pd / "03_voice", "Narration")
        self._add_folder(self._project_tree, pd / "06_assembly", "Assembly")

        self._project_tree.expandAll()

        # BGM
        self._bgm_tree.clear()
        bgm_dir = pd.parent.parent / "assets" / "bgm"
        if bgm_dir.exists():
            for f in sorted(bgm_dir.glob("*.mp3")):
                item = QTreeWidgetItem([f.stem, f.stem.split("_")[0] if "_" in f.stem else "misc"])
                item.setData(0, Qt.UserRole, str(f))
                self._bgm_tree.addTopLevelItem(item)

    def _add_folder(self, tree, folder: Path, label: str):
        if not folder.exists():
            return
        parent = QTreeWidgetItem([label, "folder", ""])
        for f in sorted(folder.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                ext = f.suffix.lower()
                ftype = "image" if ext in (".png", ".jpg", ".jpeg", ".webp") else \
                        "audio" if ext in (".mp3", ".wav", ".ogg") else \
                        "video" if ext in (".mp4", ".avi", ".mkv") else \
                        "data" if ext == ".json" else "other"
                item = QTreeWidgetItem([f.name, ftype, ""])
                item.setData(0, Qt.UserRole, str(f))
                parent.addChild(item)
        tree.addTopLevelItem(parent)

    def _import_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Files", "",
            "Media Files (*.png *.jpg *.jpeg *.mp3 *.wav *.mp4 *.avi);;All Files (*)"
        )
        for f in files:
            self.file_double_clicked.emit(f)

    def _on_item_clicked(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path:
            self.file_selected.emit(path)

    def _on_item_dbl_clicked(self, item, col):
        path = item.data(0, Qt.UserRole)
        if path:
            self.file_double_clicked.emit(path)
