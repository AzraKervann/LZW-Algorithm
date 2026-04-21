#Bu Level 1 LZW Kodlayıcısı, tekrarlayan dizileri benzersiz 
# sayısal kodlarla değiştirerek veriyi sıkıştırmak için dinamik 
# bir sözlük uygular.
import csv

class LZWEncoder:
    def __init__(self):
        self.dictionary = {chr(i): i for i in range(256)}
        self.next_code = 256
        self.history = []

    def encode(self, text, output_file="lzw_compressed.csv"):
        buffer = ""
        result = []

        for char in text:
            current = buffer + char
            if current in self.dictionary:
                buffer = current
            else:
                result.append(self.dictionary[buffer])
                self.history.append([current, self.next_code])
                self.dictionary[current] = self.next_code
                self.next_code += 1
                buffer = char

        if buffer:
            result.append(self.dictionary[buffer])

        self._save_csv(output_file)
        return result

    def _save_csv(self, output_file):
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Sequence', 'Code'])
            writer.writerows(self.history)


encoder = LZWEncoder()
print(encoder.encode("ABRACADABRA"))