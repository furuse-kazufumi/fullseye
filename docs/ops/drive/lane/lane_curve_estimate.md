---
op: lane_curve_estimate
dim: drive
category: lane
in: table × table
out: table
gpu: なし
examples: [poc_ginza_stage2_ops]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# lane_curve_estimate — DRIVE `lane` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.lane_curve_estimate(left, right, *, lane_width=3.5, samples=51, band_inset=0.2, pixel_to_world=None, camera_height=None, seed=0)` (実装を直接呼ぶなら `import laneops; laneops.lane_curve_estimate(left, right, *, lane_width=3.5, samples=51, band_inset=0.2, pixel_to_world=None, camera_height=None, seed=0)`、台帳から引くなら `opsdrive.get("lane_curve_estimate")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

左右の二次境界から車線中央、弧長、符号つき曲率を一つの表で返す。

:func:`lane_center_path` で中央と走行帯を作り、その中央点へ既存の
:func:`lane_boundary_fit` をもう一度適用する。正準二次式
``x=b0+b1*u+b2*u², u=(y-y0)/scale`` を解析微分し、右曲がり(+x側)を正とする
``kappa=x''/(1+x'^2)^(3/2)``を求める。強いS字、ヘアピン、地面が単一平面でない
場合は契約外である。

Parameters
----------
left, right : table or None
    :func:`lane_boundary_fit` の左右境界。少なくとも一方が必要。
lane_width, samples, band_inset
    :func:`lane_center_path` と同じ車線幅[m]、標本数、走行帯の内側余白[m]。
pixel_to_world : (3, 3) matrix or None
    画像/BEV画素から世界平面[m]への明示的な射影。上流の境界表に同じ行列が
    入っている場合は一致を検査し、出力へ保存する。BEV世界点を直接渡す場合はNone。
camera_height : float or None
    画像由来の点で使ったカメラ高[m]を監査用に保存する。射影そのものは
    ``pixel_to_world``に含まれるため、ここで固定値を仮定しない。
seed : int
    中央線の頑健当てはめに使う固定seed。

Returns
-------
table
    ``path``(x,y)[m]、``arc_length``[m]、``curvature``[1/m]、``radius``[m]、
    中央二次式、走行帯、確信度、明示された較正条件。

English: build the centre path with :func:`lane_center_path`, robustly refit its
metric BEV points with the existing quadratic fitter, and analytically differentiate
that polynomial. Positive curvature bends towards +x. Camera height is audit metadata;
the supplied pixel-to-world homography carries the actual metric projection, so this op
never assumes a hidden camera height. It is not valid for hairpins, strong S-curves, or
non-planar road points.

呼び出し例::

    import numpy as np
    import laneops
    left = laneops.lane_boundary_fit(np.c_[-1.75 + .002*np.arange(21)**2, np.arange(21)], side="left")
    right = laneops.lane_boundary_fit(np.c_[1.75 + .002*np.arange(21)**2, np.arange(21)], side="right")
    out = laneops.lane_curve_estimate(left, right, camera_height=1.6)
    assert abs(out["curvature"][0] - .004) < 1e-10

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_ginza_stage2_ops](../../../../examples/poc_ginza_stage2_ops.py) — `py -3.11 examples/poc_ginza_stage2_ops.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`lane`)

[color_rule_mask](color_rule_mask.md) · [plane_topview_color](plane_topview_color.md) · [lane_boundary_fit](lane_boundary_fit.md) · [lane_center_path](lane_center_path.md) · [stop_line_detect](stop_line_detect.md)

---
*Provenance: laneops.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
