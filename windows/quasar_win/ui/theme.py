"""Dark space theme. Palette follows the Android app (navy base, editorial red)."""

NAVY = "#0E1B2A"
MIDNIGHT = "#070B14"
PAPER = "#F5F5F3"
STEEL = "#B0B7C0"
SOFT = "#ADB6C6"
RED = "#D52B1E"
RED_GLOW = "#FF4A3A"
CYAN = "#46E1FF"
VIOLET = "#AA64FF"
GOOD = "#3DDC97"
WARN = "#FFC857"

QSS = f"""
* {{ font-family: "Segoe UI"; font-size: 10.5pt; color: {PAPER}; }}
QMainWindow, QDialog {{ background: {MIDNIGHT}; }}
QWidget#page {{ background: transparent; }}
QLabel {{ background: transparent; }}
QLabel#title {{ font-size: 21pt; font-weight: 600; }}
QLabel#subtitle {{ color: {STEEL}; }}
QLabel#h2 {{ font-size: 13pt; font-weight: 600; }}
QLabel#muted {{ color: {SOFT}; }}
QLabel#good {{ color: {GOOD}; }}
QLabel#warn {{ color: {WARN}; }}
QLabel#bad {{ color: {RED_GLOW}; }}
QFrame#card {{ background: qlineargradient(x1:0, y1:0, x2:0.8, y2:1,
               stop:0 rgba(24, 38, 60, 245), stop:1 rgba(13, 23, 40, 245));
               border: 1px solid rgba(139, 182, 210, 65);
               border-radius: 12px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QFrame#sidebar {{ background: rgba(7, 11, 20, 235); border-right: 1px solid rgba(70, 225, 255, 40); }}
QListWidget#nav {{ background: transparent; border: none; outline: none; }}
QListWidget#nav::item {{ padding: 11px 16px; border-radius: 8px; margin: 2px 8px; color: {STEEL}; }}
QListWidget#nav::item:hover {{ background: rgba(70, 225, 255, 25); }}
QListWidget#nav::item:selected {{ background: rgba(170, 100, 255, 70); color: white;
                                  border-left: 3px solid {CYAN}; }}
QPushButton {{ background: rgba(26, 37, 47, 230); border: 1px solid rgba(176, 183, 192, 90);
               border-radius: 8px; padding: 8px 16px; }}
QPushButton:hover {{ border-color: {CYAN}; background: rgba(70, 225, 255, 30); }}
QPushButton:disabled {{ color: {SOFT}; border-color: rgba(176, 183, 192, 30); }}
QPushButton#primary {{ background: {RED}; border: 1px solid {RED_GLOW}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {RED_GLOW}; }}
QPushButton#primary:disabled {{ background: rgba(213, 43, 30, 70); color: {SOFT}; border-color: transparent; }}
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{ background: rgba(7, 11, 20, 220);
    border: 1px solid rgba(176, 183, 192, 90); border-radius: 7px; padding: 6px 8px;
    selection-background-color: {VIOLET}; }}
QLineEdit:focus, QComboBox:focus {{ border-color: {CYAN}; }}
QPushButton:focus {{ border: 2px solid {CYAN}; }}
QComboBox QAbstractItemView {{ background: {NAVY}; selection-background-color: {VIOLET}; }}
QCheckBox {{ spacing: 9px; background: transparent; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px;
                        border: 1px solid {STEEL}; background: rgba(7, 11, 20, 220); }}
QCheckBox::indicator:checked {{ background: {CYAN}; border-color: {CYAN}; }}
QProgressBar {{ background: rgba(7, 11, 20, 220); border: 1px solid rgba(176, 183, 192, 70);
                border-radius: 7px; height: 14px; text-align: center; font-size: 8.5pt; }}
QProgressBar::chunk {{ border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {CYAN}, stop:1 {VIOLET}); }}
QTableWidget {{ background: rgba(7, 11, 20, 200); border: 1px solid rgba(176, 183, 192, 60);
                border-radius: 8px; gridline-color: rgba(176, 183, 192, 30);
                alternate-background-color: rgba(26, 37, 47, 160); }}
QHeaderView::section {{ background: rgba(26, 37, 47, 255); border: none; padding: 6px;
                        color: {STEEL}; font-weight: 600; }}
QTabWidget::pane {{ border: none; background: transparent; top: -1px; }}
QTabBar::tab {{ background: rgba(26, 37, 47, 230); color: {STEEL}; padding: 8px 18px;
                border: 1px solid rgba(176, 183, 192, 50); border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; }}
QTabBar::tab:selected {{ color: {PAPER}; border-color: {CYAN}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: rgba(176, 183, 192, 80); border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {NAVY}; color: {PAPER}; border: 1px solid {CYAN}; }}
"""
