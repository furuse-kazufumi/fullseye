---
op: stroke_tone_error
dim: printpath
category: stroke
in: image2d × pairs
out: table
examples: [poc_one_stroke_epicycles]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# stroke_tone_error — PRINTPATH `stroke` op

- **データ種**: `image2d × pairs` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stroke_tone_error(image, points, pen_width=1.0, blur_sigma=3.0, gamma=1.0)` (実装を直接呼ぶなら `import printpath; printpath.stroke_tone_error(image, points, pen_width=1.0, blur_sigma=3.0, gamma=1.0)`、台帳から引くなら `opsprintpath.get("stroke_tone_error")`)

## 使い方

線を引いた結果の**濃淡**が目標とどれだけ違うか。→ ``table``

★これが一筆書きの**本当の目的関数**。「絵として似ている」を人の目に任せず、
ペン幅で描いて目の尺度にぼかし、目標の暗さと比べて数で返す。

返り値: dict
    "rms" / "max_abs" / "bias" —— 暗さの差(``[0, 1]`` の尺度)
    "corr" —— 目標の暗さと描いた暗さの相関(1 に近いほど濃淡を追えている)
    "ink_fraction" —— 紙に乗ったインクの面積率
    "target_darkness" —— 目標の平均暗さ(インク率と釣り合うべき量)
    "length_px" —— 線の長さ[px]

★**ペン幅は連続なノブ**(被覆率で塗る)。線が重ならない範囲では
``インク率 ≈ 線長 × ペン幅 / 画像の面積`` が成り立つので、目標の濃さに合う
ペン幅を **閉形式で解いてから**確かめられる:
``pen_width ≈ target_darkness × area / length_px``。

## 詳しい使い方ガイド

- [printpath ファミリ ガイド](../guides/printpath.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_one_stroke_epicycles](../../../../examples/poc_one_stroke_epicycles.py) — `py -3.11 examples/poc_one_stroke_epicycles.py`

## 型が繋がる次の op(`table` を入力に取れる)

[gcode_write](../gcode/gcode_write.md) · [gcode_extrusion_volume](../gcode/gcode_extrusion_volume.md) · [gcode_time_estimate](../gcode/gcode_time_estimate.md) · [gcode_layer_image](../gcode/gcode_layer_image.md) · [contours_to_gcode](../slice/contours_to_gcode.md)

## 同カテゴリ(`stroke`)

[stipple_points_from_image](stipple_points_from_image.md) · [stipple_energy](stipple_energy.md) · [stroke_tour_closed](stroke_tour_closed.md) · [mst_length](mst_length.md) · [stroke_resample_closed](stroke_resample_closed.md)

---
*Provenance: printpath.py — PRINTPATH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
