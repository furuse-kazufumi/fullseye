---
op: tb_angular_spectrum_propagate
dim: 2d
category: typed
in: cimage
out: cimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# tb_angular_spectrum_propagate — 2D `typed` op

- **データ種**: `cimage` → `cimage`
- **呼び出し**: `fullseye.apply(img, "tb_angular_spectrum_propagate", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

型契約は `cimage → cimage`。挙動の言語説明は下記のファミリ使い方ガイドと実行可能サンプルを参照(ここでは推測を書かない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`cimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_cx_ifft](tb_cx_ifft.md) · [tb_cx_magnitude](tb_cx_magnitude.md) · [tb_cx_phase](tb_cx_phase.md) · [tb_cx_real](tb_cx_real.md) · [tb_cx_imag](tb_cx_imag.md) · [tb_cx_log_magnitude](tb_cx_log_magnitude.md) · [tb_cx_apply_transfer_function](tb_cx_apply_transfer_function.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_mls_smooth](tb_mls_smooth.md) · [tb_estimate_alpha](tb_estimate_alpha.md) · [tb_arc_length](tb_arc_length.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
