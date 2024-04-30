from datetime import timedelta, datetime
from enum import Enum, auto
from typing import List, Dict


class MeasureKind(Enum):
    T = "тепло/вода"
    G = "газ"
    E = "электроэнергия"


class BusProtocolType(Enum):
    SPbus = 6
    RSbus = 4

    def __str__(self):
        descriptions = {
            BusProtocolType.SPbus: "СПСеть",
            BusProtocolType.RSbus: "M4",
        }
        return descriptions[self]


class TagKind(Enum):
    Undefined = "?"
    Parameter = "настроечные"
    Info = "информационные"
    Realtime = "текущие"
    TotalCtr = "тотальные"


class ArchiveTimingType(Enum):
    # не архив (набор тэгов)
    NoneType = auto()
    # интервальный архив
    Synchronous = auto()
    # сервисный архив
    Asynchronous = auto()


class ArchiveType:
    atDict: Dict[str, 'ArchiveType'] = {}

    Hour = None
    Day = None
    Decade = None
    Month = None
    ParamsLog = None
    PowerLog = None
    ErrorsLog = None
    Control = None
    Minute = None
    HalfHour = None
    Turn = None
    Diags = None

    def __init__(self, name: str, description: str, timingType: ArchiveTimingType, acronym: str, intvSpan: timedelta):
        self.Name = name
        self.Description = description
        self.Timing = timingType
        self.Acronym = acronym
        self.Interval = intvSpan
        self.VariableInterval = False

        ArchiveType.atDict[name] = self

    @property
    def is_interval_archive(self):
        return self.Timing == ArchiveTimingType.Synchronous

    @property
    def is_service_archive(self):
        return self.Timing == ArchiveTimingType.Asynchronous

    def __str__(self):
        return self.Name

    @staticmethod
    def from_string(archiveName):
        return ArchiveType.atDict[archiveName]

    @property
    def all(self) -> List['ArchiveType']:
        return list(ArchiveType.atDict.values())


class VQT:
    def __init__(self):
        self.Value = None
        self.Quality = 0
        self.Timestamp = datetime.now()

    def __str__(self):
        return self.Timestamp.strftime("%d.%m.%Y - %H:%M:%S") + " - " + (
            "[null]" if self.Value is None else str(self.Value))


class HistoricalSeries:
    def __init__(self):
        self.ClientHandle = 0
        self.Data = []


class ImportantTag(Enum):
    Ident = 1  # ИД или 008
    Model = 2  # модель (исполнение) прибора
    SerialNo = 3  # серийный номер платы
    NetAddr = 4  # сетевой адрес
    RDay = 5  # расчетные сутки
    RHour = 6  # расчетный час
    EngUnits = 7  # единицы измерения
    ParamsCSum = 8  # контрольная сумма БД, рассчитанная прибором


class VitalInfo:
    def __init__(self):
        self.id = ""  # ИД прибора из настроечной БД
        self.hwRev = ""  # модель (x4) / 099н00 (x6)
        self.hwSerial = ""  # серийный номер
        self.intfConfig = []  # конфигурация интерфейсов
        self.nt = None  # сетевой адрес
        self.rd = None  # расчетные сутки
        self.rh = None  # расчетный час
        self.mtrParamsHash = ""  # контрольная сумма БД (рассчитанная прибором)
        self.clockDiff = None  # clockDiff = Tdevice - Tcomp. Tdevice = Tcomp + clockDiff


class ColumnInfo:
    def __init__(self):
        self.name = ""
        self.dataType = ""
        self.nullable = False

    def __str__(self):
        return self.name

    def equals(self, other):
        return (
                self.name.lower() == other.name.lower() and
                self.dataType.lower() == other.dataType.lower() and
                self.nullable == other.nullable
        )


ArchiveType.Hour = ArchiveType("Hour", "часовой архив", ArchiveTimingType.Synchronous, "Час", timedelta(hours=1))
ArchiveType.Day = ArchiveType("Day", "суточный архив", ArchiveTimingType.Synchronous, "Сут", timedelta(days=1))
ArchiveType.Decade = ArchiveType("Decade", "декадный архив", ArchiveTimingType.Synchronous, "Дек", timedelta(days=10))
ArchiveType.Month = ArchiveType("Month", "месячный архив", ArchiveTimingType.Synchronous, "Мес", timedelta(days=30))
ArchiveType.ParamsLog = ArchiveType("ParamsLog", "изменения БД", ArchiveTimingType.Asynchronous, "Изм", timedelta(0))
ArchiveType.PowerLog = ArchiveType("PowerLog", "перерывы питания", ArchiveTimingType.Asynchronous, "Пит", timedelta(0))
ArchiveType.ErrorsLog = ArchiveType("ErrorsLog", "нештатные", ArchiveTimingType.Asynchronous, "НСа", timedelta(0))
ArchiveType.Control = ArchiveType("Control", "контрольный архив", ArchiveTimingType.Synchronous, "Контр",
                                  timedelta(days=1))
ArchiveType.Minute = ArchiveType("Minute", "минутный архив", ArchiveTimingType.Synchronous, "Мин", timedelta(0))
ArchiveType.Minute.VariableInterval = True
ArchiveType.HalfHour = ArchiveType("HalfHour", "[полу]часовой архив", ArchiveTimingType.Synchronous, "ПЧас",
                                   timedelta(0))
ArchiveType.HalfHour.VariableInterval = True
ArchiveType.Turn = ArchiveType("Turn", "сменный архив", ArchiveTimingType.Asynchronous, "См", timedelta(0))
ArchiveType.Diags = ArchiveType("DiagsLog", "диагностические", ArchiveTimingType.Asynchronous, "ДСа", timedelta(0))
