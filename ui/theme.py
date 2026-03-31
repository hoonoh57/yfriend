"""테마 + QSS — v0.2 전문가 에디터 스타일"""

DARK_THEME = {
    "bg_primary": "#0d1117",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#21262d",
    "bg_surface": "#1a1f29",
    "accent": "#4361ee",
    "accent_hover": "#5a7bff",
    "accent_dim": "#4361ee44",
    "text_primary": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_dim": "#484f58",
    "border": "#30363d",
    "border_active": "#4361ee",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "info": "#7ec8e3",
    "video_clip": "#4361ee",
    "audio_clip": "#2ecc71",
    "text_clip": "#f39c12",
    "bgm_clip": "#9b59b6",
    "playhead": "#ff6b6b",
    "ruler_bg": "#161b22",
    "lane_odd": "#0d1117",
    "lane_even": "#111820",
    "header_bg": "#161b22",
}

MAIN_QSS = """
* { font-family: 'Segoe UI', 'Malgun Gothic', sans-serif; }
QMainWindow { background-color: #0d1117; }

/* ─── Menu ─── */
QMenuBar { background: #161b22; color: #e6edf3; font-size: 12px; padding: 2px 0; border-bottom: 1px solid #30363d; }
QMenuBar::item { padding: 6px 12px; border-radius: 4px; margin: 1px 2px; }
QMenuBar::item:selected { background: #4361ee; }
QMenu { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 12px; border-radius: 3px; }
QMenu::item:selected { background: #4361ee; }
QMenu::separator { height: 1px; background: #30363d; margin: 4px 8px; }

/* ─── Toolbar ─── */
QToolBar { background: #161b22; border: none; spacing: 2px; padding: 2px 4px; border-bottom: 1px solid #30363d; }
QToolBar::separator { width: 1px; background: #30363d; margin: 4px 6px; }
QToolButton { color: #e6edf3; background: transparent; border: 1px solid transparent; padding: 5px; border-radius: 5px; min-width: 28px; min-height: 28px; }
QToolButton:hover { background: #4361ee33; border-color: #4361ee55; }
QToolButton:pressed { background: #4361ee66; }
QToolButton:checked { background: #4361ee44; border-color: #4361ee; }
QToolButton[text]:!icon { font-size: 11px; padding: 5px 10px; }

/* ─── Dock ─── */
QDockWidget { color: #e6edf3; font-weight: 600; }
QDockWidget::title { background: #161b22; padding: 7px 10px; border-bottom: 1px solid #30363d; }

/* ─── Lists/Trees ─── */
QTreeWidget, QListWidget { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; alternate-background-color: #111820; font-size: 11px; }
QTreeWidget::item, QListWidget::item { padding: 3px 4px; border-radius: 3px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #4361ee; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #21262d; }
QHeaderView::section { background: #161b22; color: #8b949e; border: none; border-right: 1px solid #30363d; padding: 4px 8px; font-size: 11px; }

/* ─── Inputs ─── */
QLabel { color: #e6edf3; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 5px; padding: 5px 8px; selection-background-color: #4361ee; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #4361ee; }
QComboBox { background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 5px; padding: 5px 10px; min-height: 22px; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #161b22; color: #e6edf3; border: 1px solid #30363d; selection-background-color: #4361ee; }

/* ─── Buttons ─── */
QPushButton { background: #4361ee; color: #fff; border: none; border-radius: 6px; padding: 7px 16px; font-weight: 600; font-size: 12px; }
QPushButton:hover { background: #5a7bff; }
QPushButton:pressed { background: #3350cc; }
QPushButton:disabled { background: #21262d; color: #484f58; }
QPushButton[flat="true"], QPushButton#flatBtn { background: transparent; color: #8b949e; border: 1px solid #30363d; }
QPushButton[flat="true"]:hover, QPushButton#flatBtn:hover { background: #21262d; color: #e6edf3; }

/* ─── Sliders ─── */
QSlider::groove:horizontal { height: 4px; background: #30363d; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; height: 14px; background: #4361ee; border-radius: 7px; margin: -5px 0; }
QSlider::handle:horizontal:hover { background: #5a7bff; }
QSlider::sub-page:horizontal { background: #4361ee; border-radius: 2px; }

/* ─── Scrollbars ─── */
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4361ee; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 0; }
QScrollBar::handle:horizontal { background: #30363d; border-radius: 4px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: #4361ee; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ─── Tabs ─── */
QTabWidget::pane { border: 1px solid #30363d; background: #0d1117; border-radius: 0 0 6px 6px; }
QTabBar::tab { background: #161b22; color: #8b949e; padding: 7px 16px; border: 1px solid #30363d; border-bottom: none; margin-right: 1px; }
QTabBar::tab:selected { background: #0d1117; color: #e6edf3; border-bottom: 2px solid #4361ee; }
QTabBar::tab:hover:!selected { background: #21262d; color: #e6edf3; }

/* ─── GroupBox ─── */
QGroupBox { color: #8b949e; border: 1px solid #30363d; border-radius: 6px; margin-top: 12px; padding-top: 16px; font-weight: 600; font-size: 11px; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 2px 10px; }

/* ─── Splitter ─── */
QSplitter::handle { background: #30363d; }
QSplitter::handle:hover { background: #4361ee; }
QSplitter::handle:horizontal { width: 3px; }
QSplitter::handle:vertical { height: 3px; }

/* ─── StatusBar ─── */
QStatusBar { background: #161b22; color: #8b949e; border-top: 1px solid #30363d; font-size: 11px; padding: 2px 8px; }
QStatusBar::item { border: none; }

/* ─── Progress ─── */
QProgressBar { background: #21262d; border: none; border-radius: 4px; text-align: center; color: #e6edf3; height: 6px; }
QProgressBar::chunk { background: #4361ee; border-radius: 4px; }

/* ─── Tooltip ─── */
QToolTip { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; font-size: 11px; }
"""
