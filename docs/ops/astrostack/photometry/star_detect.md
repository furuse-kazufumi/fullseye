---
op: star_detect
dim: astrostack
category: photometry
in: image2d
out: keypoints
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# star_detect — ASTROSTACK `photometry` op

- **データ種**: `image2d` → `keypoints`
- **呼び出し**: `import astrostack; astrostack.star_detect(image, threshold_sigma=5.0, min_separation=3, max_stars=200, edge_margin=None, centroid_box=None, method='mad')` (または `opsastrostack.get("star_detect")`)

## 使い方

星を検出して ``(row, col)`` の重心列を返す。

背景と雑音を :func:`noise_sigma` と同じ頑健推定で出し、
``background + threshold_sigma * sigma`` を超える**局所最大**を拾う
(最大値フィルタとの一致で判定するので、``min_separation`` 画素以内に
2 つは出ない)。中心はしきい値の画素位置ではなく、``centroid_box``
(既定 ``2*min_separation+1``)の窓で**背景を引いた強度で重み付けした重心**
—— これが副画素の位置精度を出す唯一の理由で、連結成分の重心
(:func:`detect.segment_objects`)は硬いしきい値の分だけ明るさに依存して
偏る。

明るい順に並べて ``max_stars`` 個で打ち切る。縁から ``edge_margin``
(既定 ``centroid_box // 2``)より内側の星だけを返す —— 窓が画像からはみ出す
星は重心が縁側へ引っ張られるので、黙って偏った値を返すより落とす。

Returns ``(N, 2)`` float64 ``keypoints``。1 個も無ければ ``(0, 2)``
(空は正当な答えなので例外にしない —— 星が無い視野は存在する)。

**Raises** ``ValueError``: 2-D でない / 非有限を含む / *threshold_sigma* が
非正 / *min_separation* が 1 未満 / *max_stars* が 1 未満の場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[psf_fit](psf_fit.md) · [aperture_photometry](aperture_photometry.md)

## 同カテゴリ(`photometry`)

[psf_fit](psf_fit.md) · [aperture_photometry](aperture_photometry.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
