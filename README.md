# Hujjat tahlili tizimi

PDF hujjatdan (matnli yoki skaner qilingan) **rekvizitlarni** (jo'natuvchi, raqam, sana, imzolagan shaxs) va
**topshiriqlarni** (matn, ijrochi, muddat) avtomatik ajratib oladi. Veb-sahifada PDF yuklaysiz, «Tahlil qilish»
tugmasini bosasiz, rekvizitlar va topshiriqlar ro'yxati muddatlari bilan chiqadi.

- Hamma narsa **lokal** ishlaydi: hujjatlar tashqi bulut xizmatlariga yuborilmaydi, sahifada CDN yo'q.
- **LLM/VLM ishlatilmaydi**: qoidalar + OCR (sababi va keyingi bosqich rejasi: [REPORT.md](REPORT.md)).
- CPU'da ishlaydi, GPU kerak emas. Bir skan taxminan 3 soniyada tahlil qilinadi.

## Tezkor start

```bash
git clone https://github.com/VALIJONY/doc-analyzer.git
cd doc-analyzer
docker compose up -d --build
```

Brauzerda **http://localhost:8002** ni oching.

## Ishga tushirish

### 1) Docker bilan (tavsiya)

Kerak: Docker va Docker Compose. Tesseract va o'zbek tili imij ichida o'rnatiladi.

```bash
docker compose up -d --build     # qurish va ishga tushirish (port 8002)
docker compose logs -f web       # loglar
docker compose down              # to'xtatish
```

### 2) Docker'siz

Kerak: Python 3.12 va Tesseract (o'zbek tili bilan).

```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-uzb

# macOS:   brew install tesseract tesseract-lang
# Windows: Tesseract o'rnatuvchisida "Uzbek" tilini belgilang va PATH ga qo'shing

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --port 8002
```

`uzb` tili topilmasa, dastur o'zi `eng` tiliga o'tadi (aniqlik pasayadi). Til o'rnatilganini tekshirish:
`tesseract --list-langs`.

### Tez-tez uchraydigan muammolar

| Muammo | Yechim |
|---|---|
| `port is already allocated` | 8002 band. `docker-compose.yml` dagi `"8002:8000"` ni boshqa portga o'zgartiring |
| `TesseractNotFoundError` | Tesseract o'rnatilmagan yoki PATH da yo'q (Docker'siz yo'l) |
| Skan natijasi bo'sh yoki aralash | Skan sifati past (150 DPI dan past, kuchli shovqin). Chegaralar: [REPORT.md](REPORT.md) |
| Sahifa eski ko'rinadi | Kod o'zgargan bo'lsa `docker compose up -d --build` bilan qayta quring |

## Foydalanish

**Veb-sahifa.** PDF'ni sahifadagi varaqqa tashlang yoki tanlang: hujjat sahifalari shu yerning o'zida ko'rinadi
(«Kattalashtirish» tugmasi o'qish uchun kattaroq oyna ochadi). «Tahlil qilish» tugmasini bosing. Chapda
rekvizitlar, o'ngda topshiriqlar, ijrochilar va muddatlar shkalasi chiqadi. Sariq belgi: OCR ishonchi past
maydon, hujjat bilan solishtiring. «JSON yuklab olish» natijani fayl qilib saqlaydi.

**API.**

```bash
curl -F "file=@hujjat.pdf" http://localhost:8002/analyze        # JSON natija
curl -F "file=@hujjat.pdf" http://localhost:8002/preview        # sahifalar rasmi (base64)
```

Cheklov: faqat PDF, 20 MB gacha.

## Natijalar

Baholash 6 hujjat × 2 versiya (matnli va skan) = 12 ta PDF'da o'tkazildi. Ground truth matnli PDF'lardan qo'lda
tayyorlangan va tasdiqlangan; skan uchun ham o'sha ishlatiladi.

| Ko'rsatkich | Matnli PDF | Skan |
|---|---|---|
| Rekvizit maydonlari to'g'ri | 36 / 36 | 36 / 36 |
| Topshiriqlar: precision / recall / F1 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| Ijrochi aniqligi (mos topshiriqlarda) | 1.00 | 1.00 |
| Muddat aniqligi (tur + sana + manba) | 1.00 | 1.00 |
| OCR sifati, CER (kam bo'lgani yaxshi) | - | 0.047 |

Hujjatlar bo'yicha CER (skan): NAMUNA_1 0.081, NAMUNA_2 0.007, NAMUNA_3 0.072, xat_1 0.045, xat_2 0.041, xat_3 0.038.
Eng katta qismi OCR xatosi emas: sarlavhadagi "Q A R O R I" / "QARORI" farqi va sahifa pastidagi test izohining
chala o'qilgan qoldig'i.

**Bu natijani to'g'ri o'qing.** 1.00 umumlashuvni isbotlamaydi: qoidalar aynan shu 6 hujjatga qarab yozilgan,
ground truth ham ulardan tuzilgan, alohida "ko'rilmagan" test to'plami yo'q. Sifatsiz skanda tizim sinadi:
80 DPI, kuchli shovqin, 2.5° burilish va JPEG siqish birga qo'llanganda rekvizitlar 4/36, topshiriqlar 4/39
topildi. Batafsil: [REPORT.md](REPORT.md).

## Qanday ishlaydi

```
PDF
 └─ har sahifa
     ├─ matn qatlami bor (>50 belgi) ── PyMuPDF: matn + jadvallar
     └─ skan ── 300 DPI rasm → median → deskew → Otsu
                 ├─ OpenCV: chiziqlar → jadval kataklari → har katak Tesseract (psm 6)
                 └─ jadvaldan tashqari qism → Tesseract (psm 4), uzb+eng
                 (har so'z uchun ishonch bali)
 └─ ikkala yo'l bir xil format:  {"pages": [{"text", "tables", "words"}]}      ocr.py
 └─ qoidalar: rekvizitlar, topshiriqlar (abzats / jadval / ilova), muddatlar    parse.py
 └─ JSON
```

| Fayl | Vazifasi |
|---|---|
| `app.py` | FastAPI: `GET /` sahifa, `POST /analyze`, `POST /preview` |
| `ocr.py` | PDF → matn va jadvallar (faqat OCR; boshqa dvigatelga o'tish shu fayl orqali) |
| `parse.py` | Rekvizitlar, topshiriqlar, muddatlar (faqat qoidalar) |
| `evaluate.py` | Ground truth bilan solishtirish |
| `ground_truth/` | 6 hujjat uchun kutilgan natija |
| `templates/index.html` | Veb-sahifa (CSS va JS ichida, tashqi resurslarsiz) |
| `data/pdfs/` | Berilgan 12 ta PDF (`matnli/`, `skaner/`) |

## Natija formati

```json
{
  "file": "xat_1_abzatsdagi_topshiriqlar.pdf", "source": "text", "doc_type": "xat",
  "requisites": {
    "sender": "RAQAMLI HUQUQIY XIZMATLAR AGENTLIGI", "number": "03-12/1456",
    "date": "2026-09-08", "date_raw": "08.09.2026",
    "signer_position": "Direktor o'rinbosari", "signer_name": "Sh. Qodirov",
    "recipient": "Adliya organlari va muassasalarida axborot texnologiyalarini rivojlantirish markaziga",
    "prepared_by": "N. Sobirova", "low_confidence": []
  },
  "tasks": [{
    "n": "3", "text": "Axborot xavfsizligi bo'limi Sun'iy intellekt laboratoriyasi bilan birgalikda ...",
    "executor": "Axborot xavfsizligi bo'limi", "co_executors": ["Sun'iy intellekt laboratoriyasi"],
    "deadline_raw": "o'n kun muddatda", "deadline_type": "relative", "deadline_date": "2026-09-18",
    "computed": true, "deadline_source": "explicit", "location": "paragraph",
    "low_confidence": false, "low_fields": []
  }]
}
```

- `doc_type`: `qaror` yoki `xat`. `source`: `text` (matn qatlami) yoki `ocr` (skan).
- `deadline_type`: `date`, `relative`, `periodic`, `conditional`, `permanent`, `start`, `none`, `unknown`.
- `deadline_source`: `explicit` (matnda yozilgan), `default_rule` (hujjatdagi standart qoida), `none`.
- `location`: `paragraph`, `table` yoki `appendix` (ilova jadvali).
- `low_confidence`, `low_fields`: OCR ishonchi 70 dan past maydonlar (matnli PDF'da bo'sh).

## Qoidalar

**Nima topshiriq.** Tashkiliy birlik (yoki xat qabul qiluvchisi) biror ishni bajarishi kerak bo'lgan band yoki gap
(`-sin`, `-sinlar`, `so'raymiz`, `so'raladi` bilan tugaydi) yoki jadval qatori. Quyidagilar topshiriq **emas**:

- nazorat: "qaror ijrosini nazorat qilish ... zimmasiga yuklansin";
- tasdiqlash: "reja ilovaga muvofiq tasdiqlansin";
- umumiy chaqiriq: "o'z vaqtida ijro etilishi ta'minlansin";
- jadvalga kirish gapi ("quyidagi topshiriqlar belgilansin:");
- standart muddat qoidasining o'zi ("muddati alohida ko'rsatilmagan topshiriqlar bir oy muddatda ijro etilsin").

**Ijrochi.** Abzatsda gap boshidagi ot birikmasi, birinchi tashkiliy birlik so'zigacha (boshqarmasi, departamenti,
bo'limi, ...). "X Y bilan birgalikda" bo'lsa, ijrochi X, hamkor Y (`co_executors`). Jadvalda "A, B" bo'lsa,
birinchisi `executor`, qolganlari `co_executors`. Ijrochisi yozilmagan xat topshirig'i qabul qiluvchiga ("Markaz")
beriladi. Xat ostidagi "Ijrochi: N. Sobirova" xatni tayyorlagan xodim (`prepared_by`): topshiriq ijrochisi ham,
imzolagan shaxs ham emas.

**Muddat.** `deadline_raw` doim saqlanadi.

| Tur | Misol | Izoh |
|---|---|---|
| `date` | `2026-yil 1-iyulga qadar`, `01.10.2026 yilgacha`, `18.09.2026` | ISO sana bilan |
| `relative` | `o'n kun muddatda`, `bir oy muddatda`, `uch ish kuni ichida` | hujjat sanasidan hisoblanadi (`computed: true`), bayramlar hisobga olinmaydi |
| `periodic` | `har oyda`, `har chorakda`, `har oyning 5-sanasiga qadar` | sana yo'q |
| `conditional` | `prototip tayyor bo'lgandan so'ng 15 kun ichida` | sana yo'q |
| `permanent` | `doimiy` | |
| `start` | `2026-yil 15-martdan boshlab` | muddat emas, boshlanish sanasi |

Muddati yo'q topshiriqqa hujjatdagi standart qoida qo'llanadi (`deadline_source: "default_rule"`).

## Baholashni qayta ishga tushirish

```bash
python evaluate.py analyze   # 12 ta PDF → results/*.json
python evaluate.py           # + ground_truth bilan solishtirish → results/eval.md
```

`results/` lokal papka, repoga kiritilmaydi. Xatolar ro'yxati (qaysi hujjat, qaysi maydon, nima kutilgan, nima
chiqqan) shu yerga yoziladi.

## Cheklovlar va keyingi bosqich

- Qoidalar 6 ta namuna asosida tuzilgan: yangi format, qo'lyozma, rangli muhr yoki sifatsiz skan ishlamasligi mumkin.
- Bitta sahifada bitta jadval deb faraz qilinadi; jadvalning birinchi qatori sarlavha hisoblanadi.
- **VLM (ko'rish-til modeli) hozir ishlatilmagan** va keyingi bosqichga qoldirilgan: CPU'da sekin, sana va raqamni
  "to'qib chiqarish" xavfi bor, natijani tushuntirib bo'lmaydi. Reja: GPU'da ikkinchi tekshiruvchi sifatida
  qo'shish. [REPORT.md](REPORT.md) da sabablar va reja batafsil.
- Boshqa rejalar: PaddleOCR / PP-Structure, abzats ijrochisini LLM bilan ajratish, foydalanuvchi tuzatishlaridan
  o'rganish.
