import json
from pythainlp.tag import pos_tag
from pythainlp.tokenize import word_tokenize
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from sklearn.cluster import DBSCAN
import matplotlib.font_manager as fm

thai_font = fm.FontProperties(fname="C:/Windows/Fonts/tahoma.ttf")

# โหลดไฟล์ JSON
with open("Data/overlap_testing_file.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)

def visualize_words_and_clustering(word_boxes, lines, page_width, page_height, save_path=None):
    """แสดงภาพ word boxes และผลการจัดกลุ่มบรรทัด"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 12))
    
    # ภาพซ้าย: แสดง word boxes ทั้งหมด
    ax1.set_title("All Word Boxes (Original)", fontsize=14)
    for i, word in enumerate(word_boxes):
        # วาด bounding box
        rect = Rectangle((word["min_x"] * page_width, 
                         (1 - word["max_y"]) * page_height),
                        (word["max_x"] - word["min_x"]) * page_width,
                        (word["max_y"] - word["min_y"]) * page_height,
                        linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.3)
        ax1.add_patch(rect)
        
        # แสดงข้อความ
        ax1.text(word["center_x"] * page_width, 
                (1 - word["center_y"]) * page_height, 
                word["content"], fontproperties=thai_font, fontsize=6, verticalalignment='top')
    
    ax1.set_xlim(0, page_width)
    ax1.set_ylim(0, page_height)
    ax1.set_aspect('equal')
    
    # ภาพขวา: แสดงผลการจัดกลุ่มบรรทัด
    ax2.set_title("Line Clustering Result", fontsize=14)
    colors = plt.cm.tab20(np.linspace(0, 1, len(lines)))
    
    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        for word in line:
            # วาด bounding box ด้วยสีตามบรรทัด
            rect = Rectangle((word["min_x"] * page_width, 
                             (1 - word["max_y"]) * page_height),
                            (word["max_x"] - word["min_x"]) * page_width,
                            (word["max_y"] - word["min_y"]) * page_height,
                            linewidth=2, edgecolor=color, facecolor=color, alpha=0.3)
            ax2.add_patch(rect)
            
            # แสดงข้อความ
            ax2.text(word["center_x"] * page_width, 
                    (1 - word["center_y"]) * page_height, 
                    word["content"], fontproperties=thai_font, fontsize=6, verticalalignment='top')
    
    ax2.set_xlim(0, page_width)
    ax2.set_ylim(0, page_height)
    ax2.set_aspect('equal')
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.show()

def cluster_lines_with_dbscan(word_boxes):
    """ใช้ DBSCAN clustering สำหรับจัดกลุ่มบรรทัด"""
    if not word_boxes:
        return []
    
    # เตรียมข้อมูลสำหรับ DBSCAN (ใช้ center_y และ height)
    features = []
    for word in word_boxes:
        features.append([word["center_y"], word["height"]])
    
    features = np.array(features)
    
    # ใช้ DBSCAN clustering
    # eps: ระยะทางสูงสุดระหว่างจุดในกลุ่มเดียวกัน
    # min_samples: จำนวนจุดขั้นต่ำในกลุ่ม
    clustering = DBSCAN(eps=0.02, min_samples=1).fit(features)
    
    # จัดกลุ่มคำตาม cluster labels
    clusters = {}
    for i, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(word_boxes[i])
    
    # เรียงกลุ่มตามตำแหน่ง Y และเรียงคำภายในกลุ่มตามตำแหน่ง X
    lines = []
    for cluster_id, words in clusters.items():
        # เรียงคำในบรรทัดตามแกน X
        words.sort(key=lambda w: w["center_x"])
        lines.append(words)
    
    # เรียงบรรทัดตามแกน Y (ใช้ค่าเฉลี่ยของ center_y ในแต่ละบรรทัด)
    lines.sort(key=lambda line: sum(w["center_y"] for w in line) / len(line))
    
    return lines

def cluster_lines_improved(word_boxes):
    """การจัดกลุ่มบรรทัดแบบปรับปรุง"""
    if not word_boxes:
        return []
    
    lines = []
    remaining_words = word_boxes.copy()
    
    while remaining_words:
        # เริ่มต้นด้วยคำที่มี Y ต่ำสุด (บนสุด)
        remaining_words.sort(key=lambda w: w["center_y"])
        seed_word = remaining_words.pop(0)
        current_line = [seed_word]
        
        # หาคำที่อยู่บรรทัดเดียวกัน
        words_to_remove = []
        for i, word in enumerate(remaining_words):
            if is_same_line(seed_word, word, current_line):
                current_line.append(word)
                words_to_remove.append(i)
        
        # ลบคำที่ใช้แล้วออกจาก remaining_words
        for i in sorted(words_to_remove, reverse=True):
            remaining_words.pop(i)
        
        # เรียงคำในบรรทัดตามแกน X
        current_line.sort(key=lambda w: w["center_x"])
        lines.append(current_line)
    
    return lines

def is_same_line(reference_word, test_word, current_line):
    """ตรวจสอบว่าคำสองคำอยู่บรรทัดเดียวกันหรือไม่"""
    # คำนวณค่าเฉลี่ยของบรรทัดปัจจุบัน
    avg_y = sum(w["center_y"] for w in current_line) / len(current_line)
    avg_height = sum(w["height"] for w in current_line) / len(current_line)
    
    # เช็ค vertical overlap
    ref_top = reference_word["min_y"]
    ref_bottom = reference_word["max_y"]
    test_top = test_word["min_y"]
    test_bottom = test_word["max_y"]
    
    overlap_top = max(ref_top, test_top)
    overlap_bottom = min(ref_bottom, test_bottom)
    overlap_height = max(0, overlap_bottom - overlap_top)
    
    min_height = min(reference_word["height"], test_word["height"])
    overlap_ratio = overlap_height / min_height if min_height > 0 else 0
    
    # เงื่อนไขการจัดกลุ่ม
    y_distance = abs(test_word["center_y"] - avg_y)
    
    # เงื่อนไข 1: มี overlap ratio เพียงพอ
    has_enough_overlap = overlap_ratio > 0.4
    
    # เงื่อนไข 2: ระยะห่าง Y ไม่เกินครึ่งหนึ่งของความสูงเฉลี่ย
    reasonable_distance = y_distance < (avg_height * 0.4)
    
    return has_enough_overlap and reasonable_distance

output_lines = []
total_words = 0
total_words_filtered = 0 

for page_idx, page in enumerate(json_data["analyzeResult"]["pages"]):
    print(f"\n=== ประมวลผลหน้า {page_idx + 1} ===")
    
    words = page["words"]
    page_width = page["width"]
    page_height = page["height"]

    word_boxes = []
    for word in words:
        # ถ้า content มี \n ให้แตกเป็นคำย่อย
        if "\n" in word["content"]:
            parts = [p.strip() for p in word["content"].split("\n") if p.strip()]
        else:
            parts = [word["content"]]

        polygon = word["polygon"]
        x_coords = polygon[::2]
        y_coords = polygon[1::2]

        # คำนวณตำแหน่ง bounding box
        min_x = min(x_coords) / page_width
        max_x = max(x_coords) / page_width
        min_y = min(y_coords) / page_height
        max_y = max(y_coords) / page_height
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        height = max_y - min_y

        # เก็บคำ (หรือบรรทัดย่อยจาก \n)
        for part in parts:
            word_boxes.append({
                "content": part,
                "center_x": center_x,
                "center_y": center_y,
                "min_x": min_x,
                "max_x": max_x,
                "min_y": min_y,
                "max_y": max_y,
                "height": height
            })

    # ลองทั้งสองวิธี
    print("\n--- ทดสอบ Improved Method ---")
    lines_improved = cluster_lines_improved(word_boxes)
    
    print("\n--- ทดสอบ DBSCAN Method ---")
    lines_dbscan = cluster_lines_with_dbscan(word_boxes)
    
    # เลือกวิธีที่ให้ผลดีที่สุด (ใช้จำนวนบรรทัดเป็นเกณฑ์เบื้องต้น)
    if abs(len(lines_improved) - 8) < abs(len(lines_dbscan) - 8):  # สมมติว่าควรมี 8 บรรทัด
        lines = lines_improved
        method_used = "Improved"
    else:
        lines = lines_dbscan
        method_used = "DBSCAN"
    
    print(f"\n🎯 ใช้วิธี: {method_used}")
    print(f"จำนวนบรรทัดที่ตรวจพบ: {len(lines)}")

    # แสดง visualization
    visualize_words_and_clustering(word_boxes, lines, page_width, page_height, 
                                 f"Data/clustering_result_page_{page_idx + 1}.png")

    # แปลงเป็นข้อความ
    for line_idx, line in enumerate(lines):
        line_text = ""
        for i, word in enumerate(line):
            line_text += word["content"]
            if i < len(line) - 1:
                next_word = line[i + 1]
                space = next_word["center_x"] - word["center_x"]
                if space > 0.06:  # threshold สำหรับการเว้นวรรค
                    line_text += "_"

        # Debug: แสดงข้อมูลบรรทัด
        y_positions = [w["center_y"] for w in line]
        heights = [w["height"] for w in line]
        
        print(f"บรรทัด {line_idx + 1}: {line_text}")
        print(f"  - Y range: {min(y_positions):.4f} - {max(y_positions):.4f}")
        print(f"  - Height range: {min(heights):.4f} - {max(heights):.4f}")
        print(f"  - จำนวนคำ: {len(line)}")
        
        # ตรวจสอบ overlap ระหว่างบรรทัด
        if line_idx > 0:
            prev_line = lines[line_idx - 1]
            prev_y_max = max(w["max_y"] for w in prev_line)
            curr_y_min = min(w["min_y"] for w in line)
            if prev_y_max > curr_y_min:
                print(f"  ⚠️  มี overlap กับบรรทัดก่อนหน้า: {prev_y_max:.4f} > {curr_y_min:.4f}")
        print()

        tokens = word_tokenize(line_text.replace("_", " "), keep_whitespace=False)
        tags = pos_tag(tokens, engine="perceptron", corpus="orchid")

        filtered_tokens = [word for word, tag in tags if tag not in ["NPRP", "NTTL"]]

        word_count = len(tokens)
        word_count_filtered = len(filtered_tokens)

        total_words += word_count
        total_words_filtered += word_count_filtered

        output_lines.append(line_text)

print(f"\n📊 สรุปผล:")
print(f"จำนวนคำทั้งหมดก่อนคัดกรอง: {total_words}")
print(f"จำนวนคำทั้งหมดหลังคัดกรอง: {total_words_filtered}")

# บันทึกผลลัพธ์เป็นไฟล์ txt
with open("Data/output_sorted_lines.txt", "w", encoding="utf-8") as out_file:
    for line in output_lines:
        out_file.write(line + "\n")

print("✅ บันทึกไฟล์เรียบร้อย: Data/output_sorted_lines.txt")
print("🎨 ภาพ visualization ถูกบันทึกที่: Data/clustering_result_page_*.png")