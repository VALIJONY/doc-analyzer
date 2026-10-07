# Hisobot: hujjat tahlili tizimi

## 1. Tushunish

Vazifa: PDF (matnli yoki skan) dan ikki narsani ajratish: **rekvizitlar** (jo'natuvchi, raqam, sana, imzolagan
shaxs) va **topshiriqlar** (matn, ijrochi, muddat). Topshiriq abzatsda, bandda yoki jadvalda (shu jumladan 2-sahifadagi
ilovada) kelishi mumkin. Cheklov: hujjatlar tashqi bulutga yuborilmaydi.

Qiyin joylari: (1) skanda jadvalni o'qish, (2) nima topshiriq va nima emasligini ajratish, (3) ijrochi va
hamkorni ajratish, (4) muddatning 6 xil turi, (5) xat ostidagi "Ijrochi: ..." topshiriq ijrochisi emas.

## 2. Yondashuv va sabablari

```
PDF -> matn qatlami bormi?
  ha  -> PyMuPDF matn + find_tables
  yo'q -> 300 DPI -> median -> deskew -> Otsu -> chiziqlardan jadval kataklari
          -> har katak Tesseract psm 6, qolgan qism psm 4 (uzb+eng)
-> {"pages": [{"text", "tables", "words"}]}  -> parse.py (qoidalar) -> JSON
```

- **Nega qoidalar, LLM/VLM emas.** Mashina CPU'da, disk kam; qoidalar tez (bir skan taxminan 3 s) va tushuntirib beriladi:
  har maydon qaysi regex/qoidadan chiqqanini ko'rsatish mumkin. LLM sana va raqamni "to'qib chiqarishi" mumkin,
  bu huquqiy hujjatda xavfli. Hujjat tashqariga chiqmaydi.
- **Nega Tesseract.** Lokal, yengil, `uzb` tili bor, so'z darajasida ishonch bali beradi (UI'dagi "tekshiring"
  belgisi shundan). Matnli abzatslarni yaxshi o'qiydi.
- **Nega jadval katak-katak.** Sahifani butunlay OCR qilsak, ustunlar aralashadi. Chiziqlardan kataklar topilib,
  har biri alohida o'qilgani uchun ustun va qator tuzilishi saqlanadi.
- **Nega deskew kulrang rasmda.** Burchakni binar rasmdan topib, burishni kulrang rasmda qildim va keyin Otsu
  qo'lladim. Birinchi urinishda binar rasmni burganimda ingichka vertikal chiziqlar uzilib, jadval kataklari
  topilmadi (butun sahifa bitta bog'langan soha bo'lib qoldi, to'g'ri o'qishda 24 ta katak chiqadi).
- OCR faqat `ocr.py` da, shuning uchun dvigatelni almashtirish oson.

## 3. Tuzoqlar va ularning yechimi

| Tuzoq | Yechim |
|---|---|
| "Ijrochi: N. Sobirova" | `prepared_by` ga yoziladi; imzo va ijrochi bilan aralashmaydi |
| Standart muddat (NAMUNA_1, 6-band) | Qoida matnidan o'qiladi, muddatsiz topshiriqqa `default_rule` bilan qo'llanadi |
| Topshiriq emas: nazorat, tasdiqlash, umumiy chaqiriq, qoidaning o'zi, jadvalga kirish gapi | `NOT_A_TASK_RE` |
| Raqamsiz topshiriqlar (xat_1) | Band ichidagi qo'shimcha gaplar ajratiladi, ijrochi = qabul qiluvchi ("Markaz") |
| Hamkor ijrochi | "X Y bilan birgalikda" -> `executor` X, `co_executors` Y; jadvalda "A, B" -> A va [B] |
| Muddat turlari | `DEADLINE_PATTERNS`: tartib muhim (conditional -> start -> periodic -> permanent -> date -> relative) |
| Abzats ijrochisi | Gap boshidan birinchi tashkiliy birlik so'zigacha (dastlabki 6 so'zda) |

## 4. Baholash natijalari

`python evaluate.py` natijasi (`results/eval.md`). Ground truth 6 ta matnli PDF'dan qo'lda tayyorlangan,
tasdiqlangan, skan uchun ham o'sha ishlatiladi.

| Hujjat | Manba | CER | Rekvizit | Precision | Recall | F1 | Ijrochi | Muddat | Muddat matni |
|---|---|---|---|---|---|---|---|---|---|
| NAMUNA_1_abzats | matnli | - | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| NAMUNA_2_jadval | matnli | - | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| NAMUNA_3_ilova | matnli | - | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_1_abzatsdagi_topshiriqlar | matnli | - | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_2_jadvaldagi_topshiriqlar | matnli | - | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_3_ilovadagi_topshiriqlar | matnli | - | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| **JAMI (matnli)** | matnli | - | 36/36 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| NAMUNA_1_abzats | skaner | 0.081 | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| NAMUNA_2_jadval | skaner | 0.007 | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| NAMUNA_3_ilova | skaner | 0.072 | 5/5 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_1_abzatsdagi_topshiriqlar | skaner | 0.045 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_2_jadvaldagi_topshiriqlar | skaner | 0.041 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| xat_3_ilovadagi_topshiriqlar | skaner | 0.038 | 7/7 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| **JAMI (skaner)** | skaner | 0.047 | 36/36 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

**Bu natijani qanday o'qish kerak (muhim).** 1.00 umumlashuv isboti emas:

- Qoidalar aynan shu 6 ta hujjatga qarab yozilgan, ground truth'ni ham o'sha hujjatlardan tuzdik. Alohida
  "ko'rilmagan" test to'plami yo'q. Natija faqat "tizim ma'lum namunalarni to'g'ri qayta ishlaydi" deb o'qiladi.
- Ground truth'dagi bahsli qarorlar (hisobot berish topshiriq hisoblanishi, `start` turi, xat_2 oxiridagi gap,
  "A, B" ijrochilar) men va foydalanuvchi kelishgan variantga mos. Boshqacha kelishuv bo'lsa, ball o'zgaradi.
- Skanlar sifatli (150 DPI, ozgina shovqin). Pastdagi 5-bo'limda sifatsiz skan bilan natija keskin tushadi.

**CER nimadan iborat (skan, o'rtacha 4.7%).** Haqiqiy harf xatosi juda kam. Asosiy qismi:

- Matnli PDF'da sarlavha harflari orasida bo'sh joy bor ("Q A R O R I"), skanda esa "QARORI": taxminan 0.5-1% hisobiga
  qo'shiladi, bu OCR xatosi emas.
- Sahifa pastidagi test izohining chala o'qilgan qoldig'i ("test uchun cvgmple AE tizimini sinash...", ~113 belgi):
  izohni filtrlaydigan so'zlar ("example", "shartli") buzilganda filtr ishlamaydi. NAMUNA_1 va NAMUNA_3 CER'ining
  katta qismi shundan (8.1% va 7.2%).
- "№" -> "Ne"/"No"/kirill "Ме": regex shu variantlarni qabul qiladi, shuning uchun maydonga ta'sir qilmadi.
- xat_1: "«__» ___ dagi ___-son xatga" qatori qabul qiluvchi bilan birikib ketdi, "Tel." -> "Те).;".

## 5. Qayerda xato qiladi

**Sifatsiz skan (o'lchangan).** Bir martalik stress test (skript repoda yo'q, parametrlari: 80 DPI, Gauss shovqini
sigma=25, 2.5 daraja burilish, JPEG sifati 35, bir vaqtda qo'llangan; 6 ta skanning hammasi). Natija:

| Ko'rsatkich | Toza skan | Stress test |
|---|---|---|
| Rekvizit maydonlari | 36/36 | 4/36 |
| Topshiriqlar (topilgan / jami) | 39/39 | 4/39 |
| Ortiqcha topshiriqlar | 0 | 12 |

Qaysi qadam sinadi: jadvalli 3 hujjatda (NAMUNA_2, xat_2, xat_3) jadval kataklari umuman topilmadi va hech narsa
chiqmadi. Qolgan matn OCR'i ham buzildi ("2026-yil L-ivulga qa", "Integrarsiyasinl", "NOTARIAT VAFBDYOFAOLIYATINI").
Imzo qatori o'qilmagani uchun raqam, sana, imzolovchi bo'sh qoldi. Ya'ni qoidalar OCR toza bo'lishiga tayanadi,
xatoni tuzatmaydi. Bu stress test juda qattiq va bitta uslubda; real skanerlar bundan yaxshi bo'lishi mumkin, lekin
chegara qayerdaligi aniqlanmagan.

**Kod darajasida ma'lum zaif joylar (sinalmagan, kod tuzilishidan kelib chiqadi):**

- Jadvalning birinchi qatori doim sarlavha deb tashlanadi; sarlavhasiz jadvalning 1-qatori yo'qoladi.
- Sahifada bitta jadval deb faraz qilinadi; birlashgan kataklar va bir sahifadagi ikkita jadval qo'llab-quvvatlanmaydi.
- Ijrochi gap boshidagi 6 so'zda tashkiliy birlik so'zi bo'lsagina topiladi; ro'yxatda yo'q so'z ("sektori",
  "inspeksiyasi") yoki uzun nom bo'lsa, abzats ijrochisi `None` bo'ladi (xatda esa noto'g'ri holda qabul qiluvchiga
  yoziladi).
- Qabul qiluvchi "-ga" bilan tugaydigan birinchi so'zgacha olinadi; ikki so'zli yoki boshqa tuzilishdagi manzil buziladi.
  "Markaz" qisqartmasi "markaziga" so'zidan hosil qilinadi, boshqa tashkilot nomlari uchun noto'g'ri bo'ladi.
- Topshiriq emas deb belgilovchi so'zlar ("quyidagi", "nazorat qilish") haqiqiy topshiriqda uchrasa, u yo'qoladi.
- Bir xatboshida bir nechta muddat bo'lsa, birinchi mos kelgani olinadi.
- Ishonch belgisi: Tesseract apostrofli so'zlarni to'g'ri o'qiganda ham past ball beradi, shuning uchun
  ular hisobga olinmaydi. Natijada apostrofdagi xato ("o'" -> "o") belgilanmaydi, so'zma-so'z qolgan
  ishonchli so'zlar bo'lsa ham ba'zan to'g'ri so'zlar sariq chiqadi (masalan, "intellekt" 48 ball).

## 6. Cheklovlar

- Qoidalar 6 ta namuna asosida tuzilgan: yangi format (boshqa band belgilari, "a)", "-", jadvalsiz ro'yxat), boshqa
  imzo joylashuvi yoki boshqa tashkiliy birlik so'zlari ishlamasligi mumkin.
- Qo'lyozma, rangli muhr/imzo, ikki ustunli sahifa, sifatsiz skan qo'llab-quvvatlanmaydi.
- Baholash kichik (39 topshiriq, 12 fayl) va tuzatuvchi bo'lmagan to'plamda; ishonch oralig'i keng.
- Ish kunlari hisobida bayramlar hisobga olinmaydi.
- Yuklangan fayl faqat vaqtinchalik faylga yoziladi va so'rovdan keyin o'chadi; autentifikatsiya va so'rov
  cheklovlari yo'q (ichki tarmoq uchun mo'ljallangan).

## 7. Keyingi qadamlar

1. **Ko'rilmagan hujjatlarda baholash:** 30-50 ta real hujjat va mustaqil ground truth; qoidalarni shunga qarab sozlash.
2. **PaddleOCR / PP-Structure:** jadval tuzilishi va sifatsiz skanlarda Tesseract'dan kuchliroq bo'lishi kutiladi;
   `ocr.py` ni almashtirish kifoya.
3. **GPU'da VLM ikkinchi tekshiruvchi sifatida:** qoidalar natijasini tasdiqlaydi yoki ishonchi past maydonlarni
   qayta o'qiydi (raqam va sana qoida yo'lidan olinadi, VLM faqat solishtiradi).
4. **LLM abzats ijrochisini ajratish uchun:** tashkiliy birlik so'zlari ro'yxatiga bog'liqlikni yo'qotadi.
5. **Foydalanuvchi tuzatishlaridan o'rganish:** UI'da tuzatish tugmasi, tuzatilgan natijalardan yangi ground truth
   va qoidalar uchun regressiya testlari.
6. Rasm sifatini oldindan tekshirish (DPI, shovqin, jadval topilmadi) va foydalanuvchiga ogohlantirish berish.

## 8. VLM tajribasi

[natija kutilmoqda]
