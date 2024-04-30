from typing import Dict

from Logika.Meters.Logika6 import Logika6
from Logika.Meters.Types import MeasureKind, ImportantTag


class TSPG762(Logika6):
    def __init__(self):
        self.mdb_R_ords = [81]
        self.mdb_P_ords = [251, 201, 206, 211, 221, 231]
        self.mdb_C_ords = [411, 421]
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.G

    @property
    def caption(self) -> str:
        return "СПГ762"

    @property
    def description(self) -> str:
        return "корректор СПГ762"

    @property
    def max_channels(self) -> int:
        return 3

    @property
    def max_groups(self) -> int:
        return 1

    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        dt = Logika6.get_common_tag_defs(self)
        dt[ImportantTag.EngUnits] = "030"
        return dt
