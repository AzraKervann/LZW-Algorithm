import os
from LZW import TextLZW

filename = "sample"
lzw = TextLZW(filename, "text")
output_path = lzw.decompress()

# Compare original vs decompressed
base_dir = os.path.dirname(os.path.realpath(__file__))

original_path     = os.path.join(base_dir, filename + ".txt")
decompressed_path = os.path.join(base_dir, filename + "_decompressed.txt")

with open(original_path, "r") as f1, open(decompressed_path, "r") as f2:
    match = f1.read() == f2.read()

status = "match" if match else "do NOT match"
print(f"{filename}.txt and {filename}_decompressed.txt {status}.")