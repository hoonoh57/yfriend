"""테마 정의 - 다크/라이트"""

DARK_THEME = {
    "timeLabel_bg": "#1a1a2e",
    "timeLabel_text": "#e0e0e0",
    "ruler_bg": "#16213e",
    "ruler_tick_major": "#7ec8e3",
    "ruler_tick_minor": "#4a6fa5",
    "playhead_color": "#ff6b6b",
    "track_header_bg": "#1a1a2e",
    "track_header_text": "#e0e0e0",
    "track_lane_bg1": "#0f3460",
    "track_lane_bg2": "#162447",
    "track_lane_border": "#1b4965",
    "clip_fill": "#4361ee",
    "clip_fill_selected": "#7b9ef9",
    "clip_border": "#1a1a2e",
    "end_line_color": "#ff6b6b",
    "background_color": "#0a0a1a",
}

LIGHT_THEME = {
    "timeLabel_bg": "#f0f0f5",
    "timeLabel_text": "#2d2d2d",
    "ruler_bg": "#e8e8f0",
    "ruler_tick_major": "#333333",
    "ruler_tick_minor": "#999999",
    "playhead_color": "#e74c3c",
    "track_header_bg": "#dcdce6",
    "track_header_text": "#2d2d2d",
    "track_lane_bg1": "#f5f5fa",
    "track_lane_bg2": "#ebebf0",
    "track_lane_border": "#c0c0d0",
    "clip_fill": "#3498db",
    "clip_fill_selected": "#5dade2",
    "clip_border": "#2c3e50",
    "end_line_color": "#e74c3c",
    "background_color": "#fafafa",
}

MAIN_DARK_QSS = """
QMainWindow { background-color: #0a0a1a; }
QMenuBar { background-color: #1a1a2e; color: #e0e0e0; font-size: 13px; }
QMenuBar::item:selected { background-color: #4361ee; }
QMenu { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #333; }
QMenu::item:selected { background-color: #4361ee; }
QToolBar { background-color: #1a1a2e; border: none; spacing: 4px; }
QToolButton { color: #e0e0e0; background: transparent; border: none; padding: 6px; border-radius: 4px; }
QToolButton:hover { background-color: #4361ee33; }
QToolButton:pressed { background-color: #4361ee66; }
QDockWidget { color: #e0e0e0; titlebar-close-icon: none; }
QDockWidget::title { background-color: #16213e; padding: 6px; font-weight: bold; }
QTreeView, QListView { background-color: #0f0f1f; color: #e0e0e0; border: 1px solid #333; alternate-background-color: #151530; }
QTreeView::item:selected, QListView::item:selected { background-color: #4361ee; }
QLabel { color: #e0e0e0; }
QLineEdit, QTextEdit, QPlainTextEdit { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; padding: 4px; }
QLineEdit:focus { border-color: #4361ee; }
QPushButton { background-color: #4361ee; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; }
QPushButton:hover { background-color: #5a7bff; }
QPushButton:pressed { background-color: #3350cc; }
QPushButton:disabled { background-color: #555; color: #888; }
QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; height: 14px; background: #4361ee; border-radius: 7px; margin: -5px 0; }
QSlider::sub-page:horizontal { background: #4361ee; border-radius: 2px; }
QComboBox { background-color: #1a1a2e; color: #e0e0e0; border: 1px solid #333; border-radius: 4px; padding: 4px 8px; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #1a1a2e; color: #e0e0e0; selection-background-color: #4361ee; }
QStatusBar { background-color: #1a1a2e; color: #aaa; }
QProgressBar { background-color: #1a1a2e; border: 1px solid #333; border-radius: 4px; text-align: center; color: #e0e0e0; }
QProgressBar::chunk { background-color: #4361ee; border-radius: 3px; }
QSplitter::handle { background-color: #333; }
QSplitter::handle:hover { background-color: #4361ee; }
QTabWidget::pane { border: 1px solid #333; background-color: #0f0f1f; }
QTabBar::tab { background-color: #1a1a2e; color: #aaa; padding: 8px 16px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background-color: #4361ee; color: white; }
QScrollBar:vertical { background: #0a0a1a; width: 10px; }
QScrollBar::handle:vertical { background: #333; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4361ee; }
QScrollBar:horizontal { background: #0a0a1a; height: 10px; }
QScrollBar::handle:horizontal { background: #333; border-radius: 5px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #4361ee; }
"""
