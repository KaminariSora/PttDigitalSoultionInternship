import pythainlp
from pythainlp.tokenize import word_tokenize

input_file = "Data/output_1_new.txt"
output_file = "Data/output_tokenize.txt"

engines = [
    "newmm", "longest", "multi_cut", "attacut",
    "deepcut", "mm", "nercut", "newmm-safe"
]

with open(input_file, "r", encoding="utf-8") as f_in, \
     open(output_file, "w", encoding="utf-8") as f_out:

    for i, line in enumerate(f_in):
        if i >= 210:
            break
        text_strip = line.strip()
        f_out.write(f"{i} ---------\n")
        f_out.write(f"Original: {text_strip}\n")

        for engine in engines:
            try:
                tokens = word_tokenize(text_strip, engine=engine)
                f_out.write(f"{engine:10}: {tokens}\n")
            except Exception as e:
                f_out.write(f"{engine:10}: Error - {e}\n")

        f_out.write("\n")

print(f"✅ เขียนผลลัพธ์ลงไฟล์เรียบร้อย: {output_file}")
