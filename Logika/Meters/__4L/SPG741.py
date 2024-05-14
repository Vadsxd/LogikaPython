from datetime import timedelta
from typing import List, Dict

from Logika.Meters.DataTag import DataTag
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4L import Logika4L, ADSFlashRun


class TSPG741(Logika4L):
    def __init__(self):
        super().__init__()
        self.sensors = ["ПД1", "ПД2", "ПД3", "ПД4", "ПД5", "ТС1", "ТС2", "СГ1", "СГ2"]

        self.sp_param_map = [
            ["P1", "dP3", "dP1", "Pб", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=0
            ["P1", "dP3", "P2", "Pб", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=1
            ["P1", "dP3", "P2", "dP1", "dP2", "t1", "t2", "Qр1", "Qр2"],  # СП=2
            ["P1", "dP2", "P2", "Pб", "dP1", "t1", "t2", "Qр1", "Qр2"],  # СП=3
            ["P1", "dP2", "P2", "dP1", "P3", "t1", "t2", "Qр1", "Qр2"],  # СП=4
            ["P1", "dP3", "dP1", "Pб", "P3", "t1", "t3", "Qр1", ""],  # СП=5
            ["P1", "dP3", "dP1", "P3", "P4", "t1", "t3", "Qр1", ""],  # СП=__6
        ]

        self.sensor_vars = ["ВД", "ТД", "ВП", "НП", "ЦИ", "КС", "КВ", "КН", "УВ", "УН", "Vн"]

    @property
    def ident_word(self):
        return 0x4729

    @property
    def measure_kind(self):
        return MeasureKind.G

    @property
    def caption(self):
        return "СПГ741"

    @property
    def description(self):
        return "корректор СПГ741"

    @property
    def max_channels(self):
        return 2

    @property
    def max_groups(self):
        return 1

    @staticmethod
    def get_common_tag_defs():
        return {
            ImportantTag.EngUnits: ["ОБЩ.[P1]", "ОБЩ.[dP1]", "ОБЩ.[P2]", "ОБЩ.[dP2]", "ОБЩ.[dP3]", "ОБЩ.[Pб]",
                                    "ОБЩ.[P3]", "ОБЩ.[P4]"],
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.RDay: "ОБЩ.СР",
            ImportantTag.RHour: "ОБЩ.ЧР"
        }

    @staticmethod
    def get_ns_descriptions():
        return [
            "Разряд батареи",  # 00
            "",
            "Перегрузка по цепям питания датчиков объема",  # 02
            "Активен входной сигнал ВС",  # 03
            "Рабочий расход Qр1 ниже нижнего предела",
            "Рабочий расход Qр2 ниже нижнего предела",
            "Рабочий расход Qр1 выше верхнего предела",
            "Рабочий расход Qр2 выше верхнего предела",  # 07
            "",
            "Входной сигнал по цепи Х12 вне диапазона",  # 09
            "Входной сигнал по цепи Х13 вне диапазона",
            "Входной сигнал по цепи Х14 вне диапазона",
            "Входной сигнал по цепи Х15 вне диапазона",
            "Входной сигнал по цепи Х16 вне диапазона",  # 13
            "Температура t1 вне диапазона",
            "Температура t2 вне диапазона",
            "Давление Р1 за пределами уставок",  # 16
            "Перепад давления dР1 за пределами уставок",
            "Рабочий расход Qр1 за пределами уставок",
            "Давление Р2 за пределами уставок",
            "Перепад давления dР2 за пределами уставок",
            "Рабочий расход Qр2 за пределами уставок",
            "Перепад давления dР3 за пределами уставок",
            "Давление Р3 за пределами уставок",
            "Давление Р4 за пределами уставок",
            "Объем выше нормы поставки",  # 25
            "Некорректные вычисления по первому трубопроводу",
            "Некорректные вычисления по второму трубопроводу"
        ]

    @property
    def supports_baud_rate_change_requests(self) -> bool:
        return False

    @property
    def max_baud_rate(self) -> int:
        return 2400

    @property
    def session_timeout(self) -> timedelta:
        return timedelta(minutes=30)

    @property
    def supports_fast_session_init(self) -> bool:
        return False

    def get_mapped_db_param_addr(self, paramName: str, sp) -> int:
        DB_FLASH_START = 0x200
        PARAM_SIZE = 16

        paramOrd = self.get_mapped_db_param_ordinal(paramName, sp)
        if paramOrd is None:
            paramOrd = 103
        addr = DB_FLASH_START + paramOrd * PARAM_SIZE

        return addr

    def get_mapped_db_param_ordinal(self, paramName: str, sp) -> int | None:
        pn = paramName.split('/')

        if len(pn) != 2:
            raise Exception("недопустимое имя параметра СПГ741: {}".format(paramName))

        sp_map = self.sp_param_map[sp]
        sensIdx = sp_map.index(pn[1])

        if sensIdx < 0:
            return None

        varIdx = self.GetMappedDBParamOrdinalsensorVars.index(pn[0])

        if varIdx < 0:
            return None

        MAPPED_PARAMS_START_NO = 100
        PARAMS_PER_SENSOR = 11

        return MAPPED_PARAMS_START_NO + sensIdx * PARAMS_PER_SENSOR + varIdx

    @staticmethod
    def build_eu_dict(euTags: List[DataTag]) -> Dict[str, str]:
        eus = {}
        if len(euTags) != 8:
            raise Exception("incorrect EU tags supplied")

        for t in euTags:
            iEU = int(t.Value) & 0x03 if isinstance(t.Value, int) else ""
            eus[t.name] = Logika4.get_gas_pressure_units(iEU)

        return eus

    @staticmethod
    def get_ads_file_layout(self, everyone: bool, model: str):
        if everyone:
            return [ADSFlashRun(0x00000, 0x17C80)]
        else:
            return [
                ADSFlashRun(0x00000, 0x4840),
                ADSFlashRun(0x13440, 0x4840)
            ]

    @staticmethod
    def get_model_from_image(self, flashImage):
        return ""

