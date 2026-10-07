"""Baholash.

python evaluate.py analyze   -> faqat 12 ta PDF'ni tahlil qilib results/*.json ga yozadi
python evaluate.py           -> tahlil + ground_truth bilan solishtirib results/eval.md yozadi
"""
import glob
import json
import os
import re
import sys
from difflib import SequenceMatcher

from rapidfuzz.distance import Levenshtein

import ocr
import parse

PDF_DIRS = {"matnli": "data/pdfs/matnli", "skaner": "data/pdfs/skaner"}
MATCH_THRESHOLD = 0.8  # topshiriq matnlari shundan o'xshash bo'lsa, mos hisoblanadi
REQUISITE_FIELDS = ["sender", "number", "date", "signer_position", "signer_name"]
LETTER_ONLY_FIELDS = ["recipient", "prepared_by"]


def normalize(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower().rstrip(".,;")


def full_text(raw: dict) -> str:
    parts = []
    for page in raw["pages"]:
        parts.append(page["text"])
        parts += [" ".join(row) for table in page["tables"] for row in table]
    return normalize(" ".join(parts))


def analyze_all() -> dict:
    """Qaytaradi: {"matnli": {asosiy_nom: (raw, natija)}, "skaner": {...}}"""
    os.makedirs("results", exist_ok=True)
    analyzed = {}
    for kind, folder in PDF_DIRS.items():
        analyzed[kind] = {}
        for path in sorted(glob.glob(f"{folder}/*.pdf")):
            raw = ocr.read_pdf(path)
            result = parse.parse_document(raw, path)
            with open(f"results/{os.path.basename(path)[:-4]}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            analyzed[kind][os.path.basename(path)[:-4].removesuffix("_skaner")] = (raw, result)
    return analyzed


def match_tasks(expected: list, got: list):
    """Matn o'xshashligi bo'yicha ochko'zlik bilan juftlaydi. Qaytaradi: [(kutilgan, chiqqan)]."""
    scores = sorted(((SequenceMatcher(None, normalize(e["text"]), normalize(g["text"])).ratio(), i, j)
                     for i, e in enumerate(expected) for j, g in enumerate(got)), reverse=True)
    used_e, used_g, pairs = set(), set(), []
    for score, i, j in scores:
        if score >= MATCH_THRESHOLD and i not in used_e and j not in used_g:
            used_e.add(i)
            used_g.add(j)
            pairs.append((expected[i], got[j]))
    missing = [e for i, e in enumerate(expected) if i not in used_e]
    extra = [g for j, g in enumerate(got) if j not in used_g]
    return pairs, missing, extra


def executors_equal(e: dict, g: dict) -> bool:
    return (normalize(e["executor"]) == normalize(g["executor"])
            and sorted(map(normalize, e["co_executors"])) == sorted(map(normalize, g["co_executors"])))


def deadline_equal(e: dict, g: dict) -> bool:
    return all(e[k] == g[k] for k in ("deadline_type", "deadline_date", "deadline_source"))


def score_document(name: str, kind: str, expected: dict, raw_text: dict, raw: dict, result: dict, errors: list):
    fields = REQUISITE_FIELDS + (LETTER_ONLY_FIELDS if expected["doc_type"] == "xat" else [])
    req_ok = 0
    for field in fields:
        want, got = expected["requisites"][field], result["requisites"][field]
        if normalize(want) == normalize(got):
            req_ok += 1
        else:
            errors.append(f"| {name} | {kind} | rekvizit: {field} | {want} | {got} |")

    pairs, missing, extra = match_tasks(expected["tasks"], result["tasks"])
    for e in missing:
        errors.append(f"| {name} | {kind} | topshiriq topilmadi | {e['text'][:70]} | - |")
    for g in extra:
        errors.append(f"| {name} | {kind} | ortiqcha topshiriq | - | {g['text'][:70]} |")
    exec_ok = deadline_ok = raw_ok = 0
    for e, g in pairs:
        label = (e["text"][:40] + "...")
        if executors_equal(e, g):
            exec_ok += 1
        else:
            errors.append(f"| {name} | {kind} | ijrochi ({label}) | {e['executor']} {e['co_executors']} | {g['executor']} {g['co_executors']} |")
        if deadline_equal(e, g):
            deadline_ok += 1
        else:
            errors.append(f"| {name} | {kind} | muddat ({label}) | {e['deadline_type']} {e['deadline_date']} {e['deadline_source']} | {g['deadline_type']} {g['deadline_date']} {g['deadline_source']} |")
        raw_ok += normalize(e["deadline_raw"]) == normalize(g["deadline_raw"])

    cer = None
    if kind == "skaner":
        ref = full_text(raw_text)
        cer = Levenshtein.distance(ref, full_text(raw)) / len(ref)
    return {"cer": cer, "req_ok": req_ok, "req_total": len(fields), "tp": len(pairs), "gt": len(expected["tasks"]),
            "pred": len(result["tasks"]), "exec_ok": exec_ok, "deadline_ok": deadline_ok, "raw_ok": raw_ok}


def ratio(a: int, b: int) -> str:
    return f"{a / b:.2f}" if b else "-"


def row(label: str, kind: str, s: dict) -> str:
    precision, recall = s["tp"] / s["pred"] if s["pred"] else 0, s["tp"] / s["gt"] if s["gt"] else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    cer = f"{s['cer']:.3f}" if s["cer"] is not None else "-"
    return (f"| {label} | {kind} | {cer} | {s['req_ok']}/{s['req_total']} | {precision:.2f} | {recall:.2f} | {f1:.2f} "
            f"| {ratio(s['exec_ok'], s['tp'])} | {ratio(s['deadline_ok'], s['tp'])} | {ratio(s['raw_ok'], s['tp'])} |")


def main():
    analyzed = analyze_all()
    if sys.argv[1:] == ["analyze"]:
        print(f"{sum(len(v) for v in analyzed.values())} ta fayl results/ ga yozildi")
        return

    lines = ["# Baholash natijalari", "",
             "| Hujjat | Manba | CER | Rekvizit | Precision | Recall | F1 | Ijrochi | Muddat | Muddat matni |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    errors = []
    for kind in PDF_DIRS:
        scores = []
        for name, (raw, result) in analyzed[kind].items():
            expected = json.load(open(f"ground_truth/{name}.json", encoding="utf-8"))
            scores.append(score_document(name, kind, expected, analyzed["matnli"][name][0], raw, result, errors))
            lines.append(row(name, kind, scores[-1]))
        totals = {key: sum(s[key] for s in scores) for key in scores[0] if key != "cer"}
        totals["cer"] = sum(s["cer"] for s in scores) / len(scores) if kind == "skaner" else None
        lines.append(row(f"**JAMI ({kind})**", kind, totals))

    lines += ["", "CER = skan matni bilan matnli PDF matni orasidagi Levenshtein masofasi / matnli PDF uzunligi (o'rtacha).",
              "Rekvizit = to'g'ri maydonlar / jami maydonlar. Ijrochi, Muddat = mos kelgan topshiriqlar ichida aniqlik.", "",
              "## Xatolar", "", "| Hujjat | Manba | Maydon | Kutilgan | Chiqqan |", "|---|---|---|---|---|"]
    lines += errors or ["| - | - | xato yo'q | - | - |"]
    with open("results/eval.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
