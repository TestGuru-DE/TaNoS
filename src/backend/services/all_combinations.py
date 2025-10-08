import itertools

def generate(categories: dict) -> list[dict]:
    """
    Erzeugt alle möglichen Kombinationen.
    categories = {"Gewicht": ["500g", "1000g"], "Größe": ["klein", "mittel"]}
    """
    keys = list(categories.keys())
    values = [categories[k] for k in keys]
    testcases = []
    for combo in itertools.product(*values):
        testcases.append(dict(zip(keys, combo)))
    return testcases
