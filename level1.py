import os
import math
from io import StringIO


class LZWProcessor:
    def __init__(self, filepath, mode="text"):
        self.filepath = filepath
        self.mode = mode
        self.bit_width = None
        self.initial_size = 256

    # ---------- Statistics ----------

    def compute_entropy(self, sequence):
        freq = {}
        for sym in sequence:
            freq[sym] = freq.get(sym, 0) + 1
        total = len(sequence)
        if total == 0:
            return 0.0
        result = 0.0
        for cnt in freq.values():
            p = cnt / total
            result -= p * math.log2(p)
        return result

    # ---------- Compress / Decompress ----------

    def compress(self):
        with open(self.filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
            raw = f.read()

        entropy = self.compute_entropy(raw)
        codes = self._encode(raw)
        bitstream = self._codes_to_bits(codes)
        bitstream = self._prepend_width(bitstream)
        bitstream = self._apply_padding(bitstream)
        byte_data = self._bits_to_bytes(bitstream)

        out_path = self.filepath + "_compressed.bin"
        with open(out_path, "wb") as f:
            f.write(bytes(byte_data))

        original_size = len(raw)
        packed_size = len(byte_data)
        ratio = original_size / packed_size if packed_size else 0
        avg_bits = (packed_size * 8) / len(codes) if codes else 0

        return out_path, entropy, avg_bits, ratio, original_size, packed_size

    def decompress(self, bin_path):
        with open(bin_path, "rb") as f:
            raw_bytes = f.read()

        bits = "".join(bin(b)[2:].rjust(8, "0") for b in raw_bytes)
        bits = self._strip_padding(bits)
        bits = self._extract_width(bits)
        codes = self._bits_to_codes(bits)
        text = self._decode(codes)

        out_path = bin_path.replace("_compressed.bin", "_decompressed.txt")
        with open(out_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(text)

        return out_path

    # ---------- Core LZW ----------

    def _encode(self, data):
        table = {chr(i): i for i in range(self.initial_size)}
        next_code = self.initial_size
        output = []
        buf = ""

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

        self.bit_width = math.ceil(math.log2(next_code)) if next_code > 1 else 1
        return output

    def _decode(self, codes):
        table = {i: chr(i) for i in range(self.initial_size)}
        next_code = self.initial_size
        buf = StringIO()

        if not codes:
            return ""

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
        segments = []
        for num in codes:
            segment = ""
            for i in range(self.bit_width - 1, -1, -1):
                segment += "1" if (num >> i) & 1 else "0"
            segments.append(segment)
        return "".join(segments)

    def _bits_to_codes(self, bits):
        return [int(bits[i: i + self.bit_width], 2)
                for i in range(0, len(bits), self.bit_width)]

    def _prepend_width(self, bits):
        return format(self.bit_width, "08b") + bits

    def _extract_width(self, bits):
        self.bit_width = int(bits[:8], 2)
        return bits[8:]

    def _apply_padding(self, bits):
        pad_count = (8 - len(bits) % 8) % 8
        return format(pad_count, "08b") + bits + "0" * pad_count

    def _strip_padding(self, bits):
        pad_count = int(bits[:8], 2)
        bits = bits[8:]
        if pad_count:
            bits = bits[:-pad_count]
        return bits

    def _bits_to_bytes(self, bits):
        return bytearray(int(bits[i: i + 8], 2) for i in range(0, len(bits), 8))