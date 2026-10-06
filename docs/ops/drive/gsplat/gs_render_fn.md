---
op: gs_render_fn
dim: drive
category: gsplat
in: table
out: any
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# gs_render_fn — DRIVE `gsplat` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_render_fn(gs: 'dict', **render_kw)` (実装を直接呼ぶなら `import gsplatnp; gsplatnp.gs_render_fn(gs: 'dict', **render_kw)`、台帳から引くなら `opsdrive.get("gs_render_fn")`)

## 使い方

``render_fn(world, cam) → (H, W, 3)``(:func:`kendamaworld.camera_perceiver` の描画の差し替え口)を返す: 呼ばれるたびに
:func:`gs_update` で世界のいまの頂点へガウシアンを付け直し、``cam``(dict: pose, K, width, height)で :func:`gs_render` する。
``render_kw`` は gs_render へそのまま渡す。属性 ``n_calls``・``n_pairs``(累計)を持つ。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_update](gs_update.md) · [gs_render](gs_render.md) · [gs_read_file](gs_read_file.md)

---
*Provenance: gsplatnp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
