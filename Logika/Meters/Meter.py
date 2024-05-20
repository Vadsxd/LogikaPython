import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional
import sqlite3

from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef
from Logika.Meters.ArchiveDef import ArchiveDef
from Logika.Meters.Channel import ChannelKind, ChannelDef
from Logika.Meters.DataTag import DataTag
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import DataTagDef
from Logika.Meters.Types import ImportantTag, TagKind
from Logika.Meters.__4L.SPG741 import TSPG741
from Logika.Meters.__4L.SPT941 import TSPT941
from Logika.Meters.__4L.SPT941_10 import TSPT941_10
from Logika.Meters.__4L.SPT942 import TSPT942
from Logika.Meters.__4L.SPT943 import TSPT943
from Logika.Meters.__4M.LGK410 import TLGK410
from Logika.Meters.__4M.SPG740 import TSPG740
from Logika.Meters.__4M.SPG742 import TSPG742
from Logika.Meters.__4M.SPT940 import TSPT940
from Logika.Meters.__4M.SPT941_20 import TSPT941_20
from Logika.Meters.__4M.SPT943rev3 import TSPT943rev3
from Logika.Meters.__4M.SPT944 import TSPT944
from Logika.Meters.__6.SPE542 import TSPE542
from Logika.Meters.__6.SPG761 import TSPG761
from Logika.Meters.__6.SPG762 import TSPG762
from Logika.Meters.__6.SPG763 import TSPG763
from Logika.Meters.__6.SPT961 import TSPT961
from Logika.Meters.__6.SPT961M import TSPT961M
from Logika.Meters.__6N.SPE543 import TSPE543
from Logika.Meters.__6N.SPG761_1 import TSPG761_1
from Logika.Meters.__6N.SPG761_3 import TSPG761_3
from Logika.Meters.__6N.SPG762_1 import TSPG762_1
from Logika.Meters.__6N.SPG763_1 import TSPG763_1
from Logika.Meters.__6N.SPT961_1 import TSPT961_1
from Logika.Meters.__6N.SPT961_1M import TSPT961_1M
from Logika.Meters.__6N.SPT962 import TSPT962
from Logika.Meters.__6N.SPT963 import TSPT963
from Logika.Utils.Conversions import Conversions


class CommonTagDef:
    def __init__(self, channel, key):
        self.channels = [channel]
        self.keys = [key]


class MeterType(Enum):
    SPT941 = 1
    SPT941_10 = 2
    SPT941_20 = 3
    SPT942 = 4
    SPT943 = 5
    SPT961 = 6
    SPT961M = 7
    SPT961_1 = 8
    SPG741 = 9
    SPG742 = 10
    SPG761 = 11
    SPG762 = 12
    SPG763 = 13
    SPG761_1 = 14
    SPG762_1 = 15
    SPG763_1 = 16
    SPE542 = 17
    SPT961_1M = 18  # модернизированный под новые правила 961.1/2
    SPT943rev3 = 19  # модернизированный под новые правила 943
    SPT944 = 20
    SPT962 = 21
    LGK410 = 22  # расходомер ЛГК410


class TagVault:
    def __init__(self, tags):
        self.ref_tags = tags
        self.tag_key_dict = {}
        for t in tags:
            self.tag_key_dict[(t.ChannelDef.Prefix, Conversions.rus_string_to_stable_alphabet(t.key))] = t

    def find(self, channel_kind, key):
        return self.tag_key_dict.get((channel_kind, Conversions.rus_string_to_stable_alphabet(key)))

    @property
    def all(self):
        return self.ref_tags


class Meter(ABC):
    SPT941 = TSPT941()
    SPG741 = TSPG741()
    SPT942 = TSPT942()
    SPT943 = TSPT943()
    SPT941_10 = TSPT941_10()

    SPG742 = TSPG742()
    SPT941_20 = TSPT941_20()
    SPT943rev3 = TSPT943rev3()
    SPT944 = TSPT944()
    LGK410 = TLGK410()
    SPT940 = TSPT940()
    SPG740 = TSPG740()

    SPT961 = TSPT961()
    SPG761 = TSPG761()
    SPG762 = TSPG762()
    SPG763 = TSPG763()
    SPT961M = TSPT961M()
    SPE542 = TSPE542()

    SPT961_1 = TSPT961_1()
    SPG761_1 = TSPG761_1()
    SPG762_1 = TSPG762_1()
    SPG763_1 = TSPG763_1()
    SPT961_1M = TSPT961_1M()
    SPT962 = TSPT962()
    SPT963 = TSPT963()
    SPE543 = TSPE543()

    SPG761_3 = TSPG761_3()

    meter_dict = {}
    df_temperature: str = "0.00"

    _archives: List[ArchiveDef] = None
    _channels = None
    ref_archive_fields: List[ArchiveFieldDef] = None
    _tagVault: TagVault = None
    _rr = []

    tagsLock = object()
    channelsTable = None
    metadata = sqlite3.connect('Logika_database.db')

    @property
    @abstractmethod
    def measure_kind(self):
        pass

    @property
    @abstractmethod
    def caption(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

    @property
    @abstractmethod
    def max_channels(self):
        pass

    @property
    @abstractmethod
    def max_groups(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, Meter):
            return False
        return type(self) == type(other)

    def __hash__(self):
        return super().__hash__()

    @staticmethod
    def get_defined_meter_types(cls: type):
        if not issubclass(cls, Meter):
            raise Exception("wrong type")
        lm = [getattr(cls, attr) for attr in dir(cls) if isinstance(getattr(cls, attr), Meter)]

        return lm

    @property
    @abstractmethod
    def supported_by_prolog4(self):
        pass

    @property
    def outdated(self) -> bool:
        return False

    @staticmethod
    def from_type_string(meter_type_string: str):
        if meter_type_string is None:
            return None
        return Meter.meter_dict[meter_type_string]

    @staticmethod
    def supported_meters():
        return list(Meter.meter_dict.values())

    @property
    def vendor_id(self) -> str:
        return "ЛОГИКА"

    @property
    def vendor(self) -> str:
        return "ЗАО НПФ ЛОГИКА"

    @property
    @abstractmethod
    def bus_type(self) -> str:
        pass

    @abstractmethod
    def get_common_tag_defs(self) -> Dict[ImportantTag, object]:
        pass

    def __str__(self):
        return self.caption

    @staticmethod
    def initialize_meter_dict():
        with threading.Lock():
            mtrs = Meter.get_defined_meter_types(type(Meter))

            for m in mtrs:
                Meter.meter_dict[m.__class__.__name__] = m

    @abstractmethod
    def get_event_prefix_for_tv(self, TVnum: int):
        pass

    def get_well_known_tags(self) -> Dict[ImportantTag, List[DataTag]]:
        tdefs = self.get_common_tag_defs()
        wtd = {}
        for key, value in tdefs.items():
            dta = self.lookup_common_tags(value)
            wtd[key] = dta

        return wtd

    def lookup_common_tags(self, tlist: object) -> List[DataTag]:
        if isinstance(tlist, str):
            tagAddrs = [tlist]
        elif isinstance(tlist, list):
            tagAddrs = tlist
        else:
            raise Exception("unknown object passed as common tag address")

        dta = []
        for tagAddr in tagAddrs:
            ap = tagAddr.split('.')
            if len(ap) == 1:
                tagName = ap[0]
                chNo = 0
                chType = next(x.Prefix for x in self.channels if x.Start == 0 and x.Count == 1)
            elif len(ap) == 2:
                chType = ''.join(filter(str.isalpha, ap[0]))
                chNo = 0 if len(chType) == len(ap[0]) else int(ap[0][len(chType):])
                tagName = ap[1]
            else:
                raise Exception("incorrect common tag address")

            dd = self.find_tag(chType, tagName)
            if dd is None:
                raise Exception(f"common tag {tagAddr} not found")
            dta.append(DataTag(dd, chNo))

        return dta

    @abstractmethod
    def advance_read_ptr(self, archiveType, time):
        pass

    @abstractmethod
    def get_display_format(self, fi):
        pass

    @property
    def archives(self):
        with self.tagsLock:
            if self._archives is None:
                self.load_metadata()
            return self._archives

    def has_archive(self, at):
        return any(x.ArchiveType == at for x in self.archives)

    @property
    def archive_fields(self):
        with self.tagsLock:
            if self.ref_archive_fields is None:
                self.load_metadata()
            return self.ref_archive_fields

    def find_archive_field_def(self, archiveType, ordinal):
        raise Exception("no ordinal anymore")

    @property
    def channels(self):
        if self._channels is None:
            self.load_metadata()
        return self._channels

    @abstractmethod
    def read_archive_field_def(self, r):
        pass

    @abstractmethod
    def family_name(self) -> str:
        pass

    # @property
    # def res_reader(self):
    #     if self._rr is None:
    #         mrs = Assembly.GetExecutingAssembly().GetManifestResourceStream("Logika.Tags.resources")
    #         self._rr = ResourceReader(mrs)
    #     return self._rr

    @staticmethod
    def read_common_def(r):
        chKey = str(r["Channel"])
        name = str(r["Name"])
        ordinal = int(r["Ordinal"])
        desc = str(r["Description"])

        kind = str(r["Kind"])

        isBasicParam = bool(r["Basic"])
        updRate = int(r["UpdateRate"])

        dataType = None
        sDataType = str(r["DataType"])
        if sDataType:
            dataType = type("System." + sDataType, True)

        stv = StdVar.unknown if r["VarT"] is None else str(r["VarT"])
        descriptionEx = str(r["DescriptionEx"])
        ranging = str(r["Range"])

        return chKey, name, ordinal, kind, isBasicParam, updRate, dataType, stv, desc, descriptionEx, ranging

    @abstractmethod
    def read_tag_def(self, r):
        pass

    @abstractmethod
    def tags_sort(self):
        pass

    @abstractmethod
    def archive_fields_sort(self):
        pass

    def perf_debug_reset(self):
        self._tagVault = None
        self.channelsTable = None
        self._channels = None
        self._archives = None
        self.metadata.Tables.Clear()

    def load_metadata(self):
        devName = self.__class__.__name__[1:]  # TSPTxxx -> SPTxxx

        with Meter.tagsLock:
            # loading channels
            if self.channelsTable is None:
                self.channelsTable = self.load_res_table("Channels")

            if self._channels is None:
                cr = self.channelsTable.Select("Device='" + devName + "'")
                lc = []
                for row in cr:
                    st = int(row["Start"])
                    ct = int(row["Count"])
                    lc.append(ChannelDef(self, str(row["Key"]), st, ct, (row["Description"])))
                self._channels = lc

            # loading tags
            if self._tagVault is None:
                tableName = self.family_name() + "Tags"
                dt = self.metadata.Tables.get(tableName)
                if dt is None:
                    dt = self.load_res_table(tableName)

                lt = []
                for r in dt.Select("Device='" + devName + "'", self.tags_sort):
                    rt = self.read_tag_def(r)
                    lt.append(rt)
                self._tagVault = TagVault(lt)

            # loading archives
            arTableName = self.family_name() + "Archives"
            dta = self.metadata.Tables.get(arTableName)
            if dta is None:
                dta = self.load_res_table(arTableName)

            if self._archives is None:
                aclassName = self.__class__.__name__
                rows = dta.Select("Device='" + devName + "'", "Device, ArchiveType")
                self._archives = self.read_archive_defs(rows)

            # loading archive fields
            afTableName = self.family_name() + "ArchiveFields"
            dtf = self.metadata.Tables.get(afTableName)
            if dtf is None:
                dtf = self.load_res_table(afTableName)

            if self.ref_archive_fields is None:
                aclassName = self.__class__.__name__
                rows = dtf.Select("Device='" + devName + "'", self.archive_fields_sort)
                lf = []
                for r in rows:
                    rf = self.read_archive_field_def(r)
                    lf.append(rf)
                self.ref_archive_fields = lf

    @abstractmethod
    def read_archive_defs(self, rows: List[DataRow]) -> List[ArchiveDef]:
        pass

    @staticmethod
    def load_res_table(tableName: str):
        # TODO: получить получить таблицу
        pass

    @property
    def tags(self) -> TagVault:
        with Meter.tagsLock:
            if self._tagVault is None:
                self.load_metadata()

        return self._tagVault

    @property
    def supports_params_db_checksum(self) -> bool:
        return ImportantTag.ParamsCSum in self.get_common_tag_defs()

    def find_tag(self, chKind: str, key: str) -> DataTagDef:
        return self.tags.find(chKind, key)

    @abstractmethod
    def get_nt_from_tag(self, tagValue: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def get_channel_kind(self, channelStart: int, channelCount: int, channelName: str) -> ChannelKind:
        pass

    def get_basic_params(self) -> List[DataTag]:
        dts = []
        param_tag_defs = [x for x in self.tags.all if x.Kind in [TagKind.Parameter, TagKind.Info] and x.isBasicParam]

        for chDef in self.channels:
            for chNo in range(chDef.Start, chDef.Start + chDef.Count):
                for td in param_tag_defs:
                    if td.ChannelDef == chDef:
                        dts.append(DataTag(td, chNo))

        return dts
