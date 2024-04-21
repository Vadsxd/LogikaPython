from enum import Enum
from Logika.Meters.ItemDefBase import ItemDefBase
from Logika.Meters.Channel import ChannelDef


class TagDef(ItemDefBase):
    def __init__(self, channelDef, ordinal, name, stdVar, desc, dataType, dbType, displayFormat):
        super().__init__(channelDef, ordinal, name, desc, dataType)
        self.StdVar = stdVar
        self.dbType = dbType
        self.DisplayFormat = displayFormat

    @property
    def Key(self):
        pass

    @property
    def DbType(self):
        if not self.dbType:
            if self.ElementType.Name == "Byte":
                return "tinyint"
            elif self.ElementType.Name == "Int32":
                return "int"
            elif self.ElementType.Name == "Int64":
                return "bigint"
            elif self.ElementType.Name == "Single":
                return "real"
            elif self.ElementType.Name == "Double":
                return "float"
            elif self.ElementType.Name == "String":
                return "varchar(128)"
            else:
                raise NotImplementedError("cannot map DataType to DbType")


class DataTagDef(TagDef):
    def __init__(self, channel, name, stdVar, desc, dataType, dbType, displayFormat, tagKind, basicParam, updateRate,
                 order, descEx, ranging):
        super().__init__(channel, order, name, stdVar, desc, dataType, dbType, displayFormat)
        self.Kind = tagKind
        self.isBasicParam = basicParam
        self.UpdateRate = updateRate
        self.DescriptionEx = descEx
        self.ranging = ranging

    def __str__(self):
        return "{0} {1} {2}".format(self.Key, self.Ordinal, self.Name)


class Tag6NodeType(Enum):
    Tag = 0
    Array = 1
    Structure = 2


class DataTagDef6(DataTagDef):
    def __init__(self, ownerChannel, nodeType, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType,
                 sDbType, index, count, descEx, ranging):
        super().__init__(ownerChannel, name, stdVar, desc, dataType, sDbType, None, tagKind, basicParam, updateRate,
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
    def __init__(self, ch, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType, units,
                 displayFormat, descEx, ranging):
        super().__init__(ch, name, stdVar, desc, dataType, sDbType, displayFormat, tagKind, basicParam, updateRate,
                         order, descEx, ranging)
        self.Units = units

    @property
    def Key(self):
        return self.Name


class TagDef4L(TagDef4):
    def __init__(self, parentChannel, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType,
                 units, displayFormat, descEx, ranging,
                 binType, inRam, addr, chnOffs, addonAddr, addonChnOffs):
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
    def __init__(self, parentChannel, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType,
                 units, displayFormat, descEx, ranging):
        super().__init__(parentChannel, name, stdVar, tagKind, basicParam, updateRate, order, desc, dataType, sDbType,
                         units, displayFormat, descEx, ranging)

    def __str__(self):
        return f"{self.Ordinal} {ChannelDef.Prefix} {self.Name} {self.Kind}"
