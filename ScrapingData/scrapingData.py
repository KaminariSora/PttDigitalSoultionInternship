import requests
from bs4 import BeautifulSoup
import re

url = "https://www.eppo.go.th/index.php/th/component/k2/item/21751-cepa-settha71"
resp = requests.get(url)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

content_tag = soup.find("div", class_="itemFullText")

title, meeting_no, meeting_seq, meeting_date = "", "", "", ""

if content_tag:
    centered_paras = content_tag.find_all("p", style=lambda v: v and "text-align: center" in v)
    texts = [p.get_text(strip=True) for p in centered_paras if p.get_text(strip=True)]

    if len(texts) >= 1:
        title = texts[0]
    if len(texts) >= 2:
        meeting_no = texts[1]
        # แยกเลขในวงเล็บด้วย regex
        m = re.search(r"\(ครั้งที่\s*(\d+)\)", meeting_no)
        if m:
            meeting_seq = m.group(1)  # 71
    if len(texts) >= 3:
        meeting_date = texts[2]  # วันพฤหัสบดีที่ 27 มีนาคม 2568

print("Title:", title)
print("Meeting No (Raw):", meeting_no)
print("Meeting Seq (Extracted):", meeting_seq)
print("Date:", meeting_date)

agendas = []
resolutions = []
summaries = []

if content_tag:
    paragraphs = content_tag.find_all("p")
    
    current_section = None
    temp_text = ""

    for p in paragraphs:
        text = p.get_text(strip=True)
        if not text:
            continue

        # ตรวจสอบหัวเรื่อง (Agenda)
        a_tag = p.find("a")
        if a_tag and a_tag.get("id"):
            if temp_text and current_section == "resolution":
                resolutions.append(temp_text.strip())
                temp_text = ""
            current_section = "agenda"
            agendas.append(a_tag.get_text(strip=True))
            continue

        # ตรวจสอบมติการประชุม (Resolution)
        span_tag = p.find("span", style=lambda v: v and "underline" in v)
        if span_tag:
            span_text = span_tag.get_text()
            if "มติ" in span_text:
                if temp_text and current_section == "resolution":
                    resolutions.append(temp_text.strip())
                    temp_text = ""
                current_section = "resolution"
                continue
            elif "สรุปสาระสำคัญ" in span_text:
                if temp_text and current_section == "resolution":
                    resolutions.append(temp_text.strip())
                    temp_text = ""
                current_section = "summary"
                continue

        # เก็บข้อความตาม section ปัจจุบัน
        if current_section == "agenda":
            # ข้อความหลังหัวเรื่องถือเป็น resolution
            current_section = "resolution"
            temp_text += text + "\n"
        elif current_section == "resolution":
            temp_text += text + "\n"
        elif current_section == "summary":
            summaries.append(text)

    # ถ้ามี resolution สุดท้ายค้างอยู่
    if temp_text and current_section == "resolution":
        resolutions.append(temp_text.strip())

# -------------------------
# แสดงผล
# -------------------------
print("Agendas / หัวเรื่อง:")
for a in agendas:
    print("-", a)

print("\nSummary / สรุปสาระสำคัญ:")
for s in summaries:
    print("-", s)

print("\nResolutions / มติการประชุม:")
for r in resolutions:
    print("-", r[:300], "...")  # preview 300 ตัวอักษร


with open("ScrapingData/Data/output.txt", "w", encoding="utf-8") as f:
    f.write(f"Agendas / หัวเรื่อง:\n")
    f.write(f"Title: {title}\n")
    f.write(f"Meeting No (Raw): {meeting_no}\n")
    f.write(f"Meeting Seq (Extracted): {meeting_seq}\n")
    f.write(f"Date: {meeting_date}\n\n")
    for a in agendas:
        f.write(a + "\n")
    
    f.write("\nResolutions / มติการประชุม:\n")
    for r in resolutions:
        f.write(r + "\n\n")  # เพิ่มบรรทัดว่างระหว่างมติ
    
    f.write("\nSummary / สรุปสาระสำคัญ:\n")
    for s in summaries:
        f.write(s + "\n")