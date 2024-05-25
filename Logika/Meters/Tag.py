from Logika.Meters.Channel import Channel
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Logika6 import Logika6
from Logika.Meters.TagDef import TagDef


class Tag:
    def __init__(self, refTag: TagDef = None, channelNo: int = None, vt: 'Tag' = None):
        if refTag and channelNo:
            self.deffinition = refTag
            if channelNo < refTag.ChannelDef.Start or channelNo >= refTag.ChannelDef.Start + refTag.ChannelDef.Count:
                raise ValueError("некорректный номер канала")
            self.channel = Channel(refTag.ChannelDef, channelNo)
        elif vt:
            self.deffinition = vt.deffinition
            self.channel = vt.channel

    @property
    def name(self):
        return self.deffinition.Name

    @property
    def field_name(self) -> str:
        if isinstance(self.deffinition.meter, Logika4):
            if self.deffinition.ChannelDef.Prefix == "ТВ":
                return f"{self.channel.Name}_{self.deffinition.Name}"
            return self.deffinition.Name
        elif isinstance(self.deffinition.meter, Logika6):
            tagName = self.deffinition.Name
            if self.channel.No > 0 and self.deffinition.ChannelDef.Prefix:
                tagName += f" {self.deffinition.ChannelDef.Prefix}{self.channel.No:02d}"
            return tagName
        else:
            raise Exception("unsupported dev family")

    @property
    def ordinal(self) -> int:
        return self.deffinition.Ordinal

    @property
    def description(self) -> str:
        return self.deffinition.Description

    @property
    def address(self):
        raise NotImplementedError("Tag is abstract")

    def __str__(self) -> str:
        idxStr = ""
        return f"{self.channel.Name}.{self.deffinition.Ordinal}{idxStr}({self.deffinition.Name})"
