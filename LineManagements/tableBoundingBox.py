import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import json
import matplotlib.font_manager as fm

thai_font = fm.FontProperties(fname="C:/Windows/Fonts/tahoma.ttf")

with open("LineManagements/Data/meeting_executive4_66.pdf.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

page_to_plot = 28

fig, ax = plt.subplots(figsize=(8, 11))

for table_index, table in enumerate(json_data["analyzeResult"]["tables"]):
    for cell in table["cells"]:
        content = cell.get("content", "")
        for br in cell.get("boundingRegions", []):
            if br.get("pageNumber") != page_to_plot:
                continue

            polygon = br.get("polygon", [])
            if not polygon:
                continue

            points = [(polygon[i], polygon[i+1]) for i in range(0, len(polygon), 2)]

            poly = Polygon(points, closed=True, edgecolor='blue', facecolor='none', linewidth=1)
            ax.add_patch(poly)

            text_x, text_y = points[0]
            ax.text(text_x, text_y, content, fontproperties=thai_font, fontsize=6, verticalalignment='top')

page_data = next((p for p in json_data["analyzeResult"]["pages"] if p["pageNumber"] == page_to_plot), None)
if page_data:
    page_width = page_data["width"]
    page_height = page_data["height"]
else:
    page_width, page_height = 800, 1100  # fallback

ax.set_xlim(0, page_width)
ax.set_ylim(page_height, 0)
ax.set_aspect('equal')
ax.set_title(f"All Tables - Page {page_to_plot} Cell Bounding Boxes", fontproperties=thai_font)

plt.show()
