---
op: sun_position
dim: geocam
category: sun
in: signal
out: table
examples: [poc_public_camera_heading, poc_public_camera_heading_real]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# sun_position — GEOCAM `sun` op

- **データ種**: `signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.sun_position(lat_deg, lon_deg, unix_times)` (実装を直接呼ぶなら `import geocam; geocam.sun_position(lat_deg, lon_deg, unix_times)`、台帳から引くなら `opsgeocam.get("sun_position")`)

## 使い方

緯度・経度・時刻(UNIX 秒、UTC)→ 太陽の方位・仰角 [度] (NOAA の太陽位置アルゴリズム、Meeus 1998 の低精度式)。

公開された閉形式(NOAA Global Monitoring Laboratory の Solar Calculator と同じ式:
ユリウス世紀 → 平均黄経・平均近点角・中心差 → 視黄経 → 黄道傾斜 → 赤緯 と均時差 →
時角 → 天頂角・方位角)。精度は 2000 年 ± 1 世紀で **0.01° 程度**(NOAA の記述)、
大気屈折は仰角に足す(NOAA の区分式、水平近くで最大 0.57°)。時刻は UTC の UNIX 秒
(1-D、float でよい)。うるう秒・ΔT は無視する(0.01° に効かない)。

Args:
    lat_deg, lon_deg: 観測点。経度は東が正。
    unix_times: (N,) UNIX 秒(UTC)。スカラも可。

Returns:
    table: ``azimuth_deg`` (N,)(北 0°、時計回り)/ ``elevation_deg`` (N,)(屈折込み)/
    ``elevation_true_deg`` (N,)(屈折なし)/ ``declination_deg`` / ``equation_of_time_min`` /
    ``hour_angle_deg`` / ``n``。

真値で確かめてある性質(tests/test_geocam.py): 春分の正午に仰角 = 90 − |緯度|、
正午の方位は北半球で 180°(南)、方位は東 → 南 → 西と単調、日の出と日の入りの
仰角が対称、赤緯は ±23.44° に収まる。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading](../../../../examples/poc_public_camera_heading.py) — `py -3.11 examples/poc_public_camera_heading.py`
- [poc_public_camera_heading_real](../../../../examples/poc_public_camera_heading_real.py) — `py -3.11 examples/poc_public_camera_heading_real.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](../skyline/render_skyline_view.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`sun`)

[sun_pixel_position](sun_pixel_position.md) · [camera_orientation_from_sun](camera_orientation_from_sun.md) · [sun_bloom_fit](sun_bloom_fit.md) · [camera_orientation_from_sun_candidates](camera_orientation_from_sun_candidates.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
