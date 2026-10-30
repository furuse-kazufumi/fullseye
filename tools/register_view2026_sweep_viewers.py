#!/usr/bin/env python3
"""Register the reproducible parameter-sweep viewers in exhibits.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/view2026/exhibits.json"
SWEEPS = {
    "poc_focus_stacking": (("F値", "f-number", "光圈值", "光圈值", "조리개값", "Blendenzahl", "एफ़-नंबर", "nombre d’ouverture"), "2.0–16.0"),
    "poc_interferometry_step": (("雑音 σ", "noise σ", "噪声 σ", "雜訊 σ", "잡음 σ", "Rauschen σ", "शोर σ", "bruit σ"), "0.000–0.120"),
    "poc_polarization_specular": (("入射角", "incidence angle", "入射角", "入射角", "입사각", "Einfallswinkel", "आपतन कोण", "angle d’incidence"), "0–80°"),
    "poc_photoelasticity": (("検光子角", "analyser angle", "检偏器角度", "檢偏器角度", "검광자 각도", "Analysatorwinkel", "विश्लेषक कोण", "angle de l’analyseur"), "0–135°"),
    "poc_motion_magnification": (("運動振幅", "motion amplitude", "运动振幅", "運動振幅", "운동 진폭", "Bewegungsamplitude", "गति आयाम", "amplitude du mouvement"), "0.02–0.80 px"),
    "poc_compound_eye": (("視点ごとのSNR", "per-view SNR", "每视点信噪比", "每視點訊噪比", "시점별 SNR", "SNR je Ansicht", "प्रति-दृश्य SNR", "SNR par vue"), "0.5–16.0"),
    "poc_ct_void_morphology": (("しきい値", "threshold", "阈值", "閾值", "임계값", "Schwellenwert", "सीमा", "seuil"), "0.2–0.8"),
    "poc_active_contours": (("反復回数", "iterations", "迭代次数", "迭代次數", "반복 횟수", "Iterationen", "पुनरावृत्तियाँ", "itérations"), "0–1000"),
}

PREFIX = {
    "ja": "PoC 関数を再実行して {p} を {r} で掃引する。",
    "en": "Re-runs the PoC function while sweeping {p} over {r}.",
    "zh": "重新运行 PoC 函数，将 {p} 在 {r} 范围内扫描。",
    "tw": "重新執行 PoC 函數，將 {p} 在 {r} 範圍內掃描。",
    "ko": "PoC 함수를 다시 실행해 {p}을(를) {r} 범위에서 훑는다.",
    "de": "Führt die PoC-Funktion erneut aus und variiert {p} über {r}.",
    "hi": "PoC फ़ंक्शन दोबारा चलाकर {p} को {r} तक बदलता है।",
    "fr": "Réexécute la fonction du PoC en faisant varier {p} de {r}.",
}


def main():
    d = json.loads(PATH.read_text(encoding="utf-8"))
    labels = {e["id"]: e["label"] for e in d["all"]}
    old = [x for x in d["viewers"]["items"] if x["id"] not in SWEEPS]
    for pid, (parameters, range_) in SWEEPS.items():
        translated = dict(zip(d["langs"], parameters))
        old.append({"id": pid, "title": labels[pid],
                    "line": {lang: PREFIX[lang].format(p=translated[lang], r=range_) for lang in d["langs"]}})
    d["viewers"]["items"] = old
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
