import itertools

def generate(categories: dict) -> list[dict]:
    """All Combinations: Kreuzprodukt aller Werte."""
    if not categories:
        return []
    keys = list(categories.keys())
    values = [categories[k] for k in keys]
    combos = itertools.product(*values)
    return [{k: v for k, v in zip(keys, c)} for c in combos]
