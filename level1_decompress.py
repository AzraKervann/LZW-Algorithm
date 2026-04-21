import csv

class LZWDecoder:
    def __init__(self):
        self.table = {i: chr(i) for i in range(256)}
        self.next_code = 256
        self.log = []

    def decode(self, codes, output_file="lzw_decompressed.csv"):
        if not codes:
            return ""

        result = []
        prev = self.table[codes[0]]
        result.append(prev)

        for code in codes[1:]:
            if code in self.table:
                entry = self.table[code]
            elif code == self.next_code:
                entry = prev + prev[0]
            else:
                raise ValueError(f"Invalid code: {code}")

            result.append(entry)
            new_entry = prev + entry[0]
            self.table[self.next_code] = new_entry
            self.log.append([self.next_code, new_entry])
            self.next_code += 1
            prev = entry

        self._export_csv(output_file)
        return "".join(result)

    def _export_csv(self, output_file):
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Code', 'Sequence'])
            writer.writerows(self.log)


decoder = LZWDecoder()
input_codes = [65, 66, 82, 65, 67, 256, 68, 259, 65]
print(decoder.decode(input_codes))