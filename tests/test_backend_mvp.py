import os
import tempfile
from fastapi.testclient import TestClient
import uuid
from app.main import app


# Sicherstellen, dass src/ importierbar ist (conftest.py existiert bereits)
from app.main import app

client = TestClient(app)

def test_end_to_end_pairwise_generation(tmp_path):
    # Eindeutiger Projektname pro Testlauf
    project_name = f"Demo-{uuid.uuid4().hex[:6]}"

    # 1) Projekt anlegen
    r = client.post("/projects", json={"name": project_name})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    # 2) Kategorien & Werte
    r = client.post(f"/projects/{pid}/categories", json={"name": "Gewicht", "order_index": 0})
    assert r.status_code == 200
    cid_w = r.json()["id"]
    r = client.post(f"/categories/{cid_w}/values", json={"value": "500g"})
    assert r.status_code == 200
    r = client.post(f"/categories/{cid_w}/values", json={"value": "1000g"})
    assert r.status_code == 200

    r = client.post(f"/projects/{pid}/categories", json={"name": "Farbe", "order_index": 1})
    assert r.status_code == 200
    cid_f = r.json()["id"]
    r = client.post(f"/categories/{cid_f}/values", json={"value": "Rot"})
    assert r.status_code == 200
    r = client.post(f"/categories/{cid_f}/values", json={"value": "Blau"})
    assert r.status_code == 200

    # 3) Strategien abrufen
    r = client.get("/strategies")
    assert r.status_code == 200
    assert "pairwise" in r.json()

    # 4) Generieren (pairwise)
    r = client.post(f"/projects/{pid}/generate", json={"strategy": "pairwise"})
    assert r.status_code == 200, r.text
    gen_id = r.json()["generation_id"]
    count = r.json()["count"]
    assert count > 0

    # 5) Testfälle lesen
    r = client.get(f"/generations/{gen_id}/testcases")
    assert r.status_code == 200
    testcases = r.json()
    assert len(testcases) == count
    assert "assignments" in testcases[0]
    # Prüfen, dass jede Zuordnung beide Kategorien enthält
    for tc in testcases:
        assert set(tc["assignments"].keys()) == {"Gewicht", "Farbe"}

    # 6) CSV export
    r = client.get(f"/generations/{gen_id}/export/csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "Kategorie;Status;" in r.text

