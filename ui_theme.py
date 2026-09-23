"""Shared desktop colors and spacing; keep the product list visually dominant."""

from pathlib import Path

APP_STYLESHEET = """
QMainWindow, QWidget#appRoot { background: #f3f6fa; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #243247; }
QLabel { background: transparent; }
QLabel#brand { background: #245fe5; color: white; border-radius: 9px;
               font-size: 16px; font-weight: 700; padding: 10px 12px; }
QLabel#pageTitle { color: #14243c; font-size: 22px; font-weight: 600; }
QLabel#subtitle, QLabel#fieldLabel { color: #586b83; font-size: 12px; }
QLabel#sectionTitle { color: #14243c; font-size: 15px; font-weight: 600; }
QLabel#resultCount { color: #586b83; font-size: 12px; }
QFrame#filterPanel, QFrame#tablePanel {
    background: #ffffff; border: 1px solid #dce3ec; border-radius: 10px;
}
QLineEdit, QComboBox {
    background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px;
    padding: 7px 10px; min-height: 22px; selection-background-color: #245fe5;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #245fe5; }
QComboBox { padding-right: 24px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { image: url("__CHEVRON__"); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background: #ffffff; color: #243247; selection-background-color: #e8efff;
    selection-color: #174dc0; outline: none;
}
QPushButton {
    background: #ffffff; color: #34465f; border: 1px solid #cbd5e1;
    border-radius: 6px; padding: 7px 14px; min-height: 22px;
}
QPushButton:hover { background: #f0f4fa; border-color: #9cafc6; }
QPushButton:pressed { background: #e3ebf7; }
QPushButton:focus { border-color: #245fe5; }
QPushButton:disabled { color: #91a0b3; border-color: #e2e8f0; background: #f5f7fa; }
QPushButton#primaryButton { background: #245fe5; color: #ffffff; border-color: #245fe5; font-weight: 600; }
QPushButton#primaryButton:hover { background: #1d4fc4; }
QPushButton#primaryButton:disabled { background: #8ca9e9; border-color: #8ca9e9; }
QCheckBox { spacing: 7px; color: #586b83; }
QTableView {
    background: #ffffff; alternate-background-color: #f8fafc;
    border: none; selection-background-color: #e8efff; selection-color: #14243c;
    gridline-color: #edf1f6; outline: none;
}
QTableView::item { padding: 0px 10px; border-bottom: 1px solid #edf1f6; }
QHeaderView::section {
    background: #f1f5fa; color: #586b83; font-size: 12px; font-weight: 600;
    padding: 10px; border: none; border-bottom: 1px solid #dce3ec;
}
QLabel#emptyState { color: #6a7b91; font-size: 14px; padding: 32px; }
QWidget#emailNotice { background: #fff8e8; border: 1px solid #edd7a0; border-radius: 8px; }
QWidget#emailNotice QLabel { border: none; background: transparent; color: #865418; }
QStatusBar { background: #f3f6fa; color: #64748b; border: none; font-size: 12px; }
QStatusBar::item { border: none; }
QStatusBar QLabel { color: #64748b; font-size: 12px; padding: 2px 4px; }
QProgressBar { background: #dce5f4; border: none; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: #245fe5; border-radius: 3px; }
QToolTip { background: #172b45; color: #ffffff; border: none; padding: 6px; }
"""
APP_STYLESHEET = APP_STYLESHEET.replace("__CHEVRON__", (Path(__file__).parent / "assets" / "chevron-down.svg").as_posix())
