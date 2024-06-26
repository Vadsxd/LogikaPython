from typing import List

from Logika.Meters import Tag
from Logika.Meters.TagDef import DataTagDef6, DataTagDef


class DataTag(Tag):
    def __init__(self, refTag: DataTagDef, channelNo: int, t: 'DataTag' = None):
        if t:
            super().__init__(vt=t)
            self.Value = t.Value
            self.EU = t.EU
            self.Oper = t.Oper
            self.addr = t.addr
            self.Name = t.name
        else:
            super().__init__(refTag, channelNo)
            if isinstance(refTag, DataTagDef6):
                self.addr = refTag.Address
                if channelNo > 0:
                    self.addr += refTag.ChannelDef.Prefix + str(channelNo)
            else:
                td = refTag
                self.addr = (td.ChannelDef.Prefix + str(channelNo) + "_" if channelNo > 0 else "") + td.name

    @property
    def index(self):
        return self.deffintion.Index if isinstance(self.deffintion, DataTagDef6) else None

    @property
    def display_format(self):
        return self.deffintion.display_format

    @property
    def address(self):
        return self.addr

    def __str__(self):
        idxStr = "н{0:d2}".format(self.index) if self.index is not None else ""
        euStr = "[" + self.EU.strip() + "]" if self.EU.strip() else ""
        return "{0}.{1:d3}{2}({3}) = {4} {5}".format(self.Channel.name, self.deffintion.ordinal, idxStr,
                                                     self.deffintion.name, self.Value, euStr)


class DataTag6Container(Tag):
    def __init__(self, refTag: DataTagDef, channelNo: int, leafs: List[DataTagDef6]):
        super().__init__(refTag, channelNo)
        self.tags: List[DataTag] = [DataTag(leaf, channelNo) for leaf in leafs]

    @property
    def address(self):
        return self.deffintion.address

    def __str__(self):
        # TODO: разобраться с тегами (self.deffinition - не рабочий)
        containerType = self.deffintion.NodeType[0]
        return "<{0}> {1}.{2:d3} ({3})".format(containerType, self.Channel.name,
                                               self.deffintion.ordinal, self.deffintion.description)
