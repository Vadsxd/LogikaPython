class ItemDefBase:
    def __init__(self, channelDef, ordinal, name, description, elementType):
        self.ChannelDef = channelDef
        self.Ordinal = ordinal
        self.Name = name
        self.Description = description
        self.ElementType = elementType

    @property
    def Meter(self):
        return self.ChannelDef.Meter
