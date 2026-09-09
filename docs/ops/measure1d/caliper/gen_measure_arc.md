---
op: gen_measure_arc
dim: measure1d
category: caliper
in: 
out: measurehandle
examples: [poc_dimensional_inspection]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# gen_measure_arc — MEASURE1D `caliper` op

- **データ種**: `なし` → `measurehandle`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_measure_arc(center_row, center_col, radius, angle_start, angle_extent, width, shape)` (実装を直接呼ぶなら `import measuring1d; measuring1d.gen_measure_arc(center_row, center_col, radius, angle_start, angle_extent, width, shape)`、台帳から引くなら `opsmeasure1d.get("gen_measure_arc")`)

## 使い方

測定弧(円周方向に ≈1 px 間隔でプロファイルを取る)を定義(gen_measure_arc)。
サンプル数 n = round(|angle_extent|*radius)+1、``spacing`` = 弧長/(n-1)。

弧上のサンプル点は ``row = center_row + radius sin(θ)``、
``col = center_col + radius cos(θ)``、``θ = angle_start + linspace(0, angle_extent, n)``。
角度は **ラジアン**で、col 軸(x)から row 軸(画像下向き)へ回る向きが正。
``angle_extent`` が負なら逆回りに進み、``measure_pos`` の ``pos`` / ``dist`` は
その進行方向に沿って数える。

- ``radius``: [px]。``n = max(2, round(|angle_extent| * radius) + 1)`` なので、
  半径や角度幅が小さすぎるとサンプル 2 点・``spacing`` が弧長そのものになる。
  ``radius = 0`` は ``spacing = 0`` になり後段の微分で破綻する(ここでは検証しない)。
- ``width``: 幅方向(法線)の平均化幅 [px]。``int`` に切られ、1 以下なら平均なし。
- ``shape``: 画像の ``(H, W)``。dict に保存されるだけで、範囲外は
  ``measure_pos`` 側が最近傍で外挿する(例外は出ない)。
- 返り値: ``{"type": "arc", "rows", "cols", "width", "shape", "spacing", "center",
  "radius", "angles"}`` の dict(``measurehandle`` 型)。

``measure_pos`` / ``measure_pairs`` / ``fuzzy_measure_pairing`` に渡す。直線なら
``gen_measure_rectangle2``。位置決め後は ``translate_measure`` で動かす。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`

## 型が繋がる次の op(`measurehandle` を入力に取れる)

[translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

## 同カテゴリ(`caliper`)

[gen_measure_rectangle2](gen_measure_rectangle2.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
