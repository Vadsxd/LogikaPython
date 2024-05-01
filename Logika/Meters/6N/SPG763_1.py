from Logika.Meters.Types import MeasureKind
from Logika6N import Logika6N


class TSPG763_1(Logika6N):
    def __init__(self):
        self.mdb_R_ords = [91, 86, 79, 83]
        self.mdb_P_ords = [235, 196, 201, 206, 239, 243, 211, 216, 221, 246]
        self.mdb_C_ords = [401, 406, 411]
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.G

    @property
    def caption(self) -> str:
        return "СПГ763.1"

    @property
    def description(self) -> str:
        return "корректор СПГ763, мод. 1, 2"
