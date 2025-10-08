def generate(categories: dict) -> list[dict]:
    """
    Dummy-Orthogonal-Generator (vereinfachte Version).
    Nimmt den ersten Wert jeder Kategorie.
    """
    tc = {k: v[0] for k, v in categories.items() if v}
    return [tc]
