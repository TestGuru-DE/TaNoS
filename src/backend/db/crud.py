from . import models

def create_category(db, name, parent_id=None):
    cat = models.Category(name=name, parent_id=parent_id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def get_all_categories(db):
    return db.query(models.Category).all()


def create_value(db, category_id, name, schaden=0, nutzung=0, status="allowed"):
    gewichtung = schaden * nutzung
    val = models.Value(
        category_id=category_id,
        name=name,
        schaden=schaden,
        nutzung=nutzung,
        gewichtung=gewichtung,
        status=status
    )
    db.add(val)
    db.commit()
    db.refresh(val)
    return val


def get_values_by_category(db, category_id):
    return db.query(models.Value).filter(models.Value.category_id == category_id).all()

def create_rule(db, name: str, type_: str, definition: dict):
    """Neue Regel speichern."""
    rule = models.Rule(name=name, type=type_, definition=definition)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_all_rules(db):
    """Alle Regeln abrufen."""
    return db.query(models.Rule).all()


