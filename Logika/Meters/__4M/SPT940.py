from datetime import timedelta
from typing import List

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock
from SPT941_20 import TSPT941_20


class TSPT940(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def ident_word(self):
        return 0x9228

    @property
    def measure_kind(self) -> MeasureKind:
        return MeasureKind.T

    @property
    def caption(self) -> str:
        return "СПТ940"

    @property
    def description(self) -> str:
        return "тепловычислитель СПТ940"

    @property
    def max_channels(self) -> int:
        return 3

    @property
    def max_groups(self) -> int:
        return 1

    @staticmethod
    def get_ns_descriptions(self):
        return [
            "Разряд батареи",  # 00
            "Отсутствие напряжения на разъеме X1 тепловычислителя",
            "Разность t между подающим и обратным труб-ми < 3 °C",
            "Значение контролируемого параметра, определяемого КУ1 вне диапазона УН1..УВ1",
            "Значение контролируемого параметра, определяемого КУ2 вне диапазона УН2..УВ2",
            "Значение контролируемого параметра, определяемого КУ3 вне диапазона УН3..УВ3",
            "Значение контролируемого параметра, определяемого КУ4 вне диапазона УН4..УВ4",
            "Значение контролируемого параметра, определяемого КУ5 вне диапазона УН5..УВ5",
            "Параметр P1 вне диапазона 0..1,03*ВП1",
            "Параметр P2 вне диапазона 0..1,03*ВП2",
            "Параметр t1 вне диапазона 0..176 °C",
            "Параметр t2 вне диапазона 0..176 °C",

            # 12
            "Расход через ВС1 выше верхнего предела диапазона измерений (G1>Gв1)",
            "Ненулевой расход через ВС1 ниже нижнего предела диапазона измерений (0<G1<Gн1)",
            "Расход через ВС2 выше верхнего предела диапазона измерений (G2>Gв2)",
            "Ненулевой расход через ВС2 ниже нижнего предела диапазона (0<G2<Gн2)",
            "Расход через ВС3 выше верхнего предела диапазона измерений (G3>Gв3)",
            "Ненулевой расход через ВС3 ниже нижнего предела диапазона (0<G3<Gн3)",

            # 18
            "Диагностика отрицательного значения разности часовых масс теплоносителя (М1ч–М2ч), выходящего за "
            "допустимые пределы",
            "Значение разности часовых масс (М1ч–М2ч) находится в пределах (-НМ)*М1ч <(М1ч–М2ч)<0",
            "Значение разности часовых масс (М1ч–М2ч) находится в пределах 0<(М1ч–М2ч)< НМ*М1ч",
            "Некорректное задание температурного графика",

            # 22
            "Текущее значение температуры по обратному трубопроводу выше чем значение температуры, вычисленное по "
            "заданному температурному графику",
            "Сигнал \"длительное состояние замкнуто\" входа ВС1",
            "Сигнал \"длительное состояние замкнуто\" входа ВС2",
            "Сигнал \"длительное состояние замкнуто\" входа ВС3",
        ]

    @staticmethod
    def get_common_tag_defs(self):
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.EngUnits: ["ОБЩ.ЕИ/P", "ОБЩ.ЕИ/Q"],
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }

    @staticmethod
    def build_eu_dict(euTags):
        return TSPT941_20.build_eu_dict(euTags)

    @property
    def supports_baud_rate_change_requests(self) -> bool:
        return True

    @property
    def max_baud_rate(self) -> int:
        return 57600

    @property
    def session_timeout(self) -> timedelta:
        return timedelta(minutes=1)  # 1 min

    @property
    def supports_archive_partitions(self) -> bool:
        return True

    @property
    def supports_flz(self) -> bool:
        return False

    @staticmethod
    def get_ads_tag_blocks(self) -> List[AdsTagBlock]:
        return [
            AdsTagBlock(0, 0, 0, 200),  # БД (167 окр. до 200)
            AdsTagBlock(3, ["8224", "1024", "1025"]),  # info T D
            AdsTagBlock(3, 0, 2048, 32)  # тотальные (19 окр. до 32)
        ]
