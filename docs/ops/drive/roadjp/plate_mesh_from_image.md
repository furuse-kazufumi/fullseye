---
op: plate_mesh_from_image
dim: drive
category: roadjp
in: rgba
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# plate_mesh_from_image — DRIVE `roadjp` op

- **データ種**: `rgba` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.plate_mesh_from_image(rgba, width: 'float', height: 'float', *, cell: 'int' = 4, thickness: 'float' = 0.004, back_color=(0.55, 0.55, 0.55), label: 'int' = 4) -> 'dict'` (実装を直接呼ぶなら `import roadjp; roadjp.plate_mesh_from_image(rgba, width: 'float', height: 'float', *, cell: 'int' = 4, thickness: 'float' = 0.004, back_color=(0.55, 0.55, 0.55), label: 'int' = 4) -> 'dict'`、台帳から引くなら `opsdrive.get("plate_mesh_from_image")`)

## 使い方

RGBA 画像を、面の色を持つ薄い板のメッシュにする。

画像を ``cell × cell`` 画素の区画に切り、alpha の平均が 0.5 以上の区画だけを面にする(2 三角形)。面の色 =
その区画の alpha で重みづけた平均色 ``Σ(α·rgb) / Σα``。表面の法線 = **−x**(yaw 0 で +x へ進んで来る車に向く)、
裏面は同じ形で ``back_color``(法線 +x)。原点 = 板の中心、板は y-z 平面(画像の左 = +y、上 = +z)、
厚さ ``thickness`` を x の ±半分に振る。使われない頂点は残さない(寸法を頂点から測れるように)。

返り値 ``{"V", "F", "color", "label", "front_faces": (0, n), "back_faces": (n, 2n), "cells": (rows, cols)}``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [sign_image](sign_image.md) · [sign_mesh](sign_mesh.md) · [add_sign](add_sign.md) · [signal_jp_mesh](signal_jp_mesh.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
