"""Local glass-and-light visual theme; no remote assets or services."""
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QSize, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient, QPixmap, QIcon, QImageReader, QFont, QLinearGradient
from PySide6.QtWidgets import QWidget
from .themes import current_style


class GlassStage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.light = False
        self.color_style = "orange"

    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor("#e7edf2" if self.light else "#0b111b"))
        w,h=self.width(),self.height()
        if self.color_style == "melina":
            base=QLinearGradient(0,0,w,h)
            for stop,c in [(0,"#f6aaa4"),(.28,"#edaaa0"),(.58,"#d5dfc8"),(1,"#8bcfac")]: base.setColorAt(stop,QColor(c))
            p.fillRect(self.rect(),base)
        for x,y,r,color,alpha in ([] if self.color_style == "melina" else [(.03,.60,.66,"#de692d",65),(.69,.12,.63,"#8462c2",84),(.98,.61,.66,"#28bdac",74)]):
            gradient=QRadialGradient(QPointF(w*x,h*y),min(w,h)*r)
            c=QColor(color);c.setAlpha(alpha if not self.light else alpha//2)
            gradient.setColorAt(0,c);c.setAlpha(0);gradient.setColorAt(1,c)
            p.fillRect(self.rect(),gradient)
        # Subtle strands connect the three columns without covering controls.
        p.setBrush(Qt.BrushStyle.NoBrush)
        for offset in [-.13,0,.13]:
            for left in [True,False]:
                start=QPointF(w*.23,h*(.47+offset)) if left else QPointF(w*.62,h*.47)
                end=QPointF(w*.38,h*.47) if left else QPointF(w*.77,h*(.47+offset))
                path=QPainterPath(start)
                path.cubicTo(QPointF(w*(.32 if left else .70),start.y()),QPointF(w*(.32 if left else .70),end.y()),end)
                p.setPen(QPen(QColor(219,177,150,28) if left else QColor(137,225,220,40),1.2));p.drawPath(path)
        p.end()


def file_icon(path):
    path=Path(path)
    pix=QPixmap(112,86);pix.fill(Qt.GlobalColor.transparent)
    p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    melina=current_style()=="melina"
    p.setBrush(QColor(255,255,241,100 if melina else 18));p.setPen(QPen(QColor(255,255,235,170) if melina else QColor(219,232,242,45),1))
    p.drawRoundedRect(QRectF(1,1,110,84),10,10)
    reader=QImageReader(str(path));reader.setAutoTransform(True)
    if reader.canRead():
        reader.setScaledSize(reader.size().scaled(QSize(96,72),Qt.AspectRatioMode.KeepAspectRatio))
        image=reader.read()
        if not image.isNull():
            p.drawImage(QPointF((112-image.width())/2,(86-image.height())/2),image)
            p.end();return QIcon(pix)
    shape=QPainterPath();shape.moveTo(36,14);shape.lineTo(66,14);shape.lineTo(79,27)
    shape.lineTo(79,71);shape.lineTo(33,71);shape.lineTo(33,17);shape.closeSubpath()
    p.setBrush(QColor("#f8f0dd" if melina else "#ccd6df"));p.setPen(QPen(QColor("#f4f8fc"),.7));p.drawPath(shape)
    p.setPen(QPen(QColor("#8397a5"),1));p.drawLine(66,14,66,27);p.drawLine(66,27,79,27)
    font=QFont("Segoe UI");font.setPixelSize(10);font.setBold(True);p.setFont(font)
    p.setPen(QColor("#573b32" if melina else "#253544"));p.drawText(QRectF(32,34,48,24),Qt.AlignmentFlag.AlignCenter,(path.suffix[1:] or "FICHIER").upper()[:7])
    p.end();return QIcon(pix)
