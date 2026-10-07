# Hujjat tahlili tizimi

PDF hujjatdan (matnli yoki skaner qilingan) rekvizitlarni (jo'natuvchi, raqam, sana, imzolagan shaxs) va
topshiriqlarni (matn, ijrochi, muddat) ajratib oladi. Hamma narsa lokal ishlaydi: hujjatlar tashqi bulut
xizmatlariga yuborilmaydi, LLM/VLM ishlatilmaydi, sahifada CDN yo'q.

## Ishga tushirish

Docker bilan (port 8002):

```bash
docker compose up -d --build
# http://localhost:8002
```

Docker'siz:

```bash
sudo apt install tesseract-ocr tesseract-ocr-uzb   # uzb bo'lmasa, kod eng tiliga o'tadi
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 8002
```

Testlar va baholash:

```bash
pytest                         # muddat parseri, regex'lar, hujjatlar bo'yicha tekshiruvlar
python evaluate.py analyze     # 12 ta PDF -> results/*.json
python evaluate.py             # + ground_truth bilan solishtirish -> results/eval.md
```

## Arxitektura

```
PDF -> har sahifa:
  matn qatlami bor (PyMuPDF, >50 belgi) -> matn + jadvallar (PyMuPDF find_tables)
  skan -> rasm (300 DPI) -> kulrang -> median -> deskew -> Otsu
       -> OpenCV: gorizontal/vertikal chiziqlar -> jadval kataklari -> har katak Tesseract (psm 6)
       -> jadvaldan tashqari qism Tesseract (psm 4), lang uzb+eng
       -> image_to_data: har so'z uchun ishonch bali
-> ikkala yo'l bir xil format: {"pages": [{"text", "tables", "words"}]}     (ocr.py)
-> parse.py: rekvizitlar (regex + joylashuv), topshiriqlar (abzats / jadval / ilova), muddat normalizatsiyasi
-> JSON
```

- `app.py`: FastAPI, `GET /` sahifa, `POST /analyze` (PDF -> JSON).
- `ocr.py`: faqat OCR. Boshqa dvigatelga (masalan, PaddleOCR) o'tish uchun shu fayl o'zgaradi.
- `parse.py`: faqat qoidalar.
- `evaluate.py`: baholash, `ground_truth/` bilan solishtiradi.

## Natija formati

```json
{
  "file": "xat_1_abzatsdagi_topshiriqlar.pdf", "source": "text|ocr", "doc_type": "qaror|xat",
  "requisites": {"sender": "...", "number": "03-12/1456", "date": "2026-09-08", "date_raw": "08.09.2026",
                 "signer_position": "...", "signer_name": "Sh. Qodirov", "recipient": "...",
                 "prepared_by": "N. Sobirova", "low_confidence": []},
  "tasks": [{"n": "1", "text": "...", "executor": "...", "co_executors": [],
             "deadline_raw": "...", "deadline_type": "date", "deadline_date": "2026-09-20", "computed": false,
             "deadline_source": "explicit|default_rule|none", "location": "paragraph|table|appendix",
             "low_confidence": false, "low_fields": []}]
}
```

`low_confidence` / `low_fields`: OCR ishonchi 70 dan past so'zli maydonlar. UI'da sariq rangda "tekshiring" deb
chiqadi. Matnli PDF'da bunday belgi bo'lmaydi. Apostrofli so'zlar ishonch hisobiga kirmaydi (sababi REPORT.md'da).

## Qoidalar

**Nima topshiriq.** Topshiriq: tashkiliy birlik (yoki qabul qiluvchi) biror ishni bajarishi kerak bo'lgan band
yoki gap (`-sin`, `-sinlar`, `so'raymiz`, `so'raladi` bilan tugaydi) yoki jadval qatori. Quyidagilar
topshiriq **emas**:

- nazorat: "qaror ijrosini nazorat qilish ... zimmasiga yuklansin";
- tasdiqlash: "reja ilovaga muvofiq tasdiqlansin";
- umumiy chaqiriq: "o'z vaqtida ijro etilishi ta'minlansin";
- jadvalga kirish gapi ("quyidagi topshiriqlar belgilansin:", ":" bilan tugaydi);
- standart muddat qoidasining o'zi ("muddati alohida ko'rsatilmagan topshiriqlar bir oy muddatda ijro etilsin").

**Ijrochi.** Abzatsda gap boshidagi ot birikmasi, birinchi tashkiliy birlik so'zigacha (boshqarmasi, departamenti,
bo'limi, ...). "X Y bilan birgalikda" bo'lsa, ijrochi X, hamkor Y (`co_executors`). Jadvalda "A, B" bo'lsa,
birinchisi `executor`, qolganlari `co_executors`ga yoziladi. Ijrochi yozilmagan xat topshirig'i qabul qiluvchiga
("Markaz") beriladi. "Ijrochi: N. Sobirova" xatni tayyorlagan xodim (`prepared_by`), topshiriq ijrochisi ham,
imzolagan shaxs ham emas.

**Muddat.** `deadline_raw` doim saqlanadi. Turlari: `date`, `relative` (hujjat sanasidan hisoblanadi,
`computed: true`, ish kunlarida bayramlar hisobga olinmaydi), `periodic`, `conditional`, `permanent`,
`start` (boshlanish sanasi, muddat emas; `deadline_date` bo'sh). Muddati yo'q topshiriqlarga hujjatdagi
standart qoida qo'llanadi (`deadline_source: "default_rule"`).
