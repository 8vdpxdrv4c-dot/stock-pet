"""Windows 自检脚本：确认环境、网络、key 都 OK。用法：python self_check.py"""
import sys


def hr(title=""):
    if title:
        print(f"\n=== {title} ===")
    else:
        print("-" * 50)


ok = 0
fail = 0


def check(name, fn):
    global ok, fail
    try:
        msg = fn()
        print(f"  [OK]   {name}" + (f"  -> {msg}" if msg else ""))
        ok += 1
    except Exception as e:
        print(f"  [FAIL] {name}  -> {e}")
        fail += 1


hr("1. Python 版本")
print(f"  Python {sys.version.split()[0]}  ({sys.executable})")
if sys.version_info < (3, 9):
    print("  [FAIL] 需要 Python 3.9+")
    sys.exit(1)

hr("2. 依赖库")
def _import_pyqt():
    from PyQt5.QtCore import QT_VERSION_STR
    return QT_VERSION_STR
check("PyQt5", _import_pyqt)
def _import_openai():
    import openai
    return openai.__version__
check("openai", _import_openai)
def _import_keyring():
    import keyring
    return f"backend={keyring.get_keyring().__class__.__name__}"
check("keyring", _import_keyring)

hr("3. 凭据存储")
def _cred():
    import credential_store
    credential_store.set_api_key("__self_check__")
    v = credential_store.get_api_key()
    credential_store.set_api_key("")
    assert v == "__self_check__"
    return "读写删 OK"
check("credential_store", _cred)

hr("4. DeepSeek API 连通性")
def _deepseek():
    import credential_store, requests
    key = credential_store.get_api_key()
    if not key:
        return "未配置 key，跳过（首次启动会弹设置页）"
    r = requests.get("https://api.deepseek.com/models", headers={"Authorization": f"Bearer {key}"}, timeout=10)
    if r.status_code == 200:
        return "API Key 有效"
    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
check("DeepSeek API", _deepseek)

hr()
print(f"通过 {ok} 项，失败 {fail} 项")
if fail == 0:
    print("\n全部通过！可以运行 python main.py")
else:
    print("\n有失败项，把上面的 [FAIL] 信息发出来看。")
sys.exit(0 if fail == 0 else 1)
