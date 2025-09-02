import re
import os
from pymongo import MongoClient, ReturnDocument
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "DocxResolutionScraping"

INPUT_FILES = [
    r"ScrapingData/Data/InputData/ตัวอย่างมติกพช.docx",
]

org = "กพง"
ORGANIZATION = org + "."
DOC_TYPE = "มติ"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
meetings_col  = db["meetings"]
attendees_col = db["attendees"]
agendas_col   = db["agendas"]
details_col   = db["details"]

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

THAI2AR = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
THAI_MONTHS = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3,
    "เมษายน": 4, "พฤษภาคม": 5, "มิถุนายน": 6,
    "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9,
    "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12,
}
MONTHS_ALT = r"(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)"

def read_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == ".docx":
        if not HAS_DOCX:
            raise RuntimeError("ต้องติดตั้ง python-docx ก่อน (pip install python-docx)")
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError("รองรับเฉพาะ .txt และ .docx เท่านั้น")

def norm(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s.strip())

def parse_thai_date(date_str: str):
    s = norm(date_str).translate(THAI2AR)
    pat = re.compile(
        rf"(?:วัน[ก-๙]+(?:ที่)?)?\s*"
        rf"(?P<day>\d{{1,2}})\s+"
        rf"(?P<month>{MONTHS_ALT})\s+"
        rf"(?:(?:พ\.?\s*ศ\.?|พศ)\s*)?"
        rf"(?P<year>\d{{4}})"
        rf"(?:\s*(?:เวลา)?\s*(?P<hour>\d{{1,2}})[.:](?P<minute>\d{{2}}))?",
        re.IGNORECASE
    )
    m = pat.search(s)
    if not m:
        return None
    day = int(m.group("day"))
    month = THAI_MONTHS.get(m.group("month"))
    year = int(m.group("year"))
    if year >= 2400:  # พ.ศ. → ค.ศ.
        year -= 543
    hour = int(m.group("hour")) if m.group("hour") else 0
    minute = int(m.group("minute")) if m.group("minute") else 0
    return datetime(year, month, day, hour, minute)

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
    return line, ""

def scrape_from_file(file_path: str, organization: str, documentType: str = "มติ"):
    text = read_text_from_file(file_path)
    lines = [norm(l) for l in text.splitlines() if norm(l)]

    title = lines[0] if lines else ""
    meeting_no_full = ""
    meeting_seq = None
    meeting_date = ""
    location = ""

    for l in lines[:5]:
        if "ครั้งที่" in l:
            meeting_no_full = l
            m_seq = re.search(r"\(ครั้งที่\s*([0-9]+)\)", l)
            if m_seq:
                meeting_seq = int(m_seq.group(1))
        if any(m in l for m in THAI_MONTHS.keys()):
            meeting_date = l
        if "ณ" in l and "ห้อง" in l:
            location = l

    meeting_date_obj = parse_thai_date(meeting_date)

    attendees = []
    try:
        start_idx = next(i for i,l in enumerate(lines) if "ผู้มาประชุม" in l)
        end_idx = next(i for i,l in enumerate(lines) if re.match(r"^(เรื่องที่|วาระที่)", l))
        attendee_lines = lines[start_idx+1:end_idx]
        for i in range(0, len(attendee_lines), 2):
            pos = attendee_lines[i]
            name = attendee_lines[i+1] if i+1 < len(attendee_lines) else ""
            position, role = split_position_role(pos)
            attendees.append({
                "position": position,
                "role": role,
                "name": name
            })
    except StopIteration:
        pass

    agendas = []
    current_agenda = None
    current_section = None

    for l in lines:
        if re.match(r"^(เรื่องที่|วาระที่)\s*\d+", l):
            if current_agenda:
                agendas.append(current_agenda)
            current_agenda = {"agenda": l, "summaries": [], "resolutions": []}
            current_section = None
            continue

        if re.search(r"สรุป\s*สาระ\s*สำคัญ", l):
            current_section = "summary"
            continue

        if re.match(r"^(มติ|ที่ประชุมมีมติ)", l):
            current_section = "resolution"
            continue

        if current_agenda:
            if current_section == "summary":
                current_agenda["summaries"].append(l)
            elif current_section == "resolution":
                current_agenda["resolutions"].append(l)

    if current_agenda:
        agendas.append(current_agenda)


    if meetings_col.find_one({"meeting_no_full": meeting_no_full, "organization": organization}):
        print(f"Already exists, skip: {file_path}")
        return

    meeting_ref = db["counters"].find_one_and_update(
        {"_id": "meeting_ref"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )["seq"]

    meetings_col.insert_one({
        "title": title,
        "meeting_ref": meeting_ref,
        "meeting_no_full": meeting_no_full,
        "meeting_seq": meeting_seq,
        "meeting_date": meeting_date,
        "meeting_date_obj": meeting_date_obj,
        "organization": organization,
        "doc_type": documentType,
    })

    for person in attendees:
        attendees_col.insert_one({"meeting_ref": meeting_ref, **person})

    for i, agenda in enumerate(agendas, start=1):
        agendas_col.insert_one({
            "meeting_ref": meeting_ref,
            "agenda_no": i,
            "agenda_title": agenda["agenda"]
        })
        details_col.insert_one({
            "meeting_ref": meeting_ref,
            "agenda_no": i,
            "summary": " ".join(agenda["summaries"]),
            "resolution": " ".join(agenda["resolutions"])
        })
    print(f"✅ Inserted from file: {file_path}")

for file in INPUT_FILES:
    scrape_from_file(file, ORGANIZATION, DOC_TYPE)
