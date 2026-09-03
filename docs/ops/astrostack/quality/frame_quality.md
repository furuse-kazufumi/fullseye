---
op: frame_quality
dim: astrostack
category: quality
in: image2d
out: table
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.5  # fullseye lib version this note was generated for
---

# frame_quality — ASTROSTACK `quality` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import astrostack; astrostack.frame_quality(image, threshold_sigma=5.0, max_stars=25, min_separation=3, psf_box=11, n_score_stars=5)` (または `opsastrostack.get("frame_quality")`)

## 使い方

1 枚の品質を数える —— 鋭さ・FWHM・背景・真円度、そして選別用の点。

lucky imaging の選別基準は歴史的に **「基準星のピーク強度」** である
(Law, Mackay & Baldwin, *Lucky imaging: high angular resolution imaging in
the visible from the ground*, A&A 446, 739 (2006))—— 大気が良い瞬間ほど
同じ総フラックスが少ない画素に集まるので、``ピーク / 総フラックス`` が
上がる。ここでもそれを採り、追尾の伸びを弾くために真円度を掛ける::

    score = median(roundness) * median(peak_fraction)

``peak_fraction`` は明るい方から ``n_score_stars`` 個の星について
``(ピーク画素 - 背景) / 開口フラックス``。**尺度に依らない**(露出時間や
ゲインを変えても動かない)ので、フレーム間の比較にそのまま使える。

``sharpness`` は別に、ラプラシアンの分散を画像の分散で割った古典的な
合焦指標(Pech-Pacheco et al., *Diatom autofocusing in brightfield
microscopy*, ICPR 2000)。星の数が変わると動くので**選別には使わない**が、
星が 1 つも無いフレームでも値が出る唯一の指標なので残してある。

Returns dict(``table`` 語彙)。キーは ``n_stars`` / ``background`` /
``noise_sigma`` / ``fwhm_px``(検出星の FWHM 中央値)/ ``roundness`` /
``peak_fraction`` / ``peak_snr`` / ``sharpness`` / ``score`` /
``total_flux``。星が 1 つも無いときは星由来の値が ``nan``、``score`` は
``0.0``(「選ばない」が正しい答えなので、``nan`` で並べ替えを壊さない)。

**Raises** ``ValueError``: 2-D でない / 非有限を含む / *n_score_stars* が
1 未満の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`quality`)

[lucky_select](lucky_select.md) · [noise_sigma](noise_sigma.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
