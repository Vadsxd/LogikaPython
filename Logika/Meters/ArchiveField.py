from Logika.Meters import Tag
from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef6, ArchiveFieldDef


class ArchiveField(Tag):
    def __init__(self, rt: ArchiveFieldDef, channelNo: int, vt: 'ArchiveField' = None):
        if vt:
            super().__init__(vt=vt)
            self.Caption = vt.caption
            self.EU = vt.EU
        else:
            super().__init__(rt, channelNo)
            self.Caption = None
            self.archiveOrd = None

    @property
    def archive_type(self):
        # TODO: не работает deffinition, Channel
        return self.deffinition.archive_type

    @property
    def display_format(self):
        return self.deffinition.display_format

    @property
    def address(self):
        if isinstance(self.deffinition, ArchiveFieldDef6):
            return self.deffinition.address
        else:
            return str(self.deffinition.ordinal)

    def __str__(self):
        sChNum = "" if self.Channel.No == 0 else str(self.Channel.No)
        euStr = "[" + self.EU.strip() + "]" if self.EU and self.EU.strip() else ""
        return "{0} {1} {2}".format(self.Channel.name, self.deffinition.name, euStr)
