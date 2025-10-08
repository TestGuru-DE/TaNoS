import requests

API_URL = "http://127.0.0.1:8000"

# -------- Kategorien --------
def get_categories():
    """Alle Kategorien aus der Datenbank laden"""
    resp = requests.get(f"{API_URL}/categories")
    resp.raise_for_status()
    return resp.json()

def create_category(name):
    """Neue Kategorie anlegen"""
    resp = requests.post(f"{API_URL}/categories", params={"name": name})
    resp.raise_for_status()
    return resp.json()


# -------- Werte --------
def get_values(category_id):
    """Werte zu einer Kategorie abrufen"""
    resp = requests.get(f"{API_URL}/values/{category_id}")
    resp.raise_for_status()
    return resp.json()

def create_value(category_id, name, schaden=0, nutzung=0):
    """Neuen Wert zu Kategorie hinzufügen"""
    resp = requests.post(
        f"{API_URL}/values",
        params={
            "category_id": category_id,
            "name": name,
            "schaden": schaden,
            "nutzung": nutzung,
        },
    )
    resp.raise_for_status()
    return resp.json()

# -------- Testfälle --------
def create_testcase(name, data):
    resp = requests.post(f"{API_URL}/testcases", params={"name": name}, json=data)
    resp.raise_for_status()
    return resp.json()

def get_testcases():
    resp = requests.get(f"{API_URL}/testcases")
    resp.raise_for_status()
    return resp.json()

