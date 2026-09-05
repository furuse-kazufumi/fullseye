---
op: piv_sample_at_windows
dim: piv
category: assess
in: flow2d
out: flow2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# piv_sample_at_windows — PIV `assess` op

- **データ種**: `flow2d` → `flow2d`
- **呼び出し**: `import pivops; pivops.piv_sample_at_windows(field, info)` (または `opspiv.get("piv_sample_at_windows")`)

## 使い方

画素ごとの場 ``(2, H, W)`` を窓中心の格子へ落とす(最近傍)。

真値は画素解像度で作られるが、PIV の出力は窓の格子に載る。**比べる前に
同じ格子へ持ってくる**必要があり、その持ってき方(最近傍か窓内平均か)で
誤差が変わる。ここは最近傍 —— 窓内平均にすると、勾配のある場で PIV 自身の
平滑化と区別がつかなくなる。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_error_stats](piv_error_stats.md) · [piv_peak_locking](piv_peak_locking.md)

## 同カテゴリ(`assess`)

[piv_error_stats](piv_error_stats.md) · [piv_peak_locking](piv_peak_locking.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
