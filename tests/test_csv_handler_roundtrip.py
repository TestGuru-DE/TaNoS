import tempfile, os
from io_handlers import csv_handler

def test_export_import_roundtrip_always_four_values():
    categories = ["Gewicht", "Größe"]
    status = {"Gewicht":"allowed","Größe":"error"}
    testcases = [
        {"Gewicht":"500g","Größe":"Klein"},
        {"Gewicht":"1000g","Größe":"Mittel"},
    ]
    names = ["HappyPath", "EdgeCase"]

    with tempfile.TemporaryDirectory() as tmpdir:
        file = os.path.join(tmpdir, "test.csv")
        csv_handler.export_to_csv(file, categories, status, testcases, testcase_names=names)

        # Rückgabe sind immer 4 Werte – unabhängig vom zweiten Param
        cats2, status2, tcs2, names2 = csv_handler.import_from_csv(file)
        assert categories == cats2
        assert status == status2
        assert testcases == tcs2
        assert names == names2

        cats3, status3, tcs3, names3 = csv_handler.import_from_csv(file, return_names=True)
        assert (cats2, status2, tcs2, names2) == (cats3, status3, tcs3, names3)

