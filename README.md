# GeTeCaDe - TestCase Designer (Version 5.0)

### Neu in v5.0
- Export/Import von Testfällen im CSV-Format (Trennzeichen = Semikolon).
- Status-Spalte (allowed/error) wird mit exportiert und beim Import wieder gesetzt.
- Auswahl beim Import: Überschreiben oder Ergänzen bestehender Daten.
- Unit Tests für Export/Import (csv_handler).



### Neu in v5.7.1
- CSV-API harmonisiert: `export_to_csv` akzeptiert optional `testcase_names`, `import_from_csv` liefert standardmäßig (categories, status, testcases), optional mit `return_names=True` zusätzlich die Spaltennamen.
- Orthogonal-Strategie implementiert als Pairwise-Generator (2-Wege-Abdeckung), inkl. Unittests.
- Test-Setup verbessert (`tests/conftest.py`) für saubere Importe aus `src/`.

#### Beispiel: CSV-Export/Import
```python
from io_handlers import csv_handler

cats = ["Gewicht", "Größe"]
status = {"Gewicht":"allowed","Größe":"error"}
tcs = [
    {"Gewicht":"500g","Größe":"Klein"},
    {"Gewicht":"1000g","Größe":"Mittel"},
]
csv_handler.export_to_csv("out.csv", cats, status, tcs)  # Spalten: TC_1, TC_2
cats2, status2, tcs2 = csv_handler.import_from_csv("out.csv")

## Backend & Browser (MVP)

### Start (Entwicklung)
```bash
# 1) Abhängigkeiten
pip install -r requirements.txt
# Falls nicht vorhanden, minimal nötig:
# pip install fastapi uvicorn sqlalchemy jinja2 httpx

# 2) Backend
uvicorn app.main:app --reload

# 3) Browser-UI
# http://127.0.0.1:8000/ui/generate
# API-Docs (Swagger):
# http://127.0.0.1:8000/docs


### Umbenennen / Löschen / Sortieren (UI)
- Projekte: /ui/projects – Umbenennen & Löschen per Inline-Formular.
- Kategorien & Werte: /ui/projects/{pid}/data – Umbenennen/Löschen je Zeile, Kategorien per Drag&Drop sortieren.
- Sicherheit: Löschen/Umsortieren/Umbenennen ist blockiert, wenn bereits Generierungen existieren.
