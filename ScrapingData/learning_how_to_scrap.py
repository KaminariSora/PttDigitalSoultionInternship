import requests
from bs4 import BeautifulSoup
import re 

url = "https://www.eppo.go.th/index.php/th/component/k2/item/10911-cepa-prayut16"
response = requests.get(url)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

content_tag = soup.find("div", class_="itemFullText")

title, meeting_no, meeting_seq, meeting_date = "", "", "", ""
MONTHS_ALT = r"(?:มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)"


if content_tag:
    center_paragraphs = content_tag.find_all("p", style=lambda v: v and "text-align: center" in v)
    texts = [p.get_text(strip=True) for p in center_paragraphs if p.get_text(strip=True)]

    print(texts[0])

    m = re.search(r"ครั้งที่\s*(\d+)\s*/\s*(\d{4})\s*\(\s*ครั้งที่\s*(\d+)\s*\)", texts[0])
    # day = re.search()
    month = re.search(rf"(?P<month>{MONTHS_ALT})\s+", texts[0])
    if m:
        meeting_no = f"{m.group(1)}/{m.group(2)}"
        meeting_seq = m.group(3)
        print(meeting_no)
        print(meeting_seq)
    if month:
        meeting_date = month.group(1)
        print(meeting_date)