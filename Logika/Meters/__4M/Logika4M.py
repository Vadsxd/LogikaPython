import array
import struct
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List

from Logika.Meters.ArchiveDef import ArchiveDef4M
from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef4M
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef4M
from Logika.Meters.Types import ArchiveType


class OperParamFlag(Enum):
    No = 0,
    Yes = 1


class AdsTagBlock:
    def __init__(self, Id, *args):
        self.Id = Id
        if len(args) == 3:
            channel, start, count = args
            self.chns = [channel] * count
            self.ords = [start + i for i in range(count)]
        elif len(args) == 1:
            tags = args[0]
            self.chns = []
            self.ords = []
            for tag in tags:
                if tag[1] == '.':
                    self.chns.append(int(tag[0]))
                    self.ords.append(int(tag[2:]))
                else:
                    self.chns.append(0)
                    self.ords.append(int(tag))


class Logika4M(ABC, Logika4):
    ND_STR = "#н/д"

    def __init__(self):
        super().__init__()
        self.t_len = 0

    @property
    def supports_fast_session_init(self) -> bool:
        return True

    @property
    def family_name(self) -> str:
        return "M4"

    @property
    def tags_sort(self) -> str:
        return "device, channel, ordinal"

    @property
    def archive_fields_sort(self) -> str:
        return "device, archive_type, index"

    @abstractmethod
    def get_ads_tag_blocks(self) -> List[AdsTagBlock]:
        pass

    @abstractmethod
    def supports_flz(self) -> bool:
        pass

    @abstractmethod
    def supports_archive_partitions(self) -> bool:
        pass

    @property
    def supported_by_prolog4(self) -> bool:
        return True

    @staticmethod
    def get_tag_length(buf: bytearray, idx: int) -> tuple[int, int]:
        tl = buf[idx]
        if (tl & 0x80) > 0:
            tl &= 0x7F
            if tl == 1:
                t_len = buf[idx + 1]
            elif tl == 2:
                t_len = (buf[idx + 1] << 8) | buf[idx + 2]
            else:
                raise Exception("length field >1 byte")
            return tl + 1, t_len
        else:
            t_len = tl
            return 1, t_len

    @staticmethod
    def parse_tag(buf: bytearray, idx: int):
        tID = buf[idx]
        lenLen, t_len = Logika4M.get_tag_length(buf, idx + 1)
        iSt = idx + 1 + lenLen

        if tID == 0x05:
            v = None
        elif tID == 0x43:
            v = struct.unpack('<f', buf[iSt:iSt + 4])[0]
        elif tID == 0x41:
            if t_len == 1:
                v = struct.unpack('<I', buf[iSt:iSt + 1])[0]
            elif t_len == 2:
                v = struct.unpack('<I', buf[iSt:iSt + 2])[0]
            elif t_len == 4:
                v = struct.unpack('<I', buf[iSt:iSt + 4])[0]
            else:
                raise Exception("Unsupported tag length for 'uint' type")
        elif tID == 0x04:
            v = array.array('B', buf[iSt:iSt + t_len])
        elif tID == 0x16:
            v = buf[iSt:iSt + t_len].decode('cp1251')
        elif tID == 0x44:
            int_val = struct.unpack('<i', buf[iSt:iSt + 4])[0]
            float_val = struct.unpack('<f', buf[iSt + 4:iSt + 8])[0]
            v = float(int_val) + float_val
        elif tID == 0x45:
            if t_len > 0:
                v = OperParamFlag.Yes if buf[iSt] > 0 else OperParamFlag.No
            else:
                v = OperParamFlag.No
        elif tID == 0x46:
            v = buf[iSt] if t_len == 1 else None
        elif tID == 0x47:
            v = "{:02}:{:02}:{:02}".format(buf[iSt + 3], buf[iSt + 2], buf[iSt + 1])
        elif tID == 0x48:
            v = "{:02}-{:02}-{:02}".format(buf[iSt], buf[iSt + 1], buf[iSt + 2])
        elif tID == 0x49:
            tv = [0, 1, 1, 0, 0, 0, 0, 0]
            if t_len > 0:
                for t in range(min(t_len, len(tv))):
                    tv[t] = buf[iSt + t]
                ms = (tv[7] << 8) | tv[6]
                if ms > 999:
                    raise Exception("Incorrect millisecond field in timestamp of archive record: " + str(ms))
                v = datetime(2000 + tv[0], tv[1], tv[2], tv[3], tv[4], tv[5], ms)
            else:
                v = datetime.min
        elif tID == 0x4A:
            v = (buf[iSt], struct.unpack('<H', buf[iSt + 1:iSt + 3])[0])
        elif tID == 0x4B:
            if t_len <= 16:
                v = Logika4.bit_numbers_from_array(buf, iSt, t_len * 8)
            else:
                raise Exception("FLAGS tag length unsupported")
        elif tID == 0x55:  # ERR
            v = buf[iSt]
        else:
            raise Exception("unknown tag type 0x{:X2}".format(tID))

        return 1 + lenLen + t_len, v  # tag code + length field + payload

    def read_tag_def(self, r):
        chKey, name, ordinal, kind, is_basic_param, updRate, dataType, stv, desc, description_ex, ranging = (
            self.readCommonDef(r))

        ch = next((x for x in self.channels if x.Prefix == chKey), None)

        sDbType = r["db_type"] if r["db_type"] is not None else None
        units = str(r["units"])
        displayFormat = str(r["display_format"])

        return TagDef4M(ch, name, stv, kind, is_basic_param, updRate, ordinal, desc, dataType, sDbType, units,
                        displayFormat, description_ex, ranging)

    def read_archive_defs(self, rows):
        d = []
        for r in rows:
            r = dict(r)
            chKey = str(r["channel"])
            ch = next((x for x in self.channels if x.Prefix == chKey), None)
            art = ArchiveType.from_string(str(r["archive_type"]))
            rec_type = type("System." + str(r["record_type"]))
            name = str(r["name"])
            desc = str(r["description"])
            capacity = int(r["capacity"])
            ra = ArchiveDef4M(ch, art, rec_type, capacity, name, desc)
            d.append(ra)

        return d

    def read_archive_field_def(self, r):
        r = dict(r)
        art = ArchiveType.from_string(str(r["archive_type"]))
        ra = next((x for x in self.archives if x.ArchiveType == art), None)

        idx = int(r["index"])
        t = type("System." + str(r["data_type"]))

        s_db_type = str(r["db_type"])
        name = str(r["name"])
        desc = str(r["description"])

        oStdType = r["var_t"]
        stv = StdVar[getattr(StdVar, oStdType) if isinstance(oStdType, str) and oStdType else 'unknown']

        units = str(r["units"])
        display_format = str(r["display_format"])

        return ArchiveFieldDef4M(ra, idx, name, desc, stv, t, s_db_type, display_format, units)
