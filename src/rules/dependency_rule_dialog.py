from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout


class DependencyRuleDialog(QDialog):
    def __init__(self, categories: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Neue Abhängigkeitsregel")

        self.categories = categories  # <-- Früh setzen, bevor Combos gefüllt werden

        self.if_category = None
        self.if_value = None
        self.then_category = None
        self.then_value = None

        layout = QVBoxLayout(self)

        # IF-Kategorie
        layout.addWidget(QLabel("Wenn Kategorie:"))
        self.if_cat_combo = QComboBox()
        self.if_cat_combo.addItems(categories.keys())
        layout.addWidget(self.if_cat_combo)

        # IF-Wert
        layout.addWidget(QLabel("Hat Wert:"))
        self.if_val_combo = QComboBox()
        layout.addWidget(self.if_val_combo)

        # THEN-Kategorie
        layout.addWidget(QLabel("Dann Kategorie:"))
        self.then_cat_combo = QComboBox()
        self.then_cat_combo.addItems(categories.keys())
        layout.addWidget(self.then_cat_combo)

        # THEN-Wert
        layout.addWidget(QLabel("Hat Wert:"))
        self.then_val_combo = QComboBox()
        layout.addWidget(self.then_val_combo)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        # Initial füllen
        self.update_if_values()
        self.update_then_values()
        self.if_cat_combo.currentTextChanged.connect(self.update_if_values)
        self.then_cat_combo.currentTextChanged.connect(self.update_then_values)


    def update_if_values(self):
        cat = self.if_cat_combo.currentText()
        self.if_val_combo.clear()
        if cat in self.categories:
            self.if_val_combo.addItems(self.categories[cat])

    def update_then_values(self):
        cat = self.then_cat_combo.currentText()
        self.then_val_combo.clear()
        if cat in self.categories:
            self.then_val_combo.addItems(self.categories[cat])

    def get_rule(self):
        if_cat = self.if_cat_combo.currentText()
        if_val = self.if_val_combo.currentText()
        then_cat = self.then_cat_combo.currentText()
        then_val = self.then_val_combo.currentText()
        return (if_cat, if_val, then_cat, then_val)
