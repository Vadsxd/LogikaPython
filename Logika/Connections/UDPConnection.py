import socket

import select

from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError
from Logika.Utils.ByteQueue import ByteQueue


class UDPConnection(NetConnection):
    def __init__(self, read_timeout, host, port):
        super().__init__(read_timeout, host, port)
        self.uc = None
        self.inQue = ByteQueue(65535)
        self.ipEndpoint = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def dispose(self, disposing: bool):
        if disposing:
            if self.uc is not None:
                self.uc.close()
                self.uc = None

    def is_conflicting_with(self, target):
        if not isinstance(target, UDPConnection):
            return False
        tar_con = target
        return tar_con.host == self.host and tar_con.port == self.port

    def internal_write(self, buf: bytes, start: int, length: int):
        self.uc.send(buf[start:start + length])

    def on_set_read_timeout(self, new_timeout: int):
        if self.uc is not None:
            self.uc.settimeout(new_timeout)

    def internal_open(self):
        self.uc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.uc.settimeout(self.read_timeout)

        try:
            self.uc.connect((self.host, self.port))

        except socket.error as se:
            try:
                self.internal_close()
            except:
                pass
            self.uc = None
            if se.errno == 11004:
                raise ECommException(ExcSeverity.Stop, CommError.SystemError, se.strerror)
            raise ECommException(ExcSeverity.Reset, CommError.SystemError, se.strerror)

    def internal_read(self, buf: bytes, start: int, max_length: int):
        ptr = start

        n_read = self.inQue.dequeue(buf, start, max_length)
        ptr += n_read

        if n_read < max_length:
            if not select.select([self.uc], [], [], self.read_timeout)[0]:
                raise ECommException(ExcSeverity.Error, CommError.Timeout)

            data, addr = self.uc.recvfrom(max_length)
            if data:
                self.inQue.enqueue(data, 0, data.length)
                n_read += self.inQue.dequeue(buf, ptr, max_length - n_read)

        return n_read

    def internal_close(self):
        if self.uc is not None:
            self.uc.close()
            self.uc = None

    def internal_purge_comms(self, what: PurgeFlags):
        while self.uc and self.uc.recv(1024):
            pass
