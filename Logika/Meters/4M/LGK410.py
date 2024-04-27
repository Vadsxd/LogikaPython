from Logika.Meters.Types import MeasureKind, ImportantTag
from Logika4M import Logika4M


class TLGK410(Logika4M):
    def __init__(self):
        super().__init__()

    @property
    def SupportedByProlog4(self):
        return True

    @property
    def MeasureKind(self):
        return MeasureKind.T

    @property
    def Caption(self):
        return "ЛГК410"

    @property
    def Description(self):
        return "расходомер ЛГК410"

    @property
    def MaxChannels(self):
        return 1

    @property
    def MaxGroups(self):
        return 0

    @property
    def MaxBaudRate(self):
        return 57600

    @property
    def SupportsBaudRateChangeRequests(self):
        return False

    @property
    def SessionTimeout(self):
        return float('inf')

    @staticmethod
    def getNsDescriptions(self):
        return []

    @property
    def SupportsFLZ(self):
        return False

    @property
    def SupportsArchivePartitions(self):
        return False

    @property
    def IdentWord(self):
        return 0x460A

    def BuildEUDict(self, euTags):
        return

    @staticmethod
    def getADSTagBlocks(self):
        return []

    @staticmethod
    def GetCommonTagDefs(self):
        return {
            ImportantTag.SerialNo: "ОБЩ.serial",
            ImportantTag.NetAddr: "ОБЩ.NT",
            ImportantTag.Ident: "ОБЩ.ИД",
            ImportantTag.ParamsCSum: "ОБЩ.КСБД"
        }
