import socket
from queue import Queue

from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError


class UDPConnectionXamarin(NetConnection):
    def __init__(self, readTimeout, host, port):
        super().__init__(readTimeout, host, port)
        self.rcvBuf = bytearray(65535)
        self.inQue = Queue(65535)
        self.socket = self.CreateSocket()

    def CreateSocket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return s

    def InternalRead(self, buf, Start, Length):
        ptr = Start
        nRead = 0

        while not self.inQue.empty() and nRead < Length:
            buf[ptr] = self.inQue.get()
            ptr += 1
            nRead += 1

        if nRead < Length:
            if not self.socket.poll(self.ReadTimeout * 1000):
                raise ECommException(ExcSeverity.Error, CommError.Timeout)

            data, _ = self.socket.recvfrom(self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
            for byte in data:
                self.inQue.put(byte)

            while not self.inQue.empty() and nRead < Length:
                buf[ptr] = self.inQue.get()
                ptr += 1
                nRead += 1

        return nRead

    def InternalPurgeComms(self, flg):
        super().InternalPurgeComms(flg)
        if flg & PurgeFlags.RX:
            self.inQue.queue.clear()

    def isConflictingWith(self, Target):
        if isinstance(Target, UDPConnectionXamarin):
            TarCon = Target
            return TarCon.mSrvHostName == self.mSrvHostName and TarCon.mSrvPort == self.mSrvPort
        return False
