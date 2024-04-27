from datetime import timedelta
from typing import List, Dict

from Logika.Meters.Channel import ChannelKind
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import CalcFieldDef
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4L import Logika4L, ADSFlashRun
from SPT942 import TSPT942


class TSPT943(Logika4L):
    def __init__(self):
        super().__init__()

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self):
        return "СПТ943"

    @property
    def Description(self):
        return "тепловычислитель СПТ943"

    @property
    def MaxChannels(self):
        return 6

    @property
    def MaxGroups(self):
        return 2

    @property
    def ident_word(self):
        return 0x542B

    def IdentMatch(self, id0, id1, ver):
        return super().IdentMatch(id0, id1, ver) and ver < 0x0A

    @staticmethod
    def GetCommonTagDefs(self) -> Dict[ImportantTag, str]:
        return {
            ImportantTag.Model: "ОБЩ.model",
            ImportantTag.EngUnits: "ОБЩ.ЕИ",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР"
        }

    @staticmethod
    def get_ns_descriptions(self) -> List[str]:
        return [
            "Разряд батареи",
            "Перегрузка по цепям питания датчиков объема"
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
    def getModelFromImage(self, flashImage: bytes) -> str:
        return chr(flashImage[0x30])

    def BuildEUDict(self, euTags: List[DataTag]) -> Dict[str, str]:
        return TSPT942.BuildEUDict(self, euTags)

    @staticmethod
    def getAdsFileLayout(self, everyone, model):
        if everyone:
            return [
                ADSFlashRun(0x00000, 0x3A980)
            ]
        else:
            return [
                ADSFlashRun(0x00000, 0x8CC0),
                ADSFlashRun(0x1AEC0, 0x6E00),
                ADSFlashRun(0x33B80, 0x6E00),
            ]

    def GetCalculatedFields(self) -> List[CalcFieldDef]:
        cTV = next(x for x in self.Channels if x.Kind == ChannelKind.TV)
        return [
            CalcFieldDef(
                cTV,
                1,
                -1,
                "dt",
                StdVar.T,
                "dt ТВ1",
                float,
                None,
                "0.00",
                "ТВ1_t2",
                "ТВ1_t1-ТВ1_t2",
                "°C"
            ),
            CalcFieldDef(
                cTV,
                2,
                -1,
                "dt",
                StdVar.T,
                "dt ТВ2",
                float,
                None,
                "0.00",
                "ТВ2_t2",
                "ТВ2_t1-ТВ2_t2",
                "°C"
            )
        ]
