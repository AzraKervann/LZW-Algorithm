import os
import math
from PIL import Image
import numpy as np


class RGBImageLZW:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bit_width = None
        self.base_size = 256

    # ---------- Entropy ----------

    def compute_entropy(self, sequence):
        freq = {}
        for val in sequence:
            freq[val] = freq.get(val, 0) + 1
        total = len(sequence)
        if not total:
            return 0.0
        return -sum((c / total) * math.log2(c / total) for c in freq.values())

    # ---------- Core LZW ----------

    def _encode(self, values):
        table = {(i,): i for i in range(self.base_size)}
        next_code = self.base_size
        buf = []
        output = []

        for v in values:
            candidate = tuple(buf + [v])
            if candidate in table:
                buf.append(v)
            else:
                output.append(table[tuple(buf)])
                table[candidate] = next_code
                next_code += 1
                buf = [v]

        if buf:
            output.append(table[tuple(buf)])

        self.bit_width = math.ceil(math.log2(next_code)) if next_code > 1 else 1
        return output

    def _decode(self, codes):
        table = {i: [i] for i in range(self.base_size)}
        next_code = self.base_size
        output = []

        if not codes:
            return output

        prev = table[codes.pop(0)]
        output.extend(prev)

        for code in codes:
            if code in table:
                entry = table[code]
            elif code == next_code:
                entry = prev + [prev[0]]
            else:
                raise ValueError(f"Unexpected code: {code}")
            output.extend(entry)
            table[next_code] = prev + [entry[0]]
            next_code += 1
            prev = entry

        return output

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

    # ---------- Compress / Decompress ----------

    def compress(self):
        img = Image.open(self.filepath).convert("RGB")
        arr = np.array(img)
        rows, cols, channels = arr.shape
        pixels = arr.flatten().tolist()

        entropy = self.compute_entropy(pixels)
        codes = self._encode(pixels)
        bits = self._codes_to_bits(codes)

        header = f"{rows},{cols},{channels}|"
        header_bits = "".join(format(ord(c), "08b") for c in header)

        full_bits = header_bits + self._prepend_width(bits)
        padded = self._apply_padding(full_bits)
        byte_data = self._pack_bytes(padded)

        out_path = self.filepath + "_lv4_compressed.bin"
        with open(out_path, "wb") as f:
            f.write(bytes(byte_data))

        orig_size = os.path.getsize(self.filepath)
        comp_size = len(byte_data)
        ratio = orig_size / comp_size if comp_size else 0
        avg_bits = (comp_size * 8) / len(codes) if codes else 0

        return out_path, entropy, avg_bits, ratio, orig_size, comp_size

    def decompress(self, bin_path):
        with open(bin_path, "rb") as f:
            raw = f.read()

        bits = "".join(bin(b)[2:].rjust(8, "0") for b in raw)
        bits = self._strip_padding(bits)

        header = ""
        while not header.endswith("|"):
            header += chr(int(bits[:8], 2))
            bits = bits[8:]

        rows, cols, channels = (int(x) for x in header[:-1].split(","))

        bits = self._extract_width(bits)
        codes = self._bits_to_codes(bits)
        flat = self._decode(codes)

        arr = np.array(flat, dtype=np.uint8).reshape((rows, cols, channels))
        Image.fromarray(arr, "RGB").save(
            out_path := bin_path.replace("_lv4_compressed.bin", "_lv4_decompressed.png")
        )
        return out_path