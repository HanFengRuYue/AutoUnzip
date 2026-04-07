from __future__ import annotations


def build_stylesheet() -> str:
    return """
    QMainWindow, QDialog {
        background: #eef4ff;
    }
    QWidget {
        color: #163252;
        font-family: "Segoe UI Variable", "Segoe UI", sans-serif;
        font-size: 13px;
    }
    QMenuBar {
        background: rgba(255, 255, 255, 0.88);
        border-bottom: 1px solid rgba(93, 131, 198, 0.16);
        padding: 4px 10px;
    }
    QMenuBar::item {
        padding: 6px 10px;
        border-radius: 8px;
    }
    QMenuBar::item:selected {
        background: rgba(59, 130, 246, 0.12);
    }
    QMenu {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(93, 131, 198, 0.16);
        border-radius: 12px;
        padding: 8px;
    }
    QMenu::item {
        padding: 8px 12px;
        border-radius: 8px;
    }
    QMenu::item:selected {
        background: rgba(59, 130, 246, 0.12);
    }
    QWidget[panel="true"] {
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(114, 153, 216, 0.16);
        border-radius: 22px;
    }
    QLabel[role="muted"] {
        color: #5e7aa0;
        font-size: 12px;
    }
    QLabel[role="section"] {
        color: #23456f;
        font-size: 12px;
        font-weight: 700;
    }
    QLabel[role="dropTitle"] {
        color: #12345d;
        font-size: 20px;
        font-weight: 700;
    }
    QFrame[dropzone="true"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(239, 246, 255, 0.98),
            stop:1 rgba(224, 236, 255, 0.96));
        border: 2px dashed rgba(59, 130, 246, 0.35);
        border-radius: 20px;
    }
    QFrame[dropzone="true"][dragging="true"] {
        border-color: #2563eb;
        background: rgba(219, 234, 254, 0.98);
    }
    QLineEdit, QPlainTextEdit, QListWidget {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(114, 153, 216, 0.18);
        border-radius: 14px;
        padding: 10px 12px;
        selection-background-color: #2563eb;
    }
    QListWidget::item {
        padding: 8px 6px;
        border-radius: 10px;
    }
    QListWidget::item:selected {
        background: rgba(59, 130, 246, 0.12);
        color: #0f2440;
    }
    QPushButton {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(114, 153, 216, 0.22);
        border-radius: 14px;
        padding: 10px 16px;
        font-weight: 600;
        color: #173359;
    }
    QPushButton:hover {
        border-color: rgba(59, 130, 246, 0.42);
        background: rgba(245, 250, 255, 1);
    }
    QPushButton:disabled {
        color: #9eb3cf;
        background: rgba(255, 255, 255, 0.72);
    }
    QPushButton[accent="true"] {
        background: #2563eb;
        color: white;
        border: none;
    }
    QPushButton[accent="true"]:hover {
        background: #1d4ed8;
    }
    QPushButton[ghost="true"] {
        background: transparent;
    }
    QProgressBar {
        border: none;
        background: rgba(37, 99, 235, 0.10);
        border-radius: 999px;
        min-height: 10px;
        max-height: 10px;
    }
    QProgressBar::chunk {
        border-radius: 999px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #3b82f6, stop:1 #60a5fa);
    }
    """
