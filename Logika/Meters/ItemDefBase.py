from Logika.Meters.Channel import ChannelDef


class ItemDefBase:
    def __init__(self, channelDef: ChannelDef, ordinal: int, name: str, description: str, elementType):
        self.ChannelDef = channelDef
        self.Ordinal = ordinal
        self.Name = name
        self.Description = description
        self.ElementType = elementType

    @property
    def meter(self):
        return self.ChannelDef.Meter
