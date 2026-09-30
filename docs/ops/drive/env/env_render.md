---
op: env_render
dim: drive
category: env
in: table × matrix × matrix
out: table
examples: [poc_driving_weather]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# env_render — DRIVE `env` op

- **データ種**: `table × matrix × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.env_render(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, env: 'Optional[dict]' = None, *, ego=None, ego_pose=None, shadows: 'bool' = True, shadow_cache: 'Optional[dict]' = None, shadow_res: 'int' = 1024) -> 'Dict[str, np.ndarray]'` (実装を直接呼ぶなら `import driveenv; driveenv.env_render(world: 'dict', pose, K, width: 'int' = 640, height: 'int' = 400, env: 'Optional[dict]' = None, *, ego=None, ego_pose=None, shadows: 'bool' = True, shadow_cache: 'Optional[dict]' = None, shadow_res: 'int' = 1024) -> 'Dict[str, np.ndarray]'`、台帳から引くなら `opsdrive.get("env_render")`)

## 使い方

太陽・空・影・灯火・前照灯・霧・雨・まぶしさを物理の単位で描く。

Returns
-------
dict : ``color``(カメラの線形 RGB [0,1]、:func:`tone_map` で圧縮 —— 画像処理はこれを読む)、``display``(sRGB に符号化した
表示用、図だけに使う)、``radiance``(RGB の輝度 cd/m²、線形)、``depth``・``label``・
``face``(driveworld.world_camera と同じ)、``shadow``(bool、太陽の影の画素)、``exposure``(使った倍率)、
``veil``(光幕輝度 cd/m² (H,W))、``illuminance``(面の照度 lx (H,W))。

``ego_pose=(x, y, yaw)`` = 前照灯を付ける自車の姿勢(前端 2.25 m・左右 ±0.6 m・高さ 0.65 m に 2 灯)。
``shadow_cache`` に dict を渡すと太陽のシャドウマップを使い回す(太陽と世界が変わらない間)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_driving_weather](../../../../examples/poc_driving_weather.py) — `py -3.11 examples/poc_driving_weather.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`env`)

[julian_day](julian_day.md) · [sun_at](sun_at.md) · [sun_events](sun_events.md) · [sun_vector](sun_vector.md) · [sun_illuminance](sun_illuminance.md) · [koschmieder](koschmieder.md) · [mor_from_beta](mor_from_beta.md) · [beta_from_mor](beta_from_mor.md)

---
*Provenance: driveenv.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
