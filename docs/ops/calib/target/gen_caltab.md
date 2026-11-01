---
op: gen_caltab
dim: calib
category: target
in: 
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# gen_caltab — CALIB `target` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.gen_caltab(rows=7, cols=7, spacing=1.0, radius=0.3, image_size=256)` (実装を直接呼ぶなら `import caltab; caltab.gen_caltab(rows=7, cols=7, spacing=1.0, radius=0.3, image_size=256)`、台帳から引くなら `opscalib.get("gen_caltab")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

円マーク格子の校正板画像を生成(gen_caltab)。

返りは ``image``(板の絵)・``centers``(絵の上のマーク中心 (row, col) [px])に加えて、
``create_caltab`` と同じ板の記述(``points`` = 板中心を原点にした (y, x) [mm]、``spacing``)
を持つ —— この dict はそのまま ``sim_caltab`` / ``find_marks_and_pose`` の板として使える。
★2026-10-23 まで ``spacing`` は受け取るだけで返りのどこにも効いていなかった(台帳の
探針が「効かないつまみ」として検出)。絵の配置は ``image_size`` で決まり、実寸は
``points`` に載る。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](sim_caltab.md) · [disp_caltab](disp_caltab.md)

## 同カテゴリ(`target`)

[caltab_points](caltab_points.md) · [create_caltab](create_caltab.md) · [sim_caltab](sim_caltab.md) · [disp_caltab](disp_caltab.md) · [find_caltab](find_caltab.md)

---
*Provenance: caltab.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
