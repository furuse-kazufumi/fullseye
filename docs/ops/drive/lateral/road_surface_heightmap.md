---
op: road_surface_heightmap
dim: drive
category: lateral
in: table
out: depth
gpu: なし
examples: [heightmap_depth_camera_tour, road_surface_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# road_surface_heightmap — DRIVE `lateral` op

- **データ種**: `table` → `depth`
- **呼び出し**: `import fullseye as fs; fs.ledger.road_surface_heightmap(alignment, cell: 'float' = 0.05, *, extent=None, margin: 'float' = 10.0, half_width: 'float' = 3.0, shoulder: 'float' = 0.5, crossfall: 'float' = 0.02, gutter_width: 'float' = 0.5, gutter_depth: 'float' = 0.06, verge_drop: 'float' = 0.04, terrain=None, blend_start: 'float' = 5.0, blend_width: 'float' = 4.5, return_truth: 'bool' = False)` (実装を直接呼ぶなら `import drivelateral; drivelateral.road_surface_heightmap(alignment, cell: 'float' = 0.05, *, extent=None, margin: 'float' = 10.0, half_width: 'float' = 3.0, shoulder: 'float' = 0.5, crossfall: 'float' = 0.02, gutter_width: 'float' = 0.5, gutter_depth: 'float' = 0.06, verge_drop: 'float' = 0.04, terrain=None, blend_start: 'float' = 5.0, blend_width: 'float' = 4.5, return_truth: 'bool' = False)`、台帳から引くなら `opsdrive.get("road_surface_heightmap")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

中心線の線形と横断の決まりから、道の面の高さ図と、セルごとの解析の真値(勾配・横勾配)を作る。

各セルの中心を中心線へ射影した (s, e)(s = 中心線の弧長、e = 横ずれ、進行方向の左が正)で高さを決める:

    z = z_c(s) + p(e; β(s), rate(s))

* **射影**: 既存の :func:`lateral_offset`(折線への射影、近い頂点から窓 2 区間)で区間を決め、その区間の始点の
  向き・曲率の**局所の円弧**へ射影し直す。直線と円弧では厳密で、折線の頂点ごとの mm の折れ目が出ない
  (クロソイドは区間の中で 3 次の誤差)。線形の端より外は、端の向きの直線で延ばす。隣り合う局所の円弧の法線の
  間に残る楔(曲率が変わる所の曲がりの外側、ヘアピンの中心の近く)は、``lateral_offset`` が見つけた折線の区間へ
  その区間の中の座標で射影し、直線として扱う(真値の ``curvature`` は 0、``grade`` は ds/d(弦) = 弧/弦 で直す)。
  足が頂点になる所は s が頂点の値で一定で、``heading`` は頂点からの向きに直交、``grade`` は 0(どれもこの作り方の
  微分)。
* **縦断** z_c(s): 標本の z と勾配 g = dz/ds(``grade`` の列、無ければ ``np.gradient``、2 次まで厳密)の
  3 次 Hermite 補間。放物線の縦断曲線は標本の間でも厳密。
* **横断** p(e): 車道(|e| ≤ ``half_width + shoulder``)は、拝み勾配 −``crossfall``·|e| と一方向の片勾配
  −``rate``·e を ``β`` で混ぜる(β = 0 拝み、β = 1 片勾配、rate > 0 で左が下がる)。β と rate は線形の列
  (標本の間は一次補間)で、片勾配への移り変わり(すりつけ)を表す。車道の外は縁の高さのまま、側溝
  (幅 ``gutter_width``、深さ ``gutter_depth`` の半正弦)、その外は路側の段 ``verge_drop`` だけ下げる。
* **地形へのなじませ**(``terrain`` を渡したとき): |e| が ``blend_start`` から ``blend_width`` かけて、線形の端より
  外では端からの距離で、道の高さを ``terrain``(同じ格子の高さ図)へ一次で混ぜる。

返り値は (ny, nx) の高さ図 ``heights``(``grid[i, j]`` はセル (行 i = y、列 j = x)の中心
(xmin + (j + ½)·cell, ymin + (i + ½)·cell) の高さ。:func:`terrain.elevation_map` と同じ並び)。台帳の型
``depth`` のまま他の op(``dem_slope``・``heightmap_depth_camera``・``crop_rectangle2`` …)へ渡せる。
``return_truth=True`` なら ``(heights, truth)`` を返す。``truth`` は同じ形のセルごとの解析の真値(作り方の
偏微分。数値微分ではない):

* ``s``・``e``・``heading``(足の点での中心線の向き [rad])・``curvature``(そこで使った曲率 [1/m])。
* ``grade`` = ∇z·t(中心線の向き t に沿った勾配 = (z_c' + ∂p/∂β·β' + ∂p/∂rate·rate') / (1 − κe))。
  曲線の内側ほど急になる(1/(1 − κe))。片勾配のすりつけでは縁の勾配が中心線と違う(相対勾配)。
* ``cross`` = ∇z·n(左向きの横勾配 ∂p/∂e、+ で左が上がる)。
* ``carriageway``(bool: 車道の中で、地形と混ぜていないセル)。地形と混ぜたセルの ``grade``・``cross`` は nan
  (真値を作り方から出せないので、言わない)。
* ``extent`` (xmin, xmax, ymin, ymax)、``cell``、``cross_section``(使った横断の値)。

側溝の外縁の段は不連続で、その上の勾配は定義されない(真値は段の両側の値)。拝みの頂(e = 0)の横勾配は
左右の平均(β = 0 なら 0)。

Parameters
----------
alignment : dict
    中心線の表。``x``・``y``・``z``(N ≥ 2)が要る。任意の列: ``s``(弧長。無ければ折線の長さ)、
    ``heading``・``curvature``(:func:`clothoid_points` の返りをそのまま渡すと射影が厳密になる。無ければ
    標本から 2 次の差分で作る。端も 2 次)、``grade``(dz/ds)、``beta``(0..1)、``rate``(片勾配 [m/m]、
    |rate| ≤ 0.2)。任意の列は xy・z の折線と突き合わせ、単位・符号の取り違え(度とラジアン、1/km、%、km、
    逆向き)は ValueError で断る(heading は弦の向きと 0.01 rad + |κ|·h まで、curvature は弦の折れ角または
    1 区間なら heading の差と 1e-3 rad + 10 % まで、grade は z の傾きと 1e-3 + 10 % まで、s は弦/弧が
    0.5〜1.01)。2 標本で heading がない非零 curvature は照合できないので断る。この幅より小さい誤り
    (例: 区間の曲がりの角 2|κ|·h が 1e-3 rad を切るほど緩い曲線の、曲率の符号)は見分けない。
cell : float
    格子の間隔 [m]。
extent : (xmin, xmax, ymin, ymax) or None
    格子の範囲(:func:`terrain.elevation_map` の ``bounds`` と同じく nx = ceil((xmax − xmin)/cell))。
    None なら中心線の外接矩形に ``margin`` を足す。
crossfall : float
    拝み勾配 [m/m] (0.02 = 2 %)。|crossfall| ≤ 0.2 でなければ断る(% のつもりの 2 を通すと勾配 2 m/m の面になる)。
terrain : (ny, nx) array or None
    外側の地形の高さ(同じ格子)。None なら混ぜず、路側の高さがそのまま外へ続く。
return_truth : bool
    True なら ``(heights, truth)``(真値の表つき)。既定は高さ図だけ。

**Raises** ``ValueError``: 列の欠け・未知の列・非有限、任意の列が折線と合わない(単位・符号)、
|crossfall|・|rate| > 0.2、格子が 2.5e7 セルを超える 等。

空の入力(``alignment`` が 0 要素)は ValueError で拒否する。

English: road surface height map from a centre-line alignment (x, y, z + optional s / heading / curvature /
grade / crossfall blend beta / superelevation rate) and a cross-section (crown, one-way slope, gutter,
verge drop); with return_truth=True also the per-cell analytic truth (grade along the road, cross slope,
s, e) from the construction's partial derivatives. Cells are projected with lateral_offset and then onto the local arc of
the segment (exact for lines and arcs, no polyline kinks). Optional blending into a terrain grid. The optional
columns are checked against the polyline (unit and sign mistakes are refused); with two samples, nonzero curvature
is checked against the heading integral and is refused if heading is absent. |crossfall| and |rate| <= 0.2 m/m.

呼び出し例::

    import numpy as np
    import drivelateral as DL
    s = np.arange(0.0, 40.01, 0.5)                               # 直線 40 m、勾配 6 %、拝み 2 %
    road = {"x": s, "y": np.zeros_like(s), "z": 0.06 * s, "s": s}
    H, T = DL.road_surface_heightmap(road, 0.1, extent=(5.0, 35.0, -3.0, 3.0), return_truth=True)
    xc = 5.0 + (np.arange(H.shape[1]) + 0.5) * 0.1
    yc = -3.0 + (np.arange(H.shape[0]) + 0.5) * 0.1
    assert np.allclose(H, 0.06 * xc[None, :] - 0.02 * np.abs(yc)[:, None], atol=1e-12)
    assert np.allclose(T["grade"], 0.06) and np.allclose(T["cross"][yc > 0], -0.02)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [heightmap_depth_camera_tour](../../../../examples/heightmap_depth_camera_tour.py) — `py -3.11 examples/heightmap_depth_camera_tour.py`
- [road_surface_tour](../../../../examples/road_surface_tour.py) — `py -3.11 examples/road_surface_tour.py`

## 型が繋がる次の op(`depth` を入力に取れる)

[spin_from_marker_sequence](../balltrack/spin_from_marker_sequence.md) · [carla_transform_matrix](../carla/carla_transform_matrix.md) · [carla_pose_to_world](../carla/carla_pose_to_world.md) · [carla_camera_pose](../carla/carla_camera_pose.md) · [carla_xy_yaw](../carla/carla_xy_yaw.md) · [carla_scene_load](../carla/carla_scene_load.md) · [town_chain](../town/town_chain.md) · [osm_parse](../japan/osm_parse.md)

## 同カテゴリ(`lateral`)

[friction_circle_usage](friction_circle_usage.md) · [curve_speed_limit](curve_speed_limit.md) · [design_min_radius](design_min_radius.md) · [understeer_gradient](understeer_gradient.md) · [steady_cornering](steady_cornering.md) · [bicycle_model_step](bicycle_model_step.md) · [ackermann_steer_angles](ackermann_steer_angles.md) · [offtracking_circle](offtracking_circle.md)

---
*Provenance: drivelateral.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
