import matplotlib.pyplot as plt
import json
import matplotlib.font_manager as fm

# ฟอนต์ภาษาไทย
thai_font = fm.FontProperties(fname="C:/Windows/Fonts/tahoma.ttf")

DPI = 1
page_to_plot = 1

# โหลด JSON
with open("LineManagements/Data/ReportMeeting_4_58 copy.pdf.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

paragraphs = json_data["analyzeResult"]["paragraphs"]

# เลือกเฉพาะ paragraph ของหน้านี้
page_paragraphs = [
    p for p in paragraphs
    if any(br["pageNumber"] == page_to_plot for br in p["boundingRegions"])
]

plt.figure(figsize=(8, 11))

for paragraph in page_paragraphs:
    for br in paragraph["boundingRegions"]:
        if br["pageNumber"] == page_to_plot:
            polygon = br["polygon"]
            if len(polygon) < 6 or len(polygon) % 2 != 0:
                continue
            
            # แปลงเป็น list ของ (x, y)
            points = [(polygon[i] * DPI, polygon[i+1] * DPI) for i in range(0, len(polygon), 2)]
            
            # ปิด loop polygon (วนกลับจุดแรก)
            points.append(points[0])
            
            xs, ys = zip(*points)
            plt.plot(xs, ys, color='black')
            
            # เนื้อหา paragraph
            content = paragraph.get("content", "")
            if len(content) > 100:
                content = content[:100] + "..."
            
            # พิกัดมุมบนซ้าย
            text_x, text_y = points[0]
            
            # วางข้อความ
            plt.text(
                text_x, text_y, content,
                fontproperties=thai_font, fontsize=8,
                verticalalignment='top', color='red'
            )

# ตั้งค่ากราฟ
plt.gca().invert_yaxis()
plt.title(f"Paragraph Bounding Boxes - Page {page_to_plot}", fontproperties=thai_font)
plt.xlabel("X Coordinate", fontproperties=thai_font)
plt.ylabel("Y Coordinate", fontproperties=thai_font)
plt.grid(True, alpha=0.3)
plt.axis("equal")

plt.tight_layout()
plt.show()
