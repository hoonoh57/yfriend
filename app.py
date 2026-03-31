"""yFriend Video Editor - Application Entry Point"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("yFriend Video Editor")
    app.setOrganizationName("yFriend")

    # 기본 폰트
    font = QFont("Malgun Gothic", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    # 명령줄 인자로 프로젝트 폴더가 주어졌으면 자동 로드
    if len(sys.argv) > 1:
        from pathlib import Path
        folder = Path(sys.argv[1])
        if folder.is_dir():
            from core.project_model import ProjectModel
            try:
                project = ProjectModel.from_yfriend_project(folder)
                window._project = project
                window._apply_project()
                window._media_browser.set_project_dir(folder)
            except Exception as e:
                print(f"[WARN] Could not auto-load project: {e}")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
