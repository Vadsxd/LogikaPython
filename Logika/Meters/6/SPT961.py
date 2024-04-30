from Logika.Meters.Logika6 import Logika6
from Logika.Meters.Types import MeasureKind


class TSPT961(Logika6):
    def __init__(self):
        self.mdb_R_ords = [71, 75]
        self.mdb_P_ords = [201, 206, 211, 216, 231, 241, 221]
        self.mdb_C_ords = [401, 406]
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.T

    @property
    def caption(self) -> str:
        return "СПТ961"

    @property
    def description(self) -> str:
        return "тепловычислитель СПТ961"

    @property
    def max_channels(self) -> int:
        return 5

    @property
    def max_groups(self) -> int:
        return 2
