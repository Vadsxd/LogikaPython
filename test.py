from Logika.Connections.TCPConnection import TCPConnection

if __name__ == '__main__':
    buffer = bytes([0xff, 0xff, 0xff])
    con = TCPConnection(30000, "127.0.0.1", 8084)
    con.open()
    con.write(buffer, 0, 3)
