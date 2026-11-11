---
op: gen_measure_rectangle2
dim: measure1d
category: caliper
in: 
out: measurehandle
halcon: gen_measure_rectangle2
gpu: なし
examples: [example_scratch_width, poc_barcode_1d, poc_battery_electrode_breathing, poc_calipers_under_illusion, poc_dimensional_inspection, poc_screw_thread_metrology, poc_solar_limb_darkening, poc_telecentric_metrology, poc_tree_ring_dendro, poc_water_level, poc_weld_bead_profile, poc_weld_radiograph_porosity]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# gen_measure_rectangle2 — MEASURE1D `caliper` op

- **データ種**: `なし` → `measurehandle`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_measure_rectangle2(row, col, phi, length1, length2, shape)` (実装を直接呼ぶなら `import measuring1d; measuring1d.gen_measure_rectangle2(row, col, phi, length1, length2, shape)`、台帳から引くなら `opsmeasure1d.get("gen_measure_rectangle2")`)
- **HALCON 相当**: `gen_measure_rectangle2`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

回転測定矩形(長軸 ``phi`` 方向に 1 px 間隔でプロファイルを取る)を定義
(gen_measure_rectangle2)。サンプル数 n = max(2, round(2*length1)+1)、始点は
中心から -(n-1)/2 px の位置。``length2`` は幅方向の平均化幅 [px]。

★長さの意味(2026-11-09 に実装へ合わせて明記。値は変えていない):
  * ``length1`` は**半長**(プロファイルは中心 ± length1)。HALCON の Length1 と同じ。
  * ``length2`` は**全幅**: ``measure_pos`` は法線方向の ``np.linspace(-w/2, w/2, max(2, w))``
    (``w = int(length2)``)の w 本を平均し、``w ≤ 1`` なら平均しない。HALCON の Length2 は
    **半高**(Half height of the rectangle、HALCON の reference)で、同じライブラリの
    ``gen_rectangle2_contour_xld`` も length2 を半幅(角が ±length2)として描く —— 同じ
    数字を渡すと、ここでは半分の幅しか平均しない。★HALCON の整数 offset −L2..+L2(2·L2+1 本)を
    そのまま作る length2 は無い: ``length2 = 2·L2 + 1`` を渡すと本数は 2·L2+1 だが、offset は
    ±(L2 + 0.5) の範囲に間隔 (2·L2+1)/(2·L2) で並ぶ(L2=2 → w=5 で −2.5, −1.25, 0, 1.25, 2.5)——
    整数でなく幅も 1 画素広い。辺が測定線に直交していれば平均の結果は近いが、幅方向に構造が
    あると別の矩形を測る。
  * w が偶数のとき標本は中心の行を通らない(w=2 は offset ±1 の 2 本だけ、w=4 は
    ±2, ±0.67)。中心を含めたいなら奇数の w。
★角の向き: プロファイルは ``(row + t·sin φ, col + t·cos φ)`` に進む。行が下向きの
画像座標で φ を時計回りに数える(φ = +π/2 は画面の下向き)。HALCON の Phi は水平からの
「数学的に正」の角(gen_rectangle2 の reference)で、行が下向きの画像では反時計回り
(φ = π/2 は上向き)と読める —— 符号が逆。HALCON の Phi を移すなら ``phi = −Phi``
(極性 positive/negative と並び順が HALCON と揃う)。★HALCON の実機での照合はしていない
(reference の文言からの読み)。ライブラリ内では ``gen_rectangle2_contour_xld`` も同じ +sin
で一貫している。

## 詳しい使い方ガイド

- [subpixel_measuring ファミリ ガイド](../guides/subpixel_measuring.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [example_scratch_width](../../../../examples/example_scratch_width.py) — `py -3.11 examples/example_scratch_width.py`
- [poc_barcode_1d](../../../../examples/poc_barcode_1d.py) — `py -3.11 examples/poc_barcode_1d.py`
- [poc_battery_electrode_breathing](../../../../examples/poc_battery_electrode_breathing.py) — `py -3.11 examples/poc_battery_electrode_breathing.py`
- [poc_calipers_under_illusion](../../../../examples/poc_calipers_under_illusion.py) — `py -3.11 examples/poc_calipers_under_illusion.py`
- [poc_dimensional_inspection](../../../../examples/poc_dimensional_inspection.py) — `py -3.11 examples/poc_dimensional_inspection.py`
- [poc_screw_thread_metrology](../../../../examples/poc_screw_thread_metrology.py) — `py -3.11 examples/poc_screw_thread_metrology.py`
- [poc_solar_limb_darkening](../../../../examples/poc_solar_limb_darkening.py) — `py -3.11 examples/poc_solar_limb_darkening.py`
- [poc_telecentric_metrology](../../../../examples/poc_telecentric_metrology.py) — `py -3.11 examples/poc_telecentric_metrology.py`
- [poc_tree_ring_dendro](../../../../examples/poc_tree_ring_dendro.py) — `py -3.11 examples/poc_tree_ring_dendro.py`
- [poc_water_level](../../../../examples/poc_water_level.py) — `py -3.11 examples/poc_water_level.py`
- [poc_weld_bead_profile](../../../../examples/poc_weld_bead_profile.py) — `py -3.11 examples/poc_weld_bead_profile.py`
- [poc_weld_radiograph_porosity](../../../../examples/poc_weld_radiograph_porosity.py) — `py -3.11 examples/poc_weld_radiograph_porosity.py`

## 型が繋がる次の op(`measurehandle` を入力に取れる)

[translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

## 同カテゴリ(`caliper`)

[gen_measure_arc](gen_measure_arc.md) · [translate_measure](translate_measure.md) · [measure_pos](measure_pos.md) · [measure_pairs](measure_pairs.md) · [fuzzy_measure_pairing](fuzzy_measure_pairing.md)

---
*Provenance: measuring1d.py — MEASURE1D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
