
## `CHANGELOG.md` (neu anlegen im Projektstamm)

```markdown
# Changelog

## [5.7.1] – 2025-10-06
### Added
- Pairwise/Orthogonal-Generator implementiert (`combinatorics/orthogonal.py`).
- Tests: `tests/test_pairwise.py`, `tests/test_csv_handler_names.py`, `tests/conftest.py`.

### Changed
- CSV-API stabilisiert: `export_to_csv` mit optionalen `testcase_names`, `import_from_csv` liefert per Default 3 Werte, optional 4.

### Fixed
- Import-Probleme in Tests durch fehlende `conftest.py`.

## Browser-CRUD-UI (Projekte, Kategorien, Werte)

- Projekte: `GET /ui/projects`
  - Neues Projekt anlegen (HTMX-Form)
- Projekt-Daten: `GET /ui/projects/{pid}/data`
  - Kategorien anlegen (Name, order_index)
  - Werte pro Kategorie anlegen (value, risk_weight)

Navigation: In der Generate-Seite gibt es einen Link zurück zu „Projekte“.


## [5.8.1] – 2025-10-07
### Added
- UI: Rename & Delete für Projekte, Kategorien, Werte (Jinja+HTMX).
- UI: Kategorien per Drag&Drop sortieren (SortableJS), persistiert als order_index.
### Changed
- SQLite: PRAGMA foreign_keys=ON (sauberere Cascades).
### Guardrails
- Änderungen blockiert, wenn Generierungen existieren (später Force-Option geplant).
