"""PDF -> {"source", "pages": [{"text", "tables", "words"}]}.

Matn qatlami bo'lsa PyMuPDF, bo'lmasa OpenCV + Tesseract. Boshqa OCR dvigatelga
almashtirish uchun faqat shu fayl o'zgaradi.
"""
import re

import cv2
import numpy as np
import pymupdf
import pytesseract

MIN_TEXT_CHARS = 50  # shundan kam bo'lsa sahifa skan hisoblanadi
DPI = 300
LANG = "uzb+eng" if "uzb" in pytesseract.get_languages() else "eng"

# Har sahifadagi test izohi: "Test uchun example — AI tizimini sinash uchun ... shartli."
FOOTER_RE = re.compile(r"example|AI tizimini|shartli", re.I)
PAGE_NUMBER_RE = re.compile(r"^\d{1,2}$")
QUOTES = str.maketrans({"‘": "'", "’": "'", "ʻ": "'", "ʼ": "'", "`": "'",
                        "“": '"', "”": '"', "«": '"', "»": '"'})


def clean_text(text: str) -> str:
    text = text.translate(QUOTES)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [l for l in lines if l and not FOOTER_RE.search(l) and not PAGE_NUMBER_RE.match(l)]
    return "\n".join(lines)


def read_pdf(path: str) -> dict:
    pages = []
    for page in pymupdf.open(path):
        if len(page.get_text().strip()) > MIN_TEXT_CHARS:
            pages.append(read_text_page(page))
        else:
            pages.append(read_scan_page(page))
    source = "text" if all(not p["words"] for p in pages) else "ocr"
    return {"source": source, "pages": pages}


def read_text_page(page) -> dict:
    found = page.find_tables().tables
    tables = [[[clean_text(c or "").replace("\n", " ") for c in row] for row in t.extract()] for t in found]
    # jadval ichidagi matn alohida chiqadi, shuning uchun abzats matnidan olib tashlaymiz
    blocks = []
    for x0, y0, x1, y1, block_text, *_ in page.get_text("blocks", sort=True):
        center = pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)
        if not any(center in pymupdf.Rect(t.bbox) for t in found):
            blocks.append(block_text)
    return {"text": clean_text("\n".join(blocks)), "tables": tables, "words": []}


def read_scan_page(page) -> dict:
    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
    gray = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    gray = deskew(cv2.medianBlur(gray, 3))  # median nuqtali shovqinni yo'qotadi
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    words = []
    tables = []
    rows = find_table_cells(bw)
    if rows:
        for row in rows:
            cells = []
            for x, y, w, h in row:
                text, cell_words = run_tesseract(bw[y + 5:y + h - 5, x + 5:x + w - 5], psm=6)
                cells.append(clean_text(text).replace("\n", " "))
                words += cell_words
            tables.append(cells)
        tables = [tables]
        # jadvaldan tashqari qismni alohida o'qiymiz
        x0 = min(c[0] for r in rows for c in r)
        y0 = min(c[1] for r in rows for c in r)
        x1 = max(c[0] + c[2] for r in rows for c in r)
        y1 = max(c[1] + c[3] for r in rows for c in r)
        bw = bw.copy()
        bw[y0 - 10:y1 + 10, x0 - 10:x1 + 10] = 255
    text, text_words = run_tesseract(bw, psm=4)
    words += text_words
    words = [(w.translate(QUOTES), conf) for w, conf in words]
    return {"text": clean_text(text), "tables": tables, "words": words}


def deskew(gray):
    # burchakni binar rasmdan topamiz, lekin burishni kulrang rasmda qilamiz: shunda ingichka chiziqlar uzilmaydi
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ink = cv2.resize(255 - bw, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    h, w = ink.shape

    def score(angle):
        rotated = cv2.warpAffine(ink, cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1), (w, h))
        return np.var(rotated.sum(axis=1))

    coarse = max(np.arange(-4, 4.01, 0.25), key=score)
    best = max(np.arange(coarse - 0.25, coarse + 0.26, 0.05), key=score)
    h, w = gray.shape
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), best, 1)
    return cv2.warpAffine(gray, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)


def find_table_cells(bw):
    """Jadval chiziqlaridan kataklar topadi. Qaytaradi: qatorlar ro'yxati, har qator [(x, y, w, h), ...]."""
    ink = 255 - bw
    h, w = ink.shape
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (w // 25, 1)))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 40)))
    grid = cv2.dilate(horizontal | vertical, np.ones((3, 3), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(255 - grid)

    cells = []
    for x, y, cw, ch, _ in stats[1:]:
        touches_border = x == 0 or y == 0 or x + cw >= w or y + ch >= h
        if cw > 40 and ch > 30 and not touches_border:
            cells.append((x, y, cw, ch))
    cells.sort(key=lambda c: (c[1], c[0]))

    rows = []
    for cell in cells:
        if rows and abs(cell[1] - rows[-1][0][1]) < 15:  # bir xil y = bir qator
            rows[-1].append(cell)
        else:
            rows.append([cell])
    rows = [sorted(r) for r in rows]
    if len(rows) < 2 or max(len(r) for r in rows) < 2:
        return []
    return rows


def run_tesseract(img, psm: int):
    img = cv2.copyMakeBorder(img, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    data = pytesseract.image_to_data(img, lang=LANG, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    lines = {}
    words = []
    for i, word in enumerate(data["text"]):
        conf = float(data["conf"][i])
        if not word.strip() or conf < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        words.append((word, conf))
    return "\n".join(" ".join(ws) for ws in lines.values()), words
