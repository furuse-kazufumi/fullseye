#!/usr/bin/env python3
"""ViEW2026 A 群の再生成図が最近傍拡大でないことを検査する。

``figures.json`` の ``name`` で変更前後を対応させるため、個別修正で番号が動いても
同じ図を比べられる。寸法が正確に 2 倍の PNG は、変更前を画素複製した像との
前景一致率が 0.9 未満でなければ失敗する。同寸法は実データをネイティブ解像度で
保った ``native``、縦積みなどは ``layout`` として表に残す。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


SHORTLIST = (
    "poc_phase_measuring_deflectometry", "poc_industrial_oct",
    "poc_hyperspectral_foreign_matter", "poc_thin_film_reflectometry",
    "poc_cad_scan_deviation", "poc_telecentric_metrology",
    "poc_tem_ctf_thon_rings", "poc_virtual_sem_kv_cd_bse",
    "poc_dual_energy_xray", "poc_weld_radiograph_porosity",
    "poc_good_sample_variation_model", "poc_code_matching_breakdown",
    "poc_fourier_ptychography", "poc_photoelasticity",
)


def _pngs(root: Path, poc_id: str) -> dict[str, Path]:
    directory = root / poc_id
    manifest = json.loads((directory / "figures.json").read_text(encoding="utf-8-sig"))
    return {str(row["name"]): directory / str(row["file"])
            for row in manifest if str(row.get("file", "")).lower().endswith(".png")}


def _rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _foreground_match(redrawn: np.ndarray, nearest: np.ndarray) -> float:
    foreground = (redrawn.min(axis=2) < 250) | (nearest.min(axis=2) < 250)
    if not np.any(foreground):
        return 0.0
    delta = np.abs(redrawn[foreground].astype(np.int16) - nearest[foreground].astype(np.int16))
    return float(np.mean(np.all(delta <= 1, axis=1)))


def check(before_root: Path, after_root: Path) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    for poc_id in SHORTLIST:
        before, after = _pngs(before_root, poc_id), _pngs(after_root, poc_id)
        for name in sorted(set(before) | set(after)):
            if name not in after:
                errors.append(f"{poc_id}/{name}: 再生成後に無い")
                rows.append({"id": poc_id, "name": name, "mode": "missing", "match": None})
                continue
            if name not in before:
                rows.append({"id": poc_id, "name": name, "mode": "new", "match": None})
                continue
            old, new = _rgb(before[name]), _rgb(after[name])
            oh, ow = old.shape[:2]
            nh, nw = new.shape[:2]
            match = None
            if (nh, nw) == (2 * oh, 2 * ow):
                nearest = old.repeat(2, axis=0).repeat(2, axis=1)
                match = _foreground_match(new, nearest)
                mode = "redrawn-2x"
                if match >= 0.9:
                    errors.append(f"{poc_id}/{name}: 最近傍拡大との前景一致率 {match:.3f} >= 0.9")
            elif (nh, nw) == (oh, ow):
                mode = "native"
            else:
                mode = "layout"
            rows.append({"id": poc_id, "name": name, "mode": mode, "match": match,
                         "before": f"{ow}x{oh}", "after": f"{nw}x{nh}"})
    return rows, errors


def markdown(rows: list[dict[str, object]]) -> str:
    lines = ["| id | PNG | 判定 | 変更前 → 変更後 | 最近傍との前景一致率 |",
             "|---|---|---:|---:|---:|"]
    for row in rows:
        match = "—" if row.get("match") is None else f"{row['match']:.3f}"
        sizes = "—" if "before" not in row else f"{row['before']} → {row['after']}"
        lines.append(f"| {row['id']} | {row['name']} | {row['mode']} | {sizes} | {match} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path,
                        default=Path("docs/articles/assets/poc"))
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    rows, errors = check(args.before, args.after)
    report = markdown(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    for error in errors:
        print("NG:", error)
    print("PNG %d 枚、NG %d 件" % (len(rows), len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
