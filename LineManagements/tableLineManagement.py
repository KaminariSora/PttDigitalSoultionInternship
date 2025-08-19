import json
from pythainlp.tag import pos_tag
from pythainlp.tokenize import word_tokenize

# โหลดไฟล์ JSON
with open("LineManagements/Data/meeting_executive4_66.pdf.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

output_tables = []

total_words = 0
total_words_filtered = 0

for table_idx, table in enumerate(json_data["analyzeResult"]["tables"]):
    row_count = table.get("rowCount", 0)
    col_count = table.get("columnCount", 0)

    # สร้าง list ของ row
    table_rows = [["" for _ in range(col_count)] for _ in range(row_count)]

    for cell in table["cells"]:
        row_idx = cell.get("rowIndex", 0)
        col_idx = cell.get("columnIndex", 0)
        content = cell.get("content", "")

        # เก็บลงตาราง
        table_rows[row_idx][col_idx] = content

        # นับคำเหมือนเดิม
        tokens = word_tokenize(content, keep_whitespace=False)
        tags = pos_tag(tokens, engine="perceptron", corpus="orchid")
        filtered_tokens = [word for word, tag in tags if tag not in ["NPRP", "NTTL"]]

        total_words += len(tokens)
        total_words_filtered += len(filtered_tokens)

    output_tables.append(table_rows)

# แสดงผล table
for t_idx, table_rows in enumerate(output_tables):
    print(f"\n===== Table {t_idx+1} =====")
    for row in table_rows:
        print("\t".join(row))

print(f"\nจำนวนคำทั้งหมดก่อนคัดกรอง: {total_words}")
print(f"จำนวนคำทั้งหมดหลังคัดกรอง: {total_words_filtered}")

# บันทึกเป็นไฟล์ text
with open("LineManagements/Data/report_Table_Output.txt", "w", encoding="utf-8") as out_file:
    for t_idx, table_rows in enumerate(output_tables):
        out_file.write(f"===== Table {t_idx+1} =====\n")
        for row in table_rows:
            out_file.write("\t".join(row) + "\n")

print("✅ บันทึกไฟล์เรียบร้อย: Data/report_Table_Output.txt")
