"""Capture the real video editor using an isolated profile and a generated clip."""
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['ZESTE_CONFIG_DIR']=str(ROOT/'build/video-documentation-profile')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QFontDatabase
from zeste.engine import Engine
from zeste.ui import MainWindow
from zeste.video_trimmer import VideoTrimmer

source=ROOT/'build/video-documentation/Video de demonstration.mp4'
source.parent.mkdir(parents=True,exist_ok=True)
if not source.exists():
    Engine().ff(['-f','lavfi','-i','testsrc2=s=960x540:r=12:d=90','-c:v','libx264','-preset','ultrafast',source])
app=QApplication([])
app.setStyle('Fusion')
for name in ['segoeui.ttf','segoeuib.ttf']:
    QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name))
window=MainWindow();window.watcher.timer.stop();window.tray.hide()
window.style_switch.setChecked(True)
dialog=VideoTrimmer(source,window)
dialog.show()
deadline=time.monotonic()+30
while time.monotonic()<deadline and not hasattr(dialog,'picture'):
    app.processEvents();time.sleep(.02)
assert dialog.total and hasattr(dialog,'picture'),'Video preview did not render'
dialog.set_selection(15000,75000)
deadline=time.monotonic()+10
while time.monotonic()<deadline:
    app.processEvents();time.sleep(.02)
    if not dialog.seek_timer.isActive() and dialog.decoder.process is None:break
dialog.grab().save(str(ROOT/'docs/images/decoupage-video.png'))
dialog.reject();dialog.deleteLater()
app.removeEventFilter(window);window.hide();window.deleteLater()
QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
print('Video editor screenshot saved.')
