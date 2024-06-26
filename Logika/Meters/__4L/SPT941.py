from datetime import timedelta

from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4L import Logika4L, ADSFlashRun


class TSPT941(Logika4L):
    def __init__(self):
        super().__init__()

    @property
    def ident_word(self):
        return 0x5429

    @property
    def measure_kind(self):
        return MeasureKind.T

    @property
    def caption(self):
        return "СПТ941"

    @property
    def description(self):
        return "тепловычислитель СПТ941, мод. 01 - 08"

    @property
    def max_channels(self):
        return 3

    @property
    def max_groups(self):
        return 1

    @property
    def supported_by_prolog4(self):
        return False

    def build_eu_dict(self, euTags):
        raise NotImplementedError("not supported")

    @staticmethod
    def get_model_from_image(self, flashImage):
        return ""

    @staticmethod
    def get_common_tag_defs(self):
        return {
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
        }

    @staticmethod
    def get_ns_descriptions(self):
        return [
            "Разряд батареи",
            "Выход температуры на ТС1 за диапазон",
            "Выход температуры на ТС2 за диапазон",
            "Перегрузка цепи питания ВС",
            "Масса М3 (ГВС) меньше минус 0,04 М1",
            "Отрицательная тепловая энергия"
        ]

    @property
    def supports_baud_rate_change_requests(self):
        return False

    @property
    def max_baud_rate(self):
        return 2400

    @property
    def session_timeout(self):
        return timedelta(minutes=30)

    @property
    def supports_fast_session_init(self):
        return False

    @staticmethod
    def get_ads_file_layout(self, everyone, model):
        if everyone:
            return [
                ADSFlashRun(0x00000, 0xD880)
            ]
        else:
            return [
                ADSFlashRun(0x00000, 0x1700),
                ADSFlashRun(0x09E00, 0x3A80)
            ]

    @staticmethod
    def expand_hour_record(hour_rec):
        norm_rec = [None] * 12
        norm_rec[:4] = hour_rec[:4]  # SP NS T1 T2 are in place already

        sp = hour_rec[0]
        v12, v23, m12, m23, q = hour_rec[4:9]

        if sp == 0:
            norm_rec[4] = v12
            norm_rec[5] = v23
            norm_rec[6] = None
            norm_rec[7] = m12  # m1
            norm_rec[8] = m23  # m2
            norm_rec[9] = m12 - m23
        elif sp == 1:
            norm_rec[4] = v12
            norm_rec[5] = None
            norm_rec[6] = v23
            norm_rec[7] = m12
            norm_rec[8] = m23
            norm_rec[9] = m12 - m23
        elif sp == 2:
            norm_rec[4] = None
            norm_rec[5] = v12
            norm_rec[6] = v23
            norm_rec[7] = m12
            norm_rec[8] = m23
            norm_rec[9] = m12 - m23
        elif sp in [3, 4]:
            norm_rec[4] = v12
            norm_rec[5] = v23
            norm_rec[6] = None
            norm_rec[7] = m12
            norm_rec[8] = m23
            norm_rec[9] = None
        elif sp == 5:
            norm_rec[4] = v12
            norm_rec[5] = None
            norm_rec[6] = v23
            norm_rec[7] = m12
            norm_rec[8] = None
            norm_rec[9] = m23
        elif sp == 6:
            norm_rec[4] = None
            norm_rec[5] = v12
            norm_rec[6] = v23
            norm_rec[7] = None
            norm_rec[8] = m12
            norm_rec[9] = m23
        elif sp == 7:
            norm_rec[3] = None  # t2
            norm_rec[4] = v12
            norm_rec[5] = None
            norm_rec[6] = None
            norm_rec[7] = m12
            norm_rec[8] = None
            norm_rec[9] = None
        elif sp == 8:
            norm_rec[4] = v12
            norm_rec[5] = v23
            norm_rec[6] = None
            norm_rec[7] = m12
            norm_rec[8] = None
            norm_rec[9] = None
        elif sp == 9:
            norm_rec[4] = v12
            norm_rec[5] = v23
            norm_rec[6] = None
            norm_rec[7] = None
            norm_rec[8] = None
            norm_rec[9] = None

        norm_rec[10] = q
        norm_rec[11] = None  # have no Ti

        return norm_rec
