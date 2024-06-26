import gc
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from enum import Flag, auto
from typing import Optional

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


class ConnectionType(Enum):
    Offline = (-1, "Отключено")
    Serial = (0, "COM порт")
    Modem = (1, "Модем")
    TCP = (2, "TCP")
    UDP = (3, "UDP")
    Radius = (4, "Радиус")


class PurgeFlags(Flag):
    RX = auto()
    TX = auto()


class ConnectionState(Enum):
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
        self.on_connection_state_change = None
        self.m_last_rx_time: datetime = datetime.min
        self.m_read_timeout = None
        self.m_state = None
        self.tx_byte_cnt: int = 0
        self.rx_byte_cnt: int = 0
        self.on_log_event = None
        self.address: str = address
        self.closing_event: ManualResetEvent = ManualResetEvent()
        self.read_timeout: int = read_timeout
        self.state: ConnectionState = ConnectionState.NotConnected
        self.on_before_disconnect: EventHandler = EventHandler()
        self.on_after_connect: EventHandler = EventHandler()
        self.on_connect_required: EventHandler = EventHandler()

    @abstractmethod
    def dispose(self, disposing: bool):
        self.dispose(True)
        gc.disable()

    @staticmethod
    def reset_bus_state_tracker():
        print("resetting bus state")

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
    def internal_read(self, buf: bytes, start: int, max_length: int) -> int:
        pass

    @abstractmethod
    def internal_write(self, buf: bytes, start: int, n_bytes: int):
        pass

    @property
    def resource_name(self):
        return None

    async def open(self):
        async with threading.Lock:
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

                self.log(LogLevel.Info,
                         "соединение установлено" + ("" if connDetails == "" else " (" + connDetails + ")"))

                if self.on_after_connect is not None:
                    try:
                        self.on_after_connect.add_handler(None)
                    except:
                        pass

            except Exception as e:
                self.log(LogLevel.Error, "", e)
                raise

    def close(self):
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
                    self.log(LogLevel.Info, "соединение завершено")

                except Exception as e:
                    self.log(LogLevel.Warn, "ошибка при завершении соединения", e)

            self.state = ConnectionState.NotConnected

    @abstractmethod
    def internal_purge_comms(self, what: PurgeFlags):
        pass

    def purge_comms(self, what: PurgeFlags):
        if self.state == ConnectionState.Connected:
            self.internal_purge_comms(what)
            sp = "# purge "
            if what & PurgeFlags.RX:
                sp += "RX "
            if what & PurgeFlags.TX:
                sp += "TX"

    def read_available(self, buf: bytes, start: int, maxLength: int) -> int:
        self.check_if_connected()
        try:
            nRead = self.internal_read(buf, start, maxLength)
            if nRead > 0:
                self.rx_byte_cnt += nRead
                rr = buf[start:start + nRead]
        except Exception as e:
            raise e

        self.m_last_rx_time = datetime.now()

        return nRead

    def read(self, buf: bytes, start: int, length: int):
        nRead = 0

        while nRead < length:
            self.check_if_closing()
            nRead += self.read_available(buf, start + nRead, length - nRead)

    def write(self, buf: bytes, start: int, nBytes: int):
        self.check_if_connected()
        self.check_if_closing()
        try:
            self.internal_write(buf, start, nBytes)
            self.tx_byte_cnt += nBytes
            if nBytes > 0:
                wr = buf[start:start + nBytes]
        except Exception as e:
            raise

    def state_change_delegate(self, new_state: ConnectionState):
        if self.on_connection_state_change is not None:
            self.on_connection_state_change(new_state)

    @property
    def state(self):
        return self.m_state

    @state.setter
    def state(self, value):
        self.m_state = value
        self.state_change_delegate(value)

    @property
    def read_timeout(self):
        return self.m_read_timeout

    @read_timeout.setter
    def read_timeout(self, value):
        self.m_read_timeout = value
        self.on_set_read_timeout(value)

    def on_set_read_timeout(self, new_timeout: int):
        pass

    @abstractmethod
    def is_conflicting_with(self, target):
        pass

    def conflicts_with(self, target) -> bool:
        if self.state == ConnectionState.NotConnected or not isinstance(target, type(self)):
            return False
        return self.is_conflicting_with(target)

    @property
    def last_rx_time(self) -> datetime:
        return self.m_last_rx_time

    def reset_statistics(self):
        self.tx_byte_cnt = 0
        self.rx_byte_cnt = 0
