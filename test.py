from Logika.Connections.Connection import PurgeFlags
from Logika.Connections.TCPConnection import TCPConnection
from Logika.Connections.UDPConnection import UDPConnection
from Logika.Protocols.M4.M4Protocol import M4Protocol


def test_M4():
    ip_address = "91.209.59.238"
    port = 8002
    m4 = M4Protocol()
    con = TCPConnection(30000, ip_address, port)
    con.open()
    m4.connection = con
    m4.read_service_archive_4M()


def test_tcp():
    buffer = bytes([0xff, 0xff, 0xff])
    con = TCPConnection(30000, "127.0.0.1", 8084)
    con.open()
    con.write(buffer, 0, 3)
    con.close()


def test_udp():
    buffer = bytes([0xff, 0xff, 0xff])
    udp_con = UDPConnection(30000, "127.0.0.1", 8083)
    udp_con.open()
    udp_con.write(buffer, 0, 3)
    udp_con.purge_comms(PurgeFlags.RX)
    udp_con.close()


if __name__ == '__main__':
    test_tcp()
    test_udp()
    test_M4()
