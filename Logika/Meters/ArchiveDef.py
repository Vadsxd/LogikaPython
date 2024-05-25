from Logika.Meters.ItemDefBase import ItemDefBase
from Logika.Meters.Types import ArchiveType
from Channel import ChannelDef


class ArchiveDef(ItemDefBase):
    def __init__(self, channel_def: ChannelDef, Ordinal: int, ArchType: ArchiveType, ElementType: type, Capacity: int,
                 Name: str, Description: str):
        super().__init__(channel_def, Ordinal, Name, Description, ElementType)
        self.ArchiveType = ArchType
        self.Capacity = Capacity
        self.Name = Name

    def __str__(self):
        return str(self.ArchiveType) + " " + self.Name + " (" + self.Description + ")"


class ArchiveDef6(ArchiveDef):
    def __init__(self, channel_def: ChannelDef, ArchType: ArchiveType, RecordType: type, Capacity: int, Name: str,
                 Description: str, Ordinal: int):
        super().__init__(channel_def, Ordinal, ArchType, RecordType, Capacity, Name, Description)
        self.Address = str(Ordinal).zfill(3)


class MultipartArchiveDef6(ArchiveDef):
    def __init__(self, channel_def: ChannelDef, ArchType: ArchiveType, RecordType: type, Capacity: int, Name: str,
                 Description: str, Ordinals: int):
        super().__init__(channel_def, -1, ArchType, RecordType, Capacity, Name, Description)
        self.Ordinals = Ordinals

    @property
    def ordinal(self):
        raise Exception("'ordinal' is not available for class")


class ArchiveDef4L(ArchiveDef):
    def __init__(self, channel_def: ChannelDef, ArchType: ArchiveType, RecordType: type, Capacity: int, Name: str,
                 Description: str, RecSize: int, IndexAddr: int, HeadersAddr: int, RecordsAddr: int, IndexAddr2: int,
                 HeadersAddr2: int, RecordsAddr2: int, isTiny42: bool):
        super().__init__(channel_def, -1, ArchType, RecordType, Capacity, Name, Description)
        self.poorMans942 = isTiny42
        self.RecordSize = RecSize
        self.IndexAddr = IndexAddr
        self.HeadersAddr = HeadersAddr
        self.RecordsAddr = RecordsAddr
        self.IndexAddr2 = IndexAddr2
        self.HeadersAddr2 = HeadersAddr2
        self.RecordsAddr2 = RecordsAddr2


class ArchiveDef4M(ArchiveDef):
    def __init__(self, channel_def: ChannelDef, ArchType: ArchiveType, RecordType: type, Capacity: int, Name: str,
                 Description: str):
        super().__init__(channel_def, -1, ArchType, RecordType, Capacity, Name, Description)
