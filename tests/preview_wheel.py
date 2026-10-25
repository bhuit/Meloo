"""Render the application's own translucent widget over a generated backdrop."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter,QPixmap,QColor,QLinearGradient,QFont,QFontDatabase
from PySide6.QtCore import Qt,QPointF
from zeste.radial import Wheel

root=Path(__file__).resolve().parents[1]
app=QApplication([])
for name in ['segoeui.ttf','segoeuib.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
wheel=Wheel(popup=True);wheel.reduce_motion=True
wheel.set_files([str(root/'exemples/Carte de démonstration.png')])
wheel.show();wheel.hovered=0;app.processEvents()
result=QPixmap(700,430);result.fill(QColor('#edf2f3'))
p=QPainter(result);p.setRenderHint(QPainter.RenderHint.Antialiasing)
gradient=QLinearGradient(QPointF(0,0),QPointF(700,430));gradient.setColorAt(0,QColor('#b8d6dc'));gradient.setColorAt(1,QColor('#f3d6b8'))
p.fillRect(result.rect(),gradient)
p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(255,255,255,65));p.drawEllipse(QPointF(140,160),200,200)
p.drawPixmap(350,55,wheel.grab())
p.setPen(QColor('#203e43'));p.setFont(QFont('Segoe UI',24,QFont.Weight.DemiBold));p.drawText(35,110,'Glisser. Ctrl. Déposer.')
p.setFont(QFont('Segoe UI',13));p.drawText(38,160,'Compresser ou convertir,');p.drawText(38,188,'sans ouvrir une fenêtre.')
p.setFont(QFont('Segoe UI',11));p.drawText(38,330,'ZESTE · WINDOWS · 0.2.1');p.drawText(38,355,'Roue claire translucide · traitement local')
p.end();result.save(str(root/'apercu-roue-021.png'))
wheel.close();app.quit()
