"""Keep our Qt windows visible after a Windows hidden-start launch."""
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication


def _user32():
    app = QApplication.instance()
    if app is None or app.platformName() != "windows":
        return None
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.IsWindowVisible.restype = wintypes.BOOL
    user.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user.ShowWindow.restype = wintypes.BOOL
    return user


def native_visible(widget):
    if not widget.isVisible():
        return False
    user = _user32()
    return bool(user.IsWindowVisible(int(widget.winId()))) if user else widget.isVisible()


def ensure_native_visible(widget):
    # STARTF_USESHOWWINDOW/SW_HIDE can override Qt's first ShowWindow call.
    # Qt then considers the widget visible and skips later show() requests.
    # Repair only this application's explicitly shown window; never resurrect
    # a closed widget or activate a wheel during Explorer's native drag loop.
    if not widget.isVisible() or widget.isMinimized():
        return
    user = _user32()
    if user and not user.IsWindowVisible(int(widget.winId())):
        user.ShowWindow(int(widget.winId()), 4)  # SW_SHOWNOACTIVATE
