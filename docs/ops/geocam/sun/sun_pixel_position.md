---
op: sun_pixel_position
dim: geocam
category: sun
in: image2d
out: keypoints
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# sun_pixel_position — GEOCAM `sun` op

- **データ種**: `image2d` → `keypoints`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_pixel_position(image, threshold=0.98, min_area=4)` (実装を直接呼ぶなら `import geocam; geocam.sun_pixel_position(image, threshold=0.98, min_area=4)`、台帳から引くなら `opsgeocam.get("sun_pixel_position")`)

## 使い方

画像の中の太陽(センサを**飽和**させる円盤)の重心 → keypoints (1, 2) = (u, v)。

前提は「太陽はセンサを飽和させ、雲や雪は飽和の手前で止まる」。値が ``threshold``(絶対値、
画像は 0〜1)以上の画素を 8 近傍で連結し、**最大の塊**の輝度重心を返す。塊が ``min_area`` 未満、
または飽和画素が無ければ「太陽が写っていない」として ValueError(黙って雲の反射を返さない —— 太陽が
山に隠れた時刻の写真で、雲を太陽と読んで姿勢を汚さないための門)。**画像の最大値に対する比では
ない**(比にすると、太陽の無い写真で一番明るい雲が必ず「太陽」になる)。夜景の人工光源や
太陽の水面反射は飽和しうるので、その場面では使えない。塊は**詰まった丸**であること(充填率 ≥ 0.4、
縦横比 ≤ 2.5)—— 露出過多で空の帯が飽和した写真は細長い塊になり、拒否される。

Args:
    image: (H, W) float、0〜1(範囲外は ValueError)。
    threshold: 飽和とみなす絶対値(既定 0.98)。
    min_area: 塊の最小画素数。
Returns:
    keypoints (1, 2) float: (u, v)。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`keypoints` を入力に取れる)

[camera_orientation_from_sun](camera_orientation_from_sun.md) · [camera_orientation_from_sun_candidates](camera_orientation_from_sun_candidates.md)

## 同カテゴリ(`sun`)

[sun_position](sun_position.md) · [camera_orientation_from_sun](camera_orientation_from_sun.md) · [sun_bloom_fit](sun_bloom_fit.md) · [camera_orientation_from_sun_candidates](camera_orientation_from_sun_candidates.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
