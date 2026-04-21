#Ayhan Azra Kervan - 042301127
import os
import sys
import importlib
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

sys.path.append(os.path.dirname(os.path.abspath(__file__)))




MODULE_REGISTRY = {
    "Text (Lv1)":       ("level1", "LZWProcessor"),
    "Gray (Lv2)":       ("level2", "ImageLZW"),
    "Gray+Diff (Lv3)":  ("level3", "DiffLZW"),
    "Color (Lv4)":      ("level4", "RGBImageLZW"),
    "Color+Diff (Lv5)": ("level5", "RGBDiffLZW"),
}

COMPRESSED_SUFFIX = {
    "Text (Lv1)":       "_compressed.bin",
    "Gray (Lv2)":       "_compressed.bin",
    "Gray+Diff (Lv3)":  "_lv3_compressed.bin",
    "Color (Lv4)":      "_lv4_compressed.bin",
    "Color+Diff (Lv5)": "_lv5_compressed.bin",
}


def load_coder(method_key):
    module_name, class_name = MODULE_REGISTRY[method_key]
    try:
        mod = importlib.import_module(module_name)
        importlib.reload(mod)
        cls = getattr(mod, class_name, None)
        if cls is None:
            raise AttributeError(f"{class_name} not found in {module_name}.py")
        return cls
    except Exception as exc:
        raise RuntimeError(f"Failed to load {method_key}:\n{exc}\n\n{traceback.format_exc()}")


# ---------- Main App ----------

class LZWSuiteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LZW Compression Suite")
        self.root.geometry("900x650")
        self.filepath = None

        self._build_toolbar()
        self._build_stats()
        self._build_panels()

    # ---------- UI Construction ----------

    def _build_toolbar(self):
        bar = tk.Frame(self.root)
        bar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)

        tk.Button(bar, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=4)

        self.method_var = tk.StringVar(value=next(iter(MODULE_REGISTRY)))
        for label in MODULE_REGISTRY:
            tk.Radiobutton(bar, text=label, variable=self.method_var,
                           value=label).pack(side=tk.LEFT, padx=2)

        tk.Button(bar, text="Compress",   command=self.run_compress).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Decompress", command=self.run_decompress).pack(side=tk.LEFT, padx=4)

    def _build_stats(self):
        self.stats_label = tk.Label(
            self.root,
            text="Entropy: —\nAvg Bits: —\nRatio: —\nOriginal: —\nCompressed: —",
            justify=tk.LEFT,
            font=("Courier", 11),
        )
        self.stats_label.pack(side=tk.TOP, fill=tk.X, padx=10, pady=6)

    def _build_panels(self):
        container = tk.Frame(self.root)
        container.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        for side, attr, caption in [
            (tk.LEFT,  "left_panel",  "Original"),
            (tk.RIGHT, "right_panel", "Reconstructed"),
        ]:
            frame = tk.Frame(container)
            frame.pack(side=side, fill=tk.BOTH, expand=True)
            panel = tk.Label(frame, text=caption, bg="gray", compound=tk.BOTTOM)
            panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            setattr(self, attr, panel)

    # ---------- Helpers ----------

    def _get_coder(self):
        try:
            return load_coder(self.method_var.get())
        except RuntimeError as e:
            messagebox.showerror("Module Error", str(e))
            return None

    def _display(self, panel, path):
        try:
            img = Image.open(path)
            w, h = img.size
            img.thumbnail((350, 350), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            panel.configure(image=photo, text=f"{w}×{h}")
            panel.image = photo
        except Exception as e:
            panel.configure(image="", text=f"Preview unavailable:\n{e}")

    def _update_stats(self, ent, avg, ratio, orig, comp):
        self.stats_label.configure(text=(
            f"Entropy: {ent:.4f}\n"
            f"Avg Bits: {avg:.2f}\n"
            f"Ratio: {ratio:.2f}\n"
            f"Original: {orig} bytes\n"
            f"Compressed: {comp} bytes"
        ))

    # ---------- Callbacks ----------

    def open_file(self):
        path = filedialog.askopenfilename()
        if not path:
            return
        self.filepath = path
        if path.lower().endswith((".png", ".bmp", ".jpg", ".jpeg")):
            self._display(self.left_panel, path)
        else:
            self.left_panel.configure(image="", text=f"Loaded:\n{os.path.basename(path)}")

    def run_compress(self):
        if not self.filepath:
            messagebox.showwarning("No File", "Please open a file first.")
            return

        method = self.method_var.get()
        CoderClass = self._get_coder()
        if not CoderClass:
            return

        try:
            coder = CoderClass(self.filepath)
            out, ent, avg, ratio, orig, comp = coder.compress()
            self._update_stats(ent, avg, ratio, orig, comp)
            messagebox.showinfo("Done", f"Saved: {out}")
        except Exception as e:
            messagebox.showerror("Compression Error", f"{e}\n\n{traceback.format_exc()}")

    def run_decompress(self):
        if not self.filepath:
            messagebox.showwarning("No File", "Please open a file first.")
            return

        method = self.method_var.get()
        suffix = COMPRESSED_SUFFIX[method]
        bin_path = self.filepath if self.filepath.endswith(".bin") else self.filepath + suffix

        if not os.path.exists(bin_path):
            messagebox.showerror("Not Found",
                f"Compressed file not found:\n{bin_path}\n\nCompress first or select the .bin file.")
            return

        CoderClass = self._get_coder()
        if not CoderClass:
            return

        try:
            coder = CoderClass(bin_path)
            out = coder.decompress(bin_path)
            if out.lower().endswith((".png", ".jpg", ".bmp")):
                self._display(self.right_panel, out)
            else:
                self.right_panel.configure(image="", text=f"Saved:\n{os.path.basename(out)}")
            messagebox.showinfo("Done", f"Saved: {out}")
        except Exception as e:
            messagebox.showerror("Decompression Error", f"{e}\n\n{traceback.format_exc()}")


if __name__ == "__main__":
    root = tk.Tk()
    LZWSuiteApp(root)
    root.mainloop()