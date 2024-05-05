from typing import Dict

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika6N import Logika6N


class TSPE543(Logika6N):
    def __init__(self):
        super.__init__(self)

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.E

    @property
    def caption(self) -> str:
        return "СПЕ543"

    @property
    def description(self) -> str:
        return "сумматор СПЕ543"

    @property
    def max_channels(self) -> int:
        return 128

    @property
    def max_groups(self) -> int:
        return 32

    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        dt = Logika6N.get_common_tag_defs(self)
        dt.pop(ImportantTag.EngUnits)  # no configurable EUs
        dt.pop(ImportantTag.ParamsCSum)
        return dt
