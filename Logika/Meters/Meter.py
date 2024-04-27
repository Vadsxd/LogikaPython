import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional

from Logika.Meters.ArchiveDef import ArchiveDef
from Logika.Meters.Channel import ChannelKind, ChannelDef
from Logika.Meters.DataTag import DataTag
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import DataTagDef
from Logika.Meters.Types import ImportantTag, TagKind
from Logika.Utils.Conversions import Conversions


class CommonTagDef:
    def __init__(self, channel, key):
        self.channels = [channel]
        self.keys = [key]


class Devices:
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
        self.refTags = tags
        self.tagKeyDict = {}
        for t in tags:
            self.tagKeyDict[(t.ChannelDef.Prefix, Conversions.rus_string_to_stable_alphabet(t.Key))] = t

    def Find(self, channelKind, key):
        return self.tagKeyDict.get((channelKind, Conversions.rus_string_to_stable_alphabet(key)))

    @property
    def All(self):
        return self.refTags


class Meter(ABC):
    meterDict = {}
    dfTemperature = "0.00"

    _archives = None
    _channels = None
    refArchiveFields = None
    _tagVault = None
    _rr = []

    tagsLock = object()
    channelsTable = None
    metadata = DataSet("metadata")

    @property
    @abstractmethod
    def MeasureKind(self):
        pass

    @property
    @abstractmethod
    def Caption(self):
        pass

    @property
    @abstractmethod
    def Description(self):
        pass

    @property
    @abstractmethod
    def MaxChannels(self):
        pass

    @property
    @abstractmethod
    def MaxGroups(self):
        pass

    def __eq__(self, other):
        if not isinstance(other, Meter):
            return False
        return type(self) == type(other)

    def __hash__(self):
        return super().__hash__()

    @staticmethod
    def getDefinedMeterTypes(cls):
        if not issubclass(cls, Meter):
            raise Exception("wrong type")
        lm = [getattr(cls, attr) for attr in dir(cls) if isinstance(getattr(cls, attr), Meter)]

        return lm

    @property
    @abstractmethod
    def SupportedByProlog4(self):
        pass

    @property
    def Outdated(self):
        return False

    @staticmethod
    def FromTypeString(meterTypeString):
        if meterTypeString is None:
            return None
        return Meter.meterDict[meterTypeString]

    @staticmethod
    def SupportedMeters():
        return list(Meter.meterDict.values())

    @property
    def VendorID(self) -> str:
        return "ЛОГИКА"

    @property
    def Vendor(self) -> str:
        return "ЗАО НПФ ЛОГИКА"

    @property
    @abstractmethod
    def bus_type(self) -> str:
        pass

    @abstractmethod
    def GetCommonTagDefs(self) -> Dict[ImportantTag, object]:
        pass

    def __str__(self):
        return self.Caption

    @staticmethod
    def initialize_meter_dict():
        with threading.Lock():
            mtrs = Meter.getDefinedMeterTypes(type(Meter))

            for m in mtrs:
                Meter.meterDict[m.__class__.__name__] = m

    @abstractmethod
    def GetEventPrefixForTV(self, TVnum: int):
        pass

    def GetWellKnownTags(self) -> Dict[ImportantTag, DataTag]:
        tdefs = self.GetCommonTagDefs()
        wtd = {}
        for key, value in tdefs.items():
            dta = self.lookupCommonTags(value)
            wtd[key] = dta
        return wtd

    def lookupCommonTags(self, tlist: object) -> List[DataTag]:
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
                chType = next(x.Prefix for x in self.Channels if x.Start == 0 and x.Count == 1)
            elif len(ap) == 2:
                chType = ''.join(filter(str.isalpha, ap[0]))
                chNo = 0 if len(chType) == len(ap[0]) else int(ap[0][len(chType):])
                tagName = ap[1]
            else:
                raise Exception("incorrect common tag address")

            dd = self.FindTag(chType, tagName)
            if dd is None:
                raise Exception(f"common tag {tagAddr} not found")
            dta.append(DataTag(dd, chNo))

        return dta

    @abstractmethod
    def advanceReadPtr(self, archiveType, time):
        pass

    @abstractmethod
    def GetDisplayFormat(self, fi):
        pass

    @property
    def Archives(self):
        with self.tagsLock:
            if self._archives is None:
                self.loadMetadata()
            return self._archives

    def HasArchive(self, at):
        return any(x.ArchiveType == at for x in self.Archives)

    @property
    def ArchiveFields(self):
        with self.tagsLock:
            if self.refArchiveFields is None:
                self.loadMetadata()
            return self.refArchiveFields

    def FindArchiveFieldDef(self, archiveType, ordinal):
        raise Exception("no ordinal anymore")

    @property
    def Channels(self):
        if self._channels is None:
            self.loadMetadata()
        return self._channels

    @abstractmethod
    def readArchiveFieldDef(self, r):
        pass

    @abstractmethod
    def family_name(self) -> str:
        pass

    @property
    def resReader(self):
        if self._rr is None:
            mrs = Assembly.GetExecutingAssembly().GetManifestResourceStream("Logika.Tags.resources")
            self._rr = ResourceReader(mrs)
        return self._rr

    @staticmethod
    def readCommonDef(r):
        chKey = str(r["Channel"])
        name = str(r["Name"])
        ordinal = int(r["Ordinal"])
        desc = str(r["Description"])

        kind = TagKind.Undefined
        Enum.TryParse(TagKind, str(r["Kind"]), kind)

        isBasicParam = bool(r["Basic"])
        updRate = int(r["UpdateRate"])

        dataType = None
        sDataType = str(r["DataType"])
        if sDataType:
            dataType = type("System." + sDataType, True)

        stv = StdVar.unknown if r["VarT"] is None else Enum.Parse(StdVar, r["VarT"].ToString())
        descEx = str(r["DescriptionEx"])
        range = str(r["Range"])

    @abstractmethod
    def readTagDef(self, r):
        pass

    @abstractmethod
    def tagsSort(self):
        pass

    @abstractmethod
    def archiveFieldsSort(self):
        pass

    def perfDebugReset(self):
        self._tagVault = None
        self.channelsTable = None
        self._channels = None
        self._archives = None
        self.metadata.Tables.Clear()

    def loadMetadata(self):
        devName = self.__class__.__name[1:]  # TSPTxxx -> SPTxxx

        with Meter.tagsLock:
            # loading channels
            if self.channelsTable is None:
                self.channelsTable = self.loadResTable("Channels")

            if self._channels is None:
                cr = self.channelsTable.Select("Device='" + devName + "'")
                lc = []
                for row in cr:
                    st = int(row["Start"])
                    ct = int(row["Count"])
                    lc.append(ChannelDef(self, row["Key"].ToString(), st, ct, row["Description"].ToString()))
                self._channels = lc

            # loading tags
            if self._tagVault is None:
                tableName = self.family_name() + "Tags"
                dt = self.metadata.Tables.get(tableName)
                if dt is None:
                    dt = self.loadResTable(tableName)

                lt = []
                for r in dt.Select("Device='" + devName + "'", self.tagsSort):
                    rt = self.readTagDef(r)
                    lt.append(rt)
                self._tagVault = TagVault(lt)

            # loading archives
            arTableName = self.family_name() + "Archives"
            dta = self.metadata.Tables.get(arTableName)
            if dta is None:
                dta = self.loadResTable(arTableName)

            if self._archives is None:
                aclassName = self.__class__.__name
                rows = dta.Select("Device='" + devName + "'", "Device, ArchiveType")
                self._archives = self.readArchiveDefs(rows)

            # loading archive fields
            afTableName = self.FamilyName() + "ArchiveFields"
            dtf = self.metadata.Tables.get(afTableName)
            if dtf is None:
                dtf = self.loadResTable(afTableName)

            if self.refArchiveFields is None:
                aclassName = self.__class__.__name
                rows = dtf.Select("Device='" + devName + "'", self.archiveFieldsSort)
                lf = []
                for r in rows:
                    rf = self.readArchiveFieldDef(r)
                    lf.append(rf)
                self.refArchiveFields = lf

    @abstractmethod
    def readArchiveDefs(self, rows: List[DataRow]) -> List[ArchiveDef]:
        pass

    @staticmethod
    def loadResTable(tableName: str) -> DataTable:
        RES_OFFSET = 4

        dt = None
        resType = None
        resData = None

        resReader.GetResourceData(tableName, resType, resData)
        dt = Deserializer.DeserializeDataTable(resData, RES_OFFSET, Encoding.Unicode)
        dt.TableName = tableName
        metadata.Tables.Add(dt)

        return dt

    @property
    def Tags(self) -> TagVault:
        with Meter.tagsLock:
            if self._tagVault is None:
                self.loadMetadata()

        return self._tagVault

    @property
    def SupportsParamsDbChecksum(self) -> bool:
        return ImportantTag.ParamsCSum in self.GetCommonTagDefs()

    def FindTag(self, chKind: str, key: str) -> DataTagDef:
        return self.Tags.Find(chKind, key)

    @abstractmethod
    def GetNTFromTag(self, tagValue: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def getChannelKind(self, channelStart: int, channelCount: int, channelName: str) -> ChannelKind:
        pass

    def getBasicParams(self) -> List[DataTag]:
        dts = []
        paramTagDefs = [x for x in self.Tags.All if x.Kind in [TagKind.Parameter, TagKind.Info] and x.isBasicParam]

        for chDef in self.Channels:
            for chNo in range(chDef.Start, chDef.Start + chDef.Count):
                for td in paramTagDefs:
                    if td.ChannelDef == chDef:
                        dts.append(DataTag(td, chNo))

        return dts
