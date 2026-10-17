---
id: interreflection-to-convergence
title: 凹んだ部品の相互反射を、測光の真値を保ったまま収束まで数える(3-D の形態係数・漸進ラジオシティ・検査用の多重反射描画)
title_en: Count interreflection in concave parts to convergence without losing the photometric truth (3-D view factors, progressive radiosity, an inspection render with bounces)
category: 光と色
ops: [form_factor_parallel_rects, form_factor_perpendicular_rects, form_factor_polygons, radiosity_patches, form_factor_matrix, radiosity_progressive_3d, render_optscene_gi]
examples: [poc_pocket_interreflection]
version: 0.6.1
inputs: [table]
pipeline: [radiosity_patches, form_factor_matrix]
alternatives: [render_optscene_gi, radiosity_progressive_3d, render_optscene, render_studio, transport_matrix_radiosity, form_factors_2d]
limits: Lambert(完全拡散)だけ。シーンは箱・箱をくり抜いたポケット・有限の板(球・円筒・鏡面・加工目・欠陥は拒否)。パッチ内のラジオシティは一様で、画素の相互反射は点 → 多角形の閉形式で集め直す(遮蔽はパッチ中心への光線 1 本)。
calibration: 照明の強さは線形に効き、幾何(形態係数・画素とパッチの対応)はシーンの形・カメラ・パッチの大きさの SHA-256 で使い回すので、反射率と照明の強さを動かす較正の繰り返しではラジオシティだけを解き直す。
---

# 凹んだ部品の相互反射を、測光の真値を保ったまま収束まで数える

## できること

`render_optscene` は検査用の描画で、実在の照明器具を物理単位で置いて**直接光だけ**を数えます(測光に根拠があり、真値と突き合わせられる)。`render_studio` は多重反射まで解きますが、明るさの絶対値に意味がありません。加工ポケット・内角・箱の隅のような凹んだ部品では、向かいの壁で反射した光が底を照らすので、直接光だけのモデルを実写に合わせると、その分が反射率や照明の強さに**吸収されて、もっともらしく合ってしまいます**。

`render_optscene_gi` は同じシーン・同じカメラ・同じ照明(`illumdesign.light_source`)を受け、直接光は `render_optscene` と同じ式で数え(反射 0 回で一致)、その上に Lambert 面どうしの反射を `bounces=k` 回(Neumann 和)か `bounces=None` で収束まで足します。返すのは像・直接光だけの像・その差(相互反射の地図)・像に占める相互反射の割合と、収束の証拠(残エネルギーの履歴・撃った回数・converged)、そして反射の回数に対する観測収束比と GCI 型の見積もりから決めた「何回数えれば足りるか」です。

下ごしらえの op も単独で使えます。`form_factor_parallel_rects` / `form_factor_perpendicular_rects` は Howell のカタログ C-11 / C-14 の閉形式、`form_factor_polygons` は平らな凸多角形どうしの数値の形態係数(点 → 多角形は Lambert の輪郭和で厳密、受け側だけ Gauss 求積)、`radiosity_patches` はシーンか多角形からパッチの組を作り、`form_factor_matrix` は全対の形態係数(遮蔽はシーンの光線)、`radiosity_progressive_3d` は Cohen ら 1988 の漸進ラジオシティ(未放射エネルギー ΔB·A が最大のパッチから撃つ)です。止める閾値は論文が数で決めていないので、残エネルギー Σ ΔB·A ≤ tol × 初期のエネルギー、を**こちらの判断**として返り値に書いてあります。

PoC `poc_pocket_interreflection` は、反射率 0.7 のポケットの観測に「直接光だけ / 1 回反射 / 収束解」の 3 つのモデルを `simcal_fit` で合わせ、直接光だけのモデルが反射率 1.32(エネルギー保存に反する)で合って絶対 χ² の門と残差 PCA で落ち、収束解が真値(0.70 / 1.00)に戻って残差が白色になることを示します。

## What it does

Seven ops in `radiosity3d` (category `radiosity` of `opsoptics`). `render_optscene_gi` takes the scene, camera and lights of `render_optscene`, keeps its direct photometry exactly (zero bounces reproduce `render_optscene`), and adds Lambertian interreflection — `k` bounces as a Neumann partial sum or the converged sum by progressive radiosity (Cohen et al. 1988) — returning the image, the direct image, their difference (the interreflection map), the convergence evidence (residual unshot energy, shots, converged) and a bounce study (observed ratio of successive increments, a GCI-style estimate trusted in the asymptotic range, the bounce count that brings the remainder under a tolerance). The building blocks: Howell's closed forms C-11 and C-14, numerical view factors between flat convex polygons, patch sets from a scene or from polygons, the all-pairs view-factor matrix with occlusion, and the progressive solver whose stopping rule (residual energy below `tol` of the initial) is stated as our choice.

## 向くところ / 向かないところ

**向く**: 凹んだ部品の検査画像の順方向モデル(sim-to-real の較正で、相互反射を係数に吸収させない)、照明の設計で「底がどれだけ明るくなるか」を数える、直接光だけのモデルの誤差の見積もり、反射を何回数えれば足りるかを数で決める。

**向かない**: ★鏡面・金属の相互反射は扱いません(導体・誘電体の材質は ValueError)。鏡面の真値には `gi_render`(Mitsuba、optional)。球・円筒・入れ子の差集合・傾いた面(V 溝)のシーンも拒否します —— 押し出し形状なら `lighttransport` の 2-D(`transport_matrix_radiosity`)か、多角形を直接 `radiosity_patches(polygons=...)` に渡してください。ToF の位相への影響は扱いません。

## 推奨パイプライン

`radiosity_patches` → `form_factor_matrix`

シーンをパッチに割り → 全対の形態係数を見る(どの壁がどの壁をどれだけ照らすか)。解いて描くのは `render_optscene_gi` 1 本で、中で同じ順に割って形態係数を作り、`radiosity_progressive_3d` の漸進法で収束まで解き、画素に集め直して直接光の像に足します。放射を自分で決めたいとき(光る面・多角形のパッチ)は `radiosity_progressive_3d` を直接呼びます。

## 代替

直接光だけでよいなら `render_optscene`。見せる絵なら `render_studio`。溝の軸方向に長い形なら 2-D の `form_factors_2d` / `transport_matrix_radiosity`(crossed-strings の厳密解、縞投影と ToF の誤差の予測つき)。

## 限界

- Lambert だけ。パッチ内は一様なラジオシティ(パッチを細かくして真値との差を数えること —— PoC では 1.5 / 1.0 / 0.7 mm で雑音の 0.18 / 0.11 / 0.06 倍)。
- 画素の相互反射の遮蔽はパッチ中心への光線 1 本(パッチの一部だけ隠れる配置では 0/1 に丸まる)。
- 反射の回数の見積もりは等比級数の比を使う。漸近域(比が 2 回続けて 5 % 以内)より前では楽観しうる(PoC で k = 3 に実測)。

## 実寸校正

座標は optscene と同じ mm、明るさは `render_optscene` と同じ線形の放射輝度。カメラの DN にするには露光の係数を掛けて黒レベルを足す(PoC は EMVA 1288 の線形カメラの雑音模型で)。

## 最初の 1 本

```python
import illumdesign as ID
import optscene as OS
import radiosity3d as R

m = OS.scene_material("lambert", albedo=0.7)
pocket = OS.scene_difference(OS.scene_box((0, 0, 7), (14, 11, 7), m), OS.scene_box((0, 0, 12), (10, 7, 8)))
scene = [pocket, OS.scene_plane(0.0, OS.scene_material("lambert", albedo=0.0))]   # 黒い台
cam = OS.optical_camera(focal_mm=12.0, pixel_um=27.6, resolution=(64, 64), working_distance_mm=200.0)
light = ID.light_source(kind="dome", radius_mm=60.0, n=48)

r = R.render_optscene_gi(scene, cam, light, bounces=None, patch_mm=2.0, outer_mm=4.0, study_bounces=8)
print(r["converged"], r["n_patches"], round(float(r["indirect_share"].max()), 2))   # True、相互反射の割合の最大
print(r["bounces_needed"])                                                            # 像の 1 % まで何回反射を数えるか
print(round(R.form_factor_perpendicular_rects(), 6))                                  # 0.200044(Howell C-14)
```
