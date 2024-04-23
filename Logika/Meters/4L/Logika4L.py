from enum import Enum
import struct
from datetime import datetime, timezone
from Logika.Meters.Logika4 import Logika4
from Logika.Meters.StandardVars import StdVar
from Logika.Meters.TagDef import TagDef4L
from Logika.Meters.Types import ArchiveType


class BinaryType(Enum):
    undefined = 0
    r32 = 1  # single microchip-float
    r32x3 = 2  # triple consequtive microchip floats, sum to obtain result
    time = 3  # HH MM SS (3 bytes)
    date = 4  # YY MM DD (3 bytes)
    MMDD = 5  # ММ-DD-xx-xx (32-bit) (дата перехода на летнее/зимнее время)
    bitArray32 = 6  # сборки НС
    bitArray24 = 7
    bitArray16 = 8
    bitArray8 = 9
    # параметр БД приборов 942, 741, (943?), структура, используется строка
    dbentry = 10
    # параметр БД приборов, используется бинарное представление ([P], [dP] - единицы измерения 741)
    dbentry_byte = 11
    u8 = 12  # unsigned 8bit char
    i32r32 = 13  # int32+float во FLASH (+ float приращение за текущий час в ОЗУ, не читаем и не добавляем)
    MMHH = 14  # minutes, hours (941: 'ТО' )
    NSrecord = 15
    IZMrecord = 16
    archiveStruct = 17  # архивный срез (структура, определяемая прибором)
    modelChar = 18  # код модели прибора
    u24 = 19  # серийный номер прибора
    svcRecordTimestamp = 20  # метка времени записи сервисного архива


class ADSFlashRun:
    def __init__(self, start, length):
        self.Start = start
        self.Length = length


class Logika4L(Logika4):
    def __init__(self):
        super().__init__()
        self.SupportedByProlog4 = True
        self.Outdated = True

    FLASH_PAGE_SIZE = 0x40
    PARAMS_FLASH_ADDR = 0x0200

    lcd_char_map = ['Б', 'Г', 'ё', 'Ж', 'З', 'И', 'Й', 'Л', 'П', 'У', 'Ф', 'Ч', 'Ш', 'Ъ', 'Ы', 'Э', 'Ю', 'Я', 'б', 'в',
                    'г', 'ё', 'ж', 'з', 'и', 'й', 'к', 'л', 'м', 'н', 'п', 'т', 'ч', 'ш', 'ъ', 'ы', 'ь', 'э', 'ю', 'я',
                    ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                    ' ', ' ', ' ', ' ', 'Д', 'Ц', 'Щ', 'д', 'ф', 'ц', 'щ']

    @staticmethod
    def GetValue(binaryType, buffer, offset, operFlag):
        operFlag = False

        if binaryType == BinaryType.r32:
            Val = Logika4L.GetMFloat(buffer, offset)
            return Val

        elif binaryType == BinaryType.time:
            t = datetime(2000, 1, 1, buffer[offset], buffer[offset + 1], buffer[offset + 2],
                         tzinfo=timezone.utc)
            return t.strftime("%H:%M:%S")  # long time pattern

        elif binaryType == BinaryType.date:
            d = datetime(2000 + buffer[offset], buffer[offset + 1], buffer[offset + 2], tzinfo=timezone.utc)
            return d.strftime("%d/%m/%y")

        elif binaryType == BinaryType.MMDD:
            Dt = datetime(2000, buffer[offset], buffer[offset + 1], tzinfo=timezone.utc)
            return Dt.strftime("%d/%m")

        elif binaryType == BinaryType.bitArray8:
            return BitNumbers(buffer[offset], 8, 0)

        elif binaryType == BinaryType.bitArray16:
            usv = int.from_bytes(buffer[offset:offset + 2], byteorder='little')
            return BitNumbers(usv, 16, 8)

        elif binaryType == BinaryType.bitArray24:
            bExt = bytearray([0, 0, 0]) + buffer[offset:offset + 3]
            ulv = int.from_bytes(bExt, byteorder='little')
            return BitNumbers(ulv, 24, 0)

        elif binaryType == BinaryType.bitArray32:
            u32v = int.from_bytes(buffer[offset:offset + 4], byteorder='little')
            return BitNumbers(u32v, 32, 0)

        elif binaryType == BinaryType.dbentry:
            PARAM_BIN_PART_LEN = 4
            PARAM_STR_LEN = 8
            strPartOffset = offset + PARAM_BIN_PART_LEN
            if buffer[strPartOffset] == 0xFF:
                operFlag = False
                return ""
            operFlag = (buffer[offset] & 0x01) > 0
            c = buffer[strPartOffset:strPartOffset + PARAM_STR_LEN].decode('utf-8').strip('\0 ')
            return c

        elif binaryType == BinaryType.dbentry_byte:
            operFlag = (buffer[offset] & 0x01) > 0
            return buffer[offset + 12]

        elif binaryType == BinaryType.u8:
            return buffer[offset]

        elif binaryType == BinaryType.r32x3:
            v1 = Logika4L.GetMFloat(buffer, offset)
            v2 = Logika4L.GetMFloat(buffer, offset + 4)
            v3 = Logika4L.GetMFloat(buffer, offset + 8)
            return v1 + v2 + v3

        elif binaryType == BinaryType.i32r32:
            intPart = int.from_bytes(buffer[offset:offset + 4], byteorder='little', signed=True)
            floatPart = Logika4L.GetMFloat(buffer, offset + 4)
            vtv = float(intPart) + floatPart
            return vtv

        elif binaryType == BinaryType.MMHH:
            mh = datetime(2000, 1, 1, buffer[offset + 1], buffer[offset], 0)
            return mh.strftime("%H:%M")  # long time pattern

        elif binaryType == BinaryType.u24:
            return int.from_bytes(buffer[offset:offset + 3], byteorder='little') & 0x00FFFFFF

        elif binaryType == BinaryType.modelChar:
            return chr(buffer[offset])

        elif binaryType == BinaryType.svcRecordTimestamp:
            if buffer[offset] != 0x10:
                return None

            year = buffer[offset + 1]
            mon = buffer[offset + 2]
            day = buffer[offset + 3]
            hour = buffer[offset + 4]
            minutes = buffer[offset + 5]

            if year == 0xFF or mon == 0 or mon > 12 or day == 0 or day > 31 or hour > 23 or min > 59:
                return datetime.min
            try:
                return datetime(year + 2000, mon, day, hour, minutes, 0, tzinfo=timezone.utc)
            except ValueError:
                return datetime.min

        elif binaryType == BinaryType.NSrecord:
            return f"НС{buffer[offset + 6]:02d}{'+' if (buffer[offset + 7] & 1) > 0 else '-'}"

        elif binaryType == BinaryType.IZMrecord:
            return LcdCharsToString(buffer, offset + 8, 16).strip()

        else:
            raise Exception(f"unsupported binary type in GetValue: '{binaryType}'")

    @staticmethod
    def SizeOf(dataType):
        if dataType == BinaryType.u8 or dataType == BinaryType.bitArray8:
            return 1
        elif dataType == BinaryType.bitArray16:
            return 2
        elif dataType == BinaryType.bitArray24:
            return 3
        elif dataType == BinaryType.bitArray32:
            return 4
        elif dataType == BinaryType.MMHH:
            return 2
        elif dataType in [BinaryType.time, BinaryType.date, BinaryType.r32, BinaryType.MMDD]:
            return 4
        elif dataType == BinaryType.i32r32:
            return 8
        elif dataType == BinaryType.NSrecord:
            return 8
        elif dataType == BinaryType.r32x3:
            return 12
        elif dataType in [BinaryType.dbentry, BinaryType.dbentry_byte]:
            return 16
        elif dataType == BinaryType.IZMrecord:
            return 24
        elif dataType == BinaryType.modelChar:
            return 1
        elif dataType == BinaryType.u24:
            return 4
        else:
            raise Exception("unknown type")

    @staticmethod
    def GetMFloat(buf, offset):
        i = int.from_bytes(buf[offset:offset + 4], byteorder='little')

        sign = (i >> 23) & 1
        exponent = i >> 24
        mantissa = i & 0x007FFFFF

        i = (exponent << 23) | (sign << 31) | mantissa

        if (i & 0x7F800000) == 0x7F800000:
            i &= 0xFF7FFFFF

        return struct.unpack('<f', i.to_bytes(4, byteorder='little'))[0]

    @staticmethod
    def LcdCharsToString(buf, offset, length):
        result = [''] * length

        for i in range(length):
            rCh = chr(buf[offset + i])
            result[i] = rCh if ord(rCh) < 0xA0 or ord(rCh) > 0xEF else Logika4L.lcd_char_map[ord(rCh) - 0xA0]

        return ''.join(result)

    @staticmethod
    def syncHeaderToDatetime(arType, rd, rh, buffer, offset):
        rawhdr = int.from_bytes(buffer[offset:offset + 4], byteorder='little')
        if rawhdr == 0x00000000 or rawhdr == 0xFFFFFFFF:
            return None

        year = buffer[offset]
        mon = buffer[offset + 1]
        day = rd if arType == ArchiveType.Month else buffer[offset + 2]
        hour = buffer[offset + 3] if arType == ArchiveType.Hour else rh

        try:
            if mon < 1 or mon > 12 or day == 0 or day > 31 or hour > 23:
                return None
            return datetime(year + 1900, mon, day, hour, 0, 0)
        except ValueError:
            return None

    @property
    def FamilyName(self):
        return "L4"

    @property
    def tagsSort(self):
        return "Device, Channel, Ordinal"

    @property
    def archiveFieldsSort(self):
        return "Device, ArchiveType, FieldOffset"

    def getModelFromImage(self, flashImage):
        pass

    def getAdsFileLayout(self, everyone, model):
        pass

    def readTagDef(self, r):
        self.readCommonDef(r)
        chKey = r["Channel"]
        ch = next((x for x in self.Channels if x.Prefix == chKey), None)
        dbType = r["dbType"] if r["dbType"] is not None else None
        units = str(r["Units"])
        displayFormat = str(r["DisplayFormat"])
        sNativeType = str(r["InternalType"])
        nativeType = BinaryType[sNativeType]
        inRam = bool(r["InRAM"])
        addr = r["Address"] if r["Address"] is not None else None
        chOfs = r["ChannelOffset"] if r["ChannelOffset"] is not None else None
        addonAddr = r["Addon"] if r["Addon"] is not None else None
        addonChOfs = r["AddonOffset"] if r["AddonOffset"] is not None else None
        return TagDef4L(ch, name, stv, kind, isBasicParam, updRate, ordinal, desc, dataType, dbType, units,
                        displayFormat, descriptionEx, ranging, nativeType, inRam, addr, chOfs, addonAddr, addonChOfs)

    def readArchiveDefs(self, rows):
        d = []
        for r in rows:
            chKey = r["Channel"]
            ch = next((x for x in self.Channels if x.Prefix == chKey), None)
            art = ArchiveType.FromString(r["ArchiveType"])
            name = r["Name"]
            desc = r["Description"]
            sRecType = "System." + r["RecordType"]
            recType = type(sRecType)
            recSize = r["RecordSize"]
            count = r["Count"]
            idx1 = r["Index1"]
            hdr1 = r["Headers1"] if r["Headers1"] is not None else None
            rec1 = r["Records1"]
            idx2 = r["Index2"] if r["Index2"] is not None else None
            hdr2 = r["Headers2"] if r["Headers2"] is not None else None
            rec2 = r["Records2"] if r["Records2"] is not None else None
            ra = ArchiveDef4L(ch, art, recType, count, name, desc, recSize, idx1, hdr1, rec1, idx2, hdr2, rec2, False)
            d.append(ra)

        return d

    def readArchiveFieldDef(self, r):
        art = ArchiveType.FromString(r["ArchiveType"])
        ra = next((x for x in self.Archives if x.ArchiveType == art), None)
        sDataType = "System." + r["DataType"]
        t = type(sDataType)
        sDbType = str(r["DbType"])
        name = r["Name"]
        desc = r["Description"]
        stdType = r["VarT"]
        units = r["Units"]
        displayFormat = None
        nativeType = BinaryType[r["InternalType"]]
        offset = r["FieldOffset"]
        stv = StdVar.unknown if r["VarT"] is None else StdVar[r["VarT"]]

        return ArchiveFieldDef4L(ra, name, desc, stv, t, sDbType, units, displayFormat, nativeType, offset)
