---
op: camera_calibration
dim: calib
category: calibrate
in: points
out: table
examples: [lens_calibration_loop_demo, poc_camera_calibration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.0  # fullseye lib version this note was generated for
---

# camera_calibration — CALIB `calibrate` op

- **データ種**: `points` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_calibration(object_points, image_points_list)` (実装を直接呼ぶなら `import calib; calib.camera_calibration(object_points, image_points_list)`、台帳から引くなら `opscalib.get("camera_calibration")`)

## 使い方

Zhang 法で平面ターゲット多視点から内部行列 K を推定(camera_calibration)。

``object_points``: (N,2) 平面ターゲット座標 **(x, y)**(z=0 平面、ワールド単位)。
``image_points_list``: 各視点の (N,2) 画素対応。**(row, col)** — このモジュールの
他 API(``project_3d_point`` の戻り値、``image_points_to_world_plane`` の入力)と
同じ規約。内部で (x=col, y=row) に並べ替えてから解くので、``fx``/``cx`` は
col 軸、``fy``/``cy`` は row 軸の値になる(2026-09-02 以前は (x,y) として
扱っており fx↔fy, cx↔cy が入れ替わっていた)。

fail-closed: 視点が 3 未満、すべての視点が正面平行(回転不足)で解が定まらない、
または K が非有限/非正になる場合は ``ValueError``(NaN を返さない)。戻り値の
``homographies`` は (x,y)→(x=col,y=row) の 3x3、``reproj_rms`` は各視点の
ホモグラフィ再投影 RMS [px] (対応づけの健全性チェックに使う)。

``orientation_rank_ratio`` は視点の向きが内部パラメータをどれだけ拘束して
いるか(``sv[-2]/sv[0]``、大きいほど良い)。**再投影誤差は配置の良し悪しを
映さない** —— 2026-09-06 の実測で、同じ 10 視点・同じ雑音 0.05 px で板の
傾きだけを 32 度から 2 度に変えると、再投影 RMS は 0.0690 と 0.0688 で
比 1.00 倍のまま、fx の誤差は 0.026 % から **7.33 %(281 倍)**になった。
この比のほうは 129 倍動く。ただし**歪み補正前の点では意味を持たない**
(下の門の注記を見よ)。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [lens_calibration_loop_demo](../../../../examples/lens_calibration_loop_demo.py) — `py -3.11 examples/lens_calibration_loop_demo.py`
- [poc_camera_calibration](../../../../examples/poc_camera_calibration.py) — `py -3.11 examples/poc_camera_calibration.py`

## 型が繋がる次の op(`table` を入力に取れる)

[sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md)

## 同カテゴリ(`calibrate`)

[find_marks_and_pose](find_marks_and_pose.md) · [hand_eye_calibration](hand_eye_calibration.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
