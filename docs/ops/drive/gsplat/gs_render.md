---
op: gs_render
dim: drive
category: gsplat
in: table × matrix
out: table
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# gs_render — DRIVE `gsplat` op

- **データ種**: `table × matrix` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_render(gs: 'dict', pose, K, width: 'int', height: 'int', *, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, sky=(0.62, 0.75, 0.92), max_radius: 'int' = 64, max_pairs: 'int' = 12000000, antialias: 'bool' = True) -> 'dict'` (実装を直接呼ぶなら `import gsplatnp; gsplatnp.gs_render(gs: 'dict', pose, K, width: 'int', height: 'int', *, light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, sky=(0.62, 0.75, 0.92), max_radius: 'int' = 64, max_pairs: 'int' = 12000000, antialias: 'bool' = True) -> 'dict'`、台帳から引くなら `opsdrive.get("gs_render")`)

## 使い方

3DGS をカメラ(``pose`` = world→camera 4×4、``K`` 3×3、driveworld.world_camera と同じ規約: −Z を見る、行は上が小さい)で描く。

手順: (1) 中心をカメラ系へ、深さ d = −z ≤ 1e-6 は捨てる、(2) 2-D 共分散 Σ' = J W Σ Wᵀ Jᵀ + 0.3 I、
J = [[fx/d, 0, fx·x/d²], [0, −fy/d, −fy·y/d²]]、(3) 半径 r = ⌈3 √λ_max(Σ')⌉(≤ ``max_radius``、超える物は捨てずに r を切る)の窓の
画素ごとに α = min(0.99, o · exp(−½ Δᵀ Σ'⁻¹ Δ))(α < 1/255 は捨てる)、(4) 画素ごとに深さの順で手前から
C = Σ c_i α_i T_i、T_i = Π_{j<i}(1 − α_j)、背景 = (1 − Σ α_i T_i) · sky。色は Lambert(world_camera と同じ ambient + (1 − ambient)|n·l|、
光はカメラ系)。すべて配列演算(ガウシアン × 窓の画素の組を平らに並べ、画素 → 深さで並べて群ごとの累積和で T を出す)。

返り値: ``color`` (H,W,3)・``alpha`` (H,W)(= Σ α_i T_i)・``depth`` (H,W)(α で重みづけた深さ / alpha、alpha < 0.5 は NaN)・
``label`` (H,W)(重み最大のガウシアンのラベル、alpha < 0.5 は −1)・``n_pairs``・``n_visible``。
fail-closed: 画像の大きさ ≤ 0、max_radius < 1、組の数が ``max_pairs`` を超える(遅すぎる描画を黙って走らせない)は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_update](gs_update.md) · [gs_render_fn](gs_render_fn.md)

---
*Provenance: gsplatnp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
