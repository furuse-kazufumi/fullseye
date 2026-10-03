---
op: gs_from_world
dim: drive
category: gsplat
in: table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# gs_from_world — DRIVE `gsplat` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_from_world(world: 'dict', *, spacing: 'float' = 0.004, max_per_object: 'int' = 20000, pos_noise: 'float' = 0.0, color_noise: 'float' = 0.0, sigma_ratio: 'float' = 1.0, normal_ratio: 'float' = 0.1, opacity: 'float' = 0.99, curv_ratio: 'float' = 0.5, edge_ratio: 'float' = 0.25, seed: 'int' = 0) -> 'dict'` (実装を直接呼ぶなら `import gsplatnp; gsplatnp.gs_from_world(world: 'dict', *, spacing: 'float' = 0.004, max_per_object: 'int' = 20000, pos_noise: 'float' = 0.0, color_noise: 'float' = 0.0, sigma_ratio: 'float' = 1.0, normal_ratio: 'float' = 0.1, opacity: 'float' = 0.99, curv_ratio: 'float' = 0.5, edge_ratio: 'float' = 0.25, seed: 'int' = 0) -> 'dict'`、台帳から引くなら `opsdrive.get("gs_from_world")`)

## 使い方

世界の面にガウシアンを貼った 3DGS を返す(``world`` = driveworld の世界 dict: V, F, face_color, objects)。

物体ごとに間隔 s_o = max(``spacing``, √(物体の面積 / ``max_per_object``))、個数 N_o = ⌈面積 / s_o²⌉。面は面積に比例した層化抽出
(累積面積の (k + u)/N_o 点、u は物体ごとの一様乱数)で選び、面の中は R2 低食い違い列(一様乱数だと隙間 = 穴が空く)。共分散は面に沿う平たい円盤
局所間隔 s_f = max(s_o / 8, min(s_o, ``curv_ratio`` · R_f / ``sigma_ratio``))(R_f = 面の曲率半径の見積り、角 ≥ 75° は数えない):
平たい円盤が曲面からはみ出さない大きさに抑え、細い所(糸)はそのぶん密に置く(個数の重み = 面積 / s_f²)。角(隣の面と 75° 以上)に
接する面は s_f ≤ ``edge_ratio`` · s_o(3DGS が縁で細かくするのと同じ: 大きな円盤が縁の外 —— 玉の穴の口 —— へはみ出して穴を塞いだ)。
Σ = R diag(σt², σt², σn²) Rᵀ、σt = ``sigma_ratio`` · s_f(既定 1.0 = 3DGS の初期値「近い 3 点までの平均距離」と同じ。0.7 では
板の 7 % の画素で α < 0.95 の隙間が残った)、σn = ``normal_ratio`` · σt、R = [t1 t2 n] (面の局所座標)。
誤差(1 個ごとに固定、コマをまたいで同じ): 面の局所座標での位置 N(0, ``pos_noise``²)(3 軸)・色 N(0, ``color_noise``²)(切り詰め)。

返り値 dict: ``face`` (N,)・``bary`` (N,3)・``offset_local`` (N,3)・``color`` (N,3)・``opacity`` (N,)・``sigma_t`` (N,)・``sigma_n`` (N,)・
``obj`` (N,)(世界の objects の索引)・``label`` (N,)・``spacing_obj`` (物体数,)、加えて :func:`gs_update` が埋める ``mu`` (N,3)・
``R`` (N,3,3)(列 = t1, t2, n)・``normal`` (N,3)。
fail-closed: spacing ≤ 0、max_per_object < 1、雑音 < 0、sigma_ratio ≤ 0、normal_ratio ≤ 0、opacity ∉ (0, 1]、面の無い世界は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_update](gs_update.md) · [gs_render](gs_render.md) · [gs_render_fn](gs_render_fn.md) · [gs_read_file](gs_read_file.md)

---
*Provenance: gsplatnp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
