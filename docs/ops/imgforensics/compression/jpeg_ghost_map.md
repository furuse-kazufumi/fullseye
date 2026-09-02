---
op: jpeg_ghost_map
dim: imgforensics
category: compression
in: image2d
out: images
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# jpeg_ghost_map — IMGFORENSICS `compression` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import imgforensics; imgforensics.jpeg_ghost_map(image, qualities=None, block: 'int' = 16) -> 'list'` (または `opsimgforensics.get("jpeg_ghost_map")`)

## 使い方

JPEG ゴースト(Farid 2009)。品質を掃引した **再圧縮残差の地図の列**。``images``。

ある領域が品質 ``q0`` で一度圧縮されていると、``q = q0`` で再圧縮したときに
その領域の差分が **谷** になる。画像全体が同じ ``q0`` なら谷は全面に出るが、
別の品質で圧縮された部分が貼られていると、**その領域だけ別の ``q`` で谷になる**。

返りは ``len(qualities)`` 本の ``(H, W)`` 地図(``block`` 角の箱平均で平滑化した
二乗差)。谷の位置を画素ごとに読むのは :func:`jpeg_ghost_quality`。

**Pillow 必須**(:class:`ImportError`)。理由は :func:`error_level_map` と同じ。

実測(``tests/test_imgforensics.py::test_jpeg_ghost_finds_the_pasted_quality``、
品質 92 の背景に品質 60 で圧縮した 64x64 を貼った 192x192、掃引 40..95 step 5):
貼った領域の谷は **品質 60**(真値 60、誤差 0)、背景の谷は **品質 95**。
背景が 92 ではなく 95 になるのは掃引が 5 刻みで 92 を含まないからで、
**谷は掃引した品質の中からしか出ない** —— 刻みより細かい品質は読めない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`images` を入力に取れる)

[sensor_fingerprint](../sensor/sensor_fingerprint.md) · [jpeg_ghost_quality](jpeg_ghost_quality.md)

## 同カテゴリ(`compression`)

[error_level_map](error_level_map.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_quality](jpeg_ghost_quality.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
