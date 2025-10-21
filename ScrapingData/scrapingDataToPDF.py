import requests
from bs4 import BeautifulSoup
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors


# -------------------------------
#  ตั้งค่าฟอนต์ไทย
# -------------------------------
FONT_PATH = "ScrapingData/fonts/Sarabun-Regular.ttf"
pdfmetrics.registerFont(TTFont('THSarabun', FONT_PATH))

# -------------------------------
#  ฟังก์ชันสร้าง PDF
# -------------------------------
def save_pdf(title, meeting_no, meeting_seq, meeting_date, agendas, resolutions, summaries, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4)

    title_style = ParagraphStyle('Title', fontName='THSarabun', fontSize=20, textColor=colors.darkblue)
    section_style = ParagraphStyle('Section', fontName='THSarabun', fontSize=16, textColor=colors.darkred)
    normal_style = ParagraphStyle('Normal', fontName='THSarabun', fontSize=14, leading=18)

    story = []
    story.append(Paragraph(f"สรุปข้อมูลการประชุม", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"หัวข้อ: {title}", normal_style))
    story.append(Paragraph(f"การประชุม: {meeting_no}", normal_style))
    story.append(Paragraph(f"ครั้งที่: {meeting_seq}", normal_style))
    story.append(Paragraph(f"วันที่ประชุม: {meeting_date}", normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("หัวข้อการประชุม / Agendas", section_style))
    for a in agendas:
        story.append(Paragraph(f"- {a}", normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("มติการประชุม / Resolutions", section_style))
    for r in resolutions:
        story.append(Paragraph(r.replace("\n", "<br/>"), normal_style))
        story.append(Spacer(1, 5))

    story.append(Paragraph("สรุปสาระสำคัญ / Summary", section_style))
    for s in summaries:
        story.append(Paragraph(s, normal_style))
        story.append(Spacer(1, 5))

    doc.build(story)
    print(f"✅ PDF saved: {output_path}")


# -------------------------------
#  ฟังก์ชันหลัก: ดึงข้อมูลจาก 1 ลิงก์
# -------------------------------
def scrape_eppo_page(url):
    print(f"🔍 กำลังดึงข้อมูลจาก: {url}")
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_tag = soup.find("div", class_="itemFullText")
    title = meeting_no = meeting_seq = meeting_date = ""
    agendas, resolutions, summaries = [], [], []

    if content_tag:
        centered_paras = content_tag.find_all("p", style=lambda v: v and "text-align: center" in v)
        texts = [p.get_text(strip=True) for p in centered_paras if p.get_text(strip=True)]
        if len(texts) >= 1: title = texts[0]
        if len(texts) >= 2:
            meeting_no = texts[1]
            m = re.search(r"\(ครั้งที่\s*(\d+)\)", meeting_no)
            if m: meeting_seq = m.group(1)
        if len(texts) >= 3: meeting_date = texts[2]

        paragraphs = content_tag.find_all("p")
        current_section, temp_text = None, ""
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

    # -------------------------------
    #  สร้าง PDF
    # -------------------------------
    safe_title = re.sub(r'[^\w\d-]', '_', title[:50]) or "meeting"
    filename = f"{safe_title}_ครั้งที่{meeting_seq or 'X'}"
    output_path = os.path.join("ScrapingData/Data", f"{filename}.pdf")
    save_pdf(title, meeting_no, meeting_seq, meeting_date, agendas, resolutions, summaries, output_path)
    return output_path


# -------------------------------
#  ดึงหลายลิงก์พร้อมกัน
# -------------------------------
urls = [
    "https://www.eppo.go.th/index.php/th/component/k2/item/21751-cepa-settha71",
    "https://www.eppo.go.th/index.php/th/component/k2/item/21609-cepa-settha70", 
    "https://www.eppo.go.th/index.php/th/component/k2/item/21264-cepa-settha69",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/21140-cepa-settha68",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20989-cepa-settha67",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20741-cepa-settha66",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20660-cepa-settha65",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20412-cepa-settha64",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20411-cepa-settha63",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/20120-cepa-settha62",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/19991-cepa-settha60",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/19855-cepa-prayut60",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/19323-cepa-prayut59",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/19322-cepa-prayut58",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/19249-cepa-prayut56",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/18753-cepa-prayut56",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/18665-cepa-prayut55",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/18611-cepa-prayut54",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/18561-cepa-prayut53",       
    "https://www.eppo.go.th/index.php/th/component/k2/item/18520-cepa-prayut52",             
]
os.makedirs("ScrapingData/Data", exist_ok=True)

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(scrape_eppo_page, url) for url in urls]
    for future in as_completed(futures):
        try:
            print(f"🎯 เสร็จแล้ว -> {future.result()}")
        except Exception as e:
            print(f"❌ Error: {e}")
