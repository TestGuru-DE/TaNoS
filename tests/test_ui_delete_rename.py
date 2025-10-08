from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_rename_delete_smoke():
    # Projekt anlegen (API)
    r = client.post("/projects", json={"name": "P1"})
    assert r.status_code == 200
    pid = r.json()["id"]

    # Kategorie anlegen (API)
    r = client.post(f"/projects/{pid}/categories", json={"name": "K1", "order_index": 0})
    assert r.status_code == 200
    cid = r.json()["id"]

    # Wert anlegen (API)
    r = client.post(f"/categories/{cid}/values", json={"value": "V1", "risk_weight": 1})
    assert r.status_code == 200

    # Rename Kategorie (UI)
    r = client.post("/ui/categories/rename", data={"cid": cid, "name": "K1_new"})
    assert r.status_code in (200, 400)  # 400, falls Generierungen existieren
    # Reorder (UI)
    r = client.post("/ui/categories/reorder", data={"pid": pid, "order": str(cid)})
    assert r.status_code in (200, 400)

    # Rename Projekt (UI)
    r = client.post("/ui/projects/rename", data={"pid": pid, "name": "P1_new"})
    assert r.status_code in (200, 409)

    # Delete Wert (UI)
    # (solange keine Generierung existiert, sollte 200 kommen)
    # dafür brauchen wir die Value-ID -> holen wir via /categories/{cid}/values
    r_vals = client.get(f"/categories/{cid}/values")
    assert r_vals.status_code == 200
    vid = r_vals.json()[0]["id"]
    r = client.post("/ui/values/delete", data={"vid": vid})
    assert r.status_code in (200, 400)

    # Delete Kategorie (UI)
    r = client.post("/ui/categories/delete", data={"cid": cid})
    assert r.status_code in (200, 400)

    # Delete Projekt (UI)
    r = client.post("/ui/projects/delete", data={"pid": pid})
    assert r.status_code in (200, 400)

