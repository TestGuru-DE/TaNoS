import json
from PySide6.QtGui import QStandardItem, QStandardItemModel, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QStyle
from rules.dependency_rule import DependencyRule


def save_project(filepath, tree_model, rules, rule_names, table_widget):
    """Speichert das Projekt (Testdaten, Regeln, Testfälle) als JSON."""
    data = {
        "testdaten": {},
        "testfaelle": {},
        "regeln": []
    }

    # Testdatenbaum serialisieren (rekursiv)
    root = tree_model.invisibleRootItem()
    for i in range(root.rowCount()):
        cat_item = root.child(i, 0)
        data["testdaten"][cat_item.text()] = serialize_item(cat_item)

    # Testfälle serialisieren
    for col in range(table_widget.columnCount()):
        tc_name = (
            table_widget.horizontalHeaderItem(col).text()
            if table_widget.horizontalHeaderItem(col)
            else f"Testfall {col+1}"
        )
        testcase = {}
        for row in range(table_widget.rowCount()):
            cat = table_widget.verticalHeaderItem(row).text()
            widget = table_widget.cellWidget(row, col)
            if widget:
                testcase[cat] = widget.currentText()
        data["testfaelle"][tc_name] = testcase

    # Regeln serialisieren
    for idx, rule in enumerate(rules):
        name = rule_names[idx] if idx < len(rule_names) else f"Regel {idx+1}"

        if hasattr(rule, "conditions"):  # ExcludeRule
            data["regeln"].append({
                "name": name,
                "type": "exclude",
                "conditions": rule.conditions
            })
        elif isinstance(rule, DependencyRule):
            data["regeln"].append({
                "name": name,
                "type": "dependency",
                "if": {rule.if_category: rule.if_value},
                "then": {rule.then_category: rule.then_value}
            })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def serialize_item(item):
    """Rekursiv einen QStandardItem und seine Kinder in ein dict/list umwandeln."""
    if item.hasChildren():
        data = {}
        for i in range(item.rowCount()):
            child = item.child(i, 0)
            data[child.text()] = serialize_item(child)
        return data
    else:
        # Blatt → Wert mit Status
        return item.data(Qt.UserRole) or "allowed"


def deserialize_item(data, parent_item):
    style = QApplication.style()

    if isinstance(data, dict):
        # Kategorie
        for key, value in data.items():
            child = QStandardItem(key)
            child.setIcon(style.standardIcon(QStyle.SP_FileDialogListView))  # Ordnersymbol
            row = [child] + [QStandardItem("") for _ in range(3)]
            parent_item.appendRow(row)
            deserialize_item(value, child)
    else:
        # Blattwert
        parent_item.setData(data, Qt.UserRole)
        if data == "allowed":
            parent_item.setIcon(style.standardIcon(QStyle.SP_DialogApplyButton))
        else:
            parent_item.setIcon(style.standardIcon(QStyle.SP_MessageBoxCritical))  # anderes Symbol für "unerlaubt"


def load_project(filepath, exclude_rule_class):
    """Lädt Projekt-JSON und gibt (tree_model, rules, rule_names, testfaelle) zurück."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(["Testdaten"])
    root = model.invisibleRootItem()

    # Testdaten
    for cat, values in data.get("testdaten", {}).items():
        cat_item = QStandardItem(cat)
        root.appendRow([cat_item])
        deserialize_item(values, cat_item)

    # Regeln
    rules = []
    rule_names = []
    for rule in data.get("regeln", []):
        if rule["type"] == "exclude":
            r = exclude_rule_class(rule["conditions"])
        elif rule["type"] == "dependency":
            if_cat, if_val = list(rule["if"].items())[0]
            then_cat, then_val = list(rule["then"].items())[0]
            r = DependencyRule(if_cat, if_val, then_cat, then_val)
        else:
            continue  # unbekannter Typ
        rules.append(r)
        rule_names.append(rule["name"])

    testfaelle = data.get("testfaelle", {})

    return model, rules, rule_names, testfaelle
