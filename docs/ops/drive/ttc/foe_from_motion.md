---
op: foe_from_motion
dim: drive
category: ttc
in: matrix × matrix
out: signal
examples: [poc_ttc_rss, poc_world_terrain]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# foe_from_motion — DRIVE `ttc` op

- **データ種**: `matrix × matrix` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.foe_from_motion(K, T_rel) -> 'np.ndarray'` (実装を直接呼ぶなら `import drivettc; drivettc.foe_from_motion(K, T_rel) -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("foe_from_motion")`)

## 使い方

拡大の中心(FoE)の画素 ``(col, row)``: 相対運動の並進 ``t`` を無限遠で投影した点。

``T_rel`` の回転が単位でないと FoE は定義されない(``ValueError``)。奥行き方向の並進が 0(純粋な横滑り)なら
``(nan, nan)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ttc_rss](../../../../examples/poc_ttc_rss.py) — `py -3.11 examples/poc_ttc_rss.py`
- [poc_world_terrain](../../../../examples/poc_world_terrain.py) — `py -3.11 examples/poc_world_terrain.py`

## 型が繋がる次の op(`signal` を入力に取れる)

—

## 同カテゴリ(`ttc`)

[relative_motion](relative_motion.md) · [flow_from_depth_motion](flow_from_depth_motion.md) · [ttc_truth](ttc_truth.md) · [ttc_from_flow](ttc_from_flow.md) · [ttc_from_scale](ttc_from_scale.md) · [ttc_from_range](ttc_from_range.md) · [label_extent](label_extent.md) · [foe_from_flow](foe_from_flow.md)

---
*Provenance: drivettc.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
