---
op: homotopy_class_compare
dim: drive
category: braidpath
in: any × any
out: table
gpu: なし
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# homotopy_class_compare — DRIVE `braidpath` op

- **データ種**: `any × any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.homotopy_class_compare(traj_a, traj_b, obstacles=None, angle=0.1, jitter='auto', tol=1e-09)` (実装を直接呼ぶなら `import braidpath; braidpath.homotopy_class_compare(traj_a, traj_b, obstacles=None, angle=0.1, jitter='auto', tol=1e-09)`、台帳から引くなら `opsdrive.get("homotopy_class_compare")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

始点と終点が同じ 2 つの経路族(複数エージェントの計画)が、同じホモトピー類か。

衝突せずに(エージェント同士も障害物の点とも重ならずに)始点と終点を止めたまま連続に変形できる ⇔ 組紐が等しい。
組紐は :func:`braid_from_trajectories`、比較は Dynnikov 座標。射影の角度に依らない(門で複数の角度を振る)。

Returns: dict ``same``、``word_a`` / ``word_b``、``key_a`` / ``key_b``、``quotient``(a b⁻¹ を簡約した語 —— 空なら同じ類、
空でなければ「どう回り方が違うか」の語)、``endpoint_error``(始点・終点の最大のずれ)、``tol_limit``(``tol`` の上限)。
始点と終点は ``tol``(既定 ``ENDPOINT_TOL`` = 1e-9、座標の単位、各座標の差の最大)以内でそろっていること。
``tol`` は答えを変えず通す / 拒むだけの門で、効かないノブの台帳に理由つきで載せている。``tol`` 以内でずれた
B の端は、A の端へ直線で寄せる区間を B の前後に足してから比べる(``word_b`` はその寄せた計画の語)。
``tol`` の上限は ``tol_limit`` = d / (2√2)(d = A の始点と終点の配置での紐どうしの最小距離、障害物の点を含む):
各台は各座標で ``tol`` 以内 = 距離 √2·``tol`` 以内しか動かないので、2 台の距離の変化は 2√2·``tol`` 未満に収まり、
寄せる区間は衝突しない。しかも A の端から各座標 ``tol`` 以内の配置の集まりは凸で衝突を含まないので、どう寄せても
類は同じ —— 答えが射影の角度にも ``tol`` にも依らない。上限を超える ``tol`` は端の違う計画どうしを同じ類と
呼べてしまうので拒む。計画器ごとに端が丸めで違うときは ``tol`` を上限の内側で広げるか、比べる前に端をそろえる
(類は端を止めた変形の類なので、端の違う 2 つの計画は比べられない)。

Raises: ValueError(台数が違う、始点か終点が ``tol`` より離れている、``tol`` が負か非有限か ``tol_limit`` 以上、
射影の上で始点か終点の並びが食い違う、衝突)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_reduce](braid_reduce.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
