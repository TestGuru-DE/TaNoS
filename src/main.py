import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTreeView, QTableWidget, QTableWidgetItem,
    QStatusBar, QMenuBar, QFileDialog, QMessageBox, QMenu, QComboBox,
    QGroupBox, QVBoxLayout, QHeaderView, QToolBar, QStyle, QInputDialog
)
import api_client
from PySide6.QtGui import QStandardItem, QAction, QStandardItemModel
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIcon


from tree_view import create_example_tree, load_wertesammlung_config, deep_copy_item
from tree_view import create_example_tree #add_category, add_value
from combinatorics import all_combinations, each_choice, orthogonal
from io_handlers import csv_handler

from rules.exclude_rule_dialog import ExcludeRuleDialog
from rules.exclude_rule import ExcludeRule

from rules.dependency_rule_dialog import DependencyRuleDialog
from rules.dependency_rule import DependencyRule

from project_handler import save_project, load_project


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TaNoS - TestAutomatisierungsNotationsSystem v5.4")
        self.resize(1280, 800)

        self.wertesammlungen = {}
        self.clipboard_item = None
        self.rules = []        # aktive Regeln (Objekte)
        self.rule_names = []   # Namen der Regeln (für Header)

        # Menüleiste
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        # Datei-Menü
        file_menu = menu_bar.addMenu("Datei")
 
        new_proj_action = file_menu.addAction("Neues Projekt…")
        new_proj_action.triggered.connect(self.new_project)

        save_proj_action = file_menu.addAction("Projekt speichern…")
        save_proj_action.triggered.connect(self.save_project)

        load_proj_action = file_menu.addAction("Projekt laden…")
        load_proj_action.triggered.connect(self.load_project)

        import_action = file_menu.addAction("Import Wertesammlung…")
        import_action.triggered.connect(self.import_wertesammlung)

        export_csv_action = file_menu.addAction("Export Testfälle")
        export_csv_action.triggered.connect(self.export_csv)

        import_csv_action = file_menu.addAction("Import Testfälle")
        import_csv_action.triggered.connect(self.import_csv)

        # Bearbeiten-Menü
        edit_menu = menu_bar.addMenu("Bearbeiten")
        remove_testcase_action = edit_menu.addAction("Testfall entfernen")
        remove_testcase_action.triggered.connect(self.remove_selected_testcase_column)
        new_testcase_action = edit_menu.addAction("Neuer Testfall")
        new_testcase_action.triggered.connect(self.add_testcase_column)

        # Regeln-Menü
        rules_menu = menu_bar.addMenu("Regeln")
        new_exclude_rule_action = rules_menu.addAction("Neue Ausschlussregel…")
        new_exclude_rule_action.triggered.connect(self.add_exclude_rule)
        dep_rule_action = rules_menu.addAction("Neue Abhängigkeitsregel…")
        dep_rule_action.triggered.connect(self.add_dependency_rule)

        # Toolbar mit Kombinatorik-Buttons
        toolbar = QToolBar("Kombinationen")
        self.addToolBar(toolbar)

        btn_all = QAction("All Combinations", self)
        btn_all.triggered.connect(self.generate_all_combinations)
        toolbar.addAction(btn_all)

        btn_each = QAction("Each Choice", self)
        btn_each.triggered.connect(self.generate_each_choice)
        toolbar.addAction(btn_each)

        btn_orth = QAction("Orthogonal", self)
        btn_orth.triggered.connect(self.generate_orthogonal)
        toolbar.addAction(btn_orth)

        # Splitter
        splitter = QSplitter(Qt.Horizontal, self)

        # Linkes Fenster (Testdaten mit Regeln im TreeView)

        left_box = QGroupBox("Testdaten & Regeln")
        left_layout = QVBoxLayout()
        self.tree_view = QTreeView()
        self.model = create_example_tree()  # liefert QStandardItemModel
        self.tree_view.setModel(self.model)
        # Alle Spalten sichtbar machen
        for col in range(self.model.columnCount()):
            self.tree_view.setColumnHidden(col, False)

        # Optional: Spaltenbreite
        self.tree_view.header().setSectionResizeMode(QHeaderView.Interactive)
        # Neues Modell mit zusätzlichen Spalten
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels([
            "Klassifikations-Baum", "Gewichtung", "Schaden", "Nutzung"
        ])
        self.tree_view.setModel(self.model)
        self.tree_view.setHeaderHidden(False)

        self.model.dataChanged.connect(self.handle_data_changed)
        # Style: horizontale Linien für bessere Orientierung
        self.tree_view.setStyleSheet("QTreeView::item { border-bottom: 1px solid #ccc; }")
    # Beispiel Baum
        self.model = create_example_tree()
        self.tree_view.setModel(self.model)
        self.model.dataChanged.connect(self.handle_data_changed)
        
        self.tree_view.expandAll()
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.open_context_menu)

        # Header editierbar machen (für Regeln)
        self.tree_view.header().setSectionsClickable(True)
        self.tree_view.header().sectionDoubleClicked.connect(self.rename_rule_header)

        self.load_tree_from_api()

        left_layout.addWidget(self.tree_view)
        left_box.setLayout(left_layout)
        
        #Regeln löschen
        remove_rule_action = rules_menu.addAction("Regel löschen…")
        remove_rule_action.triggered.connect(self.remove_rule)
        
        # Rechtes Fenster (Testfälle)
        right_box = QGroupBox("Testfälle")
        right_layout = QVBoxLayout()
        self.table_widget = QTableWidget()
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Scrollbars immer sichtbar, wenn Inhalt größer ist
        self.table_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Spaltenbreite manuell anpassbar
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # statt Stretch
        header.setStretchLastSection(False)

        # Zeilenhöhe dynamisch, wie bisher
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        
        right_layout.addWidget(self.table_widget)
        right_box.setLayout(right_layout)

        # Editierbare Testfall-Namen
        self.table_widget.horizontalHeader().sectionDoubleClicked.connect(self.rename_testcase_column)

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        self.setCentralWidget(splitter)

        # Statusleiste
        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage("Bereit")
        #----EXPERIMENT
        #print("Model columnCount:", self.model.columnCount())
        #root = self.model.invisibleRootItem()
        #for i in range(root.rowCount()):
        #    print("Row", i, "cols:", root.child(i, 0).columnCount())

        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setStyleSheet("""
            QTreeView::item {
                color: black;
                border-bottom: 1px solid #ccc;
            }
            QTreeView::item:selected {
                background-color: lightblue;
                color: black;
            }
        """)

    def load_tree_from_api(self):
        """Lädt Kategorien und Werte aus der DB und baut den Baum auf."""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Klassifikations-Baum"])
        root = self.model.invisibleRootItem()

        categories = api_client.get_categories()
        cats_by_id = {}

        # Kategorien erstellen
        for cat in categories:
            item = QStandardItem(cat["name"])
            item.setEditable(False)
            cats_by_id[cat["id"]] = item
            if cat["parent_id"]:
                parent_item = cats_by_id.get(cat["parent_id"])
                if parent_item:
                    parent_item.appendRow(item)
                else:
                    root.appendRow(item)
            else:
                root.appendRow(item)

        # Werte hinzufügen
        for cat_id, cat_item in cats_by_id.items():
            values = api_client.get_values(cat_id)
            for val in values:
                val_item = QStandardItem(val["name"])
                val_item.setEditable(False)
                cat_item.appendRow(val_item)

        self.tree_view.setModel(self.model)
        self.tree_view.expandAll()

    def add_category_via_api(self, parent_item=None):
        name, ok = QInputDialog.getText(self, "Neue Kategorie", "Name der Kategorie:")
        if not ok or not name.strip():
            return
        cat = api_client.create_category(name)
        new_item = QStandardItem(cat["name"])
        if parent_item:
            parent_item.appendRow(new_item)
        else:
            self.model.invisibleRootItem().appendRow(new_item)
        self.statusBar().showMessage(f"Kategorie '{name}' erstellt (ID {cat['id']})")


    def add_value_via_api(self, parent_item):
        name, ok = QInputDialog.getText(self, "Neuer Wert", "Name des Werts:")
        if not ok or not name.strip():
            return
        # Wir nehmen die Kategorie-ID über den Namen (später eleganter via Mapping)
        categories = api_client.get_categories()
        cat = next((c for c in categories if c["name"] == parent_item.text()), None)
        if not cat:
            QMessageBox.warning(self, "Fehler", "Kategorie in DB nicht gefunden.")
            return
        val = api_client.create_value(cat["id"], name)
        new_item = QStandardItem(val["name"])
        parent_item.appendRow(new_item)
        self.statusBar().showMessage(f"Wert '{name}' gespeichert (Gewichtung: {val['gewichtung']})")

    def save_current_testcases(self):
        """Speichert alle aktuell angezeigten Testfälle in der DB."""
        for col in range(self.table_widget.columnCount()):
            name_item = self.table_widget.horizontalHeaderItem(col)
            name = name_item.text() if name_item else f"Testfall {col+1}"
            data = {}
            for row in range(self.table_widget.rowCount()):
                cat = self.table_widget.verticalHeaderItem(row).text()
                combo = self.table_widget.cellWidget(row, col)
                if combo:
                    data[cat] = combo.currentText()
            api_client.create_testcase(name, data)
        self.statusBar().showMessage("Alle Testfälle in DB gespeichert ✅")

    def load_testcases_from_api(self):
        tcs = api_client.get_testcases()
        # Hier: wie bei display_testcases aus deiner bisherigen Logik anzeigen

    def rename_rule_header(self, col: int):
        """Erlaubt das Umbenennen von Regelspalten (aber nicht 'Testdaten')."""
        if col == 0:
            return  # Die erste Spalte "Testdaten" bleibt fix
        old_name = self.model.headerData(col, Qt.Horizontal)
        new_name, ok = QInputDialog.getText(self, "Regel umbenennen", "Neuer Name:", text=old_name)
        if ok and new_name.strip():
            self.rule_names[col - 4] = new_name.strip()
            self.model.setHeaderData(col, Qt.Horizontal, new_name.strip())
    
    def handle_data_changed(self, topLeft, bottomRight, roles):
        """Berechnet Gewichtung = Schaden × Nutzung automatisch."""
        for row in range(topLeft.row(), bottomRight.row() + 1):
            parent = topLeft.model().itemFromIndex(topLeft.siblingAtColumn(0)).parent()
            if not parent:  # Root oder Kategorie → überspringen
                continue
            gewichtung_item = parent.child(row, 1)
            schaden_item = parent.child(row, 2)
            nutzung_item = parent.child(row, 3)

            try:
                schaden = int(schaden_item.text()) if schaden_item and schaden_item.text() else 0
                nutzung = int(nutzung_item.text()) if nutzung_item and nutzung_item.text() else 0
                auto_value = schaden * nutzung
            except ValueError:
                auto_value = 0

            # Nur überschreiben, wenn Nutzer nicht manuell gesetzt hat
            if gewichtung_item and (not gewichtung_item.text() or gewichtung_item.text() == "0"):
                gewichtung_item.setText(str(auto_value))

    
    #-------Projekthandling---------------
    def new_project(self):
        """Leeres Projekt starten mit nur einem Root-Element 'Neues Projekt'."""
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Testdaten"])
        root = self.model.invisibleRootItem()
        root.appendRow(QStandardItem("Neues Projekt"))

        self.tree_view.setModel(self.model)
        self.rules = []
        self.rule_names = []
        self.table_widget.clear()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.statusBar().showMessage("Neues Projekt gestartet.")


    def save_project(self):
        """Speichert das aktuelle Projekt als JSON."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Projekt speichern", "", "Projektdateien (*.tanosproj)")
        if not file_path:
            return
        save_project(file_path, self.model, self.rules, self.rule_names, self.table_widget)
        self.statusBar().showMessage(f"Projekt gespeichert: {file_path}")

    def load_project(self):
        """Lädt ein Projekt aus JSON."""
        from rules.exclude_rule import ExcludeRule
        file_path, _ = QFileDialog.getOpenFileName(self, "Projekt laden", "", "Projektdateien (*.tanosproj)")
        if not file_path:
            return

        model, rules, rule_names, testfaelle = load_project(file_path, ExcludeRule)

        self.model = model
        self.tree_view.setModel(self.model)
        self.rules = rules
        self.rule_names = rule_names

        # Regelspalten hinzufügen (einmalig!)
        for idx, name in enumerate(self.rule_names, start=1):
            col = self.model.columnCount()
            self.model.setColumnCount(col + 1)
            self.model.setHeaderData(col, Qt.Horizontal, name)

        self.update_rule_columns()

        # Regel-Spalten hinzufügen
        #for idx, name in enumerate(self.rule_names, start=1):
        #    col = self.model.columnCount()
        #    self.model.setColumnCount(col + 1)
        #    self.model.setHeaderData(col, Qt.Horizontal, name)
        #self.update_rule_columns()

        # Testfälle wiederherstellen
        if testfaelle:
            cats = list(next(iter(testfaelle.values())).keys())
            self.table_widget.setRowCount(len(cats))
            self.table_widget.setColumnCount(len(testfaelle))
            self.table_widget.setVerticalHeaderLabels(cats)

            for col, (tc_name, tc_data) in enumerate(testfaelle.items()):
                header_item = QTableWidgetItem(tc_name)
                self.table_widget.setHorizontalHeaderItem(col, header_item)
                for row, cat in enumerate(cats):
                    combo = QComboBox()
                    combo.addItems(self.get_categories_from_tree().get(cat, []))
                    if cat in tc_data:
                        idx = combo.findText(tc_data[cat])
                        if idx >= 0:
                            combo.setCurrentIndex(idx)
                    self.table_widget.setCellWidget(row, col, combo)

        self.statusBar().showMessage(f"Projekt geladen: {file_path}")


    # ---------------- Regeln ----------------
    def add_exclude_rule(self):
        dlg = ExcludeRuleDialog(self.get_categories_from_tree(), self)
        if dlg.exec() == QDialog.Accepted:
            rule = dlg.get_rule()
            if rule:
                self.rules.append(rule)
                self.rule_names.append(f"Regel {len(self.rule_names)+1}")
                # Neue Spalte ins Modell einfügen
                col = self.model.columnCount()
                self.model.setColumnCount(col + 1)
                self.model.setHeaderData(col, Qt.Horizontal, self.rule_names[-1])
                self.update_rule_columns()
                self.statusBar().showMessage(f"Ausschlussregel hinzugefügt: {rule.conditions}")

    def add_dependency_rule(self):
        """Dialog für neue Abhängigkeitsregel öffnen."""
        from PySide6.QtWidgets import QDialog
        cats = self.get_categories_from_tree()
        dlg = DependencyRuleDialog(cats, self)
        if dlg.exec() == QDialog.Accepted:
            if_cat, if_val, then_cat, then_val = dlg.get_rule()

            # Prüfen: keine zweite Abhängigkeit für dieselbe Kategorie
            for rule in self.rules:
                if isinstance(rule, DependencyRule) and rule.if_category == if_cat:
                    QMessageBox.warning(self, "Regel ungültig",
                                        f"Es existiert bereits eine Abhängigkeit für '{if_cat}'.")
                    return

            # Regel anlegen
            rule = DependencyRule(if_cat, if_val, then_cat, then_val)
            self.rules.append(rule)
            self.rule_names.append(f"Dependency: {if_cat}→{then_cat}")

            # Neue Spalte für die Regel
            col = self.model.columnCount()
            self.model.setColumnCount(col + 1)
            self.model.setHeaderData(col, Qt.Horizontal, self.rule_names[-1])

            self.update_rule_columns()
            self.statusBar().showMessage(f"Abhängigkeitsregel hinzugefügt: {rule}")
    #REgelspalten bauen
    #QStyle.SP_MessageBoxCritical oder QStyle.SP_MediaStop

    def update_rule_columns(self):
        """Aktualisiert die Symbole der Regeln im TreeView (Exclude + Dependency)."""
        from rules.dependency_rule import DependencyRule
        style = self.style()

        def apply_rules(item):
            if item.rowCount() == 0:  # Blatt
                text = item.text()
                cat_item = item.parent()
                cat_name = cat_item.text() if cat_item else None

                for col, rule in enumerate(self.rules, start=4):
                    rule_item = self.model.itemFromIndex(item.index().siblingAtColumn(col))
                    if rule_item is None:
                        rule_item = QStandardItem()
                        cat_item.setChild(item.row(), col, rule_item)

                    # Exclude-Rule
                    if hasattr(rule, "conditions"):
                        if cat_name in rule.conditions and text in rule.conditions[cat_name]:
                            rule_item.setIcon(style.standardIcon(QStyle.SP_MediaStop))
                        else:
                            rule_item.setIcon(QIcon())

                    # Dependency-Rule
                    elif isinstance(rule, DependencyRule):
                        if (cat_name == rule.if_category and text == rule.if_value):
                            rule_item.setIcon(style.standardIcon(QStyle.SP_ArrowRight))  # Bedingung
                        elif (cat_name == rule.then_category and text == rule.then_value):
                            rule_item.setIcon(style.standardIcon(QStyle.SP_ArrowForward))  # Konsequenz
                        else:
                            rule_item.setIcon(QIcon())
            else:
                for r in range(item.rowCount()):
                    apply_rules(item.child(r))

        root = self.model.invisibleRootItem()
        for i in range(root.rowCount()):
            apply_rules(root.child(i))


        def rename_rule_header(self, col: int):
            if col == 0:
                return  # "Testdaten" bleibt fix
            old_name = self.model.headerData(col, Qt.Horizontal)
            new_name, ok = QInputDialog.getText(self, "Regel umbenennen", "Neuer Name:", text=old_name)
            if ok and new_name.strip():
                self.rule_names[col-1] = new_name.strip()
                self.model.setHeaderData(col, Qt.Horizontal, new_name.strip())

    def apply_rules(self, testcases: list[dict]) -> list[dict]:
        """Wendet alle Regeln (Exclude + Dependency) auf die generierten Testfälle an."""
        result = []
        for tc in testcases:
            valid = True
            for rule in self.rules:
                if hasattr(rule, "conditions"):  # ExcludeRule
                    if not rule.check(tc):
                        valid = False
                        break
                elif isinstance(rule, DependencyRule):
                    tc = rule.apply(tc)  # verändert den Testfall
            if valid:
                result.append(tc)
        return result
    
    #    Regel Löschen
    def remove_rule(self):
        """Ermöglicht das Löschen einer bestehenden Regel."""
        if not self.rule_names:
            QMessageBox.information(self, "Info", "Keine Regeln vorhanden.")
            return

        # Auswahl-Dialog
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self,
            "Regel löschen",
            "Wählen Sie eine Regel zum Löschen:",
            self.rule_names,
            0,
            False
        )

        if ok and name in self.rule_names:
            idx = self.rule_names.index(name)
            del self.rules[idx]
            del self.rule_names[idx]

            # Spalte entfernen (Index +1, da Spalte 0 = Testdaten ist)
            self.model.removeColumn(idx + 1)

            self.update_rule_columns()
            self.statusBar().showMessage(f"Regel gelöscht: {name}")

    # ---------------- Testfälle ----------------
    def rename_testcase_column(self, col: int):
        old_name = self.table_widget.horizontalHeaderItem(col).text()
        new_name, ok = QInputDialog.getText(self, "Testfall umbenennen", "Neuer Name:", text=old_name)
        if ok and new_name.strip():
            self.table_widget.setHorizontalHeaderItem(col, QTableWidgetItem(new_name.strip()))

    def export_csv(self):
        cats = list(self.get_categories_from_tree().keys())
        if not cats:
            QMessageBox.warning(self, "Warnung", "Keine Kategorien vorhanden.")
            return

        # Status aus Baum
        status = {}
        root = self.tree_view.model().invisibleRootItem()
        if root.rowCount() == 1 and root.child(0).rowCount() > 0:
            root = root.child(0)
        for i in range(root.rowCount()):
            cat_item = root.child(i)
            status[cat_item.text()] = cat_item.child(0).data(Qt.UserRole)

        # Testfälle
        testcases = []
        testcase_names = []
        for col in range(self.table_widget.columnCount()):
            tc = {}
            for row in range(self.table_widget.rowCount()):
                cat = self.table_widget.verticalHeaderItem(row).text()
                widget = self.table_widget.cellWidget(row, col)
                if widget:
                    tc[cat] = widget.currentText()
            testcases.append(tc)
            header_item = self.table_widget.horizontalHeaderItem(col)
            testcase_names.append(header_item.text() if header_item else f"Testfall {col+1}")

        file_path, _ = QFileDialog.getSaveFileName(self, "Testfälle exportieren", "", "CSV Dateien (*.csv)")
        if not file_path:
            return
        csv_handler.export_to_csv(file_path, cats, status, testcases, testcase_names)
        self.statusBar().showMessage(f"CSV exportiert: {file_path}")

    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Testfälle importieren", "", "CSV Dateien (*.csv)")
        if not file_path:
            return
        cats, status, testcases, testcase_names = csv_handler.import_from_csv(file_path)
        if not cats:
            QMessageBox.warning(self, "Warnung", "CSV-Datei leer oder ungültig.")
            return

        reply = QMessageBox.question(
            self,
            "Import-Optionen",
            "Möchten Sie bestehende Testdaten/Testfälle überschreiben?\nJa = Überschreiben, Nein = Ergänzen",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.table_widget.clear()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.tree_view.setModel(create_example_tree())

        self.display_testcases_with_names(testcases, testcase_names)

    def display_testcases_with_names(self, testcases: list[dict], testcase_names: list[str]):
        if not testcases:
            return
        categories = list(testcases[0].keys())
        self.table_widget.clear()
        self.table_widget.setRowCount(len(categories))
        self.table_widget.setColumnCount(len(testcases))
        self.table_widget.setVerticalHeaderLabels(categories)

        for col, tc in enumerate(testcases):
            name = testcase_names[col] if col < len(testcase_names) else f"Testfall {col+1}"
            header_item = QTableWidgetItem(name)
            header_item.setFlags(header_item.flags() | Qt.ItemIsEditable)
            self.table_widget.setHorizontalHeaderItem(col, header_item)

            for row, cat in enumerate(categories):
                combo = QComboBox()
                combo.addItems(self.get_categories_from_tree().get(cat, []))
                if cat in tc:
                    idx = combo.findText(tc[cat])
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                self.table_widget.setCellWidget(row, col, combo)

    # ---------------- Wertesammlung ----------------
    def import_wertesammlung(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wertesammlung importieren", "", "JSON Dateien (*.json)"
        )
        if not file_path:
            return
        try:
            self.wertesammlungen = load_wertesammlung_config(file_path)
            self.statusBar().showMessage(f"Wertesammlung geladen: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Import fehlgeschlagen:\n{e}")
#---- nur zur probe

#--- probe ende
    def open_context_menu(self, pos: QPoint):
        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return

        item = self.tree_view.model().itemFromIndex(index)
        menu = QMenu(self)

        # Neues Element
        menu.addAction("Neues Element", lambda: self.add_new_item(item))
        menu.addSeparator()

        
        menu.addAction("Neue Kategorie (DB)", lambda: self.add_category_via_api(item))
        menu.addAction("Neuer Wert (DB)", lambda: self.add_value_via_api(item))
        menu.addSeparator()
        # Basisfunktionen
        menu.addAction("Einfügen", lambda: self.insert_item(item))
        menu.addAction("Kopieren", lambda: self.copy_item(item))
        menu.addAction("Ausschneiden", lambda: self.cut_item(item))
        menu.addAction("Löschen", lambda: self.delete_item(item))

        # Kontextmenü für Werte (Blätter)
        if item.rowCount() == 0:
            menu.addSeparator()
            menu.addAction("Als erlaubt markieren", lambda: self.mark_item(item, "allowed"))
            menu.addAction("Als Fehlerwert markieren", lambda: self.mark_item(item, "error"))
        else:
            menu.addSeparator()
            menu.addAction("Als Kategorie markieren", lambda: self.mark_item(item, "category"))

        menu.addSeparator()

        # Wertesammlung
        ws_menu = menu.addMenu("Wertesammlung")
        self.add_submenu(ws_menu, self.wertesammlungen, item)

        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def add_submenu(self, parent_menu, data, parent_item):
        """Rekursives Menü für Wertesammlungen."""
        if isinstance(data, dict):
            for key, value in data.items():
                sub_menu = parent_menu.addMenu(str(key))
                if isinstance(value, (dict, list)):
                    sub_menu.addAction("Alle Werte",
                        lambda checked=False, v=value: self.add_all_values_to_item(parent_item, v))
                self.add_submenu(sub_menu, value, parent_item)
        elif isinstance(data, list):
            if all(not isinstance(e, (dict, list)) for e in data):
                for val in data:
                    parent_menu.addAction(str(val),
                        lambda checked=False, v=val: self.add_value_to_item(parent_item, v))
            else:
                for i, entry in enumerate(data):
                    sub_menu = parent_menu.addMenu(f"Eintrag {i+1}")
                    sub_menu.addAction("Alle Werte",
                        lambda checked=False, v=entry: self.add_all_values_to_item(parent_item, v))
                    self.add_submenu(sub_menu, entry, parent_item)
        else:
            parent_menu.addAction(str(data),
                lambda checked=False, v=data: self.add_value_to_item(parent_item, v))

    def add_value_to_item(self, parent_item, value):
        new_item = QStandardItem(str(value))
        self.mark_item(new_item, "allowed")  # Standard: allowed
        parent_item.appendRow([new_item])

    def add_all_values_to_item(self, parent_item, data):
        if isinstance(data, dict):
            for value in data.values():
                self.add_all_values_to_item(parent_item, value)
        elif isinstance(data, list):
            for entry in data:
                self.add_all_values_to_item(parent_item, entry)
        else:
            new_item = QStandardItem(str(data))
            self.mark_item(new_item, "allowed")
            parent_item.appendRow([new_item])


    # ---------------- Baum-Operationen ----------------
    def add_new_item(self, parent_item: QStandardItem):
        """Fügt ein neues Kind-Element unter dem ausgewählten Item ein."""
        text, ok = QInputDialog.getText(self, "Neues Element", "Name des neuen Elements:")
        if ok and text.strip():
            new_item = QStandardItem(text.strip())

            style = self.style()

            if parent_item.hasChildren() or parent_item.parent() is None:
                # Wenn unter einem Kategorie-Knoten → neuer Wert
                new_item.setData("allowed", Qt.UserRole)
                new_item.setIcon(style.standardIcon(QStyle.SP_DialogApplyButton))
            else:
                # Wenn unter einem Wert oder Root → neue Kategorie
                new_item.setData(None, Qt.UserRole)
                new_item.setIcon(style.standardIcon(QStyle.SP_FileDialogListView))

            parent_item.appendRow([new_item])
            self.statusBar().showMessage(f"Neues Element hinzugefügt: {text.strip()}")

        
    def insert_item(self, item: QStandardItem):
        if not self.clipboard_item:
            self.statusBar().showMessage("Zwischenablage ist leer.")
            return
        item.appendRow(deep_copy_item(self.clipboard_item))

    def copy_item(self, item: QStandardItem):
        self.clipboard_item = deep_copy_item(item)
        self.statusBar().showMessage(f"Kopiert: {item.text()}")

    def cut_item(self, item: QStandardItem):
        self.clipboard_item = deep_copy_item(item)
        parent = item.parent() or self.tree_view.model().invisibleRootItem()
        parent.removeRow(item.row())
        self.statusBar().showMessage(f"Ausgeschnitten: {item.text()}")

    def delete_item(self, item: QStandardItem):
        parent = item.parent() or self.tree_view.model().invisibleRootItem()
        text = item.text()
        parent.removeRow(item.row())
        self.statusBar().showMessage(f"Gelöscht: {text}")
   
   #Setzt das Icon und den Status für ein Item.
    def mark_item(self, item: QStandardItem, status: str):
        """Setzt Icon und Status abhängig vom Typ (Kategorie oder Wert)."""
        style = self.style()

        if status == "category":
            # explizit als Kategorie markieren
            item.setIcon(style.standardIcon(QStyle.SP_FileDialogListView))
            item.setData(None, Qt.UserRole)
        elif status == "allowed":
            item.setIcon(style.standardIcon(QStyle.SP_DialogApplyButton))
            item.setData("allowed", Qt.UserRole)
        elif status == "error":
            item.setIcon(style.standardIcon(QStyle.SP_MessageBoxCritical)) #QStyle.SP_MessageBoxCritical
            item.setData("error", Qt.UserRole)
        
    # ---------------- Testfälle ----------------
    def get_categories_from_tree(self):
        cats = {}
        root = self.tree_view.model().invisibleRootItem()
        if root.rowCount() == 1 and root.child(0).rowCount() > 0:
            root = root.child(0)
        for i in range(root.rowCount()):
            cat_item = root.child(i)
            cat_name = cat_item.text()
            values = [cat_item.child(j).text() for j in range(cat_item.rowCount())]
            if not values:
                values = ["----"]
            cats[cat_name] = values
        return cats

    def display_testcases(self, testcases: list[dict]):
        if not testcases:
            return
        categories = list(testcases[0].keys())
        self.table_widget.clear()
        self.table_widget.setRowCount(len(categories))
        self.table_widget.setColumnCount(len(testcases))
        self.table_widget.setVerticalHeaderLabels(categories)
        for col, tc in enumerate(testcases):
            header_item = QTableWidgetItem(f"Testfall {col+1}")
            header_item.setFlags(header_item.flags() | Qt.ItemIsEditable)
            self.table_widget.setHorizontalHeaderItem(col, header_item)
            for row, cat in enumerate(categories):
                combo = QComboBox()
                combo.addItems(self.get_categories_from_tree().get(cat, []))
                if cat in tc:
                    idx = combo.findText(tc[cat])
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                self.table_widget.setCellWidget(row, col, combo)

    def ensure_table_rows_for_categories(self):
        categories = self.get_categories_from_tree()
        cat_names = list(categories.keys())
        self.table_widget.setRowCount(len(cat_names))
        self.table_widget.setVerticalHeaderLabels(cat_names)

    def add_testcase_column(self):
        categories = self.get_categories_from_tree()
        if not categories:
            QMessageBox.warning(self, "Warnung", "Keine Kategorien im Baum gefunden.")
            return
        self.ensure_table_rows_for_categories()
        col = self.table_widget.columnCount()
        self.table_widget.insertColumn(col)
        header_item = QTableWidgetItem(f"Testfall {col+1}")
        header_item.setFlags(header_item.flags() | Qt.ItemIsEditable)
        self.table_widget.setHorizontalHeaderItem(col, header_item)
        for row, (cat_name, values) in enumerate(categories.items()):
            combo = QComboBox()
            if values:
                combo.addItems(values)
                combo.setCurrentIndex(0)
            else:
                combo.addItem("--kein Wert--")
            self.table_widget.setCellWidget(row, col, combo)

    def remove_selected_testcase_column(self):
        col = self.table_widget.currentColumn()
        if col < 0:
            QMessageBox.information(self, "Info", "Keine Spalte ausgewählt.")
            return
        self.table_widget.removeColumn(col)

    # ---------------- Kombinatorik ----------------
    def generate_all_combinations(self):
        cats = self.get_categories_from_tree()
        tcs = all_combinations.generate(cats)
        tcs = self.apply_rules(tcs)  # NEU
        self.display_testcases(tcs)
        self.update_rule_columns()

    def generate_each_choice(self):
        cats = self.get_categories_from_tree()
        tcs = each_choice.generate(cats)
        tcs = self.apply_rules(tcs)  # NEU
        self.display_testcases(tcs)
        self.update_rule_columns()

    def generate_orthogonal(self):
        cats = self.get_categories_from_tree()
        tcs = orthogonal.generate(cats)
        tcs = self.apply_rules(tcs)  # NEU
        self.display_testcases(tcs)
        self.update_rule_columns()



def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
