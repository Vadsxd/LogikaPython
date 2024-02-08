from enum import Enum


class M4ArchiveId(Enum):  # код архива в протокольном запросе
    Hour = 0
    Day = 1
    Dec = 2
    Mon = 3
    ParamsLog = 4  # Изменения БД
    PowerLog = 5  # перерывы питания
    NSLog = 6  # НС
    Ctrl = 7  # контрольный архив
