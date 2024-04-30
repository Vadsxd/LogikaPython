from Logika.Connections.Connection import Connection, PurgeFlags


class OfflineConnection(Connection):
    def __init__(self, owner: object):
        super().__init__("", -1)

    def dispose(self, disposing: bool):
        pass

    def internal_open(self, connect_details: str):
        connect_details = None

    def internal_close(self):
        pass

    def internal_read(self, buf: bytes, start: int, max_length: int):
        return 0

    def internal_write(self, buf: bytes, start: int, n_bytes: int):
        pass

    def on_set_read_timeout(self, new_timeout: int):
        pass

    def internal_purge_comms(self, what: PurgeFlags):
        pass

    def is_conflicting_with(self, target: Connection):
        return False
