from Logika.Connections.Connection import Connection


class OfflineConnection(Connection):
    def __init__(self, owner):
        super().__init__("", -1)

    def dispose(self, disposing: bool):
        pass

    def internal_open(self,  connect_details: str):
        return None

    def internal_close(self):
        pass

    def internal_read(self, buf, start: int, max_length: int):
        return 0

    def internal_write(self, buf, start: int, n_bytes: int):
        pass

    def on_set_read_timeout(self, new_timeout):
        pass

    def internal_purge_comms(self, what):
        pass

    def is_conflicting_with(self, target):
        return False
