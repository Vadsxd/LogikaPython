from typing import List
from datetime import datetime

from Logika.Meters.ArchiveDef import ArchiveDef4L
from Logika.Meters.ArchiveFieldDef import ArchiveFieldDef
from Logika.Meters.__4L.Logika4L import Logika4L
from Logika.Protocols.M4.FlashRingBuffer import FRBIndex, FlashArray
from Logika.Protocols.M4.M4Protocol import MeterInstance


class Logika4LTVReadState:
    def __init__(self):
        self.idx = -1
        self.restartPoint = -1
        self.indexes = []
        self.headersRead = False
        self.dirtyIndexes = None
        self.dirtyIndexesInitialCount = 0
        self.fArchive = None


class Logika4LArchiveRequestState:
    def __init__(self, ars):
        self.ars = ars


class VQT:
    def __init__(self, Quality=0, Timestamp=None):
        self.Quality = Quality
        self.Timestamp = Timestamp
        self.Value = None


class FlashArchive4:
    def __init__(self, mi: MeterInstance, arDef, channelNo, elementSize, HeaderTimeGetter, HeaderValueGetter):
        self.mi = mi
        self.deffinition = arDef
        idxAddr = self.deffinition.IndexAddr2 if channelNo == 2 else self.deffinition.IndexAddr
        if arDef.ArchiveType.IsIntervalArchive:
            dataAddr = self.deffinition.HeadersAddr2 if channelNo == 2 else deffinition.HeadersAddr
        else:
            dataAddr = self.deffinition.RecordsAddr2 if channelNo == 2 else self.deffinition.RecordsAddr
        self.headers = FlashRingBuffer(self, idxAddr, dataAddr, self.deffinition.Capacity, elementSize, HeaderTimeGetter, HeaderValueGetter)

    @property
    def Meter(self):
        return self.mi.mtr if isinstance(self.mi.mtr, Logika4L) else None

    @property
    def ArchiveType(self):
        return self.deffinition.ArchiveType

    def reset(self):
        self.headers.reset()

    def get_data_point(self, index: int):
        nts = self.headers.Times[index]
        if not nts:  # empty / erased header
            return None

        hdp = VQT(Quality=0, Timestamp=nts)

        if self.headers.Values:  # ValueGetter supplied
            hdp.Value = self.headers.Values[index]

        return hdp

    def invalidate_data(self, outdated_indexes: List[int]):
        pass

    def update_data(self, indexes_to_read):
        pass


class SyncFlashArchive4(FlashArchive4):
    def __init__(self, mi, arDef, channelNo, mtrInfo):
        super().__init__(mi, arDef, channelNo, 4, self.get_header_time, None)
        self.data = FlashArray(mi, arDef.RecordsAddr2 if channelNo == 2 else arDef.RecordsAddr, arDef.Capacity, arDef.RecordSize)
        self.RD = int(mi.rd)
        self.RH = int(mi.rh)
        self.fields = [x for x in mi.mtr.ArchiveFields if x.ArchiveType == arDef.ArchiveType]

    @property
    def RH(self):
        return self.RH

    @RH.setter
    def RH(self, value):
        self.RH = value

    @property
    def RD(self):
        return self.RD

    @RD.setter
    def RD(self, value):
        self.RD = value

    @staticmethod
    def get_header_time(fa: FlashArchive4, buffer: List[bytes], offset: int):
        sfa = fa.__class__ = SyncFlashArchive4
        return Logika4L.sync_header_to_datetime(sfa.ArchiveType, sfa.RD, sfa.RH, buffer, offset)

    def update_data(self, indexes: List[FRBIndex]):
        self.data.update_elements(indexes)

    def invalidate_data(self, outdated_indexes: List[int]):
        for i in outdated_indexes:
            self.data.invalidate_element(i)

    def get_data_point(self, index: int):
        nhdp = super().get_data_point(index)
        if nhdp:
            buf, offset = self.data.get_element(index)
            varArray = [Logika4L.get_value(field.InternalType, buf, offset + field.FieldOffset) for field in self.fields]
            nhdp.Value = varArray
        return nhdp


class AsyncFlashArchive4(FlashArchive4):
    def __init__(self, mi: MeterInstance, arDef: ArchiveDef4L, channelNo: int, ValueGetter):
        super().__init__(mi, arDef, channelNo, arDef.RecordSize, self.get_async_record_time, ValueGetter)

    @staticmethod
    def get_async_record_time(archive: FlashArchive4, buffer: List[bytes], offset: int):
        return Logika4L.get_value(Logika4L.BinaryType.svcRecordTimestamp, buffer, offset)

    def update_data(self, indexes: List[FRBIndex]):
        indexes.clear()

