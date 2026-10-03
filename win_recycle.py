"""Windows 回收站相关：定位桌面回收站图标位置、查询与清空回收站。

全部用 ctypes 直接调 Win32，不引入新依赖。
- 定位图标：读桌面 SysListView32（explorer.exe 进程内），需跨进程读内存。
  找不到（图标被隐藏 / 非经典桌面）时返回 None，调用方自行兜底。
- 清空：shell32.SHEmptyRecycleBinW。这是**不可恢复**的操作。
"""
import ctypes
import logging
from ctypes import wintypes

logger = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

# ---------- Win32 常量 ----------
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

LVM_FIRST = 0x1000
LVM_GETITEMCOUNT = LVM_FIRST + 4
LVM_GETITEMPOSITION = LVM_FIRST + 16
LVM_GETITEMRECT = LVM_FIRST + 14
LVM_GETITEMSPACING = LVM_FIRST + 51
LVM_GETITEMTEXTW = LVM_FIRST + 115

LVIF_TEXT = 0x0001

SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004

_S_OK = 0
_S_FALSE = 1

# 各语言下的回收站显示名（小写比较）
RECYCLE_NAMES = ("回收站", "recycle bin", "資源回收筒", "资源回收站", "垃圾桶")

# ---------- 原型声明（不声明的话 HANDLE/WPARAM 会被截成 32 位）----------
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND

user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = wintypes.LPARAM

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t,
                                   wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = wintypes.LPVOID

kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD]
kernel32.VirtualFreeEx.restype = wintypes.BOOL

kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID,
                                        ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.restype = wintypes.BOOL

shell32.SHQueryRecycleBinW.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
shell32.SHQueryRecycleBinW.restype = ctypes.c_long

shell32.SHEmptyRecycleBinW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD]
shell32.SHEmptyRecycleBinW.restype = ctypes.c_long


class LVITEMW(ctypes.Structure):
    """只声明前 15 个字段；偏移与 64 位下真实的 LVITEMW 一致。"""
    _fields_ = [
        ("mask", wintypes.UINT),
        ("iItem", ctypes.c_int),
        ("iSubItem", ctypes.c_int),
        ("state", wintypes.UINT),
        ("stateMask", wintypes.UINT),
        ("pszText", wintypes.LPVOID),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("lParam", wintypes.LPARAM),
        ("iIndent", ctypes.c_int),
        ("iGroupId", ctypes.c_int),
        ("cColumns", wintypes.UINT),
        ("puColumns", wintypes.LPVOID),
        ("piColFmt", wintypes.LPVOID),
        ("iGroup", ctypes.c_int),
    ]


class SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("i64Size", ctypes.c_longlong),
        ("i64NumItems", ctypes.c_longlong),
    ]


# ---------- 桌面图标定位 ----------
def _find_defview():
    progman = user32.FindWindowW("Progman", None)
    if progman:
        view = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        if view:
            return view
    # Win11 上 DefView 可能挂在某个 WorkerW 下
    hits = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(hwnd, _lparam):
        view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if view:
            hits.append(view)
            return False
        return True

    user32.EnumWindows(WNDENUMPROC(_cb), 0)
    return hits[0] if hits else None


def _desktop_listview():
    view = _find_defview()
    if not view:
        return None
    return user32.FindWindowExW(view, None, "SysListView32", None) or None


def _open_target(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc = kernel32.OpenProcess(
        PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION,
        False, pid.value)
    return (proc or None), pid.value


def _read_item_text(hwnd, proc, index):
    size = ctypes.sizeof(LVITEMW)
    text_chars = 260
    total = size + text_chars * 2
    remote = kernel32.VirtualAllocEx(proc, None, total, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    if not remote:
        return None
    try:
        item = LVITEMW()
        item.mask = LVIF_TEXT
        item.iItem = index
        item.iSubItem = 0
        item.pszText = wintypes.LPVOID(remote + size)
        item.cchTextMax = text_chars
        if not kernel32.WriteProcessMemory(proc, remote, ctypes.byref(item), size, None):
            return None
        user32.SendMessageW(hwnd, LVM_GETITEMTEXTW, index, remote)
        buf = ctypes.create_unicode_buffer(text_chars)
        if not kernel32.ReadProcessMemory(proc, remote + size, buf,
                                          text_chars * 2, None):
            return None
        return buf.value
    finally:
        kernel32.VirtualFreeEx(proc, remote, 0, MEM_RELEASE)


def _read_item_pos(hwnd, proc, index):
    remote = kernel32.VirtualAllocEx(proc, None, ctypes.sizeof(wintypes.POINT),
                                     MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    if not remote:
        return None
    try:
        pt = wintypes.POINT()
        user32.SendMessageW(hwnd, LVM_GETITEMPOSITION, index, remote)
        if not kernel32.ReadProcessMemory(proc, remote, ctypes.byref(pt),
                                          ctypes.sizeof(wintypes.POINT), None):
            return None
        user32.ClientToScreen(hwnd, ctypes.byref(pt))
        return (pt.x, pt.y)
    finally:
        kernel32.VirtualFreeEx(proc, remote, 0, MEM_RELEASE)


def _read_icon_rect(hwnd, proc, index):
    rect = wintypes.RECT(1, 0, 0, 0)  # LVIR_ICON, excludes label and grid spacing.
    remote = kernel32.VirtualAllocEx(proc, None, ctypes.sizeof(rect),
                                    MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
    if not remote:
        return None
    try:
        if not kernel32.WriteProcessMemory(proc, remote, ctypes.byref(rect), ctypes.sizeof(rect), None):
            return None
        if not user32.SendMessageW(hwnd, LVM_GETITEMRECT, index, remote):
            return None
        if not kernel32.ReadProcessMemory(proc, remote, ctypes.byref(rect), ctypes.sizeof(rect), None):
            return None
        a, b = wintypes.POINT(rect.left, rect.top), wintypes.POINT(rect.right, rect.bottom)
        user32.ClientToScreen(hwnd, ctypes.byref(a))
        user32.ClientToScreen(hwnd, ctypes.byref(b))
        return _qt_screen_rect((a.x, a.y, b.x, b.y))
    finally:
        kernel32.VirtualFreeEx(proc, remote, 0, MEM_RELEASE)


def _qt_screen_rect(rect):
    """Convert Windows physical pixels into Qt screen coordinates, including mixed DPI."""
    from PyQt5.QtWidgets import QApplication
    if QApplication.instance() is None:
        return rect
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)]
    user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
    user32.MonitorFromRect.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    native = wintypes.RECT(*rect)
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(info)
    monitor = user32.MonitorFromRect(ctypes.byref(native), 2)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return rect
    screen = next((s for s in QApplication.screens() if s.name() == info.szDevice), None)
    if screen is None:
        return rect
    origin = screen.geometry()
    scale = screen.devicePixelRatio()
    return (round(origin.x() + (rect[0] - info.rcMonitor.left) / scale),
            round(origin.y() + (rect[1] - info.rcMonitor.top) / scale),
            round(origin.x() + (rect[2] - info.rcMonitor.left) / scale),
            round(origin.y() + (rect[3] - info.rcMonitor.top) / scale))


def find_recycle_bin_icon():
    """返回桌面回收站图标的屏幕矩形 (left, top, right, bottom)，找不到返回 None。"""
    try:
        lv = _desktop_listview()
        if not lv:
            logger.info("找不到桌面 SysListView32（桌面图标可能被隐藏）")
            return None
        count = int(user32.SendMessageW(lv, LVM_GETITEMCOUNT, 0, 0))
        if count <= 0:
            return None
        proc, pid = _open_target(lv)
        if not proc:
            logger.warning("OpenProcess 失败，无法读取桌面图标（排除权限受限）")
            return None
        try:
            for i in range(count):
                name = (_read_item_text(lv, proc, i) or "").strip()
                if name.lower() in RECYCLE_NAMES:
                    icon_rect = _read_icon_rect(lv, proc, i)
                    if icon_rect:
                        return icon_rect
                    pos = _read_item_pos(lv, proc, i)
                    if not pos:
                        return None
                    x, y = pos
                    spacer = int(user32.SendMessageW(lv, LVM_GETITEMSPACING, 0, 0))
                    w = (spacer & 0xFFFF) or 75
                    h = ((spacer >> 16) & 0xFFFF) or 75
                    logger.info("回收站图标: 名称=%s 位置=(%d,%d) 尺寸=%dx%d", name, x, y, w, h)
                    return _qt_screen_rect((x, y, x + w, y + h))
            logger.info("桌面 %d 个图标里没找到回收站（pid=%d）", count, pid)
            return None
        finally:
            kernel32.CloseHandle(proc)
    except Exception as e:  # 任何 Win32 异常都不该让宠物崩掉
        logger.warning("定位回收站图标失败: %s", e)
        return None


# ---------- 回收站查询 / 清空 ----------
def query_bin():
    """返回 (字节数, 项目数)；查询失败返回 None。"""
    try:
        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        hr = shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        if hr != _S_OK:
            logger.warning("SHQueryRecycleBin 返回 hr=0x%08X", hr & 0xFFFFFFFF)
            return None
        return int(info.i64Size), int(info.i64NumItems)
    except Exception as e:
        logger.warning("查询回收站失败: %s", e)
        return None


def human_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def empty_recycle_bin(confirm=False, progress=False, sound=False):
    """清空回收站。**不可恢复**。返回 (是否成功, 给用户看的文案)。

    confirm=True 时由 Windows 弹原生确认框；本项目自己弹确认，所以默认 False。
    """
    flags = 0
    if not confirm:
        flags |= SHERB_NOCONFIRMATION
    if not progress:
        flags |= SHERB_NOPROGRESSUI
    if not sound:
        flags |= SHERB_NOSOUND
    try:
        hr = shell32.SHEmptyRecycleBinW(None, None, flags)
    except Exception as e:
        logger.exception("SHEmptyRecycleBin 调用异常")
        return False, f"清空失败：{e}"
    if hr == _S_OK:
        return True, "回收站已清空。"
    if hr == _S_FALSE:
        return True, "回收站本来就是空的，白跑一趟。"
    if hr in (0x8000FFFF, -2147418113):  # E_UNEXPECTED
        return False, "清空失败：系统返回 E_UNEXPECTED（回收站可能被别的程序占用）。"
    return False, f"清空失败：HRESULT 0x{hr & 0xFFFFFFFF:08X}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("回收站当前:", query_bin(), "(字节, 项目数)")
    print("桌面回收站图标:", find_recycle_bin_icon())
    print("桌面 ListView 句柄:", _desktop_listview())
