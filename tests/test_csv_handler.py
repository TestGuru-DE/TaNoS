import tempfile, os
from io_handlers import csv_handler

def test_export_import_roundtrip():
    categories = ["Gewicht", "Größe"]
    status = {"Gewicht": "allowed", "Größe": "error"}
    testcases = [
        {"Gewicht": "500g", "Größe": "Klein"},
        {"Gewicht": "1000g", "Größe": "Mittel"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "t.csv")
        csv_handler.export_to_csv(file_path, categories, status, testcases)

        # Robust gegen 3 oder 4+ Rückgabewerte:
        cats, stat, tcs, *_ = csv_handler.import_from_csv(file_path)

    assert cats == categories
    assert stat == status
    assert tcs == testcases
