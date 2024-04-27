from abc import ABC
from datetime import datetime, timedelta
from typing import Dict

from Logika.Meters.Meter import Meter
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef
from Logika.Meters.Types import ArchiveType, BusProtocolType, ImportantTag, MeasureKind


class Logika6(ABC, Meter):
    def __init__(self):
        super().__init__()

    @property
    def family_name(self) -> str:
        return "X6"

    @property
    def tags_sort(self) -> str:
        return "Device, Ordinal, Index"

    @property
    def archive_fields_sort(self) -> str:
        return "Device, ArchiveType, Ordinal"

    @property
    def supported_by_prolog4(self) -> bool:
        return True

    @property
    def outdated(self) -> bool:
        return True

    @property
    def bus_type(self) -> BusProtocolType:
        return BusProtocolType.RSbus

    @staticmethod
    def GetEventPrefixForTV(self) -> str:
        return ""

    @staticmethod
    def get_display_format(self, fi: TagDef):
        if fi.StdVar == StdVar.T:
            return "0.##"
        elif fi.StdVar == StdVar.AVG:
            return "0.###"
        else:
            return None

    def GetCommonTagDefs(self) -> Dict[ImportantTag, str]:
        ct_dict = {
            ImportantTag.NetAddr: "003",  # --отдельного тега для NT нет - поэтому ImportantTag.NetAddr тоже не будет
            ImportantTag.Ident: "008",
            ImportantTag.RHour: "024",
            ImportantTag.RDay: "025",
            ImportantTag.EngUnits: "030н00",
            ImportantTag.Model: "099",
        }
        # TODO: не понятно откуда MeasureKind
        if self.MeasureKind == MeasureKind.T:
            ct_dict[ImportantTag.ParamsCSum] = "054н06"
        return ct_dict

    @staticmethod
    def advanceReadPtr(archiveType: ArchiveType, time: datetime) -> datetime:
        if archiveType == ArchiveType.Hour:
            return time + timedelta(hours=1)
        elif archiveType == ArchiveType.Day:
            return time + timedelta(days=1)
        elif archiveType == ArchiveType.Month:
            return time + timedelta(weeks=4)
        elif archiveType == ArchiveType.ErrorsLog:
            return time + timedelta(days=7)
        elif archiveType in (ArchiveType.ParamsLog, ArchiveType.PowerLog):
            return time + timedelta(weeks=4)
        else:
            raise Exception("Unsupported archive")

    @staticmethod
    def get_nt_from_tag(tag_value: str):
        if not tag_value or len(tag_value) < 7:
            return None

        nt_str = tag_value[5:7]
        try:
            nt = int(nt_str)
            return nt
        except ValueError:
            return None
