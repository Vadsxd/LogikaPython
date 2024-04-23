class Conversions:
    sr = ['А', 'В', 'Е', 'К', 'М', 'Н', 'О', 'Р', 'С', 'Т', 'Х', 'а', 'е', 'о', 'р', 'с', 'у', 'х']
    sl = ['A', 'B', 'E', 'K', 'M', 'H', 'O', 'P', 'C', 'T', 'X', 'a', 'e', 'o', 'p', 'c', 'y', 'x']

    @staticmethod
    def str_to_limited_byte(value, min_val, max_val):
        if not value or value.isspace():
            return None
        try:
            result = int(value)
        except ValueError:
            return None
        if result < min_val or result > max_val:
            return None
        return result

    @staticmethod
    def rus_string_to_stable_alphabet(s):
        if s is None:
            return None
        res = list(s)
        for i in range(len(res)):
            ci = Conversions.sr.index(res[i]) if res[i] in Conversions.sr else -1
            if ci >= 0:
                res[i] = Conversions.sl[ci]
        return ''.join(res)

    @staticmethod
    def strings_look_equal(a, b):
        return Conversions.rus_string_to_stable_alphabet(a) == Conversions.rus_string_to_stable_alphabet(b)

    @staticmethod
    def normalize_eu(eu):
        if eu == "'C" or eu == "'С":
            eu = "°C"
        return eu

    @staticmethod
    def get_enum_description(ct):
        mem_info = ct.__class__.__dict__.get(ct.name)
        if mem_info:
            attrs = mem_info.get('description')
            if attrs:
                return attrs
        return ct.name

    @staticmethod
    def array_to_string(ba, delimiter):
        return delimiter.join(map(str, ba))

    @staticmethod
    def rot_n(text, n):
        if text is None:
            return None
        bta = text.encode('ascii')

        for i in range(len(bta)):
            if bta[i] < 32 or bta[i] > 127:
                raise Exception("недопустимый символ в строке сообщения")
            rc = bta[i] + n
            if n > 0 and rc > 127:
                rc = rc - 127 + 32
            if n < 0 and rc < 32:
                rc = rc + 127 - 32
            bta[i] = rc.to_bytes(1, byteorder='big')

        return b''.join(bta).decode('ascii')
