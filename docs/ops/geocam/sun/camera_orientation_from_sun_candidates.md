---
op: camera_orientation_from_sun_candidates
dim: geocam
category: sun
in: keypoints × signal × signal
out: table
examples: [poc_public_camera_heading_real]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# camera_orientation_from_sun_candidates — GEOCAM `sun` op

- **データ種**: `keypoints × signal × signal` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_orientation_from_sun_candidates(candidates, frame_index, unix_times, lat_deg, lon_deg, shape, K=None, hfov_range_deg=(25.0, 120.0), tol_px=20.0, roll_max_deg=12.0, pitch_range_deg=(-40.0, 0.0), min_dt=1800.0, max_pairs=600, seed=0)` (実装を直接呼ぶなら `import geocam; geocam.camera_orientation_from_sun_candidates(candidates, frame_index, unix_times, lat_deg, lon_deg, shape, K=None, hfov_range_deg=(25.0, 120.0), tol_px=20.0, roll_max_deg=12.0, pitch_range_deg=(-40.0, 0.0), min_dt=1800.0, max_pairs=600, seed=0)`、台帳から引くなら `opsgeocam.get("camera_orientation_from_sun_candidates")`)

## 使い方

フレームごとに複数ある「明るい塊」の候補(太陽・白い車・標識・文字が混じる)から、**時刻どおりに動く 1 本**を
RANSAC で選び、(yaw, pitch, roll) と焦点距離を同時に決める → table。固定カメラでは太陽だけが太陽の速さで動く
ので、見た目で太陽を決めずに動きで決める(Fintraffic 天候カメラでは見た目の門が 24/24 誤検出だった、2026-09-21)。

仮説 = 時刻差 ≥ ``min_dt`` の 2 フレームから候補を 1 つずつ → ``camera_orientation_from_sun`` と同じ Wahba の
2 点解。**道路カメラの事前知識**(|roll| ≤ ``roll_max_deg``、pitch が ``pitch_range_deg``、水平画角が
``hfov_range_deg``)を満たさない仮説は捨てる —— 自由度 4(回転 3 + 焦点距離)に対して候補が多いと、偶然の 3 点で
非物理な姿勢が通るため。票 = 予測位置から ``tol_px`` 以内に候補があるフレーム数(地平線下の時刻は投票しない)。実写のブルーム中心は 5〜13 px ぶれる(雲・露出)ので既定 20 px。最良仮説のインライアで焦点距離を
1 次元最適化し、回転を全点で引き直す(2 回)。

**濡れた路面に映った太陽の反射も太陽の速さで動く**(鏡像)ので、動きだけでは区別できない。反射は画像の下側(路面)に
あるから、それを太陽として当てはめると「カメラが上を向く」姿勢(pitch > 0)になる —— 既定の ``pitch_range_deg`` の上限 0 は
そのための門(道路カメラは上を向かない)。上を向くカメラなら広げること。独立な検算(車線の消失点の仰角 ≈ 0)も勧める。

``K`` を渡せばそれを使う(焦点距離は探索しない)。``K=None`` なら主点は画像中心、``fx = fy = f`` を
``hfov_range_deg`` の範囲で探索する —— 公開カメラは内部パラメータが無いのが普通。

Args:
    candidates: (N, 2) の (u, v)。全フレームの候補を積んだもの(``sun_bloom_fit`` や ``sun_pixel_position`` の出力)。
    frame_index: (N,) 各候補がどのフレームか(``unix_times`` の添字、整数値)。
    unix_times: (F,) 各フレームの UNIX 秒(UTC)。
    lat_deg, lon_deg: カメラの位置。
    shape: (H, W)。
    K: (fx, fy, cx, cy) か None。
Returns:
    table: ``yaw_deg`` / ``pitch_deg`` / ``roll_deg`` / ``f_px`` / ``hfov_deg`` / ``K``(4,)/ ``inlier``(N,、1 = 採用)/
    ``n_inliers`` / ``n_frames`` / ``n_frames_with_candidates`` / ``residual_deg``(採用点の角度残差 RMS)/
    ``max_residual_deg`` / ``residual_px`` / ``loo_px``(1 点抜き予測誤差の平均)/ ``loo_max_px`` / ``span_h``
    (採用点の時間幅)/ ``n_hypotheses``(事前知識を通った仮説の数)/ ``at_prior_bound``(1 = 答えが事前知識の縁に張り付いている: 信用しない)。
Raises:
    ValueError: 候補が 2 フレーム未満、事前知識を通る仮説が無い、インライアが 3 未満。

## 詳しい使い方ガイド

- [geocam ファミリ ガイド](../guides/geocam.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_public_camera_heading_real](../../../../examples/poc_public_camera_heading_real.py) — `py -3.11 examples/poc_public_camera_heading_real.py`

## 型が繋がる次の op(`table` を入力に取れる)

[render_skyline_view](../skyline/render_skyline_view.md) · [camera_orientation_from_skyline](../orientation/camera_orientation_from_skyline.md)

## 同カテゴリ(`sun`)

[sun_position](sun_position.md) · [sun_pixel_position](sun_pixel_position.md) · [camera_orientation_from_sun](camera_orientation_from_sun.md) · [sun_bloom_fit](sun_bloom_fit.md)

---
*Provenance: geocam.py — GEOCAM operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
