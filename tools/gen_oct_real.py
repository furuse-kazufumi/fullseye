# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""OCT の PoC の実測データ(CC BY 4.0 の 1 件)を、取得した原本から ``data/oct_real/`` の小さな npz に抜き出す。

    py -3.11 tools/gen_oct_real.py <原本の zip を展開したディレクトリ(その下に data/ がある)>

原本(このスクリプトは取得しない。手で落として展開する):
  University of Liverpool Research Data Catalogue, record 126 "AppliedOptics2016"
  <https://datacat.liverpool.ac.uk/126/>(ライセンス: Creative Commons Attribution 4.0)。
  Y. Dong, S. Lawman, Y. Zheng, D. Williams, J. Zhang, Y.-C. Shen, "Nondestructive analysis of automotive paints
  with spectral domain optical coherence tomography", *Applied Optics* 55(13), 3695–3700 (2016),
  doi:10.1364/AO.55.003695 の生データ(分光器の 2048 画素の干渉スペクトル、uint16、と画素ごとの波長)。

抜き出すもの(``data/oct_real/paint_sdoct_cc_by.npz``):
  * ``wavelength_nm`` —— 画素ごとの波長(原本の ``wavel``、797.24〜972.04 nm、等間隔でない)
  * ``spectra_<見本>`` —— 塗装見本 5 枚の B スキャンから A ラインを**等間隔に 100 本**(原本は 1600〜4000 本)
    見本の名前は原本のファイル名の番号だけを残す(V-D / VI-D / III-B / IV-C / II-A)。色の名前は README に書く。
  * ``glass_pair`` —— 軸分解能の原本(論文の図 3)の 200 本目と 201 本目(ガラス板と参照鏡)
改変(CC BY の表示義務として ``data/oct_real/README.md`` に書く): A ラインを間引いた、ファイル名を付け替えた。
値(uint16)と波長はそのまま。原本は untrusted として ``scipy.io.loadmat`` で読むだけで、何も実行しない。
"""
from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "oct_real", "paint_sdoct_cc_by.npz")

SAMPLES = {
    "V-D": "solid basecoat/black/BlackSampleV-D-2.mat",
    "VI-D": "solid basecoat/black/BlackSampleVI-D-2.mat",
    "III-B": "solid basecoat/onyx/OnyxSampleIII-B-2.mat",
    "IV-C": "solid basecoat/onyx/OnyxSampleIV-C-2.mat",
    "II-A": "solid basecoat/white/WhiteSampleII-A-2.mat",
}
N_LINES = 100


def main(src: str) -> None:
    import scipy.io as sio
    base = os.path.join(src, "data")
    out = {}
    wl = None
    for key, rel in SAMPLES.items():
        m = sio.loadmat(os.path.join(base, rel))
        sp = np.asarray(m["spectra"])
        w = np.asarray(m["wavel"], float).ravel()
        if sp.dtype != np.uint16 or sp.ndim != 2 or sp.shape[1] != w.size:
            raise SystemExit("unexpected layout in %s: %s %s" % (rel, sp.dtype, sp.shape))
        if wl is None:
            wl = w
        elif not np.array_equal(wl, w):
            raise SystemExit("wavelength calibration differs in %s" % rel)
        idx = np.linspace(0, sp.shape[0] - 1, N_LINES).round().astype(int)
        out["spectra_" + key] = sp[idx]
        out["lines_" + key] = idx.astype(np.int32)
        out["n_lines_" + key] = np.int32(sp.shape[0])
    g = sio.loadmat(os.path.join(base, "axial resolution", "OnyxSampleIII-B-1.mat"))
    out["glass_pair"] = np.asarray(g["spectra"])[[199, 200]]
    out["wavelength_nm"] = wl
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, **out)
    print("wrote %s (%.2f MB)" % (OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
