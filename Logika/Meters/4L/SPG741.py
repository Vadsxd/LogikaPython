from datetime import timedelta
from enum import Enum

from Logika.Meters.Types import MeasureKind
from Logika4L import Logika4L
from Logika.Meters.Logika4 import Logika4


class ImportantTag(Enum):
    EngUnits = 1
    NetAddr = 2
    Ident = 3
    RDay = 4
    RHour = 5


class TSPG741(Logika4L):
    def __init__(self):
        self.sensors = ["ПД1", "ПД2", "ПД3", "ПД4", "ПД5", "ТС1", "ТС2", "СГ1", "СГ2"]

        self.spParamMap = [
            ["P1", "dP3", "dP1", "Pб", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=0
            ["P1", "dP3", "P2", "Pб", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=1
            ["P1", "dP3", "P2", "dP1", "dP2", "t1", "t2", "Qр1", "Qр2"],  # СП=2
            ["P1", "dP2", "P2", "Pб", "dP1", "t1", "t2", "Qр1", "Qр2"],  # СП=3
            ["P1", "dP2", "P2", "dP1", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=4
            ["P1", "dP3", "dP1", "Pб", "P3", "t1", "t3", "Qр1", ""],  # СП=5
            ["P1", "dP3", "dP1", "P3", "P4", "t1", "t3", "Qр1", ""],  # СП=6
        ]

        self.sensorVars = ["ВД", "ТД", "ВП", "НП", "ЦИ", "КС", "КВ", "КН", "УВ", "УН", "Vн"]

    @property
    def IdentWord(self):
        return 0x4729

    @property
    def MeasureKind(self) -> str:
        return MeasureKind.G.name

    @property
    def Caption(self):
        return "СПГ741"

    @property
    def Description(self):
        return "корректор СПГ741"

    @property
    def MaxChannels(self):
        return 2

    @property
    def MaxGroups(self):
        return 1

    def GetCommonTagDefs(self):
        return {
            ImportantTag.EngUnits: ["ОБЩ.[P1]", "ОБЩ.[dP1]", "ОБЩ.[P2]", "ОБЩ.[dP2]", "ОБЩ.[dP3]", "ОБЩ.[Pб]",
                                    "ОБЩ.[P3]", "ОБЩ.[P4]"],
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР"
        }

    def getNsDescriptions(self):
        return [
            "Разряд батареи",  # 00
            "",
            "Перегрузка по цепям питания датчиков объема",  # 02
            "Активен входной сигнал ВС",  # 03
            "Рабочий расход Qр1 ниже нижнего предела",
            "Рабочий расход Qр2 ниже нижнего предела",
            "Рабочий расход Qр1 выше верхнего предела",
            "Рабочий расход Qр2 выше верхнего предела",  # 07
            "",
            "Входной сигнал по цепи Х12 вне диапазона",  # 09
            "Входной сигнал по цепи Х13 вне диапазона",
            "Входной сигнал по цепи Х14 вне диапазона",
            "Входной сигнал по цепи Х15 вне диапазона",
            "Входной сигнал по цепи Х16 вне диапазона",  # 13
            "Температура t1 вне диапазона",
            "Температура t2 вне диапазона",
            "Давление Р1 за пределами уставок",  # 16
            "Перепад давления dР1 за пределами уставок",
            "Рабочий расход Qр1 за пределами уставок",
            "Давление Р2 за пределами уставок",
            "Перепад давления dР2 за пределами уставок",
            "Рабочий расход Qр2 за пределами уставок",
            "Перепад давления dР3 за пределами уставок",
            "Давление Р3 за пределами уставок",
            "Давление Р4 за пределами уставок",
            "Объем выше нормы поставки",  # 25
            "Некорректные вычисления по первому трубопроводу",
            "Некорректные вычисления по второму трубопроводу"
        ]

    @property
    def SupportsBaudRateChangeRequests(self):
        return False

    @property
    def MaxBaudRate(self):
        return 2400

    @property
    def SessionTimeout(self):
        return timedelta(minutes=30)

    @property
    def SupportsFastSessionInit(self):
        return False

    def GetMappedDBParamAddr(self, paramName, sp):
        DB_FLASH_START = 0x200
        PARAM_SIZE = 16

        paramOrd = self.GetMappedDBParamOrdinal(paramName, sp)
        if paramOrd is None:
            paramOrd = 103
        addr = DB_FLASH_START + paramOrd * PARAM_SIZE

        return addr

    def GetMappedDBParamOrdinal(self, paramName, sp):
        pn = paramName.split('/')
        if len(pn) != 2:
            raise Exception("недопустимое имя параметра СПГ741: {}".format(paramName))
        sp_map = self.spParamMap[sp]
        sensIdx = sp_map.index(pn[1])
        if sensIdx < 0:
            return None
        varIdx = self.GetMappedDBParamOrdinalsensorVars.index(pn[0])
        if varIdx < 0:
            return None
        MAPPED_PARAMS_START_NO = 100
        PARAMS_PER_SENSOR = 11
        return MAPPED_PARAMS_START_NO + sensIdx * PARAMS_PER_SENSOR + varIdx

    @staticmethod
    def BuildEUDict(euTags):
        eus = {}
        if len(euTags) != 8:
            raise Exception("incorrect EU tags supplied")

        for t in euTags:
            iEU = int(t.Value) & 0x03 if isinstance(t.Value, int) else ""
            eus[t.Name] = Logika4.getGasPressureUnits(iEU)

        return eus

    @staticmethod
    def getAdsFileLayout(everyone):
        if everyone:
            return [{"Start": 0x00000, "Length": 0x17C80}]
        else:
            return [
                {"Start": 0x00000, "Length": 0x4840},
                {"Start": 0x13440, "Length": 0x4840}
            ]

    @staticmethod
    def getModelFromImage():
        return ""
