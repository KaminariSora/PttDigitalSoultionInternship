import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient

mongoDB = "mongodb://localhost:27017/"
DataBaseName = "TestData"
websiteUrl = "https://www.eppo.go.th/index.php/th/component/k2/item/10921-cepa-taksin13"

client = MongoClient(mongoDB)
db = client[DataBaseName]

meetings_col = db["meetings"]
attendees_col = db["attendees"]
agendas_col = db["agendas"]
details_col = db["details"]

# --------------------------
# Scraping
# --------------------------
url = websiteUrl
resp = requests.get(url)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

content_tag = soup.find("div", class_="itemFullText")

title, meeting_no, meeting_seq, meeting_date = "", "", "", ""

if content_tag:
    # --- เก็บ <p> ก่อนถึง <hr> ---
    pre_hr_paras = []
    for child in content_tag.children:
        if child.name == "hr":
            break
        if child.name == "p":
            txt = child.get_text(strip=True)
            if txt:
                pre_hr_paras.append(txt)

    # -------------------------
    # Mapping ข้อมูลจาก pre_hr_paras
    # -------------------------
    if len(pre_hr_paras) >= 1:
        title = pre_hr_paras[0]   # หัวเรื่องประชุม
    if len(pre_hr_paras) >= 2:
        meeting_no = pre_hr_paras[1]  # "การประชุม... (ครั้งที่ 71)"
        m = re.search(r"\(ครั้งที่\s*(\d+)\)", meeting_no)
        if m:
            meeting_seq = int(m.group(1))  # แปลงเป็น int
    if len(pre_hr_paras) >= 3:
        meeting_date = pre_hr_paras[2]  # วันที่
    if len(pre_hr_paras) >= 4:
        location = pre_hr_paras[3]  # สถานที่

# -------------------------
# หาผู้เข้าประชุม Attendees (parse position/role/name)
# -------------------------
def norm(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def split_position_role(line: str):
    """
    รับบรรทัดที่เป็น 'ตำแหน่ง..............บทบาท'
    แล้วแยกเป็น (position, role)
    """
    line = norm(line)
    parts = re.split(r"\s{4,}", line)
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        position = parts[0]
        role = parts[-1]
        return position, role

    ROLE_WORDS = r"(ประธานกรรมการ|รองประธานกรรมการ|กรรมการและเลขานุการ|กรรมการและผู้ช่วยเลขานุการ|กรรมการ|เลขานุการ)"
    m = re.search(ROLE_WORDS + r"$", line)
    if m:
        role = m.group(1)
        position = norm(line[:m.start()].rstrip(" ."))
        return position, role

    return line, ""  # ถ้าแยกไม่ได้

def clean_person_name(line: str):
    line = norm(line)
    m = re.match(r"^\((.+)\)$", line)
    return m.group(1).strip() if m else line

attendees = []
if content_tag:
    nodes = list(content_tag.find_all("p"))
    in_section = False
    buffer_lines = []

    for p in nodes:
        t = p.get_text(" ", strip=True)
        t = norm(t)
        if not t:
            continue

        if not in_section:
            if "ผู้มาประชุม" in t:
                in_section = True
            continue
        else:
            # ถ้าเริ่มเป็นหัวข้อถัดไป/วาระ หยุด
            if re.match(r"^(เรื่องที่|วาระที่)\s*\d+", t) or re.fullmatch(r"มติ", t) or re.search(r"สรุป\s*สาระ\s*สำคัญ", t):
                break
            buffer_lines.append(t)

    # จับคู่: (ตำแหน่ง+บทบาท) -> (ชื่อ)
    i = 0
    while i < len(buffer_lines):
        pos_role_line = buffer_lines[i]
        name_line = buffer_lines[i+1] if i+1 < len(buffer_lines) else ""
        position, role = split_position_role(pos_role_line)
        person_name = clean_person_name(name_line)
        attendees.append({
            "position": position,
            "role": role,
            "name": person_name
        })
        i += 2

agendas = []
current_agenda = None
current_section = None

def norm(s: str) -> str:
    # แก้ NBSP และช่องว่างติดกัน
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

if content_tag:
    # เก็บทั้ง <p> และ <li> เพราะหลายหัวข้อ/ข้อย่อยอยู่ใน <li>
    nodes = content_tag.find_all(["p", "li"])

    for node in nodes:
        text = node.get_text(" ", strip=True)
        text = norm(text)
        if not text:
            continue

        # --- เริ่ม agenda ใหม่: ถ้ามี <a id> หรือขึ้นต้นด้วย "เรื่องที่/วาระที่"
        a_tag = node.find("a")
        if a_tag and a_tag.get("id"):
            if current_agenda:
                agendas.append(current_agenda)
            current_agenda = {
                "agenda": norm(a_tag.get_text(" ", strip=True)),
                "summaries": [],
                "resolutions": []
            }
            current_section = None
            continue

        if re.match(r"^(เรื่องที่|วาระที่)\s*\d+", text):
            if current_agenda:
                agendas.append(current_agenda)
            current_agenda = {
                "agenda": text,    # เก็บทั้งบรรทัดเป็นชื่อเรื่อง
                "summaries": [],
                "resolutions": []
            }
            current_section = None
            continue

        # --- หัวข้อย่อยแบบเป็น "หัวข้อ" เต็มบรรทัด
        if re.match(r"^\s*สรุป\s*สาระ\s*สำคัญ\s*[:：]?\s*$", text):
            current_section = "summary"
            continue

        # หัวข้อ "มติ" เฉพาะกรณีเป็นหัวข้อเต็มบรรทัดเท่านั้น
        if re.match(r"^\s*(?:มติ(?:ของที่ประชุม)?|ที่ประชุมมีมติ)\s*[:：]?\s*$", text):
            current_section = "resolution"
            continue

        # --- กรณี "มติ" แบบ inline ในบรรทัดเดียว (ขึ้นต้นด้วยมติแล้วตามด้วยเนื้อหา)
        m_res_inline = re.match(
            r"^\s*(?:มติ(?:ของที่ประชุม)?|ที่ประชุมมีมติ)\s*[:：]?\s*(.+)$", text
        )
        if m_res_inline:
            if current_agenda:
                current_section = "resolution"
                current_agenda["resolutions"].append(m_res_inline.group(1).strip())
            continue

        # --- เก็บข้อความตามเซกชันปัจจุบัน
        if current_agenda:
            if current_section == "summary":
                current_agenda["summaries"].append(text)
            elif current_section == "resolution":
                current_agenda["resolutions"].append(text)
            else:
                # ยังไม่ประกาศหัวข้อ summary/resolution: ข้าม (กันข้อมูลหลุดเซกชัน)
                pass

    # เก็บ agenda สุดท้าย
    if current_agenda:
        agendas.append(current_agenda)

# --------------------------
# Insert into MongoDB
# --------------------------

# Meeting
meeting_doc = {
    "title": title,
    "meeting_no": meeting_no,
    "meeting_seq": meeting_seq,
    "meeting_date": meeting_date,
}

meeting_id = meetings_col.insert_one(meeting_doc).inserted_id

# Attendees
for person in attendees:
    attendees_col.insert_one({
        "meeting_seq": meeting_seq,
        "position": person["position"], 
        "role": person["role"],         
        "name": person["name"]          
    })

# Agendas and details
for i, agenda in enumerate(agendas, start=1):
    # Insert เข้า collection "เรื่องที่ประชุม"
    agendas_col.insert_one({
        "meeting_seq": meeting_seq,
        "agenda_no": i,
        "agenda_title": agenda["agenda"]
    })

    # Insert เข้า collection "รายละเอียดการประชุม"
    details_col.insert_one({
        "meeting_seq": meeting_seq,
        "agenda_no": i,
        "summary": " ".join(agenda["summaries"]) if agenda["summaries"] else "",
        "resolution": " ".join(agenda["resolutions"]) if agenda["resolutions"] else ""
    })

print(f"Insert information from {websiteUrl} to {DataBaseName} complete!")
