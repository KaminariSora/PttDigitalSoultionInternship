import re
import os
from typing import List, Tuple, Optional

# ถ้าจะรองรับ .docx ให้ติดตั้งก่อน: pip install python-docx
try:
    from docx import Document
    HAS_DOCX = True
except Exception:
    HAS_DOCX = False

# -------------------------
# Utils
# -------------------------
THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

def normalize_digits(s: str) -> str:
    return s.translate(THAI_DIGITS)

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

# -------------------------
# Extraction with Regex
# -------------------------
# 1) Title: โดยทั่วไปจะอยู่บรรทัดแรกที่ไม่ว่าง หรือบรรทัดที่มีคำว่า "เรื่องที่" ก่อนหน้า
#    ถ้ามีหัวบน ๆ หลายบรรทัด ให้ใช้บรรทัดแรก ๆ เป็น Title
def extract_title(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[0] if lines else ""

# 2) Meeting No / Seq: หา "(ครั้งที่ 71)" หรือรูปแบบใกล้เคียง
MEETING_SEQ_RE = re.compile(r"\(ครั้งที่\s*([0-9๐-๙]+)\)")
def extract_meeting_no_and_seq(text: str) -> Tuple[str, str]:
    # ลองหาแถวที่มีคำว่า "ครั้งที่"
    meeting_no_line = ""
    for line in text.splitlines():
        if "ครั้งที่" in line:
            meeting_no_line = line.strip()
            break
    seq = ""
    if meeting_no_line:
        m = MEETING_SEQ_RE.search(meeting_no_line)
        if m:
            seq = normalize_digits(m.group(1))
    return meeting_no_line, seq

# 3) Meeting Date: รูปแบบตัวอย่าง "วันพฤหัสบดีที่ 27 มีนาคม 2568"
MONTHS = "มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม"
DATE_RE = re.compile(
    rf"วัน[^\n]*?(\d{{1,2}}|[๐-๙]{{1,2}})\s*({MONTHS})\s*(\d{{4}}|[๐-๙]{{4}})",
    flags=re.MULTILINE
)
def extract_meeting_date(text: str) -> str:
    m = DATE_RE.search(text)
    if not m:
        return ""
    day = normalize_digits(m.group(1))
    month = m.group(2)
    year = normalize_digits(m.group(3))
    # ไม่แปลง พ.ศ. -> ค.ศ. ที่นี่ เก็บดิบไว้ก่อน
    return f"{day} {month} {year}"

# 4) แยก Agenda / มติ / สรุปสาระสำคัญ
#    สมมุติรูปแบบหัวข้อ agenda พบได้จากคำว่า "เรื่องที่", "ระเบียบวาระที่", "วาระที่", หรือ "เรื่องที่ 1"
AGENDA_HEADER_RE = re.compile(
    r"^(?:เรื่องที่|ระเบียบวาระที่|วาระที่)\s*([0-9๐-๙]+)[\.\)]?\s*(.*)$",
    flags=re.MULTILINE
)

# จับหัว section "มติ" และ "สรุปสาระสำคัญ" (ขึ้นต้นบรรทัด, มีหรือไม่มีเครื่องหมาย : ก็ได้)
RESOLUTION_HEAD_RE = re.compile(r"^\s*มติ\s*:?\s*$", flags=re.MULTILINE)
SUMMARY_HEAD_RE    = re.compile(r"^\s*สรุปสาระสำคัญ\s*:?\s*$", flags=re.MULTILINE)

def split_by_agenda(text: str) -> List[Tuple[str, str]]:
    """
    คืนค่าเป็น [(agenda_title, agenda_block_text), ...]
    โดย agenda_title คือ string เช่น 'เรื่องที่ 1 ...'
    """
    blocks = []
    matches = list(AGENDA_HEADER_RE.finditer(text))
    if not matches:
        # ถ้าไม่เจอหัว agenda เลย ถือว่าทั้งเอกสารเป็นบล็อกเดียว (ไม่มีหัวเรื่อง)
        return [("", text)]
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i + 1 < len(matches) else len(text)
        num = normalize_digits(m.group(1))
        tail = m.group(2).strip()
        agenda_title = f"เรื่องที่ {num}" + (f" {tail}" if tail else "")
        blocks.append((agenda_title, text[start:end]))
    return blocks

def extract_resolution_and_summary(block_text: str) -> Tuple[str, List[str]]:
    """
    จากบล็อกของ agenda หนึ่งอัน: ดึง 'มติ' (string เดียว) และ 'สรุปสาระสำคัญ' (list ของข้อความ)
    กติกา:
      - เนื้อหาก่อน 'มติ' หากเป็นคำอธิบายหลังหัวข้อ จะนับรวมเข้า 'มติ' ด้วย (เหมือนเดิมในโค้ด HTML)
      - 'สรุปสาระสำคัญ' อาจมีหลายย่อหน้า แยกเป็น list ตามบรรทัด/ย่อหน้า
    """
    # หาตำแหน่งหัว "มติ" และ "สรุปสาระสำคัญ"
    res_pos = [m.start() for m in RESOLUTION_HEAD_RE.finditer(block_text)]
    sum_pos = [m.start() for m in SUMMARY_HEAD_RE.finditer(block_text)]

    # กรณีไม่มี "มติ" เลย: คืนว่าง ๆ
    if not res_pos:
        # แต่ถ้ามี "สรุปสาระสำคัญ" ก็ยังดึงส่วนสรุปออกมาได้
        summaries = []
        if sum_pos:
            start = sum_pos[0]
            end = sum_pos[1] if len(sum_pos) > 1 else len(block_text)
            summary_text = block_text[start:end]
            summaries = clean_summary(summary_text)
        return "", summaries

    # มี "มติ" อย่างน้อยหนึ่ง
    first_res = res_pos[0]
    # หา "สรุป..." ที่ตามหลัง "มติ"
    first_sum_after_res = None
    for pos in sum_pos:
        if pos > first_res:
            first_sum_after_res = pos
            break

    # เนื้อหา "มติ": จากบรรทัดหลังหัว "มติ" ไปจนก่อน "สรุป..." หรือจบ
    # ก่อน "มติ" (คำอธิบายของหัวข้อ) ให้รวมเข้า "มติ" ด้วย (เหมือนเวิร์กโฟลว์เดิม)
    # ตัดหัวคำว่า "มติ" ออก
    # หาเส้นเขตหัว "มติ" ทั้งบรรทัด แล้วดึงส่วนถัดไป
    res_head_line = RESOLUTION_HEAD_RE.search(block_text)
    if res_head_line:
        res_content_start = res_head_line.end()
    else:
        res_content_start = first_res

    res_content_end = first_sum_after_res if first_sum_after_res is not None else len(block_text)

    # รวมเนื้อหาตั้งแต่หลังหัว "มติ" + คำอธิบายก่อนหน้าเล็กน้อย (หากอยากตัดก่อนหัว "มติ" ออก ให้คงตามนี้)
    resolution_text = block_text[res_content_start:res_content_end].strip()

    # "สรุปสาระสำคัญ"
    summaries: List[str] = []
    if first_sum_after_res is not None:
        # ตัดเอาตั้งแต่หัว "สรุปสาระสำคัญ" ตัวแรกจนก่อนหัว "สรุป..." ถัดไป (ถ้ามี)
        start = first_sum_after_res
        end = None
        # ถ้ามีหัวสรุปหลายจุด ให้ไปทีละช่วง
        sum_matches = list(SUMMARY_HEAD_RE.finditer(block_text[first_sum_after_res:]))
        if len(sum_matches) >= 2:
            # ถ้ามี 2 หัวขึ้นไป ใช้ช่วงแรก
            end = first_sum_after_res + sum_matches[1].start()
        if end is None:
            end = len(block_text)
        summary_text = block_text[start:end]
        summaries = clean_summary(summary_text)

    return resolution_text, summaries

def clean_summary(summary_block: str) -> List[str]:
    """
    ลบหัวคำว่า 'สรุปสาระสำคัญ' และแยกเป็นย่อหน้าสั้น ๆ
    """
    # ตัดหัว
    summary_block = re.sub(r"^\s*สรุปสาระสำคัญ\s*:?\s*", "", summary_block, flags=re.MULTILINE).strip()
    # แบ่งตามย่อหน้า/บรรทัดยาว
    parts = [p.strip() for p in re.split(r"\n{2,}|\r\n{2,}", summary_block) if p.strip()]
    # ถ้าน้อยไป ให้แตกตามบรรทัด
    if len(parts) <= 1:
        parts = [l.strip() for l in summary_block.splitlines() if l.strip()]
    return parts

# -------------------------
# Main runner
# -------------------------
def parse_meeting_from_file(input_path: str, output_path: str = "ScrapingData/Data/output.txt"):
    text_raw = read_text_from_file(input_path)
    text = text_raw.strip()

    title = extract_title(text)
    meeting_no, meeting_seq = extract_meeting_no_and_seq(text)
    meeting_date = extract_meeting_date(text)

    # แยกเป็นบล็อกตามหัวข้อ (Agenda)
    agenda_blocks = split_by_agenda(text)

    agendas: List[str] = []
    resolutions: List[str] = []
    summaries_all: List[str] = []

    for agenda_title, block in agenda_blocks:
        if agenda_title:
            agendas.append(agenda_title)
        res_text, summary_list = extract_resolution_and_summary(block)
        if res_text:
            resolutions.append(res_text)
        summaries_all.extend(summary_list)

    # แสดงผลบนจอ
    print("Title:", title)
    print("Meeting No (Raw):", meeting_no)
    print("Meeting Seq (Extracted):", meeting_seq)
    print("Date:", meeting_date)

    print("\nAgendas / หัวเรื่อง:")
    for a in agendas:
        print("-", a)

    print("\nSummary / สรุปสาระสำคัญ:")
    for s in summaries_all:
        print("-", s)

    print("\nResolutions / มติการประชุม:")
    for r in resolutions:
        print("-", (r[:300] + ("..." if len(r) > 300 else "")))

    # เขียนไฟล์ผลลัพธ์
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Agendas / หัวเรื่อง:\n")
        f.write(f"Title: {title}\n")
        f.write(f"Meeting No (Raw): {meeting_no}\n")
        f.write(f"Meeting Seq (Extracted): {meeting_seq}\n")
        f.write(f"Date: {meeting_date}\n\n")
        for a in agendas:
            f.write(a + "\n")

        f.write("\nResolutions / มติการประชุม:\n")
        for r in resolutions:
            f.write(r.strip() + "\n\n")

        f.write("\nSummary / สรุปสาระสำคัญ:\n")
        for s in summaries_all:
            f.write(s.strip() + "\n")

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    # ปรับ path ให้ตรงไฟล์ของคุณ
    input_file = r"ScrapingData/Data/InputData/ตัวอย่างมติกพช.docx"
    output_file = r"ScrapingData/Data/RawOutput_txt/ตัวอย่างมติกพช_output.txt"
    parse_meeting_from_file(input_file, output_file)
