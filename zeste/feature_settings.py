"""Persistent, per-tool switches shared by both wheels and the dispatcher."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from .catalog import feature_groups


class FeatureSettings(QWidget):
    changed = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        root = QVBoxLayout(self); root.setContentsMargins(32, 30, 32, 24)
        title = QLabel("Fonctionnalités"); title.setObjectName("title"); root.addWidget(title)
        note = QLabel("Coche les outils à proposer dans la roue. Le type de fichier et le nombre de fichiers sélectionnés déterminent ensuite les outils disponibles.")
        note.setWordWrap(True); root.addWidget(note)
        self.search = QLineEdit(); self.search.setPlaceholderText("Rechercher une fonctionnalité…"); root.addWidget(self.search)
        row = QHBoxLayout()
        for text, enabled in [("Tout activer", True), ("Tout désactiver", False)]:
            button = QPushButton(text); button.clicked.connect(lambda checked=False, value=enabled: self.set_all(value)); row.addWidget(button)
        root.addLayout(row)
        self.tree = QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.setColumnCount(1)
        self.items = {}
        for title, features in feature_groups():
            group = QTreeWidgetItem(self.tree, [title]); group.setExpanded(True)
            for key, label, detail in features:
                item = QTreeWidgetItem(group, [label]); item.setData(0, Qt.ItemDataRole.UserRole, key)
                item.setToolTip(0, detail); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if settings.value("features/"+key, True, bool) else Qt.CheckState.Unchecked)
                self.items[key] = item
        root.addWidget(self.tree, 1)
        self.tree.itemChanged.connect(self.save)
        self.search.textChanged.connect(self.filter)
        hint = QLabel("Pendant un glissement : Ctrl ouvre la roue ; Tab passe aux Outils puis aux Actions. Les changements sont enregistrés immédiatement.")
        hint.setWordWrap(True); root.addWidget(hint)

    def save(self, item, column):
        key = item.data(0, Qt.ItemDataRole.UserRole)
        if key:
            self.settings.setValue("features/"+key, item.checkState(0) == Qt.CheckState.Checked)
            self.settings.sync(); self.changed.emit()

    def set_all(self, enabled):
        self.tree.blockSignals(True)
        for key, item in self.items.items():
            item.setCheckState(0, Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.settings.setValue("features/"+key, enabled)
        self.tree.blockSignals(False); self.settings.sync(); self.changed.emit()

    def filter(self, text):
        text = text.casefold().strip()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i); count = 0
            for j in range(group.childCount()):
                item = group.child(j)
                visible = text in (group.text(0)+" "+item.text(0)+" "+item.toolTip(0)).casefold()
                item.setHidden(not visible); count += visible
            group.setHidden(count == 0)
