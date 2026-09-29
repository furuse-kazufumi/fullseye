---
op: fbm_params
dim: drive
category: terrain
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fbm_params — DRIVE `terrain` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fbm_params(seed: 'int' = 0, hurst: 'float' = 0.8, n_waves: 'int' = 128, f_min: 'float' = 0.005, f_max: 'float' = 0.125, amplitude: 'float' = 1.0) -> 'dict'` (実装を直接呼ぶなら `import driveterrain; driveterrain.fbm_params(seed: 'int' = 0, hurst: 'float' = 0.8, n_waves: 'int' = 128, f_min: 'float' = 0.005, f_max: 'float' = 0.125, amplitude: 'float' = 1.0) -> 'dict'`、台帳から引くなら `opsdrive.get("fbm_params")`)

## 使い方

乱数位相の正弦の和で fBm 面を作るための表(Saupe 1988 のスペクトル合成の連続版)。

周波数は [f_min, f_max] に対数一様、向きは一様、位相は一様、振幅 ∝ f^{−H}。対数一様に撒いた波は
2 次元周波数面の密度が ∝ f^{−2} なので、パワースペクトルは ∝ A(f)² f^{−2} = f^{−(2H+2)}、
つまり β = 2H + E(E = 2)。振幅は RMS が ``amplitude`` になるよう正規化する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`terrain`)

[perlin2](perlin2.md) · [fbm_height](fbm_height.md) · [fbm_gradient](fbm_gradient.md) · [radial_periodogram](radial_periodogram.md) · [spectral_slope](spectral_slope.md) · [course_distance](course_distance.md) · [terrain_params](terrain_params.md) · [terrain_height](terrain_height.md)

---
*Provenance: driveterrain.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
