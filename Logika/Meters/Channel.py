from enum import Enum
from Meter import Meter


class ChannelKind(Enum):
    Undefined = 0
    Common = 1
    header = 2
    Channel = 3  # measuring channel pipe.СПТ(Г): "т", СПЕ: "к"
    Group = 4  # group of channels / consumer.СПТ(Г): "п", СПЕ: "г"
    TV = 5


class ChannelDef:
    Prefix = None

    def __init__(self, meter: Meter, Prefix: str, Start: int, Count: int, Description: str, a: 'ChannelDef' = None):
        if a:
            self.Meter = a.Meter
            self.Kind = a.Kind
            self.Prefix = a.Prefix
            self.Start = a.Start
            self.Count = a.Count
            self.Description = a.Description
        else:
            self.Meter = meter
            self.Kind = meter.get_channel_kind(Start, Count, Prefix)
            self.Prefix = Prefix
            self.Start = Start
            self.Count = Count
            self.Description = Description

    def __str__(self):
        return self.Prefix + " (" + self.Description + ")"


class Channel(ChannelDef):
    def __init__(self, cdef: 'ChannelDef', channelNo: int):
        super().__init__(Meter(), '', 0, 0, '', cdef)
        self.No = channelNo
        self.Name = cdef.Prefix + (str(channelNo) if channelNo > 0 else "")

    def __str__(self):
        return self.Name + " (" + self.Description + ")"
