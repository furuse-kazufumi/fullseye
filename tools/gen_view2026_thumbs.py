#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の案内ページ(`docs/view2026/`)のサムネイルを作る。

    py -3.11 tools/gen_view2026_thumbs.py            # thumbs/ を作り直す
    py -3.11 tools/gen_view2026_thumbs.py --sheet X  # 見どころのサムネイルの一覧画像を X に書く(repo の外に)

論文の QR コードからスマートフォンで開かれるページなので、最初に読み込むのは
**サムネイルだけ**にする。動画・GIF・原寸の図はタイルを押したときに初めて読む —— それらは
各 PoC がすでに `docs/articles/assets/poc/` に出している既存の図で、ここでは複製しない。

* 見どころ(``thumbs/<id>.jpg``、320 px): ``SPEC`` に手で選んだコマと切り出し枠。
* ぜんぶ見る(``thumbs/all/<id>.jpg``、200 px・25 KB 以下): ``docs/view2026/exhibits.json``
  の ``all`` を全部。元は ``thumb_src``(PoC の図の名前)か ``thumb_path``(docs/ からの相対)、
  GIF なら真ん中のコマ、切り出しは中央の正方形。
* シリーズの入口(``thumbs/series_*.gif``): 元の GIF からコマを等間隔に抜いた動くサムネイル。
  ``series_humanoid.gif`` だけは元が著者の別 repo(ヒューマノイド運動会の素材)にあるので
  ここでは作らず、在ることだけを確かめる。

切り出し枠は (左, 上, 一辺) で、左は幅に対する比、上と一辺は高さに対する比(正方形を歪めずに切る)。
数値はここに書かない(ページの数値は各 PoC の図の説明と実行ログが正本)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
POC = DOCS / "articles" / "assets" / "poc"
OUT = DOCS / "view2026" / "thumbs"
OUT_ALL = OUT / "all"
DATA = DOCS / "view2026" / "exhibits.json"
SIZE, SIZE_ALL = 320, 200
QUALITY, QUALITY_ALL = 80, 72
LIMIT_ALL = 25_000

#: 見どころ: (id, 元(docs/ からの相対), コマの位置 or None, 切り出し枠 or None)
_P = "articles/assets/poc/"
SPEC = [
    ("poc_real_defect_floor", _P + "poc_real_defect_floor/02_defect_floor_sweep.gif", 0.85, (0.02, 0.0, 1.0)),
    ("poc_active_contours", _P + "poc_active_contours/06_u_shape_snakes.gif", 1.0, (0.5, 0.0, 1.0)),
    ("poc_dic_strain", _P + "poc_dic_strain/05_tensile_ramp.gif", 1.0, (0.33, 0.0, 0.55)),
    ("poc_focus_stacking", _P + "poc_focus_stacking/05_focus_sweep.gif", 1.0, (0.5, 0.04, 0.55)),
    ("poc_registration_basin", _P + "poc_registration_basin/05_icp_basin_iterations.gif", 0.5, (0.335, 0.0, 0.47)),
    ("poc_stockpile_volume", _P + "poc_stockpile_volume/07_scan_orbit.gif", 0.3, None),
    ("poc_ct_fidelity", _P + "poc_ct_fidelity/01_recon_sweep_720.jpg", None, None),
    ("poc_ct_void_morphology", _P + "poc_ct_void_morphology/13_section_sweep.gif", 0.5, None),
    ("poc_interferometry_step", _P + "poc_interferometry_step/05_step_sweep.gif", 0.6, (0.53, 0.0, 1.0)),
    ("poc_polarization_specular", _P + "poc_polarization_specular/03_separation_720.jpg", None, None),
    ("poc_photoelasticity", _P + "poc_photoelasticity/03_load_and_isoclinics.gif", 0.45, (0.0, 0.0, 1.0)),
    ("poc_thermography_ndt", _P + "poc_thermography_ndt/02_depth_map_720.jpg", None, None),
    ("poc_motion_magnification", _P + "poc_motion_magnification/05_magnify_video.gif", 0.3, None),
    ("poc_table_tennis_bounce", _P + "poc_table_tennis_bounce/01_drop_test.gif", 0.5, None),
    ("poc_compound_eye", _P + "poc_compound_eye/02_compound_eye_superposition_720.jpg", None, None),
    ("poc_pegsim_insertion", _P + "poc_pegsim_insertion/04_pegsim_insert_corrected.gif", 0.7, None),
    ("poc_air_hockey_intercept", _P + "poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif", 1.0, (0.0, 0.0, 1.0)),
    ("poc_tacsim_elastic_membrane", _P + "poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif", 1.0, (0.0, 0.0, 1.0)),
    ("poc_table_tennis_spin", _P + "poc_table_tennis_spin/01_side_three_serves.gif", 0.9, (0.42, 0.0, 1.0)),
    ("poc_table_tennis_rally_loop", _P + "poc_table_tennis_rally_loop/02_height_misread.gif", 0.9, (0.42, 0.0, 1.0)),
    ("poc_driving_traffic", _P + "poc_driving_traffic/01_dashcam_occlusion.gif", 0.62, (0.05, 0.0, 1.0)),
    ("poc_driving_crossing", _P + "poc_driving_crossing/01_crossing_dashcam.gif", 0.45, (0.35, 0.0, 1.0)),
    ("poc_driving_pass", _P + "poc_driving_pass/03_mirror_tjunction.gif", 0.6, (0.0, 0.0, 1.0)),
    ("poc_ttc_rss", _P + "poc_ttc_rss/06_approach_gif.gif", 0.3, None),
    ("poc_eye_to_brain", _P + "poc_eye_to_brain/01_eye_sweep.gif", 0.5, None),
    ("poc_malecns_activity_wave", _P + "poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif", 0.6, (0.0, 0.0, 1.0)),
    ("poc_microns_brain_wave", _P + "poc_microns_brain_wave/04_wave_on_wiring.gif", 0.5, None),
    ("evis_stereo_depth", "articles/assets/evis_stereo_fullseye_still.png", None, (0.0, 0.0, 1.0)),
    ("evis_bean_track", "articles/assets/evis_bean_track_fullseye_still.png", None, (0.5, 0.0, 1.0)),
]

#: シリーズの入口の動くサムネイル。(名前, 元の GIF(docs/ からの相対), コマ数, 幅)。64 色に減らす。
SERIES_GIF = [
    ("series_table_tennis", _P + "poc_table_tennis_spin/01_side_three_serves.gif", 10, 360),
    ("series_driving", _P + "poc_driving_crossing/01_crossing_dashcam.gif", 10, 360),
    ("series_connectome", _P + "poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif", 6, 320),
]
#: 紙面の計測館は 1 本の動画が無いので、見どころの最初の 18 枚を 3 枚ずつ並べて巡回させる。
SERIES_MUSEUM = "series_museum"
MUSEUM_IDS = [s[0] for s in SPEC[:18]]
#: repo の外が元なので作らない(在ることだけ確かめる)。
SERIES_EXTERNAL = ["series_humanoid.gif"]
SERIES_COLORS = 64
SERIES_MS = 700


def _load(src: Path, frame: float | None) -> Image.Image:
    """静止図ならそのまま、GIF なら位置 `frame` のコマを RGB で返す。"""
    im = Image.open(src)
    n = getattr(im, "n_frames", 1)
    if frame is None or n == 1:
        return im.convert("RGB")
    k = min(n - 1, max(0, round(frame * (n - 1))))
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        if i == k:
            return fr.convert("RGB")
    raise RuntimeError("frame %d not found in %s" % (k, src))


def _square(im: Image.Image, crop, size: int) -> Image.Image:
    """切り出し枠(無ければ中央の正方形)で切り、size × size に縮める。"""
    w, h = im.size
    if crop is None:
        s = min(w, h)
        box = ((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)
    else:
        s = round(crop[2] * h)
        x0, y0 = min(round(crop[0] * w), w - s), min(round(crop[1] * h), h - s)
        if s <= 0 or x0 < 0 or y0 < 0:
            raise ValueError("切り出し枠が画像に収まらない: %r (%dx%d)" % (crop, w, h))
        box = (x0, y0, x0 + s, y0 + s)
    return im.crop(box).resize((size, size), Image.LANCZOS)


def _save_jpg(im: Image.Image, dst: Path, quality: int, limit: int | None = None) -> int:
    """JPEG で書く。limit を超えたら品質を下げて書き直す(下限 40)。"""
    q = quality
    while True:
        im.save(dst, "JPEG", quality=q, optimize=True, progressive=True)
        n = dst.stat().st_size
        if limit is None or n <= limit or q <= 40:
            return n
        q -= 8


def build() -> list[tuple[str, int]]:
    """見どころのサムネイルを書く。元が無ければ例外で止める(黙って欠けさせない)。"""
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for pid, rel, frame, crop in SPEC:
        src = DOCS / rel
        if not src.is_file():
            raise FileNotFoundError("サムネイルの元が無い: %s" % src)
        dst = OUT / (pid + ".jpg")
        out.append((dst.name, _save_jpg(_square(_load(src, frame), crop, SIZE), dst, QUALITY)))
    return out


def _all_source(e: dict) -> Path:
    if e.get("thumb_path"):
        return DOCS / e["thumb_path"]
    return POC / e["id"] / e["thumb_src"]


def build_all() -> list[tuple[str, int]]:
    """ぜんぶ見るのサムネイル(exhibits.json の all を全部)。"""
    OUT_ALL.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA.read_text(encoding="utf-8"))
    out = []
    for e in data["all"]:
        src = _all_source(e)
        if not src.is_file():
            raise FileNotFoundError("サムネイルの元が無い: %s" % src)
        dst = OUT_ALL / (e["id"] + ".jpg")
        out.append(("all/" + dst.name, _save_jpg(_square(_load(src, 0.5), None, SIZE_ALL), dst, QUALITY_ALL, LIMIT_ALL)))
    keep = {e["id"] for e in data["all"]}
    for p in OUT_ALL.glob("*.jpg"):
        if p.stem not in keep:
            p.unlink()                      # 台帳から消えた展示のサムネイルは残さない
    return out


def _gif(frames: list, dst: Path, ms: int = SERIES_MS) -> int:
    """RGB のコマ列を、共通パレット(SERIES_COLORS 色)の繰り返す GIF に書く。"""
    pal = frames[len(frames) // 2].quantize(SERIES_COLORS, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(dst, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True, disposal=1)
    return dst.stat().st_size


def build_series() -> list[tuple[str, int]]:
    """シリーズの入口の動くサムネイル(GIF)を書く。"""
    out = []
    for name, rel, n, width in SERIES_GIF:
        src = DOCS / rel
        if not src.is_file():
            raise FileNotFoundError("シリーズのサムネイルの元が無い: %s" % src)
        im = Image.open(src)
        total = im.n_frames
        want = {round(i * (total - 1) / (n - 1)) for i in range(n)}
        frames = []
        for i, fr in enumerate(ImageSequence.Iterator(im)):
            if i in want:
                f = fr.convert("RGB")
                frames.append(f.resize((width, round(f.height * width / f.width)), Image.LANCZOS))
        out.append((name + ".gif", _gif(frames, OUT / (name + ".gif"))))
    tiles = [Image.open(OUT / (pid + ".jpg")).convert("RGB").resize((120, 120), Image.LANCZOS) for pid in MUSEUM_IDS]
    frames = []
    for k in range(0, len(tiles), 3):
        f = Image.new("RGB", (360, 120), "white")
        for j, t in enumerate(tiles[k:k + 3]):
            f.paste(t, (j * 120, 0))
        frames.append(f)
    out.append((SERIES_MUSEUM + ".gif", _gif(frames, OUT / (SERIES_MUSEUM + ".gif"), ms=1200)))
    for name in SERIES_EXTERNAL:
        p = OUT / name
        if not p.is_file():
            raise FileNotFoundError("repo の外が元のサムネイルが無い(生成器では作れない): %s" % p)
        out.append((name, p.stat().st_size))
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
    res = build() + build_series()
    res_all = build_all()
    keep = {s[0] + ".jpg" for s in SPEC}
    stale = sorted(p.name for p in OUT.glob("*.jpg") if p.name not in keep)
    if stale:
        print("SPEC に無いサムネイルが残っている(消すこと): %s" % stale, file=sys.stderr)
    for name, n in res:
        print("%-40s %7d B" % (name, n))
    big = [(n, b) for n, b in res_all if b > LIMIT_ALL]
    print("highlights+series %d files, %d B" % (len(res), sum(n for _, n in res)))
    print("all %d files, %d B (max %d B)%s" % (len(res_all), sum(n for _, n in res_all), max(n for _, n in res_all),
                                              " OVER: %s" % big if big else ""))
    if a.sheet:
        sheet(os.path.abspath(a.sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
