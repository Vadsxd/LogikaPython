class FLZ:
    def __init__(self):
        self.MAX_DISTANCE: int = 8191

    @staticmethod
    def decompress(input_data: bytes, offset: int, length: int):
        if length == 0:
            return bytes()

        level = (input_data[0] >> 5) + 1
        if level != 1:
            raise NotImplementedError("only FLZ level1 decompression supported")

        output_data = bytearray(32768)

        ip: int = offset
        ip_limit: int = ip + length
        op: int = 0
        op_limit: int = len(output_data)
        ctrl: int = (input_data[ip]) & 31
        loop: bool = True

        while loop:
            ref = op
            length_ctrl = ctrl >> 5
            offset_ctrl = (ctrl & 31) << 8

            if ctrl >= 32:
                length_ctrl -= 1
                ref -= offset_ctrl
                if length_ctrl == 7 - 1:
                    length_ctrl += input_data[ip]
                ref -= input_data[ip]

                if op + length_ctrl + 3 > op_limit or ref - 1 < 0:
                    return None

                if ip < ip_limit:
                    ctrl = input_data[ip]
                    ip += 1
                else:
                    loop = False

                if ref == op:
                    # optimize copy for a run
                    byte_val = output_data[ref - 1]
                    for _ in range(length_ctrl + 1):
                        output_data[op] = byte_val
                        op += 1

                else:
                    ref -= 1

                    for _ in range(3):
                        output_data[op] = output_data[ref]
                        ref += 1
                        op += 1

                    if length_ctrl % 2 == 1:
                        output_data[op] = output_data[ref]
                        length_ctrl -= 1
                        op += 1

                    q = op
                    op += length_ctrl
                    p = ref

                    for _ in range(length_ctrl // 2):
                        for _ in range(4):
                            output_data[q] = output_data[p]
                            q += 1
                            p += 1

                    for _ in range(length_ctrl % 2):
                        output_data[q] = output_data[p]
                        q += 1
                        p += 1

            else:
                ctrl += 1

                if op + ctrl > op_limit or ip + ctrl > ip_limit:
                    return None

                output_data[op] = input_data[ip]
                op += 1

                for _ in range(ctrl - 1):
                    output_data[op] = input_data[ip]
                    op += 1
                    ip += 1

                loop = ip < ip_limit
                if loop:
                    ctrl = input_data[ip]

        return output_data[:op]
