from pathlib import Path
import copy
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QFont
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QDialogButtonBox, QLabel, QInputDialog, QDoubleSpinBox, QSpinBox, QFormLayout, QScrollArea, QColorDialog, QCheckBox
from .engine import Engine
from .photo import ADJUSTMENTS, adjust_photo, annotate


class Canvas(QWidget):
    cropChanged = Signal()
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.preview = image
        self.annotations = []
        self.crop = None
        self.start = None
        self.current = None
        self.tool = "crop"
        self.color = "#ff7845"
        self.pen_width = 5
        self.font_size = 32
        self.ratio = 0
        self.points = []
        self.history = []
        self.show_original = False
        self.setMinimumSize(600, 420)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def image_rect(self):
        scale = min((self.width()-30)/self.image.width, (self.height()-30)/self.image.height)
        w, h = self.image.width*scale, self.image.height*scale
        return QRectF((self.width()-w)/2, (self.height()-h)/2, w, h)

    def image_point(self, p):
        rect = self.image_rect()
        x = max(0, min(self.image.width, (p.x()-rect.x())/rect.width()*self.image.width))
        y = max(0, min(self.image.height, (p.y()-rect.y())/rect.height()*self.image.height))
        return QPointF(x, y)

    def display_rect(self, box):
        rect = self.image_rect()
        sx, sy = rect.width()/self.image.width, rect.height()/self.image.height
        return QRectF(rect.x()+box[0]*sx, rect.y()+box[1]*sy, (box[2]-box[0])*sx, (box[3]-box[1])*sy)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#11130f"))
        rgba = self.preview.convert('RGBA') if self.show_original else annotate(self.preview, self.annotations, self.preview.width/self.image.width)
        q = QImage(rgba.tobytes(), rgba.width, rgba.height, rgba.width*4, QImage.Format.Format_RGBA8888).copy()
        p.drawImage(self.image_rect(), q)
        if self.crop and not self.show_original:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#c5e7a3"), 2, Qt.PenStyle.DashLine))
            p.drawRect(self.display_rect(self.crop))
        if self.start is not None and self.current is not None:
            box = [min(self.start.x(), self.current.x()), min(self.start.y(), self.current.y()), max(self.start.x(), self.current.x()), max(self.start.y(), self.current.y())]
            p.setPen(QPen(QColor("#ffbe82"), 2, Qt.PenStyle.DashLine))
            p.setBrush(QColor(255, 177, 90, 35))
            p.drawRect(self.display_rect(box))
        p.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.tool == "adjust": return
        self.history.append((copy.deepcopy(self.annotations), self.crop[:] if self.crop else None))
        self.start = self.image_point(event.position())
        self.current = self.start
        self.points = [[self.start.x(), self.start.y()]]
        if self.tool in {"text", "number"}:
            text, ok = (str(1+sum(a['type']=='number' for a in self.annotations)), True) if self.tool == "number" else QInputDialog.getText(self, "Annotation", "Texte à ajouter")
            if ok and text: self.annotations.append({"type": self.tool, "box": [self.start.x(), self.start.y(), self.start.x()+100, self.start.y()+30], "text": text, "color":self.color, "font_size":self.font_size})
            self.start = None
        self.update()

    def mouseMoveEvent(self, event):
        if self.start is not None:
            self.current = self.image_point(event.position())
            self.points.append([self.current.x(), self.current.y()]); self.update()

    def mouseReleaseEvent(self, event):
        if self.start is None: return
        end = self.image_point(event.position())
        box = [round(min(self.start.x(), end.x())), round(min(self.start.y(), end.y())), round(max(self.start.x(), end.x())), round(max(self.start.y(), end.y()))]
        if self.tool == "crop" and self.ratio:
            width = min(box[2]-box[0], (box[3]-box[1])*self.ratio)
            box[2],box[3] = box[0]+round(width),box[1]+round(width/self.ratio)
        area = box[2]-box[0] >= 2 and box[3]-box[1] >= 2
        line = self.tool in {'arrow','line','pen','highlight'} and max(box[2]-box[0],box[3]-box[1])>=2
        if area or line:
            if self.tool == "crop": self.crop = box; self.cropChanged.emit()
            else:
                points = self.points + [[end.x(),end.y()]] if self.tool in {"pen", "highlight"} else [[self.start.x(),self.start.y()],[end.x(),end.y()]]
                self.annotations.append({"type": self.tool, "box": box, "points":points, "color":self.color, "width":self.pen_width, "font_size":self.font_size})
        self.start = None
        self.current = None
        self.update()


class ImageEditor(QDialog):
    def __init__(self, path, parent=None, initial="edit_image", enabled=None):
        super().__init__(parent)
        self.setWindowTitle("Retoucher · " + Path(path).name)
        self.resize(1100, 760)
        self.image = Engine().open_image(Path(path))
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Aperçu local · l’original reste intact · Enregistrer une copie pour appliquer les changements"))
        top = QHBoxLayout()
        self.sections = QComboBox()
        for key,title in [("edit_image","Retoucher"),("annotate_image","Annoter"),("crop_image","Recadrer"),("redact_image","Masquer")]:
            if enabled is None or enabled("image/"+key): self.sections.addItem(title,key)
        top.addWidget(self.sections)
        self.tools = QComboBox(); top.addWidget(self.tools)
        self.tools.currentIndexChanged.connect(lambda: setattr(self.canvas,"tool",self.tools.currentData() or "adjust"))
        self.color_button = QPushButton("Couleur"); self.color_button.clicked.connect(self.choose_color); top.addWidget(self.color_button)
        undo = QPushButton("Annuler le dernier dessin")
        undo.clicked.connect(self.undo)
        top.addWidget(undo)
        reset = QPushButton("Réinitialiser")
        reset.clicked.connect(self.reset)
        top.addWidget(reset)
        root.addLayout(top)
        self.canvas = Canvas(self.image)
        self.preview_source = self.image.copy(); self.preview_source.thumbnail((1200,1200))
        self.canvas.preview = self.preview_source
        body = QHBoxLayout(); body.addWidget(self.canvas, 1); root.addLayout(body,1)
        self.controls = QWidget(); form = QFormLayout(self.controls)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFixedWidth(285); scroll.setWidget(self.controls); body.addWidget(scroll)
        self.adjust_widgets = []
        self.values = {}
        self.preview_timer = QTimer(self); self.preview_timer.setSingleShot(True); self.preview_timer.timeout.connect(self.adjust)
        for key, text, default, low, high, step in ADJUSTMENTS:
            spin = QDoubleSpinBox()
            spin.setRange(low, high); spin.setSingleStep(step); spin.setValue(default)
            spin.valueChanged.connect(lambda: self.preview_timer.start(80))
            title = QLabel(text); form.addRow(title,spin); self.adjust_widgets.extend([title,spin])
            self.values[key] = spin
        self.crop_widgets = []; self.crop_values = {}
        self.ratio = QComboBox()
        for title,value in [("Libre",0),("Carré 1:1",1),("Paysage 4:3",4/3),("Paysage 16:9",16/9),("Portrait 3:4",3/4),("Portrait 9:16",9/16)]: self.ratio.addItem(title,value)
        ratio_label=QLabel("Proportions"); form.addRow(ratio_label,self.ratio); self.crop_widgets += [ratio_label,self.ratio]
        self.ratio.currentIndexChanged.connect(lambda: setattr(self.canvas,"ratio",self.ratio.currentData()))
        for key,title,limit,value in [("x","Position X",self.image.width-1,0),("y","Position Y",self.image.height-1,0),("width","Largeur",self.image.width,self.image.width),("height","Hauteur",self.image.height,self.image.height)]:
            spin=QSpinBox(); spin.setRange(0 if key in {"x","y"} else 1,limit); spin.setValue(value)
            spin.valueChanged.connect(self.set_crop); title_widget=QLabel(title); form.addRow(title_widget,spin)
            self.crop_values[key]=spin; self.crop_widgets += [title_widget,spin]
        self.canvas.cropChanged.connect(self.sync_crop)
        self.pen_size=QSpinBox(); self.pen_size.setRange(1,100); self.pen_size.setValue(5)
        self.pen_size.valueChanged.connect(lambda v:setattr(self.canvas,"pen_width",v))
        self.font_size=QSpinBox(); self.font_size.setRange(8,300); self.font_size.setValue(32)
        self.font_size.valueChanged.connect(lambda v:setattr(self.canvas,"font_size",v))
        pen_label,font_label=QLabel("Trait (pixels)"),QLabel("Texte (pixels)")
        form.addRow(pen_label,self.pen_size); form.addRow(font_label,self.font_size)
        self.annotation_widgets=[pen_label,self.pen_size,font_label,self.font_size]
        self.compare=QCheckBox("Voir l’original"); self.compare.toggled.connect(self.adjust); root.addWidget(self.compare)
        self.sections.currentIndexChanged.connect(self.change_section)
        self.sections.setCurrentIndex(max(0,self.sections.findData(initial))); self.change_section()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer une copie")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def adjust(self):
        self.canvas.show_original = self.compare.isChecked()
        self.canvas.preview = self.preview_source if self.compare.isChecked() else adjust_photo(self.preview_source, {key:spin.value() for key,spin in self.values.items()})
        self.canvas.update()

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self.canvas.color),self,"Couleur des annotations")
        if color.isValid(): self.canvas.color=color.name()

    def change_section(self):
        key=self.sections.currentData(); self.tools.clear()
        choices={"edit_image":[("Ajuster la photo","adjust")],"crop_image":[("Tracer le recadrage","crop")],"redact_image":[("Masque opaque","redact"),("Flou","blur")],"annotate_image":[("Flèche","arrow"),("Texte","text"),("Rectangle","rectangle"),("Ellipse","ellipse"),("Numéro","number"),("Dessin libre","pen"),("Surligner","highlight"),("Ligne","line")]}
        for title,tool in choices.get(key,[]): self.tools.addItem(title,tool)
        self.canvas.tool=self.tools.currentData() or "adjust"
        for widgets,visible in [(self.adjust_widgets,key=="edit_image"),(self.crop_widgets,key=="crop_image"),(self.annotation_widgets,key=="annotate_image")]:
            for widget in widgets: widget.setVisible(visible)
        self.color_button.setVisible(key=="annotate_image")

    def set_crop(self):
        v={key:spin.value() for key,spin in self.crop_values.items()}
        self.canvas.crop=[v['x'],v['y'],min(self.image.width,v['x']+v['width']),min(self.image.height,v['y']+v['height'])]
        self.sync_crop(); self.canvas.update()

    def sync_crop(self):
        x,y,right,bottom=self.canvas.crop or [0,0,self.image.width,self.image.height]
        for key,value in dict(x=x,y=y,width=right-x,height=bottom-y).items():
            self.crop_values[key].blockSignals(True); self.crop_values[key].setValue(value); self.crop_values[key].blockSignals(False)

    def undo(self):
        if self.canvas.history: self.canvas.annotations,self.canvas.crop=self.canvas.history.pop()
        elif self.canvas.annotations: self.canvas.annotations.pop()
        else: self.canvas.crop = None
        self.sync_crop()
        self.canvas.update()

    def reset(self):
        self.canvas.crop = None
        self.canvas.annotations = []
        self.canvas.history = []
        for key,title,default,*_ in ADJUSTMENTS: self.values[key].setValue(default)
        self.sync_crop(); self.adjust()
        self.canvas.update()

    def options(self):
        result = {key: spin.value() for key, spin in self.values.items()}
        result["crop"] = self.canvas.crop
        dx, dy = self.canvas.crop[:2] if self.canvas.crop else (0, 0)
        result["annotations"] = [{**a, "box": [a["box"][0]-dx, a["box"][1]-dy, a["box"][2]-dx, a["box"][3]-dy], **({"points":[[p[0]-dx,p[1]-dy] for p in a["points"]]} if "points" in a else {})} for a in self.canvas.annotations]
        return result
