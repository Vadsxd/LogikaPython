from Logika.Meters.Logika6 import Logika6
from Logika.Meters.Types import MeasureKind


class TSPT961M(Logika6):
    def __init__(self):
        self.mdb_R_ords = [91, 72, 75, 79, 83, 87]
        self.mdb_P_ords = [235, 196, 201, 206, 239, 243, 211, 216, 221]
        self.mdb_C_ords = [401, 406]
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.T

    @property
    def caption(self) -> str:
        return "СПТ961М"

    @property
    def description(self) -> str:
        return "тепловычислитель СПТ961М"

    @property
    def max_channels(self) -> int:
        return 6

    @property
    def max_groups(self) -> int:
        return 3
