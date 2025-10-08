from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from db.connection import Base, engine, get_db
from db import crud, models

# DB-Tabellen anlegen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GeTeCaDe DB-Backend")

@app.get("/")
def root():
    return {"status": "OK", "message": "GeTeCaDe-DB läuft"}

# --- Kategorien ---
@app.get("/categories")
def read_categories(db: Session = Depends(get_db)):
    cats = crud.get_all_categories(db)
    return [{"id": c.id, "name": c.name, "parent_id": c.parent_id} for c in cats]

@app.post("/categories")
def create_category(name: str, db: Session = Depends(get_db)):
    cat = crud.create_category(db, name=name)
    return {"id": cat.id, "name": cat.name}

# --- Werte ---
@app.post("/values")
def create_value(category_id: int, name: str, schaden: float = 0, nutzung: float = 0, db: Session = Depends(get_db)):
    val = crud.create_value(db, category_id, name, schaden, nutzung)
    return {"id": val.id, "name": val.name, "gewichtung": val.gewichtung}

@app.get("/values/{category_id}")
def read_values(category_id: int, db: Session = Depends(get_db)):
    vals = crud.get_values_by_category(db, category_id)
    return [{"id": v.id, "name": v.name, "gewichtung": v.gewichtung} for v in vals]

# --- Testfälle ---
@app.post("/testcases")
def create_testcase(name: str, data: dict, db: Session = Depends(get_db)):
    tc = crud.create_testcase(db, name, data)
    return {"id": tc.id, "name": tc.name, "data": tc.data}

@app.get("/testcases")
def read_testcases(db: Session = Depends(get_db)):
    tcs = crud.get_all_testcases(db)
    return [{"id": t.id, "name": t.name, "data": t.data} for t in tcs]

# --- Regeln ---
@app.post("/rules")
def create_rule(name: str, type_: str, definition: dict, db: Session = Depends(get_db)):
    rule = crud.create_rule(db, name, type_, definition)
    return {"id": rule.id, "name": rule.name, "type": rule.type, "definition": rule.definition}


@app.get("/rules")
def read_rules(db: Session = Depends(get_db)):
    rules = crud.get_all_rules(db)
    return [
        {"id": r.id, "name": r.name, "type": r.type, "definition": r.definition}
        for r in rules
    ]
