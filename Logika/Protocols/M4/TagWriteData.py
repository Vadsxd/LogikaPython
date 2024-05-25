class TagWriteData:
    def __init__(self, channel: int, ordinal: int, value: object, oper: bool):
        self.channel = channel
        self.ordinal = ordinal
        self.value = value
        self.oper = oper  # non-null value indicates that tag's 'operative' flag should be set to given value
