# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""hessian_numpy_chain — torch なしで ``voxel → hessian → voxel`` の鎖を通し、管と球を見分ける。

    py -3.11 examples/hessian_numpy_chain.py

【この例が解く問題】
``hessian`` 型(3-D Hessian の 6 成分)を受ける op —— ``hessian_determinant``(塊の検出)と
``hessian_vesselness``(Frangi 1998 の管らしさ)—— は、産み手が torch の ``hessian3d`` しか
無かったので、素の ``pip install fullseye``(numpy + scipy だけ)では入力が届かなかった。
``reprconv.voxel_to_hessian`` は numpy と scipy だけで同じ形(list の 6 本、各 (D,H,W) float32、
順 zz, yy, xx, zy, zx, yx)を返す。この例は **torch を import できない状態で** 鎖を通す。

呼び出し例:

    import fullseye as fs
    h = fs.ledger.voxel_to_hessian(vol, sigma=2.0)       # voxel -> hessian
    v = fs.ledger.hessian_vesselness(h)                   # hessian -> voxel, [0, 1]
    d = fs.ledger.hessian_determinant(h)                  # hessian -> voxel, 符号つき

【グラウンドトゥルース】すべて閉形式。どれか 1 つでも外れたら exit 1(数値は毎回印字する)。

1. 2 次多項式 ½xᵀAx + bᵀx + 620 → 内部で H = A(6 成分すべて、σ = 1.5)。明るさ 620 を足しても
   漏れない(標本化したガウス微分核のままだと Hxx が 1 → 0.95 に落ちる)。
2. ガウス球(s0 = 2.5)を σ = 1 で微分 → 中心の対角 = −(s0²/s²)^{3/2}/s²、s² = s0² + σ²。
3. 同じ球の ``hessian_determinant`` は中心で λ³(3 つの固有値が等しい負の値)。
4. z に沿う管(半径 2)の ``hessian_vesselness`` は軸上で 0.5 超、球の中心は閉形式の
   (1 − e^{−2})² e^{−2} ≈ 0.101(α = β = 0.5、Ra = Rb = 1)。
5. 管と球を並べた体積で、vesselness の高い voxel は管の側にだけ出る。
"""
from __future__ import annotations

import sys
from pathlib import Path

import importlib.abc


class _BlockTorch(importlib.abc.MetaPathFinder):
    """torch を import できない状態(素の pip install と同じ)を作る。

    ★2026-11-06: 以前は ``sys.modules["torch"] = None`` で塞いでいたが、scipy 1.17 の
    ``array_api_compat`` は ``sys.modules`` に名前があれば本物の torch とみなして
    ``Tensor`` を引き(``None.Tensor``)、torch の入った環境で AttributeError になった。
    import の段で ModuleNotFoundError を出す形なら、``sys.modules`` に名前が載らない。
    """

    def find_spec(self, name, path=None, target=None):
        if name == "torch" or name.startswith("torch."):
            raise ModuleNotFoundError("No module named 'torch' (blocked by this example)")
        return None


sys.meta_path.insert(0, _BlockTorch())

import numpy as np  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

import fullseye as fs  # noqa: E402

FAILED: list[str] = []
CHECKED: list[str] = []


def check(label: str, got: float, want: float, tol: float) -> None:
    ok = abs(got - want) <= tol
    CHECKED.append(label)
    print(f"  {'ok ' if ok else 'NG '} {label:52s} {got: .6g}  (真値 {want:.6g}, 許容 {tol:g})")
    if not ok:
        FAILED.append(label)


def main() -> int:
    L = fs.ledger
    n = 33
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(float) - (n - 1) / 2.0
    c = n // 2

    print("1. 2 次多項式 → H = A(σ = 1.5、内部)")
    A = np.array([[1.5, 0.3, -0.4], [0.3, -2.0, 0.7], [-0.4, 0.7, 0.8]])
    X = (z, y, x)
    f = 620.0 + 0.5 * X[0] - 1.0 * X[1] + 2.0 * X[2]
    for i in range(3):
        for j in range(3):
            f = f + 0.5 * A[i, j] * X[i] * X[j]
    h = L.voxel_to_hessian(f, sigma=1.5)
    inner = (slice(8, -8),) * 3
    want = (A[0, 0], A[1, 1], A[2, 2], A[0, 1], A[0, 2], A[1, 2])
    for name, comp, w in zip(("zz", "yy", "xx", "zy", "zx", "yx"), h, want):
        check(f"H{name} の内部の最大偏差 → 0", float(np.max(np.abs(comp[inner] - w))), 0.0, 2e-4)

    print("2-3. ガウス球(s0 = 2.5、σ = 1)")
    s0, sg = 2.5, 1.0
    ball = np.exp(-(x * x + y * y + z * z) / (2 * s0 * s0))
    hb = L.voxel_to_hessian(ball, sigma=sg)
    s2 = s0 * s0 + sg * sg
    lam = -((s0 * s0 / s2) ** 1.5) / s2
    check("中心の Hxx", float(hb[2][c, c, c]), lam, 0.02 * abs(lam))
    check("中心の det H = λ³", float(L.hessian_determinant(hb)[c, c, c]), lam ** 3, 0.06 * abs(lam ** 3))

    print("4. 管と球の vesselness")
    tube = np.exp(-(x * x + y * y) / (2 * 2.0 ** 2))
    vt = L.hessian_vesselness(L.voxel_to_hessian(tube, sigma=2.0))
    check("管の軸上の最小 vesselness(> 0.5)", float(vt[2:-2, c, c].min()), 1.0, 0.5)
    vb = L.hessian_vesselness(hb)
    check("球の中心の vesselness", float(vb[c, c, c]), (1 - np.exp(-2.0)) ** 2 * np.exp(-2.0), 0.01)

    print("5. 管と球を並べた体積")
    both = (np.exp(-((x - 7) ** 2 + y * y) / (2 * 2.0 ** 2))
            + np.exp(-((x + 8) ** 2 + y * y + z * z) / (2 * 3.0 ** 2)))
    vv = L.hessian_vesselness(L.voxel_to_hessian(both, sigma=2.0))
    hot = vv > 0.5
    n_hot = int(hot.sum())
    on_tube = int(hot[:, :, c:].sum())
    print(f"     vesselness > 0.5 の voxel {n_hot} 個、うち管の側(x > 0){on_tube} 個")
    check("vesselness > 0.5 のうち管の側の割合", on_tube / max(n_hot, 1), 1.0, 1e-12)
    check("vesselness > 0.5 の voxel がある(管の長さ 33 以上)", float(n_hot >= 33), 1.0, 0.0)

    print(f"\n{len(CHECKED)} 項目中 {len(CHECKED) - len(FAILED)} 項目が真値と一致"
          f"(torch は import していない: {'torch' not in sys.modules})")
    return 1 if FAILED or len(CHECKED) != 12 else 0


if __name__ == "__main__":
    sys.exit(main())
