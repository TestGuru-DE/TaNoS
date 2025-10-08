def generate(categories: dict) -> list[dict]:
    """Each Choice nach ISTQB v4: jeder Wert jeder Kategorie mindestens einmal."""
    if not categories:
        return []
    keys = list(categories.keys())
    max_len = max(len(v) for v in categories.values())
    testcases = []
    for i in range(max_len):
        tc = {}
        for k in keys:
            vals = categories[k]
            tc[k] = vals[i % len(vals)]
        testcases.append(tc)
    return testcases
