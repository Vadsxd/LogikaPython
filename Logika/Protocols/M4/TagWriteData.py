class TagWriteData:
    def __init__(self, channel, ordinal, value, oper):
        self.channel: int = channel
        self.ordinal: int = ordinal
        self.value: object = value
        self.oper: bool = oper  # non-null value indicates that tag's 'operative' flag should be set to given value
