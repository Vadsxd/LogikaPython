from datetime import datetime, timedelta
from typing import List

from Logika.Meters.Meter import Meter
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef
from Logika.Meters.Types import ArchiveType, BusProtocolType
from Logika.Meters.Channel import ChannelKind


class Logika4(Meter):
    dfPressure = "0.000"
    dfMass = "0.000"
    dfVolume = "0.000"
    dfFlow = "0.000"
    dfEnergy = "0.000"
    dfTimeInt = "0.00"
    df0000 = "0.0000"
    dfTemperature = "0.0000"

    nsDescs = None

    def __init__(self):
        pass

    def get_ns_description(self, ns_number: int) -> str:
        if self.nsDescs is None:
            self.nsDescs = self.get_ns_descriptions()

        if ns_number > len(self.nsDescs) - 1:
            return ""
        return self.nsDescs[ns_number]

    @staticmethod
    def display_ns(value):
        separator = ","
        sb = []
        if value is None:
            return ""
        elif isinstance(value, bytes):
            bns = value
            for i in range(len(bns) * 8):
                if (bns[i // 8] & (1 << i % 8)) > 0:
                    sb.append(str(i))
                    sb.append(separator)
            if sb:
                sb.pop()
            else:
                sb.append("-")
        else:
            return "?"

        return "".join(sb)

    def get_ns_description_from_string(self, ns_string: str) -> str:
        evt_desc = None
        if ns_string.endswith("+"):
            si = ns_string.index("С")
            if si > 0:
                ns_string = ns_string[si + 1: -2]
            ns_no = int(ns_string)
            evt_desc = self.get_ns_description(ns_no)
        return evt_desc

    def get_ns_descriptions(self) -> List[str]:
        pass

    def get_display_format(self, fi: TagDef):
        if fi.DisplayFormat:
            return fi.DisplayFormat
        if fi.StdVar == StdVar.G.name:
            return self.dfFlow
        elif fi.StdVar == StdVar.M.name:
            return self.dfMass
        elif fi.StdVar == StdVar.P.name:
            return self.dfPressure
        elif fi.StdVar == StdVar.T.name:
            return self.dfTemperature
        elif fi.StdVar == StdVar.ti.name:
            return self.dfTimeInt
        elif fi.StdVar == StdVar.V.name:
            return self.dfVolume
        elif fi.StdVar == StdVar.W.name:
            return self.dfEnergy
        else:
            return None

    @property
    def BusType(self) -> str:
        return BusProtocolType.RSbus.name

    def GetEventPrefixForTV(self, TVnum: int) -> str:
        if self.MaxGroups == 1:
            return ""
        else:
            return f"ТВ{TVnum} "

    def advanceReadPtr(self, archiveType: ArchiveType, time: datetime) -> datetime:
        if archiveType == ArchiveType.Hour:
            return time + timedelta(days=1)
        elif archiveType in (ArchiveType.Day, ArchiveType.Control):
            return time + timedelta(weeks=4)
        elif archiveType == ArchiveType.Month:
            return time + timedelta(weeks=52)
        elif archiveType == ArchiveType.IsServiceArchive:
            return time + timedelta(days=7)
        else:
            raise Exception("Unsupported archive")

    @staticmethod
    def getGasPressureUnits(euParamValue: int) -> str:
        units = {
            0: "кПа",
            1: "МПа",
            2: "кгс/см²",
            3: "кгс/м²"
        }
        return units.get(euParamValue, "кПа")

    @staticmethod
    def BitNumbers(val: int, nBits: int, nOffset: int) -> List[int]:
        bitNumbers = [ib + nOffset for ib in range(nBits) if val & (1 << ib)]
        return bitNumbers

    @staticmethod
    def BitNumbersFromArray(array: List[int], offset: int, nBits: int) -> List[int]:
        bitNumbers = [i for i in range(nBits) if array[offset + i // 8] & (1 << i % 8)]
        return bitNumbers

    @staticmethod
    def CombineDateTime(dateTag: str, timeTag: str) -> datetime:
        dt = [int(x) for x in dateTag.split('.')]
        tt = [int(x) for x in timeTag.split(':')]
        return datetime(2000 + dt[2], dt[1], dt[0], tt[0], tt[1], tt[2])

    @staticmethod
    def get_nt_from_tag(tag_value):
        nt = None
        try:
            nt = int(tag_value)
        except:
            pass
        return nt

    @staticmethod
    def checksum8(buf, start, length):
        a = 0xFF
        for i in range(length):
            a -= buf[start + i]

        return a

    @staticmethod
    def get_channel_kind(channel_start: int):
        if channel_start == 0:
            return ChannelKind.Common.name
        else:
            return ChannelKind.TV.name

    @staticmethod
    def get_eu(eu_dict, eu_def):
        if eu_dict is not None and eu_def in eu_dict:
            return eu_dict[eu_def]
        else:
            return eu_def

    def build_eu_dict(self, eu_tags):
        raise NotImplementedError


class CalcFieldDef:
    def __init__(self, channel, channel_no, ordinal, name, std_var, desc, data_type, db_type, display_format,
                 insert_after, expression, eu):
        self.channel_no = channel_no
        self.insert_after = insert_after
        self.expression = expression
        self.eu = eu

    @property
    def key(self):
        raise NotImplementedError

    @staticmethod
    def get_calculated_fields():
        return []

