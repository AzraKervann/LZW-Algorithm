import os
import math
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from io import StringIO


class ImageLZW:
    def __init__(self, filepath, mode="image"):
        self.filepath = filepath
        self.mode = mode
        self.bit_width = None
        self.base_size = 256
        self.img_dimensions = None

    # ---------- Entropy ----------

    def compute_entropy(self, sequence):
        freq = {}
        for val in sequence:
            freq[val] = freq.get(val, 0) + 1
        total = len(freq) and len(sequence)
        if not total:
            return 0.0
        return -sum((c / total) * math.log2(c / total) for c in freq.values())

    # ---------- Compress / Decompress ----------

    def compress(self):
        img = Image.open(self.filepath).convert("L")
        self.img_dimensions = img.size          # (width, height)
        pixels = np.array(img).flatten().tolist()

        entropy = self.compute_entropy(pixels)
        codes = self._encode(pixels)
        bits = self._codes_to_bits(codes)

        header = f"{self.img_dimensions[1]},{self.img_dimensions[0]}|"
        header_bits = "".join(format(ord(c), "08b") for c in header)

        full_bits = header_bits + self._prepend_width(bits)
        padded = self._apply_padding(full_bits)
        byte_data = self._pack_bytes(padded)

        out_path = self.filepath + "_compressed.bin"
        with open(out_path, "wb") as f:
            f.write(bytes(byte_data))

        original_size = os.path.getsize(self.filepath)
        packed_size = len(byte_data)
        ratio = original_size / packed_size if packed_size else 0
        avg_bits = (packed_size * 8) / len(codes) if codes else 0

        return out_path, entropy, avg_bits, ratio, original_size, packed_size

    def decompress(self, bin_path):
        with open(bin_path, "rb") as f:
            raw = f.read()

        bits = "".join(bin(b)[2:].rjust(8, "0") for b in raw)
        bits = self._strip_padding(bits)

        # Read header until '|'
        header = ""
        while True:
            header += chr(int(bits[:8], 2))
            bits = bits[8:]
            if header.endswith("|"):
                break

        rows, cols = (int(x) for x in header[:-1].split(","))

        bits = self._extract_width(bits)
        codes = self._bits_to_codes(bits)
        flat = self._decode(codes)

        arr = np.array(flat, dtype=np.uint8).reshape((rows, cols))
        out_img = Image.fromarray(arr, "L")

        out_path = bin_path.replace("_compressed.bin", "_decompressed.png")
        out_img.save(out_path)
        return out_path

    # ---------- Core LZW ----------

    def _encode(self, pixels):
        table = {(i,): i for i in range(self.base_size)}
        next_code = self.base_size
        buf = []
        output = []

        for px in pixels:
            candidate = tuple(buf + [px])
            if candidate in table:
                buf.append(px)
            else:
                output.append(table[tuple(buf)])
                table[candidate] = next_code
                next_code += 1
                buf = [px]

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
                raise ValueError(f"Unexpected code encountered: {code}")
            output.extend(entry)
            table[next_code] = prev + [entry[0]]
            next_code += 1
            prev = entry

        return output

    # ---------- Bit Manipulation ----------

    def _codes_to_bits(self, codes):
        return "".join(
            "".join("1" if (num >> i) & 1 else "0" for i in range(self.bit_width - 1, -1, -1))
            for num in codes
        )

    def _bits_to_codes(self, bits):
        return [int(bits[i: i + self.bit_width], 2) for i in range(0, len(bits), self.bit_width)]

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


# ---------- GUI ----------

class LZWImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LZW Image Compression — Grayscale")
        self.root.geometry("800x600")
        self.filepath = None

        toolbar = tk.Frame(root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        for label, cmd in [
            ("Open Image", self.open_file),
            ("Compress",   self.run_compress),
            ("Decompress", self.run_decompress),
        ]:
            tk.Button(toolbar, text=label, command=cmd).pack(side=tk.LEFT, padx=5)

        self.stats = tk.Label(
            root,
            text="Entropy: —\nAvg Bits: —\nRatio: —\nOriginal: —\nCompressed: —",
            justify=tk.LEFT,
            font=("Courier", 11),
        )
        self.stats.pack(side=tk.TOP, fill=tk.X, padx=10, pady=6)

        panel = tk.Frame(root)
        panel.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.left_panel  = tk.Label(panel, text="Original")
        self.right_panel = tk.Label(panel, text="Reconstructed")
        self.left_panel.pack(side=tk.LEFT,  expand=True)
        self.right_panel.pack(side=tk.RIGHT, expand=True)

    # ---------- Helpers ----------

    def _show_image(self, widget, path):
        img = Image.open(path)
        img.thumbnail((300, 300))
        photo = ImageTk.PhotoImage(img)
        widget.configure(image=photo, text="")
        widget.image = photo

    # ---------- Callbacks ----------

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.bmp;*.jpg;*.jpeg")]
        )
        if path:
            self.filepath = path
            self._show_image(self.left_panel, path)

    def run_compress(self):
        if not self.filepath:
            messagebox.showwarning("No File", "Please open an image first.")
            return
        proc = ImageLZW(self.filepath)
        out, ent, avg, cr, orig, comp = proc.compress()
        self.stats.configure(
            text=(
                f"Entropy: {ent:.4f}\n"
                f"Avg Bits: {avg:.2f}\n"
                f"Ratio: {cr:.2f}\n"
                f"Original: {orig} bytes\n"
                f"Compressed: {comp} bytes"
            )
        )
        messagebox.showinfo("Done", f"Saved: {out}")

    def run_decompress(self):
        path = filedialog.askopenfilename(filetypes=[("Binary", "*.bin")])
        if not path:
            return
        proc = ImageLZW(path)
        out = proc.decompress(path)
        self._show_image(self.right_panel, out)
        messagebox.showinfo("Done", f"Saved: {out}")


if __name__ == "__main__":
    root = tk.Tk()
    LZWImageApp(root)
    root.mainloop()