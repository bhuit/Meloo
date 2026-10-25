"""Windows radial interaction.

Rounded wedge geometry adapted from Open Tangerine RadialView.swift,
commit a1ff18575c5000cc50373e851e2bbe7a2b919245, GPL-3.0-only.
Qt event handling, animation and drawing are implemented for this port.
"""
from __future__ import annotations
import math
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont, QTransform, QRadialGradient
from PySide6.QtWidgets import QWidget, QApplication
from .catalog import operations, Operation, destination_order, format_label, family
from .engine import office_path

ACCENT = "#ff5c00"
GLASS_ACCENT = "#a4e7e3"
# Slate glass from the user-provided processing-hub reference.
GLASS_STOPS = ((0., (148,168,181,205)), (.68, (123,142,156,175)), (1., (164,183,197,210)))


def wedge_path(count, index):
    """Rounded annular sector in a 340px local coordinate system."""
    r0, r1, gap = 64., 150., 4.
    step = math.tau / max(count, 1)
    end = math.pi / 2 - step * index + step / 2
    start = end - step
    sn = math.sin(step * .34)
    corner = max(4, min(10 if count > 8 else 14, (r0 * sn - gap/2) / (1-sn)))
    po = math.asin((corner + gap/2) / (r1 - corner))
    pi = math.asin((corner + gap/2) / (r0 + corner))
    def pt(r, a): return QPointF(170 + math.cos(a)*r, 170 - math.sin(a)*r)
    def offset(p, a, inward):
        normal = QPointF(math.sin(a), math.cos(a)) if inward else QPointF(-math.sin(a), -math.cos(a))
        return p - normal*corner
    def arc(path, c, r, a, b, clockwise=True):
        sa = math.degrees(math.atan2(c.y()-a.y(), a.x()-c.x()))
        ea = math.degrees(math.atan2(c.y()-b.y(), b.x()-c.x()))
        sweep = (ea-sa) % 360
        if clockwise: sweep = -((sa-ea) % 360)
        path.arcTo(QRectF(c.x()-r, c.y()-r, r*2, r*2), sa, sweep)
    oe, ie = pt(r1-corner, end-po), pt(r0+corner, end-pi)
    ins, outs = pt(r0+corner, start+pi), pt(r1-corner, start+po)
    oet, iet = offset(oe, end, True), offset(ie, end, True)
    ist, ost = offset(ins, start, False), offset(outs, start, False)
    path = QPainterPath(pt(r1, start+po))
    # Outer arc proceeds counterclockwise in Cartesian coordinates.
    path.arcTo(QRectF(20, 20, 300, 300), math.degrees(start+po), math.degrees(end-start-2*po))
    arc(path, oe, corner, pt(r1, end-po), oet, False)
    path.lineTo(iet)
    arc(path, ie, corner, iet, pt(r0, end-pi), False)
    path.arcTo(QRectF(106, 106, 128, 128), math.degrees(end-pi), -math.degrees(end-start-2*pi))
    arc(path, ins, corner, pt(r0, start+pi), ist, False)
    path.lineTo(ost)
    arc(path, outs, corner, ost, pt(r1, start+po), False)
    path.closeSubpath()
    return path


def draw_symbol(p, x, y, op):
    """Small vector symbols avoid font-dependent emoji rendering."""
    p.save()
    p.translate(x, y)
    p.setBrush(Qt.BrushStyle.NoBrush)
    pen = p.pen(); pen.setWidthF(1.6); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin); p.setPen(pen)
    key = op.id
    if key.startswith("to:") or not key:
        p.drawRoundedRect(QRectF(-7, -10, 14, 19), 2, 2)
        p.drawLine(QPointF(-3, -3), QPointF(3, -3)); p.drawLine(QPointF(-3, 2), QPointF(3, 2))
    elif key == "compress":
        for sign in [-1, 1]:
            p.drawLine(QPointF(sign*9,sign*9),QPointF(sign*3,sign*3))
            p.drawLine(QPointF(sign*3,sign*3),QPointF(sign*3,sign*8))
            p.drawLine(QPointF(sign*3,sign*3),QPointF(sign*8,sign*3))
    elif key in {"extract", "copy", "move", "next", "copy_path", "reveal", "share"}:
        p.drawLine(QPointF(-7, 2), QPointF(7, 2)); p.drawLine(QPointF(2, -3), QPointF(7, 2)); p.drawLine(QPointF(2, 7), QPointF(7, 2))
        p.drawLine(QPointF(-7, -7), QPointF(-7, -2))
    elif key in {"metadata", "edit_metadata", "checksum", "strip_metadata"}:
        p.drawEllipse(QRectF(-9, -9, 18, 18)); p.drawLine(QPointF(0,-1), QPointF(0,5)); p.drawPoint(QPointF(0,-5))
    elif key in {"trim", "split_media", "split_pdf"}:
        p.drawEllipse(QRectF(-9,2,6,6)); p.drawEllipse(QRectF(3,2,6,6)); p.drawLine(QPointF(-6,2),QPointF(7,-9)); p.drawLine(QPointF(6,2),QPointF(-7,-9))
    elif key in {"join_media", "merge_pdf", "collage", "duplicate", "images_pdf"}:
        p.drawRoundedRect(QRectF(-9,-9,13,13),2,2); p.drawRoundedRect(QRectF(-3,-3,13,13),2,2)
    elif key in {"normalize", "visualizer", "bleep", "channels", "speed", "mute"}:
        for i,h in enumerate([4,8,11,7,3]): p.drawLine(QPointF(-8+i*4,-h/2),QPointF(-8+i*4,h/2))
    elif key in {"edit_image", "crop_video", "resize", "frame_image", "redact_video", "redact_pdf"}:
        p.drawLine(QPointF(-5,-10),QPointF(-5,5)); p.drawLine(QPointF(-5,5),QPointF(10,5)); p.drawLine(QPointF(-10,-5),QPointF(5,-5)); p.drawLine(QPointF(5,-5),QPointF(5,10))
    elif key in {"rotate", "rotate_pdf"}:
        p.drawArc(QRectF(-9,-9,18,18),45*16,280*16); p.drawLine(QPointF(6,-7),QPointF(2,-8)); p.drawLine(QPointF(6,-7),QPointF(5,-3))
    else:
        p.drawRoundedRect(QRectF(-9,-8,18,16),3,3); p.drawLine(QPointF(-4,0),QPointF(4,0))
    p.restore()


class Wheel(QWidget):
    activated = Signal(str, list)
    filesChanged = Signal(list)
    def __init__(self, popup=False, enabled=None):
        super().__init__()
        self.popup, self.paths, self.items = popup, [], []
        self.feature_enabled = enabled
        self.page_hover_latched = False
        self.center_entered = False
        self.mode, self.page, self.hovered = "quick" if popup else "convert", 0, -1
        self.drag_session = None
        self.progress_value = None
        self.busy = False
        self.move_origin = None
        self.move_window_origin = None
        self.moving = False
        self.glass_strength = 1.
        self.paths_hit = []
        self.reduce_motion = False
        self.light = False
        self.color_style = "orange"
        self.scale_value = 1.
        self.setMinimumSize(300, 300)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Roue de conversion : flèches pour choisir, Entrée pour lancer, Tab pour changer de menu")
        self.page_timer = QTimer(self)
        self.page_timer.setSingleShot(True)
        self.page_timer.timeout.connect(self.hover_next_page)
        self.mode_timer = QTimer(self); self.mode_timer.setSingleShot(True)
        self.mode_timer.timeout.connect(self.cycle_mode)
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(280)
        self.animation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.animation.valueChanged.connect(self.animate)
        if popup:
            self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.resize(320, 320)
            self.setStyleSheet("background:transparent;")

    def animate(self, value): self.scale_value = float(value); self.update()

    def showEvent(self, event):
        super().showEvent(event)
        if self.popup:
            from .window_visibility import ensure_native_visible
            QTimer.singleShot(0, self, lambda: ensure_native_visible(self))
        if self.popup and not self.reduce_motion:
            self.animation.setStartValue(.84); self.animation.setEndValue(1.); self.animation.start()

    def set_files(self, paths): self.paths = list(paths); self.page = 0; self.refresh()
    def set_mode(self, mode): self.mode = mode; self.page = 0; self.refresh()
    def cycle_mode(self):
        modes = ["quick" if self.popup else "convert", "tools", "actions"]
        self.set_mode(modes[(modes.index(self.mode)+1)%3] if self.mode in modes else modes[0])
    def refresh(self):
        self.page_timer.stop(); self.page_hover_latched=False
        self.items = operations(self.paths, self.mode, bool(office_path()), self.feature_enabled)
        self.page = 0
        self.hovered = -1
        self.update()

    def page_count(self):
        count = len(destination_order(self.paths)) if self.mode in {"quick", "convert"} else len(self.items)
        return max(1, math.ceil(count/(5 if self.mode in {"quick", "convert"} else 7)))

    def visible_items(self):
        self.page %= self.page_count()
        if self.mode in {"quick", "convert"}:
            available = {op.id:op for op in self.items}
            tools = {op.id:op for op in operations(self.paths, "tools", bool(office_path()), self.feature_enabled)}
            if not self.paths or len({family(p) for p in self.paths}) != 1 or family(self.paths[0]) not in {"image", "pdf", "video", "audio"}: tools.pop("compress", None)
            slots = [available.get("create_zip", Operation("", "Créer ZIP" if not self.paths else "")),
                     tools.get("compress", Operation("", "Compresser" if not self.paths else ""))]
            for ext in destination_order(self.paths)[self.page*5:(self.page+1)*5]:
                allowed = self.feature_enabled is None or self.feature_enabled("convert/"+ext)
                same = all(Path(p).suffix.lower().lstrip(".")==ext for p in self.paths)
                slots.append(available.get("to:"+ext, Operation("", (ext.upper()+"\nActuel" if same else format_label(ext)) if allowed else "", detail="Format d’origine" if same else "Format indisponible pour cette sélection")))
        else:
            slots = self.items[self.page*7:(self.page+1)*7]
        slots += [Operation("", "") for _ in range(7-len(slots))]
        if self.page_count()>1:
            next_number=(self.page+1)%self.page_count()+1
            slots.append(Operation("next", (("Autres\nformats" if self.page==0 else "Premiers\nformats") if self.mode in {"quick","convert"} else f"Suite {next_number}/{self.page_count()} →"), detail="Survoler un instant pour changer de page, puis viser le format. Tab : outils / actions."))
        else: slots.append(Operation("", ""))
        return slots

    def set_progress(self, value=None, busy=False):
        self.progress_value=value;self.busy=busy;self.update()

    def paintEvent(self, event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        zoom=min(self.width(),self.height())/340*self.scale_value
        transform=QTransform().translate(self.width()/2,self.height()/2).scale(zoom,zoom).translate(-170,-170)
        p.setTransform(transform);self.paths_hit=[];items=self.visible_items()
        melina=self.color_style=="melina"
        opacity=self.glass_strength if self.popup else 1.
        def color(r,g,b,a):return QColor(r,g,b,round(min(255,a*opacity)))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for radius,alpha in [(158,7),(155,12),(153,20)]:
            p.setPen(QPen(QColor(174,206,224,alpha),3));p.drawEllipse(QPointF(170,170),radius,radius)
        p.setPen(QPen(color(65,133,90,210) if melina else color(198,219,232,74),3 if melina else 1));p.setBrush(color(126,186,135,220) if melina else color(19,31,43,190))
        p.drawEllipse(QPointF(170,170),152,152)
        if not items:
            p.setPen(QColor("#d0dce6"));p.setFont(QFont("Segoe UI",10))
            p.drawText(QRectF(45,82,250,45),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,"Aucun outil actif pour cette sélection")
        for i,op in enumerate(items):
            path=wedge_path(len(items),i);self.paths_hit.append(transform.map(path))
            active=i==self.hovered and bool(op.id);angle=math.pi/2-math.tau*i/len(items)
            p.save()
            if self.paths and not op.id: p.setOpacity(.40 if op.label else .18)
            if active and not self.reduce_motion:
                p.translate(math.cos(angle)*3,-math.sin(angle)*3)
            gradient=QRadialGradient(QPointF(170,170),160)
            for stop,rgba in GLASS_STOPS:
                r,g,b,a=rgba
                # Violet towards the top, cool teal towards the output side.
                r+=int(max(0,math.sin(angle))*12)
                g+=int(max(0,math.cos(angle))*17)
                gradient.setColorAt(stop,color(r,g,b,a))
            if melina:
                gradient=QRadialGradient(QPointF(170,170),160)
                for stop,rgba in [(0,(249,158,149,220)),(.60,(247,150,146,222)),(.82,(252,180,164,230)),(.94,(236,240,205,245)),(1,(159,207,161,240))]:
                    gradient.setColorAt(stop,color(*rgba))
            p.setBrush((QColor("#ffdbbc") if melina else QColor(GLASS_ACCENT)) if active else gradient)
            p.setPen(QPen(color(255,249,221,220 if active else 160) if melina else color(219,239,245,190 if active else 100),1 if active else .8));p.drawPath(path)
            if melina and (op.id.startswith("to:") or op.detail=="Format d’origine"):
                # Seeds stay near the inner edge, clear of labels and hit targets.
                for offset in [-.105,.105]:
                    a=angle+offset
                    p.save();p.translate(170+math.cos(a)*78,170-math.sin(a)*78);p.rotate(90-math.degrees(a))
                    p.setPen(QPen(color(100,59,43,185),.5));p.setBrush(color(102,61,43,210))
                    p.drawEllipse(QRectF(-1.7,-3.2,3.4,6.4));p.restore()
            x,y=170+math.cos(angle)*109,170-math.sin(angle)*109
            p.setPen(QColor("#57352c" if melina else "#11282d" if active else "#14232e"))
            if op.label: draw_symbol(p,x,y-10,op)
            font=QFont("Segoe UI");font.setPixelSize(12 if op.id.startswith("to:") else 11);font.setWeight(QFont.Weight.DemiBold);p.setFont(font)
            title=op.label.replace(" (", "\n").replace(")", "").replace("Partager sous Windows","Partager").replace("Redimensionner","Dimensions").replace("Garder à portée","À portée").replace("Copier le chemin","Chemin").replace("Extraire une image","Image").replace("Nettoyer les infos","Nettoyer").replace("Ouvrir un terminal","Terminal")
            p.drawText(QRectF(x-45,y+5,90,31),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,title)
            p.restore()
        # The luminous centre ring doubles as the draggable handle.
        center=QRadialGradient(QPointF(158,145),95)
        center.setColorAt(0,color(255,217,199,245));center.setColorAt(1,color(237,151,143,235))
        p.setBrush(center if melina else color(14,28,39,246));p.setPen(QPen(color(255,239,212,200) if melina else color(152,197,204,105),1))
        p.drawEllipse(QPointF(170,170),52,52)
        ring=QRectF(113,113,114,114)
        p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(color(255,240,215,130) if melina else color(150,188,201,65),4));p.drawEllipse(ring)
        p.setPen(QPen(color(73,133,94,230) if melina else color(164,237,231,240),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
        sweep=round(360*min(100,max(0,self.progress_value))/100) if self.progress_value is not None else 255
        p.drawArc(ring,90*16,-sweep*16)
        title={"quick":"CONVERTIR","convert":"CONVERTIR","tools":"OUTILS","actions":"ACTIONS"}[self.mode]
        subtitle=f"Page {self.page+1}/{self.page_count()}" if self.paths else "Dépose un fichier"
        if 0 <= self.hovered < len(items):
            op=items[self.hovered]
            if not op.id and op.detail=="Format d’origine": title="FORMAT ACTUEL"; subtitle=op.label.split("\n")[0]
            if op.id.startswith("to:"): title="VERS "+op.id[3:].upper()
            elif op.id=="create_zip": title="CRÉER ZIP"
            elif op.id=="compress": title="COMPRESSER"
            elif op.id=="next": title="AUTRES FORMATS" if self.mode in {"quick","convert"} else "PAGE SUIVANTE"
        if self.busy:
            title="EN COURS";subtitle=f"{self.progress_value}%" if self.progress_value is not None else "Traitement local"
        elif self.progress_value==100: title="TERMINÉ";subtitle="Copies enregistrées"
        font=QFont("Segoe UI");font.setPixelSize(10);font.setWeight(QFont.Weight.Medium);p.setFont(font);p.setPen(QColor("#57352c" if melina else "#edf7fa"))
        p.drawText(QRectF(122,152,96,22),Qt.AlignmentFlag.AlignCenter,title)
        font.setPixelSize(8);font.setWeight(QFont.Weight.Normal);p.setFont(font);p.setPen(QColor("#765246" if melina else "#aec8d2"))
        p.drawText(QRectF(120,176,100,17),Qt.AlignmentFlag.AlignCenter,subtitle)
        if not self.busy:
            p.drawText(QRectF(120,193,100,12),Qt.AlignmentFlag.AlignCenter,"Tab : outils / actions" if self.popup else "Format de destination")
        p.end()

    def hit(self, point): return next((i for i,path in enumerate(self.paths_hit) if path.contains(QPointF(point))),-1)

    def hover(self, point, drag=False):
        # Crossing the centre must never change the destination menu.
        index = self.hit(point)
        items=self.visible_items()
        is_next=0 <= index < len(items) and items[index].id=="next"
        if not is_next: self.page_hover_latched=False
        if index != self.hovered:
            self.page_timer.stop()
            self.hovered = index
            items=self.visible_items()
            if drag and is_next and not self.page_hover_latched: self.page_timer.start(900)
            self.setToolTip(items[index].detail or items[index].label if 0 <= index < len(items) else "")
            self.update()

    def hover_next_page(self):
        self.page_hover_latched=True
        self.next_page()

    def next_page(self):
        self.page_timer.stop(); self.page=(self.page+1)%self.page_count(); self.hovered=-1; self.update()
    def in_center(self, point):
        return math.hypot(point.x()-self.width()/2, point.y()-self.height()/2) < min(self.width(),self.height())/340*45

    def hideEvent(self,event):
        self.page_timer.stop(); self.mode_timer.stop(); self.center_entered=False
        self.move_origin = None; self.move_window_origin = None; self.moving = False
        self.unsetCursor()
        super().hideEvent(event)
    def mousePressEvent(self, event):
        if self.popup and event.button() == Qt.MouseButton.LeftButton and self.in_center(event.position()):
            self.move_origin = event.globalPosition().toPoint()
            self.move_window_origin = self.pos()
            self.moving = False
            self.drag_session = None
            self.page_timer.stop(); self.mode_timer.stop()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.move_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.move_origin
            if self.moving or delta.manhattanLength() >= QApplication.startDragDistance():
                self.moving = True
                position = self.move_window_origin + delta
                screen = QApplication.screenAt(event.globalPosition().toPoint()) or self.screen()
                area = screen.availableGeometry()
                position.setX(max(area.left(), min(position.x(), area.right() - self.width() + 1)))
                position.setY(max(area.top(), min(position.y(), area.bottom() - self.height() + 1)))
                self.move(position)
            event.accept()
            return
        self.setCursor(Qt.CursorShape.OpenHandCursor if self.popup and self.in_center(event.position()) else Qt.CursorShape.ArrowCursor)
        self.hover(event.position())
        if self.popup and self.in_center(event.position()):
            self.setToolTip("Glisser le centre pour déplacer la roue · Cliquer pour changer de menu")
    def leaveEvent(self,event): self.hovered=-1; self.page_timer.stop(); self.mode_timer.stop(); self.center_entered=False; self.update()

    def activate_at(self,point):
        index=self.hit(point); items=self.visible_items()
        if index<0 or index>=len(items): return False
        op=items[index]
        if op.id=="next": self.next_page(); return False
        if op.id and self.paths:
            self.activated.emit(op.id,list(self.paths))
            if self.popup: self.hide()
            return True
        return False

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            if self.move_origin is not None:
                moved = self.moving
                self.move_origin = None; self.move_window_origin = None; self.moving = False
                self.unsetCursor()
                if not moved and self.in_center(event.position()): self.cycle_mode()
                event.accept()
                return
            if self.in_center(event.position()): self.cycle_mode()
            else: self.activate_at(event.position())

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():
            paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if not paths: event.ignore(); return
            self.set_files(paths); self.filesChanged.emit(paths)
            event.setDropAction(Qt.DropAction.CopyAction);event.accept()

    def dragMoveEvent(self,event): self.hover(event.position(),True);event.setDropAction(Qt.DropAction.CopyAction);event.accept()
    def dragLeaveEvent(self,event): self.page_timer.stop(); self.mode_timer.stop(); self.center_entered=False; self.page_hover_latched=False; self.hovered=-1;self.update();event.accept()
    def dropEvent(self,event):
        self.page_timer.stop()
        self.mode_timer.stop()
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if not paths or paths != self.paths:
            event.ignore()
            if self.popup: self.hide()
            return
        if self.activate_at(event.position()): event.setDropAction(Qt.DropAction.CopyAction);event.accept()
        else:
            event.ignore()
            if self.popup: self.hide()
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Escape and self.popup: self.hide()
        elif event.key() in {Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down}:
            delta = 1 if event.key() in {Qt.Key.Key_Right,Qt.Key.Key_Down} else -1
            items=self.visible_items()
            for _ in items:
                self.hovered=(self.hovered+delta)%len(items)
                if items[self.hovered].id: break
            self.update()
        elif event.key() in {Qt.Key.Key_Return,Qt.Key.Key_Enter}:
            items=self.visible_items()
            if 0 <= self.hovered < len(items):
                op=items[self.hovered]
                if op.id=="next": self.next_page()
                elif op.id and self.paths:
                    self.activated.emit(op.id,list(self.paths))
                    if self.popup: self.hide()
        elif event.key()==Qt.Key.Key_Tab:
            self.cycle_mode()
        else: super().keyPressEvent(event)
