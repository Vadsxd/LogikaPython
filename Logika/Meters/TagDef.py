from abc import ABC, abstractmethod
from enum import Enum

from Logika.Meters.Channel import ChannelDef
from Logika.Meters.ItemDefBase import ItemDefBase
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.Types import TagKind
from Logika.Meters.__4L.Logika4L import BinaryType


class Tag6NodeType(Enum):
    Tag = 0
    Array = 1
    Structure = 2


class TagDef(ABC, ItemDefBase):
    def __init__(self, channelDef: ChannelDef, ordinal: int, name: str, stdVar: StdVar, desc: str, dataType: type,
                 dbType: str, displayFormat: str):
        super().__init__(channelDef, ordinal, name, desc, dataType)
        self.StdVar = stdVar
        self.dbType = dbType
        self.DisplayFormat = displayFormat

    @property
    @abstractmethod
    def key(self):
        pass

    @property
    def DbType(self) -> str:
        if not self.dbType:
            if self.ElementType == "Byte":
                return "tinyint"
            elif self.ElementType == "Int32":
                return "int"
            elif self.ElementType == "Int64":
                return "bigint"
            elif self.ElementType == "Single":
                return "real"
            elif self.ElementType == "Double":
                return "float"
            elif self.ElementType == "String":
                return "varchar(128)"
            else:
                raise NotImplementedError("cannot map DataType to DbType")


class DataTagDef(ABC, TagDef):
    def __init__(self, channel: ChannelDef, name: str, stdVar: StdVar, desc: str, dataType: type, dbType: str, displayFormat: str, tagKind: TagKind, basicParam: bool, updateRate: int,
                 order: int, descEx: str, ranging: str):
        super().__init__(channel, order, name, stdVar, desc, dataType, dbType, displayFormat)
        self.Kind = tagKind
        self.isBasicParam = basicParam
        self.UpdateRate = updateRate
        self.DescriptionEx = descEx
        self.ranging = ranging

    def __str__(self):
        return "{0} {1} {2}".format(self.key, self.Ordinal, self.Name)


class DataTagDef6(DataTagDef):
    def __init__(self, ownerChannel: ChannelDef, nodeType: Tag6NodeType, name: str, stdVar: StdVar, tagKind: TagKind,
                 basicParam: bool, updateRate: int, order: int, desc: str, dataType: type, sDbType: str, index: int,
                 count: int, descEx: str, ranging: str):
        super().__init__(ownerChannel, name, stdVar, desc, dataType, sDbType, '', tagKind, basicParam, updateRate,
                         order, descEx, ranging)
        self.NodeType = nodeType
        self.Index = index
        self.Count = count
        self.Address = f"{order:03d}" + (f"н{index:02d}" if index is not None else "")

    def __str__(self):
        if self.NodeType == Tag6NodeType.Structure:
            return f"structure {self.Name} {self.Description}"
        elif self.NodeType == Tag6NodeType.Array:
            return f"array {self.Name} {self.Description}"
        else:
            return super().__str__()


class TagDef4(DataTagDef):
    def __init__(self, ch: ChannelDef, name: str, stdVar: StdVar, tagKind: TagKind, basicParam: bool, updateRate: int,
                 order: int, desc: str, dataType: type, sDbType: str, units: str, displayFormat: str, descEx: str,
                 ranging: str):
        super().__init__(ch, name, stdVar, desc, dataType, sDbType, displayFormat, tagKind, basicParam, updateRate,
                         order, descEx, ranging)
        self.Units = units

    @property
    def key(self):
        return self.Name


class TagDef4L(TagDef4):
    def __init__(self, parentChannel: ChannelDef, name: str, stdVar: StdVar, tagKind: TagKind, basicParam: bool,
                 updateRate: int, order: int, desc: str, dataType: type, sDbType: str, units: str, displayFormat: str,
                 descEx: str, ranging: str, binType: BinaryType, inRam: bool, addr: int, chnOffs: int, addonAddr: int,
                 addonChnOffs: int):
        super().__init__(parentChannel, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType,
                         units, displayFormat, descEx, ranging)
        if addr < 0 or chnOffs < 0 or addonAddr < 0 or addonChnOffs < 0:
            raise ValueError("Nullable address value cannot be < 0")
        self.internalType = binType
        self.inRAM = inRam
        self.address = addr
        self.channelOffset = chnOffs
        self.addonAddress = addonAddr
        self.addonChannelOffset = addonChnOffs

    def __str__(self):
        return f"{self.Ordinal} {ChannelDef.Prefix} {self.Name} {self.Kind}"


class TagDef4M(TagDef4):
    def __init__(self, parentChannel: ChannelDef, name: str, stdVar: StdVar, tagKind: TagKind, basicParam: bool,
                 updateRate: int, order: int, desc: str, dataType: type, sDbType: str, units: str, displayFormat: str,
                 descEx: str, ranging: str):
        super().__init__(parentChannel, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType,
                         units, displayFormat, descEx, ranging)

    def __str__(self):
        return f"{self.Ordinal} {ChannelDef.Prefix} {self.Name} {self.Kind}"
