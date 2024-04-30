from datetime import timedelta
from typing import List, Dict

from Logika.Meters.DataTag import DataTag
from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock
from SPT941_20 import TSPT941_20


class TSPT943rev3(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.T

    @property
    def caption(self) -> str:
        return "СПТ943rev3"

    @property
    def description(self) -> str:
        return "тепловычислитель СПТ943 vXX03XX"

    @property
    def max_channels(self) -> int:
        return 6

    @property
    def max_groups(self) -> int:
        return 2

    @property
    def ident_word(self):
        return 0x542B

    def ident_match(self, id0, id1, ver):
        return super().ident_match(id0, id1, ver) and (0x0A <= ver <= 0x1F)

    @staticmethod
    def get_ns_descriptions(self):
        return [
            "Разряд батареи",  # 00
            "Перегрузка по цепям питания преобразователей расхода",
            "Изменение сигнала на дискретном входе",
            "Параметр tхв вне диапазона 0..176°C",
            "Выход контролируемого параметра за границы диапазона УН..УВ",
            "Выход контролируемого параметра за границы диапазона УН2..УВ2",
            "",
            "Отсутствует внешнее питание",  # 7
            "Параметр P1 по вводу вне диапазона 0..1,1*ВП1",  # 08
            "Параметр P2 по вводу вне диапазона 0..1,1*ВП2",
            "Параметр t1 по вводу вне диапазона 0..176°C",
            "Параметр t2 по вводу вне диапазона 0..176°C",
            "Параметр t3 по вводу вне диапазона 0..176°C",  # 12
            "Расход через ВС1 выше верхнего предела измерений",
            "Ненулевой расход через ВС1 ниже нижнего предела измерений",
            "Расход через ВС2 выше верхнего предела измерений",
            "Ненулевой расход через ВС2 ниже нижнего предела измерений",
            "Расход через ВС3 выше верхнего предела измерений",
            "Ненулевой расход через ВС3 ниже нижнего предела измерений",  # 18
            "Отрицательное значение разности часовых масс теплоносителя(М1ч–М2ч), выходит за допустимые пределы",
            "Отрицательное значение часового количества тепловой энергии (Qч<0)",
            "Значение разности часовых масс (М1ч–М2ч) меньше нуля",
            "Значение разности часовых масс (М1ч–М2ч) в пределах допустимого расхождения",
            "Значение разности температур (dt) ниже минимального нормированного значения",  # 23
        ]

    @staticmethod
    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.EngUnits: "ОБЩ.ЕИ",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }

    @staticmethod
    def build_eu_dict(eu_tags: List[DataTag]) -> Dict[str, str]:
        return TSPT941_20.build_eu_dict([eu_tags[0], eu_tags[0]])  # Simulating separate EI/P + EI/Q

    @property
    def supports_baud_rate_change_requests(self) -> bool:
        return True

    @property
    def max_baud_rate(self) -> int:
        return 19200

    @property
    def session_timeout(self) -> timedelta:
        return timedelta(minutes=1)  # 1 minute

    @property
    def supports_archive_partitions(self) -> bool:
        return False

    @property
    def supports_flz(self) -> bool:
        return False

    @staticmethod
    def get_ads_tag_blocks(self) -> List[AdsTagBlock]:
        return [
            AdsTagBlock(0, 0, 0, 64),  # DB ch0
            AdsTagBlock(100, 1, 0, 64),  # DB ch1
            AdsTagBlock(200, 2, 0, 64),  # DB ch2
            AdsTagBlock(3, ["8224", "1024", "1025", "0.2048"]),  # info T D Qobshch
            AdsTagBlock(103, 1, 2048, 16),  # that TV1
            AdsTagBlock(203, 2, 2048, 16),  # that TV2
        ]
