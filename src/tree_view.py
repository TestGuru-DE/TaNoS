import json
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyle

def create_example_tree():
    """Erstellt ein Beispielmodell mit Kategorien und Werten (4 Spalten)."""
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels([
        "Klassifikations-Baum", "Gewichtung", "Schaden", "Nutzung"
    ])
    root = model.invisibleRootItem()

    # Beispiel-Root
    root_cat = QStandardItem("Portoberechnung")
    row = [root_cat] + [QStandardItem("") for _ in range(3)]
    root.appendRow(row)

    # Beispielkategorien und Werte
    gewicht_cat = add_category(root_cat, "Gewicht")
    add_value(gewicht_cat, "Bis 500 g")
    add_value(gewicht_cat, "501 bis 1000 g")
    add_value(gewicht_cat, "1001 bis 2000 g")

    groesse_cat = add_category(root_cat, "Größe")
    add_value(groesse_cat, "Klein")
    add_value(groesse_cat, "Mittel")
    add_value(groesse_cat, "Groß")

    versandart_cat = add_category(root_cat, "Versandart")
    add_value(versandart_cat, "Overnight")
    add_value(versandart_cat, "Normal")
    add_value(versandart_cat, "Gefahrgut")

    innerDeutsch_cat = add_category(root_cat, "Innerdeutsch")
    add_value(innerDeutsch_cat, "True")
    add_value(innerDeutsch_cat, "False")
   
    nachrichtPostbote_cat = add_category(root_cat, "Nachricht an Bote")
    add_value(nachrichtPostbote_cat, "nichts")
    add_value(nachrichtPostbote_cat, "An der Tür abgeben")
    add_value(nachrichtPostbote_cat, "Mülleimer")
    add_value(nachrichtPostbote_cat, "NULL")

    return model

def add_category(parent, name):
    """Kategorie hinzufügen (nur Name, restliche Spalten leer)."""
    cat_item = QStandardItem(name)
    gewichtung_item = QStandardItem("")
    schaden_item = QStandardItem("")
    nutzung_item = QStandardItem("")

    # Flags: Kategorien sind NICHT editierbar
    for col_item in [gewichtung_item, schaden_item, nutzung_item]:
        col_item.setFlags(Qt.ItemIsEnabled)  # nur sichtbar, nicht editierbar

    row = [cat_item, gewichtung_item, schaden_item, nutzung_item]
    parent.appendRow(row)
    return cat_item

def add_value(parent, name, status="allowed"):
    value_item = QStandardItem(name)

    gewichtung_item = QStandardItem("0")
    schaden_item = QStandardItem("")
    nutzung_item = QStandardItem("")

    # Sichtbarkeit sicherstellen
    for col_item in [gewichtung_item, schaden_item, nutzung_item]:
        col_item.setFlags(col_item.flags() | Qt.ItemIsEditable)
        col_item.setForeground(Qt.black)  # <<<<< wichtig!

    value_item.setForeground(Qt.black)

    row = [value_item, gewichtung_item, schaden_item, nutzung_item]
    parent.appendRow(row)
    return value_item


def load_wertesammlung_config(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def deep_copy_item(item: QStandardItem) -> QStandardItem:
    clone = QStandardItem(item.text())
    clone.setData(item.data(Qt.UserRole), Qt.UserRole)
    clone.setIcon(item.icon())
    for row in range(item.rowCount()):
        child = item.child(row)
        clone.appendRow(deep_copy_item(child))
    return clone
