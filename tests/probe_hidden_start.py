"""Isolated native-window probe; never connects to the installed session."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication
from zeste.ui import MainWindow

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
window = MainWindow()
window.watcher.timer.stop()
window.tray.hide()
window.settings.setValue("global_drag", False)
user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
observations = []

def record(label, widget):
    observations.append({"action": label, "qt_visible": widget.isVisible(),
                         "native_visible": bool(user32.IsWindowVisible(int(widget.winId()))),
                         "page": window.stack.currentIndex()})

steps = iter(["Réglages", "Fonctionnalités…", "Atelier avancé", "Derniers résultats", "Afficher la roue"])

def step():
    try:
        label = next(steps)
    except StopIteration:
        Path(sys.argv[1]).write_text(json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf8")
        window.watcher.input.close()
        app.removeEventFilter(window)
        for widget in app.topLevelWidgets():
            widget.hide()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.quit()
        return
    action = next(a for a in window.tray.contextMenu().actions() if a.text() == label)
    action.trigger()
    def inspect():
        record(label, window.popup if label == "Afficher la roue" else window)
        QTimer.singleShot(20, step)
    QTimer.singleShot(100, inspect)

QTimer.singleShot(50, step)
QTimer.singleShot(8000, app.quit)
app.exec()
