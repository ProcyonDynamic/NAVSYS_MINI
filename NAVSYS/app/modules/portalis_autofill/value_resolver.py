class ValueResolver:
    def __init__(self, portalis_data):
        self.data = portalis_data

    def resolve(self, target_path):
        parts = target_path.split(".")

        current = self.data

        try:
            for p in parts:
                current = current[p]
            return current
        except Exception:
            return None