class ArchiveDescriptorElement:
    def __init__(self, archiveOrd, channel, ordinal, name, eu):
        # номер (части)архива, содержащего данную переменную (актуально для СПЕ, у которых архивы срезов состоят из
        # нескольких частей)
        self.archiveOrd = archiveOrd
        self.channel = channel
        self.ordinal = ordinal
        self.name = name
        self.eu = eu

    def __str__(self):
        desc = "{0}-{1} {2}".format(self.channel, self.ordinal, self.name)
        if self.eu:
            desc += " ({})".format(self.eu)
        return desc
