class SPBusArchiveRecord:
    def __init__(self, time, value, eu):
        self.time = time
        self.value = value
        self.eu = eu

    def __str__(self):
        sEU = f"({self.eu})" if self.eu else ""
        return f"{self.time}: {self.value} {sEU}"
