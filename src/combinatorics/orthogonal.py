from itertools import product
from typing import Dict, List, Tuple, Set

def _all_pairs(categories: Dict[str, List[str]]) -> Set[Tuple[str, str, str]]:
    keys = list(categories.keys())
    universe: Set[Tuple[str, str, str]] = set()
    for i, k1 in enumerate(keys):
        for j, k2 in enumerate(keys):
            if i >= j:
                continue
            for a in categories[k1]:
                for b in categories[k2]:
                    universe.add((k1, k2, a, b))
    return universe

def _pairs_covered_by_assignment(assignment: Dict[str, str]) -> Set[Tuple[str, str, str]]:
    keys = list(assignment.keys())
    covered=set()
    for i, k1 in enumerate(keys):
        for j, k2 in enumerate(keys):
            if i >= j:
                continue
            covered.add((k1, k2, assignment[k1], assignment[k2]))
    return covered

def generate(categories: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """
    Pairwise/Orthogonal-ähnliche Erzeugung über eine einfache Greedy-Heuristik.
    Deckt alle 2er-Kombinationen zwischen Kategorien ab.
    """
    if not categories or any(len(v)==0 for v in categories.values()):
        return []
    keys = list(categories.keys())
    if len(keys) == 1:
        return [{keys[0]: v} for v in categories[keys[0]]]

    universe = _all_pairs(categories)
    suite: List[Dict[str, str]] = []

    seed = {k: categories[k][0] for k in keys}
    suite.append(seed)
    covered = _pairs_covered_by_assignment(seed)

    all_assignments = list(product(*[categories[k] for k in keys]))
    assignment_dicts: List[Dict[str, str]] = [{k: v for k, v in zip(keys, assg)} for assg in all_assignments]
    assignment_dicts = [a for a in assignment_dicts if a != seed]

    while covered != universe and assignment_dicts:
        best = None
        best_gain = -1
        for a in assignment_dicts:
            gain = len(_pairs_covered_by_assignment(a) - covered)
            if gain > best_gain:
                best_gain = gain
                best = a
        if best is None or best_gain == 0:
            break
        suite.append(best)
        covered |= _pairs_covered_by_assignment(best)
        assignment_dicts.remove(best)

    if covered != universe:
        for a in assignment_dicts:
            if covered == universe:
                break
            new_pairs = _pairs_covered_by_assignment(a) - covered
            if new_pairs:
                suite.append(a)
                covered |= new_pairs
    return suite
