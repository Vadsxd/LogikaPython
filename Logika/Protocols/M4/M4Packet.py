from Logika.Protocols.M4.M4Opcode import M4Opcode
from Logika.Protocols.M4.M4Protocol import M4Protocol


class M4Packet:
    def __init__(self):
        self.NT = 0xFF
        self.Extended: bool = False
        self.ID = 0
        self.Attributes = 0
        self.FunctionCode = M4Opcode
        self.Data = bytearray()
        self.Check = 0

    def getDump(self):
        lb = [M4Protocol.FRAME_START, self.NT]

        if self.Extended:
            lb.append(M4Protocol.EXT_PROTO)
            lb.append(self.ID)
            lb.append(self.Attributes)
            payloadLen = 1 + len(self.Data)
            lb.append(payloadLen & 0xFF)
            lb.append(payloadLen >> 8)

        lb.append(self.FunctionCode.value)
        lb.extend(self.Data)

        if self.Extended:
            lb.append(self.Check >> 8)
            lb.append(self.Check & 0xFF)
        else:
            lb.append(self.Check & 0xFF)
            lb.append(M4Protocol.FRAME_END)

        return bytes(lb)
