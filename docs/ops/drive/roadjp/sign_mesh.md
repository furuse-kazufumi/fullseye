---
op: sign_mesh
dim: drive
category: roadjp
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# sign_mesh — DRIVE `roadjp` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sign_mesh(kind: 'str', *, value=None, cell: 'int' = 4, size_px: 'int' = 128, font_path=None, side: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import roadjp; roadjp.sign_mesh(kind: 'str', *, value=None, cell: 'int' = 4, size_px: 'int' = 128, font_path=None, side: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("sign_mesh")`)

## 使い方

:func:`sign_image` + :func:`sign_params` + :func:`plate_mesh_from_image`。返り値に ``width``・``height``・``params`` を足す。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [sign_image](sign_image.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [add_sign](add_sign.md) · [signal_jp_mesh](signal_jp_mesh.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
