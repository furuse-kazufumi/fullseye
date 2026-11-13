---
op: frenet_frame
dim: 3d
category: curve
in: points
out: frame
gpu: なし
examples: [space_curve, torus_knot_curve]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# frenet_frame — 3D `curve` op

- **データ種**: `points` → `frame`
- **呼び出し**: `import fullseye as fs; fs.ledger.frenet_frame(curve)` (実装を直接呼ぶなら `import curve3d; curve3d.frenet_frame(curve)`、台帳から引くなら `ops3d.get("frenet_frame")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Frenet 標構(接線 T, 主法線 N, 陪法線 B)を各点で。→ (T, N, B) 各 (Npts,3) 単位ベクトル。

順序付き点列 (N,3) を index パラメータで ``np.gradient``(内部は中心差分、両端は
片側差分)して r', r'' を取り、
- T = r' / ‖r'‖
- N = (r'' − (r''·T) T) / ‖…‖(r'' の T 直交成分 = 曲率中心へ向く向き)
- B = T × N
を各点で計算する。r'' の T 直交成分の向きは再パラメータ化に不変なので、点間隔が
滑らかに変わる限り index パラメータで正しい向きが出る。

- 正規化に床は置かない(2026-11-05 敵対的検証 N1 の兄弟: 以前は分母に絶対値 1e-12 を
  足しており、尺度 1e-6 の曲線で N の長さが 0.998、1e-9 で 0.33 になった)。T は ‖r'‖ = 0 の点
  (同じ点の繰り返し)だけ 0 ベクトル。N は r'' の T 直交成分が ‖r'‖ の 1e-9 倍以下(1 標本あたりの
  曲がりが 1e-9 rad 未満 = 直線区間)の点で 0 ベクトル、B もそこで 0。変曲点の前後では N の向きが
  反転する。
- N<2 の点列は ``np.gradient`` が ``ValueError`` を出す。形状検証はそれ以外に無い。
- 両端 2 点は片側差分なので精度が落ちる。等間隔化(``resample_uniform``)や平滑
  (``fit_spline_curve``)を先に掛けると安定する。

曲率・捩率の数値そのものは ``curvature_torsion``、弧長は ``arc_length``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [space_curve](../../../../examples_3d/space_curve.py) — `py -3.11 examples_3d/space_curve.py`
- [torus_knot_curve](../../../../examples_3d/torus_knot_curve.py) — `py -3.11 examples_3d/torus_knot_curve.py`

## 型が繋がる次の op(`frame` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`curve`)

[curvature_torsion](curvature_torsion.md) · [arc_length](arc_length.md) · [resample_uniform](resample_uniform.md) · [fit_spline_curve](fit_spline_curve.md)

---
*Provenance: curve3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
