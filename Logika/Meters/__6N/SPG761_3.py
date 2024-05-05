from Logika.Meters.Types import MeasureKind
from Logika6N import Logika6N


class TSPG761_3(Logika6N):
    def __init__(self):
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.G

    @property
    def caption(self) -> str:
        return "СПГ761.3"

    @property
    def description(self) -> str:
        return "корректор СПГ761, мод. 3, 4"

    @property
    def supported_by_prolog4(self) -> bool:
        return True
