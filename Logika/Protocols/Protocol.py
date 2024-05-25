import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List

from Logika.Connections.Connection import ConnectionState, ConnectionType, PurgeFlags, Connection
from Logika.Connections.SerialConnection import StopBits, Parity, SerialConnection, BaudRate
from Logika.ECommException import ECommException, CommError, ExcSeverity
from Logika.Meters.Archive import IntervalArchive
from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Meter import Meter
from Logika.Meters.Types import BusProtocolType, ArchiveType
from Logika.Protocols.M4.ErrorCode import ErrorCode
from Logika.Protocols.M4.M4Opcode import M4Opcode
from Logika.Protocols.M4.M4Protocol import M4Protocol
from Logika.Meters.__4L.Logika4L import Logika4L
from Logika.Protocols.SPBus.SPBusProtocol import SPBusProtocol


class ProtoEvent(Enum):
    packetTransmitted = 1,
    packetReceived = 2,
    rxTimeout = 3,
    rxCrcError = 4,
    genericError = 5


class Protocol(ABC):
    LGK_ERA_START = datetime(2000, 1, 1)  # should not request any data before this date

    def __init__(self):
        self.cn = None
        self.packetsSent = 0
        self.packetsRcvd = 0
        self.rxTimeouts = 0
        self.rxCRCs = 0
        self.rxLatePkts = 0
        self.genErrs = 0

        self.waitMtx_ = threading.Lock()
        self.waitCond_ = threading.Condition(self.waitMtx_)

    @abstractmethod
    def reset_internal_bus_state(self):
        pass

    @abstractmethod
    def internal_close_comm_session(self, src_nt: bytes, dst_nt: bytes):
        pass

    @abstractmethod
    def get_meter_type(self, src_nt: bytes, dst_nt: bytes) -> Meter:
        pass

    @abstractmethod
    def get_device_clock(self, meter: Meter, src: bytes, dst: bytes) -> datetime:
        pass

    @abstractmethod
    def update_tags(self, src, dst, tags: List[DataTag]):
        pass

    @abstractmethod
    def read_interval_archive_def(self, m: Meter, src_nt: bytes, dst_nt: bytes,
                                  ar_type: ArchiveType) -> IntervalArchive:
        pass

    @abstractmethod
    def read_interval_archive(self, m: Meter, src_nt: bytes, nt: bytes, ar: IntervalArchive, start: datetime,
                              end: datetime) -> bool:
        pass

    @abstractmethod
    def read_service_archive(self, m: Meter, src: bytes, dst: bytes, ar: IntervalArchive, start: datetime,
                             end: datetime) -> bool:
        pass

    @property
    def connection(self):
        return self.cn

    @connection.setter
    def connection(self, value):
        if value is not None:
            value.busTrackerResetEvent += self.reset_internal_bus_state
        elif self.cn is not None:
            self.cn.busTrackerResetEvent -= self.reset_internal_bus_state
        self.cn = value

    def log(self, level, msg, exc=None):
        if self.cn is not None:
            self.cn.log(level, msg, exc)

    def reset(self):
        self.packetsRcvd = 0
        self.packetsSent = 0
        self.rxTimeouts = 0
        self.rxCRCs = 0
        self.rxLatePkts = 0
        self.genErrs = 0

        self.reset_internal_bus_state()

    def report_proto_event(self, evType: ProtoEvent):
        try:
            if evType == ProtoEvent.packetReceived:
                self.packetsRcvd += 1
            elif evType == ProtoEvent.packetTransmitted:
                self.packetsSent += 1
            elif evType == ProtoEvent.rxTimeout:
                self.rxTimeouts += 1
            elif evType == ProtoEvent.rxCrcError:
                self.rxCRCs += 1
            else:
                self.genErrs += 1
        except:
            pass

    def close_comm_session(self, src_nt: bytes, dst_nt: bytes):
        try:
            if self.connection is not None and self.connection.state == ConnectionState.Connected:
                self.internal_close_comm_session(src_nt, dst_nt)
        except:
            pass

    def cancel(self):
        try:
            if self.connection is not None:
                self.connection.close()
        except:
            pass

    def wait_for(self, duration: int):
        with self.waitMtx_:
            return not self.waitCond_.wait(timeout=duration / 1000)

    def cancel_wait(self):
        with self.waitMtx_:
            self.waitCond_.notify_all()

    def detect_x6(self, bus):
        # req = SPBus.SPBusPacket.BuildReadTagsPacket(None, None, "", [0], [99])
        # reqBytes = req.AsByteArray()
        # bus.connection.Write(reqBytes, 0, len(reqBytes))
        # dump = bus.ReadPacket6()
        # pkt = SPBus.SPBusPacket.Parse(dump, 0, SPBus.SPBusPacket.ParseFlags.None)
        #
        # if len(pkt.Records) != 2:
        #     raise ECommException(ExcSeverity.Error, CommError.Unspecified, "некорректная структура пакета")
        #
        # p099 = pkt.Records[1].Fields[0]
        # return SPBusProtocol.MeterTypeFromResponse(p099, model)
        pass

    def detect_m4(self, bus: M4Protocol):
        model = ""
        reply = bus.handshake(bytes([0xFF]), bytearray([0]), False)
        dump = reply.getDump()
        mtr = Logika4.meter_type_from_response(reply.Data[0], reply.Data[1], reply.Data[2])

        if mtr == Meter.SPT942:
            mtr_4L = mtr.__class__ = Logika4L()
            modelBytes = bus.read_flash_bytes(mtr_4L, bytes([0xFF]), 0x30, 1)
            model = chr(modelBytes[0])

        return mtr, dump, model

    def autodetect_spt_stable(self, conn: Connection, fixedBaudRate: BaudRate, tryM4: bool, trySPBus: bool,
                              tryMEK: bool):
        m = None
        model = ""
        bus4 = M4Protocol()
        bus6 = SPBusProtocol(True)
        bus4.connection = conn
        bus6.connection = conn
        canChangeBaudrate = isinstance(conn, SerialConnection)
        detectedBaud = 0
        savedTimeout = conn.ReadTimeout
        conn.ReadTimeout = 500

        try:
            baudRateList = [2400, 57600, 4800, 19200, 9600, 38400, 115200] if canChangeBaudrate else [0]
            if fixedBaudRate != BaudRate.Undefined:
                baudRateList = [fixedBaudRate]

            for baudRate in baudRateList:
                if canChangeBaudrate:
                    # TODO: сделать каст на SerialConnection
                    conn.set_params(baudRate, 8, StopBits.One, Parity.Zero)
                    detectedBaud = baudRate
                    print(f"trying {detectedBaud} bps...")

                if tryM4:
                    try:
                        m, dump, model = self.detect_m4(bus4)
                        devBaudRate = detectedBaud
                        return m, dump, model
                    except Exception:
                        pass

                if trySPBus:
                    try:
                        m = self.detect_x6(bus6)
                        devBaudRate = detectedBaud
                        return m, dump, model
                    except Exception:
                        pass

            if tryMEK and trySPBus and canChangeBaudrate:
                conn.ReadTimeout = 1000
                try:
                    detectedBaud = bus6.MEKHandshake()
                    if detectedBaud > 0:
                        devBaudRate = detectedBaud
                        return self.detect_x6(bus6)
                except Exception:
                    pass

        finally:
            conn.ReadTimeout = savedTimeout

        devBaudRate = 0
        dump = None
        return None, dump, model

    @staticmethod
    def detect_response(c: Connection):
        rxDetected = False
        dump = None
        model = None
        buf = bytearray(64)
        ReadStart = datetime.now()

        try:
            while True:
                while True:
                    c.read(buf, 0, 1)
                    rxDetected = True
                    if buf[0] == 0x10:
                        break

                    Elapsed = datetime.now() - ReadStart
                    if Elapsed.total_seconds() * 1000 > c.read_timeout:
                        raise ECommException(ExcSeverity.Error, CommError.Timeout)

                c.read(buf, 1, 5)

                if buf[2] == M4Opcode.Error and buf[3] == ErrorCode.BadRequest and buf[5] == M4Protocol.FRAME_END:
                    continue

                if buf[1] == 0x01 and buf[2] != M4Opcode.Handshake:
                    p = 6
                    iETX = -1

                    while True:
                        c.read(buf, p, 1)
                        p += 1
                        if iETX == -1:
                            iETX = SPBus.SPBusPacket.findMarker(buf, 2, p, 0x10, 0x03)
                        if iETX < 0 or (iETX > 0 and p < iETX + 4):
                            break

                    crc = 0
                    Protocol.crc16(crc, buf, 2, iETX + 2)

                    if crc != 0:
                        raise ECommException(ExcSeverity.Error, CommError.Checksum)

                    dump = buf[:iETX + 4]
                    pkt = SPBus.SPBusPacket.parse(buf, 0)

                    if len(pkt.Records) != 2:
                        raise ECommException(ExcSeverity.Error, CommError.Unspecified, "некорректная структура пакета")

                    p099 = pkt.Records[1].Fields[0]
                    return SPBusProtocol.MeterTypeFromResponse(p099, model)

                elif buf[2] == M4Opcode.Handshake:
                    c.read(buf, 6, 2)
                    cs = buf[6]
                    calculatedCheck = ~Logika4.Checksum8(buf, 1, 5) & 0xFF

                    if cs != calculatedCheck:
                        raise ECommException(ExcSeverity.Error, CommError.Checksum)

                    m = Logika4.MeterTypeFromResponse(buf[3], buf[4], buf[5])

                    if m == Meter.SPT942:
                        bus4 = M4Protocol()
                        bus4.connection = c
                        mtr_4L = m.__class__ = Logika4L()
                        modelBytes = bus4.read_flash_bytes(mtr_4L, bytes(0xFF), 0x30, 1)
                        model = chr(modelBytes[0])
                    else:
                        model = ""

                    dump = buf[:8]
                    return m

                else:
                    continue

        except Exception as e:
            print(e)

        return None

    @staticmethod
    def autodetect_spt(conn: Connection, fixedBaudRate: BaudRate, waitTimeout: int, tryM4: bool, trySPBus: bool,
                       tryMEK: bool, srcAddr: bytearray, dstAddr: bytearray):
        m = None
        model = ""

        canChangeBaudrate = conn.CanChangeBaudrate if isinstance(conn, SerialConnection) else False
        currentBaudRate = 0

        while True:
            savedTimeout = conn.ReadTimeout
            conn.ReadTimeout = waitTimeout

            try:
                baudRateList = [fixedBaudRate] if (fixedBaudRate > 0 and canChangeBaudrate) \
                    else [2400, 57600, 4800,
                          19200, 9600, 38400,
                          115200] if canChangeBaudrate else [0]

                X6Request = SPBusProtocol.gen_raw_handshake(srcAddr, dstAddr)
                M4Request = M4Protocol.gen_raw_handshake(dstAddr)

                for baudRate in baudRateList:
                    if canChangeBaudrate:
                        conn.SetParams(baudRate, 8, StopBits.Two, Parity.Zero)
                        currentBaudRate = baudRate
                        if currentBaudRate != 0:
                            print(f"trying {currentBaudRate} bps...")

                    devBaudRate = currentBaudRate

                    try:
                        if trySPBus:
                            conn.Write(X6Request, 0, len(X6Request))

                        if trySPBus and tryM4:
                            time.sleep(0.1)

                        if tryM4:
                            conn.write(M4Protocol.WAKEUP_SEQUENCE, 0, len(M4Protocol.WAKEUP_SEQUENCE))
                            time.sleep(M4Protocol.WAKE_SESSION_DELAY)
                            conn.write(M4Request, 0, len(M4Request))

                        time.sleep(0.05)
                        m = Protocol.detect_response(conn)

                        if m is not None:
                            return m

                    except Exception as e:
                        pass

                    conn.PurgeComms(PurgeFlags.RX | PurgeFlags.TX)

                if tryMEK and trySPBus and canChangeBaudrate:
                    conn.ReadTimeout = 1000
                    bus6 = SPBusProtocol(True)
                    bus6.connection = conn

                    try:
                        currentBaudRate = bus6.MEKHandshake()
                        if currentBaudRate > 0:
                            devBaudRate = currentBaudRate
                            tryM4 = False
                            tryMEK = False
                            canChangeBaudrate = False
                            continue

                    except Exception as e:
                        pass

            finally:
                conn.ReadTimeout = savedTimeout

            devBaudRate = 0
            return None

    @staticmethod
    def get_default_timeout(proto: BusProtocolType, connType: ConnectionType):
        if connType == ConnectionType.Offline or connType == ConnectionType.Serial:
            if proto == BusProtocolType.SPbus:
                return 15000
            return 5000

        elif connType == ConnectionType.Modem:
            if proto == BusProtocolType.SPbus:
                return 15000
            return 10000

        elif connType == ConnectionType.UDP:
            return 10000

        elif connType == ConnectionType.TCP or connType == ConnectionType.Radius:
            return 15000

        else:
            return 15000  # Default case

    @staticmethod
    def crc16(crc, buf: bytearray, offset: int, length: int):
        while length > 0:
            crc ^= (buf[offset] << 8) & 0xFFFF
            for j in range(8):
                if (crc & 0x8000) != 0:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
            offset += 1
            length -= 1

        return crc
