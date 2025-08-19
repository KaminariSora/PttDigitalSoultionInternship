import json
from pythainlp.tag import pos_tag
from pythainlp.tokenize import word_tokenize

# โหลดไฟล์ JSON
with open("LineManagements/Data/ReportMeeting_4_58 copy.pdf.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

output_lines = []
total_words = 0
total_words_filtered = 0 
style = "words"

for page_idx, page in enumerate(json_data["analyzeResult"]["pages"]):
    words = page[style]
    page_width = page["width"]
    page_height = page["height"]

    word_boxes = []
    for word in words:
        polygon = word["polygon"]
        x_coords = polygon[::2]
        y_coords = polygon[1::2]

        center_x = (sum(x_coords) / 4) / page_width
        center_y = (sum(y_coords) / 4) / page_height

        word_boxes.append({
            "content": word["content"],
            "center_x": center_x,
            "center_y": center_y
        })

    line_threshold = 0.01
    word_boxes.sort(key=lambda w: w["center_y"])

    lines = []
    current_line = []
    current_y = None

    for word in word_boxes:
        if current_y is None or abs(word["center_y"] - current_y) <= line_threshold:
            current_line.append(word)
            current_y = (current_y + word["center_y"]) / 2 if current_y is not None else word["center_y"]
        else:
            lines.append(sorted(current_line, key=lambda w: w["center_x"]))
            current_line = [word]
            current_y = word["center_y"]

    if current_line:
        lines.append(sorted(current_line, key=lambda w: w["center_x"]))

    for line in lines:
        line_text = ""
        for i, word in enumerate(line):
            line_text += word["content"]
            if i < len(line) - 1:
                next_word = line[i + 1]
                space = next_word["center_x"] - word["center_x"]
                if space > 0.06:
                    line_text += "_"

        tokens = word_tokenize(line_text.replace("_", " "), keep_whitespace=False)
        tags = pos_tag(tokens, engine="perceptron", corpus="orchid")

        filtered_tokens = [word for word, tag in tags if tag not in ["NPRP", "NTTL"]]

        word_count = len(tokens)
        word_count_filtered = len(filtered_tokens)

        total_words += word_count
        total_words_filtered += word_count_filtered

        output_lines.append(
            f"{line_text}"
            # f"POS: {tags}\n"
            # f"หลังคัดกรอง: {filtered_tokens} (คำ: {word_count_filtered})\n"
        )

        print(f"{line_text} (คำทั้งหมด: {word_count}, หลังคัดกรอง: {word_count_filtered})")
        print("POS:", tags)
        print("หลังคัดกรอง:", filtered_tokens)

print(f"\nจำนวนคำทั้งหมดก่อนคัดกรอง: {total_words}")
print(f"จำนวนคำทั้งหมดหลังคัดกรอง: {total_words_filtered}")

with open("LineManagements/Data/report_Output.txt", "w", encoding="utf-8") as out_file:
    for line in output_lines:
        out_file.write(line + "\n")

print("✅ บันทึกไฟล์เรียบร้อย: Data/output_21.txt")
