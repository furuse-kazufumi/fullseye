---
op: gs_read_file
dim: drive
category: gsplat
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# gs_read_file — DRIVE `gsplat` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_read_file(path, *, min_opacity: 'float' = 0.0) -> 'dict'` (実装を直接呼ぶなら `import gsplatnp; gsplatnp.gs_read_file(path, *, min_opacity: 'float' = 0.0) -> 'dict'`、台帳から引くなら `opsdrive.get("gs_read_file")`)

## 使い方

3D Gaussian Splatting のファイルを読み、ガウスの中心・色・不透明度・大きさ・向きを返す。

対応: **INRIA 形式の .ply**(x, y, z, f_dc_0..2, opacity(logit), scale_0..2(log), rot_0..3(wxyz)。
``gsplat_train_native`` の出力もこれ)と **.splat**(1 個 32 バイト: 位置 3×f32、大きさ 3×f32、
RGBA 4×u8、回転 4×u8(wxyz、(q·128)+128))。

Args:
    path: ファイル。
    min_opacity: これ未満の不透明度のガウスを落とす(0 なら全部)。

Returns:
    ``{"xyz" (N,3), "rgb" (N,3) [0,1], "opacity" (N,) [0,1], "scale" (N,3)(実寸、exp 済み),
    "rot" (N,4) wxyz 単位四元数, "n_total", "format"}``。色は 0 次の球面調和だけ(視点で変わる高次は捨てる)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_update](gs_update.md) · [gs_render](gs_render.md) · [gs_render_fn](gs_render_fn.md)

---
*Provenance: gsplatnp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
