import gc
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from enum import IntEnum, Flag, auto
from typing import List, Optional

from Logika.ECommException import ECommException, ExcSeverity, CommError
from Logika.LogLevel import LogLevel


class ManualResetEvent:
    def __init__(self, initial_state=False):
        self.event = threading.Event()
        self.state = initial_state

    def set(self):
        self.state = True
        self.event.set()

    def reset(self):
        self.state = False
        self.event.clear()

    def wait(self):
        if not self.state:
            self.event.wait()


class ConnectionType(IntEnum):
    Offline = -1
    Serial = 0
    Modem = 1
    TCP = 2
    UDP = 3
    Radius = 4

    def __str__(self):
        descriptions = {
            ConnectionType.Offline: "Отключено",
            ConnectionType.Serial: "COM порт",
            ConnectionType.Modem: "Модем",
            ConnectionType.TCP: "TCP",
            ConnectionType.UDP: "UDP",
            ConnectionType.Radius: "Радиус",
        }
        return descriptions[self]


class PurgeFlags(Flag):
    RX = auto()
    TX = auto()


class ConnectionState(IntEnum):
    NotConnected = 0
    Connecting = 1
    Connected = 2
    Disconnecting = 3


class MonitorEventType(Enum):
    Open = "канал связи открыт"
    Close = "канал связи закрыт"
    ChannelPropertiesChanged = "изменение свойств канала связи"
    Tx = "данные отправлены"
    Rx = "данные приняты"
    Purge = "сброс буферов приёма/передачи"
    Error = "ошибка"
    Undefined = "?"


class EventArgs:
    def __init__(self, event_name, data):
        self.event_name = event_name
        self.data = data


class EventHandler:
    def __init__(self):
        self.handlers = []

    def add_handler(self, handler):
        self.handlers.append(handler)

    def remove_handler(self, handler):
        self.handlers.remove(handler)

    def fire(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)


class Connection(ABC):
    def __init__(self, address: str, read_timeout: int):
        self.OnConnectionStateChange = None
        self.mLastRXTime = None
        self.mReadTimeout = None
        self.mState = None
        self.txByteCnt = None
        self.rxByteCnt = None
        self.on_log_event = None
        self.address = address
        self.closing_event = ManualResetEvent()
        self.read_timeout = read_timeout
        self.state = ConnectionState.NotConnected
        self.last_rx_time = datetime.min
        self.on_before_disconnect = EventHandler()
        self.on_after_connect = EventHandler()
        self.on_connect_required = EventHandler()

    @abstractmethod
    def dispose(self, disposing: bool):
        self.dispose(True)
        gc.disable()

    @staticmethod
    def reset_bus_state_tracker():
        print("resetting bus state")

    # def mon(self, event: MonitorEventType, data: List[bytes], info: str):
    #     Monitor.instance.on_monitor_event(self, MonitorEvent(datetime.datetime.now(), event, self.address, data, info))

    def check_if_closing(self):
        if self.closing_event.wait():
            raise ECommException(ExcSeverity.Stop, CommError.NotConnected)

    def check_if_connected(self):
        if self.state == ConnectionState.NotConnected:
            self.on_connect_required.add_handler(EventArgs("Not Connected", "{code: 503 Service Unavailable}"))

        if self.state != ConnectionState.Connected:
            raise ECommException(ExcSeverity.Error, CommError.NotConnected)

    def log(self, level: LogLevel, msg: str, exc: Optional[Exception] = None):
        if self.on_log_event is not None:
            try:
                self.on_log_event(level, msg, exc)
                print(f"LogMsg level {level}: {msg}")
            except:
                pass

    @abstractmethod
    def internal_open(self, connect_details: str):
        pass

    @abstractmethod
    def internal_close(self):
        pass

    @abstractmethod
    def internal_read(self, buf: List[bytes], start: int, max_length: int) -> int:
        pass

    @abstractmethod
    def internal_write(self, buf: List[bytes], start: int, n_bytes: int):
        pass

    @property
    def resource_name(self):
        return None

    def Open(self):
        with threading.Lock:
            self.closing_event.reset()
            self.state = ConnectionState.Connecting

            try:
                connstr = "установка соединения" + ("" if self.address == "" else " с " + self.address)
                if self.resource_name != self.address and self.resource_name != "":
                    connstr += " (" + str(self.resource_name) + ")"
                self.log(LogLevel.Info, connstr)

                connDetails = ""
                self.internal_open(connDetails)

                self.state = ConnectionState.Connected

                # self.Mon(MonitorEventType.Open, None, "соединение с '" + self.address + "' установлено")
                self.log(LogLevel.Info,
                         "соединение установлено" + ("" if connDetails == "" else " (" + connDetails + ")"))

                if self.on_after_connect is not None:
                    try:
                        self.on_after_connect.add_handler(None)
                    except:
                        pass

            except Exception as e:
                self.log(LogLevel.Error, "", e)
                # self.mon(MonitorEventType.Error, None, e.message)
                raise

    def Close(self):
        self.closing_event.reset()

        with threading.Lock:
            if self.state == ConnectionState.Connected:
                try:
                    self.state = ConnectionState.Disconnecting

                    if self.on_before_disconnect is not None:
                        try:
                            self.on_before_disconnect.add_handler(None)
                        except:
                            pass

                    self.internal_close()
                    # self.Mon(MonitorEventType.Close, None, "соединение с '" + self.address + "' завершено")
                    self.log(LogLevel.Info, "соединение завершено")

                except Exception as e:
                    self.log(LogLevel.Warn, "ошибка при завершении соединения", e)
                    # self.Mon(MonitorEventType.Error, None, "ошибка при отключении: " + e.message)

            self.state = ConnectionState.NotConnected

    @abstractmethod
    def InternalPurgeComms(self, what):
        pass

    def PurgeComms(self, what):
        if self.state == ConnectionState.Connected:
            self.InternalPurgeComms(what)
            sp = "# purge "
            if what & PurgeFlags.RX:
                sp += "RX "
            if what & PurgeFlags.TX:
                sp += "TX"

            # self.Mon(MonitorEventType.Purge, None, sp)

    def ReadAvailable(self, buf, start, maxLength):
        self.check_if_connected()
        try:
            nRead = self.internal_read(buf, start, maxLength)
            if nRead > 0:
                self.rxByteCnt += nRead
                rr = buf[start:start + nRead]
                # self.Mon(MonitorEventType.Rx, rr, None)
        except Exception as e:
            # self.Mon(MonitorEventType.Error, None, f"! {type(e).__name__} : {e}")
            raise

        self.last_rx_time = datetime.now()

        return nRead

    def Read(self, buf, start, length):
        nRead = 0

        while nRead < length:
            self.check_if_closing()
            nRead += self.ReadAvailable(buf, start + nRead, length - nRead)

    def Write(self, buf, start, nBytes):
        self.check_if_connected()
        self.check_if_closing()
        try:
            self.internal_write(buf, start, nBytes)
            self.txByteCnt += nBytes
            if nBytes > 0:
                wr = buf[start:start + nBytes]
                # self.Mon(MonitorEventType.Tx, wr, None)
        except Exception as e:
            # self.Mon(MonitorEventType.Error, None, f"! {type(e).__name__} : {e}")
            raise

    def StateChangeDelegate(self, new_state):
        if self.OnConnectionStateChange is not None:
            self.OnConnectionStateChange(new_state)

    @property
    def State(self):
        return self.mState

    @State.setter
    def State(self, value):
        self.mState = value
        self.StateChangeDelegate(value)

    @property
    def ReadTimeout(self):
        return self.mReadTimeout

    @ReadTimeout.setter
    def ReadTimeout(self, value):
        self.mReadTimeout = value
        self.onSetReadTimeout(value)
        # self.Mon(MonitorEventType.ChannelPropertiesChanged, None, f"@ ReadTimeout = {value} ms")

    def onSetReadTimeout(self, newTimeout):
        pass

    @abstractmethod
    def isConflictingWith(self, target):
        pass

    def ConflictsWith(self, target):
        if self.State == ConnectionState.NotConnected or not isinstance(target, type(self)):
            return False
        return self.isConflictingWith(target)

    @property
    def LastRXTime(self):
        return self.mLastRXTime

    def ResetStatistics(self):
        self.txByteCnt = 0
        self.rxByteCnt = 0


class MonitorEvent:
    def __init__(self, timestamp: datetime, evt_type: MonitorEventType, address: str, data: bytearray, info: str):
        self.timestamp = timestamp
        self.evt_type = evt_type
        self.address = address
        self.data = data
        self.info = info

    def clone(self):
        me = MonitorEvent
        me.timestamp = self.timestamp
        me.evt_type = self.evt_type
        me.address = self.address
        me.info = self.info
        if self.data is not None:
            me.data = bytearray(self.data)
        return me

    def __str__(self) -> str:
        return f"{self.evt_type} {len(self.data) if self.data is not None else 0} b"
