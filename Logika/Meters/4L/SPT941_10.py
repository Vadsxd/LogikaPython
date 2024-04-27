from datetime import timedelta

from Logika.Meters.Logika4 import CalcFieldDef
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4L import Logika4L, ADSFlashRun
from SPT942 import TSPT942


class TSPT941_10(Logika4L):
    def __init__(self):
        super().__init__()

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self):
        return "СПТ941.10/11"

    @property
    def Description(self):
        return "тепловычислитель СПТ941, мод. 10, 11"

    @property
    def MaxChannels(self):
        return 3

    @property
    def MaxGroups(self):
        return 1

    @property
    def ident_word(self):
        return 0x9229

    def IdentMatch(self, id0, id1, ver):
        return super().IdentMatch(id0, id1, ver) and ver < 0x80

    @staticmethod
    def GetCommonTagDefs():
        return {
            ImportantTag.Model: "ОБЩ.model",
            ImportantTag.EngUnits: "ОБЩ.ЕИ",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
        }

    @staticmethod
    def get_ns_descriptions():
        return [
            "Разряд батареи",
            "Перегрузка по цепям питания датчиков объема",
            "Изменение сигнала на дискретном входе",
            "",
            "Выход контролируемого параметра за границы диапазона",
            "",
            "",
            "",
            "Параметр t1 вне диапазона",
            "Параметр t2 вне диапазона",
            "Расход через ВС1 выше верхнего предела",
            "Ненулевой расход через ВС1 ниже нижнего предела",
            "Расход через ВС2 выше верхнего предела",
            "Ненулевой расход через ВС2 ниже нижнего предела",
            "Расход через ВС3 выше верхнего предела",
            "Ненулевой расход через ВС3 ниже нижнего предела",
            "Отрицательное значение разности часовых масс теплоносителя, выходящее за допустимые пределы",
            "Отрицательное значение часового количества тепловой энергии",
            "Значение разности часовых масс (М1ч–М2ч) меньше нуля",
        ]

    @property
    def SupportsBaudRateChangeRequests(self):
        return True

    @property
    def MaxBaudRate(self):
        return 19200

    @property
    def SessionTimeout(self):
        return timedelta(minutes=2)

    @property
    def SupportsFastSessionInit(self):
        return True

    @staticmethod
    def getModelFromImage(self, flashImage):
        return "1" + chr(flashImage[0x30])

    def BuildEUDict(self, euTags):
        return TSPT942.BuildEUDict(self, euTags)

    @staticmethod
    def getAdsFileLayout(self, everyone, model):
        if everyone:
            return [
                ADSFlashRun(0x00000, 0x1200),
                ADSFlashRun(0x04000, 0x12880),
            ]
        else:
            return [
                ADSFlashRun(0x00000, 0x1200),
                ADSFlashRun(0x04000, 0x27C0),
                ADSFlashRun(0x12140, 0x4740),
            ]

    def GetCalculatedFields(self):
        return [
            CalcFieldDef(
                self.Channels[0],
                0,
                -1,
                "dt",
                StdVar.T,
                "dt",
                float,
                None,
                "0.00",
                "t2",
                "t1-t2",
                "°C"
            )
        ]
