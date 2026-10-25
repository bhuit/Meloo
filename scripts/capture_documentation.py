"""Render real Meloo widgets with an isolated profile and a demonstration file."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["ZESTE_CONFIG_DIR"] = str(ROOT / "build/documentation-profile")

from PySide6.QtCore import Qt, QPointF, QRectF, QCoreApplication, QEvent
from PySide6.QtGui import QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication
from zeste.ui import MainWindow
from zeste.engine import Engine

output = ROOT / "docs/images"
output.mkdir(parents=True, exist_ok=True)
app = QApplication([])
app.setStyle("Fusion")
for name in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / name))
window = MainWindow()
window.watcher.timer.stop()
window.tray.hide()
window.clear_history()
window.settings.setValue("reduce_motion", True)
window.settings.setValue("output", "")
window.settings.setValue("light", False)
window.resize(1280, 820)
window.add_files([str(ROOT / "exemples/Carte de démonstration.png")])
window.show_main()
for theme in ("orange", "melina"):
    window.style_switch.setChecked(theme == "melina")
    window.navigate(0)
    app.processEvents()
    window.grab().save(str(output / f"atelier-{theme}.png"))
    window.popup.set_files(window.selected_paths())
    window.popup.set_mode("convert")
    window.popup.show()
    app.processEvents()
    window.popup.grab().save(str(output / f"roue-{theme}.png"))
    window.popup.hide()
window.action_picker.setCurrentIndex(window.action_picker.findData("to:webp"))
results = Engine(output_dir=ROOT / "build/documentation-results").execute(window.selected_paths(), "to:webp")
window.active_job = (window.selected_paths(), "to:webp")
window.on_finished(results, [])
window.navigate(0)
app.processEvents()
window.grab().save(str(output / "conversion-webp.png"))
window.navigate(2)
app.processEvents()
window.grab().save(str(output / "reglages-melina.png"))
window.navigate(3)
app.processEvents()
window.grab().save(str(output / "fonctionnalites.png"))

# A presentation graphic composed directly from real widget renders.
canvas = QPixmap(1440, 610)
canvas.fill(QColor("#0d171b"))
painter = QPainter(canvas)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
gradient = QLinearGradient(QPointF(0, 0), QPointF(1440, 610))
gradient.setColorAt(0, QColor("#241b23"))
gradient.setColorAt(0.55, QColor("#15262b"))
gradient.setColorAt(1, QColor("#194737"))
painter.fillRect(canvas.rect(), gradient)
painter.setPen(Qt.PenStyle.NoPen)
painter.setBrush(QColor("#f79062"))
painter.drawRoundedRect(QRectF(66, 52, 190, 38), 19, 19)
painter.setPen(QColor("#241b23"))
painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
painter.drawText(QRectF(66, 52, 190, 38), Qt.AlignmentFlag.AlignCenter, "WINDOWS · BÊTA")
painter.setPen(QColor("#ffffff"))
painter.setFont(QFont("Segoe UI", 53, QFont.Weight.Bold))
painter.drawText(64, 174, "Meloo")
painter.setFont(QFont("Segoe UI", 29, QFont.Weight.DemiBold))
painter.drawText(66, 246, "Glissez. Ctrl. Déposez.")
painter.setFont(QFont("Segoe UI", 17))
painter.setPen(QColor("#c8d6d7"))
painter.drawText(68, 296, "Convertir et compresser ses fichiers")
painter.drawText(68, 328, "directement sur son PC.")
painter.setFont(QFont("Segoe UI", 14))
painter.drawText(68, 418, "Une roue flottante · Deux thèmes")
painter.drawText(68, 448, "Images · PDF · Audio · Vidéo · Documents")
painter.setPen(QColor("#f4b49a"))
painter.setFont(QFont("Segoe UI", 12))
painter.drawText(68, 545, "Version expérimentale : peut contenir des erreurs.")
for theme, x, y, size in (("orange", 760, 80, 370), ("melina", 1020, 220, 340)):
    wheel = QPixmap(str(output / f"roue-{theme}.png"))
    wheel = wheel.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    painter.drawPixmap(x, y, wheel)
painter.end()
canvas.save(str(output / "meloo-beta.png"))
app.removeEventFilter(window)
window.hide()
window.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
print("Documentation images generated from Meloo widgets.")
