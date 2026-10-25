from pathlib import Path
import pymupdf as fitz
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QImage, QPixmap, QTransform
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QPushButton, QDialogButtonBox, QMessageBox


class PdfOrganizer(QDialog):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Organiser les pages · "+Path(path).name); self.resize(880,650)
        root=QVBoxLayout(self); root.addWidget(QLabel("Glisse les pages pour changer leur ordre. Sélectionne une ou plusieurs pages pour les modifier."))
        self.pages=QListWidget(); self.pages.setViewMode(QListWidget.ViewMode.IconMode)
        self.pages.setIconSize(QSize(120,160)); self.pages.setGridSize(QSize(170,210))
        self.pages.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.pages.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.pages.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.pages.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.thumbnails={}
        with fitz.open(path) as doc:
            if doc.needs_pass: raise ValueError("Déverrouille une copie du PDF avant de continuer.")
            for index,page in enumerate(doc):
                pix=page.get_pixmap(matrix=fitz.Matrix(min(120/page.rect.width,160/page.rect.height),min(120/page.rect.width,160/page.rect.height)),alpha=False)
                thumb=QPixmap.fromImage(QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy())
                self.thumbnails[index]=thumb
                item=QListWidgetItem(QIcon(thumb),f"Page {index+1}"); item.setData(Qt.ItemDataRole.UserRole,dict(page=index,rotation=0))
                self.pages.addItem(item)
        root.addWidget(self.pages,1)
        row=QHBoxLayout()
        for title,fn in [("Pivoter 90°",self.rotate),("Dupliquer",self.duplicate),("Retirer",self.remove)]:
            button=QPushButton(title); button.clicked.connect(fn); row.addWidget(button)
        root.addLayout(row)
        note=QLabel("Les pages retirées le sont uniquement dans la nouvelle copie. L’original est conservé."); note.setWordWrap(True); root.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer une copie")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def rotate(self):
        for item in self.pages.selectedItems():
            data=dict(item.data(Qt.ItemDataRole.UserRole)); data['rotation']=(data['rotation']+90)%360
            item.setData(Qt.ItemDataRole.UserRole,data)
            item.setIcon(QIcon(self.thumbnails[data['page']].transformed(QTransform().rotate(data['rotation']))))
            item.setText(f"Page {data['page']+1} · {data['rotation']}°")

    def duplicate(self):
        for item in self.pages.selectedItems(): self.pages.insertItem(self.pages.row(item)+1,item.clone())

    def remove(self):
        for item in self.pages.selectedItems(): self.pages.takeItem(self.pages.row(item))

    def options(self):
        return {"page_plan":[self.pages.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.pages.count())]}

    def accept(self):
        if not self.pages.count(): QMessageBox.information(self,"Pages","Conserve au moins une page."); return
        super().accept()


class FileOrderDialog(QDialog):
    def __init__(self, paths, parent=None):
        super().__init__(parent); self.setWindowTitle("Ordre des fichiers"); self.resize(600,420)
        root=QVBoxLayout(self); root.addWidget(QLabel("Glisse les fichiers pour définir l’ordre de l’assemblage."))
        self.files=QListWidget(); self.files.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        for path in paths:
            item=QListWidgetItem(Path(path).name); item.setData(Qt.ItemDataRole.UserRole,str(path)); item.setToolTip(str(path)); self.files.addItem(item)
        root.addWidget(self.files)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Assembler")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def paths(self): return [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]
