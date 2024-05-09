from datetime import datetime, timedelta
from enum import Enum

from Logika.Meters.Archive import Archive, IntervalArchive, ServiceRecord, ServiceArchive
from Logika.Meters.ArchiveDef import ArchiveDef4L
from Logika.Meters.ArchiveField import ArchiveField
from Logika.Meters.Channel import ChannelKind
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Meter import Meter
from Logika.Meters.TagDef import TagDef4L, TagDef4M
from Logika.Meters.Types import ImportantTag, TagKind, ArchiveType
from Logika.Meters.__4L.Logika4L import Logika4L
from Logika.Meters.__4L.SPG741 import TSPG741
from Logika.Meters.__4M.Logika4M import Logika4M
from Logika.Protocols.M4.M4ArchiveId import M4ArchiveId
from M4ArchiveRecord import M4ArchiveRecord
from M4Protocol import M4Protocol as M4


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
    def __init__(self, owner: M4, m: Logika4, nt):
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
                self.proto.update_tags(self.nt, self.vipTags[ImportantTag.Model], updTagsFlags.DontGetEUs)
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
    def current_device_time(self):
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
        self.metadataCache = None
        self.CHANNEL_NBASE = 10000

    def get_meter_instance(self, m, nt):
        _nt = nt if nt is not None else 0xFF

        if _nt not in self.metadataCache:
            mi = MeterInstance(self, m, _nt)
            self.metadataCache[_nt] = mi
        else:
            mi = self.metadataCache[_nt]

        return mi

    def update_tags(self, src, dst, tags):
        if len(tags) == 0:
            return
        self.update_tags(dst, tags, updTagsFlags.Zero)

    def get_flash_pages_to_cache(self, mtr, nt, startPageNo, count, mi):
        if count <= 0 or startPageNo < 0:
            raise ValueError()
        st = -1
        ct = 0
        for i in range(count):
            p = startPageNo + i
            r = False
            if not mi.pageMap[p]:
                if st < 0:
                    st = p
                    ct = 1
                else:
                    ct += 1

            if i == count - 1 and ct > 0:
                r = True

            if r:
                print("req pages {0}..{1}".format(st, st + ct - 1))
                pg = M4.read_flash_pages(self, mtr, nt, st, ct)
                mi.flash[st * Logika4L.FLASH_PAGE_SIZE: (st + ct) * Logika4L.FLASH_PAGE_SIZE] = pg
                for f in range(ct):
                    mi.pageMap[st + f] = True

    def get4L_real_addr(self, mi: MeterInstance, t: DataTag):
        deffinition = t.deffinition
        if mi.mtr == Meter.SPG741 and 200 <= deffinition.Ordinal < 300:
            return TSPG741.get_mapped_db_param_addr(deffinition.Key, M4.get741sp(mi.nt))
        else:
            return deffinition.address + (deffinition.channelOffset if t.Channel.No == 2 else 0)

    def update4L_tags_values(self, nt, tags, mi, flags):
        mtr = tags[0].deffinition.Meter if isinstance(tags[0].deffinition.Meter, Logika4L) else None
        for i in range(len(tags)):
            t = tags[i]
            def_ = t.deffinition if isinstance(t.deffinition, TagDef4L) else None
            t.EU = def_.Units

            addr = self.get4L_real_addr(mi, t)

            stp = addr // Logika4L.FLASH_PAGE_SIZE

            if def_.inRAM:  # RAM vars
                rbuf = self.read_ram(mtr, nt, addr, Logika4L.SizeOf(def_.internalType))
                t.Value = Logika4L.GetValue(def_.internalType, rbuf, 0)
            else:  # flash (or flash + ram) vars
                pfCnt = stp % 2 if stp < len(mi.pageMap) - 1 else 0
                self.get_flash_pages_to_cache(mtr, nt, stp, 1 + pfCnt, mi)
                t.Value, t.Oper = Logika4L.GetValue(def_.internalType, mi.flash, addr)

                if def_.addonAddress is not None:  # тотальные счетчики из двух частей
                    raddr = def_.addonAddress + (def_.addonChannelOffset if t.Channel.No == 2 else 0)
                    rbuf = self.read_ram(mtr, nt, raddr, Logika4L.SizeOf(Logika4L.BinaryType.r32))
                    ramFloatAddon = Logika4L.GetMFloat(rbuf)
                    t.Value += ramFloatAddon

            if not flags & updTagsFlags.DontGetEUs:
                t.EU = Logika4.getEU(mi.EUDict, def_.Units)

            t.TimeStamp = datetime.now()

            self.post_process_value(t)

    def invalidate_flash_cache4L(self, nt, tags):
        mmd = self.get_meter_instance(
            tags[0].deffinition.Meter if isinstance(tags[0].deffinition.Meter, Logika4L) else None, nt)

        for i in range(len(tags)):
            t = tags[i]
            def_ = t.deffinition if isinstance(t.deffinition, TagDef4L) else None

            addr = self.get4L_real_addr(mmd, t)
            stp = addr // Logika4L.FLASH_PAGE_SIZE
            enp = (addr + Logika4L.SizeOf(def_.internalType) - 1) // Logika4L.FLASH_PAGE_SIZE

            for p in range(stp, enp + 1):
                mmd.pageMap[p] = False

    @staticmethod
    def post_process_value(t: DataTag):
        if t.deffinition.Meter == Meter.SPT941_10 and t.Name.lower() == "model" and t.Value is not None and len(
                str(t.Value)) == 1:
            t.Value = "1" + str(t.Value)

    def update_tags4M(self, nt, tags, mi, flags):
        mtr = tags[0].deffinition.Meter if isinstance(tags[0].deffinition.Meter, Logika4M) else None

        chs = []
        ords = []
        blkSt = 0

        for t in tags:
            td = t.deffinition if isinstance(t.deffinition, TagDef4M) else None
            chs.append(t.Channel.No)
            ords.append(t.Ordinal)

        if len(ords) == M4.MAX_TAGS_AT_ONCE or t == tags[-1]:
            va, opFlags = M4.read_tags_m4(M4, mtr, nt, chs, ords)
            for z in range(len(ords)):
                vt = tags[blkSt + z]
                vt.Value = va[z]
                if vt.Value is None:
                    vt.ErrorDesc = Logika4M.ND_STR
                if not flags & updTagsFlags.DontGetEUs:
                    vt.EU = Logika4.getEU(mi.EUDict, td.Units)
                vt.Oper = opFlags[z]
                vt.TimeStamp = datetime.now()

            blkSt += len(ords)
            chs.clear()
            ords.clear()

    def read_interval_archive_def(self, m, src_nt, dst_nt, ar_type):
        mtr4 = m if isinstance(m, Logika4) else None
        if not ar_type.is_interval_archive:
            raise ValueError("wrong archive type")

        ar = IntervalArchive(m, ar_type)

        mi = self.get_meter_instance(mtr4, dst_nt)

        if m == Meter.SPT942:
            tiny42 = mi.Model == "4" or mi.Model == "6"
            ard = next(x for x in m.Archives if x.ArchiveType == ar_type and x.poorMans942 == tiny42)
        else:
            ard = next(x for x in m.Archives if x.ArchiveType == ar_type)

        field_defs = [x for x in m.ArchiveFields if x.ArchiveType == ar_type]

        ch_start = ard.ChannelDef.Start
        ch_end = ch_start + ard.ChannelDef.Count - 1

        for ch in range(ch_start, ch_end + 1):
            for fd in field_defs:
                af = ArchiveField(fd, ch)
                af.EU = Logika4.getEU(mi.EUDict, fd.Units)
                fld_name = fd.Name
                if ard.ChannelDef.Kind == ChannelKind.TV:
                    fld_name = f"{ard.ChannelDef.Prefix}{ch}_{fd.Name}"

                dc = ar.Table.Columns.Add(fld_name, fd.ElementType)
                dc.ExtendedProperties[Archive.FLD_EXTPROP_KEY] = af

        state = None
        if isinstance(m, Logika4L):
            ars = [Logika4LTVReadState() for _ in range(ard.ChannelDef.Count)]
            for i in range(ard.ChannelDef.Count):
                ars[i].headersRead = False
                ars[i].idx = -1
                ars[i].fArchive = SyncFlashArchive4(mi, ard, ard.ChannelDef.Start + i, mi)
            rs = Logika4LArchiveRequestState(ars)
            state = rs
        else:
            rs = Logika4MArchiveRequestState()
            rs.arDef = ard
            rs.fieldDefs = [x for x in field_defs]
            state = rs

        return ar

    def read_interval_archive(self, m, src_nt, nt, ar, start, end, state):
        if isinstance(m, Logika4L):
            return self.read_flash_archive4L(m, nt, ar, start, end, state)
        elif isinstance(m, Logika4M):
            return self.read_interval_archive4M(m, nt, ar, start, end, state)
        else:
            raise ValueError("wrong meter type")

    def read_flash_archive4L(self, m, nt, ar, start, end, state_obj, progress):
        state = state_obj

        PCT_HEADERS = 0  # percentage of headers to data (progress calc)
        PCT_DATA = 0

        if ar.ArchiveType.IsIntervalArchive:
            PCT_HEADERS = 10 / len(state.ars)
            PCT_DATA = 100 / len(state.ars) - PCT_HEADERS
        else:
            if state_obj is None:
                state_obj = state = self.init_4L_service_archive_read_state(m, nt, ar.ArchiveType)
            PCT_HEADERS = 100 / len(state.ars)
            PCT_DATA = 0

        for i in range(len(state.ars)):
            trs = state.ars[i]
            fa = trs.fArchive
            if trs.idx < 0:
                fa.headers.ManageOutdatedElements(True, new_headers, trs.idx)

            pct_hdr_read = 0
            if not trs.headersRead:
                if fa.headers.GetElementIndexesInRange(start, end, trs.idx, trs.restartPoint, trs.indexes,
                                                       pct_hdr_read):
                    trs.headersRead = True
                    trs.dirtyIndexes = sorted(trs.indexes, key=lambda x: x.idx)
                    trs.dirtyIndexes_initial_count = len(trs.dirtyIndexes)
                else:
                    progress = i * (PCT_HEADERS + PCT_DATA) + (pct_hdr_read * PCT_HEADERS / 100.0)
                    return True

            fa.update_data(trs.dirtyIndexes)

            if len(trs.dirtyIndexes) > 0:
                if trs.dirtyIndexes_initial_count > 0:
                    pct_data_read = 100.0 * (
                                trs.dirtyIndexes_initial_count - len(trs.dirtyIndexes)) / trs.dirtyIndexes_initial_count
                    progress = i * (PCT_HEADERS + PCT_DATA) + PCT_HEADERS + PCT_DATA * pct_data_read / 100.0
                else:
                    progress = 0
                return True

        progress = 100

        if ar.ArchiveType.IsIntervalArchive:
            self.process_interval_data_4L(state, ar)
        else:
            self.process_service_archive_data_4L(state, ar)

        return False

    @staticmethod
    def process_interval_data_4L(state, ar):
        ar.Table.Rows.Clear()
        for tv in range(len(state.ars)):
            trs = state.ars[tv]

            for i in range(len(trs.indexes)):
                hdp = trs.fArchive.GetDataPoint(trs.indexes[i].idx)

                row = ar.Table.Rows.Find(hdp.Timestamp)  # locate by PK
                if i == 0:
                    continue  # record with non-unique timestamp (due to corrupt headers)

                if row is None:
                    oa = [None] * (1 + len(hdp.Value) * len(state.ars))
                    oa[0] = hdp.Timestamp
                    fields = hdp.Value
                    for idx, field in enumerate(fields):
                        oa[1 + tv * len(fields) + idx] = field
                    ar.Table.Rows.Add(oa)
                else:
                    oa = list(row.ItemArray)
                    fields = hdp.Value
                    for idx, field in enumerate(fields):
                        oa[1 + tv * len(fields) + idx] = field
                    row.ItemArray = oa

    @staticmethod
    def process_service_archive_data_4L(state, svcArchive):
        svcArchive.Records.clear()

        for tv in range(len(state.ars)):
            trs = state.ars[tv]

            for ch in range(len(trs.indexes)):
                hdp = trs.fArchive.GetDataPoint(trs.indexes[ch].idx)
                if hdp is not None:
                    evt = str(hdp.Value)
                    desc = None
                    if trs.fArchive.ArchiveType == ArchiveType.ErrorsLog:
                        desc = svcArchive.Meter.GetNSDescription(evt)

                    if len(state.ars) > 1:  # devices with two TV
                        evt = str(tv + 1) + "-" + evt

                    sr = ServiceRecord(hdp.Timestamp, evt, desc)
                    svcArchive.Records.append(sr)

    def init_4L_service_archive_read_state(self, m, nt, arType):
        mi = self.get_meter_instance(m, nt)
        ard = next(x for x in m.Archives if x.ArchiveType == arType)
        tvsa = [Logika4LTVReadState() for _ in range(ard.ChannelDef.Count)]

        record_getter = None
        if arType == ArchiveType.ErrorsLog:
            record_getter = lambda _ar, b, o: Logika4L.GetValue(Logika4L.BinaryType.NSrecord, b, o)
        elif arType == ArchiveType.ParamsLog:
            record_getter = lambda _ar, b, o: Logika4L.GetValue(Logika4L.BinaryType.IZMrecord, b, o)

        for i in range(ard.ChannelDef.Count):
            tvsa[i] = Logika4LTVReadState()
            tvsa[i].fArchive = AsyncFlashArchive4(mi, ard as ArchiveDef4L, ard.ChannelDef.Start + i, record_getter)
            tvsa[i].headersRead = False
            tvsa[i].idx = -1

        return Logika4LArchiveRequestState(tvsa)

    @staticmethod
    def fix_intv_timestamp(r: M4ArchiveRecord, art, mtd: MeterInstance):
        if r.dt == datetime.min:
            if art == ArchiveType.Hour:
                r.dt = r.interval_mark
            elif art == ArchiveType.Day or art == ArchiveType.Control:
                r.dt = r.interval_mark + timedelta(hours=mtd.rh)
            elif art == ArchiveType.Month:
                r.dt = r.interval_mark + timedelta(days=mtd.rd - 1) + timedelta(hours=mtd.rh)
            else:
                raise Exception("fix_intv_timestamp: неподдерживаемый тип архива")

    @staticmethod
    def get_ar_code(at: ArchiveType) -> M4ArchiveId:
        if at == ArchiveType.Hour:
            return M4ArchiveId.Hour
        elif at == ArchiveType.Day:
            return M4ArchiveId.Day
        elif at == ArchiveType.Month:
            return M4ArchiveId.Mon
        elif at == ArchiveType.Control:
            return M4ArchiveId.Ctrl
        else:
            raise Exception("get_ar_code: неподдерживаемый тип архива")

    def read_interval_archive_4m(self, m: Logika4M, nt, ar: IntervalArchive, start, end, state, progress):
        mtd = self.get_meter_instance(m if isinstance(m, Logika4) else None, nt)
        rs = state

        archive_code = self.get_ar_code(ar.ArchiveType)

        ch_start = rs.ar_def.channel_def.start
        ch_end = rs.ar_def.channel_def.start + rs.ar_def.channel_def.count - 1
        if rs.current_channel is None:
            rs.current_channel = ch_start
            rs.n_ch_recs_read = 0

        t_start = rs.t_ptr if rs.t_ptr != datetime.min else start

        self.read_archive_m4(m, nt, 0, M4.PARTITION_CURRENT, rs.current_channel, archive_code, t_start, end, 64, data, next_ptr)

        for r in data:
            self.fix_intv_timestamp(r, ar.ArchiveType, mtd)

            row = ar.table.rows.find(r.dt)
            if row is None:
                row = ar.table.rows.add(r.dt)
            oa = row.item_array

            idst = 1 + len(rs.field_defs) * (rs.current_channel - ch_start)
            oa[idst:idst + len(r.values)] = r.values

            row.item_array = oa
            rs.n_ch_recs_read += 1

        data_start = ar.table.rows[0].item_array[0] if len(ar.table.rows) > 0 else start
        intv_count = int((end - data_start).ticks / ar.ArchiveType.Interval)
        total_intervals_per_ch = min(rs.ar_def.capacity, intv_count)
        total_rec_parts = total_intervals_per_ch * rs.ar_def.channel_def.count
        n_parts = (rs.current_channel - ch_start) * total_intervals_per_ch + rs.n_ch_recs_read
        progress = min(100.0, 100.0 * n_parts / total_rec_parts)

        rs.t_ptr = next_ptr

        if next_ptr == datetime.min or next_ptr > end:
            rs.t_ptr = datetime.min
            rs.n_ch_recs_read = 0
            rs.current_channel += 1

        has_more_data = rs.current_channel <= ch_end and rs.t_ptr <= end
        return has_more_data

    @staticmethod
    def archive_rec_to_service_rec(mtr: Logika4M, at: ArchiveType, channel: int, aRec: M4ArchiveRecord) -> ServiceRecord:
        sEvent = str(aRec.values[0])
        eventDesc = None
        if at == ArchiveType.ErrorsLog:
            eventDesc = mtr.get_ns_description(sEvent)

        if channel > 0:
            sEvent = str(channel) + "-" + sEvent

        return ServiceRecord(aRec.dt, sEvent, eventDesc)

    def get_device_clock(self, meter: Meter, src, dst) -> datetime:
        mtd = self.get_meter_instance(meter if isinstance(meter, Logika4) else None, dst)
        return mtd.current_device_time

    def read_service_archive(self, m, srcNt, nt, ar, start, end, state, progress):
        if not ar.ArchiveType.IsServiceArchive:
            raise ValueError("wrong archive type")

        if isinstance(m, Logika4M):
            return self.read_service_archive_4M(m, nt, ar, start, end, state, progress)

        elif isinstance(m, Logika4L):
            return self.read_flash_archive_4L(m, nt, ar, start, end, state, progress)

        else:
            raise ValueError("wrong meter type")

    def read_service_archive_4M(self, m: Logika4M, nt, ar: ServiceArchive, start: datetime, end: datetime, state, progress):
        if ar.ArchiveType == ArchiveType.ParamsLog:
            archive_code = M4ArchiveId.ParamsLog
        elif ar.ArchiveType == ArchiveType.ErrorsLog:
            archive_code = M4ArchiveId.NSLog
        else:
            raise Exception("unsupported archive type")

        m4m = m if isinstance(m, Logika4M) else None
        ard = next((x for x in m.Archives if x.ArchiveType == ar.ArchiveType), None)
        if ard is None:
            raise ValueError("Archive definition not found")

        ch_start = ard.ChannelDef.Start
        ch_end = ard.ChannelDef.Start + ard.ChannelDef.Count - 1

        t_ptr = state if state is not None else datetime.min

        next_ptrs = [datetime.min] * ard.ChannelDef.Count
        t_start = t_ptr if t_ptr != datetime.min else start
        tmp_list = []

        for ch in range(ch_start, ch_end + 1):
            data, next_ptr = self.read_archive_m4(m4m, nt, 0, M4.PARTITION_CURRENT, ch, archive_code, t_start, end, 64)
            for r in data:
                evt = self.archive_rec_to_service_rec(m4m, ar.ArchiveType, ch, r)
                tmp_list.append(evt)
            next_ptrs[ch - ch_start] = next_ptr

        t_ptr = datetime.min
        for np in next_ptrs:
            if np != datetime.min and np > t_ptr:
                t_ptr = np

        ar.Records.extend(tmp_list)

        first_rec_time = ar.Records[0].tm if ar.Records else start

        state = t_ptr
        if t_ptr == datetime.min:
            progress = 100
        else:
            progress = ((t_ptr - first_rec_time).total_seconds() * 100) / (end - first_rec_time).total_seconds()

        return t_ptr != datetime.min and t_ptr < end
