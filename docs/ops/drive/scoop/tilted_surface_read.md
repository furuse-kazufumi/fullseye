---
op: tilted_surface_read
dim: drive
category: scoop
in: image2d × scalar × scalar × scalar × scalar
out: table
examples: [poc_powder_scoop_pour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# tilted_surface_read — DRIVE `scoop` op

- **データ種**: `image2d × scalar × scalar × scalar × scalar` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tilted_surface_read(side, lip_row: 'float', lip_col: 'float', theta_deg: 'float', L_px: 'float', *, wall_px: 'float | None' = None, threshold: 'float' = 0.5, shell_px: 'float' = 0.0, smooth_px: 'int' = 1) -> 'dict'` (実装を直接呼ぶなら `import scoop; scoop.tilted_surface_read(side, lip_row: 'float', lip_col: 'float', theta_deg: 'float', L_px: 'float', *, wall_px: 'float | None' = None, threshold: 'float' = 0.5, shell_px: 'float' = 0.0, smooth_px: 'int' = 1) -> 'dict'`、台帳から引くなら `opsdrive.get("tilted_surface_read")`)

## 使い方

傾いた器を横から見た像(被覆率)から、器に残る粉の断面積と奥の平らな面の高さを読む。

器の座標: 口(``lip_row``, ``lip_col``、画素の端が整数)を原点に、床に沿って奥へ ``x``(口を下げて θ 傾けた床 = 画像の
右上がり)、床に垂直に ``y``。``0 ≤ x ≤ L_px``・``0 ≤ y ≤ wall_px``(None = ``L_px``)の中の被覆率の和が断面積 [px²]
(口の外の流れは数えない)。粒の側面像の輪郭は粒の外側の包絡なので、自由表面に沿って厚さ約 1 粒半径の殻が
余分に入る —— ``shell_px``(粒の半径 [px] を渡す)× 自由表面の長さ(器の中の各列の粉面を ``smooth_px`` 列で
移動平均した折れ線の長さ)を引いた ``area_corrected`` も返す。奥の平らな面の高さ ``plateau_px`` = 器の後ろ半分の
粉面の床からの高さの中央値(楔の模型ではここは θ < θ_b の間変わらない; 実際の層は流れて薄くなる —— PoC で見る)。
返り: ``area_px``, ``area_corrected``, ``surface_len_px``, ``plateau_px``(後ろ半分に粉面が無ければ None)。
**Raises** ``ValueError``: 被覆率でない / 器の中が空 / 引数の範囲。

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
