from argparse import ArgumentError
from datetime import timedelta
from typing import List, Dict

from Logika.Meters.ArchiveDef import ArchiveDef4L, ArchiveDef
from Logika.Meters.Channel import ChannelKind, ChannelDef
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import CalcFieldDef
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.Types import MeasureKind, ImportantTag, ArchiveType
from Logika4L import Logika4L, ADSFlashRun


class TSPT942(Logika4L):
    def __init__(self):
        super().__init__()

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self):
        return "СПТ942"

    @property
    def Description(self):
        return "тепловычислитель СПТ942"

    @property
    def ident_word(self):
        return 0x542A

    @property
    def MaxChannels(self):
        return 6

    @property
    def MaxGroups(self):
        return 2

    @staticmethod
    def GetCommonTagDefs(self) -> Dict[ImportantTag, str]:
        return {
            ImportantTag.Model: "ОБЩ.model",
            ImportantTag.EngUnits: "ОБЩ.ЕИ",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
        }

    @staticmethod
    def get_ns_descriptions(self) -> List[str]:
        return [
            "Разряд батареи",
            "Перегрузка по цепям питания датчиков объема и давления",
            "",
            "",
            "",
            "",
            "",
            "",
            "Параметр P1 вне диапазона",
            "Параметр P2 вне диапазона",
            "Параметр t1 вне диапазона",
            "Параметр t2 вне диапазона",
            "Расход через ВС1 выше верхнего предела",
            "Ненулевой расход через ВС1 ниже нижнего предела",
            "Расход через ВС2 выше верхнего предела",
            "Ненулевой расход через ВС2 ниже нижнего предела",
            "Расход через ВС3 выше верхнего предела",
            "Ненулевой расход через ВС3 ниже нижнего предела",
            "Абсолютное значение отрицательной часовой массы М3ч больше, чем 4 % часовой массы М1ч",
            "Отрицательное значение часового количества тепловой энергии",
        ]

    @property
    def SupportsBaudRateChangeRequests(self):
        return True

    @property
    def MaxBaudRate(self):
        return 9600

    @property
    def SessionTimeout(self):
        return timedelta(minutes=30)

    @property
    def SupportsFastSessionInit(self):
        return False

    @staticmethod
    def getModelFromImage(self, flashImage: bytes) -> str:
        return chr(flashImage[0x30])

    @staticmethod
    def BuildEUDict(self, euTags: List[DataTag]) -> Dict[str, str]:
        eus = {}
        if len(euTags) != 1 or euTags[0].Name != "ЕИ" or euTags[0].Value is None:
            raise Exception("incorrect EU tag supplied")

        sEU = str(euTags[0].Value)
        euP, euQ = "", ""
        if sEU == "0":
            euP = "кгс/см²"
            euQ = "Гкал"
        elif sEU == "1":
            euP = "МПа"
            euQ = "ГДж"
        elif sEU == "2":
            euP = "бар"
            euQ = "МВт·ч"

        eus["[P]"] = euP
        eus["[Q]"] = euQ

        return eus

    @staticmethod
    def getAdsFileLayout(self, everyone: bool, model: str) -> List[ADSFlashRun]:
        lfr = []

        bothTVs = False
        if model in ["1", "2", "3", "5"]:
            bothTVs = True
        elif model in ["4", "6"]:
            bothTVs = False
        else:
            raise ArgumentError(None, "неподдерживаемая модель СПТ942: '" + str(model) + "'")

        if everyone:  # AL
            if bothTVs:
                lfr.append(ADSFlashRun(0x00000, 0x2A800))
            else:
                lfr.append(ADSFlashRun(0x00000, 0x19D00))
        else:  # MH
            lfr.append(ADSFlashRun(0x00000, 0x7300))
            lfr.append(ADSFlashRun(0x151C0, 0x4B40))
            if bothTVs:
                lfr.append(ADSFlashRun(0x27840, 0x2FC0))

        return lfr

    def readArchiveDefs(self, rows) -> List[ArchiveDef]:
        la = Logika4L.readArchiveDefs(self, rows)

        ah = next((x for x in la if x.ArchiveType == ArchiveType.Hour), None)
        ad = next((x for x in la if x.ArchiveType == ArchiveType.Day), None)
        am = next((x for x in la if x.ArchiveType == ArchiveType.Month), None)

        m46tv2 = next((x for x in self.Channels if x.Start == 1 and x.Count == 1), None)

        if m46tv2 is None:
            m46tv2 = ChannelDef(self, ah.ChannelDef.Prefix, 2, 1, "канал ТВ2 в одноканальных СПТ942 (мод. 4/6)")
            lc = list(self.Channels)
            lc.append(m46tv2)
            self.Channels = lc

        la.append(
            ArchiveDef4L(m46tv2, ArchiveType.Hour, ah.ElementType, ah.Capacity, ah.Name, ah.Description, ah.RecordSize,
                         -1, None, -1, ah.IndexAddr2.Value, ah.HeadersAddr2, ah.RecordsAddr, True))
        la.append(
            ArchiveDef4L(m46tv2, ArchiveType.Day, ad.ElementType, ad.Capacity, ad.Name, ad.Description, ad.RecordSize,
                         -1, None, -1, ad.IndexAddr2.Value, ad.HeadersAddr2, ad.RecordsAddr, True))
        la.append(
            ArchiveDef4L(m46tv2, ArchiveType.Month, am.ElementType, am.Capacity, am.Name, am.Description, am.RecordSize,
                         -1, None, -1, am.IndexAddr2.Value, am.HeadersAddr2, am.RecordsAddr, True))

        return la

    def GetCalculatedFields(self) -> List[CalcFieldDef]:
        cTV = next((x for x in self.Channels if x.Kind == ChannelKind.TV and x.Start == 1), None)

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
            ),
        ]
