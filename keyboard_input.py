"""Windows background key-down notifications, without retaining key values."""
import ctypes
import logging
import os
from ctypes import wintypes

from PyQt5.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

log = logging.getLogger(__name__)


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("page", wintypes.USHORT), ("usage", wintypes.USHORT),
                ("flags", wintypes.DWORD), ("target", wintypes.HWND)]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("kind", wintypes.DWORD), ("size", wintypes.DWORD),
                ("device", wintypes.HANDLE), ("parameter", ctypes.c_size_t)]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("make_code", wintypes.USHORT), ("flags", wintypes.USHORT),
                ("reserved", wintypes.USHORT), ("virtual_key", wintypes.USHORT),
                ("message", wintypes.UINT), ("extra", wintypes.ULONG)]


class _KeyboardFilter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        if self.owner.active:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x00FF:  # WM_INPUT
                self.owner._read_input(msg.lParam)
        return False, 0  # Never consume or alter input to other applications.


class KeyboardInput(QObject):
    key_pressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active = False
        self._filter = _KeyboardFilter(self)
        self._user32 = None

    def start(self, window_id):
        if self.active or os.name != "nt" or QApplication.platformName() != "windows":
            return
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
        self._user32.RegisterRawInputDevices.restype = wintypes.BOOL
        self._user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p,
                                               ctypes.POINTER(wintypes.UINT), wintypes.UINT]
        self._user32.GetRawInputData.restype = wintypes.UINT
        device = RAWINPUTDEVICE(1, 6, 0x100, int(window_id))  # Keyboard, INPUTSINK.
        if not self._user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device)):
            log.warning("键盘动作监听未启动，Windows 错误 %s", ctypes.get_last_error())
            return
        QApplication.instance().installNativeEventFilter(self._filter)
        self.active = True

    def _read_input(self, handle):
        size = wintypes.UINT()
        header_size = ctypes.sizeof(RAWINPUTHEADER)
        api = self._user32.GetRawInputData
        if api(handle, 0x10000003, None, ctypes.byref(size), header_size) == 0xFFFFFFFF:
            return
        if size.value < header_size + ctypes.sizeof(RAWKEYBOARD):
            return
        buffer = ctypes.create_string_buffer(size.value)
        if api(handle, 0x10000003, buffer, ctypes.byref(size), header_size) == 0xFFFFFFFF:
            return
        header = RAWINPUTHEADER.from_buffer(buffer)
        if header.kind == 1:
            keyboard = RAWKEYBOARD.from_buffer(buffer, header_size)
            if not keyboard.flags & 1:  # Key down, including key-repeat; ignore release.
                self.key_pressed.emit()

    def stop(self):
        if not self.active:
            return
        device = RAWINPUTDEVICE(1, 6, 1, None)  # RIDEV_REMOVE
        self._user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device))
        QApplication.instance().removeNativeEventFilter(self._filter)
        self.active = False
