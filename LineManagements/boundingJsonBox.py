import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import json
import matplotlib.font_manager as fm

thai_font = fm.FontProperties(fname="C:/Windows/Fonts/tahoma.ttf")

page_number = 0
style = "words"
file_location = "LineManagements/Data/meeting_executive4_66.pdf.json"

with open(file_location, "r", encoding="utf-8") as f:
    json_data = json.load(f)

words = json_data["analyzeResult"]["pages"][page_number][style]

fig, ax = plt.subplots(figsize=(8, 11))

for word in words:
    polygon = word["polygon"]
    points = [(polygon[i], polygon[i+1]) for i in range(0, len(polygon), 2)]
    poly = Polygon(points, closed=True, edgecolor='blue', facecolor='none', linewidth=1)
    ax.add_patch(poly)

    # ใช้ฟอนต์ภาษาไทยในการแสดงข้อความ
    text_x, text_y = points[0]
    ax.text(text_x, text_y, word["content"], fontproperties=thai_font, fontsize=6, verticalalignment='top')

# ตั้งค่าการแสดงผล
ax.set_xlim(0, json_data["analyzeResult"]["pages"][0]["width"])
ax.set_ylim(json_data["analyzeResult"]["pages"][0]["height"], 0)
ax.set_aspect('equal')
ax.set_title("Word Bounding Boxes", fontproperties=thai_font)

plt.show()