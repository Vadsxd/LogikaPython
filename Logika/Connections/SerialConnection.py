from enum import Enum, IntEnum

from Logika.Connections.Connection import Connection


class SerialConnection(Connection):
    def __init__(self, read_timeout, port_name):
        super().__init__(port_name, read_timeout)

    @property
    def CanChangeBaudrate(self):
        return True

    @property
    def BaudRate(self):
        raise NotImplementedError

    def SetStopBits(self, stop_bits):
        raise NotImplementedError

    def SetParams(self, baud_rate, data_bits, stop_bits, parity):
        raise NotImplementedError


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
