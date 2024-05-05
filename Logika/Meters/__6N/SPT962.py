from Logika.Meters.Types import MeasureKind
from Logika6N import Logika6N


class TSPT962(Logika6N):
    def __init__(self):
        self.mdb_R_ords = [91, 86, 72, 75, 79, 83]
        self.mdb_P_ords = [201, 206, 239, 243, 211, 216, 221, 227, 224, 230]
        self.mdb_C_ords = [401, 406, 411, 416, 421, 426, 431, 436, 441]
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.T

    @property
    def caption(self) -> str:
        return "СПТ962"

    @property
    def description(self) -> str:
        return "тепловычислитель СПТ962"
