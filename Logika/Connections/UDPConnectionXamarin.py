import socket
from queue import Queue

import select

from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.NetConnection import NetConnection
from Logika.ECommException import ECommException, ExcSeverity, CommError


class UDPConnectionXamarin(NetConnection):
    def __init__(self, readTimeout, host, port):
        super().__init__(readTimeout, host, port)
        self.rcv_buf: bytearray = bytearray(65535)
        self.in_que: Queue = Queue(65535)
        self.socket: socket = self.create_socket()

    @staticmethod
    def create_socket() -> socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return s

    def internal_read(self, buf: bytearray, start: int, length: int) -> int:
        ptr = start
        n_read = 0

        while not self.in_que.empty() and n_read < length:
            buf[ptr] = self.in_que.get()
            ptr += 1
            n_read += 1

        if n_read < length:
            readable, _, _ = select.select([socket], [], [], self.ReadTimeout * 1000)
            if not readable:
                raise ECommException(ExcSeverity.Error, CommError.Timeout)

            data, _ = self.socket.recvfrom(self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF))
            for byte in data:
                self.in_que.put(byte)

            while not self.in_que.empty() and n_read < length:
                buf[ptr] = self.in_que.get()
                ptr += 1
                n_read += 1

        return n_read

    def internal_purge_comms(self, flg: PurgeFlags):
        super().internal_purge_comms(flg)
        if flg & PurgeFlags.RX:
            self.in_que.queue.clear()

    def is_conflicting_with(self, target) -> bool:
        if isinstance(target, UDPConnectionXamarin):
            TarCon = target
            return TarCon.mSrvHostName == self.mSrvHostName and TarCon.mSrvPort == self.mSrvPort
        return False
