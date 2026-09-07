---
op: refine_translation_lk
dim: 3d
category: refine
in: voxel × voxel × position
out: position
gpu: true
examples: [refinement]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# refine_translation_lk — 3D `refine` op

- **データ種**: `voxel × voxel × position` → `position`
- **呼び出し**: `import fullseye as fs; fs.ledger.refine_translation_lk(scene, template, init_pos, device='cpu', iters=30, tol=0.0001)` (実装を直接呼ぶなら `import match3d; match3d.refine_translation_lk(scene, template, init_pos, device='cpu', iters=30, tol=0.0001)`、台帳から引くなら `ops3d.get("refine_translation_lk")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

Gauss-Newton 逆合成 Lucas-Kanade による 3D 並進サブボクセル精緻化。

粗マッチ(整数 NCC / Fourier-Mellin / Hough)が与えた整数初期位置 ``init_pos`` を
出発点に、SSD ``Σ|I(x+p) − T(x)|²`` を最小化してサブボクセル並進 ``p`` へ収束させる。

逆合成(inverse-compositional, Baker–Matthews)方式のため steepest-descent 画像
``SD = ∇T`` と Hessian ``H = Σ SDᵀSD`` を **反復前に一度だけ**前計算し、各反復は
「scene の trilinear ワープ + 残差 + 3×3 線形解 ``Δp = H⁻¹ Σ SDᵀ(I(x+p)−T)``」のみ。
並進の合成は ``p ← p − Δp``。純並進ワープでは ∂W/∂p=I なので SD=∇T がそのまま使える。

座標系: ``init_pos`` と戻り値はいずれも **テンプレート原点(corner, index 0,0,0)** が
scene のどの (dz,dy,dx) に載るか。``sobel3d`` / ``grid_sample`` の corner 規約に一致
(NCC(ncc_locate_3d)の中心規約とは T//2 だけ異なる点に注意)。

Parameters
----------
scene : (D,H,W) array_like
    探索対象ボリューム。
template : (Td,Th,Tw) array_like
    位置合わせするテンプレート(scene より小)。
init_pos : (3,) sequence
    整数初期位置 (dz,dy,dx) = テンプレート原点の scene 座標。
device : str
    "cpu" / "cuda" 等。device 非依存。
iters : int
    最大反復数。
tol : float
    ‖Δp‖ がこの値を下回ったら収束打ち切り。

Returns
-------
pos : (3,) np.ndarray(float64)
    精緻化されたサブボクセル位置 (dz,dy,dx)。

Notes
-----
- 滑らか(帯域制限)な密度場を仮定。整数初期値が真値の ±0.5〜1 voxel 内であれば
  通常 5〜8 反復で ‖err‖ < 0.05 voxel(低ノイズ時)。実測(独立 cubic-spline GT):
  ノイズ無し mean 0.008 / max 0.013 voxel(≈6 反復, ≈1.2ms/回)、NCC サブボクセル
  baseline(mean 0.56 voxel)を約60×改善。
- ``grad_scale=32`` は分離 sobel3d(導関数[-1,0,1]×平滑[1,2,1]²)の固定スケール
  (線形ランプで実測 32.0)。真の勾配へ正規化して Δp のスケールを正す。
- H には微小 Levenberg 正則化を加え、勾配の乏しい平坦テンプレートでの数値破綻を防ぐ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [refinement](../../../../examples_3d/refinement.py) — `py -3.11 examples_3d/refinement.py`

## 型が繋がる次の op(`position` を入力に取れる)

[refine_peak_newton](refine_peak_newton.md) · [refine_lm](refine_lm.md) · [fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`refine`)

[refine_peak_newton](refine_peak_newton.md) · [refine_lm](refine_lm.md) · [refine_rotation_z](refine_rotation_z.md) · [icp_point2point_3d](icp_point2point_3d.md) · [icp_point2plane](icp_point2plane.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
