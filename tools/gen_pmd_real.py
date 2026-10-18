# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""デフレクトメトリの PoC の実データ(CC0 の 1 件)を、取得した原本から ``data/pmd_real/`` の小さな npz に抜き出す。

    py -3.11 tools/gen_pmd_real.py <原本のディレクトリ(image_0001.tif … と hammer_force.txt / hammer_time.txt)>

原本(このスクリプトは取得しない。手で落とす):
  R. Kaufmann, S. N. Olufsen, E. Fagerholt (NTNU), "Experimental data for force reconstruction using impact hammer
  and deflectometry", DataverseNO, doi:10.18710/TKS7SI(ライセンス: CC0 1.0)。鏡面に磨いた 300 mm 角・厚さ 4.95 mm の
  鋼板を裏からハンマーで叩き、板に映った十字格子を 75 kHz で撮った 512 × 512 の 16 bit TIFF 280 枚(image_0001〜0030 が
  打撃の前、image_0150〜0400 が打撃の前後、0384 は原本に無い)と、ハンマーの先の力の記録(51.2 kHz)。

抜き出すもの(``data/pmd_real/hammer_grid_cc0.npz``):
  * ``ref_mean_x8`` —— 打撃の前の 30 枚の平均 × 8(uint16)、切り出し 行 0:512 × 列 30:460
  * ``frame_hammer_peak`` / ``frame_max_slope`` —— ハンマーの峰の駒(image_0283)と、たわみが最大の駒の同じ切り出し(原本の値のまま)
  * ``rec_*`` —— 原本 280 枚の全解析(``examples/poc_phase_measuring_deflectometry.analyze_hammer_dataset``)の記録:
    力の時系列、ハンマーの記録、対照の窓、選んだ窓、探針の結果。CI は原本が無いので、この記録を読んで印字する。
改変(``data/pmd_real/README.md`` に書く): 切り出した、平均した、解析した値を足した。原本は untrusted として PIL で
画素を読むだけで、何も実行しない。
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "pmd_real", "hammer_grid_cc0.npz")
ROWS = (0, 512)
COLS = (30, 460)


def _poc():
    spec = importlib.util.spec_from_file_location(
        "poc_pmd", os.path.join(ROOT, "examples", "poc_phase_measuring_deflectometry.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(src: str) -> None:
    P = _poc()
    res = P.analyze_hammer_dataset(src)
    sl = (slice(*ROWS), slice(*COLS))
    ref = np.mean([P._load_tif(os.path.join(src, "image_%04d.tif" % f)) for f in P.REF_FRAMES], axis=0)
    t_peak = float(res["hammer_t"][int(np.argmax(res["hammer_f"]))])
    f_hammer = int(round(P.T0_FRAME + t_peak * P.FPS))
    out = {
        "crop_origin": np.asarray([ROWS[0], COLS[0]], np.int32),
        "ref_mean_x8": np.round(ref[sl] * 8.0).astype(np.uint16),
        "frame_hammer_peak": P._load_tif(os.path.join(src, "image_%04d.tif" % f_hammer))[sl].astype(np.uint16),
        "frame_max_slope": P._load_tif(os.path.join(src, "image_%04d.tif" % res["frame_peak"]))[sl].astype(np.uint16),
        "frame_numbers": np.asarray([f_hammer, res["frame_peak"]], np.int32),
    }
    for k in ("t", "F", "hammer_raw", "hammer_smooth", "null_F", "null_centres", "floor", "half", "m", "impact",
              "crop", "jump_x", "jump_y", "pre_std", "sizes", "strides", "direct_wrong", "candidates", "frame_peak"):
        out["rec_" + k] = np.asarray(res[k])
    out["rec_mode"] = np.asarray(P.ZERO_MODES.index(res["mode"]), np.int32)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, **out)
    print("wrote %s (%d bytes)" % (OUT, os.path.getsize(OUT)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
