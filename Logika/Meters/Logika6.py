from abc import ABC
from datetime import datetime, timedelta
from typing import Dict

from Logika.Meters.ArchiveDef import ArchiveDef6, MultipartArchiveDef6
from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef6
from Logika.Meters.Meter import Meter
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef, DataTagDef6, Tag6NodeType
from Logika.Meters.Types import ArchiveType, BusProtocolType, ImportantTag, MeasureKind, TagKind


class Logika6(ABC, Meter):
    def __init__(self):
        self.channel_suffixes = ['т', 'п', 'г', 'к']
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
    def get_event_prefix_for_tv(self) -> str:
        return ""

    @staticmethod
    def get_display_format(self, fi: TagDef):
        if fi.StdVar == StdVar.T:
            return "0.##"
        elif fi.StdVar == StdVar.AVG:
            return "0.###"
        else:
            return None

    def get_common_tag_defs(self) -> Dict[ImportantTag, str]:
        ct_dict = {
            ImportantTag.NetAddr: "003",  # --отдельного тега для NT нет - поэтому ImportantTag.NetAddr тоже не будет
            ImportantTag.Ident: "008",
            ImportantTag.RHour: "024",
            ImportantTag.RDay: "025",
            ImportantTag.EngUnits: "030н00",
            ImportantTag.Model: "099",
        }

        if self.measure_kind == MeasureKind.T:
            ct_dict[ImportantTag.ParamsCSum] = "054н06"
        return ct_dict

    @staticmethod
    def advance_read_ptr(archiveType: ArchiveType, time: datetime) -> datetime:
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

    def get_mdb_map(self, kind):
        fname = "mdb_{0}_ords".format(kind)
        fi = getattr(type(self), fname)

        if fi is None:
            raise Exception(fname + " not found for " + type(self).__name__)

        return fi

    def get_mdb_map_all(self):
        r_ords = self.get_mdb_map('R')
        p_ords = self.get_mdb_map('P')
        c_ords = self.get_mdb_map('C')
        map_list = []
        for i in range(max(self.MaxChannels, self.MaxGroups)):
            if i == 0:
                map_list.extend(r_ords)
            if i < self.MaxChannels:
                map_list.extend(p_ords)
            if i < self.MaxGroups:
                map_list.extend(c_ords)
        return map_list

    def split_var_caption(self, composite_name):
        s_ch = ""
        for z in range(len(composite_name) - 1, 0, -1):
            if composite_name[z].isdigit():
                s_ch = composite_name[z] + s_ch
            elif composite_name[z] in self.channel_suffixes and len(s_ch) > 0:
                channel_type = composite_name[z]
                channel_no = int(s_ch)
                caption = composite_name[:z]
                return caption, channel_type, channel_no
            else:
                break
        channel_type = "0"
        channel_no = 0
        caption = composite_name

        return caption, channel_type, channel_no

    @staticmethod
    def normalize_year(year):
        if year < 95:
            year += 2000
        elif 95 <= year < 100:
            year += 1900
        return year

    def time_string_to_datetime(self, spt_date_time):
        dt = spt_date_time.split("/", 1)
        df = dt[0].split("-", 2)
        tf = dt[1].split(":", 2)

        year = self.normalize_year(int(df[2]))

        return datetime(year, int(df[1]), int(df[0]), int(tf[0]), int(tf[1]), int(tf[2]))

    @staticmethod
    def get_channel_kind(ordinal: int, channel_start: int = None, channel_count: int = None, channel_name: str = None):
        if ordinal is None:
            if channel_start == 0 and channel_count == 1:
                return "Common"
            if channel_name in ["т", "к"]:
                return "Channel"
            elif channel_name in ["п", "г"]:
                return "Group"
            return "Undefined"

        if ordinal < 100:
            return "0"
        elif ordinal < 300:
            return "т"
        else:
            return "п"

    def read_tag_def(self, r):
        self.read_common_def(r, chKey, name, ordinal, kind, isBasicParam, updRate, dataType, stv, desc, descriptionEx,
                             ranging)

        type = Tag6NodeType.__getitem__(r["Type"])

        ch = next((x for x in self.Channels if x.Prefix == chKey), None)

        index = None
        count = int(r["Count"]) if r["Count"] is not None else None

        if type == Tag6NodeType.Tag or type == Tag6NodeType.Array:
            kind = TagKind.__getitem__((r["Kind"]))
            isBasicParam = bool(r["Basic"])
            index = int(r["Index"]) if r["Index"] is not None else None
        else:
            kind = TagKind.Undefined
            isBasicParam = False

        return DataTagDef6(ch, type, name, stv, kind, isBasicParam, updRate, ordinal, desc, dataType, None, index,
                           count, descriptionEx, ranging)

    def read_archive_defs(self, rows):
        ra = []
        ch = next((x for x in self.Channels if x.Prefix == "0"), None)

        for r in rows:
            art = ArchiveType.from_string(str(r["ArchiveType"]))
            sRecType = "System." + str(r["RecordType"])
            recType = type(sRecType)
            name = str(r["Name"])
            desc = str(r["Description"])
            sOrds = str(r["Ordinal"]).split(' ')
            capacity = int(r["Capacity"])

            if len(sOrds) == 1:
                a = ArchiveDef6(ch, art, recType, capacity, name, desc, int(sOrds[0]))
            else:
                ords = [int(s) for s in sOrds]
                a = MultipartArchiveDef6(ch, art, recType, capacity, name, desc, ords)

            ra.append(a)

        return ra

    def read_archive_field_def(self, r):
        chKey = str(r["Channel"])
        ch = next((x for x in self.Channels if x.Prefix == chKey), None)
        art = ArchiveType.from_string(str(r["ArchiveType"]))
        ord = int(r["Ordinal"])

        sDataType = "System." + str(r["DataType"])
        t = type(sDataType)

        sDbType = str(r["DbType"])
        name = str(r["Name"])
        desc = str(r["Description"])

        oStdType = r["VarT"]
        stv = StdVar[getattr(StdVar, oStdType) if isinstance(oStdType, str) and oStdType else 'unknown']

        return ArchiveFieldDef6(ch, art, name, desc, ord, stv, t, sDbType, None)
