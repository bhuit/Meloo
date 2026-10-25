from __future__ import annotations
import ctypes
import json
import math
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QSize, QTimer, Signal, QObject, QThread, QUrl, QMimeData, QSettings, QEvent
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont, QPixmap, QIcon, QLinearGradient, QRadialGradient, QDrag, QDesktopServices, QShortcut, QKeySequence, QPalette
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QCheckBox, QProgressBar, QSystemTrayIcon, QMenu, QScrollArea, QAbstractItemView, QStackedWidget
from .catalog import Operation, operations, family, ACTIONS, IMAGE_EDITORS, feature_key
from .engine import Engine, Cancelled, ConversionError, office_path, unique_path, CREATE_NO_WINDOW, ROOT
from .preferences import load_settings
from .drag_gesture import DragGesture
from .native_input import WindowsInput
from .visuals import GlassStage, file_icon
from .themes import StyleSwitch, fruit_icon, current_style, melina_stylesheet

INK = "#f6f1e9"
MUTED = "#a29b91"
ORANGE = "#ff5c00"
STYLE = """
QWidget { background: transparent; color: #e7edf4; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QDialog { background: #0b111b; }
QLabel { background: transparent; }
QLabel#eyebrow { color: #b5c6d4; font-weight: 600; font-size: 10px; letter-spacing: 2px; }
QLabel#title { font-size: 29px; font-weight: 500; letter-spacing: -1px; }
QLabel#muted { color: #9eafc0; }
QLabel#brand { font-size: 23px; font-weight: 600; letter-spacing: 1px; }
QLabel#local { color: #9be9de; border: 1px solid #305a60; border-radius: 12px; padding: 5px 13px; font-size: 10px; }
QFrame#card, QFrame#quickbar { background: rgba(33,43,56,165); border: 1px solid rgba(186,210,227,38); border-radius: 14px; }
QFrame#header { background: rgba(9,15,25,125); border-bottom: 1px solid rgba(186,210,227,26); }
QPushButton { border: 1px solid #445363; border-radius: 8px; padding: 9px 13px; background: rgba(109,126,145,30); text-align: center; }
QPushButton:hover { background: rgba(122,169,179,60); border-color: #809ca9; }
QPushButton:pressed { background: #375b62; }
QPushButton:disabled { color: #72818f; border-color: #36434f; }
QPushButton#primary { color: #102d32; background: #9de3df; border-color: #b7ede8; font-weight: 600; }
QPushButton#primary:hover { background: #c2f4ed; }
QPushButton#tab { background: transparent; border: 0; padding: 7px 12px; color: #a6b7c7; }
QPushButton#tab:checked { background: rgba(133,190,190,35); color: #cff3ed; }
QPushButton#nav { border: 0; background: transparent; padding: 10px 15px; color: #a7b7c7; }
QPushButton#nav:checked { background: rgba(162,189,213,25); color: #e8f5fa; }
QListWidget { background: rgba(9,17,28,80); border: 1px solid rgba(188,211,228,28); border-radius: 12px; padding: 7px; outline: none; }
QListWidget::item { padding: 8px 5px; border-radius: 8px; margin: 3px; }
QListWidget::item:selected { background: rgba(113,195,190,45); color: #f0fffd; border: 1px solid #739f9f; }
QListWidget::item:hover { background: rgba(145,173,192,22); }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #172431; border: 1px solid #425464; border-radius: 7px; padding: 8px; min-height: 20px; }
QComboBox QAbstractItemView { background: #172431; selection-background-color: #355b62; }
QCheckBox { spacing: 10px; padding: 6px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QProgressBar { border: 0; border-radius: 3px; background: #2b414c; height: 5px; text-align: center; }
QProgressBar::chunk { background: #95e3de; border-radius: 3px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; }
QScrollBar::handle:vertical { background: #536775; min-height: 30px; border-radius: 4px; }
QMenu { background: #15212d; border: 1px solid #546878; padding: 6px; }
QMenu::item { padding: 9px 24px; }
QMenu::item:selected { background: #355a61; }
QToolTip { color: #ecf7fc; background: #263b49; border: 1px solid #688996; padding: 6px; }
"""


def label(text, style=None, wrap=False):
    w = QLabel(text)
    w.setTextFormat(Qt.TextFormat.PlainText)
    w.setWordWrap(wrap)
    if style: w.setObjectName(style)
    return w


def button(text, callback=None, style=None):
    w = QPushButton(text)
    if callback: w.clicked.connect(callback)
    if style: w.setObjectName(style)
    return w


def logo(size=64):
    return fruit_icon(size, current_style())


class FileList(QListWidget):
    filesAdded = Signal(list)
    def __init__(self, empty_text="Dépose tes fichiers ici"):
        super().__init__()
        self.empty_text = empty_text
        self.setIconSize(QSize(112,86))
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.TopToBottom)
        self.setWrapping(False)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setGridSize(QSize(214,136))
        self.setWordWrap(True)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(190)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.setDropAction(Qt.DropAction.CopyAction); event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.setDropAction(Qt.DropAction.CopyAction); event.accept()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        self.filesAdded.emit(paths)

    def startDrag(self, supported):
        paths = [i.data(Qt.ItemDataRole.UserRole) for i in self.selectedItems()]
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(logo(48).pixmap(48))
        drag.exec(Qt.DropAction.CopyAction)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            p = QPainter(self.viewport())
            p.setPen(QColor("#725348" if current_style() == "melina" else "#bdb8a5"))
            p.setFont(QFont("Segoe UI", 25))
            p.drawText(self.viewport().rect().adjusted(0, -40, 0, -40), Qt.AlignmentFlag.AlignCenter, "↓")
            p.setFont(QFont("Segoe UI", 12))
            p.drawText(self.viewport().rect().adjusted(0, 27, 0, 27), Qt.AlignmentFlag.AlignCenter, self.empty_text)
            p.end()


from .radial import Wheel
from .result_panel import ResultPanel


class Worker(QObject):
    progress = Signal(int, str)
    finished = Signal(list, list)
    failed = Signal(str)
    done = Signal()
    def __init__(self, paths, op, options, output):
        super().__init__()
        self.paths, self.op, self.options, self.output = paths, op, options, output
        self.cancel_event = threading.Event()

    def run(self):
        try:
            engine = Engine(self.cancel_event, self.progress.emit, self.output)
            results = engine.execute(self.paths, self.op, self.options)
            self.finished.emit(results, engine.warnings)
        except Cancelled as e: self.failed.emit(str(e))
        except Exception as e: self.failed.emit(str(e))
        finally: self.done.emit()


PARAMS = {
    "frame_image": [("padding", "Marge en pixels", 80, 0, 4000), ("radius", "Arrondi en pixels", 24, 0, 2000), ("background", "Couleur du fond (ex. #e8e0d8)", "#e8e0d8", 0, 0), ("shadow", "Ajouter une ombre", True, 0, 1)],
    "redact_video": [("x", "Position X", 0, 0, 30000), ("y", "Position Y", 0, 0, 30000), ("width", "Largeur du masque", 100, 2, 30000), ("height", "Hauteur du masque", 100, 2, 30000), ("start", "Début (secondes)", 0.0, 0, 86400), ("end", "Fin (secondes)", 1.0, .1, 86400)],
    "edit_metadata": [("author", "Auteur", "", 0, 0), ("title", "Titre", "", 0, 0), ("comment", "Commentaire / sujet", "", 0, 0)],
    "compress": [("quality", "Qualité image (1–100)", 82, 1, 100), ("target_mb", "Poids cible en Mo (0 = automatique)", 0.0, 0, 100000), ("percent", "% du poids d’origine (0 = ignoré)", 0, 0, 99), ("crf", "Compression vidéo (haut = plus léger)", 28, 15, 45)],
    "resize": [("width", "Largeur en pixels", 1600, 1, 30000), ("height", "Hauteur (0 = proportionnelle)", 0, 0, 30000)],
    "rotate": [("angle", "Rotation horaire en degrés", 90, -360, 360)],
    "rotate_pdf": [("angle", "Rotation horaire : 90, 180 ou 270°", 90, 0, 270)],
    "trim": [("start", "Début en secondes", 0.0, 0, 86400), ("duration", "Durée à conserver en secondes", 10.0, .1, 86400)],
    "snapshot": [("start", "Position en secondes", 0.0, 0, 86400)],
    "crop_video": [("x", "Position X", 0, 0, 30000), ("y", "Position Y", 0, 0, 30000), ("width", "Largeur", 640, 2, 30000), ("height", "Hauteur", 480, 2, 30000)],
    "speed": [("speed", "Multiplicateur de vitesse", 1.5, .25, 4)],
    "channels": [("channels", "Canaux : 1 = mono, 2 = stéréo", 1, 1, 2)],
    "split_media": [("segment", "Durée de chaque segment (secondes)", 30.0, 1, 86400)],
    "bleep": [("start", "Début du bip (secondes)", 0.0, 0, 86400), ("end", "Fin du bip (secondes)", 1.0, .1, 86400)],
    "collage": [("columns", "Nombre de colonnes", 2, 1, 8)],
    "reorder_pdf": [("pages", "Ordre des pages (ex. 3,1,2-5)", "1", 0, 0)],
    "redact_pdf": [("text", "Texte à supprimer dans toutes les pages", "", 0, 0)],
}
PARAMS["frame_image"] += [("background_image", "Image de fond (facultative)", "", 0, 0), ("background_blur", "Flou du fond", 0.0, 0, 100)]
PARAMS["normalize"] = [("loudness", "Volume cible (LUFS)", -16.0, -50, -5), ("true_peak", "Crête maximale (dBTP)", -1.5, -9, 0), ("loudness_range", "Plage dynamique (LU)", 11.0, 1, 50)]
PARAMS["visualizer"] = [("width", "Largeur (pixels, nombre pair)", 1280, 160, 3840), ("height", "Hauteur (pixels, nombre pair)", 720, 90, 2160), ("color", "Couleur de l’onde", "#ff5c00", 0, 0), ("background", "Couleur du fond", "#15151d", 0, 0)]
PARAMS["collage"] += [("cell", "Largeur d’une case (pixels)", 640, 32, 4000), ("gap", "Espacement (pixels)", 20, 0, 500), ("radius", "Coins arrondis (pixels)", 0, 0, 500), ("background", "Couleur du fond", "#ffffff", 0, 0)]
PARAMS["snapshot"] += [("times", "Autres positions en secondes (ex. 1,2.5,8)", "", 0, 0)]
PARAMS["split_media"] += [("points", "Points de coupe en secondes (facultatif : 3,8,12)", "", 0, 0)]
PARAMS["channels"] += [("left_gain", "Volume gauche", 1.0, 0, 3), ("right_gain", "Volume droite", 1.0, 0, 3)]
PARAMS["redact_video"] += [("blur", "Flouter la zone (sinon masque noir)", False, 0, 1)]


class OptionsDialog(QDialog):
    def __init__(self, op, paths, parent):
        super().__init__(parent)
        self.setWindowTitle("Réglages du traitement")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.addWidget(label("PRÉPARER LE TRAITEMENT", "eyebrow"))
        layout.addWidget(label(f"{len(paths)} fichier(s) · nouvelles copies", "muted"))
        form = QFormLayout()
        self.fields = {}
        self.op = op
        specs = list(PARAMS.get(op, []))
        if op == "edit_metadata":
            kind = family(paths[0])
            if Path(paths[0]).suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff"}: specs = [x for x in specs if x[0] != "title"] + [("datetime", "Date EXIF (AAAA:MM:JJ HH:MM:SS)", "", 0, 0)]
            elif kind == "pdf": specs = [("subject", "Sujet", "", 0, 0) if x[0] == "comment" else x for x in specs]
        if op in {"to:png", "to:jpg"} and family(paths[0]) == "pdf": specs = [("dpi", "Résolution en DPI", 300, 72, 600)]
        if op == "compress":
            kind = family(paths[0])
            if kind == "image": specs = [x for x in specs if x[0] != "crf"]
            elif kind == "audio": specs = [x for x in specs if x[0] in {"target_mb", "percent"}]
            elif kind == "pdf": specs = []
            else: specs = [x for x in specs if x[0] != "quality"]
        for key, title, default, low, high in specs:
            if isinstance(default, str): w = QLineEdit(default)
            elif isinstance(default, bool): w = QCheckBox(); w.setChecked(default)
            else:
                w = QDoubleSpinBox() if isinstance(default, float) else QSpinBox()
                w.setRange(low, high)
                w.setValue(default)
            self.fields[key] = w
            form.addRow(title, w)
            if key == "background_image":
                picker=button("Choisir une image…", lambda checked=False, field=w: self.pick_image(field))
                form.addRow("",picker)
        layout.addLayout(form)
        if op == "edit_metadata": layout.addWidget(label("Les champs laissés vides restent inchangés. Les modifications sont enregistrées dans une copie.", "muted", True))
        if op == "edit_metadata":
            from .extras import EMBEDDED_METADATA
            if any(Path(path).suffix.lower() not in EMBEDDED_METADATA for path in paths):
                layout.addWidget(label("Pour les formats sans édition intégrée, une fiche .metadata.json séparée sera créée. Elle ne modifie pas les métadonnées internes du fichier.","muted",True))
        if op == "compress": layout.addWidget(label("Un poids cible reste approximatif. Le pourcentage, s’il est renseigné, est prioritaire. PDF : optimisation sans perte.", "muted", True))
        if op == "to:pptx": layout.addWidget(label("Depuis un PDF, chaque page devient une image dans une diapositive.", "muted", True))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Lancer")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        values = {k: w.text() if isinstance(w, QLineEdit) else w.isChecked() if isinstance(w, QCheckBox) else w.value() for k, w in self.fields.items()}
        return {k:v for k,v in values.items() if v != ""} if self.op == "edit_metadata" else values

    def pick_image(self, field):
        path,_=QFileDialog.getOpenFileName(self,"Image de fond","","Images (*.png *.jpg *.jpeg *.webp *.heic *.tif *.bmp)")
        if path: field.setText(path)


class FloatWindow(QWidget):
    def __init__(self, paths):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Meloo · À portée")
        self.resize(300, 260)
        layout = QVBoxLayout(self)
        layout.addWidget(label("À PORTÉE DE MAIN", "eyebrow"))
        layout.addWidget(label("Glisse les éléments vers leur destination.", "muted", True))
        files = FileList()
        for path in paths:
            item = QListWidgetItem(Path(path).name)
            item.setData(Qt.ItemDataRole.UserRole, path)
            files.addItem(item)
        files.selectAll()
        layout.addWidget(files)


class DragWatcher(QObject):
    """Polls only key/button state. Never records typed text or clipboard data."""
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.popup = main.popup
        self.gesture = DragGesture()
        self.tab_down = False
        self.input = WindowsInput(main)
        self.opens = 0
        self.last_source = ''
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        if os.name == "nt":
            self.user = ctypes.windll.user32
            self.user.GetForegroundWindow.restype = ctypes.c_void_p
            self.user.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
            self.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self.user.GetAsyncKeyState.restype = ctypes.c_short
            from ctypes import wintypes
            self.user.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            self.user.WindowFromPoint.argtypes = [wintypes.POINT]
            self.user.WindowFromPoint.restype = wintypes.HWND
            self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            self.user.GetAncestor.restype = wintypes.HWND
            self.timer.setTimerType(Qt.TimerType.PreciseTimer)
            self.timer.start(16)

    def down(self, key):
        if self.input.active: return self.input.state.down(key)
        return bool(self.user.GetAsyncKeyState(key) & 0x8000)

    def poll(self):
        from PySide6.QtGui import QCursor
        if QApplication.activeModalWidget() is not None:
            # A deliberate advanced-tool dialog must never leave a disabled
            # wheel on top of it, where drops would seem to stop responding.
            self.popup.hide()
            self.gesture.update(pressed=False, ctrl=False, altgr=False, escape=False,
                                source_ok=False, position=(0,0), now=time.monotonic())
            return
        enabled = self.main.settings.value("global_drag", True, bool)
        escape = self.down(0x1B)
        if escape and self.popup.isVisible(): self.popup.hide()
        if self.popup.isVisible():
            tab = self.down(0x09)
            # Qt handles keys synchronously while our application is active.
            # Poll only for drags from Explorer, avoiding two changes per Tab.
            if tab and not self.tab_down and QApplication.activeWindow() is None:
                self.popup.cycle_mode()
            self.tab_down = tab
        point = QCursor.pos()
        buf = ctypes.create_unicode_buffer(256)
        self.user.GetClassNameW(self.user.GetForegroundWindow(), buf, 256)
        sources = {"CabinetWClass", "ExploreWClass", "Progman", "WorkerW"}
        source_ok = buf.value in sources
        # The mouse press can arrive before Explorer becomes foreground.
        # Use the root actually under the pointer at the start of the drag too.
        if self.gesture.origin is None:
            from ctypes import wintypes
            physical = wintypes.POINT()
            self.user.GetCursorPos(ctypes.byref(physical))
            root = self.user.GetAncestor(self.user.WindowFromPoint(physical), 2)
            under_pointer = ctypes.create_unicode_buffer(256)
            self.user.GetClassNameW(root, under_pointer, 256)
            source_ok = source_ok or under_pointer.value in sources
            self.last_source = under_pointer.value
        # Respect left-handed mouse settings. Ctrl may be released once opened.
        primary = 0x02 if self.user.GetSystemMetrics(23) else 0x01
        signal = self.gesture.update(
            pressed=self.down(primary), ctrl=self.down(0xA2) or self.down(0xA3),
            altgr=self.down(0xA5), escape=escape,
            source_ok=source_ok,
            position=(point.x(), point.y()), now=time.monotonic(), enabled=enabled)
        if signal == "cancel": self.popup.hide()
        if signal == "release":
            session = self.gesture.session
            # Deliver the native Drop event before hiding; an old callback must
            # never dismiss a wheel subsequently opened by another gesture/F8.
            QTimer.singleShot(120, lambda: self.popup.hide() if self.popup.drag_session == session else None)
        if signal != "open": return
        self.opens += 1
        self.popup.drag_session = self.gesture.session
        self.popup.set_files([])
        self.popup.set_mode("quick")
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x = max(area.left(), min(point.x()-self.popup.width()//2, area.right()-self.popup.width()+1))
        y = max(area.top(), min(point.y()-self.popup.height()//2, area.bottom()-self.popup.height()+1))
        self.popup.move(x, y)
        self.popup.show()
        self.popup.raise_()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meloo — Vos fichiers, un geste suffit")
        self.setWindowIcon(logo())
        self.resize(1180, 820)
        self.setMinimumSize(1000, 720)
        self.settings = load_settings()
        # Wheel-only is the default resident workflow. The results panel and
        # startup balloon remain opt-in through the tray settings.
        if not self.settings.value("wheel_only_migrated", False, bool):
            self.settings.setValue("hud", False)
            self.settings.setValue("background_hint_shown", True)
            self.settings.setValue("wheel_only_migrated", True)
        office = self.settings.value("office", "")
        if office and Path(office).is_file(): os.environ["ZESTE_LIBREOFFICE"] = office
        self.thread = None
        self.worker = None
        self.pending = []
        self.floats = []
        self.last_outputs = []
        self.popup = Wheel(popup=True, enabled=self.feature_enabled)
        self.result_panel = ResultPanel()
        self.result_panel.revealRequested.connect(self.reveal)
        self.result_panel.openRequested.connect(self.show_main)
        self.result_panel.cancelRequested.connect(self.cancel_job)
        self.popup.activated.connect(self.defer_operation)
        self.popup.filesChanged.connect(self.add_files)
        central = GlassStage()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0,0,0,0);root.setSpacing(0)
        header=QFrame();header.setObjectName("header")
        bar=QHBoxLayout(header);bar.setContentsMargins(26,14,26,14);bar.setSpacing(8)
        self.brand_mark=QLabel();self.brand_mark.setPixmap(logo(30).pixmap(30));bar.addWidget(self.brand_mark)
        bar.addWidget(label("Meloo", "brand"));bar.addSpacing(22)
        self.navs=[]
        for i,name in enumerate(["Atelier","Historique","Réglages","Fonctions"]):
            b=button(name,lambda checked=False,index=i:self.navigate(index),"nav")
            b.setCheckable(True);bar.addWidget(b);self.navs.append(b)
        bar.addStretch();bar.addWidget(label("●  TRAITEMENT LOCAL", "local"))
        root.addWidget(header)
        self.stack=QStackedWidget();root.addWidget(self.stack,1)
        self.build_workshop()
        self.build_history()
        self.build_settings()
        from .feature_settings import FeatureSettings
        self.features = FeatureSettings(self.settings, self)
        self.features.changed.connect(self.refresh_features)
        self.stack.addWidget(self.features)
        self.navigate(0)
        self.tray = QSystemTrayIcon(logo(), self)
        self.tray_menu = menu = QMenu(self)
        self.tray_status = menu.addAction("Prêt · glisser un fichier puis Ctrl")
        self.tray_status.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Afficher la roue", self.show_popup)
        menu.addAction("Réglages", lambda: self.show_page(2))
        menu.addAction("Fonctionnalités…", lambda: self.show_page(3))
        menu.addAction("Atelier avancé", lambda: self.show_page(0))
        menu.addAction("Derniers résultats", lambda: self.result_panel.finished(self.last_outputs, []) if self.last_outputs else self.show_page(1))
        menu.addAction("Quitter", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Meloo · Glisser un fichier, puis Ctrl · Convertir / Compresser")
        self.tray.activated.connect(lambda why: self.show_popup() if why == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self.tray.show()
        self.watcher = DragWatcher(self)
        QShortcut(QKeySequence("Ctrl+O"), self, self.pick_files)
        QShortcut(QKeySequence("Delete"), self.files, self.remove_files)
        QShortcut(QKeySequence("F8"), self, self.show_popup)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.quit_app)
        QShortcut(QKeySequence("Escape"), self, self.popup.hide)
        QApplication.instance().installEventFilter(self)
        self.load_history()
        self.apply_appearance()

    def build_workshop(self):
        page=QWidget()
        layout=QVBoxLayout(page);layout.setContentsMargins(28,20,28,20);layout.setSpacing(14)
        headline=label("Glisse. Transforme. C’est prêt.","title");headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(headline)
        subtitle=label("Glisse un fichier · Appuie sur Ctrl · Dépose-le sur un format", "muted")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(subtitle)
        body=QHBoxLayout();body.setSpacing(26)
        left=QVBoxLayout();left.setSpacing(10)
        left.addWidget(label("FICHIERS À TRANSFORMER", "eyebrow"))
        self.files=FileList();self.files.setFixedWidth(240)
        self.files.filesAdded.connect(self.add_files);self.files.itemSelectionChanged.connect(self.selection_changed)
        left.addWidget(self.files,1)
        self.count_label=label("Aucun fichier", "muted");left.addWidget(self.count_label)
        rows=QHBoxLayout();rows.addWidget(button("+ Ajouter",self.pick_files));rows.addWidget(button("Dossier",self.pick_folder))
        left.addLayout(rows)
        rows=QHBoxLayout();rows.addWidget(button("Retirer",self.remove_files));rows.addWidget(button("Vider",self.clear_files));left.addLayout(rows)
        body.addLayout(left)
        center=QVBoxLayout();center.setSpacing(10)
        title=label("CENTRE DE CONVERSION", "eyebrow");title.setAlignment(Qt.AlignmentFlag.AlignCenter);center.addWidget(title)
        tabs=QHBoxLayout();tabs.addStretch();self.tabs={}
        for mode,title in [("convert","Convertir"),("tools","Outils"),("actions","Actions")]:
            b=button(title,lambda checked=False,mode=mode:self.set_mode(mode),"tab")
            b.setCheckable(True);self.tabs[mode]=b;tabs.addWidget(b)
        tabs.addStretch();center.addLayout(tabs)
        self.wheel=Wheel(enabled=self.feature_enabled);self.wheel.setStyleSheet("background:transparent;")
        self.wheel.activated.connect(self.defer_operation);self.wheel.filesChanged.connect(self.add_files)
        center.addWidget(self.wheel,1)
        self.action_picker=QComboBox();center.addWidget(self.action_picker)
        self.run_button=button("Lancer la transformation  ↗",self.run_selected,"primary");center.addWidget(self.run_button)
        quick_label=label("ACTIONS RAPIDES", "eyebrow");quick_label.setAlignment(Qt.AlignmentFlag.AlignCenter);center.addWidget(quick_label)
        quick=QFrame();quick.setObjectName("quickbar");row=QHBoxLayout(quick);row.setContentsMargins(7,7,7,7);row.setSpacing(6)
        self.quick_compress=button("Compresser",lambda:self.request_operation("compress",self.selected_paths(),quick=True))
        self.quick_edit=button("Retoucher",lambda:self.request_operation("edit_image",self.selected_paths()))
        row.addWidget(self.quick_compress);row.addWidget(self.quick_edit);row.addWidget(button("Fonctions",lambda:self.show_page(3)))
        center.addWidget(quick);body.addLayout(center,1)
        right=QVBoxLayout();right.setSpacing(10)
        right.addWidget(label("GALERIE DES RÉSULTATS", "eyebrow"))
        self.gallery=FileList("Tes résultats apparaîtront ici");self.gallery.setFixedWidth(240)
        self.gallery.setAcceptDrops(False);self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.gallery.itemDoubleClicked.connect(lambda item:self.reveal(item.data(Qt.ItemDataRole.UserRole)))
        right.addWidget(self.gallery,1)
        right.addWidget(label("Double-clic pour retrouver un fichier", "muted",True))
        self.results_button=button("Afficher le dernier résultat  ↗",self.open_result);self.results_button.setEnabled(False)
        right.addWidget(self.results_button);right.addWidget(button("Tout l’historique",lambda:self.navigate(1)))
        body.addLayout(right);layout.addLayout(body,1)
        self.status_card=QFrame();self.status_card.setObjectName("card")
        status=QVBoxLayout(self.status_card);status.setContentsMargins(16,10,16,10);status.setSpacing(5)
        row=QHBoxLayout();self.status_text=label("Prêt à transformer tes fichiers", "muted");self.status_text.setWordWrap(True)
        row.addWidget(self.status_text,1);self.cancel_button=button("Annuler",self.cancel_job);self.cancel_button.setVisible(False);row.addWidget(self.cancel_button)
        status.addLayout(row)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0);self.progress.setTextVisible(False);self.progress.setFixedHeight(3);status.addWidget(self.progress)
        self.notice=label("Tes originaux sont conservés. Les nouvelles copies restent sur ton PC.","muted",True);status.addWidget(self.notice)
        layout.addWidget(self.status_card)
        self.stack.addWidget(page);self.set_mode("convert")

    def build_history(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 30)
        layout.addWidget(label("LES DERNIERS GESTES", "eyebrow"))
        layout.addWidget(label("Historique", "title"))
        layout.addWidget(label("Double-clique sur un résultat pour le retrouver. Les erreurs sont conservées ici.", "muted", True))
        self.history = QListWidget()
        self.history.itemDoubleClicked.connect(self.open_history)
        layout.addWidget(self.history)
        layout.addWidget(button("Effacer l’historique", self.clear_history))
        self.stack.addWidget(page)

    def build_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 36, 36, 30)
        layout.setSpacing(18)
        layout.addWidget(label("À TA FAÇON", "eyebrow"))
        layout.addWidget(label("Réglages", "title"))
        layout.addWidget(button("Activer ou désactiver les fonctionnalités…",lambda: self.navigate(3)))
        self.global_check = QCheckBox("Afficher la roue : Ctrl pendant un glissement dans l’Explorateur ou sur le Bureau")
        self.global_check.setChecked(self.settings.value("global_drag", True, bool))
        self.global_check.toggled.connect(lambda b: self.settings.setValue("global_drag", b))
        layout.addWidget(self.global_check)
        layout.addWidget(label("Glisse un fichier, appuie sur Ctrl, puis relâche Ctrl : la roue reste ouverte jusqu’au dépôt. ZIP reste en haut ; les formats de destination gardent leurs places. Tab : outils / actions. Échap : annuler. AltGr n’est pas utilisé.", "muted", True))
        layout.addWidget(label("Compresser dans la première roue lance directement la compression automatique. Pour choisir un poids cible : Tab → Outils → Compresser.", "muted", True))
        self.tray_check = QCheckBox("Continuer dans la zone de notification quand je ferme la fenêtre")
        self.tray_check.setChecked(self.settings.value("tray", True, bool))
        self.tray_check.toggled.connect(lambda b: self.settings.setValue("tray", b))
        layout.addWidget(self.tray_check)
        self.hud_check = QCheckBox("Afficher les traitements et résultats en haut de l’écran")
        self.hud_check.setChecked(self.settings.value("hud", False, bool))
        self.hud_check.toggled.connect(lambda b: self.settings.setValue("hud", b))
        layout.addWidget(self.hud_check)
        style_card = QFrame(); style_card.setObjectName("card")
        style_row = QHBoxLayout(style_card); style_row.setContentsMargins(16, 10, 16, 10)
        style_row.addWidget(label("STYLE DE MELOO", "eyebrow")); style_row.addStretch()
        style_row.addWidget(label("Orange"))
        self.style_switch = StyleSwitch()
        self.style_switch.setChecked(self.settings.value("color_style", "orange") == "melina")
        self.style_switch.toggled.connect(lambda checked: self.set_appearance("color_style", "melina" if checked else "orange"))
        style_row.addWidget(self.style_switch)
        style_row.addWidget(label("Melina · Pastèque"))
        layout.addWidget(style_card)
        appearance = QHBoxLayout()
        appearance.addWidget(label("Apparence"))
        self.theme_picker = QComboBox()
        self.theme_picker.addItems(["Sombre", "Claire"])
        self.theme_picker.setCurrentIndex(1 if self.settings.value("light", False, bool) else 0)
        self.theme_picker.currentIndexChanged.connect(lambda i: self.set_appearance("light", bool(i)))
        appearance.addWidget(self.theme_picker, 1)
        self.melina_light = label("Claire · palette Melina", "muted")
        appearance.addWidget(self.melina_light, 1)
        self.motion_check = QCheckBox("Réduire les animations")
        self.motion_check.setChecked(self.settings.value("reduce_motion", False, bool))
        self.motion_check.toggled.connect(lambda b: self.set_appearance("reduce_motion", b))
        appearance.addWidget(self.motion_check)
        layout.addLayout(appearance)
        self.appearance_note = label("", "muted", True)
        layout.addWidget(self.appearance_note)
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(label("Opacité du verre (100 % = référence)"))
        self.glass_opacity = QSpinBox()
        self.glass_opacity.setRange(55, 125)
        self.glass_opacity.setSuffix(" %")
        self.glass_opacity.setValue(self.settings.value("glass_strength", 100, int))
        self.glass_opacity.valueChanged.connect(lambda value: self.set_appearance("glass_strength", value))
        opacity_row.addWidget(self.glass_opacity)
        layout.addLayout(opacity_row)
        self.startup_check = QCheckBox("Lancer Meloo dans la zone de notification à l’ouverture de Windows")
        self.startup_check.setChecked(self.settings.value("startup", False, bool))
        self.startup_check.toggled.connect(self.set_startup)
        layout.addWidget(self.startup_check)
        self.output_label = label("Sorties : " + (self.settings.value("output", "") or "à côté des originaux"), "muted", True)
        layout.addWidget(self.output_label)
        row = QHBoxLayout()
        row.addWidget(button("Choisir un dossier de sortie", self.choose_output))
        row.addWidget(button("À côté des originaux", self.reset_output))
        layout.addLayout(row)
        layout.addWidget(label("DOCUMENTS OFFICE", "eyebrow"))
        self.office_label = label("LibreOffice détecté" if office_path() else "LibreOffice absent : présentations et anciens formats Office indisponibles.", "muted", True)
        layout.addWidget(self.office_label)
        layout.addWidget(button("Choisir soffice.exe…", self.choose_office))
        layout.addWidget(label("PDF → PowerPoint : diapositives en images. PDF → Excel : tableaux détectables. Pas de sortie Apple Pages ni d’OCR automatique. Les fichiers GIF sont traités comme une image fixe dans les outils photo.", "muted", True))
        layout.addStretch()
        layout.addWidget(label("Meloo est une application indépendante pour Windows.\nTraitement local · aucune connexion de compte requise · aucun abonnement", "muted", True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.stack.addWidget(scroll)

    def set_appearance(self, key, value):
        self.settings.setValue(key, value)
        self.settings.sync()
        self.apply_appearance()

    def feature_enabled(self, key):
        return self.settings.value("features/"+key, True, bool)

    def refresh_features(self):
        self.popup.refresh(); self.wheel.refresh(); self.update_picker()

    def run_dialog(self, dialog):
        self.popup.page_timer.stop(); self.popup.hide()
        dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True)
        from .window_visibility import ensure_native_visible
        QTimer.singleShot(0, dialog, lambda:(ensure_native_visible(dialog),dialog.raise_(),dialog.activateWindow()))
        return dialog.exec() == QDialog.DialogCode.Accepted

    def apply_appearance(self):
        color_style = "melina" if self.settings.value("color_style", "orange") == "melina" else "orange"
        melina = color_style == "melina"
        app = QApplication.instance()
        app.setProperty("color_style", color_style)
        icon = fruit_icon(64, color_style)
        app.setWindowIcon(icon); self.setWindowIcon(icon); self.tray.setIcon(icon)
        self.brand_mark.setPixmap(fruit_icon(30, color_style).pixmap(30))
        self.tray.setToolTip(f"Meloo · {'Melina' if melina else 'Orange'} · Glisser un fichier, puis Ctrl")
        self.theme_picker.setEnabled(not melina)
        self.theme_picker.setVisible(not melina); self.melina_light.setVisible(melina)
        if app.property("orange_palette") is None: app.setProperty("orange_palette", app.palette())
        palette = QPalette(app.property("orange_palette"))
        if melina:
            for role,color in [(QPalette.ColorRole.Window,"#eceddf"),(QPalette.ColorRole.WindowText,"#4a302d"),(QPalette.ColorRole.Text,"#4a302d"),(QPalette.ColorRole.ButtonText,"#4a302d"),(QPalette.ColorRole.Button,"#e8ead8"),(QPalette.ColorRole.Base,"#f4f2e4"),(QPalette.ColorRole.Highlight,"#b6d5bb"),(QPalette.ColorRole.HighlightedText,"#4a302d")]: palette.setColor(role,QColor(color))
        app.setPalette(palette)
        self.appearance_note.setText("Melina : rose pastèque, vert menthe et verre translucide. Le centre de la roue permet de la déplacer." if melina else "Style Orange d’origine. Le centre de la roue sert de poignée pour la déplacer.")
        light = self.settings.value("light", False, bool)
        reduced = self.settings.value("reduce_motion", False, bool)
        for wheel in [self.wheel, self.popup]:
            wheel.color_style = color_style
            wheel.light = light
            wheel.reduce_motion = reduced
            wheel.glass_strength = self.settings.value("glass_strength", 100, int) / 100
            wheel.update()
        self.result_panel.reduce_motion = reduced
        self.result_panel.set_theme(color_style)
        self.centralWidget().color_style = color_style
        for files in self.findChildren(FileList):
            for i in range(files.count()):
                item = files.item(i)
                path = item.data(Qt.ItemDataRole.UserRole)
                if path: item.setIcon(file_icon(path))
            files.viewport().update()
        self.centralWidget().light=light;self.centralWidget().update()
        style = STYLE
        if melina:
            style = melina_stylesheet(style)
        elif light:
            colors = {"#e7edf4":"#203442", "#0b111b":"#e7edf2", "#b5c6d4":"#426272", "#9eafc0":"#4f6575", "#a7b7c7":"#425d70", "#e8f5fa":"#173e4c", "#a6b7c7":"#506878", "#cff3ed":"#174c4f", "#172431":"#eef4f7", "#15212d":"#edf3f6", "#263b49":"#dfeaf0", "#ecf7fc":"#173744"}
            colors.update({"rgba(33,43,56,165)":"rgba(255,255,255,175)", "rgba(9,15,25,125)":"rgba(244,248,252,185)", "rgba(9,17,28,80)":"rgba(255,255,255,100)", "#9be9de":"#215c62"})
            for old,new in colors.items(): style=style.replace(old,new)
        QApplication.instance().setStyleSheet(style)

    def set_startup(self, enabled):
        if os.name != "nt": return
        import sys, winreg
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                if enabled:
                    executable = Path(sys.executable)
                    args = [str(executable), "--tray"]
                    if not getattr(sys, "frozen", False):
                        candidate = executable.with_name("pythonw.exe")
                        args = [str(candidate if candidate.exists() else executable), str(ROOT / "main.py"), "--tray"]
                    winreg.SetValueEx(key, "ZesteWindows", 0, winreg.REG_SZ, subprocess.list2cmdline(args))
                else:
                    try: winreg.DeleteValue(key, "ZesteWindows")
                    except FileNotFoundError: pass
            self.settings.setValue("startup", enabled)
        except OSError as exc:
            self.startup_check.blockSignals(True);self.startup_check.setChecked(not enabled);self.startup_check.blockSignals(False)
            QMessageBox.warning(self, "Démarrage Windows", str(exc))

    def navigate(self, index):
        self.popup.hide()
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.navs): b.setChecked(i == index)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and self.popup.isVisible() and event.key() == Qt.Key.Key_Escape:
            self.popup.hide()
            return True
        if event.type() == QEvent.Type.KeyPress and self.popup.isVisible() and event.key() == Qt.Key.Key_Tab:
            if not event.isAutoRepeat():
                self.popup.cycle_mode()
            return True
        if event.type() == QEvent.Type.MouseButtonPress and self.popup.isVisible() and isinstance(watched, QWidget) and watched.window() != self.popup:
            self.popup.hide()
        return super().eventFilter(watched, event)

    def selected_paths(self):
        selected = self.files.selectedItems()
        return [i.data(Qt.ItemDataRole.UserRole) for i in (selected or [self.files.item(i) for i in range(self.files.count())])]

    def add_files(self, paths):
        existing = {self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())}
        self.files.blockSignals(True)
        for value in paths:
            p = Path(value)
            if not p.exists() or str(p.resolve()) in existing: continue
            p = p.resolve()
            size = "dossier" if p.is_dir() else f"{p.stat().st_size/1024**2:.2f} Mo"
            item = QListWidgetItem(f"{p.name}\n{p.suffix.upper().lstrip('.') or 'DOSSIER'}  ·  {size}")
            item.setIcon(file_icon(p))
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            item.setToolTip(str(p))
            self.files.addItem(item)
            existing.add(str(p))
        self.files.blockSignals(False)
        self.selection_changed()

    def selection_changed(self):
        paths = self.selected_paths()
        self.wheel.set_files(paths)
        if not self.thread: self.wheel.set_progress()
        self.count_label.setText(f"{len(paths)} sélectionné(s) · {self.files.count()} au total")
        self.update_picker()

    def update_picker(self):
        self.action_picker.clear()
        for op in self.wheel.items:
            self.action_picker.addItem(f"{op.icon}  {op.label}", op.id)
        self.run_button.setEnabled(bool(self.wheel.items))
        paths=self.selected_paths()
        self.quick_compress.setEnabled(bool(paths) and self.feature_enabled(feature_key(paths,"compress")))
        self.quick_edit.setEnabled(len(paths)==1 and family(paths[0])=="image" and self.feature_enabled("image/edit_image"))

    def set_mode(self, mode):
        self.wheel.set_mode(mode)
        for key, b in self.tabs.items(): b.setChecked(key == mode)
        self.update_picker()

    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Ajouter des fichiers")
        self.add_files(paths)

    def pick_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Ajouter un dossier")
        if path: self.add_files([path])

    def remove_files(self):
        for item in self.files.selectedItems(): self.files.takeItem(self.files.row(item))
        self.selection_changed()

    def clear_files(self): self.files.clear(); self.selection_changed()

    def run_selected(self):
        op = self.action_picker.currentData()
        if op: self.request_operation(op, self.selected_paths())

    def defer_operation(self, op, paths):
        # Leave the native OLE drag loop before opening dialogs or starting jobs.
        quick = self.popup.mode == "quick"
        self.popup.page_timer.stop()
        self.popup.hide()
        self.popup.drag_session = None
        def dispatch():
            try: self.request_operation(op, paths, quick=quick)
            except Exception as exc:
                # Qt callbacks otherwise only write to stderr (hidden in a
                # resident GUI executable), losing the diagnostic completely.
                message = str(exc) or type(exc).__name__
                self.add_history(op, [], message, False)
                self.report_tray_status("Échec : " + message)
                self.popup.hide()
        QTimer.singleShot(0, dispatch)

    def request_operation(self, op, paths, quick=False):
        if not paths: return
        if not self.feature_enabled(feature_key(paths,op)):
            self.report_tray_status("Fonction désactivée dans les paramètres."); return
        self.navigate(0)
        if op in {x.id for x in ACTIONS} and op not in {"checksum", "duplicate"}:
            self.file_action(op, paths)
            return
        options = {}
        if quick and op == "compress":
            options = {"quality": 82, "crf": 28}
        elif quick and op.startswith("to:"):
            # A drop is the user's confirmation. In particular PDF -> PPTX
            # needs no modal information dialog behind the hidden workshop.
            options = {"dpi": 200} if family(paths[0]) == "pdf" and op in {"to:png", "to:jpg"} else {}
        elif op in IMAGE_EDITORS:
            from .image_editor import ImageEditor
            if len(paths) != 1:
                QMessageBox.information(self, "Retouche", "Sélectionne une seule image pour la retouche visuelle.")
                return
            try: dialog = ImageEditor(paths[0], self, initial=op, enabled=self.feature_enabled)
            except Exception as exc: QMessageBox.warning(self, "Image", str(exc)); return
            if not self.run_dialog(dialog): return
            options = dialog.options()
        elif op == "reorder_pdf":
            from .pdf_organizer import PdfOrganizer
            dialog=PdfOrganizer(paths[0],self)
            if not self.run_dialog(dialog): return
            options=dialog.options()
        elif op in {"merge_pdf","join_media"}:
            from .pdf_organizer import FileOrderDialog
            dialog=FileOrderDialog(paths,self)
            if not self.run_dialog(dialog): return
            paths=dialog.paths()
        elif op in PARAMS or (op in {"to:jpg", "to:png"} and family(paths[0]) == "pdf"):
            dialog = OptionsDialog(op, paths, self)
            if not self.run_dialog(dialog): return
            options = dialog.values()
        self.pending.append((list(paths), op, options))
        self.start_next()

    def start_next(self):
        if self.thread or not self.pending: return
        paths, op, opts = self.pending.pop(0)
        self.active_job = (paths, op)
        self.worker = Worker(paths, op, opts, self.settings.value("output", ""))
        self.thread = QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.cleanup_thread)
        self.cancel_button.setVisible(True)
        self.progress.setRange(0, 0)
        self.wheel.set_progress(0,True)
        self.status_text.setText(f"En cours · {Path(paths[0]).name}")
        if self.settings.value("hud", False, bool): self.result_panel.working(Path(paths[0]).name)
        self.thread.start()

    def on_progress(self, value, text):
        self.wheel.set_progress(value,True)
        self.progress.setRange(0,100);self.progress.setValue(value)
        self.status_text.setText(f"{text}  ·  {len(self.pending)} en attente")
        self.result_panel.update_progress(text)

    def on_finished(self, outputs, warnings):
        self.last_outputs = outputs
        self.wheel.set_progress(100,False)
        self.results_button.setEnabled(bool(outputs))
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status_text.setText(f"✓ {len(outputs)} résultat(s) enregistré(s)" + (" · " + warnings[0] if warnings else ""))
        self.add_history(self.active_job[1], outputs, "\n".join(warnings), True)
        if warnings: self.notice.setText("\n".join(warnings))
        else: self.notice.setText("Les nouvelles copies sont prêtes. Tes originaux sont conservés.")
        self.report_tray_status(warnings[0] if warnings else f"{len(outputs)} résultat(s) prêt(s)")
        if self.settings.value("hud", False, bool): self.result_panel.finished(outputs, warnings)

    def on_failed(self, error):
        self.wheel.set_progress()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_text.setText("Traitement interrompu · consulte l’historique")
        self.notice.setText(error[-600:])
        self.add_history(self.active_job[1], [], error, False)
        self.report_tray_status("Échec : " + error)
        if self.settings.value("hud", False, bool): self.result_panel.failed(error)

    def report_tray_status(self, message):
        # Keep wheel-only mode: status is available on hover/right-click of
        # the tray icon, without a modal popup or extra results window.
        self.tray.setToolTip(("Meloo · " + message)[:240])
        self.tray_status.setText(message[:150].replace("&", "&&"))

    def cleanup_thread(self):
        old = self.thread
        self.thread = None
        self.worker = None
        old.deleteLater()
        self.cancel_button.setVisible(False)
        QTimer.singleShot(0, self.start_next)

    def cancel_job(self):
        self.pending.clear()
        if self.worker: self.worker.cancel_event.set(); self.status_text.setText("Annulation demandée…")

    def add_history(self, op, paths, detail, success):
        record = {"time": time.strftime("%d/%m %H:%M"), "operation": op, "outputs": paths, "detail": detail, "success": success}
        self.history_records.insert(0, record)
        self.history_records = self.history_records[:100]
        self.render_history()
        self.settings.setValue("history", json.dumps(self.history_records, ensure_ascii=False))

    def load_history(self):
        try: self.history_records = json.loads(self.settings.value("history", "[]"))
        except (ValueError, TypeError): self.history_records = []
        self.render_history()

    def render_history(self):
        self.history.clear()
        self.gallery.clear()
        seen=set()
        for r in self.history_records:
            item = QListWidgetItem(f"{'✓' if r['success'] else '×'}  {r['time']}   ·   {r['operation']}\n{len(r['outputs'])} résultat(s)" + (f"\n{r['detail'][:230]}" if r['detail'] else ""))
            item.setData(Qt.ItemDataRole.UserRole, r)
            item.setToolTip(r['detail'] or "\n".join(r['outputs']))
            self.history.addItem(item)
            for path in r["outputs"]:
                if path in seen or len(seen)>=30 or not Path(path).is_file(): continue
                seen.add(path)
                result=QListWidgetItem(file_icon(path),Path(path).name)
                result.setData(Qt.ItemDataRole.UserRole,path);result.setToolTip(path)
                self.gallery.addItem(result)

    def clear_history(self): self.history_records = []; self.settings.setValue("history", "[]"); self.render_history()

    def open_history(self, item):
        r = item.data(Qt.ItemDataRole.UserRole)
        if r["outputs"]: self.reveal(r["outputs"][0])
        elif r["detail"]: QMessageBox.information(self, "Détail du traitement", r["detail"])

    def reveal(self, path):
        p = Path(path)
        if not p.exists(): QMessageBox.information(self, "Résultat", "Ce résultat a été déplacé ou supprimé."); return
        if os.name == "nt": subprocess.Popen(["explorer.exe", "/select,", str(p)], creationflags=CREATE_NO_WINDOW)
        else: QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent)))

    def open_result(self):
        if self.last_outputs: self.reveal(self.last_outputs[0])

    def file_action(self, op, paths):
        try:
            if op == "copy_path": QApplication.clipboard().setText("\n".join(paths)); self.status_text.setText("Chemin(s) copié(s)")
            elif op == "reveal": self.reveal(paths[0])
            elif op == "copy_files":
                mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
                QApplication.clipboard().setMimeData(mime)
                self.status_text.setText("Fichiers copiés dans le presse-papiers")
            elif op == "float":
                w = FloatWindow(paths)
                self.floats.append(w)
                w.show()
            elif op == "terminal":
                folder = Path(paths[0]) if Path(paths[0]).is_dir() else Path(paths[0]).parent
                # No command interpolation; cwd selects the directory safely.
                subprocess.Popen(["powershell.exe", "-NoLogo", "-NoProfile", "-NoExit"], cwd=folder, creationflags=0x00000010)
            elif op == "share":
                from .windows_share import share
                share(int(self.winId()), paths)
            else:
                target = QFileDialog.getExistingDirectory(self, "Destination")
                if not target: return
                if op == "move" and QMessageBox.question(self, "Déplacer les originaux", f"Déplacer {len(paths)} élément(s) vers :\n{target}\n\nIls quitteront leur dossier actuel.") != QMessageBox.StandardButton.Yes: return
                for p in paths:
                    src = Path(p)
                    folder = Path(target).resolve()
                    if src.is_dir() and folder.is_relative_to(src.resolve()): raise ConversionError("La destination se trouve à l’intérieur du dossier source.")
                    dst = unique_path(folder, src.name)
                    if op == "move": shutil.move(str(src), str(dst))
                    elif src.is_dir(): shutil.copytree(src, dst)
                    else:
                        with src.open("rb") as f, dst.open("xb") as out: shutil.copyfileobj(f, out)
                self.status_text.setText("Déplacement terminé" if op == "move" else "Copie terminée")
                if op == "move": self.clear_files()
        except Exception as e: QMessageBox.warning(self, "Action impossible", str(e))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier des résultats")
        if path: self.settings.setValue("output", path); self.output_label.setText("Sorties : " + path)

    def reset_output(self): self.settings.setValue("output", ""); self.output_label.setText("Sorties : à côté des originaux")

    def choose_office(self):
        path, _ = QFileDialog.getOpenFileName(self, "Moteur LibreOffice", "", "LibreOffice (soffice.exe)")
        if path:
            os.environ["ZESTE_LIBREOFFICE"] = path
            self.settings.setValue("office", path)
            self.office_label.setText("LibreOffice : " + path)
            self.selection_changed()

    def show_popup(self):
        from PySide6.QtGui import QCursor
        self.popup.drag_session = None
        self.popup.set_mode("quick")
        self.popup.set_files(self.selected_paths())
        point = QCursor.pos()
        area = (QApplication.screenAt(point) or QApplication.primaryScreen()).availableGeometry()
        x=max(area.left(),min(point.x()-self.popup.width()//2,area.right()-self.popup.width()+1))
        y=max(area.top(),min(point.y()-self.popup.height()//2,area.bottom()-self.popup.height()+1))
        self.popup.move(x,y)
        self.popup.show()
        self.popup.activateWindow()

    def show_page(self, index):
        self.navigate(index)
        self.show_main()

    def show_main(self):
        from .window_visibility import ensure_native_visible
        self.showNormal()
        ensure_native_visible(self)
        self.raise_()
        self.activateWindow()

    def notify_background(self):
        self.tray.showMessage("Meloo est prêt", "Glisse un fichier depuis l’Explorateur ou le Bureau, appuie sur Ctrl puis dépose-le sur Compresser ou un format. Clic droit sur l’icône pour les réglages.", QSystemTrayIcon.MessageIcon.Information, 7000)

    def quit_app(self):
        if self.thread:
            self.cancel_job()
            self.notice.setText("Attends la fin de l’annulation avant de quitter.")
            self.show_main()
            return
        self.tray.hide()
        self.popup.close()
        self.result_panel.close()
        QApplication.quit()

    def closeEvent(self, event):
        if self.thread or self.settings.value("tray", True, bool): self.hide(); event.ignore()
        else: self.quit_app(); event.accept()
