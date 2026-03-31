"""내보내기 다이얼로그"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QLabel, QPushButton, QProgressBar, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal


class ExportDialog(QDialog):
    export_requested = Signal(dict)  # export settings

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Video")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self._resolution = QComboBox()
        self._resolution.addItems(["1920x1080 (Full HD)", "1280x720 (HD)", "3840x2160 (4K)", "1080x1920 (Vertical)"])
        form.addRow("Resolution:", self._resolution)

        self._fps = QSpinBox()
        self._fps.setRange(15, 60)
        self._fps.setValue(25)
        form.addRow("FPS:", self._fps)

        self._codec = QComboBox()
        self._codec.addItems(["H.264 (libx264)", "H.265 (libx265)", "VP9"])
        form.addRow("Codec:", self._codec)

        self._quality = QComboBox()
        self._quality.addItems(["High (CRF 18)", "Medium (CRF 23)", "Low (CRF 28)", "Lossless"])
        self._quality.setCurrentIndex(1)
        form.addRow("Quality:", self._quality)

        self._output = QLineEdit()
        self._output.setPlaceholderText("output.mp4")
        self._btn_browse = QPushButton("Browse...")
        self._btn_browse.clicked.connect(self._browse)
        form.addRow("Output:", self._output)
        form.addRow("", self._btn_browse)

        layout.addLayout(form)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._btn_export = QPushButton("Export")
        self._btn_export.clicked.connect(self._export)
        layout.addWidget(self._btn_export)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "MP4 (*.mp4);;All (*)")
        if path:
            self._output.setText(path)

    def _export(self):
        res = self._resolution.currentText().split("(")[0].strip()
        w, h = res.split("x")
        codec_map = {"H.264 (libx264)": "libx264", "H.265 (libx265)": "libx265", "VP9": "libvpx-vp9"}
        quality_map = {"High (CRF 18)": 18, "Medium (CRF 23)": 23, "Low (CRF 28)": 28, "Lossless": 0}
        settings = {
            "width": int(w),
            "height": int(h),
            "fps": self._fps.value(),
            "codec": codec_map.get(self._codec.currentText(), "libx264"),
            "crf": quality_map.get(self._quality.currentText(), 23),
            "output": self._output.text() or "output.mp4",
        }
        self.export_requested.emit(settings)

    def set_progress(self, value: int):
        self._progress.setValue(value)
