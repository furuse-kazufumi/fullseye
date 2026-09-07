---
op: curvature_torsion
dim: 3d
category: curve
in: points
out: pairs
examples: [space_curve, torus_knot_curve]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# curvature_torsion — 3D `curve` op

- **データ種**: `points` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.curvature_torsion(curve)` (実装を直接呼ぶなら `import curve3d; curve3d.curvature_torsion(curve)`、台帳から引くなら `ops3d.get("curvature_torsion")`)
- **台帳経由の戻り値**: `fullseye.ledger.curvature_torsion(...)` は**宣言 out 型 `pairs` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.curvature_torsion.raw(...)`、または `curve3d.curvature_torsion` を直接呼ぶ。
  - 本体の返り: `(kappa,tau) → (N,2) pairs`

## 使い方

各点の曲率 κ と捩率 τ(再パラメータ化不変な閉形式)。→ (kappa (N,), tau (N,))。

座標の一様スケール s に対し κ→κ/s, τ→τ/s と正しくスケールする。0 割り防止の epsilon は
**相対化**する: 絶対 1e-12 は cross_norm²(~s⁴)・r1_norm³(~s³)を小座標スケールで支配し、
κ/τ を破壊するため、代表スケール L=median‖r'‖(座標スケール s に線形)で各分母と同次元に
正規化した相対 eps を使う。これは曲線を L で正規化してから計算し 1/L で戻すのと厳密に等価。

計算は順序付き点列 (N,3) を index パラメータで ``np.gradient`` 3 回(中心差分、両端は
片側差分)した r', r'', r''' から
- κ = ‖r'×r''‖ / ‖r'‖³
- τ = (r'×r'')·r''' / ‖r'×r''‖²
で求める。単位は κ・τ とも 1/座標単位。τ の符号は右手系の螺旋
(a cosθ, a sinθ, bθ), b>0 で正。直線区間(‖r'×r''‖≈0)では κ≈0、τ は分母が eps だけに
なるため値は信頼できない。

- ``ValueError``: 全点が重なり median‖r'‖ が 0 または非有限のとき。
- 点間隔が急に変わる箇所は数値微分が乱れるので、先に ``resample_uniform`` で等間隔化
  するか ``fit_spline_curve`` で平滑化してから渡す。両端 2 点は片側差分で精度が落ちる。
- N<2 は ``np.gradient`` が ``ValueError``。形状 (N,3) の検証はしていない。

標構(T,N,B)が要るなら ``frenet_frame``、弧長 ds は ``arc_length`` から取る。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_curve](../../../../examples_3d/space_curve.py) — `py -3.11 examples_3d/space_curve.py`
- [torus_knot_curve](../../../../examples_3d/torus_knot_curve.py) — `py -3.11 examples_3d/torus_knot_curve.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curve`)

[frenet_frame](frenet_frame.md) · [arc_length](arc_length.md) · [resample_uniform](resample_uniform.md) · [fit_spline_curve](fit_spline_curve.md)

---
*Provenance: curve3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
