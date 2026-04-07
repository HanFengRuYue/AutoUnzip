from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .elevation import is_running_as_admin, relaunch_as_admin
from .settings import AppSettingsStore, SettingsPermissionError
from .ui.main_window import MainWindow
from .vendor import app_icon_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AutoUnzip")

    icon_path = app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    settings_store = AppSettingsStore()
    try:
        initial_settings = settings_store.load()
    except SettingsPermissionError as exc:
        if is_running_as_admin():
            QMessageBox.critical(
                None,
                "配置写入失败",
                f"程序已经在管理员权限下运行，但仍无法访问配置文件：\n{exc.path}",
            )
            return 1

        if relaunch_as_admin():
            return 0

        QMessageBox.critical(
            None,
            "需要管理员权限",
            f"无法在程序目录写入配置文件：\n{exc.path}\n\n请允许 UAC 提权后重新启动程序。",
        )
        return 1

    window = MainWindow(settings_store, initial_settings=initial_settings)
    if icon_path is not None:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
