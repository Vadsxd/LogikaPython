from abc import ABC, abstractmethod

from Logika.Connections.Connection import Connection


class NetConnection(Connection):
    def __init__(self, read_timeout: int, host: str, port: int):
        super().__init__(host + ":" + str(port), read_timeout)
        self.m_srv_host_name = host
        self.m_srv_port = port

    @abstractmethod
    def dispose(self, disposing: bool):
        pass

    def internal_open(self, connect_details: str):
        pass
