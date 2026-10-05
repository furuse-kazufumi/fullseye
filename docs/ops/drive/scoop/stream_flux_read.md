---
op: stream_flux_read
dim: drive
category: scoop
in: any × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# stream_flux_read — DRIVE `scoop` op

- **データ種**: `any × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.stream_flux_read(frames, dt: 'float', radius_px: 'float', *, band_rows=None, band_px: 'int' = 9, window: 'int' = 32, particle_mass: 'float | None' = None, c_max: 'float' = 0.95, min_valid: 'float' = 0.3, min_crossings: 'float' = 30.0) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.stream_flux_read(frames, dt: 'float', radius_px: 'float', *, band_rows=None, band_px: 'int' = 9, window: 'int' = 32, particle_mass: 'float | None' = None, c_max: 'float' = 0.95, min_valid: 'float' = 0.3, min_crossings: 'float' = 30.0) -> 'dict'`、台帳から引くなら `opsdrive.get("stream_flux_read")`)

## 使い方

流れのコマ列から流量 [個/s] (と質量流量)を読む —— 速さは PIV(``pivops.piv_cross_correlate`` の全コマ対の中央値)、
粒の線密度は時間平均の被覆率の Boolean 模型の逆(:func:`stream_areal_density`)を横に積分した ``λ``、流量 ``λ v``。

``band_rows`` = 測る行の中心の列(None なら PIV の窓の行中心を全部)。各帯は ``band_px`` 行の平均。速さは流れの
向き(行が増える向き)の成分を、PIV の窓の行の間で線形に補間し、列は被覆率の重みで平均する。
返り: ``rows``、``v_px``(px/コマ)、``v``(px/s)、``lam``(個/px)、``flux``(個/s)、``flux_naive``(素朴な ``c/(πr²)``)、
``flux_mean``、``flux_spread``(帯の間の (max − min)/平均 = 流量の連続の検査)、``mass_flux``(``particle_mass`` を与えたとき)、
``valid_fraction``(PIV の有限な窓の割合)、``c_max_seen``、``n_crossed_est``(記録の間に各帯を横切った粒の推定数
``flux·T``)、``rel_err_poisson``(``1/√n``、粒の数え上げの揺らぎ)、``reliable``(全帯で ``n ≥ min_crossings``)。
粒が少ないと流量は数え上げの揺らぎそのもの(1 帯を横切る粒が 2 個なら ±70 %)—— ``reliable=False`` で知らせる。
**Raises** ``ValueError``: コマが 2 未満 / 形が揃わない / PIV の有限な窓が ``min_valid`` 未満(粒が少なすぎて速さが
読めない —— 壊れる場所)/ 帯が像の外 / 飽和。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_scoop_pour](../../../../examples/poc_powder_scoop_pour.py) — `py -3.11 examples/poc_powder_scoop_pour.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`scoop`)

[spoon_bowl_volume](spoon_bowl_volume.md) · [scoop_synth_side](scoop_synth_side.md) · [revolution_volume_side](revolution_volume_side.md) · [two_view_volume](two_view_volume.md) · [scoop_volume_read](scoop_volume_read.md) · [scoop_count](scoop_count.md) · [scoop_image_limit](scoop_image_limit.md) · [tilt_wedge_retained](tilt_wedge_retained.md)

---
*Provenance: scoop.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
