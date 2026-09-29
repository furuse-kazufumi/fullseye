---
op: signal_jp_mesh
dim: drive
category: roadjp
in: 
out: table
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# signal_jp_mesh — DRIVE `roadjp` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.signal_jp_mesh(*, lens: 'float' = 0.3, n: 'int' = 3, hood: 'bool' = True, state: 'str' = 'off') -> 'dict'` (実装を直接呼ぶなら `import roadjp; roadjp.signal_jp_mesh(*, lens: 'float' = 0.3, n: 'int' = 3, hood: 'bool' = True, state: 'str' = 'off') -> 'dict'`、台帳から引くなら `opsdrive.get("signal_jp_mesh")`)

## 使い方

横型の車両用灯器(日本式)。原点 = 灯器の底面の中心、表示面は −x を向く。

箱: 幅 = n·(lens + 0.10) + 0.05(3 灯・300 mm で 1.25 m)、高さ = lens + 0.13(0.43 m)、奥行 0.30 m、濃い灰。
レンズ = 半径 lens/2 の円盤(24 分割)を前面より 5 mm 外(−x 側)に置く。並びは **−x を向いて見て左から 青・黄・赤**
= 青が +y、赤が −y(運転者から見て左から青・黄・赤 — Wikipedia 日本の交通信号機、一次資料で要確認)。
n = 2 なら 黄・赤、n = 1 なら 黄(一灯点滅式)。各レンズの上に庇(薄い箱、長さ 0.25 m、``hood``)。
レンズ径は 300 mm(2017 年度から標準 250 mm、どちらも現役)。

返り値 ``{"V", "F", "color", "label": 3, "lamp_faces": {"green": (f0, f1), ...}, "width", "height", "depth", "lens"}``。
``lamp_faces`` はこのメッシュ内の面の索引の範囲(世界に足すときは world_add の返す範囲へ平行移動する —
:func:`driveworld.add_signal` と同じ仕組み)。``state`` の灯だけ driveworld._LAMP の色、他は "off" の色。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`roadjp`)

[sign_params](sign_params.md) · [sign_image](sign_image.md) · [plate_mesh_from_image](plate_mesh_from_image.md) · [sign_mesh](sign_mesh.md) · [add_sign](add_sign.md) · [add_signal_jp](add_signal_jp.md)

---
*Provenance: roadjp.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
