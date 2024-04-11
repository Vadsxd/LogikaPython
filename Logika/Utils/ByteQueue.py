class ByteQueue:
    def __init__(self, initial_size: int):
        self.fHead = 0
        self.fTail = 0
        self.fSize = 0
        self.fSizeUntilCut = initial_size
        self.fInternalBuffer = bytearray(initial_size)

    @property
    def length(self) -> int:
        return self.fSize

    def clear(self, size: int = None):
        if size is None:
            self.fHead = 0
            self.fTail = 0
            self.fSize = 0
            self.fSizeUntilCut = len(self.fInternalBuffer)
        else:
            if size > self.fSize:
                size = self.fSize

            if size == 0:
                return

            self.fHead = (self.fHead + size) % len(self.fInternalBuffer)
            self.fSize -= size

            if self.fSize == 0:
                self.fHead = 0
                self.fTail = 0

            self.fSizeUntilCut = len(self.fInternalBuffer) - self.fHead

    def SetCapacity(self, capacity: int):
        newBuffer = bytearray(capacity)

        if self.fSize > 0:
            if self.fHead < self.fTail:
                newBuffer[:self.fSize] = self.fInternalBuffer[self.fHead:self.fHead + self.fSize]
            else:
                rightLength = len(self.fInternalBuffer) - self.fHead
                newBuffer[:rightLength] = self.fInternalBuffer[self.fHead:self.fHead + rightLength]
                newBuffer[rightLength:rightLength + self.fTail] = self.fInternalBuffer[:self.fTail]

        self.fHead = 0
        self.fTail = self.fSize
        self.fInternalBuffer = newBuffer

    def Enqueue(self, buffer, offset, size):
        if size == 0:
            return

        if (self.fSize + size) > len(self.fInternalBuffer):
            self.SetCapacity((self.fSize + size + 2047) & ~2047)

        if self.fHead < self.fTail:
            rightLength = len(self.fInternalBuffer) - self.fTail

            if rightLength >= size:
                self.fInternalBuffer[self.fTail:self.fTail + size] = buffer[offset:offset + size]
            else:
                self.fInternalBuffer[self.fTail:self.fTail + rightLength] = buffer[offset:offset + rightLength]
                self.fInternalBuffer[:size - rightLength] = buffer[offset + rightLength:offset + size]
        else:
            self.fInternalBuffer[self.fTail:self.fTail + size] = buffer[offset:offset + size]

        self.fTail = (self.fTail + size) % len(self.fInternalBuffer)
        self.fSize += size
        self.fSizeUntilCut = len(self.fInternalBuffer) - self.fHead

    def Dequeue(self, buffer, offset, size):
        if size > self.fSize:
            size = self.fSize

        if size == 0:
            return 0

        if self.fHead < self.fTail:
            buffer[offset:offset + size] = self.fInternalBuffer[self.fHead:self.fHead + size]
        else:
            rightLength = len(self.fInternalBuffer) - self.fHead

            if rightLength >= size:
                buffer[offset:offset + size] = self.fInternalBuffer[self.fHead:self.fHead + size]
            else:
                buffer[offset:offset + rightLength] = self.fInternalBuffer[self.fHead:self.fHead + rightLength]
                buffer[offset + rightLength:offset + size] = self.fInternalBuffer[:size - rightLength]

        self.fHead = (self.fHead + size) % len(self.fInternalBuffer)
        self.fSize -= size

        if self.fSize == 0:
            self.fHead = 0
            self.fTail = 0

        self.fSizeUntilCut = len(self.fInternalBuffer) - self.fHead
        return size

    def PeekOne(self, index):
        return self.fInternalBuffer[index - self.fSizeUntilCut] if index >= self.fSizeUntilCut else \
            self.fInternalBuffer[self.fHead + index]
