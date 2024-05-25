import time
from datetime import datetime, timedelta, timezone
from enum import Enum, IntEnum
from typing import List

from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.SerialConnection import BaudRate, SerialConnection
from Logika.ECommException import ECommException, CommError, ExcSeverity
from Logika.LogLevel import LogLevel
from Logika.Meters.Archive import IntervalArchive, ServiceArchive, ServiceRecord, Archive
from Logika.Meters.ArchiveDef import ArchiveDef4L
from Logika.Meters.ArchiveField import ArchiveField
from Logika.Meters.Channel import ChannelKind
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Meter import Meter
from Logika.Meters.TagDef import TagDef4L, TagDef4M
from Logika.Meters.Types import TagKind, ImportantTag, ArchiveType
from Logika.Meters.__4L.Logika4L import Logika4L, BinaryType
from Logika.Meters.__4L.SPG741 import TSPG741
from Logika.Meters.__4M.Logika4M import Logika4M, OperParamFlag
from Logika.Protocols.M4.ErrorCode import ErrorCode
from Logika.Protocols.M4.FlashArchive4L import AsyncFlashArchive4, Logika4LArchiveRequestState, SyncFlashArchive4, \
    Logika4LTVReadState
from Logika.Protocols.M4.M4ArchiveId import M4ArchiveId
from Logika.Protocols.M4.M4ArchiveRecord import M4ArchiveRecord
from Logika.Protocols.M4.M4Opcode import M4Opcode
from Logika.Protocols.M4.M4Packet import M4Packet
from Logika.Protocols.M4.TagWriteData import TagWriteData
from Logika.Protocols.Protocol import Protocol, ProtoEvent


class MeterInstance:
    def __init__(self, owner: 'M4Protocol', m: Logika4, nt):
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
        self.proto.update_tags(self.nt, rdta, updTagsFlags.DontGetEUs)
        self.rd = int(rdta[0].Value)
        self.rh = int(rdta[1].Value)

    @property
    def eu_dict(self):
        if self.eus is None:
            if ImportantTag.EngUnits in self.vipTags:
                self.proto.update_tags(self.nt, self.vipTags[ImportantTag.EngUnits], updTagsFlags.DontGetEUs)
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
            self.proto.update_tags(self.nt, dta, updTagsFlags.DontGetEUs)
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


class M4_MeterChannel(Enum):
    SYS = 0
    TV1 = 1
    TV2 = 2


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


class RecvFlags(IntEnum):
    DontThrowOnErrorReply = 0x01,


class CompressionType(IntEnum):
    FLZLimitedLength = 0x10


class _busActivePtr:
    def __init__(self, mtr, nt, tv):
        if mtr is None:
            raise ValueError()
        self.meter = mtr
        self.nt = nt
        self.tv = tv
        self.lastIOTime = None
        self.ioError = False

    @property
    def tsFromLastIO(self) -> datetime | None:
        if self.lastIOTime is not None:
            return datetime.now() - self.lastIOTime
        return None


class M4Protocol(Protocol):
    BROADCAST = 0xFF  # NT for broadcast requests
    FRAME_START = 0x10
    FRAME_END = 0x16
    EXT_PROTO = 0x90
    MAX_RAM_REQUEST = 0x40
    MAX_TAGS_AT_ONCE = 24
    PARTITION_CURRENT = 0xFFFF
    ALT_SPEED_FALLBACK_TIME = 10000
    WAKEUP_SEQUENCE: bytearray = bytearray(
        [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
         0xFF,
         0xFF])
    WAKE_SESSION_DELAY: int = 100

    MAX_PAGE_BLOCK = 8

    def __init__(self, targetBaudrate=BaudRate.Undefined):
        super().__init__()
        self.activeDev = None
        self.initialBaudRate = None
        self.suggestedBaudrate = targetBaudrate
        self.metadataCache = None
        self.CHANNEL_NBASE = 10000
        self.id_ctr: int = 0
        self.extra_data: object = None
        self.op_flags: List[bool] = []
        self.next_record: datetime = datetime.now()
        self.state = None
        self.progress = None
        self.result: List[M4ArchiveRecord] = []
        self.next_ptr: datetime = datetime.now()

    def reset_internal_bus_state(self):
        self.activeDev = None
        self.serial_conn_speed_fallback()
        self.log(LogLevel.Trace, "M4 bus state is reset")

    def send_attention(self, slow_wake: bool):
        self.connection.PurgeComms(PurgeFlags.RX | PurgeFlags.TX)
        if slow_wake:
            for byte in self.WAKEUP_SEQUENCE:
                self.connection.write([byte])
                time.sleep(0.02)
        else:
            self.connection.write(self.WAKEUP_SEQUENCE)

    def internal_close_comm_session(self, not_used: bytes, nt: bytes):
        self.do_legacy_request(nt, M4Opcode.SessionClose, bytearray(4),0, RecvFlags.DontThrowOnErrorReply)
        # в зависимости от ответа bsu поправить также и старый пролог

    @staticmethod
    def gen_raw_handshake(dest_nt: bytes):
        hsArgs = [0, 0, 0, 0]
        pBuf: bytearray = bytearray()
        pBuf[0] = M4Protocol.FRAME_START
        pBuf[1] = dest_nt if dest_nt else M4Protocol.BROADCAST
        pBuf[2] = M4Opcode.Handshake.value

        pBuf[3 + len(hsArgs)] = Logika4.checksum8(pBuf, 1, len(hsArgs) + 2)
        pBuf[3 + len(hsArgs) + 1] = M4Protocol.FRAME_END

        return pBuf

    def serial_conn_speed_fallback(self):
        sc = self.connection
        if isinstance(sc, SerialConnection) and self.initialBaudRate != BaudRate.Undefined:
            if sc.BaudRate != self.initialBaudRate:
                sc.BaudRate = self.initialBaudRate
                self.log(LogLevel.Debug, f"восстановлена начальная скорость обмена {int(self.initialBaudRate)} bps")

    def select_device_and_channel(self, mtr: Logika4, z_nt: bytes, tv: int = M4_MeterChannel.SYS):
        if mtr is None:
            raise ValueError()

        nt = z_nt if z_nt else self.BROADCAST

        if self.activeDev and self.activeDev.tsFromLastIO > self.activeDev.get_meter.SessionTimeout:
            self.reset_internal_bus_state()

        if isinstance(self.connection, SerialConnection):
            if self.suggestedBaudrate != BaudRate.Undefined and self.initialBaudRate == BaudRate.Undefined:
                self.initialBaudRate = BaudRate

            if self.activeDev and self.activeDev.tsFromLastIO.total_seconds() >= self.ALT_SPEED_FALLBACK_TIME:
                self.serial_conn_speed_fallback()

        reselectRequired = (not self.activeDev or self.activeDev.nt != nt or self.activeDev.tv != tv or
                            self.activeDev.ioError)

        if reselectRequired:
            if self.activeDev:
                self.activeDev.ioError = False

            alreadyAwake = self.activeDev and self.activeDev.nt == nt
            slowFFs = not mtr.supports_fast_session_init and not alreadyAwake
            hsPkt = self.handshake(nt, bytearray(tv), slowFFs)

            detectedType = Logika4.MeterTypeFromResponse(hsPkt.Data[0], hsPkt.Data[1], hsPkt.Data[2])
            if detectedType != mtr:
                self.reset_internal_bus_state()
                raise ECommException(ExcSeverity.Stop, CommError.Unspecified,
                                     f"Несоответствие типа прибора. Ожидаемый тип прибора: {mtr.Caption}, фактический: {detectedType.Caption} (NT={nt})")

            self.activeDev = _busActivePtr(mtr, nt, tv)
            self.activeDev.lastIOTime = datetime.now()

    def get_meter_type(self, src_nt: bytes, dst_nt: bytes):
        hsPkt = self.handshake(dst_nt, bytearray(0), False)
        self.extra_data = hsPkt.Data[2]

        return Logika4.meter_type_from_response(hsPkt.Data[0], hsPkt.Data[1], hsPkt.Data[2])

    def get_meter_instance(self, m, nt):
        _nt = nt if nt is not None else 0xFF

        if _nt not in self.metadataCache:
            mi = MeterInstance(self, m, _nt)
            self.metadataCache[_nt] = mi
        else:
            mi = self.metadataCache[_nt]

        return mi

    def handshake(self, nt: bytes, channel: bytearray, bSlowFFs: bool):
        if self.activeDev and nt != self.activeDev.nt:
            self.reset_internal_bus_state()

        self.send_attention(bSlowFFs)
        time.sleep(0.1)
        self.connection.purge_comms(PurgeFlags.RX)

        req_data = bytearray([channel, 0, 0, 0])
        return self.do_legacy_request(nt, M4Opcode.Handshake, req_data, 3)

    def do_legacy_request(self, nt: bytes, req_func: M4Opcode, data: bytearray, expected_data_len: int, flags: RecvFlags=0):
        self.send_legacy_packet(nt, req_func, data)
        return self.recv_packet(nt, req_func, bytearray(), expected_data_len, flags)

    def do_m4_request(self, nt: bytes, req_func: M4Opcode, data: bytearray, pktId: bytes=None, flags: RecvFlags=0):
        if pktId is None:
            pktId = self.id_ctr
            self.id_ctr += 1
        self.send_extended_packet(nt, pktId, req_func, data)
        p = self.recv_packet(nt, req_func, bytearray(pktId), 0, flags)
        return p

    def recv_packet(self, expected_nt: bytes, expected_opcode: M4Opcode, expected_id: bytearray, expectedDataLength: int,
                    flags: RecvFlags=0):
        buf = [0] * 8
        check = [0] * 2
        p = M4Packet()
        try:
            while True:
                readStartTime = time.time()
                while True:
                    self.connection.read(buf, 0, 1)
                    if buf[0] == M4Protocol.FRAME_START:
                        break

                    elapsed = time.time() - readStartTime
                    if elapsed > self.connection.read_timeout:
                        self.on_recoverable_error()
                        raise ECommException(ExcSeverity.Error, CommError.Timeout)

                self.connection.read(buf, 1, 2)
                p.NT = buf[1]
                p.FunctionCode = M4Opcode(buf[2])

                if expected_nt and p.NT != expected_nt:
                    continue

                if (expected_opcode and
                        p.FunctionCode != expected_opcode and
                        p.FunctionCode != M4Opcode.Error and
                        p.FunctionCode != M4Protocol.EXT_PROTO):
                    if expected_opcode == M4Opcode.ReadFlash:
                        self.on_recoverable_error()
                        raise ECommException(ExcSeverity.Error, CommError.Unspecified,
                                             "нарушение последовательности обмена")
                    continue

                if p.FunctionCode == M4Protocol.EXT_PROTO:
                    p.Extended = True
                    self.connection.read(buf, 3, 5)
                    p.ID = buf[3]
                    p.Attributes = buf[4]
                    payload_len = buf[5] + (buf[6] << 8)
                    p.Data = [0] * (payload_len - 1)
                    p.FunctionCode = M4Opcode(buf[7])
                    if expected_opcode and p.FunctionCode != expected_opcode and p.FunctionCode != M4Opcode.Error:
                        continue

                    if expected_id and p.ID != expected_id:
                        self.log(LogLevel.Warn,
                                 f"нарушение порядка обмена: ожидаемый ID пакета: 0x{expected_id:X2}, принятый: 0x{p.ID:X2}")

                else:
                    p.Extended = False
                    if p.FunctionCode == M4Opcode.Error:
                        p.Data = [0]
                    else:
                        p.Data = [0] * expectedDataLength

                self.connection.read(p.Data, 0, len(p.Data))
                self.connection.read(check, 0, 2)
                if p.Extended:
                    p.Check = (check[0] << 8) | check[1]
                else:
                    p.Check = check[0] | (check[1] << 8)

                if self.activeDev:
                    self.activeDev.lastIOTime = datetime.now()

                break

        except Exception:
            self.on_recoverable_error()
            raise

        calculatedCheck = 0

        if p.Extended:
            Protocol.crc16(calculatedCheck, buf, 1, 7)
            Protocol.crc16(calculatedCheck, p.Data, 0, len(p.Data))
        else:
            calculatedCheck = 0x1600
            calculatedCheck |= (~Logika4.Checksum8(buf, 1, 2) + ~Logika4.Checksum8(p.Data, 0, len(p.Data)))

        if p.Check != calculatedCheck:
            self.report_proto_event(ProtoEvent.rxCrcError)
            raise ECommException(ExcSeverity.Error, CommError.Checksum)

        self.report_proto_event(ProtoEvent.packetReceived)

        if p.FunctionCode == M4Opcode.Error:
            ec = ErrorCode(p.Data[0])
            self.report_proto_event(ProtoEvent.genericError)
            if not flags & RecvFlags.DontThrowOnErrorReply:
                raise ECommException(ExcSeverity.Error, CommError.Unspecified, f"прибор вернул код ошибки: {ec.value}")

        return p

    def set_bus_speed(self, mtr: Logika4, nt: bytes, baud_rate: BaudRate, tv: M4_MeterChannel=M4_MeterChannel.SYS):
        serialConn = self.connection
        if not isinstance(serialConn, SerialConnection):
            raise Exception("смена скорости недопустима на соединениях отличных от 'Serial'")

        m4BaudRates = [2400, 4800, 9600, 19200, 38400, 57600, 115200]
        nbr = m4BaudRates.index(int(baud_rate))
        if nbr < 0:
            raise ECommException(ExcSeverity.Stop, CommError.Unspecified,
                                 "запрошенная скорость обмена не поддерживается")

        prevBaudRate = serialConn.BaudRate
        changedOk = False
        devAcksNewBR = False
        self.log(LogLevel.Info, f"установка скорости обмена {int(baud_rate)} bps")
        try:
            rsp = self.do_legacy_request(nt, M4Opcode.SetSpeed, bytearray([nbr, 0, 0, 0]), 0, RecvFlags.DontThrowOnErrorReply)
            if rsp.FunctionCode == M4Opcode.SetSpeed:
                devAcksNewBR = True
                time.sleep(0.25)
                self.connection.PurgeComms(PurgeFlags.RX | PurgeFlags.TX)

                serialConn.BaudRate = baud_rate
                rsp = self.do_legacy_request(nt, M4Opcode.Handshake, bytearray([tv, 0, 0, 0]), 3, RecvFlags.DontThrowOnErrorReply)
                changedOk = rsp.FunctionCode == M4Opcode.Handshake

        except ECommException as ece:
            if ece.Reason != CommError.Timeout and ece.Reason != CommError.Checksum:
                raise
            changedOk = False

        if not changedOk:
            msg = "ошибка"
            if devAcksNewBR:
                msg += ", восстанавливаем предыдущую скорость обмена..."
            self.log(LogLevel.Warn, msg)
            serialConn.BaudRate = prevBaudRate
            if devAcksNewBR:
                time.sleep(int(self.ALT_SPEED_FALLBACK_TIME * 1.1))
                self.log(LogLevel.Info, f"восстановлена скорость обмена {int(prevBaudRate)} bps")
        return changedOk

    def send_legacy_packet(self, nt: bytes, func: M4Opcode, data: bytes):
        pkt = M4Packet()
        pBuf = bytearray(3 + len(data) + 2)

        pBuf[0] = self.FRAME_START
        pBuf[1] = nt if nt is not None else self.BROADCAST
        pBuf[2] = func.value

        pBuf[3:3 + len(data)] = data
        pBuf[3 + len(data)] = Logika4.Checksum8(pBuf, 1, len(data) + 2)
        pBuf[3 + len(data) + 1] = self.FRAME_END

        pktTotalLen = 3 + len(data) + 2
        self.connection.write(pBuf, 0, pktTotalLen)

        self.report_proto_event(ProtoEvent.packetTransmitted)

    def write_parameter_l4(self, mtr: Logika4L, nt: bytes, channel: bytes, nParam: int, value: str, oper_flag: bool):
        if isinstance(mtr, TSPG741) and 200 <= nParam < 300:
            td = Meter.SPG741.Tags.All.SingleOrDefault(lambda x: x.Ordinal == nParam)
            sp = self.get741sp(nt)
            mappedOrdinal = TSPG741.GetMappedDBParamOrdinal(td.key, sp)
            if mappedOrdinal is None:
                return None
            else:
                nParam = mappedOrdinal

        self.select_device_and_channel(mtr, nt, int(channel))
        if channel == 1 or channel == 2:
            nParam -= 50

        reqData = bytearray([nParam & 0xFF, (nParam >> 8) & 0xFF, 0, 0])
        pkt = self.do_legacy_request(nt, M4Opcode.WriteParam, reqData, 0, RecvFlags.DontThrowOnErrorReply)

        if pkt.FunctionCode == M4Opcode.Error:
            return ErrorCode(pkt.Data[0])

        reqData = bytearray(64)
        for i in range(len(reqData)):
            if i < len(value):
                reqData[i] = ord(value[i])
            else:
                reqData[i] = 0x20

        if oper_flag is not None:
            reqData[-1] = ord('*') if oper_flag else 0x00

        pkt = self.do_legacy_request(nt, M4Opcode.WriteParam, reqData, 0, RecvFlags.DontThrowOnErrorReply)
        if pkt.FunctionCode == M4Opcode.Error:
            return ErrorCode(pkt.Data[0])

        return None

    @staticmethod
    def get_legacy_response_data_len(functionCode: M4Opcode):
        if functionCode == M4Opcode.Handshake:
            return 3
        elif functionCode == M4Opcode.Error:
            return 1
        elif functionCode == M4Opcode.ReadFlash:
            return Logika4L.FLASH_PAGE_SIZE
        elif functionCode == M4Opcode.WriteParam:
            return 0
        elif functionCode == M4Opcode.SetSpeed:
            return 0
        else:
            return None

    def get741sp(self, nt: bytes):
        mmd = self.get_meter_instance(Meter.SPG741, nt)
        if mmd.sp is None:
            SP_741_ADDR = 0x200
            self.get_flash_pages_to_cache(Meter.SPG741, nt, SP_741_ADDR // Logika4L.FLASH_PAGE_SIZE, 1, mmd)
            mmd.sp = int(Logika4L.get_value(BinaryType.dbentry, mmd.flash, SP_741_ADDR, False))
        return mmd.sp

    def read_ram(self, mtr: Logika4L, nt: bytes, start_addr: int, nBytes: int):
        if nBytes > self.MAX_RAM_REQUEST:
            raise ValueError("too much data requested from RAM")

        self.select_device_and_channel(mtr, nt)

        reqData = bytearray([start_addr & 0xFF, (start_addr >> 8) & 0xFF, nBytes, 0])
        pkt = self.do_legacy_request(nt, M4Opcode.ReadRam, reqData, nBytes)

        return pkt.Data

    def read_flash_pages(self, mtr: Logika4L, nt: bytes, start_page: int, page_count: int) -> bytearray:
        if page_count <= 0:
            raise ValueError("ReadFlashPages: zero page count")

        self.select_device_and_channel(mtr, nt)
        cmdbuf: bytearray

        retbuf: bytearray = bytearray(page_count * Logika4L.FLASH_PAGE_SIZE)

        for p in range((page_count + self.MAX_PAGE_BLOCK - 1) // self.MAX_PAGE_BLOCK):
            pages_to_req = page_count - p * self.MAX_PAGE_BLOCK
            if pages_to_req > self.MAX_PAGE_BLOCK:
                pages_to_req = self.MAX_PAGE_BLOCK
            page_block_start = start_page + p * self.MAX_PAGE_BLOCK

            reqData = bytearray([page_block_start & 0xFF, (page_block_start >> 8) & 0xFF, pages_to_req, 0])
            self.send_legacy_packet(nt, M4Opcode.ReadFlash, reqData)

            for i in range(pages_to_req):
                try:
                    pkt = self.recv_packet(nt, M4Opcode.ReadFlash, bytearray(), Logika4L.FLASH_PAGE_SIZE)
                except:
                    if page_count > 1:
                        self.on_recoverable_error()
                    raise

                if pkt.FunctionCode != M4Opcode.ReadFlash or len(pkt.Data) != Logika4L.FLASH_PAGE_SIZE:
                    raise ECommException(ExcSeverity.Error, CommError.Unspecified,
                                         f"принят некорректный пакет, код функции 0x{pkt.FunctionCode:X2}")

                start_index: int = (p * self.MAX_PAGE_BLOCK + i) * Logika4L.FLASH_PAGE_SIZE
                end_index: int = start_index + Logika4L.FLASH_PAGE_SIZE
                retbuf[start_index:end_index] = pkt.Data[0:Logika4L.FLASH_PAGE_SIZE]

        return retbuf

    def on_recoverable_error(self):
        if self.activeDev is not None:
            self.activeDev.ioError = True

    def read_flash_bytes(self, mtr: Logika4L, nt: bytes, start_addr: int, length: int) -> bytearray:
        if length <= 0:
            raise ValueError("read length invalid")

        StartPage = start_addr // Logika4L.FLASH_PAGE_SIZE
        EndPage = (start_addr + length - 1) // Logika4L.FLASH_PAGE_SIZE
        PageCount = EndPage - StartPage + 1
        mem = self.read_flash_pages(mtr, nt, StartPage, PageCount)
        retbuf = bytearray(length)
        retbuf[:length] = mem[start_addr % Logika4L.FLASH_PAGE_SIZE:start_addr % Logika4L.FLASH_PAGE_SIZE + length]

        return retbuf

    def send_extended_packet(self, nt: bytes, packet_id: bytes, opcode: M4Opcode, data: bytearray):
        CRC_LEN = 2
        HDR_LEN = 8

        buf = bytearray(HDR_LEN + len(data) + CRC_LEN)

        buf[0] = self.FRAME_START
        buf[1] = nt if nt is not None else self.BROADCAST
        buf[2] = 0x90
        buf[3] = packet_id[0]
        buf[4] = 0x00

        payload_len = 1 + len(data)
        buf[5] = payload_len & 0xFF
        buf[6] = payload_len >> 8

        buf[7] = opcode.value
        buf[8:] = data

        check = 0
        Protocol.crc16(check, buf, 1, HDR_LEN - 1 + len(data))
        buf[HDR_LEN + len(data)] = check >> 8
        buf[HDR_LEN + len(data) + 1] = check & 0xFF

        self.connection.write(buf, 0, len(buf))
        self.report_proto_event(ProtoEvent.packetTransmitted)

    def read_tags_m4(self, m: Logika4M, nt: bytes, channels: List[int], ordinals: List[int]):
        self.select_device_and_channel(m, nt)
        if channels is None or len(channels) == 0 or ordinals is None or len(ordinals) == 0 or len(channels) != len(
                ordinals):
            raise ValueError("некорректные входные параметры функции readTagsM4")

        lb = bytearray()
        for i in range(len(ordinals)):
            ch = ordinals[i] // self.CHANNEL_NBASE if ordinals[i] >= self.CHANNEL_NBASE else channels[i]
            ordinal = ordinals[i] % self.CHANNEL_NBASE
            self.append_pnum(lb, ch, ordinal)

        p = self.do_m4_request(nt, M4Opcode.ReadTags, lb)
        lb.clear()

        oa = self.parse_m4_tags_packet(p)

        if m == Meter.SPG742 or m == Meter.SPT941_20:
            for i in range(len(ordinals)):
                if ordinals[i] == 8256 and isinstance(oa[i], int):
                    oa[i] = int(str(oa[i])) & 0x00FFFFFF

        return oa

    def parse_m4_tags_packet(self, p: M4Packet):
        if not p.Extended or p.FunctionCode != M4Opcode.ReadTags:
            raise ValueError("некорректный пакет")

        valuesList: List[object] = []
        opFlagsList: List[bool] = []

        tp = 0
        while tp < len(p.Data):
            o = None
            tag_len = Logika4M.parse_tag(p.Data, tp, o)

            if isinstance(o, OperParamFlag):
                opFlagsList[-1] = True if o == OperParamFlag.Yes else False
                tp += tag_len
                continue

            valuesList.append(o)
            opFlagsList.append(False)

            tp += tag_len

        self.op_flags.extend(opFlagsList)

        return valuesList

    @staticmethod
    def append_pnum(lb: bytearray, channel: int, ordinal: int):
        lb.append(0x4A)
        lb.append(0x03)

        lb.append(channel)
        lb.append(ordinal & 0xFF)
        lb.append((ordinal >> 8) & 0xFF)

    def write_params_m4(self, mtr: Logika4M, nt: bytes, wda: List[TagWriteData]):
        self.select_device_and_channel(mtr, nt)

        lb = bytearray()
        for twd in wda:
            v = twd.value

            ch = twd.channel if twd.ordinal < self.CHANNEL_NBASE else twd.ordinal // self.CHANNEL_NBASE
            ordinal = twd.ordinal % self.CHANNEL_NBASE
            self.append_pnum(lb, ch, ordinal)

            if v is None or (isinstance(v, str) and len(v) == 0):
                lb.extend([0x05, 0])
            elif isinstance(v, str):
                lb.extend([0x16, len(v)])
                lb.extend([ord(c) for c in v])
            elif isinstance(v, int):
                lb.extend([0x41, 0x04])
                buf = v.to_bytes(4, 'little')
                lb.extend(buf)
            elif isinstance(v, bytes):
                lb.append(0x04)
                ba = v
                if len(ba) < 0x80:
                    lb.append(len(ba))
                elif len(ba) < 0x10000:
                    lb.extend([0x82, len(ba) & 0xFF, len(ba) >> 8])
                else:
                    raise Exception("octet string too large")

                lb.extend(ba)
            else:
                raise Exception("неподдерживаемый тип данных в запросе записи переменной")

            if twd.oper is not None:
                lb.extend([0x45, 0x01, 0x01] if twd.oper else [0x45, 0x01, 0x00])

        p = self.do_m4_request(nt, M4Opcode.WriteTags, lb)
        errors = []

        tp = 0
        for i in range(len(wda)):
            tID = p.Data[tp]
            tagLength = p.Data[tp + 1]
            if tID == 0x46:
                tagLength = 0
                errors[i] = None
            elif tID == 0x55:
                errors[i] = p.Data[tp + 2]
            else:
                errors[i] = 0xFF
            tp += 2 + tagLength

        return errors

    @staticmethod
    def restrict_time(dt: datetime):
        if dt != datetime.min:
            y = dt.year - 2000
            if y < 0:
                return datetime(2000, 1, 1, 0, 0, 0, 0, dt.tzinfo)
            elif y > 255:
                return datetime(2255, 1, 31, 23, 59, 59, 999, dt.tzinfo)
        return dt

    @staticmethod
    def append_date_tag(lb: bytearray, dt: datetime, use_year_and_month_only: bool):
        lb.append(0x49)
        lb.append(2 if use_year_and_month_only else 8)
        lb.append(dt.year - 2000)
        lb.append(dt.month)
        if not use_year_and_month_only:
            lb.extend([dt.day, dt.hour, dt.minute, dt.second, dt.microsecond & 0xFF, dt.microsecond >> 8])

    def read_archive_m4(self, mtr: Logika4M, nt: bytes, pktId: bytes, partition: int, channel: bytes, archiveKind: M4ArchiveId, from_dt: datetime, to_dt: datetime, numValues: int):
        self.select_device_and_channel(mtr, nt)

        from_dt = self.restrict_time(from_dt)
        to_dt = self.restrict_time(to_dt)
        if to_dt != datetime.min and from_dt > to_dt:
            self.result = M4ArchiveRecord()
            self.next_record = datetime.min
            raise ValueError("протокол M4 не поддерживает чтение в обратном порядке")

        lb: bytearray = bytearray([0x04, 0x05, partition & 0xFF, partition >> 8, channel, archiveKind])
        if mtr.SupportsFLZ:
            compFlags_archId = archiveKind.value | CompressionType.FLZLimitedLength
            lb.append(compFlags_archId)
        if numValues > 0xFF:
            numValues = 0xFF
        lb.append(numValues)
        self.append_date_tag(lb, from_dt, False)
        if to_dt != datetime.min:
            self.append_date_tag(lb, to_dt, False)

        p = self.do_m4_request(nt, M4Opcode.ReadArchive, lb, pktId)
        lb.clear()

        self.result = self.parse_archive_packet(p)

        return p

    def parse_archive_packet(self, p: M4Packet):
        if not p.Extended or p.FunctionCode != M4Opcode.ReadArchive:
            raise ValueError("некорректный пакет")

        lr: List[M4ArchiveRecord] = []
        self.next_record = datetime.min

        zLen, oFirstTag = Logika4M.parse_tag(p.Data, 0)
        decomp_data: bytearray = bytearray()

        if isinstance(oFirstTag, bytes):
            tailLength = len(p.Data) - zLen
            decompRecords = FLZ.decompress(oFirstTag, 0, len(oFirstTag))
            decomp_data = bytearray(decompRecords) + p.Data[zLen:]
        else:
            decomp_data = p.Data

        decomp_data = p.Data
        tp = 0
        sum_tp: int = 0
        while tp < len(decomp_data):
            tp, oTime = Logika4M.parse_tag(decomp_data, tp)
            sum_tp += tp

            lenLen = Logika4M.get_tag_length(decomp_data, sum_tp + 1)
            recLen = lenLen[1]

            if recLen == 0:
                self.next_record = oTime
                break

            r = M4ArchiveRecord()
            r.interval_mark = datetime(oTime, tzinfo=timezone.utc)

            if decomp_data[sum_tp] == 0x30:
                sum_tp += 1 + lenLen[0]

                st = sum_tp

                lo = []
                while sum_tp - st < recLen:
                    tp, o = Logika4M.parse_tag(decomp_data, sum_tp)
                    sum_tp += tp
                    lo.append(o)

                if isinstance(lo[0], str) and isinstance(lo[1], str) and len(lo[0]) == 8 and len(lo[1]) == 8:
                    ta = lo[0].split('-') + lo[0].split(':')
                    da = lo[1].split('-')
                    r.dt = datetime(2000 + int(da[2]), int(da[1]), int(da[0]), int(ta[0]), int(ta[1]),
                                    int(ta[2]), tzinfo=timezone.utc)
                    lo = lo[2:]
                else:
                    r.dt = datetime.min

                r.values = lo
            else:
                tp, o = Logika4M.parse_tag(decomp_data, sum_tp)
                sum_tp += tp
                r.dt = r.interval_mark
                r.values = [o]

            lr.append(r)

        if self.next_record != datetime.min and len(lr) > 0 and self.next_record <= lr[-1].dt:
            raise ECommException(ExcSeverity.Stop, CommError.Unspecified, "зацикливание датировки архивных записей")

        return lr

    def get_device_clock(self, meter: Meter, src: bytes, dst: bytes) -> datetime:
        mtd = self.get_meter_instance(meter if isinstance(meter, Logika4) else None, dst)
        return mtd.current_device_time

    def update_tags(self, src, dst, tags: List[DataTag]):
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
                pg = self.read_flash_pages(mtr, nt, st, ct)
                mi.flash[st * Logika4L.FLASH_PAGE_SIZE: (st + ct) * Logika4L.FLASH_PAGE_SIZE] = pg
                for f in range(ct):
                    mi.pageMap[st + f] = True

    def get4L_real_addr(self, mi: MeterInstance, t: DataTag):
        deffinition = t.deffinition
        if mi.mtr == Meter.SPG741 and 200 <= deffinition.Ordinal < 300:
            return TSPG741.get_mapped_db_param_addr(mi.mtr, deffinition.key, self.get741sp(mi.nt))
        else:
            return deffinition.address + (deffinition.channelOffset if t.Channel.No == 2 else 0)

    def update4L_tags_values(self, nt: bytes, tags: List[DataTag], mi: MeterInstance, flags: updTagsFlags):
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

            if updTagsFlags.DontGetEUs not in flags:
                t.EU = Logika4.get_eu(mi.eu_dict, def_.Units)

            t.TimeStamp = datetime.now()

            self.post_process_value(t)

    @staticmethod
    def post_process_value(t: DataTag):
        if t.deffinition.Meter == Meter.SPT941_10 and t.Name.lower() == "model" and t.Value is not None and len(
                str(t.Value)) == 1:
            t.Value = "1" + str(t.Value)

    def invalidate_flash_cache4L(self, nt: bytes, tags: List[DataTag]):
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

    def update_tags4M(self, nt: bytes, tags: List[DataTag], mi: MeterInstance, flags: updTagsFlags):
        mtr = tags[0].deffinition.Meter if isinstance(tags[0].deffinition.Meter, Logika4M) else None

        chs = []
        ords = []
        blkSt = 0

        for t in tags:
            td = t.deffinition if isinstance(t.deffinition, TagDef4M) else None
            chs.append(t.Channel.No)
            ords.append(t.Ordinal)

            if len(ords) == self.MAX_TAGS_AT_ONCE or t == tags[-1]:
                va, opFlags = self.read_tags_m4(mtr, nt, chs, ords)
                for z in range(len(ords)):
                    vt = tags[blkSt + z]
                    vt.Value = va[z]
                    if vt.Value is None:
                        vt.ErrorDesc = Logika4M.ND_STR
                    if updTagsFlags.DontGetEUs not in flags:
                        vt.EU = Logika4.get_eu(mi.eu_dict, td.Units)
                    vt.Oper = opFlags[z]
                    vt.TimeStamp = datetime.now()

                blkSt += len(ords)
                chs.clear()
                ords.clear()

    def read_interval_archive_def(self, m: Meter, src_nt: bytes, dst_nt: bytes, ar_type: ArchiveType):
        mtr4 = m if isinstance(m, Logika4) else None
        if not ar_type.is_interval_archive:
            raise ValueError("wrong archive type")

        ar = IntervalArchive(m, ar_type)

        mi = self.get_meter_instance(mtr4, dst_nt)

        if m == Meter.SPT942:
            tiny42 = mi.Model == "4" or mi.Model == "6"
            ard = next(x for x in m.Archives if x.archive_type == ar_type and x.poorMans942 == tiny42)
        else:
            ard = next(x for x in m.Archives if x.archive_type == ar_type)

        field_defs = [x for x in m.ArchiveFields if x.archive_type == ar_type]

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

        self.state = None
        if isinstance(m, Logika4L):
            ars = [Logika4LTVReadState() for _ in range(ard.ChannelDef.Count)]
            for i in range(ard.ChannelDef.Count):
                ars[i].headersRead = False
                ars[i].idx = -1
                ars[i].fArchive = SyncFlashArchive4(mi, ard, ard.ChannelDef.Start + i, mi)
            rs = Logika4LArchiveRequestState(ars)
            self.state = rs
        else:
            rs = Logika4MArchiveRequestState()
            rs.arDef = ard
            rs.fieldDefs = [x for x in field_defs]
            self.state = rs

        return ar

    def read_interval_archive(self, m: Meter, src_nt: bytes, nt: bytes, ar: IntervalArchive, start: datetime, end: datetime):
        if isinstance(m, Logika4L):
            return self.read_flash_archive_4L(m, nt, ar, start, end)
        elif isinstance(m, Logika4M):
            return self.read_interval_archive_4M(m, nt, ar, start, end)
        else:
            raise ValueError("wrong meter type")

    def read_flash_archive_4L(self, m: Logika4M, nt: bytes, ar: Archive | IntervalArchive | ServiceArchive, start: datetime, end: datetime, state_obj):
        state = state_obj

        PCT_HEADERS = 0  # percentage of headers to data (progress calc)
        PCT_DATA = 0

        if ar.ArchiveType.is_interval_archive:
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
                new_headers: List[int] = []
                trs.idx = fa.headers.manage_outdated_elements(True, new_headers, trs.idx)

            pct_hdr_read = 0
            if not trs.headersRead:
                finished, trs.restartPoint = fa.headers.get_element_indexes_in_range(start, end, trs.idx, trs.restartPoint, trs.indexes,
                                                       pct_hdr_read)
                if finished:
                    trs.headersRead = True
                    trs.dirtyIndexes = sorted(trs.indexes, key=lambda x: x.idx)
                    trs.dirtyIndexes_initial_count = len(trs.dirtyIndexes)
                else:
                    self.progress = i * (PCT_HEADERS + PCT_DATA) + (pct_hdr_read * PCT_HEADERS / 100.0)
                    return True

            fa.update_data(trs.dirtyIndexes)

            if len(trs.dirtyIndexes) > 0:
                if trs.dirtyIndexes_initial_count > 0:
                    pct_data_read = 100.0 * (
                            trs.dirtyIndexes_initial_count - len(trs.dirtyIndexes)) / trs.dirtyIndexes_initial_count
                    self.progress = i * (PCT_HEADERS + PCT_DATA) + PCT_HEADERS + PCT_DATA * pct_data_read / 100.0
                else:
                    self.progress = 0
                return True

        self.progress = 100

        if ar.ArchiveType.is_interval_archive:
            self.process_interval_data_4L(state, ar)
        else:
            self.process_service_archive_data_4L(state, ar)

        return False

    @staticmethod
    def process_interval_data_4L(state, ar: IntervalArchive):
        ar.Table.Rows.Clear()
        for tv in range(len(state.ars)):
            trs = state.ars[tv]

            for i in range(len(trs.indexes)):
                hdp = trs.fArchive.get_data_point(trs.indexes[i].idx)

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
                hdp = trs.fArchive.get_data_point(trs.indexes[ch].idx)
                if hdp is not None:
                    evt = str(hdp.Value)
                    desc = None
                    if trs.fArchive.archive_type == ArchiveType.ErrorsLog:
                        desc = svcArchive.Meter.GetNSDescription(evt)

                    if len(state.ars) > 1:  # devices with two TV
                        evt = str(tv + 1) + "-" + evt

                    sr = ServiceRecord(hdp.Timestamp, evt, desc)
                    svcArchive.Records.append(sr)

    def init_4L_service_archive_read_state(self, m: Logika4L, nt: bytes, arType: ArchiveType):
        mi = self.get_meter_instance(m, nt)
        ard = next(x for x in m.Archives if x.archive_type == arType)
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
    def fix_intv_timestamp(r: M4ArchiveRecord, art: ArchiveType, mtd: MeterInstance):
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

    def read_interval_archive_4M(self, m: Logika4M, nt, ar: IntervalArchive, start: datetime, end: datetime):
        mtd = self.get_meter_instance(m if isinstance(m, Logika4) else None, nt)
        rs = self.state

        archive_code = self.get_ar_code(ar.ArchiveType)

        ch_start = rs.ar_def.channel_def.start
        ch_end = rs.ar_def.channel_def.start + rs.ar_def.channel_def.count - 1
        if rs.current_channel is None:
            rs.current_channel = ch_start
            rs.n_ch_recs_read = 0

        t_start = rs.t_ptr if rs.t_ptr != datetime.min else start

        self.read_archive_m4(m, nt, bytes(0), self.PARTITION_CURRENT, rs.current_channel, archive_code, t_start, end, 64)

        for r in self.result:
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
        self.progress = min(100.0, 100.0 * n_parts / total_rec_parts)

        rs.t_ptr = self.next_ptr

        if self.next_ptr == datetime.min or self.next_ptr > end:
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

    def read_service_archive(self, m: Meter, srcNt: bytes, nt: bytes, ar: ServiceArchive, start: datetime, end: datetime):
        if not ar.ArchiveType.is_service_archive:
            raise ValueError("wrong archive type")

        if isinstance(m, Logika4M):
            return self.read_service_archive_4M(m, nt, ar, start, end)

        elif isinstance(m, Logika4L):
            return self.read_flash_archive_4L(m, nt, ar, start, end)

        else:
            raise ValueError("wrong meter type")

    def read_service_archive_4M(self, m: Logika4M, nt: bytes, ar: ServiceArchive, start: datetime, end: datetime):
        if ar.ArchiveType == ArchiveType.ParamsLog:
            archive_code = M4ArchiveId.ParamsLog
        elif ar.ArchiveType == ArchiveType.ErrorsLog:
            archive_code = M4ArchiveId.NSLog
        else:
            raise Exception("unsupported archive type")

        m4m = m if isinstance(m, Logika4M) else None
        ard = next((x for x in m.Archives if x.archive_type == ar.ArchiveType), None)
        if ard is None:
            raise ValueError("Archive definition not found")

        ch_start = ard.ChannelDef.Start
        ch_end = ard.ChannelDef.Start + ard.ChannelDef.Count - 1

        t_ptr = self.state if self.state is not None else datetime.min

        next_ptrs = [datetime.min] * ard.ChannelDef.Count
        t_start = t_ptr if t_ptr != datetime.min else start
        tmp_list = []

        for ch in range(ch_start, ch_end + 1):
            self.read_archive_m4(m4m, nt, bytes(0), self.PARTITION_CURRENT, bytes(ch), archive_code, t_start, end, 64)
            for r in self.result:
                evt = self.archive_rec_to_service_rec(m4m, ar.ArchiveType, ch, r)
                tmp_list.append(evt)
            next_ptrs[ch - ch_start] = self.next_ptr

        t_ptr = datetime.min
        for np in next_ptrs:
            if np != datetime.min and np > t_ptr:
                t_ptr = np

        ar.Records.extend(tmp_list)

        first_rec_time = ar.Records[0].tm if ar.Records else start

        self.state = t_ptr
        if t_ptr == datetime.min:
            self.progress = 100
        else:
            self.progress = ((t_ptr - first_rec_time).total_seconds() * 100) / (end - first_rec_time).total_seconds()

        return t_ptr != datetime.min and t_ptr < end
