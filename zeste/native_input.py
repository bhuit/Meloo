"""Windows background input. Retains only mouse buttons and wheel shortcuts.

No character decoding, text logging, hooks, input suppression or injection.
RIDEV_INPUTSINK keeps normal input delivery to Explorer and other programs.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import os
import struct
from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication


class InputState:
    def __init__(self):
        self.buttons = set()
        self.shortcuts = set()
        self.mouse_presses = 0
        self.ctrl_presses = 0

    def mouse(self, flags):
        for button, down, up in [(1, 0x0001, 0x0002), (2, 0x0004, 0x0008)]:
            if flags & down:
                self.buttons.add(button)
                self.mouse_presses += 1
            if flags & up: self.buttons.discard(button)

    def keyboard(self, vkey, flags):
        if vkey == 0x11: vkey = 0xA3 if flags & 2 else 0xA2
        if vkey == 0x12: vkey = 0xA5 if flags & 2 else 0xA4
        # Never retain letter/number/function keys, scan codes or text.
        if vkey not in {0xA2, 0xA3, 0xA4, 0xA5, 0x1B, 0x09}: return
        if flags & 1:
            self.shortcuts.discard(vkey)
        else:
            if vkey in {0xA2, 0xA3} and vkey not in self.shortcuts:
                self.ctrl_presses += 1
            self.shortcuts.add(vkey)

    def down(self, key):
        return key in self.buttons or key in self.shortcuts


class RawInputDevice(ctypes.Structure):
    _fields_ = [('usage_page', wintypes.USHORT), ('usage', wintypes.USHORT),
                ('flags', wintypes.DWORD), ('target', wintypes.HWND)]


class RawInputHeader(ctypes.Structure):
    _fields_ = [('kind', wintypes.DWORD), ('size', wintypes.DWORD),
                ('device', wintypes.HANDLE), ('wparam', wintypes.WPARAM)]


class WindowsInput(QAbstractNativeEventFilter):
    def __init__(self, window):
        super().__init__()
        self.state = InputState()
        self.active = False
        self.error = ''
        self.mouse_messages = 0
        self.keyboard_messages = 0
        app = QApplication.instance()
        if os.name != 'nt' or app.platformName() != 'windows': return
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.user.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RawInputDevice), wintypes.UINT, wintypes.UINT]
        self.user.RegisterRawInputDevices.restype = wintypes.BOOL
        self.user.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
        self.user.GetRawInputData.restype = wintypes.UINT
        self.header_size = ctypes.sizeof(RawInputHeader)
        target = int(window.winId())
        devices = (RawInputDevice * 2)(RawInputDevice(1, 2, 0x100, target), RawInputDevice(1, 6, 0x100, target))
        app.installNativeEventFilter(self)
        self.active = bool(self.user.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RawInputDevice)))
        if not self.active:
            self.error = str(ctypes.get_last_error())
            app.removeNativeEventFilter(self)
        app.aboutToQuit.connect(self.close)

    def close(self):
        if not self.active: return
        devices = (RawInputDevice * 2)(RawInputDevice(1, 2, 1, None), RawInputDevice(1, 6, 1, None))
        self.user.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RawInputDevice))
        QApplication.instance().removeNativeEventFilter(self)
        self.active = False

    def registration_status(self):
        if not self.active: return []
        get = self.user.GetRegisteredRawInputDevices
        get.argtypes = [ctypes.POINTER(RawInputDevice), ctypes.POINTER(wintypes.UINT), wintypes.UINT]
        get.restype = wintypes.UINT
        count = wintypes.UINT()
        get(None, ctypes.byref(count), ctypes.sizeof(RawInputDevice))
        if not 0 < count.value < 32: return []
        devices = (RawInputDevice * count.value)()
        returned = get(devices, ctypes.byref(count), ctypes.sizeof(RawInputDevice))
        if returned == 0xFFFFFFFF: return []
        return [{'usage':d.usage, 'flags':d.flags, 'has_target':bool(d.target)} for d in devices[:returned] if d.usage_page == 1]

    def consume(self, data):
        if len(data) < self.header_size: return
        header = RawInputHeader.from_buffer_copy(data)
        if header.size > len(data): return
        offset = self.header_size
        if header.kind == 0 and len(data) >= offset + 8:
            self.mouse_messages += 1
            self.state.mouse(struct.unpack_from('<H', data, offset + 4)[0])
        elif header.kind == 1 and len(data) >= offset + 8:
            self.keyboard_messages += 1
            _, flags, _, vkey = struct.unpack_from('<HHHH', data, offset)
            self.state.keyboard(vkey, flags)

    def nativeEventFilter(self, event_type, message):
        if self.active:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x00FF:  # WM_INPUT
                size = wintypes.UINT()
                self.user.GetRawInputData(msg.lParam, 0x10000003, None, ctypes.byref(size), self.header_size)
                if self.header_size <= size.value <= 4096:
                    buffer = ctypes.create_string_buffer(size.value)
                    copied = self.user.GetRawInputData(msg.lParam, 0x10000003, buffer, ctypes.byref(size), self.header_size)
                    if copied == size.value: self.consume(buffer.raw)
        # Let Qt/DefWindowProc perform WM_INPUT cleanup. Never swallow input.
        return False, 0
