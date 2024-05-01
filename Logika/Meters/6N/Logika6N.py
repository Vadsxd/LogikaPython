from abc import ABC
from typing import Dict

from Logika.Meters.Logika6 import Logika6
from Logika.Meters.Types import ImportantTag


class Logika6N(ABC, Logika6):
    def __init__(self):
        self.dfNS = "00000000"  # формат отображения поля НС
        super().__init__()

    @property
    def outdated(self) -> bool:
        return False

    @property
    def max_channels(self) -> int:
        return 12

    @property
    def max_groups(self) -> int:
        return 6

    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        d = Logika6.get_common_tag_defs(self)
        d[ImportantTag.Model] = "099н00"
        d[ImportantTag.SerialNo] = "099н01"
        return d
