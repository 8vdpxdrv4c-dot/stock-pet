"""设置对话框：API key 存系统凭据管理器，其他配置存 config.json。"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QPushButton,
                             QHBoxLayout, QVBoxLayout, QGroupBox, QLabel,
                             QSpinBox, QMessageBox, QDialogButtonBox)


class SettingsDialog(QDialog):
    saved = pyqtSignal(dict)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("设置")
        self.setMinimumWidth(460)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        llm_box = QGroupBox("大模型（DeepSeek）")
        llm_form = QFormLayout(llm_box)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-...")
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        show_btn = QPushButton("显示")
        show_btn.setCheckable(True)
        show_btn.setFixedWidth(50)
        show_btn.toggled.connect(lambda on: self.key_edit.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        show_btn.toggled.connect(lambda on: show_btn.setText("隐藏" if on else "显示"))
        key_row.addWidget(show_btn)
        llm_form.addRow("API Key", key_row)
        self.base_url_edit = QLineEdit()
        llm_form.addRow("Base URL", self.base_url_edit)
        self.model_edit = QLineEdit()
        llm_form.addRow("模型", self.model_edit)
        root.addWidget(llm_box)
        dis_box = QGroupBox("交易纪律")
        dis_form = QFormLayout(dis_box)
        self.pet_name_edit = QLineEdit()
        dis_form.addRow("宠物名字", self.pet_name_edit)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setSuffix(" 分钟")
        dis_form.addRow("大盘检查间隔", self.interval_spin)
        self.panic_spin = QSpinBox()
        self.panic_spin.setRange(500, 5500)
        self.panic_spin.setSingleStep(100)
        self.panic_spin.setSuffix(" 家")
        dis_form.addRow("下跌家数 ≥ 此值警告", self.panic_spin)
        self.fomo_spin = QSpinBox()
        self.fomo_spin.setRange(500, 5500)
        self.fomo_spin.setSingleStep(100)
        self.fomo_spin.setSuffix(" 家")
        dis_form.addRow("上涨家数 ≥ 此值警告", self.fomo_spin)
        self.times_edit = QLineEdit()
        self.times_edit.setPlaceholderText("用英文逗号分隔，如 09:30,11:25,14:45")
        dis_form.addRow("定时提醒时点", self.times_edit)
        root.addWidget(dis_box)
        tip = QLabel("API Key 加密存到 Windows 凭据管理器，不写入任何配置文件。")
        tip.setStyleSheet("color:#888;font-size:11px;")
        tip.setWordWrap(True)
        root.addWidget(tip)
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("保存")
        btns.button(QDialogButtonBox.Cancel).setText("取消")
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load_values(self):
        d = self.cfg.get("discipline", {})
        self.key_edit.setText(self.cfg.get("deepseek_api_key", ""))
        self.base_url_edit.setText(self.cfg.get("deepseek_base_url", "https://api.deepseek.com"))
        self.model_edit.setText(self.cfg.get("deepseek_model", "deepseek-chat"))
        self.pet_name_edit.setText(self.cfg.get("pet_name", "小戒"))
        self.interval_spin.setValue(int(self.cfg.get("check_interval_minutes", 5)))
        self.panic_spin.setValue(int(d.get("panic_down_count_threshold", 3500)))
        self.fomo_spin.setValue(int(d.get("fomo_up_count_threshold", 4000)))
        self.times_edit.setText(",".join(d.get("remind_times", [])))

    def _on_save(self):
        key = self.key_edit.text().strip()
        if not key:
            ret = QMessageBox.warning(self, "提醒", "还没填 API Key。不填只能看大盘提醒不能聊天。\n仍然保存吗？", QMessageBox.Save | QMessageBox.Cancel)
            if ret != QMessageBox.Save:
                return
        times = [t.strip() for t in self.times_edit.text().split(",") if t.strip()]
        for t in times:
            if len(t) != 5 or t[2] != ":" or not t.replace(":", "").isdigit():
                QMessageBox.critical(self, "格式错", f"提醒时点格式不对：{t}\n应为 HH:MM")
                return
        new_cfg = dict(self.cfg)
        new_cfg["deepseek_base_url"] = self.base_url_edit.text().strip()
        new_cfg["deepseek_model"] = self.model_edit.text().strip() or "deepseek-chat"
        new_cfg["pet_name"] = self.pet_name_edit.text().strip() or "小戒"
        new_cfg["check_interval_minutes"] = self.interval_spin.value()
        new_cfg["discipline"] = {
            "panic_down_count_threshold": self.panic_spin.value(),
            "fomo_up_count_threshold": self.fomo_spin.value(),
            "max_trades_per_day": self.cfg.get("discipline", {}).get("max_trades_per_day", 3),
            "remind_times": times,
        }
        import config as cfg_mod
        cfg_mod.save_config(new_cfg)
        if key:
            cfg_mod.save_api_key(key)
        new_cfg["deepseek_api_key"] = key
        self.saved.emit(new_cfg)
        self.accept()
