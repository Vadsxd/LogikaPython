import socket
import threading

from select import select

from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError
from Logika.Connections.Connection import ConnectionState, PurgeFlags


class TCPConnection(NetConnection):
    def __init__(self, readTimeout, host, port):
        super().__init__(readTimeout, host, port)
        self.socket = None
        self.WSAETIMEDOUT = 10060
        self.connectEnded = threading.Event()
        self.connectException = None

    def dispose(self, disposing: bool):
        if disposing:
            if self.socket:
                self.socket.close()
                self.socket = None

    def internal_open(self, connect_details: str):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(True)

        connectDetails = None

        self.connectEnded.clear()
        self.connectException = None

        try:
            self.socket.connect((self.host, self.port))

            ready, _, _ = select([], [self.socket], [], max(self.readTimeout, 15))
            if not ready:
                self.socket.close()
                self.socket = None
                raise socket.error(self.WSAETIMEDOUT)
            else:
                if self.connectException:
                    raise self.connectException

        except socket.error as se:
            if se.errno == socket.errno.ENOENT:
                raise ECommException(ExcSeverity.Stop, CommError.SystemError, se.strerror)

            raise ECommException(ExcSeverity.Reset, CommError.SystemError, se.strerror)

    def internal_close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def on_set_read_timeout(self, newTimeout):
        if self.socket:
            self.socket.settimeout(newTimeout)

    def on_connect(self):
        try:
            self.socket.getpeername()

        except Exception as e:
            self.connectException = e

        finally:
            self.connectEnded.set()

    def isConflictingWith(self, Target):
        if not isinstance(Target, TCPConnection):
            return False
        TarCon = Target
        return TarCon.mSrvHostName == self.mSrvHostName and TarCon.mSrvPort == self.mSrvPort

    def InternalRead(self, buf, Start, MaxLength):
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

    def InternalWrite(self, buf, Start, len):
        errcode = SocketError()
        _, errcode = self.socket.Send(buf, Start, len, SocketFlags.None)
        if errcode != SocketError.Success:
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, errcode.ToString())

    def InternalPurgeComms(self, flg):
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
