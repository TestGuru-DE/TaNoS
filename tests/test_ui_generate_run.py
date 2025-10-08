from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ui_generate_run_route_exists():
    r = client.get("/ui/generate")
    assert r.status_code == 200

    # Route darf nicht 404 liefern – Status 200/400/422 sind ok je nach Datenlage
    r = client.post("/ui/generate/run", data={"pid": 1, "strategy": "pairwise"})
    assert r.status_code in (200, 400, 422), r.text
    