from enum import Enum


class M4_MeterChannel(Enum):
    SYS = 0
    TV1 = 1
    TV2 = 2


class M4Protocol:
    BROADCAST = 0xFF  # NT for broadcast requests

    FRAME_START = 0x10
    FRAME_END = 0x16

    EXT_PROTO = 0x90

    MAX_RAM_REQUEST = 0x40
    MAX_TAGS_AT_ONCE = 24

    PARTITION_CURRENT = 0xFFFF

    ALT_SPEED_FALLBACK_TIME = 10000

    ArchivePartition = PARTITION_CURRENT  # archive partition that will be read by this protocol instance