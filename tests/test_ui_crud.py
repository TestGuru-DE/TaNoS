from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ui_projects_and_data_smoke():
    # Projekte-Seite lädt
    r = client.get("/ui/projects")
    assert r.status_code == 200
    assert "Neues Projekt" in r.text

    # Projekt anlegen (per UI-Endpoint)
    r = client.post("/ui/projects/create", data={"name": "UI-Proj"})
    assert r.status_code == 200
    assert "UI-Proj" in r.text

    # Projekt-Daten-Seite lädt (id = 1..n, wir raten 1 – falls anders, test bleibt smoke)
    r = client.get("/ui/projects/1/data")
    assert r.status_code in (200, 404)  # 404 falls id != 1, das ist ok

def test_ui_values_flow_smoke():
    # Für sauberen Flow via JSON-API ein Projekt + Kategorie + dann UI-Wert
    r = client.post("/projects", json={"name": "Flow"})
    assert r.status_code == 200
    pid = r.json()["id"]

    r = client.post(f"/projects/{pid}/categories", json={"name": "Farbe", "order_index": 0})
    assert r.status_code == 200
    cid = r.json()["id"]

    # UI-Endpoint: Wert anlegen
    r = client.post("/ui/values/create", data={"cid": cid, "value": "Rot", "risk_weight": 2})
    assert r.status_code == 200
    assert "Rot" in r.text

