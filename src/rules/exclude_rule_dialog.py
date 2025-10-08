from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel, QDialogButtonBox
)

from rules.exclude_rule import ExcludeRule


class ExcludeRuleDialog(QDialog):
    def __init__(self, categories: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Ausschlussregel")
        self.categories = categories
        self.condition_rows = []

        layout = QVBoxLayout(self)

        self.conditions_layout = QVBoxLayout()
        layout.addLayout(self.conditions_layout)

        add_btn = QPushButton("+ Bedingung hinzufügen")
        add_btn.clicked.connect(self.add_condition_row)
        layout.addWidget(add_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Start mit einer Bedingung
        self.add_condition_row()

    def add_condition_row(self):
        row_layout = QHBoxLayout()

        category_combo = QComboBox()
        category_combo.addItems(self.categories.keys())
        row_layout.addWidget(QLabel("Kategorie:"))
        row_layout.addWidget(category_combo)

        value_combo = QComboBox()
        first_cat = category_combo.currentText()
        value_combo.addItems(self.categories.get(first_cat, []))
        row_layout.addWidget(QLabel("Wert:"))
        row_layout.addWidget(value_combo)

        def update_values():
            value_combo.clear()
            value_combo.addItems(self.categories.get(category_combo.currentText(), []))

        category_combo.currentIndexChanged.connect(update_values)

        remove_btn = QPushButton("- Entfernen")
        remove_btn.clicked.connect(lambda: self.remove_condition_row(row_layout))
        row_layout.addWidget(remove_btn)

        self.conditions_layout.addLayout(row_layout)
        self.condition_rows.append((category_combo, value_combo, row_layout))

    def remove_condition_row(self, row_layout):
        for i, (cat_combo, val_combo, layout) in enumerate(self.condition_rows):
            if layout == row_layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                self.conditions_layout.removeItem(layout)
                self.condition_rows.pop(i)
                break

    def get_rule(self):
        conditions = {}
        for cat_combo, val_combo, _ in self.condition_rows:
            cat = cat_combo.currentText()
            val = val_combo.currentText()
            if cat and val:
                if cat not in conditions:
                    conditions[cat] = []
                conditions[cat].append(val)
        if not conditions:
            return None
        return ExcludeRule(conditions)
