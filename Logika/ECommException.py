import inspect
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExcSeverity(Enum):
    # resumable
    Error = "Error"
    # connection should be re-established
    Reset = "Reset"
    # connection cannot be re-established, bus should leave stopped
    Stop = "Stop"
    # radius - connection to server is ok, but bus is temporarily unavailable (adapter not connected to srv)
    WaitRadius = "WaitRadius"


class CommError(Enum):
    Timeout = "таймаут"
    Checksum = "ошибка CRC"
    NotConnected = "нет соединения"
    SystemError = "ошибка"
    Unspecified = "?"


@dataclass
class ECommException(Exception):
    Severity: ExcSeverity
    Reason: CommError
    ExtendedInfo: Optional[str] = None

    def __init__(self, s: ExcSeverity, r: CommError, msg: str = "", ext_info: str = ""):
        super().__init__(msg)
        self.Severity = s
        self.Reason = r
        # через это поле путешествуют логи TAPI при неудачных попытках соединиться через модем
        self.ExtendedInfo = ext_info


def get_enum_description(ct):
    mem_info = inspect.getmembers(ct)
    if mem_info:
        attrs = getattr(mem_info[0][1], '__annotations__', None)
        if attrs and 'Description' in attrs:
            return attrs['Description']
    return ct.value
