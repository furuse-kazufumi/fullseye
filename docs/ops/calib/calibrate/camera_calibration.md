---
op: camera_calibration
dim: calib
category: calibrate
in: keypoints
out: table
halcon: camera_calibration
gpu: なし
examples: [camera_intrinsics_calibration, lens_calibration_loop_demo, poc_calibration_truth_map, poc_camera_calibration]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# camera_calibration — CALIB `calibrate` op

- **データ種**: `keypoints` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_calibration(object_points, image_points_list)` (実装を直接呼ぶなら `import calib; calib.camera_calibration(object_points, image_points_list)`、台帳から引くなら `opscalib.get("camera_calibration")`)
- **HALCON 相当**: `camera_calibration`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

[部分対応] Zhang 法で平面ターゲット多視点から内部行列 K だけを推定(camera_calibration)。

する: Zhang の閉形式で K(fx, fy, cx, cy, skew)を求める。視点不足・退化・非有限は ``ValueError``。
しない: レンズ歪みの推定と、K・歪み・外部パラメータの同時の非線形最適化(HALCON の
camera_calibration の仕事)。歪みは ``camera.estimate_distortion`` で別に求める。HALCON 対応の
数え方では「部分対応」で、対応済みには数えない(``halcon_coverage.PARTIAL``)。

[Partial HALCON analogue] Closed-form K only; no distortion, no joint non-linear refinement.

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

**雑音込みの退化の門(2026-11-09)**: 上の比の門(``<= 1e-8``)は雑音ゼロでしか鳴らない。
歪みなしでも観測雑音 0.05 px があると、全視点が正面平行(傾き 0 度)で比が 1.7e-7 になって
門を抜け、fx を真値の 33 倍(+3222 %)にした K を例外なしで返していた。そこで閉形式を
解いたあと、各視点のホモグラフィ残差から雑音 σ を見積もり、画像点を σ で揺らして
解き直す(32 回、種は固定で同じ入力なら同じ判定)。fx, fy, cx, cy の標準偏差を焦点距離で
割った値のどれかが 5 % を超えるか、揺らした解き直しが 1 回でも非有限/非正の K になったら
``ValueError``(「この配置と雑音では K が決まらない」)。実測(10 視点 9x6 格子、歪みなし、
雑音 0.05 px): 傾き 0 度 → 拒否(相対標準偏差 65 %、32 回中 10 回が非正の K)、2 度 → 拒否
(5.1 %、実際の fx 誤差 −6.6 %)、5 度 → 通過(0.8 %、誤差 −1.3 %)、30 度 → 通過(0.04 %、
誤差 −0.03 %)。雑音 0.2 px では 2 度で 65 %(誤差 +28 %)→ 拒否、5 度で 3.4 %(誤差 −4.7 %)
→ 通過。見積もりは戻り値の ``intrinsics_rel_std`` に入る。**これは 1σ の広がりで、上限では
ない**: 視点の種を 10 個変えると、通過した組の実際の fx 誤差は歪みなしでも最大 14.7 %
(0.05 px・2 度、10 個中 4 個が通過)、0.2 px・5 度で最大 10.7 % になる。精度の保証が要るなら
``calib_lm.camera_calibration_lm`` の共分散を見る。しきい値 5 % の由来と、境目では判定が
種・入力で反転することは定数 ``_K_REL_STD_MAX`` / ``_K_MC_TRIALS`` の注記を見よ(5 % は 2 % で
既存テストが落ちたあとに選んだ値)。限界: (1) 歪みのある点では残差が歪みの合わなさを含み、
それを雑音として扱う(k1=−0.18・0.05 px では 5 度で 10 個中 1 個だけ通過、8 度以上は全部通過)。
偏り(歪みを無視したことによる系統誤差)は測らない: 視点の種 10 個で、通過した組の fx 誤差は
8 度で最大 20.0 %(中央値 9.3 %)、10 度で最大 13.8 %、30 度でも最大 7.2 %(cv2 は歪み込みで
8 度でも最大 0.51 %)。歪みのあるレンズの K は ``calib_lm.camera_calibration_lm`` で求める。(2) 視点の点が 4 個だと残差の
自由度が 0 で雑音を見積もれず、``intrinsics_rel_std`` は nan で門は効かない(``reproj_rms``
も 0 になり健全性を映さない)。(3) 閉形式を 33 回解くぶん遅い(10 視点 54 点で門の前
2.4 ms、門の後 13〜80 ms。計算機の混み具合で振れる)。

**スキューは自由に推定する**(5 自由度)。cv2.calibrateCamera はスキューを 0 に固定する。
歪みのあるレンズでは、歪みを無視した閉形式のしわ寄せがスキューと主点に出る: 傾き 30 度・
k1=−0.18, k2=0.03 の 10 視点で skew −6.5 px、cx +8.2 px、fy +0.98 %(cv2 は歪み込みで
fx −0.08 %、cx +0.15 px)。歪みなしでは skew 0.09 px と良い。スキュー 0 固定・歪み込みの
cv2 相当の答えが要るなら、これを初期値に使う ``calib_lm.camera_calibration_lm``
(K のスキューは 0、歪み 5 係数と全姿勢を同時に詰める)を使う。

## 詳しい使い方ガイド

- [camera_calibration ファミリ ガイド](../guides/camera_calibration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [camera_intrinsics_calibration](../../../../examples/camera_intrinsics_calibration.py) — `py -3.11 examples/camera_intrinsics_calibration.py`
- [lens_calibration_loop_demo](../../../../examples/lens_calibration_loop_demo.py) — `py -3.11 examples/lens_calibration_loop_demo.py`
- [poc_calibration_truth_map](../../../../examples/poc_calibration_truth_map.py) — `py -3.11 examples/poc_calibration_truth_map.py`
- [poc_camera_calibration](../../../../examples/poc_camera_calibration.py) — `py -3.11 examples/poc_camera_calibration.py`

## 型が繋がる次の op(`table` を入力に取れる)

[image_points_to_world_plane](../plane/image_points_to_world_plane.md) · [contour_to_world_plane_xld](../plane/contour_to_world_plane_xld.md) · [sim_caltab](../target/sim_caltab.md) · [disp_caltab](../target/disp_caltab.md) · [calibration_error_map](../calib_truth/calibration_error_map.md) · [calibration_uncertainty_map](../calib_truth/calibration_uncertainty_map.md) · [calibration_next_pose](../calib_truth/calibration_next_pose.md)

## 同カテゴリ(`calibrate`)

[find_marks_and_pose](find_marks_and_pose.md) · [hand_eye_calibration](hand_eye_calibration.md) · [camera_calibration_lm](camera_calibration_lm.md) · [stereo_calibration_lm](stereo_calibration_lm.md)

---
*Provenance: calib.py — CALIB operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
