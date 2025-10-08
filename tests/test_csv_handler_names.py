import tempfile, os
from io_handlers import csv_handler

def test_export_import_with_names_roundtrip():
    categories = ["Gewicht", "Größe"]
    status = {"Gewicht":"allowed","Größe":"error"}
    testcases = [
        {"Gewicht":"500g","Größe":"Klein"},
        {"Gewicht":"1000g","Größe":"Mittel"},
    ]
    names = ["HappyPath", "EdgeCase"]
    with tempfile.TemporaryDirectory() as tmpdir:
        file = os.path.join(tmpdir,"test.csv")
        csv_handler.export_to_csv(file, categories, status, testcases, testcase_names=names)
        cats2, status2, tcs2, names2 = csv_handler.import_from_csv(file, return_names=True)
    assert categories == cats2
    assert status == status2
    assert testcases == tcs2
    assert names == names2

