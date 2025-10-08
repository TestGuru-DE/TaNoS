import csv
from typing import List, Dict, Tuple, Optional

# Wir verwenden Semikolon (;) – kompatibel zu deutschen Excel-Defaults.

def export_to_csv(
    filepath: str,
    categories: List[str],
    status: Dict[str, str],
    testcases: List[Dict[str, str]],
    testcase_names: Optional[List[str]] = None,
) -> None:
    """
    Layout (Semikolon-separiert):
        Kategorie;Status;TC_1;TC_2;...
        Gewicht;allowed;500g;1000g
        Größe;error;Klein;Mittel
    - categories: Reihenfolge der Zeilen
    - status: Map Kategorie -> Status (default "allowed")
    - testcases: Liste von Dicts (ein Dict pro Testfall)
    - testcase_names: Spaltenköpfe (optional, sonst TC_1..TC_N)
    """
    if testcase_names is None:
        testcase_names = [f"TC_{i+1}" for i in range(len(testcases))]
    else:
        if len(testcase_names) != len(testcases):
            raise ValueError(
                f"Length of testcase_names ({len(testcase_names)}) "
                f"does not match number of testcases ({len(testcases)})."
            )
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Kategorie", "Status", *testcase_names])
        for cat in categories:
            row = [cat, status.get(cat, "allowed")]
            for tc in testcases:
                row.append(tc.get(cat, ""))
            writer.writerow(row)


def import_from_csv(
    filepath: str,
    return_names: bool = False,  # bleibt erhalten, wird aber ignoriert (immer 4 Rückgabewerte)
) -> Tuple[List[str], Dict[str, str], List[Dict[str, str]], List[str]]:
    """
    Liest CSV im Layout:
        Kategorie;Status;TC_1;TC_2;...
        Gewicht;allowed;500g;1000g
        Größe;error;Klein;Mittel

    Rückgabe (immer 4 Werte):
        categories: List[str]
        status: Dict[str, str]               # Kategorie -> Status (default "allowed")
        testcases: List[Dict[str, str]]      # ein Dict pro Testfall
        testcase_names: List[str]            # Spaltenköpfe der Testfälle

    Hinweis:
    - 'return_names' wird aus Kompatibilitätsgründen akzeptiert, aber ignoriert.
    """
    import csv

    categories: List[str] = []
    status: Dict[str, str] = {}
    testcases: List[Dict[str, str]] = []
    testcase_names: List[str] = []

    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        rows = [row for row in reader if any(cell.strip() for cell in row)]

    if not rows:
        return categories, status, testcases, testcase_names

    header = rows[0]
    if len(header) < 2:
        raise ValueError("CSV header must contain at least 'Kategorie' and 'Status' columns")

    # Ab Spalte 3 sind es Testfall-Spaltennamen
    testcase_names = header[2:]
    num_cases = len(testcase_names)

    # Vorbereiten: ein Dict pro Testfall
    for _ in range(num_cases):
        testcases.append({})

    # Datenzeilen verarbeiten
    for r in rows[1:]:
        if not r:
            continue
        cat = r[0].strip()
        if not cat:
            continue
        categories.append(cat)
        status[cat] = r[1].strip() if len(r) > 1 and r[1].strip() != "" else "allowed"
        for i in range(num_cases):
            val = r[i + 2].strip() if len(r) > i + 2 and r[i + 2] is not None else ""
            testcases[i][cat] = val

    return categories, status, testcases, testcase_names

