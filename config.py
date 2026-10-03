"""配置加载：非敏感项从 config.json 读；API key 从系统凭据管理器读。"""
import json
import os
import sys
import shutil

import credential_store


def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = getattr(sys, "_MEIPASS", _get_base_dir())
CONFIG_PATH = (os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "StockPet", "config.json")
               if getattr(sys, "frozen", False) else os.path.join(BASE_DIR, "config.json"))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DEFAULT_SPEECH_TEXT = "主人，记得喝水哦~喵"
RETIRED_KEYS = ("check_interval_minutes", "discipline")


def load_config():
    if getattr(sys, "frozen", False) and not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        shutil.copyfile(os.path.join(BASE_DIR, "config.json"), CONFIG_PATH)
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"找不到配置文件: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for key in RETIRED_KEYS:
        cfg.pop(key, None)
    cfg["deepseek_api_key"] = credential_store.get_api_key()
    cfg["_system_prompt_template"] = cfg.get("system_prompt", "")
    cfg["system_prompt"] = cfg["_system_prompt_template"].format(pet_name=cfg.get("pet_name", "小戒"))
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        old = json.load(f)
    for key in RETIRED_KEYS:
        old.pop(key, None)
    for k in ("deepseek_base_url", "deepseek_model", "pet_name", "pet_scale_percent", "speech_reminder", "wellness", "quiet_mode", "system_prompt"):
        if k in cfg:
            old[k] = cfg[k]
    old["deepseek_api_key"] = "（已存到系统凭据管理器）"
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)


def save_api_key(key):
    credential_store.set_api_key(key)
