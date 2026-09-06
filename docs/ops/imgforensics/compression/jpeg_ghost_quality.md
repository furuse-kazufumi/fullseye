---
op: jpeg_ghost_quality
dim: imgforensics
category: compression
in: images
out: image2d
examples: [image_forensics_audit, poc_forensics_roc]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# jpeg_ghost_quality — IMGFORENSICS `compression` op

- **データ種**: `images` → `image2d`
- **呼び出し**: `import imgforensics; imgforensics.jpeg_ghost_quality(ghosts, qualities=None) -> 'np.ndarray'` (または `opsimgforensics.get("jpeg_ghost_quality")`)

## 使い方

ゴースト地図の列 → 画素ごとに **残差が最小になる品質** の地図。``image2d``。

``qualities`` を省くと :func:`jpeg_ghost_map` の既定(40..95 step 5)を仮定する
—— **枚数が合わなければ :class:`ValueError`**(添字と品質がずれた地図を返さない)。

返りは品質そのものを画素値に持つ ``(H, W)`` なので、値域は [0, 1] ではない。
表示するときは正規化すること(この op は数値を返すのであって絵を返さない)。

★ **合成後に一度でも保存すると、この argmin は使えない。** 2026-09-06 に
測った。背景 q92・素材 q60 で 32x32 を貼った 128x128 で:

====================  ==================  ================
条件                  貼付部の最頻品質    背景の最頻品質
====================  ==================  ================
合成後に保存しない            **60**(正解)              95
合成後に q95 で保存           **95**(背景と同じ)         95
====================  ==================  ================

理由は掃引の残差が品質に対して**単調減少**すること —— 最後の保存品質が
掃引の上端にあると、``argmin`` は全画素でそこに張り付く(実測: 保存後の
残差平均は 230.7 → 5.9e-02 と一直線に下がる)。実運用の改竄は必ず保存を
経るので、**この読み出しは実画像では定数地図になる**。既存テスト
``test_jpeg_ghost_finds_the_pasted_quality`` が通るのは、合成後に一度も
保存していないからである(それ自体は正しい単体テストで、`argmin` の実装は
間違っていない —— 読み出し方が現場に合わない)。

**代わりに使うもの**: 掃引方向の残差曲線の**谷の深さ**(局所的な凹み)。
同じ実験で画素ごとの ROC を取ると、argmin 読み出しは AUC 0.500(乱数と同じ)、
谷の深さ読み出しは **AUC 0.997 / 偽陽性 1 % で検出率 0.944** だった
(``examples/poc_forensics_roc.py``)。それでも全体を q60 で保存し直すと
0.475 まで落ちる —— JPEG ゴーストは後処理に弱い、というのが正しい要約。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`
- [poc_forensics_roc](../../../../examples/poc_forensics_roc.py) — `py -3.11 examples/poc_forensics_roc.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[perceptual_hash](../hash/perceptual_hash.md) · [fingerprint_correlate](../sensor/fingerprint_correlate.md) · [error_level_map](error_level_map.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md) · [noise_inconsistency_map](../noise/noise_inconsistency_map.md) · [copy_move_regions](../copy_move/copy_move_regions.md) · [watermark_embed](../watermark/watermark_embed.md)

## 同カテゴリ(`compression`)

[error_level_map](error_level_map.md) · [jpeg_quality_estimate](jpeg_quality_estimate.md) · [jpeg_ghost_map](jpeg_ghost_map.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
