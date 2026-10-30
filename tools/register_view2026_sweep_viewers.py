#!/usr/bin/env python3
"""Register the reproducible parameter-sweep viewers in exhibits.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/view2026/exhibits.json"
SWEEPS = {
    "poc_focus_stacking": ("f-number", "2.0–16.0"),
    "poc_interferometry_step": ("noise σ", "0.000–0.120"),
    "poc_polarization_specular": ("incidence angle", "0–80°"),
    "poc_photoelasticity": ("analyser angle", "0–180°"),
    "poc_motion_magnification": ("motion amplitude", "0.02–0.80 px"),
    "poc_compound_eye": ("per-view SNR", "0.5–16.0"),
    "poc_ct_void_morphology": ("threshold", "0.2–0.8"),
    "poc_active_contours": ("threshold", "image min–max"),
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
    for pid, (parameter, range_) in SWEEPS.items():
        old.append({"id": pid, "title": labels[pid],
                    "line": {lang: PREFIX[lang].format(p=parameter, r=range_) for lang in d["langs"]}})
    d["viewers"]["items"] = old
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
