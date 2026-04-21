import os
import math
from io import StringIO


class TextLZW:
    def __init__(self, filepath, mode="text"):
        self.filepath = filepath
        self.mode = mode
        self.bit_width = None

    # ---------- Compress / Decompress ----------

    def compress(self):
        src = self._resolve("", ".txt")
        dst = self._resolve("_compressed", ".bin")

        with open(src, "r") as f:
            text = f.read()

        codes = self._encode(text)
        bits = self._codes_to_bits(codes)
        bits = self._prepend_width(bits)
        bits = self._apply_padding(bits)
        buf = self._pack_bytes(bits)

        with open(dst, "wb") as f:
            f.write(bytes(buf))

        orig = len(text)
        comp = len(buf)
        print(f"{os.path.basename(src)} → {os.path.basename(dst)}")
        print(f"Original : {orig:,} bytes")
        print(f"Bit Width: {self.bit_width}")
        print(f"Compressed: {comp:,} bytes")
        print(f"Ratio    : {comp / orig:.2f}")
        return dst

    def decompress(self):
        src = self._resolve("_compressed", ".bin")
        dst = self._resolve("_decompressed", ".txt")

        with open(src, "rb") as f:
            raw = f.read()

        bits = "".join(bin(b)[2:].rjust(8, "0") for b in raw)
        bits = self._strip_padding(bits)
        bits = self._extract_width(bits)
        codes = self._bits_to_codes(bits)
        text = self._decode(codes)

        with open(dst, "w") as f:
            f.write(text)

        print(f"{os.path.basename(src)} → {os.path.basename(dst)}")
        return dst

    # ---------- Trace ----------

    def trace(self, text):
        table = {chr(i): i for i in range(256)}
        next_code = 256
        buf = ""
        rows = []

        for ch in text:
            candidate = buf + ch
            if candidate in table:
                rows.append([buf or "—", ch, "", "", ""])
                buf = candidate
            else:
                inv = {v: k for k, v in table.items()}
                out_sym = inv[table[buf]] if buf else ""
                table[candidate] = next_code
                rows.append([buf or "—", ch, out_sym, next_code, candidate])
                next_code += 1
                buf = ch

        if buf:
            inv = {v: k for k, v in table.items()}
            rows.append([buf, "EOF", inv[table[buf]], "", ""])

        return rows

    # ---------- Core LZW ----------

    def _encode(self, data):
        table = {chr(i): i for i in range(256)}
        next_code = 256
        buf = ""
        output = []

        for ch in data:
            candidate = buf + ch
            if candidate in table:
                buf = candidate
            else:
                output.append(table[buf])
                table[candidate] = next_code
                next_code += 1
                buf = ch

        if buf:
            output.append(table[buf])

        self.bit_width = math.ceil(math.log2(len(table)))
        return output

    def _decode(self, codes):
        table = {i: chr(i) for i in range(256)}
        next_code = 256
        buf = StringIO()

        prev = chr(codes.pop(0))
        buf.write(prev)

        for code in codes:
            if code in table:
                entry = table[code]
            elif code == next_code:
                entry = prev + prev[0]
            else:
                raise ValueError(f"Unexpected code: {code}")
            buf.write(entry)
            table[next_code] = prev + entry[0]
            next_code += 1
            prev = entry

        return buf.getvalue()

    # ---------- Bit Manipulation ----------

    def _codes_to_bits(self, codes):
        return "".join(
            "".join("1" if (num >> i) & 1 else "0"
                    for i in range(self.bit_width - 1, -1, -1))
            for num in codes
        )

    def _bits_to_codes(self, bits):
        return [int(bits[i: i + self.bit_width], 2)
                for i in range(0, len(bits), self.bit_width)]

    def _prepend_width(self, bits):
        return format(self.bit_width, "08b") + bits

    def _extract_width(self, bits):
        self.bit_width = int(bits[:8], 2)
        return bits[8:]

    def _apply_padding(self, bits):
        pad = (8 - len(bits) % 8) % 8
        return format(pad, "08b") + bits + "0" * pad

    def _strip_padding(self, bits):
        pad = int(bits[:8], 2)
        return bits[8: len(bits) - pad if pad else None]

    def _pack_bytes(self, bits):
        return bytearray(int(bits[i: i + 8], 2) for i in range(0, len(bits), 8))

    # ---------- Path Helper ----------

    def _resolve(self, suffix, ext):
        base = os.path.splitext(self.filepath)[0]
        return base + suffix + ext


if __name__ == "__main__":
    coder = TextLZW("dummy")
    rows = coder.trace("^WED^WE^WEE^WEB^WET")
    print("W\tK\tOutput\tIndex\tSymbol")
    for row in rows:
        print("\t".join(str(x) for x in row))