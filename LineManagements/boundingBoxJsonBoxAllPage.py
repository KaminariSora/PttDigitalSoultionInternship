import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import json
import matplotlib.font_manager as fm

thai_font = fm.FontProperties(fname="C:/Windows/Fonts/tahoma.ttf")

with open("LineManagements/Data/meeting_executive1_66.pdf.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

pages = json_data["analyzeResult"]["pages"]

# DPI = 72
DPI = 1

# แยกคำตามหน้า
words_by_page = {}
page_dims = {}  # เก็บขนาดหน้าด้วย (width, height)

for page in pages:
    pnum = page["pageNumber"]
    words_by_page[pnum] = page["words"]
    page_dims[pnum] = (page["width"] * DPI, page["height"] * DPI)

# plot ทีละหน้า
for pnum, words in words_by_page.items():
    width_px, height_px = page_dims[pnum]

    fig, ax = plt.subplots(figsize=(8, 11))

    for word in words:
        polygon = word["polygon"]
        points = [(polygon[i] * DPI, polygon[i+1] * DPI) for i in range(0, len(polygon), 2)]
        poly = Polygon(points, closed=True, edgecolor='blue', facecolor='none', linewidth=1)
        ax.add_patch(poly)

        text_x, text_y = points[0]
        ax.text(text_x, text_y, word["content"], fontproperties=thai_font, fontsize=6, verticalalignment='top')

    ax.set_xlim(0, width_px)
    ax.set_ylim(height_px, 0)
    ax.set_aspect('equal')
    ax.set_title(f"Word Bounding Boxes - Page {pnum}", fontproperties=thai_font)

    plt.show()
