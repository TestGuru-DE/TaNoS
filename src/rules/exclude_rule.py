class ExcludeRule:
    def __init__(self, conditions: dict):
        """
        conditions = {"Kategorie": "Wert", "Kategorie2": "Wert2", ...}
        """
        # self.conditions = conditions <- alt

    def __init__(self, conditions: dict[str, list[str]]):
        self.conditions = conditions # <- neu

    def check(self, testcase: dict) -> bool:
        """
        True = Testfall bleibt erhalten
        False = Testfall wird ausgeschlossen
        """
        for key, allowed_values in self.conditions.items():
            if testcase.get(key) not in allowed_values:
                return True  # Bedingung nicht vollständig erfüllt → Testfall bleibt
        return False  # alle Bedingungen erfüllt → Testfall raus