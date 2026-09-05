---
op: fingerprint_strength_map
dim: imgforensics
category: sensor
in: fingerprint
out: image2d
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# fingerprint_strength_map — IMGFORENSICS `sensor` op

- **データ種**: `fingerprint` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.fingerprint_strength_map(fingerprint, block: 'int' = 16) -> 'np.ndarray'` (または `opsimgforensics.get("fingerprint_strength_map")`)

## 使い方

指紋の **ブロックごとの実効強度**(標準偏差)を並べた地図。``image2d``。

PRNU は飽和した画素と真っ暗な画素では出ない(乗法的な欠陥なので信号が要る)。
この地図は「**指紋がどこで何も言えないか**」を見るためのもので、値が低い領域の
照合結果は弱い。``block`` 角の非重複ブロックごとの標準偏差を、元の ``(H, W)`` へ
ブロック定数で戻して返す(端は端のブロックの値で埋める)。

実測(``tests/test_imgforensics.py::test_strength_map_marks_the_saturated_half``、
128x128 の左半分だけを飽和させた 8 枚から指紋を作る):飽和側の平均強度
**0.075** に対し通常側 **1.409** = **18.8 倍**。左半分では PRNU が乗る余地が
無い(乗法的な欠陥なので信号が要る)ことがそのまま出ている。

これは ``fingerprint`` 語彙の **出口** でもある(袋小路を作らないため)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](fingerprint_correlate.md) · [error_level_map](../compression/error_level_map.md) · [jpeg_quality_estimate](../compression/jpeg_quality_estimate.md) · [jpeg_ghost_map](../compression/jpeg_ghost_map.md) · [noise_inconsistency_map](../noise/noise_inconsistency_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_embed](../watermark/watermark_embed.md)

## 同カテゴリ(`sensor`)

[sensor_fingerprint](sensor_fingerprint.md) · [fingerprint_correlate](fingerprint_correlate.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
