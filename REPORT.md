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

Raqamlar jadvali (rekvizit, precision/recall/F1, ijrochi, muddat, CER; matnli va skan alohida) **README.md** ning
"Natijalar" bo'limida. Ground truth 6 ta matnli PDF'dan qo'lda tayyorlangan va tasdiqlangan, skan uchun ham o'sha
ishlatiladi. Quyida shu natijalarni qanday o'qish kerakligi.

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
3. **GPU'da VLM ikkinchi tekshiruvchi sifatida:** 8-bo'limdagi reja bo'yicha.
4. **LLM abzats ijrochisini ajratish uchun:** tashkiliy birlik so'zlari ro'yxatiga bog'liqlikni yo'qotadi.
5. **Foydalanuvchi tuzatishlaridan o'rganish:** UI'da tuzatish tugmasi, tuzatilgan natijalardan yangi ground truth
   va qoidalar uchun regressiya testlari.
6. Rasm sifatini oldindan tekshirish (DPI, shovqin, jadval topilmadi) va foydalanuvchiga ogohlantirish berish.

## 8. Nega VLM hozir ishlatilmadi (va qachon qo'shiladi)

VLM (rasmni to'g'ridan-to'g'ri o'qiydigan model) bu bosqichda ongli ravishda ishlatilmadi:

1. **Resurs.** Ish muhiti CPU, 16 GB RAM, diskda joy kam. Foydali VLM'lar GPU'da ishlaydi; CPU'da bir sahifa
   daqiqalar oladi, veb-interfeysda foydalanuvchi shuncha kutmaydi.
2. **Aniqlik xavfi.** VLM o'qiy olmagan joyini "o'ylab topishi" mumkin: sana, raqam yoki ijrochini aytilmagan
   qiymat bilan to'ldiradi. Huquqiy hujjatda bunday xato topshiriq muddatini o'zgartiradi va uni topish qiyin.
3. **Tushuntirib bo'lmaydi.** Qoida yo'lida har maydon qaysi regex yoki qoidadan chiqqani ko'rinadi, xatoni
   tuzatish mumkin. VLM'da xatoning sababi noma'lum.
4. **Kerak emas edi.** Berilgan skanlarda Tesseract va qoidalar 12 ta hujjatning hammasida ground truth bilan
   mos keldi (README'dagi jadval), ya'ni VLM yechadigan muammo shu to'plamda ko'rinmadi.
5. **Cheklov.** Hujjatlar tashqi bulutga yuborilmasligi shart; bu faqat lokal modelni qoldiradi, u esa 1-bandga
   qaytadi.

**Bu degani VLM kerak emas degani emas.** Sifatsiz skanda (5-bo'lim) tizim sinadi, qoidalar esa buzilgan OCR matnini
tuzata olmaydi. Aynan shu joyda VLM foyda berishi kutiladi (bu hozircha faraz, sinalmagan).

**Keyingi bosqich rejasi (GPU mavjud bo'lganda):**

1. VLM qoida yo'lini almashtirmaydi, **ikkinchi tekshiruvchi** bo'ladi: qoidalar natijasini beradi, VLM
   sahifa rasmidan o'sha maydonlarni mustaqil o'qiydi.
2. Ikkalasi mos kelsa, natija tasdiqlanadi. Mos kelmasa yoki OCR ishonchi past bo'lsa, maydon UI'da sariq
   "tekshiring" belgisi bilan chiqadi (shu mexanizm hozir ham bor).
3. Sana va raqamlarning yakuniy qiymati doim qoida yo'lidan olinadi, VLM faqat solishtirish uchun.
4. Baholash: avval 5-bo'limdagi sifatsiz skanlar to'plamida, keyin real hujjatlarda; metrika: qoida yo'li bilan
   solishtirganda qo'shimcha to'g'ri topilgan va noto'g'ri tasdiqlangan maydonlar soni, bir sahifa vaqti.

Bu eksperiment natijalari alohida bo'limda yoziladi.

## 9. VLM tajribasi

[natija kutilmoqda]
