import socket
import threading

from select import select

from Logika.Connections.Connection import ConnectionState, PurgeFlags
from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError


class TCPConnection(NetConnection):
    socket = None

    def __init__(self, read_timeout: int, host: str, port: int):
        super().__init__(read_timeout, host, port)
        self.WSAETIMEDOUT: int = 10060
        self.connect_ended: threading = threading.Event()
        self.connect_exception = None
        self.host = host
        self.port = port
        self.readTimeout = read_timeout

    def dispose(self, disposing: bool):
        if disposing:
            if self.socket:
                self.socket.close()
                self.socket = None

    def internal_open(self, connect_details: str):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(True)

        connectDetails = None

        self.connect_ended.clear()
        self.connect_exception = None

        try:
            self.socket.connect((self.host, self.port))

            ready, _, _ = select([], [self.socket], [], max(self.readTimeout, 15))
            if not ready:
                self.socket.close()
                self.socket = None
                raise socket.error(self.WSAETIMEDOUT)
            else:
                if self.connect_exception:
                    raise self.connect_exception

        except socket.error as se:
            if se.errno == 11001:
                raise ECommException(ExcSeverity.Stop, CommError.SystemError, se.strerror)

            raise ECommException(ExcSeverity.Reset, CommError.SystemError, se.strerror)

    def internal_close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def on_set_read_timeout(self, new_timeout: int):
        if TCPConnection.socket:
            self.socket.settimeout(new_timeout)

    def on_connect(self):
        try:
            self.socket.getpeername()

        except Exception as e:
            self.connect_exception = e

        finally:
            self.connect_ended.set()

    def is_conflicting_with(self, target):
        if not isinstance(target, TCPConnection):
            return False
        TarCon = target
        return TarCon.m_srv_host_name == self.m_srv_host_name and TarCon.m_srv_port == self.m_srv_port

    def internal_read(self, buf: bytes, start: int, max_length: int):
        errcode = 0
        nBytes: int = 0

        if not self.socket.poll(self.readTimeout * 1000):
            raise ECommException(ExcSeverity.Error, CommError.Timeout)

        if self.state != ConnectionState.Connected or self.socket is None:
            return 0

        try:
            nBytes = self.socket.recv_into(buf, start, max_length)
        except socket.error as e:
            errcode = e.errno
            print(f"Error receiving data: {e}")

        if nBytes == 0:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, "соединение завершено удаленной стороной")

        if errcode != 0:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, errcode.__str__())

        return nBytes

    def internal_write(self, buf: bytes, start: int, length: int):
        try:
            sent_bytes = self.socket.send(buf[start:start + length])
            if sent_bytes != length:
                raise Exception("Failed to send all bytes")
        except socket.error as e:
            errcode = e.errno
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, errcode.__str__())

    def internal_purge_comms(self, flg: PurgeFlags):
        if self.state != ConnectionState.Connected:
            return

        if flg & PurgeFlags.RX:
            while True:
                nBytes = self.socket.recv(1024)
                if nBytes == 0:
                    break
                mem = bytearray(nBytes)
                self.socket.recv_into(mem)

        if flg & PurgeFlags.TX:
            pass  # no methods for aborting tcp tx
