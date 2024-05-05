from typing import Dict

from Logika.Meters.Logika6 import Logika6
from Logika.Meters.Types import MeasureKind, ImportantTag


class TSPE542(Logika6):
    def __init__(self):
        self.channels_per_cluster = 16
        self.groups_per_cluster = 4
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.E

    @property
    def caption(self) -> str:
        return "СПЕ542"

    @property
    def description(self) -> str:
        return "сумматор СПЕ542"

    @property
    def max_channels(self) -> int:
        return 128

    @property
    def max_groups(self) -> int:
        return 32

    @property
    def supported_by_prolog4(self) -> bool:
        return True

    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        dt = Logika6.get_common_tag_defs(self)
        dt.pop(ImportantTag.ParamsCSum)
        dt[ImportantTag.EngUnits] = "027н00"
        return dt
