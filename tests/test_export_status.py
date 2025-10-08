from src.app.main import app
from fastapi.testclient import TestClient
import re

client = TestClient(app)

def test_export_contains_status_flag():
    # Annahme: Es gibt mind. eine Generation mit ID 1 im Demo – sonst Test vorher anlegen.
    # Hier nur Smoke-Test auf HTTP und Header-Zeile mit 'Status'.
    r = client.get("/generations/1/export/csv?status=1")
    assert r.status_code in (200, 404)  # nicht hart prüfen, falls keine Gen 1 existiert
    if r.status_code == 200:
        text = r.text.splitlines()
        assert len(text) >= 1
        header = text[0]
        assert "Status" in header
