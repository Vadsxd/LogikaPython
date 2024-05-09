import serial

from Logika.Connections.Connection import PurgeFlags, ConnectionState, Connection
from Logika.Connections.SerialConnection import SerialConnection, BaudRate, StopBits, Parity
from Logika.ECommException import ECommException, ExcSeverity, CommError


class SerialPortConnection(SerialConnection):
    def __init__(self, readTimeout: int, portName: str, baudRate: BaudRate, stopBits: StopBits):
        super().__init__(readTimeout, portName)
        br = 2400 if baudRate == BaudRate.Undefined else baudRate.value
        sb = serial.STOPBITS_ONE if stopBits == StopBits.One else serial.STOPBITS_TWO
        self.port = serial.Serial(port=portName, baudrate=br, parity=serial.PARITY_NONE, bytesize=8, stopbits=sb)
        self.port.timeout = readTimeout

    @property
    def resource_name(self):
        return self.port.port

    def on_set_read_timeout(self, newTimeout: int):
        self.port.timeout = newTimeout

    def internal_open(self, connectionDetails: str):
        connectionDetails = None
        self.port.open()
        self.port.dtr = True
        self.port.timeout = self.readTimeout

    def internal_close(self):
        self.port.close()

    def internal_read(self, buf, start: int, maxLength: int):
        try:
            return self.port.read(buf[start:start + maxLength])
        except serial.SerialTimeoutException:
            raise ECommException(ExcSeverity.Error, CommError.Timeout)
        except Exception as e:
            raise e

    def internal_write(self, buf, start: int, nBytes: int):
        self.port.write(buf[start:start + nBytes])

    def internal_purge_comms(self, what: PurgeFlags):
        if self.State != ConnectionState.Connected:
            return
        if what & PurgeFlags.RX:
            self.port.reset_input_buffer()
        if what & PurgeFlags.TX:
            self.port.reset_output_buffer()

    def set_stop_bits(self, stopBits: StopBits):
        if stopBits == StopBits.One:
            self.port.stopbits = serial.STOPBITS_ONE
        elif stopBits == StopBits.Two:
            self.port.stopbits = serial.STOPBITS_TWO

    @property
    def baud_rate(self):
        return BaudRate(self.port.baudrate)

    @baud_rate.setter
    def baud_rate(self, value):
        self.port.baudrate = value.value

    def is_conflicting_with(self, target: Connection):
        if isinstance(target, SerialPortConnection):
            if target.port.port != self.port.port:
                return False
            else:
                return True
        else:
            return False

    def set_params(self, baudRate, dataBits, stopBits, parity):
        self.port.baudrate = baudRate.value
        self.port.bytesize = dataBits
        self.set_stop_bits(stopBits)
        if parity == Parity.Zero:
            self.port.parity = serial.PARITY_NONE
        elif parity == Parity.Odd:
            self.port.parity = serial.PARITY_ODD
        elif parity == Parity.Even:
            self.port.parity = serial.PARITY_EVEN
        else:
            raise Exception("Unsupported parity")

        if self.port.parity != serial.PARITY_NONE:
            self.port.parity_replace = 0x00

    def dispose(self, disposing: bool):
        if disposing:
            if self.port is not None:
                self.port.close()
                self.port = None
