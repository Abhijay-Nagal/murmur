"""Colors, fonts and the app-wide Qt stylesheet.

An evening palette: an espresso sidebar, warm paper for the pages and a burnt-sienna
accent, like lamplight at dusk. Headings use Instrument Serif (bundled, OFL licensed).
"""
from ..paths import ASSETS

CHEVRON = (ASSETS / "chevron-down.svg").as_posix()
FONTS_DIR = ASSETS / "fonts"

# ---- paper (pages) ----
BG = "#f4ece0"
CARD = "#fbf6ee"
CARD_HOVER = "#efe3d2"
BORDER = "#e2d3bf"
INPUT = "#fffbf5"
TEXT = "#2e2119"
MUTED = "#76604d"
FAINT = "#8c7662"
TOGGLE_OFF = "#d3c0a8"

# ---- espresso (sidebar, overlay) ----
SIDEBAR = "#2a1d15"
SIDE_HOVER = "#3a2a1f"
SIDE_TEXT = "#f3e6d3"
SIDE_MUTED = "#b8a28a"
SIDE_BORDER = "rgba(243, 230, 211, 0.12)"

# ---- accents ----
ACCENT = "#b5552b"
ACCENT_HOVER = "#9c4621"
ACCENT_SOFT = "rgba(181, 85, 43, 0.12)"
AMBER = "#e0a15a"
SUCCESS = "#5f7d47"
WARNING = "#b97a1e"
DANGER = "#b03a2e"
RECORD = "#c8432e"

STATE_COLORS = {
    "ready": SUCCESS,
    "recording": RECORD,
    "hands_free": RECORD,
    "processing": WARNING,
    "loading": MUTED,
    "paused": FAINT,
    "error": DANGER,
}

FONT = "Segoe UI Variable Text, Segoe UI, sans-serif"
SERIF = "Instrument Serif, Georgia, serif"


def load_fonts():
    """Register the bundled fonts. Call after the QApplication exists, before styling."""
    from PySide6.QtGui import QFontDatabase

    for f in FONTS_DIR.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))


STYLESHEET = f"""
* {{
    font-family: {FONT};
    font-size: 13px;
    color: {TEXT};
    outline: none;
}}
QMainWindow, #Content {{ background: {BG}; }}
QToolTip {{
    background: {SIDEBAR}; color: {SIDE_TEXT}; border: none; padding: 6px 8px; border-radius: 4px;
}}

/* ---------- sidebar ---------- */
#Sidebar {{ background: {SIDEBAR}; }}
#Sidebar QLabel {{ color: {SIDE_TEXT}; }}
#Brand {{ font-family: {SERIF}; font-size: 30px; color: {SIDE_TEXT}; }}
#BrandTag {{ font-family: {SERIF}; font-style: italic; font-size: 15px; color: {SIDE_MUTED}; }}
#HeroCard #BrandTag {{ font-size: 20px; color: {MUTED}; }}
#NavButton {{
    text-align: left; padding: 10px 12px 10px 13px; border: none; border-left: 3px solid transparent;
    border-radius: 0; color: {SIDE_MUTED}; font-size: 13px; background: transparent;
}}
#NavButton:hover {{ color: {SIDE_TEXT}; background: {SIDE_HOVER}; }}
#NavButton:checked {{ color: {SIDE_TEXT}; border-left-color: {AMBER}; background: {SIDE_HOVER}; }}
#SidebarStatus {{ background: transparent; border-top: 1px solid {SIDE_BORDER}; }}
#Sidebar #SideStatus {{ font-size: 12px; font-weight: 600; color: {SIDE_TEXT}; }}
#Sidebar #Faint {{ color: {SIDE_MUTED}; }}
#Sidebar QToolButton#Ghost:hover {{ background: {SIDE_HOVER}; }}
#Sidebar QToolButton#Ghost:checked {{ background: {SIDE_HOVER}; }}

/* ---------- typography ---------- */
#PageTitle {{ font-family: {SERIF}; font-size: 40px; }}
#PageSubtitle {{ color: {MUTED}; font-size: 13px; }}
#CardTitle {{ font-family: {SERIF}; font-size: 22px; }}
#SectionTitle {{ font-size: 13px; font-weight: 600; }}
#Muted {{ color: {MUTED}; }}
#Faint {{ color: {FAINT}; font-size: 12px; }}
#Eyebrow {{ color: {FAINT}; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; }}
#StatValue {{ font-family: {SERIF}; font-size: 38px; }}
#StatLabel {{ color: {MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; }}
#HeroTitle {{ font-family: {SERIF}; font-style: italic; font-size: 28px; }}

/* ---------- cards ---------- */
#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 6px; }}
#HeroCard {{
    border: 1px solid #e8c9ad; border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fbeee0, stop:0.6 #f7e0c9, stop:1 #f1cfb2);
}}
#Row {{ border-top: 1px solid {BORDER}; }}
#StatCell {{ border-left: 1px solid {BORDER}; }}
#Keycap {{
    background: {INPUT}; border: 1px solid #d9bfa5; border-bottom: 3px solid #c9a888;
    border-radius: 5px; padding: 5px 12px; font-weight: 600; font-size: 13px;
}}
#Badge {{ border-radius: 3px; padding: 3px 8px; font-size: 11px; font-weight: 600; }}
#Chip {{
    background: {INPUT}; border: 1px solid {BORDER}; border-radius: 14px; padding: 0 4px 0 12px;
}}

/* ---------- inputs ---------- */
QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {{
    background: {INPUT}; border: 1px solid {BORDER}; border-radius: 5px;
    padding: 7px 10px; selection-background-color: {ACCENT}; selection-color: white;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{CHEVRON}"); width: 14px; height: 14px; margin-right: 10px; }}
QComboBox QAbstractItemView {{
    background: {INPUT}; border: 1px solid {BORDER}; border-radius: 5px; padding: 4px;
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}

/* ---------- buttons ---------- */
QPushButton {{
    background: {INPUT}; border: 1px solid {BORDER}; border-radius: 5px;
    padding: 7px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: {CARD_HOVER}; border-color: #d3bfa6; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {FAINT}; }}
QPushButton:checked {{ background: {ACCENT_SOFT}; border-color: {ACCENT}; color: {ACCENT_HOVER}; }}
QPushButton#Primary {{ border: none; color: #fff8ef; background: {ACCENT}; }}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Danger {{ color: {DANGER}; }}
QPushButton#Ghost, QToolButton#Ghost {{ background: transparent; border: none; padding: 5px; border-radius: 4px; }}
QPushButton#Ghost:hover, QToolButton#Ghost:hover {{ background: {CARD_HOVER}; }}
QPushButton#Link {{ background: transparent; border: none; padding: 4px 0; color: {ACCENT}; }}
QPushButton#Link:hover {{ color: {ACCENT_HOVER}; text-decoration: underline; }}

/* ---------- lists, tables, tabs ---------- */
QTableWidget {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 6px; gridline-color: {BORDER};
}}
QTableWidget::item {{ padding: 6px; }}
QTableWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QHeaderView::section {{
    background: {CARD_HOVER}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER};
    padding: 8px; font-weight: 600;
}}
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent; color: {MUTED}; padding: 8px 16px; margin-right: 4px;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom-color: {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

/* ---------- scrollbars ---------- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {TOGGLE_OFF}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{
    background: {CARD_HOVER}; border: 1px solid {BORDER}; border-radius: 3px; height: 8px; text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{ border-radius: 2px; background: {ACCENT}; }}

QMenu {{ background: {INPUT}; border: 1px solid {BORDER}; border-radius: 5px; padding: 5px; }}
QMenu::item {{ padding: 7px 22px 7px 12px; border-radius: 3px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 6px; }}
QMessageBox {{ background: {CARD}; }}
"""
