from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict

from Logika.Meters.Channel import ChannelKind
from Logika.Meters.Meter import Meter
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef
from Logika.Meters.Types import ArchiveType, BusProtocolType


class Logika4(ABC, Meter):
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
        super().__init__()

    def get_ns_description(self, ns_number: int) -> str:
        if self.nsDescs is None:
            self.nsDescs = self.get_ns_descriptions()

        if ns_number > len(self.nsDescs) - 1:
            return ""

        return self.nsDescs[ns_number]

    @staticmethod
    def display_ns(value) -> str:
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

    @abstractmethod
    def get_ns_descriptions(self) -> List[str]:
        pass

    def get_display_format(self, fi: TagDef):
        if fi.DisplayFormat:
            return fi.DisplayFormat
        if fi.StdVar == StdVar.G:
            return self.dfFlow
        elif fi.StdVar == StdVar.M:
            return self.dfMass
        elif fi.StdVar == StdVar.P:
            return self.dfPressure
        elif fi.StdVar == StdVar.T:
            return self.dfTemperature
        elif fi.StdVar == StdVar.ti:
            return self.dfTimeInt
        elif fi.StdVar == StdVar.V:
            return self.dfVolume
        elif fi.StdVar == StdVar.W:
            return self.dfEnergy
        else:
            return None

    @property
    def bus_type(self) -> BusProtocolType:
        return BusProtocolType.RSbus

    def get_event_prefix_for_tv(self, TVnum: int) -> str:
        if self.MaxGroups == 1:
            return ""
        else:
            return f"ТВ{TVnum} "

    @staticmethod
    def advance_read_ptr(archiveType: ArchiveType, time: datetime) -> datetime:
        if archiveType == ArchiveType.Hour:
            return time + timedelta(days=1)
        elif archiveType in (ArchiveType.Day, ArchiveType.Control):
            return time + timedelta(weeks=4)
        elif archiveType == ArchiveType.Month:
            return time + timedelta(weeks=52)
        elif archiveType == ArchiveType.is_service_archive:
            return time + timedelta(days=7)
        else:
            raise Exception("Unsupported archive")

    def ident_match(self, id0, id1, ver) -> bool:
        dev_id = (id0 << 8) | id1
        return dev_id == self.ident_word

    @staticmethod
    def meter_type_from_response(id0, id1, ver):
        m4devs = [x for x in Meter.supported_meters() if isinstance(x, Logika4)]
        for dev in m4devs:
            if dev.ident_match(id0, id1, ver):
                return dev

        raise Exception(f"неподдерживаемый прибор {id0:X2} {id1:X2} {ver:X2}")

    @staticmethod
    def get_gas_pressure_units(euParamValue: int) -> str:
        units = {
            0: "кПа",
            1: "МПа",
            2: "кгс/см²",
            3: "кгс/м²"
        }

        return units.get(euParamValue, "кПа")

    @staticmethod
    def bit_numbers(val: int, nBits: int, nOffset: int) -> List[int]:
        bitNumbers = [ib + nOffset for ib in range(nBits) if val & (1 << ib)]

        return bitNumbers

    @staticmethod
    def bit_numbers_from_array(array: bytearray, offset: int, nBits: int) -> List[int]:
        bitNumbers = [i for i in range(nBits) if array[offset + i // 8] & (1 << i % 8)]

        return bitNumbers

    @staticmethod
    def combine_date_time(dateTag: str, timeTag: str) -> datetime:
        dt = [int(x) for x in dateTag.split('.')]
        tt = [int(x) for x in timeTag.split(':')]

        return datetime(2000 + dt[2], dt[1], dt[0], tt[0], tt[1], tt[2])

    @staticmethod
    def get_nt_from_tag(tag_value: str):
        nt = None
        try:
            nt = int(tag_value)
        except:
            pass
        return nt

    @staticmethod
    def checksum8(buf: bytes, start: int, length: int):
        a = 0xFF
        for i in range(length):
            a -= buf[start + i]

        return a

    @staticmethod
    def get_channel_kind(channel_start: int) -> ChannelKind:
        if channel_start == 0:
            return ChannelKind.Common
        else:
            return ChannelKind.TV

    @staticmethod
    def get_eu(eu_dict: Dict[str, str], eu_def: str) -> str:
        if eu_dict is not None and eu_def in eu_dict:
            return eu_dict[eu_def]
        else:
            return eu_def

    @abstractmethod
    def supports_baud_rate_change_requests(self) -> bool:
        pass

    @abstractmethod
    def max_baud_rate(self) -> int:
        pass

    @abstractmethod
    def session_timeout(self):
        pass

    @abstractmethod
    def supports_fast_session_init(self) -> bool:
        pass

    @abstractmethod
    def ident_word(self) -> int:
        pass

    @abstractmethod
    def build_eu_dict(self, eu_tags):
        pass


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
