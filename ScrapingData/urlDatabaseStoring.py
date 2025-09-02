import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient, ReturnDocument
from datetime import datetime

# --------------------------
# CONFIG
# --------------------------
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "ResolutionScraping"
# กพช
urls_NEPC = [
    "https://www.eppo.go.th/index.php/th/component/k2/item/21607-nepc-prayut-25-12-67",
    "https://www.eppo.go.th/index.php/th/component/k2/item/21606-nepc-prayut-26-11-67",     
    "https://www.eppo.go.th/index.php/th/component/k2/item/21188-nepc-prayut-04-09-67",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/20914-nepc-prayut25-06-67",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/20679-nepc-prayut13-12-66",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/20113-nepc-prayut03-09-66",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/19321-nepc-prayut02-13-66",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/19221-nepc-prayut11-25-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/19220-nepc-prayut11-07-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/18612-nepc-prayut09-09-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/18365-nepc-prayut06-07-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/18364-nepc-prayut22-06-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/18185-nepc-prayut06-05-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/17973-nepc-prayut09-03-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/17827-nepc-prayut06-01-65",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/17689-nepc-prayut05-11-64",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/17213-nepc-prayut04-08-64",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/16806-nepc-prayut01-04-64",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/16515-nepc-prayut25-12-63",   
    "https://www.eppo.go.th/index.php/th/component/k2/item/16391-nepc-prayut16-11-63",   
]

# กบง
urls_CEPA = [
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
org = "กบง"
ORGANIZATION = org + "."
DOC_TYPE = "มติ"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
meetings_col  = db["meetings"]
attendees_col = db["attendees"]
agendas_col   = db["agendas"]
details_col   = db["details"]

THAI2AR = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3,
    "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9,
    "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
MONTHS_ALT = r"(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)"

def norm(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s.strip())
    return s

def _norm_and_translate_digits(s: str) -> str:
    return norm(s).translate(THAI2AR)

def parse_thai_date(date_str: str):
    """
    รองรับ:
      - 'วันพุธที่ 5 กันยายน พ.ศ. 2561 เวลา 13.30 น.'
      - '5 กันยายน 2561'
      - '5 กันยายน พ.ศ.2561 09:05'
      - 'วันอังคารที่ 1 ตุลาคม 2562 เวลา 9.00 น.'
    """
    if not date_str:
        return None
    s = _norm_and_translate_digits(date_str)
    pat = re.compile(
        rf"(?:วัน[ก-๙]+(?:ที่)?)?\s*"
        rf"(?P<day>\d{{1,2}})\s+"
        rf"(?P<month>{MONTHS_ALT})\s+"
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
    month = THAI_MONTHS.get(month_name)
    if not month:
        return None
    if year >= 2400:
        year -= 543
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None

def get_next_ref_for_org(org: str) -> int:
    key = f"meeting_ref:{org}"
    ret = db["counters"].find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return ret["seq"]

def get_next_ref() -> int:
    ret = db["counters"].find_one_and_update(
        {"_id": "meeting_ref"},
        {"$inc": {"seq": 1}},  
        upsert=True,       
        return_document=ReturnDocument.AFTER
    )
    return ret["seq"]

def split_position_role(line: str):
    """แยก 'ตำแหน่ง .... บทบาท' -> (position, role)"""
    line = norm(line)
    parts = re.split(r"\s{4,}", line)
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    ROLE_WORDS = r"(ประธานกรรมการ|รองประธานกรรมการ|กรรมการและเลขานุการ|กรรมการและผู้ช่วยเลขานุการ|กรรมการ|เลขานุการ|รองประธานกรรมการทำหน้าที่ประธาน)"
    m = re.search(ROLE_WORDS + r"$", line)
    if m:
        role = m.group(1)
        position = norm(line[:m.start()].rstrip(" ."))
        return position, role
    return line, ""  # เดาไม่ได้ก็คืนทั้งบรรทัดเป็น position

def clean_person_name(line: str):
    line = norm(line)
    return line.strip("()[]{}").strip()

def scrape_and_insert(url: str, organization: str, documentType: str = "มติ"):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    content_tag = soup.find("div", class_="itemFullText")
    if not content_tag:
        print(f"⚠️  Skip (no content): {url}")
        return

    # ---------- พาร์สส่วนหัวก่อน <hr> ----------
    title = ""
    meeting_no = ""
    meeting_seq = None
    meeting_date = ""
    meeting_no_full = ""
    location = ""

    pre_hr_paras = []
    for child in content_tag.children:
        if getattr(child, "name", None) == "hr":
            break
        if getattr(child, "name", None) == "p":
            txt = child.get_text(strip=True)
            if txt:
                pre_hr_paras.append(txt)

    if len(pre_hr_paras) >= 1:
        title = pre_hr_paras[0]
    if len(pre_hr_paras) >= 2:
        line = pre_hr_paras[1]
        meeting_no_full = line  # เช่น "ครั้งที่ 4/2567 (ครั้งที่ 170)"
        m_no = re.search(r"ครั้งที่\s*([0-9]{1,3})\s*/\s*([0-9]{4})", line)
        if m_no:
            meeting_no = f"{m_no.group(1)}/{m_no.group(2)}"
        m_seq = re.search(r"\(ครั้งที่\s*([0-9]+)\)", line)
        if m_seq:
            meeting_seq = int(m_seq.group(1))
    if len(pre_hr_paras) >= 3:
        meeting_date = pre_hr_paras[2]
    if len(pre_hr_paras) >= 4:
        location = pre_hr_paras[3]

    meeting_date_obj = parse_thai_date(meeting_date)

    # ---------- ผู้มาประชุม ----------
    attendees = []
    nodes = list(content_tag.find_all("p"))
    in_section = False
    buffer_lines = []
    for p in nodes:
        t = norm(p.get_text(" ", strip=True))
        if not t:
            continue
        if not in_section:
            if "ผู้มาประชุม" in t:
                in_section = True
            continue
        else:
            if re.match(r"^(เรื่องที่|วาระที่)\s*\d+", t) or re.fullmatch(r"มติ", t) or re.search(r"สรุป\s*สาระ\s*สำคัญ", t):
                break
            buffer_lines.append(t)

    i = 0
    while i < len(buffer_lines):
        pos_role_line = buffer_lines[i]
        name_line = buffer_lines[i+1] if i+1 < len(buffer_lines) else ""
        position, role = split_position_role(pos_role_line)
        person_name = clean_person_name(name_line)
        attendees.append({"position": position, "role": role, "name": person_name})
        i += 2

    # ---------- วาระ / สรุป / มติ ----------
    agendas = []
    current_agenda = None
    current_section = None

    for node in content_tag.find_all(["p", "li"]):
        text = norm(node.get_text(" ", strip=True))
        if not text:
            continue

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
            current_agenda = {"agenda": text, "summaries": [], "resolutions": []}
            current_section = None
            continue

        if re.match(r"^\s*สรุป\s*สาระ\s*สำคัญ\s*[:：]?\s*$", text):
            current_section = "summary"
            continue

        if re.match(r"^\s*(?:มติ(?:ของที่ประชุม)?|ที่ประชุมมีมติ)\s*[:：]?\s*$", text):
            current_section = "resolution"
            continue

        m_res_inline = re.match(r"^\s*(?:มติ(?:ของที่ประชุม)?|ที่ประชุมมีมติ)\s*[:：]?\s*(.+)$", text)
        if m_res_inline:
            if current_agenda:
                current_section = "resolution"
                current_agenda["resolutions"].append(m_res_inline.group(1).strip())
            continue

        if current_agenda:
            if current_section == "summary":
                current_agenda["summaries"].append(text)
            elif current_section == "resolution":
                current_agenda["resolutions"].append(text)
            else:
                pass

    if current_agenda:
        agendas.append(current_agenda)

    # ---------- สร้าง doc และบันทึก ----------
    # ป้องกันซ้ำ: ถ้า meeting_no_full นี้เคยเก็บแล้ว ข้าม (idempotent)
    if meetings_col.find_one({"meeting_no_full": meeting_no_full, "organization": organization}):
        print(f"Already exists, skip: {url}")
        return

    # meeting_ref = get_next_ref_for_org(organization)
    meeting_ref = get_next_ref()
    agenda_titles = [a.get("agenda", "").strip() for a in agendas if a.get("agenda")]

    agenda_string = ','.join(agenda_titles)

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
        "total_title": agenda_string
    }
    meetings_col.insert_one(meeting_doc)

    for person in attendees:
        attendees_col.insert_one({
            "meeting_ref": meeting_ref,
            "meeting_seq": meeting_seq,
            "position": person["position"],
            "role": person["role"],
            "name": person["name"]
        })

    for i, agenda in enumerate(agendas, start=1):
        agendas_col.insert_one({
            "meeting_ref": meeting_ref,
            "meeting_seq": meeting_seq,
            "agenda_no": i,
            "agenda_title": agenda["agenda"]
        })
        details_col.insert_one({
            "meeting_ref": meeting_ref,
            "meeting_seq": meeting_seq,
            "agenda_no": i,
            "summary": " ".join(agenda["summaries"]) if agenda["summaries"] else "",
            "resolution": " ".join(agenda["resolutions"]) if agenda["resolutions"] else ""
        })

    print(f"✅ Inserted: {url}")

for url in urls_CEPA:
    scrape_and_insert(url, ORGANIZATION, DOC_TYPE)
