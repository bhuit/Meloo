"""Small, entirely vector-drawn companion for the conversion result panel."""

from math import sin

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class Companion(QWidget):
    """A quiet orange companion; only visible processing work animates."""

    STATES = frozenset({"watching", "processing", "success", "failed", "cancelled"})
    _LABELS = {
        "watching": "Prêt",
        "processing": "Traitement en cours",
        "success": "Traitement terminé",
        "failed": "Échec du traitement",
        "cancelled": "Traitement annulé",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(66, 64)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.color_style = "orange"
        self._state = "watching"
        self._reduce_motion = False
        self._seconds = 0.0
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(round(1000 / 12))
        self._timer.timeout.connect(self._advance)
        self.setAccessibleName(self._LABELS[self._state])

    @property
    def state(self):
        return self._state

    @property
    def reduce_motion(self):
        return self._reduce_motion

    @reduce_motion.setter
    def reduce_motion(self, value):
        self._reduce_motion = bool(value)
        self._sync_animation()
        self.update()

    def set_state(self, state: str):
        if state not in self.STATES:
            raise ValueError(f"Unknown companion state: {state!r}")
        if self._state != state:
            self._state = state
            self._seconds = 0.0
            self._elapsed.invalidate()
            self.setAccessibleName(self._LABELS[state])
        self._sync_animation()
        self.update()

    def _sync_animation(self):
        active = self._state == "processing" and self.isVisible() and not self._reduce_motion
        if active:
            if not self._timer.isActive():
                self._elapsed.start()
                self._timer.start()
        else:
            self._timer.stop()
            self._seconds = 0.0
            self._elapsed.invalidate()

    def _advance(self):
        # The guard also covers visibility changes before a queued timeout fires.
        if self._state != "processing" or not self.isVisible() or self._reduce_motion:
            self._sync_animation()
            return
        if not self._elapsed.isValid():
            self._elapsed.start()
        self._seconds += self._elapsed.restart() / 1000.0
        self.update()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_animation()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._sync_animation()

    @staticmethod
    def _pen(color, width):
        return QPen(QColor(color), width, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        moving = self._state == "processing" and not self._reduce_motion
        phase = self._seconds * 5.0 if moving else 0.0
        bounce = sin(phase) * 2.0 if moving else 0.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 38))
        painter.drawEllipse(QRectF(10 + abs(bounce), 56, 46 - 2 * abs(bounce), 8))
        painter.save()
        painter.translate(33, 35 + bounce)
        painter.rotate(sin(phase * 0.8) * 4.0 if moving else 0.0)

        # Stem and a leaf are independent paths, so no image assets are needed.
        painter.setPen(self._pen("#59792f", 2.2))
        painter.drawLine(QPointF(1, -17), QPointF(6, -25))
        painter.save()
        painter.translate(9, -24)
        painter.rotate(-35)
        leaf = QPainterPath(QPointF(-8.5, 0))
        leaf.cubicTo(-3, -6, 6, -4, 8.5, 0)
        leaf.cubicTo(3, 5, -5, 5, -8.5, 0)
        leaf_gradient = QLinearGradient(0, -4, 0, 4)
        leaf_gradient.setColorAt(0, QColor("#9acb57"))
        leaf_gradient.setColorAt(1, QColor("#4e922d"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(leaf_gradient)
        painter.drawPath(leaf)
        painter.setPen(self._pen("#bddc73", 0.8))
        painter.drawLine(QPointF(-5, 0), QPointF(6, 0))
        painter.restore()

        melina = self.color_style == "melina"
        fruit_gradient = QLinearGradient(-12, -20, 13, 21)
        fruit_gradient.setColorAt(0, QColor("#ffd4c0" if melina else "#ffcd56"))
        fruit_gradient.setColorAt(0.48, QColor("#faaca2" if melina else "#ff9c25"))
        fruit_gradient.setColorAt(1, QColor("#e97d87" if melina else "#f16a15"))
        painter.setPen(self._pen("#6da67c" if melina else "#f8ab38", 3 if melina else .6))
        painter.setBrush(fruit_gradient)
        painter.drawEllipse(QRectF(-21, -21, 42, 42))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 245, 188, 65))
        painter.drawEllipse(QRectF(-15, -17, 12, 6))
        painter.setBrush(QColor(236, 101, 89, 110))
        painter.drawEllipse(QRectF(-17, 3, 8, 4))
        painter.drawEllipse(QRectF(9, 3, 8, 4))

        ink = "#51321f"
        blink = moving and self._seconds % 3.4 > 3.20
        gaze = sin(phase * 0.36) * 1.5 if moving else 0.0
        for x in (-7.0, 7.0):
            painter.setPen(self._pen(ink, 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self._state == "success":
                eye = QPainterPath(QPointF(x - 3, -3))
                eye.quadTo(x, -7, x + 3, -3)
                painter.drawPath(eye)
            elif blink or self._state == "cancelled":
                painter.drawLine(QPointF(x - 3, -3), QPointF(x + 3, -3))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(ink))
                painter.drawEllipse(QRectF(x - 4 + gaze, -9, 8, 11))
                painter.setBrush(QColor("#fff8d7"))
                painter.drawEllipse(QRectF(x - 2.5 + gaze, -7.7, 2.4, 3.1))
                if self._state == "failed":
                    painter.setPen(self._pen(ink, 1.5))
                    direction = 1 if x < 0 else -1
                    painter.drawLine(QPointF(x - 3, -12 + direction),
                                     QPointF(x + 3, -12 - direction))

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(self._pen(ink, 1.8))
        mouth = QPainterPath(QPointF(-4.5, 7))
        if self._state == "cancelled":
            mouth.lineTo(4.5, 7)
        elif self._state == "failed":
            mouth.quadTo(0, 2.5, 4.5, 7)
        else:
            mouth.quadTo(0, 15 if self._state == "success" else 12, 4.5, 7)
        painter.drawPath(mouth)
        painter.restore()

        if self._state in {"success", "failed", "cancelled"}:
            self._draw_badge(painter)
        painter.end()

    def _draw_badge(self, painter):
        colors = {"success": "#55b679", "failed": "#d85a54", "cancelled": "#85858d"}
        painter.setPen(self._pen("#202024", 1.4))
        painter.setBrush(QColor(colors[self._state]))
        painter.drawEllipse(QRectF(44, 43, 17, 17))
        painter.setPen(self._pen("#ffffff", 1.8))
        if self._state == "success":
            check = QPainterPath(QPointF(48, 51.5))
            check.lineTo(51, 54)
            check.lineTo(57, 48.5)
            painter.drawPath(check)
        elif self._state == "failed":
            painter.drawLine(QPointF(52.5, 47), QPointF(52.5, 52))
            painter.drawPoint(QPointF(52.5, 55))
        else:
            painter.drawLine(QPointF(49.5, 48), QPointF(49.5, 55))
            painter.drawLine(QPointF(55.5, 48), QPointF(55.5, 55))
