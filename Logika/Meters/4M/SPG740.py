from datetime import timedelta

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock
from SPG742 import TSPG742


class TSPG740(Logika4M):
    def __init__(self):
        super.__init__(self)

    @property
    def IdentWord(self):
        return 0x4728

    @property
    def MeasureKind(self):
        return MeasureKind.G

    @property
    def Caption(self) -> str:
        return "СПГ740"

    @property
    def Description(self) -> str:
        return "корректор СПГ740"

    @property
    def MaxChannels(self) -> int:
        return 3

    @property
    def MaxGroups(self) -> int:
        return 1

    @staticmethod
    def getNsDescriptions(self):
        return [
            "Разряд батареи (Uб < 3,2 В)",  # 00
            "Изменение сигнала на дискретном входе",
            "Ненулевой рабочий расход Qр1 ниже Qотс1",
            "Ненулевой рабочий расход Qр2 ниже Qотс2",
            "Рабочий расход Qр1 ниже нижнего предела, но выше Qотс1",
            "Рабочий расход Qр2 ниже нижнего предела, но выше Qотс2",
            "Рабочий расход Qр1 выше верхнего предела",
            "Рабочий расход Qр2 выше верхнего предела",
            "Измеренное значение давления датчика P1 вышло за пределы измерений датчика",
            "Измеренное значение давления датчика P2 вышло за пределы измерений датчика",
            "Измеренное значение перепада давления ΔP1 вне пределов диапазона измерений датчика",
            "Сигнал д̈лительное состояние замкнутов̈хода V1",
            "Сигнал д̈лительное состояние замкнутов̈хода V2",
            "",
            "",
            "Измеренное значение бар. давления Pб вне пределов диапазона измерений датчика",  # 15
            "Измеренное значение температуры t1 вне пределов диапазона -52..107 °С",
            "Измеренное значение температуры t2 вне пределов диапазона -52..107 °С",
            "Значение контролируемого параметра, определяемого КУ1 вне диапазона УН1..УВ1",
            "Значение контролируемого параметра, определяемого КУ2 вне диапазона УН2..УВ2",
            "",  # 20
            "Частота входного сигнала на входе V1 превышает 150 Гц",
            "Частота входного сигнала на входе V2 превышает 150 Гц",
            "Отсутствие напряжения на разъеме X1 корректора",
            "",
            "Объем выше нормы поставки",  # 25
            "Некорректные вычисления по первому трубопроводу",
            "Некорректные вычисления по второму трубопроводу",  # 27
        ]

    @staticmethod
    def GetCommonTagDefs(self):
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.EngUnits: ["ОБЩ.[Pб]", "ОБЩ.[P1]", "ОБЩ.[dP1]", "ОБЩ.[P2]"],
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }

    @staticmethod
    def BuildEUDict(euTags):
        return TSPG742.BuildEUDict(euTags)

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
            AdsTagBlock(0, 0, 0, 55),  # БД ОБЩ
            AdsTagBlock(1, 1, 0, 25),  # БД канал 1
            AdsTagBlock(2, 2, 0, 25),  # БД канал 2
            AdsTagBlock(3, [
                "8224", "1024", "1025",  # info T D
                "0.2048", "0.2049", "0.2050",  # тотальные ОБЩ
                "1.2048", "1.2049",  # тотальные ch1
                "2.2048", "2.2049",  # тотальные ch2
            ]),
        ]
