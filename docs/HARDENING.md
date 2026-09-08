# PoC が上げた堅牢性 —— 見つけて直した記録

**Language:** [日本語](HARDENING.md) · [English](HARDENING.en.md)

PoC は展示であると同時に **不具合発見器**です。ここはその台帳 ——
**どの PoC が見つけ、どこを直し、どの門で再発を止めたか**を 1 件 1 ファイルで貯めます。

門(`tests/test_capabilities.py`)が `found_by` を実在する PoC に、
`ops` を 4 層(`fs.` / `fs.op.` / `fs.ledger.` / `op_find`)に、`gate` を
実在する試験関数に、`where` を実在するファイルに照らします。
**`status: fixed` なのに `gate` が空の記録は、そもそも索引を作らせません** ——
「直した」という記録だけが残って再発を止められない状態を、この台帳自身が作らないため。

* できることから引くなら → [CAPABILITIES.md](CAPABILITIES.md)
* 詳しい経緯と数字は → [KNOWN_ISSUES.md](KNOWN_ISSUES.md)

**7 件(うち直したもの 7 件)。見つけた PoC は 7 本。**

## 種別ごと

| 種別 | 件数 | 直した |
|---|---:|---:|
| 静かに間違う(例外が出ない) | 3 | 3 |
| 実装の誤り | 1 | 1 |
| 在るのに引けない | 2 | 2 |
| 説明の穴(片道の参照・古い数字) | 1 | 1 |

## 見つけた PoC ごと

| PoC | 件数 |
|---|---:|
| [`poc_geodetic_height_frames`](../examples/poc_geodetic_height_frames.py) | 1 |
| [`poc_livestock_body_volume`](../examples/poc_livestock_body_volume.py) | 1 |
| [`poc_multibeam_bathymetry`](../examples/poc_multibeam_bathymetry.py) | 1 |
| [`poc_print_registration`](../examples/poc_print_registration.py) | 1 |
| [`poc_search_sweep_width`](../examples/poc_search_sweep_width.py) | 1 |
| [`poc_stockpile_volume`](../examples/poc_stockpile_volume.py) | 1 |
| [`poc_thermal_radiometry`](../examples/poc_thermal_radiometry.py) | 1 |

## 記録

### 静かに間違う(例外が出ない)

#### [ECEF→測地座標が、自分の逆関数が拒否する緯度 180 度を黙って返していた](hardening/ecef-to-geodetic-returned-latitude-180.md)

地球の中心付近を渡すと **lat = 180.0000 度**が返る —— 緯度として存在しない値。しかも `dem_geodetic_to_ecef` 自身が「lat_deg must be within [-90, 90]」で**拒否する**値だった。**自分が産んだ値を自分の逆関数が受け取れない**。例外は出ないので、下流は「もっともらしい数字」を受け取る。

見つけた PoC: `poc_geodetic_height_frames` / 直した所: `demops.py` / 門: `test_ecef_to_geodetic_refuses_the_region_where_latitude_is_not_unique`, `test_ecef_to_geodetic_never_returns_a_latitude_its_own_inverse_rejects` / 状態: fixed

#### [位置合わせが、賛成率 1.00 のまま 80.85 px 外していた](hardening/frame-align-inlier-ratio-is-not-confidence.md)

網点のような**繰り返し構造**では、`frame_align` の `inlier_ratio` が **1.00 のまま 80.85 px 外す**。独立に再現した((0, 1.30) の真値に対し (54.24, 30.12) を返す)。例外は出ず、賛成率という「自信ありげな数字」だけが残る。

見つけた PoC: `poc_print_registration` / 直した所: `astrostack.py` / 門: `test_inlier_ratio_is_not_a_probability_that_the_answer_is_right`, `test_a_tie_in_the_smoothed_vote_no_longer_picks_an_empty_bin` / 状態: fixed

#### [頑健な雑音推定が整数画像で 0 に潰れ、点目標検出が黙って何も返さなくなっていた](hardening/noise-sigma-mad-collapses-on-quantised-data.md)

`noise_sigma(method="mad")` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返す。返せる値は **1.4826 の倍数だけ**で、σ=1.0 も σ=1.983 も**同じ 1.4826**。14 bit の生 DN はまさに整数なので、これは特殊な入力ではない。下流の影響を独立に確認: 200x200 の整数フレームに**点目標を 2 個植えて `star_detect` が 0 個**を返した(例外なし)。

見つけた PoC: `poc_thermal_radiometry` / 直した所: `astrostack.py` / 門: `test_mad_warns_when_quantisation_collapses_it_to_zero`, `test_star_detect_refuses_instead_of_silently_finding_nothing` / 状態: fixed

### 実装の誤り

#### [可視領域が、目線より高いセルを軒並み「見えない」と返していた](hardening/dem-viewshed-self-occlusion.md)

平地に置いた円錐の**頂点**が、60 m 先・目線 2.0 m の開けた平地から可視 0.0。目線より高い 1541 セルの可視は **0 個**、底面の遮蔽率 0.8863(閉形式 0.5710)。独立に最小再現: 平地に高さ 10 m の柱を立てると可視 0.0、目線より低い 1 m の柱は 可視 1.0。**凸な立体の最高点は外から必ず見える**ので、幾何として誤り。

見つけた PoC: `poc_stockpile_volume` / 直した所: `demops.py` / 門: `test_a_hill_taller_than_the_eye_is_visible_from_the_open`, `test_the_wall_itself_is_visible_even_though_its_far_side_is_not`, `test_a_hill_is_hidden_only_when_the_sight_line_passes_below_the_wall` / 状態: fixed

### 在るのに引けない

#### [空間彫刻の姿勢ヘルパが引けず、同名の別規約を掴むと例外なく空の hull が返った](hardening/carve-look-at-unreachable-and-silent.md)

`carve` / `synthesize_silhouette` が要求する姿勢は OpenCV 規約(`X_cam = R X + t`、**+Z 前方**)。それを作る `visualhull.look_at` は `fs.` / `fs.op.` / `fs.ledger.` の**どこからも引けず**、`op_find("look")` も **0 件**。一方、公開層で `look_at` の名を持つのは `render3d` の gluLookAt 版(4x4・**−Z 前方**)。その `M[:3,:3], M[:3,3]` を渡すと全点がカメラ後方に落ち、**例外を出さずに空のシルエット → 空の hull** が返る。独立に再現(立方体 8000 点で 正しい姿勢なら前景 2240 px、gluLookAt 由来で 0 px)。

見つけた PoC: `poc_livestock_body_volume` / 直した所: `visualhull.py`, `ops3d.py`, `render3d.py` / 門: `test_carve_look_at_is_reachable_from_the_public_tiers`, `test_the_public_look_at_is_the_other_convention_and_says_so` / 状態: fixed

#### [op_find が和文の複数語クエリに構造的に盲目だった](hardening/op-find-blind-to-japanese-queries.md)

副画素重心つきで点状目標の座標を返す 2-D op は `star_detect` だけなのに、`op_find("小さい目標 検出")` / `("スポット 検出")` / `("漂流 捜索")` は**いずれも 0 件**。英語の "point target detection" でようやく 20 件中 14 番目。名前が天文に閉じているせいだと思って docstring に説明語を足したが、**それでも 0 件のままだった**。

見つけた PoC: `poc_search_sweep_width` / 直した所: `opassist.py`, `astrostack.py` / 門: `test_op_find_answers_japanese_queries` / 状態: fixed

### 説明の穴(片道の参照・古い数字)

#### [ベクトル版 refract が、per-ray 版 refract_rays の存在に触れていなかった](hardening/refract-one-way-reference.md)

`refract` の docstring は「(N,3) バッチも通るが **1 本でも TIR ならバッチ全体が `None`**。バッチで使うなら呼び出し側で **1 本ずつ回すこと**」とだけ書いていた。ところが**光線ごとに TIR を判定して (方向, マスク) を返す `refract_rays` が既にある**(`refract_rays` 側からの参照は在った)。

見つけた PoC: `poc_multibeam_bathymetry` / 直した所: `match3d.py` / 門: `test_refract_points_at_the_per_ray_version_it_used_to_hide` / 状態: fixed
