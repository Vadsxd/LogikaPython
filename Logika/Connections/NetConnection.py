from abc import ABC

from Logika.Connections.Connection import Connection


class NetConnection(ABC, Connection):
    def __init__(self, read_timeout: int, host: str, port: int):
        super().__init__(host + ":" + str(port), read_timeout)
        self.m_srv_host_name: str = host
        self.m_srv_port: int = port
