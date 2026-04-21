from LZW import TextLZW

filename = 'sample'
lzw = TextLZW(filename, 'text')
output_path = lzw.compress()