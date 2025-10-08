
class DependencyRule:
    """
    Repräsentiert eine Abhängigkeitsregel:
    Wenn if_category == if_value, dann wird then_category = then_value gesetzt.
    """

    def __init__(self, if_category: str, if_value: str, then_category: str, then_value: str):
        self.if_category = if_category
        self.if_value = if_value
        self.then_category = then_category
        self.then_value = then_value

    def apply(self, testcase: dict) -> dict:
        """
        Wendet die Abhängigkeitsregel auf einen Testfall an.
        Falls die Bedingung erfüllt ist, wird der THEN-Wert gesetzt.
        """
        if testcase.get(self.if_category) == self.if_value:
            testcase[self.then_category] = self.then_value
        return testcase

    def to_dict(self) -> dict:
        """Für Export (z. B. JSON)."""
        return {
            "type": "dependency",
            "if": {self.if_category: self.if_value},
            "then": {self.then_category: self.then_value}
        }

    def __repr__(self):
        return f"<DependencyRule IF {self.if_category}={self.if_value} THEN {self.then_category}={self.then_value}>"
