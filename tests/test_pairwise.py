from combinatorics import all_combinations, each_choice, orthogonal

def test_orthogonal_pairwise_covers_all_pairs_small():
    cats = {
        "Gewicht": ["500g", "1000g"],
        "Größe": ["Klein", "Mittel", "Groß"],
        "Farbe": ["Rot", "Blau"],
    }
    suite = orthogonal.generate(cats)

    keys = list(cats.keys())
    required_pairs = set()
    for i, k1 in enumerate(keys):
        for j, k2 in enumerate(keys):
            if i >= j:
                continue
            for a in cats[k1]:
                for b in cats[k2]:
                    required_pairs.add((k1, k2, a, b))

    covered = set()
    for tc in suite:
        for i, k1 in enumerate(keys):
            for j, k2 in enumerate(keys):
                if i >= j:
                    continue
                covered.add((k1, k2, tc[k1], tc[k2]))

    assert required_pairs.issubset(covered)
    assert len(suite) < len(all_combinations.generate(cats))

