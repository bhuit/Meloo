"""Local progress/result shelf inspired by the macOS floating notch panel."""
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl, QMimeData, QPoint, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QDrag, QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QApplication
from .companion import Companion
from .themes import current_style


class ResultRow(QLabel):
    revealRequested = Signal(str)
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.origin = QPoint()
        self.setText("↗  " + Path(path).name)
        self.setToolTip("Glisser vers un dossier · double-clic pour retrouver le fichier\n" + path)
        self.setMinimumHeight(37)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.set_theme(current_style())

    def set_theme(self, style):
        bg,ink = ("#f8ecda", "#51382f") if style == "melina" else ("#29292d", "#f4f4f7")
        self.setStyleSheet(f"QLabel {{ background:{bg}; color:{ink}; padding:6px 12px; border-radius:9px; font-size:12px; }}")
    def mousePressEvent(self,event): self.origin=event.position().toPoint()
    def mouseDoubleClickEvent(self,event): self.revealRequested.emit(self.path)
    def mouseMoveEvent(self,event):
        if event.buttons() & Qt.MouseButton.LeftButton and (event.position().toPoint()-self.origin).manhattanLength() > QApplication.startDragDistance():
            mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(self.path)])
            drag=QDrag(self);drag.setMimeData(mime);drag.exec(Qt.DropAction.CopyAction)


class ResultPanel(QWidget):
    revealRequested = Signal(str)
    openRequested = Signal()
    cancelRequested = Signal()
    def __init__(self):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(360)
        self.setMinimumHeight(104)
        self.reduce_motion=False
        self.auto_hide=QTimer(self);self.auto_hide.setSingleShot(True);self.auto_hide.timeout.connect(self.hide)
        self.animation=QVariantAnimation(self);self.animation.setDuration(240);self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(lambda v:self.setWindowOpacity(float(v)))
        layout=QVBoxLayout(self);layout.setContentsMargins(16,12,16,14);layout.setSpacing(7)
        header=QHBoxLayout()
        self.mark=Companion()
        header.addWidget(self.mark)
        self.color_style="orange"
        self.title=QLabel("Meloo");self.title.setStyleSheet("font-size:13px;font-weight:600;color:white;background:transparent;")
        header.addWidget(self.title,1)
        self.close_button=QPushButton("×");self.close_button.setFixedSize(24,24)
        self.close_button.setStyleSheet("QPushButton{background:transparent;border:0;color:#b1b1b9;font-size:19px;padding:0;} QPushButton:hover{color:white;}")
        self.close_button.clicked.connect(self.hide);header.addWidget(self.close_button);layout.addLayout(header)
        self.description=QLabel();self.description.setWordWrap(True);self.description.setTextFormat(Qt.TextFormat.PlainText)
        self.description.setStyleSheet("background:transparent;color:#c0c0c9;font-size:11px;")
        layout.addWidget(self.description)
        self.progress=QProgressBar();self.progress.setFixedHeight(3);self.progress.setTextVisible(False)
        self.progress.setStyleSheet("QProgressBar{background:#3e3e43;border:0;border-radius:1px;}QProgressBar::chunk{background:#ff5c00;}")
        layout.addWidget(self.progress)
        self.rows=QVBoxLayout();self.rows.setSpacing(5);layout.addLayout(self.rows)
        actions=QHBoxLayout()
        self.more=QPushButton("Ouvrir l’atelier");self.more.clicked.connect(self.openRequested)
        self.cancel=QPushButton("Annuler");self.cancel.clicked.connect(self.cancelRequested)
        for b in [self.more,self.cancel]: b.setStyleSheet("QPushButton{background:transparent;border:0;color:#ff9052;padding:3px;font-size:11px;} QPushButton:hover{color:white;}")
        actions.addWidget(self.more);actions.addStretch();actions.addWidget(self.cancel);layout.addLayout(actions)

    def set_theme(self, style):
        self.color_style=style; self.mark.color_style=style; self.mark.update()
        ink,muted,accent,bg = ("#51382f","#70574b","#337353","#c6d7bc") if style == "melina" else ("#ffffff","#c0c0c9","#ff9052","#3e3e43")
        self.title.setStyleSheet(f"font-size:13px;font-weight:600;color:{ink};background:transparent;")
        self.description.setStyleSheet(f"background:transparent;color:{muted};font-size:11px;")
        self.close_button.setStyleSheet(f"QPushButton{{background:transparent;border:0;color:{muted};font-size:19px;padding:0;}} QPushButton:hover{{color:{ink};}}")
        self.progress.setStyleSheet(f"QProgressBar{{background:{bg};border:0;border-radius:1px;}}QProgressBar::chunk{{background:{accent};}}")
        for b in [self.more,self.cancel]: b.setStyleSheet(f"QPushButton{{background:transparent;border:0;color:{accent};padding:3px;font-size:11px;}} QPushButton:hover{{color:{ink};}}")
        for row in self.findChildren(ResultRow): row.set_theme(style)
        self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(226,238,210,250) if self.color_style=="melina" else QColor(16,16,18,250));p.setPen(QPen(QColor(255,250,228,210) if self.color_style=="melina" else QColor(90,90,98,100),1))
        p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),24,24);p.end()

    def clear_rows(self):
        while self.rows.count(): self.rows.takeAt(0).widget().deleteLater()

    def display(self):
        self.mark.reduce_motion = self.reduce_motion
        self.adjustSize()
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area=screen.availableGeometry()
        self.move(area.center().x()-self.width()//2,area.top()+8)
        from .window_visibility import ensure_native_visible
        self.show();ensure_native_visible(self);self.raise_()
        self.animation.stop()
        if not self.reduce_motion:
            self.animation.setStartValue(.15);self.animation.setEndValue(1.);self.animation.start()
        else: self.setWindowOpacity(1.)

    def working(self, filename):
        self.mark.set_state("processing")
        self.auto_hide.stop();self.clear_rows()
        self.title.setText("Traitement en cours")
        self.description.setText(filename)
        self.progress.setRange(0,0);self.progress.show();self.cancel.show();self.display()

    def update_progress(self,text): self.description.setText(text)

    def finished(self,paths,warnings):
        self.mark.set_state("success" if not warnings else "failed")
        self.auto_hide.stop();self.clear_rows();self.progress.hide();self.cancel.hide()
        self.title.setText(f"{len(paths)} résultat(s) prêt(s)" if paths else "Aucun résultat")
        self.description.setText(warnings[0][:180] if warnings else "Glisse les résultats vers leur destination.")
        for path in paths[:3]:
            row=ResultRow(path);row.revealRequested.connect(self.revealRequested);self.rows.addWidget(row)
        self.display()
        if not warnings: self.auto_hide.start(8000)

    def failed(self,error):
        self.mark.set_state("cancelled" if "annul" in error.lower() else "failed")
        self.auto_hide.stop();self.clear_rows();self.progress.hide();self.cancel.hide()
        self.title.setText("Le traitement a échoué")
        self.description.setText(error[-250:]);self.display()

    def enterEvent(self,event): self.auto_hide.stop();super().enterEvent(event)
