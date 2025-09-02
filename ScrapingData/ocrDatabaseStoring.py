import re
import json
from typing import List, Tuple
from pymongo import MongoClient, ReturnDocument
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "OCR_ResolutionScraping"

INPUT_FILES = [
    r"ScrapingData/Data/InputData/raw_OCR_output.json",
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
    s = s.replace("\u200b", "")
    return re.sub(r"[ \t]+", " ", s.strip())

def parse_thai_date(date_str: str):
    """รับ 'วันพุธที่ 25 ธันวาคม 2567' หรือ '25 ธันวาคม 2567' เป็นต้น → datetime"""
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
    if year >= 2400:
        year -= 543
    hour = int(m.group("hour")) if m.group("hour") else 0
    minute = int(m.group("minute")) if m.group("minute") else 0
    try:
        return datetime(year, month, day, hour, minute)
    except Exception:
        return None
    
def split_position_role(line: str) -> Tuple[str, str]:
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

def load_markdown_from_ocr_json(path: str) -> str:
    """รองรับ JSON เป็น list หรือ object เดียว รวม markdown ของทุก page ต่อกัน"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "pages" in item:
                for p in item["pages"]:
                    md = p.get("markdown", "")
                    if md:
                        pages.append(md)
    elif isinstance(data, dict) and "pages" in data:
        for p in data["pages"]:
            md = p.get("markdown", "")
            if md:
                pages.append(md)
    else:
        if isinstance(data, str):
            pages.append(data)

    combined = "\n".join(pages)
    return combined

def strip_inline_math(s: str) -> str:
    return re.sub(r"\$(.*?)\$", r"\1", s)

def parse_header_fields(text: str):
    """
    ดึง Title / ครั้งที่ / เลขครั้งที่ในวงเล็บ / วันที่ (บรรทัดต้น ๆ)
    """
    lines = [norm(l) for l in text.splitlines() if norm(l)]
    title = ""
    meeting_no_full = ""
    meeting_seq = None
    meeting_date = ""

    if lines:
        title = lines[0]

    for l in lines[:10]:
        if "ครั้งที่" in l:
            clean_l = strip_inline_math(l)
            meeting_no_full = clean_l
            m_seq = re.search(r"\(ครั้งที่\s*([0-9]+)\)", l)
            if m_seq:
                meeting_seq = int(m_seq.group(1))
            break

    for l in lines[:15]:
        if re.search(MONTHS_ALT, l):
            meeting_date = l
            break

    meeting_date_obj = parse_thai_date(meeting_date)
    return title, meeting_no_full, meeting_seq, meeting_date, meeting_date_obj

def parse_agendas(text: str, meeting_ref: int) -> List[dict]:
    """
    ดึง agenda จากข้อความที่แปลงเป็นบรรทัดแล้ว
    """
    agendas: List[dict] = []
    lines = [norm(l) for l in text.splitlines() if norm(l)]

    for l in lines:
        matching = re.match(r"^(?:เรื่องที่|วาระที่)\s*([0-9๐-๙]+)\s*(.*)$", l)
        if matching:
            no = int(norm(matching.group(1)).translate(THAI2AR))
            title = norm(matching.group(2))
            agendas.append({
                "meeting_ref": meeting_ref,
                "agenda_no": no,
                "agenda_title": f"เรื่องที่ {no} {title}".strip()
            })
            continue

    return agendas

def parse_details(text: str, meeting_ref: int) -> list[dict]:
    """
    ใช้ regex จับเฉพาะเนื้อหา หลังจาก 'สรุปสาระสำคัญ' และ 'มติของที่ประชุม'
    โดยไม่เอาหัวข้อกลับมา
    """
    details = []

    patt_summary = re.compile(
        r"(?:สรุป\s*สาระ\s*สำคัญ)([\s\S]*?)(?=(?:มติของที่ประชุม|มติ|เรื่องที่\s*\d+|วาระที่\s*\d+|$))"
    )

    patt_resolution = re.compile(
        r"(?:มติของที่ประชุม|มติ|ที่ประชุมมีมติ)([\s\S]*?)(?=(?:เรื่องที่\s*\d+|วาระที่\s*\d+|$))"
    )

    summaries = [s.strip() for s in patt_summary.findall(text)]
    resolutions = [r.strip() for r in patt_resolution.findall(text)]

    max_len = max(len(summaries), len(resolutions))
    for i in range(max_len):
        details.append({
            "meeting_ref": meeting_ref,
            "agenda_no": i+1,
            "summary": summaries[i] if i < len(summaries) else "",
            "resolution": resolutions[i] if i < len(resolutions) else "",
        })

    return details

def parse_attendees(text: str, meeting_ref: int) -> List[dict]:
    lines = [l for l in (l.strip() for l in text.splitlines())]
    attendees: List[dict] = []

    try:
        start = next(i for i, l in enumerate(lines) if re.search(r"ผู้มาประชุม", l))
    except StopIteration:
        return attendees

    end = len(lines)
    for i in range(start + 1, len(lines)):
        l = lines[i]
        if re.match(r"^\d+\s*[.)]\s+", l) or re.match(r"^(เรื่องที่|วาระที่)\s*\d+", l):
            end = i
            break

    i = start + 1
    while i < end:
        line = norm(lines[i])
        if not line:
            i += 1
            continue

        name = ""
        if i + 1 < end:
            nm = re.match(r"^\((.+?)\)\s*$", lines[i+1].strip())
            if nm:
                name = norm(nm.group(1))
                jump = 2
            else:
                jump = 1
        else:
            jump = 1

        position, role = split_position_role(line)
        attendees.append({
            "meeting_ref": meeting_ref,
            "position": position,
            "role": role,
            "name": name
        })
        i += jump

    return attendees

def get_next_ref() -> int:
    ret = db["counters"].find_one_and_update(
        {"_id": "meeting_ref"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return ret["seq"]

def process_ocr_json_file(path: str, organization: str, documentType: str = "มติ"):
    md = load_markdown_from_ocr_json(path)
    title, meeting_no_full, meeting_seq, meeting_date, meeting_date_obj = parse_header_fields(md)

    if meeting_no_full:
        existed = meetings_col.find_one({"organization": organization, "meeting_no_full": meeting_no_full})
        if existed:
            meeting_ref = existed["meeting_ref"]
        else:
            meeting_ref = get_next_ref()
    else:
        meeting_ref = get_next_ref()

    meetings_col.insert_one(
        {
            "title": title,
            "meeting_ref": meeting_ref,
            "meeting_no_full": meeting_no_full,
            "meeting_seq": meeting_seq,
            "meeting_date": meeting_date,
            "meeting_date_obj": meeting_date_obj,
            "organization": organization,
            "doc_type": documentType
        },
    )

    agendas = parse_agendas(md, meeting_ref)
    if agendas:
        agendas_col.delete_many({"meeting_ref": meeting_ref})
        agendas_col.insert_many(agendas)

    details = parse_details(md, meeting_ref)
    if details:
        details_col.delete_many({"meeting_ref": meeting_ref})
        details_col.insert_many(details)

    attendees = parse_attendees(md, meeting_ref)
    if attendees:
        attendees_col.delete_many({"meeting_ref": meeting_ref})
        attendees_col.insert_many(attendees)
    
if __name__ == "__main__":
    for fp in INPUT_FILES:
        process_ocr_json_file(fp, ORGANIZATION, DOC_TYPE)