---
op: braid_from_trajectories
dim: drive
category: braidpath
in: any
out: table
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# braid_from_trajectories — DRIVE `braidpath` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.braid_from_trajectories(trajectories, obstacles=None, angle=0.1, jitter='auto')` (実装を直接呼ぶなら `import braidpath; braidpath.braid_from_trajectories(trajectories, obstacles=None, angle=0.1, jitter='auto')`、台帳から引くなら `opsdrive.get("braid_from_trajectories")`)

## 使い方

平面の軌道群(と動かない障害物の点)から組紐語を作る(交差の符号列)。

各刻みの間は直線で動くとして、射影の軸 x' = x cos θ + y sin θ の上で隣り合う 2 本の紐の順が入れ替わる時刻を
閉形式で求め(相対の動きも直線なので零点は高々 1 つ)、時刻の順に文字にする。左の紐が**下**(y' の小さい側)を
通って右へ出れば ``+i``(反時計回りの半回転)、上を通れば ``−i``。

★射影の三重点: 格子の対称な動き(2 台が障害物の点をはさんで点対称に動く等)では 3 本が一直線のまま回り、
どの角度でも 3 つの交差が同時になる。``jitter="auto"`` は、そのときだけ紐ごとに一定の小さなずらし
(最小距離 × ``JITTER_FRACTION``、向きは黄金角)を足して取り直す。ずらしは最小距離よりずっと小さいので組紐は
変わらない(門で確かめる)。

Parameters
----------
trajectories : numpy の (K, T, 2) = [x, y]、または list の格子の経路(各台の (row, col) の列)/ 計画器の dict(``paths``)。
obstacles : (M, 2) の点、任意。穴を 1 点で代表させる(穴の中の点ならどれでも類は変わらない)。
angle : 射影の軸の角度 [rad]。類の判定(:func:`homotopy_class_compare`)は角度に依らないが、語そのものは変わる。
jitter : ``"auto"`` か、ずらしの大きさ(0 = ずらさない、上限は最小距離の 1 %)。

Returns
-------
dict: ``word`` (int の 1-D 配列)、``n_strands``、``n_agents``、``start_order`` / ``end_order``(位置の順の紐の番号)、
``times``(各文字の時刻、刻みの単位)、``angle``、``jitter``(使ったずらし)、``clearance``(紐どうしの最小距離)。

Raises
------
ValueError: 2 本の紐が同じ点に来る(衝突に組紐は無い)、jitter=0 で三重点(TriplePointError)、形が違う、NaN。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
