import socket
import threading

from select import select

from Logika.Connections.Connection import ConnectionState, PurgeFlags
from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError


class TCPConnection(NetConnection):
    def __init__(self, read_timeout: int, host: str, port: int):
        super().__init__(read_timeout, host, port)
        self.socket = None
        self.WSAETIMEDOUT = 10060
        self.connect_ended = threading.Event()
        self.connect_exception = None

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
            if se.errno == socket.errno.ENOENT:
                raise ECommException(ExcSeverity.Stop, CommError.SystemError, se.strerror)

            raise ECommException(ExcSeverity.Reset, CommError.SystemError, se.strerror)

    def internal_close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def on_set_read_timeout(self, new_timeout: int):
        if self.socket:
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
        return TarCon.mSrvHostName == self.mSrvHostName and TarCon.mSrvPort == self.mSrvPort

    def internal_read(self, buf, Start, MaxLength):
        if not self.socket.poll(self.ReadTimeout * 1000):
            raise ECommException(ExcSeverity.Error, CommError.Timeout)

        if self.State != ConnectionState.Connected or self.socket is None:
            return 0

        errcode = SocketError()
        avBytes = self.socket.Available
        nBytes, errcode = self.socket.Receive(buf, Start, MaxLength, SocketFlags.None)
        if nBytes == 0:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, "соединение завершено удаленной стороной")

        if errcode != SocketError.Success:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, errcode.ToString())

        return nBytes

    def internal_write(self, buf: bytes, Start: int, length: int):
        errcode = SocketError()
        _, errcode = self.socket.Send(buf, Start, length, SocketFlags.None)
        if errcode != SocketError.Success:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, errcode.ToString())

    def internal_purge_comms(self, flg: PurgeFlags):
        if self.State != ConnectionState.Connected:
            return

        if flg & PurgeFlags.RX:
            while True:
                nBytes = self.socket.Available
                if nBytes == 0:
                    break
                mem = bytearray(nBytes)
                self.socket.Receive(mem)

        if flg & PurgeFlags.TX:
            pass  # no methods for aborting tcp tx
