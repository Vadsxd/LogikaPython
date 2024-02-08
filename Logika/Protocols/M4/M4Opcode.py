from enum import Enum


class M4Opcode(Enum):
    # legacy x4 packet opcodes (fixed 4 byte data (with an exception for write 2nd op))
    Error = 0x21
    Handshake = 0x3F
    SetSpeed = 0x42
    WriteParam = 0x44
    ReadFlash = 0x45
    CalcControl = 0x4F
    ReadRam = 0x52
    DeviceDiscovery = 0xF0  # автообнаружение устройств на шине (ЛГК410)
    SessionClose = 0x71
    # modern M4 protocol opcodes
    ReadArchive = 0x61
    ReadTags = 0x72
    WriteTags = 0x77
    SetTechnologicalNT = 0xF1  # установка NT для технологического режима (ЛГК410)
