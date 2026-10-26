#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""小惑星イトカワの形状モデル(Gaskell、Q=64 の頂点・面の版)を、repo に置く小さな npz にする(手で回す取り込み)。

    py -3.11 -I tools/import_itokawa_shape.py <取得した ver64q.tab のパス>

原本は NASA PDS Small Bodies Node の「Gaskell Itokawa Shape Model V1.1」(Hayabusa AMICA の画像 775 枚から
R. Gaskell が作った形)の ``data/vertex/ver64q.tab``(25,350 頂点・49,152 面、座標の単位は km、
body-fixed 座標: z 軸 = 自転の極、x 軸 = 経度 0 = 'black rock')。利用条件は PDS の書誌の頁で
Creative Commons CC0 1.0(パブリックドメインへの献呈)。原本は repo の外に取得し(取得物は untrusted として
専用の空ディレクトリに置く)、ここでは **数として読む** だけ(形・件数・索引の範囲・有限・閉じていることを検査し、
1 つでも合わなければ何も書かずに止める)。

出力 ``data/itokawa_shape/gaskell_q64.npz``:

* ``vertices_cm`` (25350, 3) int32 —— 座標 [cm](原本は km の小数 5 桁 = 1 cm 刻みなので **無損失**)。
* ``faces`` (49152, 3) int32 —— 0 始まりの頂点番号(原本は 1 始まり)。外向きの巻き。
* ``source_sha256`` —— 原本 ver64q.tab の SHA-256(下の ``SHA256_TAB`` と一致したときだけ書く)。

改変: 頂点番号を 0 始まりにし、座標を cm の整数にした(値は変えていない)。出典と利用条件は
``data/itokawa_shape/README.md``。生成物は tools/regen_all.py の EXCLUDED(原本が repo の外にあるため CI で作れない)。
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "itokawa_shape" / "gaskell_q64.npz"
#: 2026-10-25 に PDS SBN から取得した ver64q.tab(V1.1 の data/vertex)の SHA-256。
SHA256_TAB = "b472418ab40e7b7e8b29f085fa1d334038f69a2b3dd936a4e591a77ed3610c28"
N_VERT, N_FACE = 25350, 49152


def parse_tab(raw: bytes):
    """ver64q.tab のバイト列 → (vertices_cm int64 (N,3), faces int64 (M,3) 0 始まり)。合わなければ ValueError。"""
    text = raw.decode("ascii")                           # 数字・空白・改行以外が混ざれば UnicodeDecodeError
    lines = [ln for ln in text.splitlines() if ln.strip()]
    head = lines[0].split()
    if len(head) != 2 or int(head[0]) != N_VERT or int(head[1]) != N_FACE:
        raise ValueError("見出し行が 25350 49152 ではない: %r" % lines[0])
    if len(lines) != 1 + N_VERT + N_FACE:
        raise ValueError("行数が合わない: %d" % len(lines))
    V = np.empty((N_VERT, 3), dtype=np.int64)
    for k, ln in enumerate(lines[1:1 + N_VERT]):
        f = ln.split()
        if len(f) != 4 or int(f[0]) != k + 1:
            raise ValueError("頂点の行 %d が不正: %r" % (k + 1, ln))
        for j in range(3):
            s = f[1 + j]
            whole, _, frac = s.partition(".")
            if len(frac) != 5 or not (whole.lstrip("-").isdigit() and frac.isdigit()):
                raise ValueError("座標が小数 5 桁でない: %r" % s)
            v = int(whole.lstrip("-") or "0") * 100000 + int(frac)
            V[k, j] = -v if s.startswith("-") else v
    F = np.empty((N_FACE, 3), dtype=np.int64)
    for k, ln in enumerate(lines[1 + N_VERT:]):
        f = ln.split()
        if len(f) != 4 or int(f[0]) != k + 1:
            raise ValueError("面の行 %d が不正: %r" % (k + 1, ln))
        F[k] = [int(x) - 1 for x in f[1:]]
    if F.min() < 0 or F.max() >= N_VERT:
        raise ValueError("面の頂点番号が範囲外")
    if np.abs(V).max() > 10 ** 6:                         # 10 km を越える座標はイトカワ(長さ 0.5 km)ではない
        raise ValueError("座標が大きすぎる")
    return V, F


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tab", help="取得した ver64q.tab(PDS SBN の Gaskell Itokawa Shape Model V1.1、data/vertex)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    raw = Path(a.tab).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SHA256_TAB:
        print("SHA-256 が記録と違う(%s)—— 書かない" % sha, file=sys.stderr)
        return 2
    V, F = parse_tab(raw)
    sys.path.insert(0, str(ROOT))
    import polygrav                                      # noqa: E402  閉じていること・外向きの巻き(体積 > 0)を検査
    polygrav._check_closed(F, "import_itokawa_shape")
    vol = polygrav.polyhedron_gravity((V / 100.0, F), [[1.0e4, 0.0, 0.0]])["volume"]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, vertices_cm=V.astype(np.int32), faces=F.astype(np.int32), source_sha256=np.array(sha))
    print("wrote %s (%d bytes): %d vertices, %d faces, volume %.6e m^3"
          % (out, out.stat().st_size, V.shape[0], F.shape[0], vol))
    return 0


if __name__ == "__main__":
    sys.exit(main())
