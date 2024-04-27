from datetime import timedelta

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock
from SPT941_20 import TSPT941_20


class TSPT940(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def IdentWord(self):
        return 0x9228

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self) -> str:
        return "СПТ940"

    @property
    def Description(self) -> str:
        return "тепловычислитель СПТ940"

    @property
    def MaxChannels(self) -> int:
        return 3

    @property
    def MaxGroups(self) -> int:
        return 1

    @staticmethod
    def getNsDescriptions(self):
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
    def GetCommonTagDefs(self):
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
    def BuildEUDict(euTags):
        return TSPT941_20.BuildEUDict(euTags)

    @property
    def SupportsBaudRateChangeRequests(self):
        return True

    @property
    def MaxBaudRate(self):
        return 57600

    @property
    def SessionTimeout(self):
        return timedelta(minutes=1)  # 1 min

    @property
    def SupportsArchivePartitions(self) -> bool:
        return True

    @property
    def SupportsFLZ(self) -> bool:
        return False

    @staticmethod
    def getADSTagBlocks(self):
        return [
            AdsTagBlock(0, 0, 0, 200),  # БД (167 окр. до 200)
            AdsTagBlock(3, ["8224", "1024", "1025"]),  # info T D
            AdsTagBlock(3, 0, 2048, 32)  # тотальные (19 окр. до 32)
        ]
