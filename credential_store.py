"""凭据存储：API key 优先走系统凭据管理器，失败兜底到用户目录混淆存储。"""
import base64
import json
import logging
import os

logger = logging.getLogger(__name__)
SERVICE_NAME = "StockPet"
USERNAME = "deepseek_api_key"


def _fallback_path():
    return os.path.join(os.path.expanduser("~"), ".stock_credential")


def get_api_key():
    try:
        import keyring
        v = keyring.get_password(SERVICE_NAME, USERNAME)
        if v:
            return v
    except Exception as e:
        logger.warning("keyring 不可用，走 fallback: %s", e)
    try:
        p = _fallback_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return base64.b64decode(data.get("k", "")).decode("utf-8")
    except Exception as e:
        logger.warning("fallback 读取失败: %s", e)
    return ""


def set_api_key(key):
    key = (key or "").strip()
    try:
        import keyring
        if key:
            keyring.set_password(SERVICE_NAME, USERNAME, key)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, USERNAME)
            except Exception:
                pass
        try:
            fp = _fallback_path()
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass
        return
    except Exception as e:
        logger.warning("keyring 写入失败，走 fallback: %s", e)
    fp = _fallback_path()
    if key:
        encoded = base64.b64encode(key.encode("utf-8")).decode("utf-8")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump({"k": encoded}, f)
        try:
            os.chmod(fp, 0o600)
        except Exception:
            pass
    else:
        try:
            if os.path.exists(fp):
                os.remove(fp)
        except Exception:
            pass


def clear_api_key():
    set_api_key("")
