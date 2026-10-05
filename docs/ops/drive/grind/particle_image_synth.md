---
op: particle_image_synth
dim: drive
category: grind
in: scalar × scalar × scalar
out: table
examples: [poc_powder_grinding_ae]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# particle_image_synth — DRIVE `grind` op

- **データ種**: `scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.particle_image_synth(n: 'int' = 60, d_med: 'float' = 12.0, sigma_ln: 'float' = 0.35, shape=(256, 256), pitch: 'float' = 1.0, seed: 'int' = 0, gap: 'float' = 3.0, supersample: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import grind; grind.particle_image_synth(n: 'int' = 60, d_med: 'float' = 12.0, sigma_ln: 'float' = 0.35, shape=(256, 256), pitch: 'float' = 1.0, seed: 'int' = 0, gap: 'float' = 3.0, supersample: 'int' = 4) -> 'dict'`、台帳から引くなら `opsdrive.get("particle_image_synth")`)

## 使い方

重ならない円板(粒子の投影)を撒いた被覆率の画像と真値(直径 [µm] の対数正規、``pitch`` µm/px)。

円板どうしは ``gap`` px 以上離す(融合は別の問題で、poc_particle_sizing が扱う)。既定 3 px: 2 px だと両側の部分画素が
斜めに隣り合い、8 連結のラベルで 2 個が 1 個になった(12 枚中 4 枚、体積基準の D50 が最大 8.5 % ずれた)。縁は ``supersample`` で反エイリアス。
返り: ``image``(``(H, W)`` 被覆率)、``pitch``、``truth``(``diameters`` µm、``centres`` px、``touches_border``)。
置けなかった粒子があれば ``n_placed < n``(黙って詰めない)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_powder_grinding_ae](../../../../examples/poc_powder_grinding_ae.py) — `py -3.11 examples/poc_powder_grinding_ae.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`grind`)

[particle_size_read](particle_size_read.md) · [particle_size_dx](particle_size_dx.md) · [particle_size_oversize](particle_size_oversize.md) · [particle_size_synth](particle_size_synth.md) · [comminution_energy](comminution_energy.md) · [comminution_law_fit](comminution_law_fit.md) · [breakage_first_order_fit](breakage_first_order_fit.md) · [replicate_compare](replicate_compare.md)

---
*Provenance: grind.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
