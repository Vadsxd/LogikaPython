from typing import Dict

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M


class TLGK410(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def supported_by_prolog4(self):
        return True

    @property
    def measure_kind(self):
        return MeasureKind.T

    @property
    def caption(self):
        return "ЛГК410"

    @property
    def description(self):
        return "расходомер ЛГК410"

    @property
    def max_channels(self):
        return 1

    @property
    def max_groups(self):
        return 0

    @property
    def max_baud_rate(self):
        return 57600

    @property
    def supports_baud_rate_change_requests(self):
        return False

    @property
    def session_timeout(self):
        return float('inf')

    @staticmethod
    def get_ns_descriptions(self):
        return []

    @property
    def supports_flz(self):
        return False

    @property
    def supports_archive_partitions(self):
        return False

    @property
    def ident_word(self):
        return 0x460A

    @staticmethod
    def build_eu_dict(self, euTags) -> Dict[str, str]:
        return Dict[str, str].__dict__

    @staticmethod
    def get_ads_tag_blocks(self):
        return []

    @staticmethod
    def get_common_tag_defs(self):
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }
