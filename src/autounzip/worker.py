from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from .engine import RecursiveExtractor
from .models import AppSettings, ExtractionJob, PasswordRequest, PasswordResponse
from .settings import AppSettingsStore


class ExtractionWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    log_emitted = Signal(str)
    status_changed = Signal(str)
    timeline_emitted = Signal(str)
    password_requested = Signal(object)
    settings_changed = Signal(object)

    def __init__(
        self,
        job: ExtractionJob,
        settings: AppSettings,
        settings_store: AppSettingsStore,
    ) -> None:
        super().__init__()
        self.job = job
        self.settings = settings
        self.settings_store = settings_store
        self._cancelled = False
        self._password_event = threading.Event()
        self._password_response: PasswordResponse | None = None

    @Slot()
    def run(self) -> None:
        extractor = RecursiveExtractor(
            settings=self.settings,
            settings_store=self.settings_store,
        )
        try:
            self.status_changed.emit("扫描压缩包候选…")
            result = extractor.execute(
                self.job,
                log=self.log_emitted.emit,
                timeline=self._timeline,
                request_password=self._request_password,
                is_cancelled=lambda: self._cancelled,
            )
        except Exception as exc:  # pragma: no cover - UI delivery path
            self.failed.emit(str(exc))
            self.settings_changed.emit(self.settings_store.load())
            return

        if self._cancelled:
            self.failed.emit("任务已取消。")
        else:
            self.status_changed.emit("解压完成")
            self.finished.emit(result)
        self.settings_changed.emit(self.settings_store.load())

    def request_cancel(self) -> None:
        self._cancelled = True
        self.submit_password_response(PasswordResponse(password=None, cancel=True))

    def submit_password_response(self, response: PasswordResponse) -> None:
        self._password_response = response
        self._password_event.set()

    def _timeline(self, text: str) -> None:
        self.timeline_emitted.emit(text)
        self.status_changed.emit(text)

    def _request_password(self, request: PasswordRequest) -> PasswordResponse | None:
        self._password_response = None
        self._password_event.clear()
        self.password_requested.emit(request)
        self._password_event.wait()
        return self._password_response
