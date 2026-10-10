---
op: symmetric_peg_shape
dim: drive
category: pegtactile
in: text
out: image2d
examples: [poc_peg_insertion_tactile]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# symmetric_peg_shape — DRIVE `pegtactile` op

- **データ種**: `text` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.symmetric_peg_shape(name: 'str', size: 'int' = 160, radius: 'float' = 50.0, angle: 'float' = 0.0, centre=None, ss: 'int' = 8) -> 'np.ndarray'` (実装を直接呼ぶなら `import pegtactile; pegtactile.symmetric_peg_shape(name: 'str', size: 'int' = 160, radius: 'float' = 50.0, angle: 'float' = 0.0, centre=None, ss: 'int' = 8) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("symmetric_peg_shape")`)

## 使い方

ペグの断面(真値つきの合成、反エイリアスの被覆率 0..1、(size, size)): 円・正三角形・正方形・正六角形(外接円半径 ``radius``
[px])・キー付きの円(D カット: 円の一部を弦で切る、n = 1)。``angle`` [rad] だけ**形を回して描く**(画像を回すと補間が入る)。
``centre`` = (col, row)、``ss`` = 画素あたりの副標本の 1 辺。**Raises** ValueError: 未知の形、size < 16、radius ≤ 0、ss < 1。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_peg_insertion_tactile](../../../../examples/poc_peg_insertion_tactile.py) — `py -3.11 examples/poc_peg_insertion_tactile.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`pegtactile`)

[pad_params](pad_params.md) · [pad_context](pad_context.md) · [peg_wrench_to_pad_loads](peg_wrench_to_pad_loads.md) · [pad_loads_to_peg_wrench](pad_loads_to_peg_wrench.md) · [pad_shear_asymmetry](pad_shear_asymmetry.md) · [pad_marker_displacement](pad_marker_displacement.md) · [pad_tactile_frame](pad_tactile_frame.md) · [pad_tactile_read](pad_tactile_read.md)

---
*Provenance: pegtactile.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
