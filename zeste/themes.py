"""Meloo's reversible palettes and locally drawn fruit identity."""
import math
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QIcon, QLinearGradient
from PySide6.QtWidgets import QCheckBox, QApplication


def current_style():
    app = QApplication.instance()
    return app.property("color_style") or "orange" if app else "orange"


class StyleSwitch(QCheckBox):
    """Native check-box semantics, with a visible two-state switch."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName("Style Melina pastèque")
        self.setToolTip("Orange / Melina · cliquer ou appuyer sur Espace")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#267250" if self.isChecked() else "#af531e"), 1))
        p.setBrush(QColor("#70ba91" if self.isChecked() else "#ed8b45"))
        p.drawRoundedRect(QRectF(3, 3, 64, 30), 15, 15)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#fff9ef"))
        p.drawEllipse(QRectF(39 if self.isChecked() else 7, 7, 22, 22))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#346e51" if self.isChecked() else "#f0a16b"), 1, Qt.PenStyle.DashLine))
            p.drawRoundedRect(QRectF(1, 1, 68, 34), 17, 17)
        p.end()


def fruit_icon(size=64, style="orange"):
    pix = QPixmap(size, size); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size/64, size/64)
    if style == "melina":
        p.setPen(QPen(QColor("#398660"), 1.4)); p.setBrush(QColor("#77bc8e"))
        p.drawEllipse(QRectF(3, 3, 58, 58))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#e3f1c9")); p.drawEllipse(QRectF(7, 7, 50, 50))
        g=QLinearGradient(12,10,50,57);g.setColorAt(0,QColor("#ffd1c1"));g.setColorAt(1,QColor("#ed777d"))
        p.setBrush(g);p.drawEllipse(QRectF(10,10,44,44))
        for i in range(8):
            a=math.tau*i/8
            p.save();p.translate(32+math.cos(a)*16,32+math.sin(a)*16);p.rotate(math.degrees(a)-90)
            p.setBrush(QColor("#683e32"));p.drawEllipse(QRectF(-1.6,-3,3.2,5.6));p.restore()
    else:
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor("#ff5c00"));p.drawEllipse(QRectF(3,6,56,56))
        p.setBrush(QColor("#e3ed9c"));p.drawEllipse(QRectF(36.48,0,19.2,10.24))
        p.setPen(QPen(QColor("#733915"),64/28,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        c=QPointF(30.72,33.92)
        for a in range(0,360,60):
            a=math.radians(a);v=QPointF(math.cos(a),math.sin(a));p.drawLine(c+v*6.4,c+v*18.56)
    p.end();return QIcon(pix)


def melina_stylesheet(original):
    # Map from the original dark palette, never from a previously mapped style.
    colors = {
        "#e7edf4":"#4a302d", "#0b111b":"#eceddf", "#b5c6d4":"#645347",
        "#9eafc0":"#64524b", "#9be9de":"#285c43", "#305a60":"#89b79a",
        "rgba(33,43,56,165)":"rgba(255,253,240,130)",
        "rgba(186,210,227,38)":"rgba(255,255,237,175)",
        "rgba(9,15,25,125)":"rgba(255,252,239,125)",
        "rgba(186,210,227,26)":"rgba(255,255,240,170)",
        "#445363":"#a0b9a0", "rgba(109,126,145,30)":"rgba(255,255,246,100)",
        "rgba(122,169,179,60)":"rgba(255,253,238,180)", "#809ca9":"#608f72",
        "#375b62":"#b9d9be", "#72818f":"#8a857c", "#36434f":"#b7c2ae",
        "#102d32":"#fffdf2", "#9de3df":"#397959", "#b7ede8":"#2d6749", "#c2f4ed":"#2b6548",
        "#a6b7c7":"#655047", "rgba(133,190,190,35)":"rgba(255,248,228,160)",
        "#cff3ed":"#603a32", "#a7b7c7":"#655047", "rgba(162,189,213,25)":"rgba(255,248,228,155)",
        "#e8f5fa":"#51302b", "rgba(9,17,28,80)":"rgba(255,251,235,55)",
        "rgba(188,211,228,28)":"rgba(255,255,240,160)",
        "rgba(113,195,190,45)":"rgba(255,237,215,180)","#f0fffd":"#4a302d","#739f9f":"#6b9a7c",
        "rgba(145,173,192,22)":"rgba(255,249,232,95)",
        "#172431":"#f4f2e4", "#425464":"#96af97", "#355b62":"#b6d5bb",
        "#2b414c":"#c4d6bd", "#95e3de":"#458563", "#536775":"#7da68b",
        "#15212d":"#f0f0df", "#546878":"#94b39b", "#355a61":"#c6dec5",
        "#ecf7fc":"#4a302d", "#263b49":"#fff4dd", "#688996":"#a5ba9c",
    }
    for old,new in colors.items(): original=original.replace(old,new)
    return original + "\nQCheckBox::indicator:checked { background:#488564; border:2px solid #e5eed8; border-radius:5px; }\nQCheckBox::indicator:unchecked { background:#fff6e8; border:1px solid #89a98d; border-radius:5px; }"
