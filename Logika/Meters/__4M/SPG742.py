from datetime import timedelta
from typing import List, Dict

from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock


class TSPG742(Logika4M):
    def __init__(self):
        super.__init__(self)

    @property
    def ident_word(self):
        return 0x472A

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.G

    @property
    def caption(self) -> str:
        return "СПГ742"

    @property
    def description(self) -> str:
        return "корректор СПГ742"

    @property
    def max_channels(self) -> int:
        return 4

    @property
    def max_groups(self) -> int:
        return 1

    @staticmethod
    def get_common_tag_defs(self) -> Dict[ImportantTag, object]:
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.EngUnits: ["ОБЩ.[P1]", "ОБЩ.[dP1]", "ОБЩ.[P2]", "ОБЩ.[dP2]", "ОБЩ.[P3]", "ОБЩ.[dP3]",
                                    "ОБЩ.[dP4]", "ОБЩ.[Pб]"],
        }

    @staticmethod
    def build_eu_dict(euTags: List[DataTag]) -> Dict[str, str]:
        eus = {}
        for t in euTags:
            iEU = int(t.Value)
            eus[t.Name] = Logika4.get_gas_pressure_units(iEU)
        return eus

    @staticmethod
    def get_ns_descriptions() -> List[str]:
        return [
            "Разряд батареи",
            "Частота входного сигнала на разъеме Х7 превышает 1,5 кГц",
            "Частота входного сигнала на разъеме Х8 превышает 1,5 кГц",
            "Изменение сигнала на дискретном входе",
            "Рабочий расход Qр1 ниже нижнего предела",
            "Рабочий расход Qр2 ниже нижнего предела",
            "Рабочий расход Qр1 выше верхнего предела",
            "Рабочий расход Qр2 выше верхнего предела",
            "Давление P1 вне диапазона",
            "Давление P2 вне диапазона",
            "Перепад давления dР1 вне диапазона",
            "Перепад давления dР2 вне диапазона",
            "Давление P3 вне диапазона",
            "Перепад давления dР3 вне диапазона",
            "Перепад давления dР4 вне диапазона",
            "Давление Pб вне диапазона",
            "Температура t1 вне диапазона",
            "Температура t2 вне диапазона",
            "Значение параметра по КУ1 вне диапазона",
            "Значение параметра по КУ2 вне диапазона",
            "Значение параметра по КУ3 вне диапазона",
            "Значение параметра по КУ4 вне диапазона",
            "Значение параметра по КУ5 вне диапазона",
            "",
            "Объем выше нормы поставки",
            "Некорректные вычисления по первому трубопроводу",
            "Некорректные вычисления по второму трубопроводу",
            "Измеренное значение перепада давления dP1 превышает вычисленное предельное значение, при этом Qр1>НП/Qр1",
            "Измеренное значение перепада давления dP2 превышает вычисленное предельное значение, при этом Qр2>НП/Qр2"
        ]

    @property
    def supports_baud_rate_change_requests(self) -> bool:
        return True

    @property
    def max_baud_rate(self) -> int:
        return 57600

    @property
    def session_timeout(self) -> timedelta:
        return timedelta(minutes=1)

    @property
    def supports_fast_session_init(self) -> bool:
        return True

    @property
    def supports_archive_partitions(self) -> bool:
        return True

    @property
    def supports_flz(self) -> bool:
        return False

    @staticmethod
    def get_ads_tag_blocks() -> List[AdsTagBlock]:
        return [
            AdsTagBlock(0, 0, 0, 64),  # БД ch0
            AdsTagBlock(1, 1, 0, 64),  # БД ch1
            AdsTagBlock(2, 2, 0, 64),  # БД ch2
            AdsTagBlock(3, [
                "8224", "1024", "1025",  # info T D
                "1032", "1033", "1034",  # vch vpch tich
                "0.2048", "0.2049", "0.2050",  # v vp ti
                "1.1029", "1.1030", "1.2048", "1.2049",  # vr1ch v1ch vr1 v1
                "2.1029", "2.1030", "2.2048", "2.2049"  # vr2ch v2ch vr2 v2
            ])
        ]
