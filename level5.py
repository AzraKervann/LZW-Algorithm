import os
import math
from PIL import Image
import numpy as np


class RGBDiffLZW:
    def __init__(self, filepath):
        self.filepath = filepath
        self.bit_width = None
        self.base_size = 512

    # ---------- Entropy ----------

    def compute_entropy(self, sequence):
        freq = {}
        for val in sequence:
            freq[val] = freq.get(val, 0) + 1
        total = len(sequence)
        if not total:
            return 0.0
        return -sum((c / total) * math.log2(c / total) for c in freq.values())

    # ---------- Differential Transform ----------

    def to_diff(self, channel):
        rows, cols = channel.shape
        delta = np.zeros((rows, cols), dtype=np.int32)
        delta[0, 0] = channel[0, 0]

        for r in range(1, rows):
            delta[r, 0] = int(channel[r, 0]) - int(channel[r - 1, 0])

        for r in range(rows):
            for c in range(1, cols):
                delta[r, c] = int(channel[r, c]) - int(channel[r, c - 1])

        return (delta.flatten() + 255).tolist()

    def from_diff(self, flat, shape):
        rows, cols = shape
        delta = (np.array(flat) - 255).reshape((rows, cols))
        restored = np.zeros((rows, cols), dtype=np.int32)
        restored[0, 0] = delta[0, 0]

        for r in range(1, rows):
            restored[r, 0] = delta[r, 0] + restored[r - 1, 0]

        for r in range(rows):
            for c in range(1, cols):
                restored[r, c] = delta[r, c] + restored[r, c - 1]

        return np.clip(restored, 0, 255).astype(np.uint8)

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
        rows, cols, num_ch = arr.shape

        # Apply differential transform per channel, then concatenate
        combined = []
        for ch in range(num_ch):
            combined.extend(self.to_diff(arr[:, :, ch]))

        entropy = self.compute_entropy(combined)
        codes = self._encode(combined)
        bits = self._codes_to_bits(codes)

        header = f"{rows},{cols},{num_ch}|"
        header_bits = "".join(format(ord(c), "08b") for c in header)

        full_bits = header_bits + self._prepend_width(bits)
        padded = self._apply_padding(full_bits)
        byte_data = self._pack_bytes(padded)

        out_path = self.filepath + "_lv5_compressed.bin"
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

        rows, cols, num_ch = (int(x) for x in header[:-1].split(","))

        bits = self._extract_width(bits)
        codes = self._bits_to_codes(bits)
        flat = self._decode(codes)

        # Split flat list back into per-channel segments
        seg = rows * cols
        channels = [
            self.from_diff(flat[i * seg: (i + 1) * seg], (rows, cols))
            for i in range(num_ch)
        ]

        arr = np.stack(channels, axis=-1)
        Image.fromarray(arr, "RGB").save(
            out_path := bin_path.replace("_lv5_compressed.bin", "_lv5_decompressed.png")
        )
        return out_path