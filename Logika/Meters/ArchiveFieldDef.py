from abc import ABC

from Logika.Meters import TagDef
from Logika.Meters.ArchiveDef import ArchiveDef
from Logika.Meters.Channel import ChannelDef
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.Types import ArchiveType
from Logika.Meters.__4L.Logika4L import BinaryType


class ArchiveFieldDef(ABC, TagDef):
    def __init__(self, channel: ChannelDef, ordinal: int, at: ArchiveType, name: str, description: str, stndVar: StdVar,
                 data_type: type, dbType: str, displayFormat: str):
        super().__init__(channel, ordinal, name, stndVar, description, data_type, dbType, displayFormat)
        self.ArchiveType = at
        self.ChannelDef = channel
        self.Name = name
        self.Description = description
        self.StndVar = stndVar
        self.DataType = data_type
        self.DisplayFormat = displayFormat
        self.DbType = dbType
        self.Ordinal = ordinal

    def __str__(self):
        return "{0} {1}".format(self.ChannelDef.Prefix, self.Name)


class ArchiveFieldDef6(ArchiveFieldDef):
    def __init__(self, ch: ChannelDef, at: ArchiveType, name: str, desc: str, ordinal: int, standard_variable: StdVar,
                 data_type: type, dbType: str, displayFormat: str):
        super().__init__(ch, ordinal, at, name, desc, standard_variable, data_type, dbType, displayFormat)
        self.Ordinal = ordinal
        self.NameSuffixed = name
        self.ChannelDef = ch
        ptPos = name.find('(')
        if ptPos > 0 and name.endswith(")"):
            self.Name = name[:ptPos]

    @property
    def address(self):
        return format(self.Ordinal, "000")

    @property
    def key(self):
        return self.address


class ArchiveFieldDef4(ABC, ArchiveFieldDef):
    def __init__(self, ar: ArchiveDef, name: str, desc: str, stdVar: StdVar, data_type: type, dbType: str,
                 displayFormat: str, units: str):
        super().__init__(ar.ChannelDef, -1, ar.ArchiveType, name, desc, stdVar, data_type, dbType, displayFormat)
        self.Archive = ar
        self.Units = units
        self.Name = name

    @property
    def key(self):
        return self.Name


class ArchiveFieldDef4L(ArchiveFieldDef4):
    def __init__(self, ar: ArchiveDef, name: str, desc: str, stdVar: StdVar, data_type: type, dbType: str, units: str,
                 displayFormat: str, binType: BinaryType, fldOffset: int):
        super().__init__(ar, name, desc, stdVar, data_type, dbType, displayFormat, units)
        self.InternalType = binType
        self.FieldOffset = fldOffset


class ArchiveFieldDef4M(ArchiveFieldDef4):
    def __init__(self, ar: ArchiveDef, fieldIndex: int, name: str, desc: str, standardVariable: StdVar, data_type: type,
                 dbType: str, displayFormat: str, units: str):
        super().__init__(ar, name, desc, standardVariable, data_type, dbType, displayFormat, units)
        self.FieldIndex = fieldIndex

    def __str__(self):
        return "{0} {1}".format(self.ChannelDef.Prefix, self.Name)
