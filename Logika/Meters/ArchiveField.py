from Logika.Meters import Tag
from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef6


class ArchiveField(Tag):
    def __init__(self, rt, channelNo):
        super().__init__(rt, channelNo)
        self.Caption = None
        self.archiveOrd = None

    def __init__(self, vt):
        super().__init__(vt)
        self.Caption = vt.Caption
        self.EU = vt.EU

    @property
    def ArchiveType(self):
        return self.deffinition.ArchiveType

    @property
    def DisplayFormat(self):
        return self.deffinition.DisplayFormat

    @property
    def Address(self):
        if isinstance(self.deffinition, ArchiveFieldDef6):
            return self.deffinition.Address
        else:
            return str(self.deffinition.Ordinal)

    def __str__(self):
        sChNum = "" if self.Channel.No == 0 else str(self.Channel.No)
        euStr = "[" + self.EU.strip() + "]" if self.EU and self.EU.strip() else ""
        return "{0} {1} {2}".format(self.Channel.Name, self.deffinition.Name, euStr)
