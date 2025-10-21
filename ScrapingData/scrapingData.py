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
        m = re.search(r"\(ครั้งที่\s*(\d+)\)", meeting_no)
        if m:
            meeting_seq = m.group(1)
    if len(texts) >= 3:
        meeting_date = texts[2]

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

        a_tag = p.find("a")
        if a_tag and a_tag.get("id"):
            if temp_text and current_section == "resolution":
                resolutions.append(temp_text.strip())
                temp_text = ""
            current_section = "agenda"
            agendas.append(a_tag.get_text(strip=True))
            continue

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


        if current_section == "agenda":
            current_section = "resolution"
            temp_text += text + "\n"
        elif current_section == "resolution":
            temp_text += text + "\n"
        elif current_section == "summary":
            summaries.append(text)

    if temp_text and current_section == "resolution":
        resolutions.append(temp_text.strip())

print("Agendas / หัวเรื่อง:")
for a in agendas:
    print("-", a)

print("\nSummary / สรุปสาระสำคัญ:")
for s in summaries:
    print("-", s)

print("\nResolutions / มติการประชุม:")
for r in resolutions:
    print("-", r[:300], "...")


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
        f.write(r + "\n\n")
    
    f.write("\nSummary / สรุปสาระสำคัญ:\n")
    for s in summaries:
        f.write(s + "\n")

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

# ✅ ลงทะเบียนฟอนต์ภาษาไทย
pdfmetrics.registerFont(TTFont('THSarabun', 'ScrapingData/fonts/Sarabun-Regular.ttf'))

# ✅ ตั้งชื่อไฟล์ PDF
pdf_path = "ScrapingData/Data/output_thai.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=A4)

# ✅ กำหนดสไตล์ให้ใช้ฟอนต์ไทย
title_style = ParagraphStyle(
    'title_style',
    fontName='THSarabun',
    fontSize=20,
    textColor=colors.darkblue,
    spaceAfter=10
)

section_style = ParagraphStyle(
    'section_style',
    fontName='THSarabun',
    fontSize=16,
    textColor=colors.darkred,
    spaceAfter=6
)

normal_style = ParagraphStyle(
    'normal_style',
    fontName='THSarabun',
    fontSize=14,
    leading=18,  # ระยะบรรทัด
)

# ✅ เริ่มสร้างเอกสาร
story = []

story.append(Paragraph("สรุปข้อมูลการประชุม", title_style))
story.append(Paragraph(f"หัวข้อ: {title}", normal_style))
story.append(Paragraph(f"การประชุม: {meeting_no}", normal_style))
story.append(Paragraph(f"ครั้งที่: {meeting_seq}", normal_style))
story.append(Paragraph(f"วันที่ประชุม: {meeting_date}", normal_style))
story.append(Spacer(1, 12))

# หัวข้อการประชุม
story.append(Paragraph("หัวข้อการประชุม / Agenda", section_style))
for a in agendas:
    story.append(Paragraph(f"- {a}", normal_style))
story.append(Spacer(1, 10))

# มติการประชุม
story.append(Paragraph("มติการประชุม / Resolution", section_style))
for r in resolutions:
    story.append(Paragraph(r.replace("\n", "<br/>"), normal_style))
story.append(Spacer(1, 10))

# สรุปสาระสำคัญ
story.append(Paragraph("สรุปสาระสำคัญ / Summary", section_style))
for s in summaries:
    story.append(Paragraph(s, normal_style))

# ✅ สร้าง PDF
doc.build(story)
print(f"✅ บันทึกไฟล์ PDF ภาษาไทยเรียบร้อย: {pdf_path}")
