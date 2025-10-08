# src/app/main.py
from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi import Query
from sqlalchemy.orm import Session
from typing import List, Dict,Optional, Tuple 
import io
import csv
import os
from .db import Base, engine, get_db
from . import models, schemas
import re                                      # ← neu
from datetime import datetime 
import json
from typing import List, Dict, Optional

# Kombinatorik aus bestehendem Projekt
from combinatorics import all_combinations, each_choice, orthogonal

app = FastAPI(title="TaNoS API", version="0.1.0")

# Jinja-Templates (UI)
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# --- Startup: Tabellen anlegen (Entwicklungsmodus) ---
@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)

def _migrate_db():
    # Nur SQLite hier behandeln
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        # Spalten prüfen
        cols = conn.exec_driver_sql('PRAGMA table_info("values")').fetchall()
        have = {c[1] for c in cols}  # Spaltennamen
        if "allowed" not in have:
            conn.exec_driver_sql('ALTER TABLE "values" ADD COLUMN allowed INTEGER DEFAULT 1')
            conn.exec_driver_sql('UPDATE "values" SET allowed=1 WHERE allowed IS NULL')
        if "vtype" not in have:
            conn.exec_driver_sql('ALTER TABLE "values" ADD COLUMN vtype TEXT DEFAULT "string"')
            conn.exec_driver_sql('UPDATE "values" SET vtype="string" WHERE vtype IS NULL')
                # --- Migration: rules.then_values_json (für type='combine') ---
        cols_rules = conn.exec_driver_sql('PRAGMA table_info("rules")').fetchall()
        rules_have = {c[1] for c in cols_rules}
        if "then_values_json" not in rules_have:
            conn.exec_driver_sql('ALTER TABLE "rules" ADD COLUMN then_values_json TEXT')
        # --- Migration: values.order_index (für Werte-DnD) ---
        cols_vals = conn.exec_driver_sql('PRAGMA table_info("values")').fetchall()
        vals_have = {c[1] for c in cols_vals}
        if "order_index" not in vals_have:
            conn.exec_driver_sql('ALTER TABLE "values" ADD COLUMN order_index INTEGER NOT NULL DEFAULT 0')



@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_db()  # <<< NEU

# ---------------- Hilfsfunktionen -------------------

def _load_categories_values(db: Session, project_id: int) -> Dict[str, List[str]]:
    cats = (
        db.query(models.Category)
        .filter(models.Category.project_id == project_id)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    if not cats:
        return {}
    result: Dict[str, List[str]] = {}
    for c in cats:
        values = (
            db.query(models.Value)
            .filter(models.Value.category_id == c.id, models.Value.allowed == True)  # nur erlaubte
            .order_by(models.Value.id)
            .all()
        )
        result[c.name] = [v.value for v in values]
    return result


def _generate_cases(categories: Dict[str, List[str]], strategy: str) -> List[Dict[str, str]]:
    """Ruft die gewünschte Kombinatorik-Strategie auf (ohne Geschäftsregeln!)."""
    if strategy == "all":
        return all_combinations.generate(categories)
    if strategy == "each":
        return each_choice.generate(categories)
    if strategy in ("pairwise", "orthogonal"):
        return orthogonal.generate(categories)
    raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")

    


# ------------------- API: System --------------------

@app.get("/strategies", response_model=List[str])
def list_strategies() -> List[str]:
    return ["all", "each", "pairwise"]  # "orthogonal" ist Alias zu pairwise


# --------------- API: Projekte & Stammdaten --------

@app.post("/projects", response_model=schemas.ProjectRead)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    exists = db.query(models.Project).filter(models.Project.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=409, detail="Project name already exists.")
    p = models.Project(name=payload.name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

# Das kann vermutlich weg----------------

from fastapi import Query

@app.get("/projects/{pid}/rules", response_model=list[dict])
def api_list_rules(pid: int, db: Session = Depends(get_db)):
    rules = db.query(models.Rule).filter(models.Rule.project_id == pid).order_by(models.Rule.id).all()
    return [
        {
            "id": r.id,
            "type": r.type,
            "if_category_id": r.if_category_id,
            "if_value": r.if_value,
            "then_category_id": r.then_category_id,
            "then_value": r.then_value,
            "then_values_json": r.then_values_json,
        }
        for r in rules
    ]


@app.post("/ui/rules/create", response_class=HTMLResponse)
def ui_rules_create(
    pid: int = Form(...),
    rtype: str = Form(...),  # 'exclude' | 'dependency' | 'combine'
    if_category_id: int = Form(...),
    if_value: str = Form(...),
    then_category_id: int = Form(...),
    then_value: Optional[str] = Form(None),        # nur für exclude/dependency
    then_values: Optional[List[str]] = Form(None), # nur für combine (Multi-Select)
    db: Session = Depends(get_db),
):
    # einfache Validierung
    if rtype not in ("exclude", "dependency", "combine"):
        return HTMLResponse("<p style='color:#b91c1c;'>Ungültiger Regeltyp.</p>", status_code=400)

    # Projekt / Kategorien gehören zusammen?
    cat_ids = [c.id for c in db.query(models.Category.id).filter(models.Category.project_id == pid).all()]
    if if_category_id not in cat_ids or then_category_id not in cat_ids:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie gehört nicht zum Projekt.</p>", status_code=400)

    rule = models.Rule(
        project_id=pid,
        type=rtype,
        if_category_id=if_category_id,
        if_value=if_value,
        then_category_id=then_category_id,
        then_value=then_value or "",
    )

    if rtype == "combine":
        vals = then_values or []
        vals = [v.strip() for v in vals if v and v.strip()]
        if not vals:
            return HTMLResponse("<p style='color:#b91c1c;'>Bitte mindestens einen Zielwert auswählen.</p>", status_code=400)
        rule.then_values_json = json.dumps(vals)


    db.add(rule)
    db.commit()
    return HTMLResponse(_render_rules_block(db, pid) + "<p style='color:#16a34a;'>Regel angelegt.</p>")


@app.post("/ui/rules/delete", response_class=HTMLResponse)
def ui_rules_delete(
    rid: int = Form(...),
    db: Session = Depends(get_db),
):
    r = db.get(models.Rule, rid)
    if not r:
        return HTMLResponse("<p style='color:#b91c1c;'>Regel nicht gefunden.</p>", status_code=404)
    pid = r.project_id
    db.delete(r)
    db.commit()
    return HTMLResponse(_render_rules_block(db, pid) + "<p style='color:#16a34a;'>Regel gelöscht.</p>")

# bis hier löschen?---------------


@app.get("/projects", response_model=List[schemas.ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(models.Project).order_by(models.Project.id).all()
    return rows


@app.post("/projects/{pid}/categories", response_model=schemas.CategoryRead)
def create_category(pid: int, payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    project = db.get(models.Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    c = models.Category(project_id=pid, name=payload.name, order_index=payload.order_index)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@app.get("/projects/{pid}/categories", response_model=List[schemas.CategoryRead])
def list_categories(pid: int, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Category)
        .filter(models.Category.project_id == pid)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    return rows


@app.post("/categories/{cid}/values", response_model=schemas.ValueRead)
def create_value(cid: int, payload: schemas.ValueCreate, db: Session = Depends(get_db)):
    cat = db.get(models.Category, cid)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")
    v = models.Value(category_id=cid, value=payload.value, risk_weight=payload.risk_weight)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@app.get("/categories/{cid}/values", response_model=List[schemas.ValueRead])
def list_values(cid: int, db: Session = Depends(get_db)):
    rows = db.query(models.Value).filter(models.Value.category_id == cid).order_by(models.Value.id).all()
    return rows


# --------------- API: Generierung & Export ----------

@app.post("/projects/{pid}/generate", response_model=schemas.GenerateResponse)
def generate(pid: int, payload: schemas.GenerateRequest, db: Session = Depends(get_db)):
    if payload.limit is not None and payload.limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")

    catmap = _load_categories_values(db, pid)
    if not catmap or any(len(v) == 0 for v in catmap.values()):
        raise HTTPException(status_code=400, detail="Project must have categories and values.")

    cases = _generate_cases(catmap, payload.strategy)
    if payload.limit is not None:
        cases = cases[: payload.limit]

    # Persistieren
    gen = models.Generation(project_id=pid, strategy=payload.strategy)
    db.add(gen)
    db.flush()  # gen.id verfügbar

    # Map Category.name -> id (für TestCaseValue)
    categories = (
        db.query(models.Category)
        .filter(models.Category.project_id == pid)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    cat_by_name = {c.name: c.id for c in categories}

    # Testfälle anlegen (TC_1..N) + Werte
    for idx, assignment in enumerate(cases, start=1):
        tc = models.TestCase(generation_id=gen.id, name=f"TC_{idx}")
        db.add(tc)
        db.flush()
        for k, v in assignment.items():
            db.add(models.TestCaseValue(testcase_id=tc.id, category_id=cat_by_name[k], value=v))

    db.commit()
    return schemas.GenerateResponse(generation_id=gen.id, count=len(cases))


@app.get("/generations/{gid}/testcases", response_model=List[schemas.TestCaseOut])
def get_testcases(gid: int, db: Session = Depends(get_db)):
    # 1) Generation prüfen
    gen = db.get(models.Generation, gid)
    if gen is None:
        raise HTTPException(status_code=404, detail="Generation not found.")

    # 2) Kategorien (für Namensauflösung) – definierte Reihenfolge
    categories = (
        db.query(models.Category)
        .filter(models.Category.project_id == gen.project_id)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    name_by_id = {c.id: c.name for c in categories}

    # 3) Testfälle der Generation
    testcases = (
        db.query(models.TestCase)
        .filter(models.TestCase.generation_id == gid)
        .order_by(models.TestCase.id)
        .all()
    )

    # 4) Ergebnisliste (immer Liste zurückgeben!)
    out: List[dict] = []

    for tc in testcases:
        vals = (
            db.query(models.TestCaseValue)
            .filter(models.TestCaseValue.testcase_id == tc.id)
            .order_by(models.TestCaseValue.id)
            .all()
        )
        assignments = {name_by_id.get(v.category_id, f"cat#{v.category_id}"): v.value for v in vals}
        # Dict zurückgeben; FastAPI/Pydantic validiert das zu TestCaseOut
        out.append({"name": tc.name, "assignments": assignments})

    return out  # <- garantiert Liste (auch wenn leer)

# Komfort-Redirects (nicht in OpenAPI anzeigen)
@app.get("/", include_in_schema=False)
def root():
    # Startseite -> UI
    return RedirectResponse(url="/ui/generate")

@app.get("/ui", include_in_schema=False)
def ui_root():
    # /ui -> /ui/generate
    #return RedirectResponse(url="/ui/generate")
    return RedirectResponse(url="/ui/projects")

@app.get("/ui/generate/", include_in_schema=False)
def ui_generate_slash(request: Request, db: Session = Depends(get_db)):
    # Fange die Variante mit Trailing-Slash ab
    return ui_generate(request, db)


@app.get("/ui/generate", response_class=HTMLResponse)
def ui_generate(request: Request, db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id).all()
    #return templates.TemplateResponse("generate.html", {"request": request, "projects": projects})
    return templates.TemplateResponse(request, "generate.html", {"projects": projects})

# Komfort-Redirects (optional, aber praktisch)
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/generate")

@app.get("/ui", include_in_schema=False)
def ui_root():
    return RedirectResponse(url="/ui/generate")

@app.get("/ui/generate/", include_in_schema=False)
def ui_generate_slash(request: Request, db: Session = Depends(get_db)):
    return ui_generate(request, db)

@app.post("/ui/generate/run", response_class=HTMLResponse)
def ui_generate_run(
    pid: int = Form(...),
    strategy: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Startet die Generierung für das Projekt (pid) mit der gewählten Strategie.
    NEU: Wendet nach der Roh-Kombinatorik die Geschäftsregeln an (combine/exclude/dependency).
    Gibt ein HTML-Fragment zurück: Tabelle der erzeugten Testfälle + CSV-Link.
    """
    # 1) Kategorien + erlaubte Werte laden (bereits berücksichtigt: allowed=True)
    categories = _load_categories_values(db, pid)
    if not categories:
        return HTMLResponse("<p style='color:#b91c1c;'>Keine Kategorien/Werte im Projekt.</p>", status_code=400)

    # 2) Roh-Kombinationen erzeugen
    raw_assignments = _generate_cases(categories, strategy)  # List[Dict[str,str]]

    # 3) Geschäftsregeln anwenden (Combine → Exclude → Dependency)
    final_assignments = _apply_business_rules(pid, raw_assignments, db)

    # 4) Persistieren: Generation + Testfälle + TestCaseValues
    gen = models.Generation(project_id=pid, strategy=strategy)
    db.add(gen)
    db.flush()  # gen.id holen

    # Mapping: Kategoriename -> ID (für TestCaseValue.category_id)
    cat_map = {c.name: c.id for c in db.query(models.Category).filter(models.Category.project_id == pid).all()}

    # Testfälle speichern
    for idx, a in enumerate(final_assignments, start=1):
        tc = models.TestCase(generation_id=gen.id, name=f"TC-{gen.id}-{idx}")
        db.add(tc)
        db.flush()
        for cat_name, val in a.items():
            cid = cat_map.get(cat_name)
            if cid is None:
                # Kategorie wurde evtl. umbenannt/gelöscht -> überspringen (robust)
                continue
            tcv = models.TestCaseValue(testcase_id=tc.id, category_id=cid, value=str(val))
            db.add(tcv)

    db.commit()

    # 5) HTML-Output (kleine Tabelle + Export-Links)
    #    Spaltenüberschriften aus den (aktuellen) Kategorienamen
    headers = list(cat_map.keys())
    # Ein paar Zeilen zeigen, Rest via CSV exportieren
    rows_preview = final_assignments[:25]

    # CSV/JSON-Links (passen zu deinen vorhandenen Endpoints)
    csv_url = f"/generations/{gen.id}/export/csv"
    json_url = f"/generations/{gen.id}/testcases"  # liefert JSON

    # Tabelle rendern
    parts = []
    parts.append(f"<p><strong>Erzeugt:</strong> {len(final_assignments)} Testfälle (Generation #{gen.id})</p>")
    parts.append("<div class='overflow-x-auto'>")
    parts.append("<table><thead><tr>")
    for h in headers:
        parts.append(f"<th>{h}</th>")
    parts.append("</tr></thead><tbody>")
    if rows_preview:
        for a in rows_preview:
            parts.append("<tr>")
            for h in headers:
                parts.append(f"<td>{a.get(h, '')}</td>")
            parts.append("</tr>")
    else:
        parts.append("<tr><td colspan='%d'><em>Keine Kombinationen (Regeln haben alles gefiltert?).</em></td></tr>" % max(1, len(headers)))
    parts.append("</tbody></table></div>")
    parts.append(f"<p class='mt-3'><a href='{csv_url}'>CSV exportieren</a> &nbsp;|&nbsp; <a href='{json_url}' target='_blank'>JSON ansehen</a></p>")

    return HTMLResponse("".join(parts))


# Trailing-Slash-Variante abfangen (zeigt nicht in /docs)
@app.post("/ui/generate/run/", include_in_schema=False)
async def ui_generate_run_slash(
    request: Request,
    pid: int = Form(...),
    strategy: str = Form(...),
    db: Session = Depends(get_db),
):
    return await ui_generate_run(request, pid, strategy, db)  # delegiert an obige Funktion



@app.get("/whoami", include_in_schema=False)
def whoami():
    return {
        "module": __name__,
        "file": __file__,
        "routes": sorted([r.path for r in app.routes])[:12]  # erste paar Routen
    }

@app.get("/generations/{gen_id}/export/csv")
def export_generation_csv(
    gen_id: int,
    include_status: bool = Query(False, alias="status"),
    # NEU: Excel-/Encoding-Optionen:
    encoding: str = Query("utf-8-sig", description="z. B. utf-8-sig, utf-8, cp1252, iso-8859-1, utf-16le, utf-16be, utf-16"),
    excel: bool = Query(True, description="Wenn True: erste Zeile 'sep=;' für Excel"),
    bom: Optional[bool] = Query(None, description="BOM explizit setzen/entfernen; Standard je nach Encoding"),
    db: Session = Depends(get_db),
):
    """
    CSV-Export:
    - Standard: UTF-8 mit BOM ('utf-8-sig'), Semikolon, CRLF, erste Zeile 'sep=;'
    - 'encoding' wählbar (utf-8, cp1252, iso-8859-1, utf-16le/be, utf-16)
    - 'bom' überschreibt Standardverhalten (falls gesetzt)
    - 'excel=1' setzt 'sep=;' zur sicheren Trennzeichenerkennung
    """
    # 1) Generation & Testfälle laden
    gen = db.get(models.Generation, gen_id)
    if not gen:
        raise HTTPException(status_code=404, detail="Generation not found.")
    tcs = (
        db.query(models.TestCase)
        .filter(models.TestCase.generation_id == gen_id)
        .order_by(models.TestCase.id)
        .all()
    )

    # 2) Kopfzeilen (Kategorien) bestimmen
    cats = (
        db.query(models.Category)
        .filter(models.Category.project_id == gen.project_id)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    cat_headers: List[str] = [c.name for c in cats]

    # 3) CSV in Textform bauen (Semikolon + CRLF)
    #    Achtung: newline='' + lineterminator='\r\n' -> sauberes CRLF für Excel
    out = io.StringIO(newline="")
    writer = csv.writer(out, delimiter=';', lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)

    # Optionale Excel-Hinweiszeile
    if excel:
        writer.writerow(["sep=;"])

    # Headerzeile
    headers = cat_headers + ["__TestCaseID", "__GenerationID", "__Strategy"]
    if include_status:
        headers.append("Status")
    writer.writerow(headers)

    # Datenzeilen
    for tc in tcs:
        a = _assignment_from_testcase(db, tc.id)  # {Kategorie: Wert}
        row = [a.get(h, "") for h in cat_headers]
        row += [tc.id, gen.id, gen.strategy]
        if include_status:
            row.append(_status_for_assignment(gen.project_id, a, db))
        writer.writerow(row)

    csv_text: str = out.getvalue()

    # 4) Encoding anwenden (mit optionalem BOM)
    #    Zulässige Encodings
    enc_norm = encoding.lower().strip()
    aliases = {"latin1": "iso-8859-1"}
    enc = aliases.get(enc_norm, enc_norm)

    allowed = {"utf-8", "utf-8-sig", "cp1252", "iso-8859-1", "utf-16", "utf-16le", "utf-16be"}
    if enc not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported encoding '{encoding}'. Allowed: {sorted(allowed)}")

    # Standard-BOM je Encoding
    if bom is None:
        bom_default = enc in {"utf-8-sig", "utf-16", "utf-16le", "utf-16be"}
    else:
        bom_default = bool(bom)

    data_bytes: bytes
    content_charset = enc if enc != "utf-8-sig" else "utf-8"  # header charset-Angabe

    if enc == "utf-8-sig":
        # Python-Codecs 'utf-8-sig' fügt automatisch BOM an
        data_bytes = csv_text.encode("utf-8-sig")
    elif enc in {"utf-16", "utf-16le", "utf-16be"}:
        # BOM ggf. manuell voranstellen
        data_bytes = csv_text.encode(enc if enc != "utf-16" else "utf-16")
        if bom_default:
            # Bei utf-16: Python setzt bereits BOM; bei le/be ggf. ergänzen:
            if enc == "utf-16le" and not data_bytes.startswith(b"\xff\xfe"):
                data_bytes = b"\xff\xfe" + data_bytes
            elif enc == "utf-16be" and not data_bytes.startswith(b"\xfe\xff"):
                data_bytes = b"\xfe\xff" + data_bytes
            # utf-16 (ohne le/be) enthält BOM bereits
        else:
            # BOM ggf. entfernen
            if data_bytes.startswith(b"\xff\xfe"):
                data_bytes = data_bytes[2:]
            if data_bytes.startswith(b"\xfe\xff"):
                data_bytes = data_bytes[2:]
    else:
        # 8-bit Encodings (utf-8, cp1252, iso-8859-1)
        data_bytes = csv_text.encode(enc, errors="strict")
        if bom_default and enc == "utf-8":
            # BOM für reines 'utf-8' optional einschalten
            data_bytes = b"\xef\xbb\xbf" + data_bytes

    # 5) Response mit korrektem Content-Type + Dateiname
    filename = f"tanos_generation_{gen.id}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": f"text/csv; charset={content_charset}",
    }
    return Response(content=data_bytes, headers=headers, media_type=f"text/csv; charset={content_charset}")

# ---------- UI: Projekte ----------

@app.get("/ui/projects", response_class=HTMLResponse)
def ui_projects(request: Request, db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id).all()
    # Hinweis: neue TemplateResponse-Signatur: Request zuerst
    return templates.TemplateResponse(request, "projects.html", {"projects": projects})

@app.post("/ui/projects/create")
def ui_projects_create(name: str = Form(...), db: Session = Depends(get_db)):
    exists = db.query(models.Project).filter(models.Project.name == name).first()
    if exists:
        # Nur die Liste zurückgeben (ohne Fehlerabbruch), damit UI stabil bleibt
        projects = db.query(models.Project).order_by(models.Project.id).all()
        html = ["<table><thead><tr><th>ID</th><th>Name</th><th>Aktion</th></tr></thead><tbody>"]
        for p in projects:
            html.append(f"<tr><td>{p.id}</td><td>{p.name}</td><td><a class='btn' href='/ui/projects/{p.id}/data'>Öffnen</a></td></tr>")
        if not projects:
            html.append("<tr><td colspan='3'><em>Keine Projekte vorhanden.</em></td></tr>")
        html.append("</tbody></table>")
        html.append("<p style='color:#b91c1c;'>Projektname existiert bereits.</p>")
        return HTMLResponse("".join(html))
    p = models.Project(name=name)
    db.add(p); db.commit()
    projects = db.query(models.Project).order_by(models.Project.id).all()
    html = ["<table><thead><tr><th>ID</th><th>Name</th><th>Aktion</th></tr></thead><tbody>"]
    for pr in projects:
        html.append(f"<tr><td>{pr.id}</td><td>{pr.name}</td><td><a class='btn' href='/ui/projects/{pr.id}/data'>Öffnen</a></td></tr>")
    html.append("</tbody></table>")
    return HTMLResponse("".join(html))

@app.post("/ui/projects/rename", response_class=HTMLResponse)
def ui_projects_rename(pid: int = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    p = db.get(models.Project, pid)
    if not p:
        return HTMLResponse("<p style='color:#b91c1c;'>Projekt nicht gefunden.</p>", status_code=404)
    # Namenskonflikt vermeiden
    exists = db.query(models.Project).filter(models.Project.name == name, models.Project.id != pid).first()
    if exists:
        html = _render_projects_table(db) + "<p style='color:#b91c1c;'>Name schon vergeben.</p>"
        return HTMLResponse(html, status_code=409)
    p.name = name
    db.commit()
    return HTMLResponse(_render_projects_table(db))

@app.post("/ui/projects/delete", response_class=HTMLResponse)
def ui_projects_delete(pid: int = Form(...), db: Session = Depends(get_db)):
    p = db.get(models.Project, pid)
    if not p:
        return HTMLResponse("<p style='color:#b91c1c;'>Projekt nicht gefunden.</p>", status_code=404)
    if _project_has_generations(db, pid):
        html = _render_projects_table(db) + "<p style='color:#b91c1c;'>Löschen blockiert: Es existieren Generierungen.</p>"
        return HTMLResponse(html, status_code=400)
    db.delete(p)
    db.commit()
    return HTMLResponse(_render_projects_table(db))

@app.post("/ui/categories/rename", response_class=HTMLResponse)
def ui_categories_rename(
    cid: int = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    cat = db.get(models.Category, cid)
    if not cat:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie nicht gefunden.</p>", status_code=404)
    # Umbenennen ist SAFE (Testfälle referenzieren category_id)
    cat.name = name
    db.commit()
    html = _render_categories_table(db, cat.project_id)
    html += "<p style='color:#16a34a;'>Kategorie umbenannt.</p>"
    return HTMLResponse(html)

@app.post("/ui/categories/delete", response_class=HTMLResponse)
def ui_categories_delete(
    cid: int = Form(...),
    db: Session = Depends(get_db),
):
    cat = db.get(models.Category, cid)
    if not cat:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie nicht gefunden.</p>", status_code=404)

    # pid SOFORT festhalten, bevor wir etwas zurückgeben
    pid = cat.project_id

    # Schutz: Löschen blockieren, wenn Generierungen existieren
    if _project_has_generations(db, pid):
        html = _render_categories_table(db, pid) + "<p style='color:#b91c1c;'>Löschen blockiert: Es existieren Generierungen.</p>"
        return HTMLResponse(html, status_code=400)

    db.delete(cat)
    db.commit()
    return HTMLResponse(_render_categories_table(db, pid))



@app.post("/ui/categories/reorder", response_class=HTMLResponse)
def ui_categories_reorder(
    pid: int = Form(...),
    order: str = Form(...),  # "cid1,cid2,cid3,..."
    db: Session = Depends(get_db),
):
    return HTMLResponse(_render_categories_table(db, pid))

    if _project_has_generations(db, pid):
        return HTMLResponse("<p style='color:#b91c1c;'>Umsortieren blockiert: Es existieren Generierungen.</p>", status_code=400)
    ids = [int(x) for x in order.split(",") if x.strip().isdigit()]
    # setze order_index gemäß übermittelter Reihenfolge
    for idx, cid in enumerate(ids):
        cat = db.get(models.Category, cid)
        if cat and cat.project_id == pid:
            cat.order_index = idx
    db.commit()
    return ui_project_data(pid, Request({"type": "http"}), db)

@app.post("/ui/values/rename", response_class=HTMLResponse)
def ui_values_rename(
    vid: int = Form(...),
    value: str = Form(...),
    risk_weight: int = Form(1),
    #allowed: str = Form("on"),
    allowed: str | None = Form(None),
    vtype: str = Form("string"),
    db: Session = Depends(get_db),
):
    v = db.get(models.Value, vid)
    if not v:
        return HTMLResponse("<p style='color:#b91c1c;'>Wert nicht gefunden.</p>", status_code=404)

    # Validieren/Normalisieren für neuen Wert
    normalized, err = _normalize_value_by_vtype(vtype, value)
    if err:
        html = _render_values_block(db, v.category_id) + f"<p style='color:#b91c1c;'>Fehler: {err}</p>"
        return HTMLResponse(html, status_code=400)

    old_value = v.value  # alter String für TestCaseValues
    v.value = normalized
    v.risk_weight = risk_weight
    v.allowed = _bool_from_form(allowed)
    v.vtype = vtype
    db.flush()

    # Testfälle aktualisieren (alle Vorkommen des alten Strings ersetzen)
    (
        db.query(models.TestCaseValue)
        .filter(
            models.TestCaseValue.category_id == v.category_id,
            models.TestCaseValue.value == old_value,
        )
        .update({models.TestCaseValue.value: normalized}, synchronize_session=False)
    )

    db.commit()
    html = _render_values_block(db, v.category_id) + "<p style='color:#16a34a;'>Wert gespeichert.</p>"
    return HTMLResponse(html)


@app.post("/ui/values/delete", response_class=HTMLResponse)
def ui_values_delete(
    vid: int = Form(...),
    db: Session = Depends(get_db),
):
    v = db.get(models.Value, vid)
    if not v:
        return HTMLResponse("<p style='color:#b91c1c;'>Wert nicht gefunden.</p>", status_code=404)

    cat = db.get(models.Category, v.category_id)
    if not cat:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie nicht gefunden.</p>", status_code=404)

    # Schutz: Löschen blockieren, wenn Generierungen existieren
    if _project_has_generations(db, cat.project_id):
        html = _render_values_block(db, v.category_id) + "<p style='color:#b91c1c;'>Löschen blockiert: Es existieren Generierungen.</p>"
        return HTMLResponse(html, status_code=400)

    cid = v.category_id
    db.delete(v)
    db.commit()
    return HTMLResponse(_render_values_block(db, cid))

@app.post("/ui/projects/delete_force", response_class=HTMLResponse)
def ui_projects_delete_force(pid: int = Form(...), db: Session = Depends(get_db)):
    p = db.get(models.Project, pid)
    if not p:
        return HTMLResponse("<p style='color:#b91c1c;'>Projekt nicht gefunden.</p>", status_code=404)
    _force_delete_project(db, pid)
    db.commit()
    return HTMLResponse(_render_projects_table(db) + "<p style='color:#16a34a;'>Projekt inkl. abhängiger Daten gelöscht.</p>")

@app.post("/ui/categories/delete_force", response_class=HTMLResponse)
def ui_categories_delete_force(cid: int = Form(...), db: Session = Depends(get_db)):
    cat = db.get(models.Category, cid)
    if not cat:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie nicht gefunden.</p>", status_code=404)
    pid = _force_delete_category(db, cid)
    db.commit()
    return HTMLResponse(_render_categories_table(db, pid) + "<p style='color:#16a34a;'>Kategorie inkl. Werte/Testfallwerte gelöscht.</p>")

@app.post("/ui/values/delete_force", response_class=HTMLResponse)
def ui_values_delete_force(vid: int = Form(...), db: Session = Depends(get_db)):
    v = db.get(models.Value, vid)
    if not v:
        return HTMLResponse("<p style='color:#b91c1c;'>Wert nicht gefunden.</p>", status_code=404)
    cid = _force_delete_value(db, vid)
    db.commit()
    return HTMLResponse(_render_values_block(db, cid) + "<p style='color:#16a34a;'>Wert inkl. zugehöriger Testfallwerte gelöscht.</p>")




# ---------- UI: Projekt-Daten (Kategorien & Werte) ----------

from fastapi import Request  # sicherstellen, dass Request importiert ist

@app.get("/ui/projects/{pid}/data", response_class=HTMLResponse)
def ui_project_data(pid: int, request: Request, db: Session = Depends(get_db)):
    project = db.get(models.Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")

    categories = (
        db.query(models.Category)
        .filter(models.Category.project_id == pid)
        .order_by(models.Value.order_index, models.Value.id)
        .all()
    )

    # Werte je Kategorie laden (für Tabellen + Dropdowns)
    values_by_cat = {
        c.id: (
            db.query(models.Value)
            .filter(models.Value.category_id == c.id)
            .order_by(models.Value.id)
            .all()
        )
        for c in categories
    }

    # NEU: Regeln-Block (HTML) vor-rendern
    rules_block_html = _render_rules_block(db, pid)

    return templates.TemplateResponse(
        "project_data.html",
        {
            "request": request,
            "project": project,
            "categories": categories,
            "values_by_cat": values_by_cat,
            "rules_block_html": rules_block_html,
        },
    )

@app.post("/ui/categories/create", response_class=HTMLResponse)
def ui_categories_create(
    pid: int = Form(...),
    name: str = Form(...),
    order_index: int = Form(0),
    db: Session = Depends(get_db)
):
    # Kategorie speichern
    project = db.get(models.Project, pid)
    if not project:
        return HTMLResponse("<p style='color:#b91c1c;'>Projekt nicht gefunden.</p>", status_code=400)
    c = models.Category(project_id=pid, name=name, order_index=order_index)
    db.add(c); db.commit()

    # aktualisierte Kategorien-Tabelle zurückgeben
    categories = (
        db.query(models.Category)
        .filter(models.Category.project_id == pid)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )
    # einfache HTML-Tabelle (gleiches Markup wie im Template)
    parts = ["<table><thead><tr><th>Order</th><th>Kategorie</th><th>Werte</th></tr></thead><tbody>"]
    for cat in categories:
        parts.append(f"""
        <tr>
          <td>{cat.order_index}</td>
          <td><strong>{cat.name}</strong> <span class="subtle">(#{cat.id})</span></td>
          <td>
            <div id="values-of-{cat.id}">
              <form class="row2" method="post" hx-post="/ui/values/create" hx-target="#values-of-{cat.id}" hx-swap="innerHTML">
                <input type="hidden" name="cid" value="{cat.id}" />
                <div>
                  <label>Neuer Wert</label>
                  <input name="value" placeholder="z. B. Rot" required />
                </div>
                <div>
                  <label>Risk</label>
                  <input name="risk_weight" type="number" value="1" min="1" />
                </div>
                <div>
                  <button type="submit">Hinzufügen</button>
                </div>
              </form>
              <table class="mt-3">
                <thead><tr><th>ID</th><th>Wert</th><th>Risk</th></tr></thead>
                <tbody>
        """)
        vals = db.query(models.Value).filter(models.Value.category_id == cat.id).order_by(models.Value.id).all()
        if vals:
            for v in vals:
                parts.append(f"<tr><td>{v.id}</td><td>{v.value}</td><td>{v.risk_weight}</td></tr>")
        else:
            parts.append("<tr><td colspan='3'><em>Keine Werte.</em></td></tr>")
        parts.append("</tbody></table></div></td></tr>")
    if not categories:
        parts.append("<tr><td colspan='3'><em>Noch keine Kategorien.</em></td></tr>")
    parts.append("</tbody></table>")
    return HTMLResponse(_render_categories_table(db, pid))


@app.post("/ui/values/create", response_class=HTMLResponse)
def ui_values_create(
    cid: int = Form(...),
    value: str = Form(...),
    risk_weight: int = Form(1),
    #allowed: str = Form("on"),
    allowed: str | None = Form(None),
    vtype: str = Form("string"),
    db: Session = Depends(get_db)
):
    cat = db.get(models.Category, cid)
    if not cat:
        return HTMLResponse("<p style='color:#b91c1c;'>Kategorie nicht gefunden.</p>", status_code=404)

    # Normalisieren/Validieren nach vtype
    normalized, err = _normalize_value_by_vtype(vtype, value)
    if err:
        html = _render_values_block(db, cid) + f"<p style='color:#b91c1c;'>Fehler: {err}</p>"
        return HTMLResponse(html, status_code=400)

    allowed_bool = _bool_from_form(allowed)
    v = models.Value(category_id=cid, value=normalized, risk_weight=risk_weight, allowed=allowed_bool, vtype=vtype)
    db.add(v); db.commit()
    html = _render_values_block(db, cid) + "<p style='color:#16a34a;'>Wert angelegt.</p>"
    return HTMLResponse(html)

@app.post("/ui/values/reorder", response_class=HTMLResponse)
def ui_values_reorder(
    cid: int = Form(...),
    order: str = Form(...),
    db: Session = Depends(get_db),
):
    if not order.strip():
        return HTMLResponse("<p style='color:#b91c1c;'>Leere Reihenfolge übermittelt.</p>", status_code=400)

    ids = []
    for part in order.split(","):
        part = part.strip()
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                return HTMLResponse("<p style='color:#b91c1c;'>Ungültige ID in Reihenfolge.</p>", status_code=400)

    # Nur Werte dieser Kategorie aktualisieren; Index 0..n
    for idx, vid in enumerate(ids):
        (
            db.query(models.Value)
            .filter(models.Value.id == vid, models.Value.category_id == cid)
            .update({models.Value.order_index: idx}, synchronize_session=False)
        )
    db.commit()

    # Neu rendern
    return HTMLResponse(_render_values_block(db, cid))


def _project_has_generations(db: Session, pid: int) -> bool:
    return db.query(models.Generation).filter(models.Generation.project_id == pid).first() is not None

def _force_delete_project(db: Session, pid: int) -> None:
    # 1) Generationen löschen
    gids = [g.id for g in db.query(models.Generation.id).filter(models.Generation.project_id == pid).all()]
    if gids:
        tids = [t.id for t in db.query(models.TestCase.id).filter(models.TestCase.generation_id.in_(gids)).all()]
        if tids:
            db.query(models.TestCaseValue).filter(models.TestCaseValue.testcase_id.in_(tids)).delete(synchronize_session=False)
            db.query(models.TestCase).filter(models.TestCase.id.in_(tids)).delete(synchronize_session=False)
        db.query(models.Generation).filter(models.Generation.id.in_(gids)).delete(synchronize_session=False)

    # 2) Kategorien & Werte löschen
    cids = [c.id for c in db.query(models.Category.id).filter(models.Category.project_id == pid).all()]
    if cids:
        db.query(models.Value).filter(models.Value.category_id.in_(cids)).delete(synchronize_session=False)
        db.query(models.Category).filter(models.Category.id.in_(cids)).delete(synchronize_session=False)

    # 3) Projekt löschen
    db.query(models.Project).filter(models.Project.id == pid).delete(synchronize_session=False)


def _force_delete_category(db: Session, cid: int) -> int:
    cat = db.get(models.Category, cid)
    if not cat:
        return 0
    pid = cat.project_id
    # zugehörige TestCaseValues + Werte löschen
    db.query(models.TestCaseValue).filter(models.TestCaseValue.category_id == cid).delete(synchronize_session=False)
    db.query(models.Value).filter(models.Value.category_id == cid).delete(synchronize_session=False)
    db.delete(cat)
    return pid


def _force_delete_value(db: Session, vid: int) -> int:
    v = db.get(models.Value, vid)
    if not v:
        return 0
    cid = v.category_id
    # TestCaseValues, die exakt diesen String tragen, löschen
    db.query(models.TestCaseValue).filter(
        models.TestCaseValue.category_id == cid,
        models.TestCaseValue.value == v.value
    ).delete(synchronize_session=False)
    db.delete(v)
    return cid

def _render_rules_block(db: Session, pid: int) -> str:
    id2name = _cat_id_to_name_map(db, pid)
    rules = db.query(models.Rule).filter(models.Rule.project_id == pid).order_by(models.Rule.id).all()

    rows = []
    for r in rules:
        if r.type == "exclude":
            desc = f"Verboten: ({id2name.get(r.if_category_id)} = {r.if_value})  ×  ({id2name.get(r.then_category_id)} = {r.then_value})"
        elif r.type == "dependency":
            desc = f"Abhängig: WENN ({id2name.get(r.if_category_id)} = {r.if_value}) DANN ({id2name.get(r.then_category_id)} = {r.then_value})"
        elif r.type == "combine":
            targets = "—"
            if r.then_values_json:
                try:
                    targets = ", ".join(json.loads(r.then_values_json))
                except Exception:
                    targets = r.then_values_json
            desc = f"Kombinieren: WENN ({id2name.get(r.if_category_id)} = {r.if_value}) DANN {id2name.get(r.then_category_id)} ∈ [{targets}]"
        else:
            desc = f"{r.type}"
        rows.append(
            f"<tr><td>{r.id}</td><td>{desc}</td>"
            f"<td>"
            f"<form method='post' hx-post='/ui/rules/delete' hx-target='#rules-block' hx-swap='innerHTML' style='display:inline' "
            f"onsubmit=\"return confirm('Regel löschen?');\">"
            f"<input type='hidden' name='rid' value='{r.id}' />"
            f"<button type='submit'>Löschen</button>"
            f"</form>"
            f"</td></tr>"
        )

    if not rows:
        rows.append("<tr><td colspan='3'><em>Noch keine Regeln.</em></td></tr>")

    html = [
        "<div id='rules-block'>",
        "<table>",
        "<thead><tr><th>ID</th><th>Beschreibung</th><th>Aktion</th></tr></thead>",
        "<tbody>",
        *rows,
        "</tbody></table>",
        "</div>"
    ]
    return "".join(html)

def _assignment_from_testcase(db: Session, tc_id: int) -> Dict[str, str]:
    """Liest die TestCaseValues eines Testfalls und gibt {KategorieName: Wert} zurück."""
    # Kategorienamen lookup
    rows = (
        db.query(models.TestCaseValue, models.Category.name)
        .join(models.Category, models.Category.id == models.TestCaseValue.category_id)
        .filter(models.TestCaseValue.testcase_id == tc_id)
        .all()
    )
    assignment: Dict[str, str] = {}
    for tcv, cat_name in rows:
        assignment[cat_name] = tcv.value
    return assignment

def _status_for_assignment(pid: int, a: Dict[str, str], db: Session) -> str:
    """
    Liefert 'ok' oder 'combined:<Kategorie>=<Wert>'.
    (Exclude/Dependency wurden bereits in der Generierung gefiltert.)
    """
    rules = _load_rules_structured(db, pid)
    id2name = _cat_id_to_name_map(db, pid)
    # nur Combine sichtbar machen
    for (if_cid, if_val, target_cid, target_values) in rules["combine"]:
        if not target_values:
            continue
        if_name = id2name.get(if_cid)
        target_name = id2name.get(target_cid)
        if not if_name or not target_name:
            continue
        if a.get(if_name) == if_val and a.get(target_name) in target_values:
            return f"combined:{target_name}={a.get(target_name)}"
    return "ok"


#---HELPERLINIE-----


def _cat_id_to_name_map(db: Session, pid: int) -> Dict[int, str]:
    rows = db.query(models.Category.id, models.Category.name).filter(models.Category.project_id == pid).all()
    return {cid: name for cid, name in rows}

def _load_rules_structured(db: Session, pid: int) -> Dict[str, list]:
    """
    Lädt alle Regeln für ein Projekt und liefert:
    {
      "exclude": [(if_cat_id, if_value, then_cat_id, then_value), ...],
      "dependency": [(if_cat_id, if_value, then_cat_id, then_value), ...],
      "combine": [(if_cat_id, if_value, target_cat_id, [values...]), ...],
    }
    """
    rules = db.query(models.Rule).filter(models.Rule.project_id == pid).all()
    out = {"exclude": [], "dependency": [], "combine": []}
    for r in rules:
        t = (r.if_category_id, r.if_value, r.then_category_id, r.then_value)
        if r.type == "exclude":
            out["exclude"].append(t)
        elif r.type == "dependency":
            out["dependency"].append(t)
        elif r.type == "combine":
            values = []
            if r.then_values_json:
                try:
                    values = json.loads(r.then_values_json)
                except Exception:
                    values = []
            out["combine"].append((r.if_category_id, r.if_value, r.then_category_id, values))
    return out

def _apply_business_rules(
    pid: int,
    assignments: list[dict[str, str]],  # [{cat_name: value, ...}, ...]
    db: Session
) -> list[dict[str, str]]:
    """
    Wendet in Reihenfolge an:
    1) COMBINE (fan-out anhand gegebener Zielwerte)
    2) EXCLUDE (Kombinationen verwerfen, die verbotene Paare enthalten)
    3) DEPENDENCY (verwerfen, wenn if erfüllt aber then nicht)
    """
    rules = _load_rules_structured(db, pid)
    id2name = _cat_id_to_name_map(db, pid)

    # 1) COMBINE – Fan-out
    combined: list[dict[str, str]] = []
    for a in assignments:
        clones_added = False
        for (if_cid, if_val, target_cid, target_values) in rules["combine"]:
            if not target_values:
                continue
            if_name = id2name.get(if_cid)
            target_name = id2name.get(target_cid)
            if not if_name or not target_name:
                continue
            if a.get(if_name) == if_val:
                # Für jeden Zielwert eine Kopie, in der die Zielkategorie gesetzt wird
                for tv in target_values:
                    clone = dict(a)
                    clone[target_name] = tv
                    combined.append(clone)
                clones_added = True
        if not clones_added:
            combined.append(a)

    # 2) EXCLUDE – verbotene Paare aussortieren
    def violates_exclude(a: dict[str, str]) -> bool:
        for (l_cid, l_val, r_cid, r_val) in rules["exclude"]:
            l_name = id2name.get(l_cid)
            r_name = id2name.get(r_cid)
            if not l_name or not r_name:
                continue
            if a.get(l_name) == l_val and a.get(r_name) == r_val:
                return True
        return False

    filtered = [a for a in combined if not violates_exclude(a)]

    # 3) DEPENDENCY – wenn if, dann muss then erfüllt sein
    def violates_dependency(a: dict[str, str]) -> bool:
        for (if_cid, if_val, then_cid, then_val) in rules["dependency"]:
            if_name = id2name.get(if_cid)
            then_name = id2name.get(then_cid)
            if not if_name or not then_name:
                continue
            if a.get(if_name) == if_val and a.get(then_name) != then_val:
                return True
        return False

    filtered = [a for a in filtered if not violates_dependency(a)]

    # 4) Deduplikation (falls COMBINE identische Einträge erzeugt)
    seen: set[tuple[tuple[str, str], ...]] = set()
    unique: list[dict[str, str]] = []
    for a in filtered:
        key = tuple(sorted(a.items()))
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def _normalize_value_by_vtype(vtype: str, raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalisiert 'raw' je nach 'vtype' und liefert (normalized, error_message).
    normalized = str oder None, error_message = str oder None.
    """
    if raw is None:
        return None, "Kein Wert übergeben."
    s = str(raw).strip()

    if vtype == "string":
        return s, None

    if vtype == "integer":
        # Nur Ganzzahl
        if re.fullmatch(r"[+-]?\d+", s):
            # führende Nullen entfernen, -0 -> 0
            try:
                return str(int(s)), None
            except Exception:
                return None, "Wert ist kein gültiger Integer."
        return None, "Wert ist kein Integer (z. B. 42, -7)."

    if vtype == "number":
        # Komma als Dezimaltrennzeichen erlauben
        s2 = s.replace(",", ".")
        try:
            f = float(s2)
            # kompaktes Format ohne unnötige Nullen
            return format(f, "g"), None
        except Exception:
            return None, "Wert ist keine Zahl (z. B. 3.14 oder 3,14)."

    if vtype == "boolean":
        mapping = {
            "true": "true", "false": "false",
            "wahr": "true", "falsch": "false",
            "ja": "true", "nein": "false",
            "y": "true", "n": "false",
            "1": "true", "0": "false",
        }
        key = s.lower()
        if key in mapping:
            return mapping[key], None
        return None, "Wert ist kein Boolean (true/false, ja/nein, 1/0)."

    if vtype == "date":
        # Erlaubt: YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY → normalisiert zu YYYY-MM-DD
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d"), None
            except ValueError:
                pass
        return None, "Datum nicht erkennbar (YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY)."

    # Fallback: unbekannter Typ -> nicht blockieren
    return s, None


def _bool_from_form(value: str) -> bool:
    """Checkbox-Wert aus HTML-Form ('on', 'true', '1', ...) in bool wandeln."""
    return str(value).strip().lower() in ("1", "true", "on", "yes", "y")


def _render_categories_table(db: Session, pid: int) -> str:
    categories = (
        db.query(models.Category)
        .filter(models.Category.project_id == pid)
        .order_by(models.Category.order_index, models.Category.id)
        .all()
    )

    parts = ["<table><thead><tr><th>Order</th><th>Kategorie</th><th>Werte</th><th>Aktion</th></tr></thead><tbody id='cat-tbody'>"]
    for cat in categories:
        parts.append(f"""
        <tr data-id="{cat.id}">
          <td class="drag-handle">↕ {cat.order_index}</td>
          <td>
            <form method="post" hx-post="/ui/categories/rename" hx-target="#categories" hx-swap="innerHTML" style="display:inline">
              <input type="hidden" name="cid" value="{cat.id}" />
              <input name="name" value="{cat.name}" />
              <button type="submit">Umbenennen</button>
            </form>
            <span class="subtle"> (#{cat.id})</span>
          </td>
          <td>
            <div id="values-of-{cat.id}">
              { _render_values_block(db, cat.id) }
            </div>
          </td>
          <td>
            <form method="post" hx-post="/ui/categories/delete" hx-target="#categories" hx-swap="innerHTML" style="display:inline"
              onsubmit="return confirm('Kategorie mit allen Werten löschen? (blockiert, wenn Generierungen existieren)');">
              <input type="hidden" name="cid" value="{cat.id}" />
              <button type="submit">Löschen</button>
            </form>
          </td>
        </tr>
        """)
    if not categories:
        parts.append("<tr><td colspan='4'><em>Noch keine Kategorien.</em></td></tr>")
    parts.append("</tbody></table>")
    return "".join(parts)

def _render_values_block(db: Session, cid: int) -> str:
    vals = (
        db.query(models.Value)
        .filter(models.Value.category_id == cid)
        .order_by(models.Value.order_index, models.Value.id)
        .all()
    )
    p = []
    p.append(f"""
      <form class="row2" method="post" hx-post="/ui/values/create" hx-target="#values-of-{cid}" hx-swap="innerHTML">
        <input type="hidden" name="cid" value="{cid}" />
        <div>
          <label>Neuer Wert</label>
          <input name="value" placeholder="z. B. Rot" required />
        </div>
        <div>
          <label>Risk</label>
          <input name="risk_weight" type="number" value="1" min="1" />
        </div>
        <div>
          <label>Erlaubt</label>
          <input name="allowed" type="checkbox" checked />
        </div>
        <div>
          <label>Typ</label>
          <select name="vtype">
            <option value="string">string</option>
            <option value="integer">integer</option>
            <option value="number">number</option>
            <option value="boolean">boolean</option>
            <option value="date">date</option>
          </select>
        </div>
        <div>
          <button type="submit">Hinzufügen</button>
        </div>
      </form>
      <table class="mt-3">
        <thead>
          <tr><th>Order</th><th>ID</th><th>Bearbeiten</th><th>Risk</th><th>Aktion</th></tr>
        </thead>
        <tbody id="val-tbody-{cid}">
    """)
    if vals:
        for v in vals:
            checked = "checked" if getattr(v, "allowed", True) else ""
            vtype = getattr(v, "vtype", "string")
            p.append(f"""
              <tr data-id="{v.id}">
                <td class="drag-handle">↕ {getattr(v, 'order_index', 0)}</td>
                <td>{v.id}</td>
                <td>
                  <form class="inline" method="post" hx-post="/ui/values/rename" hx-target="#values-of-{cid}" hx-swap="innerHTML">
                    <input type="hidden" name="vid" value="{v.id}" />
                    <input name="value" value="{v.value}" />
                    <input name="risk_weight" type="number" value="{v.risk_weight}" min="1" style="width:80px" />

                    <label style="margin-left:8px;">Erlaubt</label>
                    <input name="allowed" type="checkbox" {checked} />

                    <label style="margin-left:8px;">Typ</label>
                    <select name="vtype">
                      <option value="string" {"selected" if vtype=="string" else ""}>string</option>
                      <option value="integer" {"selected" if vtype=="integer" else ""}>integer</option>
                      <option value="number" {"selected" if vtype=="number" else ""}>number</option>
                      <option value="boolean" {"selected" if vtype=="boolean" else ""}>boolean</option>
                      <option value="date" {"selected" if vtype=="date" else ""}>date</option>
                    </select>

                    <button type="submit" style="margin-left:8px;">Speichern</button>
                  </form>
                </td>
                <td>{v.risk_weight}</td>
                <td>
                  <form class="inline" method="post" hx-post="/ui/values/delete" hx-target="#values-of-{cid}" hx-swap="innerHTML"
                    onsubmit="return confirm('Wert löschen? (blockiert, wenn Generierungen existieren)');">
                    <input type="hidden" name="vid" value="{v.id}" />
                    <button type="submit">Löschen</button>
                  </form>
                  <form class="inline" method="post" hx-post="/ui/values/delete_force" hx-target="#values-of-{cid}" hx-swap="innerHTML"
                    onsubmit="return confirm('Wert inkl. Testfallwerte endgültig löschen?');">
                    <input type="hidden" name="vid" value="{v.id}" />
                    <button type="submit" style="margin-left:6px;">Force löschen</button>
                  </form>
                </td>
              </tr>
            """)
    else:
        p.append("<tr><td colspan='5'><em>Keine Werte.</em></td></tr>")
    p.append(f"</tbody></table>")

    # Sortable-Bindung (wird nach jedem htmx-Swap erneut ausgeliefert)
    p.append(f"""
      <script>
        (function() {{
          var tbody = document.getElementById('val-tbody-{cid}');
          if (tbody && !tbody._sortableBound) {{
            tbody._sortableBound = true;
            new Sortable(tbody, {{
              handle: '.drag-handle',
              animation: 150,
              onEnd: function () {{
                var ids = Array.from(tbody.querySelectorAll('tr[data-id]')).map(function(tr) {{ return tr.getAttribute('data-id'); }});
                htmx.ajax('POST', '/ui/values/reorder', {{
                  target: '#values-of-{cid}',
                  swap: 'innerHTML',
                  values: {{ cid: '{cid}', order: ids.join(',') }}
                }});
              }}
            }});
          }}
        }})();
      </script>
    """)
    return "".join(p)


def _render_projects_table(db: Session) -> str:
    projects = db.query(models.Project).order_by(models.Project.id).all()
    html = ["<table><thead><tr><th>ID</th><th>Name</th><th>Aktion</th></tr></thead><tbody>"]
    for p in projects:
        html.append(
            f"<tr>"
            f"<td>{p.id}</td>"
            f"<td>"
            f"<form hx-post='/ui/projects/rename' hx-target='#projects-list' hx-swap='innerHTML' style='display:inline'>"
            f"<input type='hidden' name='pid' value='{p.id}' />"
            f"<input name='name' value='{p.name}' />"
            f"<button type='submit'>Umbenennen</button>"
            f"</form>"
            f"</td>"
            f"<td>"
            f"<form hx-post='/ui/projects/delete' hx-target='#projects-list' hx-swap='innerHTML' style='display:inline' "
            f" onsubmit=\"return confirm('Projekt wirklich löschen? (wird geblockt, wenn Generierungen existieren)');\">"
            f"<input type='hidden' name='pid' value='{p.id}' />"
            f"<button type='submit'>Löschen</button>"
            f"</form> "
            f"<a class='btn' href='/ui/projects/{p.id}/data'>Öffnen</a>"
            f"</td></tr>"
        )
    if not projects:
        html.append("<tr><td colspan='3'><em>Keine Projekte vorhanden.</em></td></tr>")
    html.append("</tbody></table>")
    return "".join(html)


