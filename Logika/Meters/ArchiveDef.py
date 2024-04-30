from enum import Enum
from Logika.Meters.Types import ArchiveType


class ItemDefBase:
    def __init__(self, ChannelDef, Ordinal, Name, Description, ElementType):
        self.ChannelDef = ChannelDef
        self.Ordinal = Ordinal
        self.Name = Name
        self.Description = Description
        self.ElementType = ElementType


class ArchiveDef(ItemDefBase):
    def __init__(self, ChannelDef, Ordinal, ArchType: ArchiveType, ElementType, Capacity, Name, Description):
        super().__init__(ChannelDef, Ordinal, Name, Description, ElementType)
        self.ArchiveType = ArchType
        self.Capacity = Capacity

    def __str__(self):
        return str(self.ArchiveType) + " " + self.Name + " (" + self.Description + ")"


class ArchiveDef6(ArchiveDef):
    def __init__(self, ChannelDef, ArchType, RecordType, Capacity, Name, Description, Ordinal):
        super().__init__(ChannelDef, Ordinal, ArchType, RecordType, Capacity, Name, Description)
        self.Address = str(Ordinal).zfill(3)


class MultipartArchiveDef6(ArchiveDef):
    def __init__(self, ChannelDef, ArchType, RecordType, Capacity, Name, Description, Ordinals):
        super().__init__(ChannelDef, -1, ArchType, RecordType, Capacity, Name, Description)
        self.Ordinals = Ordinals

    @property
    def ordinal(self):
        raise Exception("'ordinal' is not available for class")


class ArchiveDef4L(ArchiveDef):
    def __init__(self, ChannelDef, ArchType, RecordType, Capacity, Name, Description, RecSize, IndexAddr, HeadersAddr,
                 RecordsAddr,
                 IndexAddr2, HeadersAddr2, RecordsAddr2, isTiny42):
        super().__init__(ChannelDef, -1, ArchType, RecordType, Capacity, Name, Description)
        self.poorMans942 = isTiny42
        self.RecordSize = RecSize
        self.IndexAddr = IndexAddr
        self.HeadersAddr = HeadersAddr
        self.RecordsAddr = RecordsAddr
        self.IndexAddr2 = IndexAddr2
        self.HeadersAddr2 = HeadersAddr2
        self.RecordsAddr2 = RecordsAddr2


class ArchiveDef4M(ArchiveDef):
    def __init__(self, ChannelDef, ArchType, RecordType, Capacity, Name, Description):
        super().__init__(ChannelDef, -1, ArchType, RecordType, Capacity, Name, Description)
