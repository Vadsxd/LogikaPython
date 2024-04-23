from Logika.Meters import TagDef


class ArchiveFieldDef(TagDef):
    def __init__(self, channel, ordinal, at, name, description, stndVar, data_type, dbType, displayFormat):
        super().__init__(channel, ordinal, name, stndVar, description, data_type, dbType, displayFormat)
        self.ArchiveType = at

    def __str__(self):
        return "{0} {1}".format(self.ChannelDef.Prefix, self.Name)


class ArchiveFieldDef6(ArchiveFieldDef):
    def __init__(self, ch, at, name, desc, ordinal, standard_variable, data_type, dbType, displayFormat):
        super().__init__(ch, ordinal, at, name, desc, standard_variable, data_type, dbType, displayFormat)
        self.NameSuffixed = name
        ptPos = name.find('(')
        if ptPos > 0 and name.endswith(")"):
            self.Name = name[:ptPos]

    @property
    def Address(self):
        return format(self.Ordinal, "000")

    @property
    def Key(self):
        return self.Address


class ArchiveFieldDef4(ArchiveFieldDef):
    def __init__(self, ar, name, desc, stdVar, data_type, dbType, displayFormat, units):
        super().__init__(ar.ChannelDef, -1, ar.ArchiveType, name, desc, stdVar, data_type, dbType, displayFormat)
        self.Archive = ar
        self.Units = units

    @property
    def Key(self):
        return self.Name


class ArchiveFieldDef4L(ArchiveFieldDef4):
    def __init__(self, ar, name, desc, stdVar, data_type, dbType, units, displayFormat, binType, fldOffset):
        super().__init__(ar, name, desc, stdVar, data_type, dbType, displayFormat, units)
        self.InternalType = binType
        self.FieldOffset = fldOffset


class ArchiveFieldDef4M(ArchiveFieldDef4):
    def __init__(self, ar, fieldIndex, name, desc, standardVariable, data_type, dbType, displayFormat, units):
        super().__init__(ar, name, desc, standardVariable, data_type, dbType, displayFormat, units)
        self.FieldIndex = fieldIndex

    def __str__(self):
        return "{0} {1}".format(self.ChannelDef.Prefix, self.Name)
