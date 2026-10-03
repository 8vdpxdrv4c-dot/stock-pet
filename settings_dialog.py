"""Full settings editor; credentials remain in the system credential store."""
from copy import deepcopy

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

import config
import startup


class SettingsDialog(QDialog):
    saved = pyqtSignal(dict)
    speech_preview = pyqtSignal(str)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("设置")
        self.setMinimumWidth(510)
        self._build_ui()
        self._load_values()
        self.resize(560, min(760, self.screen().availableGeometry().height() - 80))

    @staticmethod
    def _spin(minimum, maximum, suffix, step=1):
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        return spin

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        groups = QVBoxLayout(content)
        groups.setContentsMargins(0, 0, 8, 0)
        groups.setSpacing(14)
        scroll.setWidget(content)
        root.addWidget(scroll)

        pet_box = QGroupBox("桌面宠物")
        form = QFormLayout(pet_box)
        self.pet_name_edit = QLineEdit()
        self.pet_name_edit.setPlaceholderText("小戒")
        form.addRow("宠物名字", self.pet_name_edit)
        self.scale_spin = self._spin(50, 300, " %", 10)
        form.addRow("宠物大小", self.scale_spin)
        self.startup_check = QCheckBox("登录 Windows 时自动启动")
        form.addRow("开机启动", self.startup_check)
        groups.addWidget(pet_box)

        llm_box = QGroupBox("大模型（DeepSeek）")
        form = QFormLayout(llm_box)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-...")
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        show_btn = QPushButton("显示")
        show_btn.setCheckable(True)
        show_btn.setFixedWidth(52)
        show_btn.toggled.connect(lambda on: self.key_edit.setEchoMode(
            QLineEdit.Normal if on else QLineEdit.Password))
        show_btn.toggled.connect(lambda on: show_btn.setText("隐藏" if on else "显示"))
        key_row.addWidget(show_btn)
        form.addRow("API Key", key_row)
        self.base_url_edit = QLineEdit()
        form.addRow("Base URL", self.base_url_edit)
        self.model_edit = QLineEdit()
        form.addRow("模型", self.model_edit)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumHeight(130)
        self.prompt_edit.setPlaceholderText("设置助手的角色、回答风格；可使用 {pet_name} 引用宠物名字。")
        form.addRow("系统提示词", self.prompt_edit)
        tip = QLabel("API Key 保存到系统凭据存储；留空会保留已有密钥。")
        tip.setWordWrap(True)
        form.addRow(tip)
        groups.addWidget(llm_box)

        self.speech_box = QGroupBox("喝水 / 自定义提醒")
        self.speech_box.setCheckable(True)
        form = QFormLayout(self.speech_box)
        self.speech_interval_spin = self._spin(1, 180, " 分钟")
        form.addRow("提醒间隔", self.speech_interval_spin)
        self.speech_text_edit = QLineEdit()
        form.addRow("提醒内容", self.speech_text_edit)
        preview = QPushButton("预览提醒")
        preview.clicked.connect(lambda: self.speech_preview.emit(
            self.speech_text_edit.text().strip() or config.DEFAULT_SPEECH_TEXT))
        form.addRow(preview)
        groups.addWidget(self.speech_box)

        self.wellness_box = QGroupBox("久坐休息提醒")
        self.wellness_box.setCheckable(True)
        form = QFormLayout(self.wellness_box)
        self.wellness_interval_spin = self._spin(1, 180, " 分钟")
        form.addRow("休息提醒间隔", self.wellness_interval_spin)
        groups.addWidget(self.wellness_box)

        quiet_box = QGroupBox("免打扰")
        form = QFormLayout(quiet_box)
        self.fullscreen_check = QCheckBox("全屏应用运行时，延后显示提醒")
        form.addRow(self.fullscreen_check)
        groups.addWidget(quiet_box)
        groups.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_values(self):
        cfg = self.cfg
        speech = cfg.get("speech_reminder", {})
        wellness = cfg.get("wellness", {})
        self.pet_name_edit.setText(cfg.get("pet_name", "小戒"))
        self.scale_spin.setValue(int(cfg.get("pet_scale_percent", 100)))
        self._startup_enabled = startup.is_enabled()
        self.startup_check.setChecked(self._startup_enabled)
        self.key_edit.setText(cfg.get("deepseek_api_key", ""))
        self.base_url_edit.setText(cfg.get("deepseek_base_url", "https://api.deepseek.com"))
        self.model_edit.setText(cfg.get("deepseek_model", "deepseek-chat"))
        self._loaded_prompt = cfg.get("_system_prompt_template", cfg.get("system_prompt", ""))
        self.prompt_edit.setPlainText(self._loaded_prompt)
        self.speech_box.setChecked(speech.get("enabled", True))
        self.speech_interval_spin.setValue(int(speech.get("interval_minutes", 5)))
        self.speech_text_edit.setText(speech.get("text", config.DEFAULT_SPEECH_TEXT))
        self.wellness_box.setChecked(wellness.get("enabled", True))
        self.wellness_interval_spin.setValue(int(wellness.get("interval_minutes", 60)))
        self.fullscreen_check.setChecked(cfg.get("quiet_mode", {}).get("fullscreen", True))

    def _on_save(self):
        name = self.pet_name_edit.text().strip() or "小戒"
        template = self.prompt_edit.toPlainText()
        try:
            prompt = template.format(pet_name=name)
        except (ValueError, KeyError, IndexError, AttributeError):
            QMessageBox.critical(self, "提示词格式错误", "提示词只支持 {pet_name} 占位符；普通花括号请写成 {{ 和 }}。")
            return
        new_cfg = deepcopy(self.cfg)
        new_cfg.update({
            "pet_name": name,
            "pet_scale_percent": self.scale_spin.value(),
            "deepseek_base_url": self.base_url_edit.text().strip() or "https://api.deepseek.com",
            "deepseek_model": self.model_edit.text().strip() or "deepseek-chat",
        })
        new_cfg.setdefault("speech_reminder", {}).update({
            "enabled": self.speech_box.isChecked(),
            "interval_minutes": self.speech_interval_spin.value(),
            "text": self.speech_text_edit.text().strip() or config.DEFAULT_SPEECH_TEXT,
        })
        new_cfg.setdefault("wellness", {}).update({
            "enabled": self.wellness_box.isChecked(),
            "interval_minutes": self.wellness_interval_spin.value(),
        })
        new_cfg.setdefault("quiet_mode", {})["fullscreen"] = self.fullscreen_check.isChecked()
        payload = dict(new_cfg)
        # Preserve the stored prompt template when editing other settings.
        if template != self._loaded_prompt:
            payload["system_prompt"] = template
        else:
            payload.pop("system_prompt", None)
        key = self.key_edit.text().strip()
        try:
            if self.startup_check.isChecked() != self._startup_enabled:
                startup.set_enabled(self.startup_check.isChecked())
            if key and key != self.cfg.get("deepseek_api_key", ""):
                config.save_api_key(key)
            config.save_config(payload)
        except (OSError, RuntimeError) as error:
            QMessageBox.critical(self, "保存失败", str(error))
            return
        new_cfg["deepseek_api_key"] = key or self.cfg.get("deepseek_api_key", "")
        new_cfg["_system_prompt_template"] = template
        new_cfg["system_prompt"] = prompt
        self.saved.emit(new_cfg)
        self.accept()
