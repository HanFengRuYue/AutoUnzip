from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class DropZone(QFrame):
    path_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setProperty("dropzone", True)
        self.setProperty("dragging", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(6)

        self.title_label = QLabel("拖拽压缩包或文件夹到这里")
        self.title_label.setProperty("role", "dropTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)

        self.path_label = QLabel("或点击下方按钮选择")
        self.path_label.setProperty("role", "muted")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(self.title_label)
        layout.addWidget(self.path_label)
        layout.addStretch(1)

    def set_path(self, path: str | None) -> None:
        if not path:
            self.path_label.setText("或点击下方按钮选择")
            return
        target = Path(path)
        kind = "文件夹" if target.is_dir() else "文件"
        self.path_label.setText(f"已选择{kind}: {target.name}")

    def dragEnterEvent(self, event) -> None:  # pragma: no cover - Qt callback
        if event.mimeData().hasUrls():
            self.setProperty("dragging", True)
            self.style().polish(self)
            event.acceptProposedAction()
            return
        event.ignore()

    def dragLeaveEvent(self, event) -> None:  # pragma: no cover - Qt callback
        self.setProperty("dragging", False)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # pragma: no cover - Qt callback
        self.setProperty("dragging", False)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        local_path = urls[0].toLocalFile()
        if local_path:
            self.path_dropped.emit(local_path)
            event.acceptProposedAction()
            return
        event.ignore()
