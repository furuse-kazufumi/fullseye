---
op: m3c2_distance
dim: 3d
category: metrics
in: points × points
out: signal
examples: [metrics_eval]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# m3c2_distance — 3D `metrics` op

- **データ種**: `points × points` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.m3c2_distance(a, b, cores, normals, radius, max_depth=None, min_points=4)` (実装を直接呼ぶなら `import metrics3d; metrics3d.m3c2_distance(a, b, cores, normals, radius, max_depth=None, min_points=4)`、台帳から引くなら `ops3d.get("m3c2_distance")`)
- **台帳経由の戻り値**: `fullseye.ledger.m3c2_distance(...)` は**宣言 out 型 `signal` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.m3c2_distance.raw(...)`、または `metrics3d.m3c2_distance` を直接呼ぶ。

## 使い方

2 時点の点群の差を**法線方向に**測る(M3C2)。→ ``(distance, lod)`` の 2 つ。

最近傍距離(chamfer / C2C)は「いちばん近い点までの距離」なので、**傾いた面では
面に沿ったずれまで距離として数えてしまう**。地形・構造物の変化検出では、それが
「測り直しただけで検出される偽の変化」の主因になる(`poc_structure_4d_deterioration`
の実測: 劣化ゼロで測り返しただけで C2C の中央値 21.07 mm、法線方向なら 0.55 mm)。

M3C2(Lague 2013)は core 点ごとに **法線 ``n`` を軸とする円筒**(半径 ``radius``、
長さ ``max_depth``)で両方の雲を切り取り、各点を ``n`` に射影した平均の差を返す。
向きは ``n`` の指す側が正 —— **符号がそのまま「増えた / 減った」**になる。

Args:
    a: 時点 1 の点群 ``(Na,3)``。
    b: 時点 2 の点群 ``(Nb,3)``。
    cores: 測る場所 ``(M,3)``(a の部分集合でも、別に置いた格子でもよい)。
    normals: core ごとの法線 ``(M,3)``(未正規化でよい。**符号が結果の符号を決める**)。
    radius: 円筒の半径(core 周りで平均する範囲。面の粗さより大きく、測りたい
        構造より小さく取る)。
    max_depth: 円筒の長さの半分。``None`` なら軸方向を制限しない。
    min_points: 片側にこの数だけ点が無い core は ``nan`` を返す(既定 4)。

Returns:
    ``(distance, lod)``: どちらも ``(M,)`` float64。``distance`` は法線方向の
    符号つき差、``lod``(level of detection)は
    ``1.96·sqrt(σa²/na + σb²/nb)`` —— **この値を超えない差は雑音と区別できない**。
    点が足りない core は両方 ``nan``。

    ★台帳経由(``fullseye.ledger.m3c2_distance``)は宣言 out 型の ``distance`` だけを
    返す。``lod`` も要るときは ``fullseye.ledger.m3c2_distance.raw(...)``。

Raises:
    ValueError: 点群 / cores が ``(N,3)`` でない、空、``normals`` の数が cores と
    合わない、``radius <= 0``、``max_depth <= 0``、``min_points < 1`` のとき。

**限界(honest)**: (1) 法線は呼び手が与える —— `estimate_normals` の符号は任意なので、
向きを揃えないと符号が場所ごとに反転する。(2) ``lod`` は雑音だけを見ており、
**位置合わせの残差は含まない**(Lague の原論文は登録誤差を別項として足す)。
(3) 円筒に入る点が少ない縁では ``nan`` になる —— 0 を返して「変化なし」に
見せない。

Reference (public): D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of
complex topography with terrestrial laser scanner: application to the Rangitikei
canyon (N-Z)", ISPRS Journal of Photogrammetry and Remote Sensing 82 (2013) 10-26.

## 背景知識ガイド(この op の手前にある物理・規約)

- [blender_interop](../guides/blender_interop.md) — Blender との併用 — 形を作って fullseye で測る(軸・単位・正解データの罠)
- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [metrics_eval](../../../../examples_3d/metrics_eval.py) — `py -3.11 examples_3d/metrics_eval.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`metrics`)

[chamfer_distance](chamfer_distance.md) · [hausdorff_distance](hausdorff_distance.md) · [fscore](fscore.md) · [rmse_correspondence](rmse_correspondence.md) · [normal_consistency](normal_consistency.md) · [voxel_iou](voxel_iou.md) · [pose_error](pose_error.md)

---
*Provenance: metrics3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
