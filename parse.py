"""OCR natijasidan (ocr.read_pdf) rekvizitlar va topshiriqlarni ajratadi. Faqat qoidalar, LLM yo'q."""
import calendar
import os
import re
from datetime import date, timedelta

CONF_THRESHOLD = 70  # undan past ishonchli so'zli maydon "tekshiring" deb belgilanadi

MONTHS = {m: i for i, m in enumerate(
    "yanvar fevral mart aprel may iyun iyul avgust sentabr oktabr noyabr dekabr".split(), 1)}
MONTH_RE = "|".join(MONTHS)
NUMBER_WORDS = {"bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "besh": 5, "olti": 6, "yetti": 7,
                "sakkiz": 8, "to'qqiz": 9, "o'n": 10, "yigirma": 20, "o'ttiz": 30}
NUMBER_RE = r"(?:\d+|" + "|".join(NUMBER_WORDS) + ")"

# Tashkiliy birlik so'zlari: ijrochi shu so'zgacha bo'lgan ot birikmasi
UNIT_WORDS = {"boshqarmasi", "departamenti", "bo'limi", "bo'linmasi", "bo'linmalar", "laboratoriyasi",
              "kotibiyati", "xizmati", "guruhi", "koordinatori", "markaz"}

# "№" ni OCR "Ne", "No" yoki kirill "Ме" qilib o'qiydi
NO = r"(?:№|[NМ][eoео]\b)"
RESOLUTION_TITLE_RE = re.compile(r"Q\s*A\s*R\s*O\s*R\s*I")                    # "Q A R O R I"
DOC_DATE_RE = re.compile(rf"(\d{{4}})-yil\s+(\d{{1,2}})-({MONTH_RE})")          # "2026-yil 10-fevral"
RESOLUTION_NUMBER_RE = re.compile(rf"{NO}\s*(\d+)")                            # "№ 121"
LETTER_NUMBER_RE = re.compile(rf"(\d{{2}}\.\d{{2}}\.\d{{4}})\s*{NO}\s*(\d[\d/-]*\d)")  # "08.09.2026 № 03-12/1456"
XATGA_RE = re.compile(r"\"?[_\s\"—-]*dagi\s*\"?[_\s\"—-]*-?\s*son\s+\w+")      # "«___» ___ dagi ___-son xatga"
ADDRESS_RE = re.compile(r"\d{6}|Tel\.|E-mail")                                # "100011, Toshkent shahri, ..."
SIGNATURE_RE = re.compile(r"^(?P<position>.*?)\s*(?P<name>(?:[A-Z][a-z]?\.\s?){1,2}[A-Z][\w']+)$")  # "Kengash raisi M. Tursunov"
PREPARED_BY_RE = re.compile(r"Ijrochi:\s*(.+)")                               # "Ijrochi: N. Sobirova"
ILOVA_RE = re.compile(r"\b[IT]LOVA\b")                                        # ilova sarlavhasi (OCR: I -> T)

ITEM_RE = re.compile(r"^(\d{1,2})\.\s+(.*)")                                  # "3. Axborot ... tayyorlasin."
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.:!])\s+")
COMMAND_RE = re.compile(r"(?:sin|sinlar|so'raymiz|so'raladi)\.?$")             # "... taqdim etsin."
# Topshiriq emas: nazorat, tasdiqlash, umumiy chaqiriq, jadvalga kirish, standart muddat qoidasi
NOT_A_TASK_RE = re.compile(
    r"nazorat qilish|tasdiqlansin|ijro etilishi ta'minlansin|quyidagi|muddati alohida ko'rsatilmagan|:$", re.I)
DEFAULT_RULE_RE = re.compile(r"muddati alohida ko'rsatilmagan topshiriqlar (.+?) ijro etilsin")
CO_EXECUTOR_RE = re.compile(r"(.+?)\s+bilan\s+birgalikda\b")                  # "X boshqarmasi Y departamenti bilan birgalikda"

# Tartib muhim: conditional "2 oy ichida" ni relative'dan, start sanani date'dan oldin ushlashi kerak
DEADLINE_PATTERNS = [
    ("conditional", rf"(?:\S+\s+){{1,3}}\S*gandan\s+so'ng\s+{NUMBER_RE}\s+(?:kun|oy|hafta)\s+ichida"),  # "prototip tayyor bo'lgandan so'ng 15 kun ichida"
    ("start", rf"\d{{4}}-yil\s+\d{{1,2}}-(?:{MONTH_RE})\w*dan\s+boshlab"),                              # "2026-yil 15-martdan boshlab"
    ("periodic", r"har\s+(?:(?:oy|hafta|yil)ning\s+(?:\d+-sana\w*(?:\s+qadar)?|\w+\s+kuni)"
                 r"|chorak\s+yakunidan\s+keyingi\s+oyning\s+\d+-sana\w*(?:\s+qadar)?|(?:oy|chorak|hafta|yil)da)"),  # "har oyning 5-sanasiga qadar"
    ("permanent", r"\bdoimiy\b"),
    ("date", rf"\d{{4}}-yil\s+\d{{1,2}}-(?:{MONTH_RE})\w*(?:\s+(?:qadar|gacha))?"),                     # "2026-yil 1-iyulga qadar"
    ("date", r"\d{2}\.\d{2}\.\d{4}(?:\s*yil\w*)?"),                                                    # "01.10.2026 yilgacha"
    ("relative", rf"{NUMBER_RE}\s+(?:ish\s+kuni|kun|hafta|oy)\s+(?:muddatda|ichida)"),                 # "uch ish kuni ichida"
]
DEADLINE_PATTERNS = [(kind, re.compile(p)) for kind, p in DEADLINE_PATTERNS]


def to_date(raw: str):
    try:
        if m := DOC_DATE_RE.search(raw):
            return date(int(m[1]), MONTHS[m[3]], int(m[2]))
        if m := re.search(r"(\d{2})\.(\d{2})\.(\d{4})", raw):
            return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:  # OCR sanani buzgan bo'lishi mumkin (masalan, 32-mart)
        return None
    return None


def add_relative(raw: str, start: date):
    m = re.match(rf"({NUMBER_RE})\s+(ish\s+kuni|kun|hafta|oy)", raw)
    n = int(m[1]) if m[1].isdigit() else NUMBER_WORDS[m[1]]
    unit = re.sub(r"\s+", " ", m[2])
    if unit == "oy":
        month = start.month - 1 + n
        year, month = start.year + month // 12, month % 12 + 1
        return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
    if unit == "ish kuni":  # bayramlar hisobga olinmaydi
        result = start
        while n:
            result += timedelta(days=1)
            n -= result.weekday() < 5
        return result
    return start + timedelta(days=n * (7 if unit == "hafta" else 1))


def find_deadline(text: str, doc_date) -> dict:
    for kind, pattern in DEADLINE_PATTERNS:
        if m := pattern.search(text):
            raw = m.group(0)
            if kind == "date":
                value = to_date(raw)
            elif kind == "relative" and doc_date:
                value = add_relative(raw, doc_date)
            else:
                value = None
            return {"raw": raw, "type": kind, "date": value.isoformat() if value else None,
                    "computed": kind == "relative" and value is not None}
    return {"raw": "", "type": "none", "date": None, "computed": False}


def find_executors(sentence: str):
    words = sentence.split()
    for i, word in enumerate(words[:6]):
        if word.lower().strip(",") in UNIT_WORDS:
            executor = re.sub(r"^\S+ning\s+", "", " ".join(words[:i + 1]))  # "Markazning Tizim tahlili bo'limi"
            co = CO_EXECUTOR_RE.match(" ".join(words[i + 1:]))
            return executor, [co[1]] if co and len(co[1].split()) <= 6 else []
    return None, []


def split_items(lines: list[str]):
    """Raqamli bandlarni [raqam, matn] ko'rinishida va band oldidagi matnni qaytaradi."""
    preamble, items = [], []
    for line in lines:
        m = ITEM_RE.match(line)
        if m and int(m[1]) == len(items) + 1:
            items.append([m[1], m[2]])
        elif items:
            items[-1][1] += " " + line
        else:
            preamble.append(line)
    return " ".join(preamble), items


def find_signature(lines: list[str]):
    found = None
    for i, line in enumerate(lines):
        m = SIGNATURE_RE.match(line)
        if m and not line.startswith("Ijrochi"):
            # matnli PDF'da lavozim va ism alohida qatorda bo'ladi
            found = (i, m["position"], m["name"]) if m["position"] else (i - 1, lines[i - 1], m["name"])
    return found


def is_upper(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) >= 0.6 * len(letters)


def parse_requisites(lines: list[str], text: str, doc_type: str) -> dict:
    req = {"sender": None, "number": None, "date": None, "date_raw": None, "signer_position": None,
           "signer_name": None, "recipient": None, "prepared_by": None}
    if doc_type == "qaror":
        title = next(i for i, l in enumerate(lines) if RESOLUTION_TITLE_RE.search(l))
        req["sender"] = " ".join(l for l in lines[:title] if is_upper(l))
        if m := DOC_DATE_RE.search(text):
            req["date_raw"], req["date"] = m[0], to_date(m[0])
        if m := RESOLUTION_NUMBER_RE.search(text):
            req["number"] = m[1]
    else:
        stop = next((i for i, l in enumerate(lines) if ADDRESS_RE.search(l) or LETTER_NUMBER_RE.search(l)), 0)
        req["sender"] = " ".join(l for l in lines[:stop] if is_upper(l))
        for i, line in enumerate(lines):
            if m := LETTER_NUMBER_RE.search(line):
                req["date_raw"], req["date"], req["number"] = m[1], to_date(m[1]), m[2]
                # qabul qiluvchi shu qatorning o'ngida va keyingi qatorlarda, "...ga" bilan tugaydi
                rest = XATGA_RE.sub(" ", " ".join([line[m.end():]] + lines[i + 1:i + 6])).split()
                end = next((j for j, w in enumerate(rest) if w.endswith("ga")), None)
                req["recipient"] = " ".join(rest[:end + 1]) if end is not None else None
                break
        if m := PREPARED_BY_RE.search(text):
            req["prepared_by"] = m[1].strip()
    if sign := find_signature(lines):
        req["signer_position"], req["signer_name"] = sign[1], sign[2]
    if req["date"]:
        req["date"] = req["date"].isoformat()
    return req


def low_fields(fields: dict, word_conf: dict) -> list[str]:
    """Qiymatidagi so'zlardan birortasi ishonchi past bo'lsa, maydon nomini qaytaradi."""
    low = []
    for name, value in fields.items():
        confs = [word_conf[w] for w in clean_words(value or "") if w in word_conf]
        if confs and min(confs) < CONF_THRESHOLD:
            low.append(name)
    return low


def clean_words(value: str) -> list[str]:
    # apostrofli so'zlarni Tesseract to'g'ri o'qiganda ham past ball bilan baholaydi, shuning uchun ularni hisobga olmaymiz
    words = [w.strip(".,;:!?()\"") for w in value.split()]
    return [w for w in words if len(w) > 2 and "'" not in w]


def make_task(n, text, executor, co_executors, deadline, location, word_conf) -> dict:
    low = low_fields({"text": text, "executor": executor, "deadline": deadline["raw"]}, word_conf)
    return {"n": n, "text": text, "executor": executor, "co_executors": co_executors,
            "deadline_raw": deadline["raw"], "deadline_type": deadline["type"],
            "deadline_date": deadline["date"], "computed": deadline["computed"],
            "deadline_source": "explicit" if deadline["type"] not in ("none", "start") else "none",
            "location": location, "low_confidence": bool(low), "low_fields": low}


def parse_document(doc: dict, path: str) -> dict:
    pages = doc["pages"]
    lines = pages[0]["text"].splitlines()
    text = "\n".join(lines)
    doc_type = "qaror" if RESOLUTION_TITLE_RE.search(text) else "xat"
    req = parse_requisites(lines, text, doc_type)
    doc_date = date.fromisoformat(req["date"]) if req["date"] else None

    word_conf = {}
    for page in pages:
        for word, conf in page["words"]:
            for w in clean_words(word):
                word_conf[w] = min(conf, word_conf.get(w, 100))
    req["low_confidence"] = low_fields({k: v for k, v in req.items() if isinstance(v, str)}, word_conf)

    sign = find_signature(lines)
    body = lines[:sign[0]] if sign else lines
    for page in pages[1:]:
        body += page["text"].splitlines()
    preamble, items = split_items(body)

    recipient_short = None
    if req["recipient"]:
        recipient_short = re.sub(r"i?ga$", "", req["recipient"].split()[-1]).capitalize()  # "markaziga" -> "Markaz"

    sentences = [(None, s) for s in SENTENCE_SPLIT_RE.split(preamble)]
    for n, item in items:
        first, *rest = SENTENCE_SPLIT_RE.split(item)
        sentences += [(n, first)] + [(None, s) for s in rest]  # band ichidagi qo'shimcha gaplar raqamsiz topshiriq

    default_deadline = None
    tasks = []
    for n, sentence in sentences:
        if m := DEFAULT_RULE_RE.search(sentence):
            default_deadline = find_deadline(m[1], doc_date)
        if NOT_A_TASK_RE.search(sentence) or (n is None and not COMMAND_RE.search(sentence)):
            continue
        executor, co_executors = find_executors(sentence)
        if executor is None and doc_type == "xat":
            executor = recipient_short  # ijrochi yozilmagan: xat qabul qiluvchiga
        tasks.append(make_task(n, sentence, executor, co_executors, find_deadline(sentence, doc_date),
                               "paragraph", word_conf))

    for page in pages:
        location = "appendix" if ILOVA_RE.search(page["text"]) else "table"
        for table in page["tables"]:
            for i, row in enumerate(table[1:], 1):  # birinchi qator sarlavha
                if len(row) < 3:
                    continue
                executors = [e.strip() for e in row[2].split(",")]  # "A, B": ikkalasi ijrochi
                deadline = find_deadline(row[-1], doc_date)
                deadline["raw"] = row[-1]
                if deadline["type"] == "none" and row[-1]:
                    deadline["type"] = "unknown"
                tasks.append(make_task(re.sub(r"\D", "", row[0]) or str(i), row[1], executors[0],
                                       executors[1:], deadline, location, word_conf))

    if default_deadline:
        for task in tasks:
            if task["deadline_type"] == "none":
                task.update(deadline_raw=default_deadline["raw"], deadline_type=default_deadline["type"],
                            deadline_date=default_deadline["date"], computed=default_deadline["computed"],
                            deadline_source="default_rule")
    return {"file": os.path.basename(path), "source": doc["source"], "doc_type": doc_type,
            "requisites": req, "tasks": tasks}
