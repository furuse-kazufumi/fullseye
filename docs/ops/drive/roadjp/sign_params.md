---
op: sign_params
dim: drive
category: roadjp
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.3.0  # fullseye lib version this note was generated for
---

# sign_params — DRIVE `roadjp` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.sign_params(kind: 'str', *, side: 'float | None' = None) -> 'dict'` (実装を直接呼ぶなら `import roadjp; roadjp.sign_params(kind: 'str', *, side: 'float | None' = None) -> 'dict'`、台帳から引くなら `opsdrive.get("sign_params")`)

## 使い方

標識 ``kind`` の形・寸法・色を返す(公表値、一次資料で要確認)。

``{"shape", "width", "height", "mount_height", "ground", "border", "ink", "side"}``。
shape は circle / triangle_down / diamond / pentagon / rect。width・height は板の外形 [m]:
円 直径 0.6、逆三角形 一辺 0.6(高さ = 一辺 × √3/2)、菱形 一辺 0.45(対角 = 一辺 × √2)、横長矩形 0.6 × 0.3、
五角形(横断歩道)0.6 × 0.6 —— 出典: 道路標識、区画線及び道路標示に関する命令 別表第二 / KICTEC 寸法表。
矩形・五角形の寸法は同表で確かめていない(要確認)。``side`` を渡すと一辺(円は直径、菱形は一辺)を置き換える
(一時停止 800 mm の記述に合わせるなど)。mount_height = 1.8(路側式、板の下端)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roadjp`)

[sign_image](sign_image.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [sign_mesh](sign_mesh.md) · [add_sign](add_sign.md) · [signal_jp_mesh](signal_jp_mesh.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
