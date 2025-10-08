def generate(categories: dict) -> list[dict]:
    """
    Erzeugt Each-Choice-Kombinationen:
    Nimmt pro Kategorie mindestens einen Wert.
    """
    keys = list(categories.keys())
    max_len = max(len(categories[k]) for k in keys)
    testcases = []
    for i in range(max_len):
        tc = {}
        for key in keys:
            values = categories[key]
            tc[key] = values[i % len(values)]
        testcases.append(tc)
    return testcases
