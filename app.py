"""yFriend Video Editor — Entry Point v0.2"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("yFriend Video Editor")
    app.setOrganizationName("yFriend")
    app.setFont(QFont("Segoe UI", 10))

    win = MainWindow()
    win.show()

    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
        if folder.is_dir():
            from core.project_model import ProjectModel
            try:
                proj = ProjectModel.from_yfriend_project(folder)
                win._project = proj
                win._apply()
                win._media.set_project_dir(folder)
            except Exception as e:
                print(f"[WARN] {e}")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
