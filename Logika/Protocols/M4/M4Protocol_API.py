from datetime import datetime
from enum import Enum

from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Types import ImportantTag, TagKind
from Logika.Meters.__4L.Logika4L import Logika4L


class updTagsFlags(Enum):
    Zero = 0,
    DontGetEUs = 1,


class Logika4MArchiveRequestState:
    def __init__(self):
        self.arDef = None
        self.fieldDefs = None
        self.currentChannel = None
        self.nChRecsRead = None
        self.tPtr = None


class MeterInstance:
    def __init__(self, owner, m: Logika4, nt):
        self.timeDiff = None
        self.eus = None
        self.proto = owner
        self.mtr = m
        if isinstance(m, Logika4L):
            lastTotalAddr = max(
                (t.address + (t.channelOffset or 0) + Logika4L.SizeOf(t.internalType) for t in m.tags.all if
                 t.Kind == TagKind.TotalCtr), default=0)
            paramsFlashSize = lastTotalAddr + Logika4L.FLASH_PAGE_SIZE - 1  # запас для хвостов
            self.flash = bytearray(paramsFlashSize)
            self.pageMap = [False] * (len(self.flash) // Logika4L.FLASH_PAGE_SIZE)
        self.vipTags = m.get_well_known_tags()
        self.nt = nt

    @property
    def model(self):
        if self.model is None:
            if ImportantTag.Model in self.vipTags:
                self.proto.updateTags(self.nt, self.vipTags[ImportantTag.Model], updTagsFlags.DontGetEUs)
                self.model = str(self.vipTags[ImportantTag.Model][0].Value)
            else:
                self.model = ""
        return self.model

    @property
    def rd(self):
        if self.rd < 0 or self.rh < 0:
            self.read_rdrh()
        return self.rd

    @property
    def rh(self):
        if self.rd < 0 or self.rh < 0:
            self.read_rdrh()
        return self.rh

    def read_rdrh(self):
        rdta = [self.vipTags[ImportantTag.RDay][0], self.vipTags[ImportantTag.RHour][0]]
        self.proto.updateTags(self.nt, rdta, updTagsFlags.DontGetEUs)
        self.rd = int(rdta[0].Value)
        self.rh = int(rdta[1].Value)

    @property
    def eu_dict(self):
        if self.eus is None:
            if ImportantTag.EngUnits in self.vipTags:
                self.proto.updateTags(self.nt, self.vipTags[ImportantTag.EngUnits], updTagsFlags.DontGetEUs)
                self.eus = self.mtr.build_eu_dict(self.vipTags[ImportantTag.EngUnits])
        return self.eus

    @property
    def CurrentDeviceTime(self):
        if self.timeDiff == float('inf'):
            tTime = self.mtr.Tags.Find("ОБЩ", "T")
            tDate = self.mtr.Tags.Find("ОБЩ", "Д")
            if tTime is None or tDate is None:
                return datetime.min
            dta = [DataTag(tDate, 0), DataTag(tTime, 0)]
            self.proto.updateTags(self.nt, dta, updTagsFlags.DontGetEUs)
            devTime = Logika4.combine_date_time(str(dta[0].Value), str(dta[1].Value))
            self.timeDiff = datetime.now() - devTime
        return datetime.now() - self.timeDiff

    @rd.setter
    def rd(self, value):
        self.rd = value

    @rh.setter
    def rh(self, value):
        self.rh = value

    @model.setter
    def model(self, value):
        self.model = value


class M4Protocol:
    def __init__(self):
        self.page_map = None

