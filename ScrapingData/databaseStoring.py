import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient
from pymongo import ReturnDocument
from datetime import datetime

mongoDB = "mongodb://localhost:27017/"
DataBaseName = "PttDigitalSolution"
websiteUrl = "https://www.eppo.go.th/index.php/th/component/k2/item/21607-nepc-prayut-25-12-67"
organization = "กพช."
documentType = "มติ"

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

def get_next_sequence(name: str):
    counters = db["counters"]
    ret = counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return ret["seq"]

def get_next_ref_for_org(org: str) -> int:
    key = f"meeting_ref:{org}"
    ret = db["counters"].find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return ret["seq"]

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
        line = pre_hr_paras[1]

        # เก็บข้อความเต็มดิบ เช่น "ครั้งที่ 4/2567 (ครั้งที่ 170)"
        meeting_no_full = line  

        # --- meeting_no: "4/2567"
        m_no = re.search(r"ครั้งที่\s*([0-9]{1,3})\s*/\s*([0-9]{4})", line)
        if m_no:
            meeting_no = f"{m_no.group(1)}/{m_no.group(2)}"

        # --- meeting_seq: "(ครั้งที่ 170)"
        m_seq = re.search(r"\(ครั้งที่\s*([0-9]+)\)", line)
        if m_seq:
            meeting_seq = int(m_seq.group(1))

    if len(pre_hr_paras) >= 3:
        meeting_date = pre_hr_paras[2]  # วันที่
    if len(pre_hr_paras) >= 4:
        location = pre_hr_paras[3]  # สถานที่

from datetime import datetime
import re

_THAI2AR = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

_THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3,
    "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9,
    "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}

_MONTHS_ALT = r"(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)"

def _norm(s: str) -> str:
    if not s:
        return ""
    # แทน NBSP และยุบช่องว่าง
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s.strip())
    # แปลงเลขไทย -> อารบิก
    return s.translate(_THAI2AR)

def parse_thai_date(date_str: str):
    """
    รองรับเช่น:
      - 'วันพุธที่ 5 กันยายน พ.ศ. 2561 เวลา 13.30 น.'
      - '5 กันยายน 2561'
      - '5 กันยายน พ.ศ.2561 09:05'
      - 'วันอังคารที่ 1 ตุลาคม 2562 เวลา 9.00 น.'
    """
    if not date_str:
        return None

    s = _norm(date_str)

    pat = re.compile(
        rf"(?:วัน[ก-๙]+(?:ที่)?)?\s*"
        rf"(?P<day>\d{{1,2}})\s+"
        rf"(?P<month>{_MONTHS_ALT})\s+"
        rf"(?:(?:พ\.?\s*ศ\.?|พศ)\s*)?"
        rf"(?P<year>\d{{4}})"
        rf"(?:\s*(?:เวลา)?\s*(?P<hour>\d{{1,2}})[.:](?P<minute>\d{{2}})\s*(?:น\.?)?)?",
        re.IGNORECASE
    )

    m = pat.search(s)
    if not m:
        return None

    day = int(m.group("day"))
    month_name = m.group("month")
    year = int(m.group("year"))
    hour = int(m.group("hour")) if m.group("hour") else 0
    minute = int(m.group("minute")) if m.group("minute") else 0

    month = _THAI_MONTHS.get(month_name)
    if not month:
        return None

    # ปีไทย -> ค.ศ. (ถ้ามากกว่า 2400 ถือว่า พ.ศ.)
    if year >= 2400:
        year -= 543

    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None



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
    line = line.strip("()[]{}")  
    return line.strip()

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
# meeting_no_auto = get_next_sequence("meeting_no")
meeting_date_obj = parse_thai_date(meeting_date)
meeting_ref = get_next_ref_for_org(organization)

agenda_titles = [a.get("agenda", "").strip() for a in agendas if a.get("agenda")]
# Meeting
meeting_doc = {
    "title": title,
    "meeting_ref": meeting_ref,
    "meeting_no_full": meeting_no_full,
    "meeting_no": meeting_no,
    "meeting_seq": meeting_seq,
    "meeting_date": meeting_date,
    "meeting_date_obj": meeting_date_obj,
    "organization": organization,
    "doc_type": documentType,
    "total_title": agenda_titles 
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
