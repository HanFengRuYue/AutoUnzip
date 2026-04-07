from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..models import AppSettings, DisguisedExtensionRule
from ..settings import normalize_extension


class PasswordDialog(QDialog):
    def __init__(self, archive_name: str, layer: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("输入压缩包密码")
        self.setModal(True)
        self.resize(420, 210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"第 {layer} 层压缩包需要密码")
        title.setProperty("role", "section")
        description = QLabel(
            f"文件: {archive_name}\n密码库未命中，请输入密码。勾选后会在成功时保存到密码库。"
        )
        description.setProperty("role", "muted")
        description.setWordWrap(True)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("请输入压缩包密码")
        self.save_checkbox = QCheckBox("成功后保存到密码库")
        self.save_checkbox.setChecked(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(self.password_edit)
        layout.addWidget(self.save_checkbox)
        layout.addStretch(1)
        layout.addWidget(buttons)

    def password(self) -> str:
        return self.password_edit.text().strip()


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(620, 720)
        self.setMinimumSize(560, 640)
        self._settings = AppSettings(
            password_library=list(settings.password_library),
            disguised_extensions=[
                DisguisedExtensionRule(rule.suffix, rule.enabled)
                for rule in settings.disguised_extensions
            ],
            default_output_dir=settings.default_output_dir,
            cleanup_policy=settings.cleanup_policy,
            recent_inputs=list(settings.recent_inputs),
        )
        self._refreshing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        password_section = self._section("密码库")
        password_layout = password_section.layout()
        assert isinstance(password_layout, QVBoxLayout)
        self.password_list = QListWidget()
        self.password_list.setMinimumHeight(180)
        self.password_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("新增密码")
        password_actions = QHBoxLayout()
        self.password_add_button = QPushButton("添加")
        self.password_remove_button = QPushButton("删除")
        password_actions.addWidget(self.password_add_button)
        password_actions.addWidget(self.password_remove_button)
        password_actions.addStretch(1)
        password_layout.addWidget(self.password_list, 1)
        password_layout.addWidget(self.password_input)
        password_layout.addLayout(password_actions)

        extension_section = self._section("伪装后缀库")
        extension_layout = extension_section.layout()
        assert isinstance(extension_layout, QVBoxLayout)
        self.extension_list = QListWidget()
        self.extension_list.setMinimumHeight(180)
        self.extension_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.extension_input = QLineEdit()
        self.extension_input.setPlaceholderText("输入后缀，例如 .png")
        extension_actions = QHBoxLayout()
        self.extension_add_button = QPushButton("添加")
        self.extension_remove_button = QPushButton("删除")
        extension_actions.addWidget(self.extension_add_button)
        extension_actions.addWidget(self.extension_remove_button)
        extension_actions.addStretch(1)
        extension_layout.addWidget(self.extension_list, 1)
        extension_layout.addWidget(self.extension_input)
        extension_layout.addLayout(extension_actions)

        hint = QLabel("伪装后缀命中后，程序仍会继续用文件签名与 7-Zip 验证内容。")
        hint.setProperty("role", "muted")
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(password_section, 1)
        layout.addWidget(extension_section, 1)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self._load_settings()
        self._wire_actions()

    def _section(self, title: str) -> QWidget:
        section = QWidget()
        section.setProperty("panel", True)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setProperty("role", "section")
        layout.addWidget(label)
        return section

    def _wire_actions(self) -> None:
        self.password_add_button.clicked.connect(self._add_password)
        self.password_remove_button.clicked.connect(self._remove_password)
        self.extension_add_button.clicked.connect(self._add_extension)
        self.extension_remove_button.clicked.connect(self._remove_extension)
        self.extension_list.itemChanged.connect(self._save_extensions_from_list)

    def _load_settings(self) -> None:
        self._refreshing = True
        self.password_list.clear()
        for password in self._settings.password_library:
            self.password_list.addItem(password)

        self.extension_list.clear()
        for rule in self._settings.disguised_extensions:
            item = QListWidgetItem(rule.suffix)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if rule.enabled else Qt.Unchecked)
            self.extension_list.addItem(item)
        self._refreshing = False

    def _add_password(self) -> None:
        password = self.password_input.text().strip()
        if not password:
            return
        existing = {
            self.password_list.item(index).text().casefold()
            for index in range(self.password_list.count())
        }
        if password.casefold() in existing:
            return
        self.password_list.insertItem(0, password)
        self.password_input.clear()

    def _remove_password(self) -> None:
        row = self.password_list.currentRow()
        if row >= 0:
            self.password_list.takeItem(row)

    def _add_extension(self) -> None:
        suffix = normalize_extension(self.extension_input.text())
        if suffix is None:
            QMessageBox.warning(self, "后缀无效", "请输入有效后缀，例如 .png 或 png。")
            return
        existing = {
            self.extension_list.item(index).text().lower()
            for index in range(self.extension_list.count())
        }
        if suffix in existing:
            QMessageBox.information(self, "已存在", "该伪装后缀已在列表中。")
            return

        item = QListWidgetItem(suffix)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setCheckState(Qt.Checked)
        self.extension_list.insertItem(0, item)
        self.extension_input.clear()

    def _remove_extension(self) -> None:
        row = self.extension_list.currentRow()
        if row >= 0:
            self.extension_list.takeItem(row)
            self._save_extensions_from_list()

    def _save_extensions_from_list(self) -> None:
        if self._refreshing:
            return
        self._settings.disguised_extensions = [
            DisguisedExtensionRule(
                suffix=self.extension_list.item(index).text(),
                enabled=self.extension_list.item(index).checkState() == Qt.Checked,
            )
            for index in range(self.extension_list.count())
        ]

    def updated_settings(self) -> AppSettings:
        self._settings.password_library = [
            self.password_list.item(index).text()
            for index in range(self.password_list.count())
        ]
        self._save_extensions_from_list()
        return self._settings
