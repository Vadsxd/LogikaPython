from abc import ABC, abstractmethod
from enum import Enum, IntEnum

from Logika.Connections.Connection import Connection


class BaudRate(IntEnum):
    Undefined = 0
    b1200 = 1200
    b2400 = 2400
    b4800 = 4800
    b9600 = 9600
    b19200 = 19200
    b38400 = 38400
    b57600 = 57600
    b115200 = 115200


class StopBits(Enum):
    One = 0
    Two = 2


class Parity(Enum):
    Zero = 0
    Odd = 1
    Even = 2


class SerialConnection(ABC, Connection):
    def __init__(self, read_timeout: int, port_name: str):
        super().__init__(port_name, read_timeout)

    @property
    def can_change_baudrate(self) -> bool:
        return True

    @property
    def baud_rate(self):
        raise NotImplementedError

    @abstractmethod
    def set_stop_bits(self, stop_bits: StopBits):
        pass

    @abstractmethod
    def set_params(self, baud_rate: BaudRate, data_bits: int, stop_bits: StopBits, parity: Parity):
        pass
