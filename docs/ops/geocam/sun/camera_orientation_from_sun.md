---
op: camera_orientation_from_sun
dim: geocam
category: sun
in: keypoints × signal
out: table
examples: [poc_public_camera_heading]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# camera_orientation_from_sun — GEOCAM `sun` op

- **データ種**: `keypoints × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_orientation_from_sun(sun_pixels, unix_times, lat_deg, lon_deg, K)` (実装を直接呼ぶなら `import geocam; geocam.camera_orientation_from_sun(sun_pixels, unix_times, lat_deg, lon_deg, K)`、台帳から引くなら `opsgeocam.get("camera_orientation_from_sun")`)

## 使い方

時刻つきの太陽の画素位置 ≥ 2 点 → カメラの (yaw, pitch, roll)(Wahba 問題の SVD 解 = Kabsch)。

各観測で、画素 → カメラ座標の光線 d_c(K から)、時刻 → 世界の太陽方向 s_w(``sun_position``、
**屈折込み**の仰角を使う: カメラが見るのは見かけの太陽)。``R = argmin Σ |R d_c − s_w|²`` を
SVD で閉形式に解き(Kabsch 1976 / Markley 1988)、``(yaw, pitch, roll)`` に分解する。

2 点で一意に決まる(2 本の方向が張る面が要る)。観測が 1 点、または全部が同じ方向(共線)なら
ValueError —— 例えば同じ時刻の 2 枚、あるいは正午だけを何日も。太陽は 1 日で方位が大きく
動くので、**同じ日の朝と夕の 2 枚**があれば足りる。

Args:
    sun_pixels: (N, 2) の (u, v)。``sun_pixel_position`` の出力を積んだもの。
    unix_times: (N,) UNIX 秒(UTC)。
    lat_deg, lon_deg: カメラの位置。
    K: (fx, fy, cx, cy)。
Returns:
    table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``residual_deg``(光線と太陽方向の
    角度残差の RMS)/ ``max_residual_deg`` / ``n`` / ``condition``(観測方向の張る面の広さ =
    2 番目の特異値、0 に近いほど不定)。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](../skyline/render_skyline_view.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`sun`)

[sun_position](sun_position.md) · [sun_pixel_position](sun_pixel_position.md) · [sun_bloom_fit](sun_bloom_fit.md) · [camera_orientation_from_sun_candidates](camera_orientation_from_sun_candidates.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
