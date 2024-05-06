class M4ArchiveRecord:
    def __init__(self):
        self.interval_mark = None  # метка интервала (время без РД РЧ)
        self.dt = None  # метка времени записи (полная, с РД/РЧ)
        self.values = []

    def __str__(self):
        dt_str = self.dt.strftime("%d.%m.%y %H:%M:%S.%f")[:-3] if self.dt else ""
        values_str = ", ".join(str(value) if value is not None else "null" for value in self.values)
        if len(self.values) > 1:
            values_str = "{ " + values_str + " }"
        return f"{dt_str} {values_str}"
