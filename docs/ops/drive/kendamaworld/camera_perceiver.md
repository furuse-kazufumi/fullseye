---
op: camera_perceiver
dim: drive
category: kendamaworld
in: table
out: any
examples: [poc_kendama]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# camera_perceiver — DRIVE `kendamaworld` op

- **データ種**: `table` → `any`
- **呼び出し**: `import fullseye as fs; fs.ledger.camera_perceiver(world: 'dict', rig: 'list', *, fps: 'float' = 100.0, pixel_noise: 'float' = 0.0, rng=None, slack_margin: 'float' = 0.005, min_frames: 'int' = 3, window: 'int' = 128, color_tol: 'float' = 0.12, g: 'float' = 9.81, keep_frames: 'bool' = False, slack_frames: 'int' = 2, min_fill: 'float' = 0.6, reject: 'float' = 0.004, render_fn=None, holes: 'bool' = True, flight_from: 'str' = 'tie', flight_margin: 'float' = 0.012)` (実装を直接呼ぶなら `import kendamaworld; kendamaworld.camera_perceiver(world: 'dict', rig: 'list', *, fps: 'float' = 100.0, pixel_noise: 'float' = 0.0, rng=None, slack_margin: 'float' = 0.005, min_frames: 'int' = 3, window: 'int' = 128, color_tol: 'float' = 0.12, g: 'float' = 9.81, keep_frames: 'bool' = False, slack_frames: 'int' = 2, min_fill: 'float' = 0.6, reject: 'float' = 0.004, render_fn=None, holes: 'bool' = True, flight_from: 'str' = 'tie', flight_margin: 'float' = 0.012)`、台帳から引くなら `opsdrive.get("camera_perceiver")`)

## 使い方

画像だけから玉の (p̂, v̂) を出す知覚 ``perceive(t, p, v, scene) → (p̂, v̂) | None``(:func:`kendama.kendama_simulate` 用、
属性 ``observe_all = True`` で毎 step 呼ばれる)。**真値 (p, v) は世界を描くためだけに使い、v は読まない。**

コマの時刻 k / fps ごとに: (1) :func:`kendama_pose` で世界(けん = scene["hand"]、玉 = p、糸)を置き、各カメラで描く
(玉の周り ``window`` 画素の窓だけを描く: 窓は前のコマの検出(放物線が当たっていればその予測)から決め、検出が無い・窓の縁に
かかったら全画面を描き直す —— 窓の画素は全画面の切り出しと同じ)、(2) :func:`balltrack.ball_detect`(chroma、橙)で玉を検出し
画素に σ = ``pixel_noise`` のガウス雑音を足す、(3) 2 台以上で見えれば :func:`balltrack.triangulate_dlt` で 3-D に戻す、
(4) 「弛んだ」= 三角測量した玉と皿胴の糸穴(scene["tie"]: 手の自己受容で分かる)の距離がひもの有効長より ``slack_margin``
以上短いコマが ``slack_frames`` 回続いたら(1 回だと画素雑音 2 px で張っている間に誤検出した —— 測って退けた)、
その最初のコマ以降の点に重力 g 既知の放物線(:func:`kendama.parabola_fit_g` と同じ式、未知 6)を最小二乗で当てる
(``min_frames`` 点以上)。返り値 = 当てた放物線を t へ外挿した (p̂, v̂)。放物線がまだ無ければ None(計画は動かない)。

世界の玉の姿勢(描画の約束、真値): scene["taut"] の間は糸穴が皿胴の糸穴を向き、弛んだら最後の姿勢のまま(``R_ball`` に記録)。
記録(属性): ``frames`` = [{"t", "p_hat" (3,) or NaN, "uv" [(col,row)…], "full" [bool…], "tie", "hole_uv", "hole_dir"}]、
``R_ball`` = 各コマの玉の真の姿勢(穴の真の向き = R_ball @ HOLE_AXIS_LOCAL: 門の真値)、``slack_frame``(弛みを
検出したコマの索引 or None)、``fits`` = [(t_frame, n_used, p_ref, v_ref, t_ref)]、``render_s``(描画 + 検出の合計秒)、
``n_render``(描いた窓の数)、``images``(``keep_frames=True`` のとき各カメラの全画面 …… 重いので図のときだけ)。
``render_fn(world, cam) → (H, W, 3) float``: 描画を差し替える口(既定 = :func:`driveworld.world_camera` のメッシュ描画。
3DGS など)。窓だけを描くときは cam の K(主点をずらした)・width・height を窓に合わせた辞書を渡す。
``holes=True``: 玉の窓の中で :func:`kendama.hole_detect` で穴を探し(雑音を足す前の画素で)、2 台で見えたコマは穴の重心を
三角測量して玉の中心からの向き ``hole_dir``(世界の単位ベクトル)を記録する(皿の技では報告だけ、計画には使わない)。
``flight_from="cup"``(19 巡目、連続技): 「飛び始め」を糸の弛みでなく、三角測量した玉と皿に乗った玉の位置(scene["rest"] = 受けている皿の
縁の中心 + h_c·軸: 手元の自己受容で分かる)の距離が ``flight_margin`` を超えたコマが ``slack_frames`` 回続いたこと で決める(皿に乗っている
間のコマは当てはめに入れない)。scene["R_ken"] があればけんをその姿勢で描く(持ち替え)。``perceive.reset()`` で今の放物線を捨て、次の
飛び始めを待つ(記録 ``flights`` = 飛び始めのコマの索引の列)。既定 "tie" は今まで通り。
fail-closed: fps ≤ 0、pixel_noise < 0、min_frames < 2、window < 32、カメラ 2 台未満、kendama の無い世界は ValueError。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_kendama](../../../../examples/poc_kendama.py) — `py -3.11 examples/poc_kendama.py`

## 型が繋がる次の op(`any` を入力に取れる)

[course_crank](../course/course_crank.md) · [course_s_curve](../course/course_s_curve.md) · [course_turnaround](../course/course_turnaround.md) · [course_slope](../course/course_slope.md) · [course_intersection](../course/course_intersection.md) · [course_parallel_parking](../course/course_parallel_parking.md) · [course_crossing](../course/course_crossing.md) · [course_road](../course/course_road.md)

## 同カテゴリ(`kendamaworld`)

[ken_mesh](ken_mesh.md) · [add_ken](add_ken.md) · [ken_set_pose](ken_set_pose.md) · [string_mesh](string_mesh.md) · [add_string](add_string.md) · [string_set](string_set.md) · [kendama_world](kendama_world.md) · [kendama_rig](kendama_rig.md)

---
*Provenance: kendamaworld.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
