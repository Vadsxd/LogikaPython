from datetime import timedelta

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M, AdsTagBlock
from SPT941_20 import TSPT941_20


class TSPT944(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def ident_word(self):
        return 0x542C

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self) -> str:
        return "СПТ944"

    @property
    def Description(self) -> str:
        return "тепловычислитель СПТ944"

    @property
    def MaxChannels(self) -> int:
        return 6

    @property
    def MaxGroups(self) -> int:
        return 1

    @staticmethod
    def getNsDescriptions(self):
        return [
            "Разряд батареи",  # 00
            "Отсутствие напряжения на разъеме X1 тепловычислителя",
            "Перегрузка по цепям питания датчиков расхода",
            "Изменение сигнала на порту D1 (разъем X4)",
            "Изменение сигнала на порту D2 (разъем X6)",
            "Изменение сигнала на порту D3 (разъем X5)",
            "Изменение сигнала на порту D4 (разъем X7)",

            # 07
            "Датчик ТС1 вне диапазона 0..176 °C или -50..176°C",
            "Датчик ТС2 вне диапазона 0..176 °C или -50..176°C",
            "Датчик ТС3 вне диапазона 0..176 °C или -50..176°C",
            "Датчик ТС4 вне диапазона 0..176 °C или -50..176°C",
            "Датчик ТС5 вне диапазона 0..176 °C или -50..176°C",
            "Датчик ТС6 вне диапазона 0..176 °C или -50..176°C",
            # 13
            "Датчик ПД1 вне диапазона 0..1,03*ВП1",
            "Датчик ПД2 вне диапазона 0..1,03*ВП1",
            "Датчик ПД3 вне диапазона 0..1,03*ВП1",
            "Датчик ПД4 вне диапазона 0..1,03*ВП1",
            "Датчик ПД5 вне диапазона 0..1,03*ВП1",
            "Датчик ПД6 вне диапазона 0..1,03*ВП1",
            # 19
            "Расход через ВС1 выше верхнего предела Gв1",
            "Расход через ВС1 ниже нижнего предела Gн1",
            "Расход через ВС1 ниже отсечки самохода Gотс1",

            "Расход через ВС2 выше верхнего предела Gв2",
            "Расход через ВС2 ниже нижнего предела Gн2",
            "Расход через ВС2 ниже отсечки самохода Gотс2",

            "Расход через ВС3 выше верхнего предела Gв3",
            "Расход через ВС3 ниже нижнего предела Gн3",
            "Расход через ВС3 ниже отсечки самохода Gотс3",

            "Расход через ВС4 выше верхнего предела Gв4",
            "Расход через ВС4 ниже нижнего предела Gн4",
            "Расход через ВС4 ниже отсечки самохода Gотс4",

            "Расход через ВС5 выше верхнего предела Gв5",
            "Расход через ВС5 ниже нижнего предела Gн5",
            "Расход через ВС5 ниже отсечки самохода Gотс5",

            "Расход через ВС6 выше верхнего предела Gв6",
            "Расход через ВС6 ниже нижнего предела Gн6",
            "Расход через ВС6 ниже отсечки самохода Gотс6",

            # 37
            "Значение параметра, определяемого КУ1 вне диапазона УН1..УВ1",
            "Значение параметра, определяемого КУ2 вне диапазона УН2..УВ2",
            "Значение параметра, определяемого КУ3 вне диапазона УН3..УВ3",
            "Значение параметра, определяемого КУ4 вне диапазона УН4..УВ4",
            "Значение параметра, определяемого КУ5 вне диапазона УН5..УВ5",

            # 42
            "Ошибка описания температурного графика",
            "Ошибка связи с сервером",
            "Используется альтернативная схема учета, назначенная параметром СА1",
            "Используется альтернативная схема учета, назначенная параметром СА2",
            # 46
            "", "", "", "", "", "", "", "",
            # 54
            "Событие по расписанию 1", "Событие по расписанию 2", "", "", "", "", "", "", "", "",
            # 64
            "ТВ1: Отрицательное значение разности часовых масс теплоносителя (М1ч–М2ч) вне допустимых пределов",
            "ТВ1: Значение разности часовых масс (М1ч–М2ч) находится в пределах (-НМ)*М1ч < (М1ч–М2ч) < 0",
            "ТВ1: Значение разности часовых масс (М1ч–М2ч) находится в пределах 0 < (М1ч–М2ч) < НМ*М1ч",
            "ТВ1: Отрицательное значение часового количества тепловой энергии (Qч<0)",
            "ТВ1: Разность температур ниже допустимого предела (dt<Уdt)",
            "ТВ1: Температура теплоносителя в обратном трубопроводе выше рассчитанной по температурному графику",
            "", "", "", "", "", "", "", "", "", "",
            # 80
            "ТВ2: Отрицательное значение разности часовых масс теплоносителя (М1ч–М2ч) вне допустимых пределов",
            "ТВ2: Значение разности часовых масс (М1ч–М2ч) находится в пределах (-НМ)*М1ч < (М1ч–М2ч) < 0",
            "ТВ2: Значение разности часовых масс (М1ч–М2ч) находится в пределах 0 < (М1ч–М2ч) < НМ*М1ч",
            "ТВ2: Отрицательное значение часового количества тепловой энергии (Qч<0)",
            "ТВ2: Разность температур ниже допустимого предела (dt<Уdt)",
            "ТВ2: Температура теплоносителя в обратном трубопроводе выше рассчитанной по температурному графику",
        ]

    @staticmethod
    def GetCommonTagDefs(self):
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР",
            ImportantTag.EngUnits: ["ОБЩ.ЕИ/P", "ОБЩ.ЕИ/Q"],
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }

    @staticmethod
    def BuildEUDict(euTags):
        return TSPT941_20.BuildEUDict(euTags)

    @property
    def SupportsBaudRateChangeRequests(self) -> bool:
        return True

    @property
    def MaxBaudRate(self) -> int:
        return 57600

    @property
    def SessionTimeout(self) -> timedelta:
        return timedelta(minutes=1)  # 1 min

    @property
    def SupportsArchivePartitions(self) -> bool:
        return True

    @property
    def SupportsFLZ(self) -> bool:
        return True

    @staticmethod
    def getADSTagBlocks(self):
        return [
            AdsTagBlock(0, 0, 0, 167 + 5),  # БД ch0 5-> запас на добавление параметров в новых версиях прибора
            AdsTagBlock(100, 1, 0, 69 + 5),  # БД ch1
            AdsTagBlock(200, 2, 0, 69 + 5),  # БД ch2
            AdsTagBlock(3, ["8224", "1024", "1025"]),  # info T D
            AdsTagBlock(3, 0, 2048, 24),  # тот ОБЩ
            AdsTagBlock(103, 1, 2048, 8),  # тот ТВ1
            AdsTagBlock(203, 2, 2048, 8),  # тот ТВ2
        ]
