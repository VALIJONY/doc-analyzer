import base64
import os
import tempfile

import pymupdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

import ocr
import parse

MAX_SIZE = 20 * 1024 * 1024
MAX_PREVIEW_PAGES = 10

app = FastAPI(title="Hujjat tahlili")


@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), encoding="utf-8") as f:
        return f.read()


def read_pdf_upload(file: UploadFile) -> bytes:
    content = file.file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "Fayl 20 MB dan katta")
    if not content.startswith(b"%PDF"):
        raise HTTPException(400, "Faqat PDF fayl yuklang")
    return content


@app.post("/preview")
def preview(file: UploadFile = File(...)):
    content = read_pdf_upload(file)
    try:
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            pages = []
            for page in doc.pages(0, min(len(doc), MAX_PREVIEW_PAGES)):
                jpeg = page.get_pixmap(dpi=110).tobytes("jpeg", jpg_quality=70)
                pages.append("data:image/jpeg;base64," + base64.b64encode(jpeg).decode())
            return {"pages": pages, "total": len(doc)}
    except Exception as error:
        raise HTTPException(422, f"PDF'ni ochib bo'lmadi: {error}")


@app.post("/analyze")
def analyze(file: UploadFile = File(...)):
    content = read_pdf_upload(file)
    # PyMuPDF faylni yo'ldan ochadi; tahlildan keyin vaqtinchalik nusxa o'chiriladi
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            result = parse.parse_document(ocr.read_pdf(tmp.name), file.filename or "hujjat.pdf")
        except Exception as error:
            raise HTTPException(422, f"PDF'ni o'qib bo'lmadi: {error}")
    return result
