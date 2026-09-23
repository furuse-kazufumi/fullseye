---
op: render_skyline_view
dim: geocam
category: skyline
in: table
out: image2d
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# render_skyline_view — GEOCAM `skyline` op

- **データ種**: `table` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.render_skyline_view(sky_table, K, shape, yaw_deg, pitch_deg, roll_deg)` (実装を直接呼ぶなら `import geocam; geocam.render_skyline_view(sky_table, K, shape, yaw_deg, pitch_deg, roll_deg)`、台帳から引くなら `opsgeocam.get("render_skyline_view")`)

## 使い方

スカイライン table と姿勢から、その向きのカメラが見る**空のマスク**(H, W)を描く → image2d(0/1)。

各画素の光線を世界へ回し、その方位のスカイライン仰角より上なら空(1)、下なら地形(0)。
合成の写真づくり(PoC)と、推定した姿勢を写真に重ねて目で確かめる図に使う。
``camera_orientation_from_skyline`` の予測と同じ幾何なので、**描いて → 抜いて → 当てる**の
往復が閉じる(テストの真値)。

Args:
    sky_table: ``dem_skyline`` の出力(``azimuth_deg`` / ``elevation_deg``)。
    K: (fx, fy, cx, cy)。shape: (H, W)。
    yaw_deg, pitch_deg, roll_deg: 姿勢(モジュール冒頭の規約)。
Returns:
    image2d (H, W) float {0, 1}: 1 = 空。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[sun_pixel_position](../sun/sun_pixel_position.md) · [sun_bloom_fit](../sun/sun_bloom_fit.md) · [skyline_extract](skyline_extract.md)

## 同カテゴリ(`skyline`)

[dem_skyline](dem_skyline.md) · [skyline_extract](skyline_extract.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
