"""配置加载：非敏感项从 config.json 读；API key 从系统凭据管理器读。"""
import json
import os
import sys

import credential_store


def _get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _get_base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"找不到配置文件: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["deepseek_api_key"] = credential_store.get_api_key()
    cfg["system_prompt"] = cfg.get("system_prompt", "").format(pet_name=cfg.get("pet_name", "小戒"))
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        old = json.load(f)
    for k in ("deepseek_base_url", "deepseek_model", "pet_name", "check_interval_minutes", "discipline", "system_prompt"):
        if k in cfg:
            old[k] = cfg[k]
    old["deepseek_api_key"] = "（已存到系统凭据管理器）"
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)


def save_api_key(key):
    credential_store.set_api_key(key)
