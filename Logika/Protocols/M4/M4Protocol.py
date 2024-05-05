import time
from datetime import datetime
from enum import Enum, IntEnum
from typing import List

from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.SerialConnection import BaudRate, SerialConnection
from Logika.ECommException import ECommException, CommError, ExcSeverity
from Logika.LogLevel import LogLevel
from Logika.Meters.Archive import IntervalArchive
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Meter import Meter
from Logika.Meters.__4L.Logika4L import Logika4L
from Logika.Meters.__4L.SPG741 import TSPG741
from Logika.Meters.__4M.Logika4M import Logika4M
from Logika.Protocols.M4.ErrorCode import ErrorCode
from Logika.Protocols.M4.M4ArchiveRecord import M4ArchiveRecord
from Logika.Protocols.M4.M4Opcode import M4Opcode
from Logika.Protocols.M4.M4Packet import M4Packet
from Logika.Protocols.Protocol import Protocol, ProtoEvent


class M4_MeterChannel(Enum):
    SYS = 0
    TV1 = 1
    TV2 = 2


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

    MAX_PAGE_BLOCK = 8

    def __init__(self, targetBaudrate=BaudRate.Undefined):
        super().__init__()
        self.activeDev = None
        self.initialBaudRate = None
        self.suggestedBaudrate = targetBaudrate
        self.WAKEUP_SEQUENCE = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                                0xFF,
                                0xFF]

    def reset_internal_bus_state(self):
        self.activeDev = None
        self.serial_conn_speed_fallback()
        self.log(LogLevel.Trace, "M4 bus state is reset")

    def send_attention(self, slowWake):
        self.connection.PurgeComms(PurgeFlags.RX | PurgeFlags.TX)
        if slowWake:
            for byte in self.WAKEUP_SEQUENCE:
                self.connection.write([byte])
                time.sleep(0.02)
        else:
            self.connection.write(self.WAKEUP_SEQUENCE)

    def internal_close_comm_session(self, notUsed, nt):
        self.do_legacy_request(nt, M4Opcode.SessionClose, bytearray([0, 0, 0, 0]), 0, RecvFlags.DontThrowOnErrorReply)
        # в зависимости от ответа bsu поправить также и старый пролог

    @staticmethod
    def gen_raw_handshake(destNT):
        hsArgs = [0, 0, 0, 0]
        pBuf = [0] * (3 + len(hsArgs) + 2)
        pBuf[0] = M4Protocol.FRAME_START
        pBuf[1] = destNT if destNT else M4Protocol.BROADCAST
        pBuf[2] = M4Opcode.Handshake

        pBuf[3 + len(hsArgs)] = Logika4.Checksum8(pBuf, 1, len(hsArgs) + 2)
        pBuf[3 + len(hsArgs) + 1] = M4Protocol.FRAME_END

        return pBuf

    def serial_conn_speed_fallback(self):
        sc = self.connection
        if isinstance(sc, SerialConnection) and self.initialBaudRate != BaudRate.Undefined:
            if sc.BaudRate != self.initialBaudRate:
                sc.BaudRate = self.initialBaudRate
                self.log(LogLevel.Debug, f"восстановлена начальная скорость обмена {int(self.initialBaudRate)} bps")

    def select_device_and_channel(self, mtr, zNt, tv=M4_MeterChannel.SYS):
        if mtr is None:
            raise ValueError()

        nt = zNt if zNt else self.BROADCAST

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
            hsPkt = self.handshake(nt, tv, slowFFs)

            detectedType = Logika4.MeterTypeFromResponse(hsPkt.Data[0], hsPkt.Data[1], hsPkt.Data[2])
            if detectedType != mtr:
                self.reset_internal_bus_state()
                raise ECommException(ExcSeverity.Stop, CommError.Unspecified,
                                     f"Несоответствие типа прибора. Ожидаемый тип прибора: {mtr.Caption}, фактический: {detectedType.Caption} (NT={nt})")

            self.activeDev = _busActivePtr(mtr, nt, tv)
            self.activeDev.lastIOTime = datetime.now()

    def get_meter_type(self, srcNT, dstNT):
        hsPkt = self.handshake(dstNT, 0, False)
        xtraData = hsPkt.Data[2]
        return Logika4.meter_type_from_response(hsPkt.Data[0], hsPkt.Data[1], hsPkt.Data[2])

    def handshake(self, nt, channel, bSlowFFs):
        if self.activeDev and nt != self.activeDev.nt:
            self.reset_internal_bus_state()

        self.send_attention(bSlowFFs)
        time.sleep(0.1)
        self.connection.purge_comms(PurgeFlags.RX)

        reqData = [channel, 0, 0, 0]
        return self.do_legacy_request(nt, M4Opcode.Handshake, reqData, 3)

    def do_legacy_request(self, nt, reqFunc, data, expectedDataLen, flags=0):
        self.send_legacy_packet(nt, reqFunc, data)
        return self.recv_packet(nt, reqFunc, None, expectedDataLen, flags)

    def do_m4_request(self, nt, reqFunc, data, pktId=None, flags=0):
        if pktId is None:
            pktId = self.idCtr
            self.idCtr += 1
        self.send_extended_packet(nt, pktId, reqFunc, data)
        p = self.recv_packet(nt, reqFunc, pktId, 0, flags)
        return p

    def recv_packet(self, expectedNT, expectedOpcode, expectedId, expectedDataLength, flags=0):
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

                if expectedNT and p.NT != expectedNT:
                    continue

                if (expectedOpcode and
                        p.FunctionCode != expectedOpcode and
                        p.FunctionCode != M4Opcode.Error and
                        p.FunctionCode != M4Protocol.EXT_PROTO):
                    if expectedOpcode == M4Opcode.ReadFlash:
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
                    if expectedOpcode and p.FunctionCode != expectedOpcode and p.FunctionCode != M4Opcode.Error:
                        continue

                    if expectedId and p.ID != expectedId:
                        self.log(LogLevel.Warn,
                                 f"нарушение порядка обмена: ожидаемый ID пакета: 0x{expectedId:X2}, принятый: 0x{p.ID:X2}")

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

    def set_bus_speed(self, mtr, nt, baudRate, tv=M4_MeterChannel.SYS):
        serialConn = self.connection
        if not isinstance(serialConn, SerialConnection):
            raise Exception("смена скорости недопустима на соединениях отличных от 'Serial'")

        m4BaudRates = [2400, 4800, 9600, 19200, 38400, 57600, 115200]
        nbr = m4BaudRates.index(int(baudRate))
        if nbr < 0:
            raise ECommException(ExcSeverity.Stop, CommError.Unspecified,
                                 "запрошенная скорость обмена не поддерживается")

        prevBaudRate = serialConn.BaudRate
        changedOk = False
        devAcksNewBR = False
        self.log(LogLevel.Info, f"установка скорости обмена {int(baudRate)} bps")
        try:
            rsp = self.do_legacy_request(nt, M4Opcode.SetSpeed, [nbr, 0, 0, 0], 0, RecvFlags.DontThrowOnErrorReply)
            if rsp.FunctionCode == M4Opcode.SetSpeed:
                devAcksNewBR = True
                time.sleep(0.25)
                self.connection.PurgeComms(PurgeFlags.RX | PurgeFlags.TX)

                serialConn.BaudRate = baudRate
                rsp = self.do_legacy_request(nt, M4Opcode.Handshake, [tv, 0, 0, 0], 3, RecvFlags.DontThrowOnErrorReply)
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

    def send_legacy_packet(self, nt, func, data):
        pkt = M4Packet()
        pBuf = bytearray(3 + len(data) + 2)

        pBuf[0] = self.FRAME_START
        pBuf[1] = nt if nt is not None else self.BROADCAST
        pBuf[2] = func

        pBuf[3:3 + len(data)] = data
        pBuf[3 + len(data)] = Logika4.Checksum8(pBuf, 1, len(data) + 2)
        pBuf[3 + len(data) + 1] = self.FRAME_END

        pktTotalLen = 3 + len(data) + 2
        self.connection.write(pBuf, 0, pktTotalLen)

        self.report_proto_event(ProtoEvent.packetTransmitted)

    def write_parameter_l4(self, mtr, nt, channel, nParam, value, operFlag):
        if isinstance(mtr, TSPG741) and 200 <= nParam < 300:
            td = Meter.SPG741.Tags.All.SingleOrDefault(lambda x: x.Ordinal == nParam)
            sp = self.get741sp(nt)
            mappedOrdinal = TSPG741.GetMappedDBParamOrdinal(td.Key, sp)
            if mappedOrdinal is None:
                return None
            else:
                nParam = mappedOrdinal

        self.select_device_and_channel(mtr, nt, M4_MeterChannel(channel))
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

        if operFlag is not None:
            reqData[-1] = ord('*') if operFlag else 0x00

        pkt = self.do_legacy_request(nt, M4Opcode.WriteParam, reqData, 0, RecvFlags.DontThrowOnErrorReply)
        if pkt.FunctionCode == M4Opcode.Error:
            return ErrorCode(pkt.Data[0])

        return None

    @staticmethod
    def get_legacy_response_data_len(functionCode):
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

    def get741sp(self, nt):
        mmd = self.getMeterInstance(Meter.SPG741, nt)
        if mmd.sp is None:
            SP_741_ADDR = 0x200
            self.getFlashPagesToCache(Meter.SPG741, nt, SP_741_ADDR // Logika4L.FLASH_PAGE_SIZE, 1, mmd)
            mmd.sp = int(Logika4L.get_value(Logika4L.BinaryType.dbentry, mmd.flash, SP_741_ADDR, False))
        return mmd.sp

    def read_ram(self, mtr, nt, StartAddr, nBytes):
        if nBytes > self.MAX_RAM_REQUEST:
            raise ValueError("too much data requested from RAM")

        self.select_device_and_channel(mtr, nt)

        reqData = bytearray([StartAddr & 0xFF, (StartAddr >> 8) & 0xFF, nBytes, 0])
        pkt = self.do_legacy_request(nt, M4Opcode.ReadRam, reqData, nBytes)

        return pkt.Data

    def read_flash_pages(self, mtr, nt, startPage, pageCount):
        if pageCount <= 0:
            raise ValueError("ReadFlashPages: zero page count")

        self.select_device_and_channel(mtr, nt)
        cmdbuf = bytearray(4)

        retbuf = bytearray(pageCount * Logika4L.FLASH_PAGE_SIZE)

        for p in range((pageCount + self.MAX_PAGE_BLOCK - 1) // self.MAX_PAGE_BLOCK):
            pagesToReq = pageCount - p * self.MAX_PAGE_BLOCK
            if pagesToReq > self.MAX_PAGE_BLOCK:
                pagesToReq = self.MAX_PAGE_BLOCK
            pageBlockStart = startPage + p * self.MAX_PAGE_BLOCK

            reqData = bytearray([pageBlockStart & 0xFF, (pageBlockStart >> 8) & 0xFF, pagesToReq, 0])
            self.send_legacy_packet(nt, M4Opcode.ReadFlash, reqData)

            for i in range(pagesToReq):
                try:
                    pkt = self.recv_packet(nt, M4Opcode.ReadFlash, None, Logika4L.FLASH_PAGE_SIZE)
                except:
                    if pageCount > 1:
                        self.on_recoverable_error()
                    raise

                if pkt.FunctionCode != M4Opcode.ReadFlash or len(pkt.Data) != Logika4L.FLASH_PAGE_SIZE:
                    raise ECommException(ExcSeverity.Error, CommError.Unspecified,
                                         f"принят некорректный пакет, код функции 0x{pkt.FunctionCode:X2}")

                retbuf[(p * self.MAX_PAGE_BLOCK + i) * Logika4L.FLASH_PAGE_SIZE:(
                                                                                        p * self.MAX_PAGE_BLOCK + i + 1) * Logika4L.FLASH_PAGE_SIZE] = pkt.Data

        return retbuf

    def on_recoverable_error(self):
        if self.activeDev is not None:
            self.activeDev.ioError = True

    def read_flash_bytes(self, mtr, nt, StartAddr, Length):
        if Length <= 0:
            raise ValueError("read length invalid")

        StartPage = StartAddr // Logika4L.FLASH_PAGE_SIZE
        EndPage = (StartAddr + Length - 1) // Logika4L.FLASH_PAGE_SIZE
        PageCount = EndPage - StartPage + 1
        mem = self.read_flash_pages(mtr, nt, StartPage, PageCount)
        retbuf = bytearray(Length)
        retbuf[:Length] = mem[StartAddr % Logika4L.FLASH_PAGE_SIZE:StartAddr % Logika4L.FLASH_PAGE_SIZE + Length]

        return retbuf

    def send_extended_packet(self, nt, packetId, opcode, data):
        CRC_LEN = 2
        HDR_LEN = 8

        buf = bytearray(HDR_LEN + len(data) + CRC_LEN)

        buf[0] = self.FRAME_START
        buf[1] = nt if nt is not None else self.BROADCAST
        buf[2] = 0x90
        buf[3] = packetId
        buf[4] = 0x00

        payload_len = 1 + len(data)
        buf[5] = payload_len & 0xFF
        buf[6] = payload_len >> 8

        buf[7] = opcode
        buf[8:] = data

        check = 0
        Protocol.crc16(check, buf, 1, HDR_LEN - 1 + len(data))
        buf[HDR_LEN + len(data)] = check >> 8
        buf[HDR_LEN + len(data) + 1] = check & 0xFF

        self.connection.Write(buf, 0, len(buf))
        self.report_proto_event(ProtoEvent.packetTransmitted)

    def read_tags_m4(self, m, nt, channels, ordinals):
        self.select_device_and_channel(m, nt)
        if channels is None or len(channels) == 0 or ordinals is None or len(ordinals) == 0 or len(channels) != len(
                ordinals):
            raise ValueError("некорректные входные параметры функции readTagsM4")

        lb = []
        for i in range(len(ordinals)):
            ch = ordinals[i] // CHANNEL_NBASE if ordinals[i] >= CHANNEL_NBASE else channels[i]
            ord = ordinals[i] % CHANNEL_NBASE
            self.append_pnum(lb, ch, ord)

        p = self.do_m4_request(nt, M4Opcode.ReadTags, bytes(lb))
        lb.clear()

        opFlags = []
        oa = self.parse_m4_tags_packet(p, opFlags)

        if m == Meter.SPG742 or m == Meter.SPT941_20:
            for i in range(len(ordinals)):
                if ordinals[i] == 8256 and isinstance(oa[i], int):
                    oa[i] = oa[i] & 0x00FFFFFF

        return oa

    def parse_m4_tags_packet(self, p, opFlags):
        if not p.Extended or p.FunctionCode != M4Opcode.ReadTags:
            raise ValueError("некорректный пакет")

        valuesList = []
        opFlagsList = []

        tp = 0
        while tp < len(p.Data):
            o = None
            tagLen = Logika4M.ParseTag(p.Data, tp, o)

            if isinstance(o, Logika4M.OperParamFlag):
                opFlagsList[-1] = True if o == Logika4M.OperParamFlag.Yes else False
                tp += tagLen
                continue

            valuesList.append(o)
            opFlagsList.append(False)

            tp += tagLen

        opFlags.extend(opFlagsList)
        return valuesList

    @staticmethod
    def append_pnum(lb, channel, ordinal):
        lb.append(0x4A)
        lb.append(0x03)

        lb.append(channel)
        lb.append(ordinal & 0xFF)
        lb.append((ordinal >> 8) & 0xFF)

    def write_params_m4(self, mtr, nt, wda):
        self.select_device_and_channel(mtr, nt)

        lb = []
        for twd in wda:
            v = twd.value

            ch = twd.channel if twd.ordinal < CHANNEL_NBASE else twd.ordinal // CHANNEL_NBASE
            ord = twd.ordinal % CHANNEL_NBASE
            self.append_pnum(lb, ch, ord)

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

        p = self.do_m4_request(nt, M4Opcode.WriteTags, bytes(lb))
        errors = [None] * len(wda)

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
    def restrict_time(dt):
        if dt != datetime.min:
            y = dt.year - 2000
            if y < 0:
                return datetime(2000, 1, 1, 0, 0, 0, dt.tzinfo)
            elif y > 255:
                return datetime(2255, 1, 31, 23, 59, 59, 999, dt.tzinfo)
        return dt

    @staticmethod
    def append_date_tag(lb, dt, useYearAndMonthOnly):
        lb.append(0x49)
        lb.append(2 if useYearAndMonthOnly else 8)
        lb.append(dt.year - 2000)
        lb.append(dt.month)
        if not useYearAndMonthOnly:
            lb.extend([dt.day, dt.hour, dt.minute, dt.second, dt.microsecond & 0xFF, dt.microsecond >> 8])

    def read_archive_m4(self, mtr, nt, pktId, partition, channel, archiveKind, from_dt, to_dt, numValues, result,
                        nextRecord):
        self.select_device_and_channel(mtr, nt)

        from_dt = self.restrict_time(from_dt)
        to_dt = self.restrict_time(to_dt)
        if to_dt != datetime.min and from_dt > to_dt:
            raise ValueError("протокол M4 не поддерживает чтение в обратном порядке")

        lb = bytearray([partition & 0xFF, partition >> 8, channel, archiveKind])
        if mtr.SupportsFLZ:
            compFlags_archId = archiveKind | self.CompressionType.FLZLimitedLength
            lb.append(compFlags_archId)
        if numValues > 0xFF:
            numValues = 0xFF
        lb.append(numValues)
        self.append_date_tag(lb, from_dt, False)
        if to_dt != datetime.min:
            self.append_date_tag(lb, to_dt, False)

        p = self.do_m4_request(nt, M4Opcode.ReadArchive, bytes(lb), pktId)
        lb.clear()

        result, nextRecord = self.parse_archive_packet(p)
        return p

    def parse_archive_packet(self, p):
        if not p.Extended or p.FunctionCode != M4Opcode.ReadArchive:
            raise ValueError("некорректный пакет")

        lr = []
        nextRecord = datetime.min

        decompData = p.Data
        tp = 0
        while tp < len(decompData):
            oTime = None
            tp += Logika4M.parse_tag(decompData, tp, oTime)

            lenLen = Logika4M.get_tag_length(decompData, tp + 1)
            recLen = lenLen[1]

            if recLen == 0:
                nextRecord = oTime
                break

            r = M4ArchiveRecord()
            r.intervalMark = datetime(oTime, tzinfo=datetime.timezone.utc)

            if decompData[tp] == 0x30:
                tp += 1 + lenLen[0]

                st = tp

                lo = []
                while tp - st < recLen:
                    o = None
                    tp += Logika4M.parse_tag(decompData, tp, o)
                    lo.append(o)

                if isinstance(lo[0], str) and isinstance(lo[1], str) and len(lo[0]) == 8 and len(lo[1]) == 8:
                    ta = lo[0].split('-') + lo[0].split(':')
                    da = lo[1].split('-')
                    r.dt = datetime(2000 + int(da[2]), int(da[1]), int(da[0]), int(ta[0]), int(ta[1]),
                                    int(ta[2]), tzinfo=datetime.timezone.utc)
                    lo = lo[2:]
                else:
                    r.dt = datetime.min

                r.values = lo
            else:
                o = None
                tp += Logika4M.ParseTag(decompData, tp, o)
                r.dt = r.intervalMark
                r.values = [o]

            lr.append(r)

        if nextRecord != datetime.min and len(lr) > 0 and nextRecord <= lr[-1].dt:
            raise ECommException(ExcSeverity.Stop, CommError.Unspecified, "зацикливание датировки архивных записей")

        return lr, nextRecord

    def get_device_clock(self, meter: Meter, src, dst) -> datetime:
        pass

    def update_tags(self, src, dst, tags: List[DataTag]):
        pass

    def read_interval_archive_def(self, m, src, dst, ar_type) -> IntervalArchive:
        pass

    def read_interval_archive(self, m, src, dst, ar, start: datetime, end: datetime) -> bool:
        pass

    def read_service_archive(self, m, src, dst, ar, start: datetime, end: datetime) -> bool:
        pass
