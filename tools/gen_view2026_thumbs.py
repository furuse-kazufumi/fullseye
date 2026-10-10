#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の案内ページ(`docs/view2026/`)のサムネイルを作る。

    py -3.11 tools/gen_view2026_thumbs.py            # docs/view2026/thumbs/<id>.jpg を作り直す
    py -3.11 tools/gen_view2026_thumbs.py --sheet X  # 確認用の一覧画像を X に書く(repo の外に)

論文の QR コードからスマートフォンで開かれるページなので、最初に読み込むのは
**サムネイルだけ**にする(1 枚 320 × 320 の JPEG、数十 KB)。動画・GIF・原寸の図は
タイルを押したときに初めて読む —— それらは各 PoC がすでに `docs/articles/assets/poc/`
に出している既存の図で、ここでは複製しない。

サムネイルの元は、動く図なら GIF の 1 コマ(`frame` = 全コマ中の位置 0〜1)、
静止図なら PoC の `_720.jpg`。`crop` は元画像に対する切り出し枠で、
省略すると中央の正方形。枠は (左, 上, 一辺) で、左は幅に対する比、上と一辺は高さに対する比
(正方形を歪めずに切るため)。数値はここに書かない(ページの数値は各 PoC の図の説明と実行ログが正本)。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "docs" / "articles" / "assets" / "poc"
OUT = ROOT / "docs" / "view2026" / "thumbs"
SIZE = 320
QUALITY = 80

#: (PoC id, サムネイルの元(POC からの相対), コマの位置 or None, 切り出し枠 or None)
SPEC = [
    ("poc_real_defect_floor", "poc_real_defect_floor/02_defect_floor_sweep.gif", 0.85, (0.02, 0.0, 1.0)),
    ("poc_active_contours", "poc_active_contours/06_u_shape_snakes.gif", 1.0, (0.5, 0.0, 1.0)),
    ("poc_dic_strain", "poc_dic_strain/05_tensile_ramp.gif", 1.0, (0.33, 0.0, 0.55)),
    ("poc_focus_stacking", "poc_focus_stacking/05_focus_sweep.gif", 1.0, (0.5, 0.04, 0.55)),
    ("poc_registration_basin", "poc_registration_basin/05_icp_basin_iterations.gif", 0.5, (0.335, 0.0, 0.47)),
    ("poc_stockpile_volume", "poc_stockpile_volume/07_scan_orbit.gif", 0.3, None),
    ("poc_ct_fidelity", "poc_ct_fidelity/01_recon_sweep_720.jpg", None, None),
    ("poc_ct_void_morphology", "poc_ct_void_morphology/13_section_sweep.gif", 0.5, None),
    ("poc_interferometry_step", "poc_interferometry_step/05_step_sweep.gif", 0.6, (0.53, 0.0, 1.0)),
    ("poc_polarization_specular", "poc_polarization_specular/03_separation_720.jpg", None, None),
    ("poc_photoelasticity", "poc_photoelasticity/03_load_and_isoclinics.gif", 0.45, (0.0, 0.0, 1.0)),
    ("poc_thermography_ndt", "poc_thermography_ndt/02_depth_map_720.jpg", None, None),
    ("poc_motion_magnification", "poc_motion_magnification/05_magnify_video.gif", 0.3, None),
    ("poc_table_tennis_bounce", "poc_table_tennis_bounce/01_drop_test.gif", 0.5, None),
    ("poc_compound_eye", "poc_compound_eye/02_compound_eye_superposition_720.jpg", None, None),
    ("poc_pegsim_insertion", "poc_pegsim_insertion/04_pegsim_insert_corrected.gif", 0.7, None),
    ("poc_air_hockey_intercept", "poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif", 1.0, (0.0, 0.0, 1.0)),
    ("poc_tacsim_elastic_membrane", "poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif", 1.0, (0.0, 0.0, 1.0)),
]


def _load(src: Path, frame: float | None) -> Image.Image:
    """静止図ならそのまま、GIF なら位置 `frame` のコマを RGB で返す。"""
    im = Image.open(src)
    if frame is None or getattr(im, "n_frames", 1) == 1:
        return im.convert("RGB")
    n = im.n_frames
    k = min(n - 1, max(0, round(frame * (n - 1))))
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        if i == k:
            return fr.convert("RGB")
    raise RuntimeError("frame %d not found in %s" % (k, src))


def _square(im: Image.Image, crop) -> Image.Image:
    """切り出し枠(無ければ中央の正方形)で切り、SIZE × SIZE に縮める。"""
    w, h = im.size
    if crop is None:
        s = min(w, h)
        box = ((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)
    else:
        s = round(crop[2] * h)                      # 一辺は高さに対する比(枠は必ず正方形)
        x0, y0 = round(crop[0] * w), round(crop[1] * h)
        x0, y0 = min(x0, w - s), min(y0, h - s)
        if s <= 0 or x0 < 0 or y0 < 0:
            raise ValueError("切り出し枠が画像に収まらない: %r (%dx%d)" % (crop, w, h))
        box = (x0, y0, x0 + s, y0 + s)
    return im.crop(box).resize((SIZE, SIZE), Image.LANCZOS)


def build() -> list[tuple[str, int]]:
    """全サムネイルを書き、(ファイル名, バイト数) を返す。元が無ければ例外で止める(黙って欠けさせない)。"""
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for pid, rel, frame, crop in SPEC:
        src = POC / rel
        if not src.is_file():
            raise FileNotFoundError("サムネイルの元が無い: %s" % src)
        th = _square(_load(src, frame), crop)
        dst = OUT / (pid + ".jpg")
        th.save(dst, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        out.append((dst.name, dst.stat().st_size))
    stale = sorted(p.name for p in OUT.glob("*.jpg") if p.stem not in {s[0] for s in SPEC})
    if stale:
        print("SPEC に無いサムネイルが残っている(消すこと): %s" % stale, file=sys.stderr)
    return out


def sheet(path: str) -> None:
    """確認用の一覧(6 列)を書く。"""
    files = [OUT / (s[0] + ".jpg") for s in SPEC]
    cols, pad = 6, 4
    rows = (len(files) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (SIZE + pad), rows * (SIZE + pad)), "white")
    for i, f in enumerate(files):
        sh.paste(Image.open(f), ((i % cols) * (SIZE + pad), (i // cols) * (SIZE + pad)))
    sh.save(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sheet", help="確認用の一覧画像の書き出し先")
    a = ap.parse_args(argv)
    res = build()
    for name, n in res:
        print("%-40s %7d B" % (name, n))
    print("total %d files, %d B" % (len(res), sum(n for _, n in res)))
    if a.sheet:
        sheet(os.path.abspath(a.sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
