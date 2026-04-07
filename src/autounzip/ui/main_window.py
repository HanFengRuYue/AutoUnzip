from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import AppSettings, ExtractionJob, PasswordRequest, PasswordResponse
from ..settings import AppSettingsStore
from ..worker import ExtractionWorker
from .dialogs import PasswordDialog, SettingsDialog
from .styles import build_stylesheet
from .widgets import DropZone


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_store: AppSettingsStore,
        initial_settings: AppSettings | None = None,
    ) -> None:
        super().__init__()
        self.settings_store = settings_store
        self.settings = initial_settings or self.settings_store.load()
        self._thread: QThread | None = None
        self._worker: ExtractionWorker | None = None
        self._last_output_dir: str | None = None

        self.setWindowTitle("AutoUnzip")
        self.resize(760, 520)
        self.setMinimumSize(700, 470)

        app = QApplication.instance()
        assert app is not None
        app.setStyleSheet(build_stylesheet())
        app.setFont(QFont("Segoe UI Variable", 10))

        self._build_ui()
        self._wire_actions()

    def _build_ui(self) -> None:
        settings_menu = self.menuBar().addMenu("设置")
        open_settings = QAction("密码库与伪装后缀...", self)
        open_settings.triggered.connect(self._open_settings_dialog)
        settings_menu.addAction(open_settings)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        self.main_panel = QWidget()
        self.main_panel.setProperty("panel", True)
        panel_layout = QVBoxLayout(self.main_panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(14)

        self.drop_zone = DropZone()
        self.drop_zone.setMinimumHeight(150)
        panel_layout.addWidget(self.drop_zone)

        self.input_edit = QLineEdit()
        self.input_edit.setReadOnly(True)
        self.input_edit.setPlaceholderText("未选择输入源")
        panel_layout.addWidget(self.input_edit)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.file_button = QPushButton("选择文件")
        self.folder_button = QPushButton("选择文件夹")
        self.open_output_button = QPushButton("打开结果目录")
        self.open_output_button.setEnabled(False)
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.start_button = QPushButton("开始解压")
        self.start_button.setProperty("accent", True)
        actions.addWidget(self.file_button)
        actions.addWidget(self.folder_button)
        actions.addStretch(1)
        actions.addWidget(self.open_output_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(self.start_button)
        panel_layout.addLayout(actions)

        self.activity_panel = QWidget()
        self.activity_panel.setVisible(False)
        activity_layout = QVBoxLayout(self.activity_panel)
        activity_layout.setContentsMargins(0, 0, 0, 0)
        activity_layout.setSpacing(10)

        self.status_value = QLabel("")
        self.status_value.setProperty("role", "section")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        log_actions = QHBoxLayout()
        log_actions.addStretch(1)
        self.copy_log_button = QPushButton("复制日志")
        self.copy_log_button.setProperty("ghost", True)
        self.clear_log_button = QPushButton("清空")
        self.clear_log_button.setProperty("ghost", True)
        log_actions.addWidget(self.copy_log_button)
        log_actions.addWidget(self.clear_log_button)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)
        self.log_output.setPlaceholderText("")

        activity_layout.addWidget(self.status_value)
        activity_layout.addWidget(self.progress_bar)
        activity_layout.addLayout(log_actions)
        activity_layout.addWidget(self.log_output, 1)

        panel_layout.addWidget(self.activity_panel)
        root.addWidget(self.main_panel, 1)
        self.setCentralWidget(central)

    def _wire_actions(self) -> None:
        self.drop_zone.path_dropped.connect(self._set_input_path)
        self.file_button.clicked.connect(self._select_input_file)
        self.folder_button.clicked.connect(self._select_input_folder)
        self.start_button.clicked.connect(self._start_job)
        self.stop_button.clicked.connect(self._stop_job)
        self.open_output_button.clicked.connect(self._open_output_directory)
        self.copy_log_button.clicked.connect(self._copy_logs)
        self.clear_log_button.clicked.connect(self.log_output.clear)

    def _set_input_path(self, path: str) -> None:
        self.input_edit.setText(path)
        self.drop_zone.set_path(path)

    def _select_input_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择压缩包文件")
        if path:
            self._set_input_path(path)

    def _select_input_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            self._set_input_path(path)

    def _start_job(self) -> None:
        input_text = self.input_edit.text().strip()
        if not input_text:
            QMessageBox.warning(self, "缺少输入", "请先选择压缩包文件或文件夹。")
            return

        input_path = Path(input_text)
        if not input_path.exists():
            QMessageBox.warning(self, "路径无效", "输入路径不存在。")
            return

        self.activity_panel.setVisible(True)
        self.log_output.clear()
        self.progress_bar.setRange(0, 0)
        self.status_value.setText("正在准备解压任务…")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.open_output_button.setEnabled(False)

        self._thread = QThread(self)
        self._worker = ExtractionWorker(
            job=ExtractionJob(input_path=input_path, output_dir=None),
            settings=self.settings,
            settings_store=self.settings_store,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.log_emitted.connect(self._append_log)
        self._worker.timeline_emitted.connect(self._append_phase)
        self._worker.status_changed.connect(self.status_value.setText)
        self._worker.password_requested.connect(self._handle_password_request)
        self._worker.finished.connect(self._handle_finished)
        self._worker.failed.connect(self._handle_failed)
        self._worker.settings_changed.connect(self._handle_settings_changed)
        self._worker.finished.connect(self._cleanup_thread)
        self._worker.failed.connect(self._cleanup_thread)
        self._thread.start()

    def _stop_job(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()
            self.status_value.setText("正在停止任务…")

    def _append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _append_phase(self, text: str) -> None:
        self._append_log(f"[阶段] {text}")

    def _copy_logs(self) -> None:
        QApplication.clipboard().setText(self.log_output.toPlainText())

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = self.settings_store.save(dialog.updated_settings())

    @Slot(object)
    def _handle_password_request(self, request: PasswordRequest) -> None:
        dialog = PasswordDialog(request.archive_path.name, request.layer, self)
        if dialog.exec():
            response = PasswordResponse(
                password=dialog.password(),
                save_to_library=dialog.save_checkbox.isChecked(),
            )
        else:
            response = PasswordResponse(password=None, cancel=True)
        if self._worker is not None:
            self._worker.submit_password_response(response)

    @Slot(object)
    def _handle_finished(self, result) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.open_output_button.setEnabled(True)
        self._last_output_dir = str(result.final_output_dir)
        message = (
            f"已完成，共解压 {result.archives_extracted} 个压缩包。\n"
            f"结果目录：{result.final_output_dir}\n"
            "中间层压缩包和临时目录已自动清理。"
        )
        if result.warnings:
            message += f"\n\n警告数量：{len(result.warnings)}"
        QMessageBox.information(self, "任务完成", message)

    @Slot(str)
    def _handle_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if message and message != "任务已取消。":
            QMessageBox.warning(self, "任务失败", message)
        self.status_value.setText(message or "任务结束")

    @Slot(object)
    def _handle_settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings

    def _cleanup_thread(self, *_args) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    def _open_output_directory(self) -> None:
        if self._last_output_dir:
            os.startfile(self._last_output_dir)
