from datetime import datetime
from Logika.Meters.Meter import Meter
from Logika.Meters.Types import ArchiveType


class Archive:
    FLD_EXTPROP_KEY = "AfInfo"

    def __init__(self, mtr: Meter, arType: ArchiveType):
        self.Meter = mtr
        self.ArchiveType = arType


class IntervalArchive(Archive):
    def __init__(self, mtr: Meter, arType: ArchiveType):
        super().__init__(mtr, arType)

        if not arType.is_interval_archive:
            raise ValueError("wrong archive type")

        self.Table = DataTable("{0}-{1}".format(type(mtr).__name__, arType.Name))
        dt_tc = self.Table.Columns.Add("tm", datetime)
        self.Table.PrimaryKey = [dt_tc]
        self.Fields = ArchiveFieldCollection(self)

    def __init__(self, mtr: Meter, arType: ArchiveType, template: DataTable):
        self.__init__(mtr, arType)

        if not arType.is_interval_archive:
            raise ValueError("wrong archive type")

        for c in template.Columns:
            if c.ColumnName.lower() != "tm":
                newCol = self.Table.Columns.Add(c.ColumnName, c.DataType)
                for k in c.ExtendedProperties.Keys:
                    newCol.ExtendedProperties[k] = c.ExtendedProperties[k]


class ArchiveFieldCollection:
    def __init__(self, owner: IntervalArchive):
        self.owner = owner

    def __getitem__(self, index):
        return self.owner.Table.Columns[index].ExtendedProperties[Archive.FLD_EXTPROP_KEY]

    def __setitem__(self, index, value):
        self.owner.Table.Columns[index].ExtendedProperties[Archive.FLD_EXTPROP_KEY] = value

    def __len__(self):
        return len(self.owner.Table.Columns)

    @property
    def sync_root(self):
        return self.owner.Table.Columns

    @property
    def is_synchronized(self) -> bool:
        return False

    @property
    def is_read_only(self):
        return True

    def copy_to(self, array, index):
        vta = [self.owner.Table.Columns[i].ExtendedProperties[Archive.FLD_EXTPROP_KEY] for i in
               range(len(self.owner.Table.Columns))]
        for i, v in enumerate(vta):
            array[index + i] = v

    def __add__(self, other):
        raise Exception("read-only collection")

    def clear(self, item):
        raise Exception("read-only collection")

    def remove(self, item):
        raise Exception("read-only collection")

    def __contains__(self, item):
        raise NotImplementedError()

    def __iter__(self):
        for c in self.owner.Table.Columns:
            yield c.ExtendedProperties[Archive.FLD_EXTPROP_KEY]


class ServiceRecord:
    def __init__(self, tm, event, description):
        self.tm = tm
        self.event = event
        self.description = description

    def __str__(self):
        return "{0} {1} {2}".format(self.tm, self.event, self.description)


class ServiceArchive(Archive):
    def __init__(self, mtr, arType):
        super().__init__(mtr, arType)

        if not arType.is_service_archive:
            raise ValueError("wrong archive type")

        self.Records = []

    def __str__(self):
        return "Service Archive"
