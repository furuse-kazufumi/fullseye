---
op: gs_update
dim: drive
category: gsplat
in: table × table
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# gs_update — DRIVE `gsplat` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_update(gs: 'dict', world: 'dict') -> 'dict'` (実装を直接呼ぶなら `import gsplatnp; gsplatnp.gs_update(gs: 'dict', world: 'dict') -> 'dict'`、台帳から引くなら `opsdrive.get("gs_update")`)

## 使い方

世界の**いまの**頂点からガウシアンの中心・向きを計算し直す(その場で書き換えて同じ dict を返す)。

μ = Σ_k bary_k · V[F[face, k]] + R · offset_local、R = 面の局所座標 [t1 t2 n]。面の数が作ったときと違う世界は ValueError
(物体を足した・消した世界には使えない: 作り直すこと)。剛体で動かした物体のガウシアンは同じ剛体変換で動く(門)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_render](gs_render.md) · [gs_render_fn](gs_render_fn.md) · [gs_read_file](gs_read_file.md)

---
*Provenance: gsplatnp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
