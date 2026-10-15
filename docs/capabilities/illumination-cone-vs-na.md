---
id: illumination-cone-vs-na
title: 照明の円錐と観察の NA で、鏡面の小さな傾きを出す・消す(球冠の交わり → 傾きの帯 → 打痕・傷・梨地)
title_en: Illumination cone versus imaging NA on specular parts (cap intersection, slope bands, dents, scratches and satin)
category: 光と色
ops: [solid_angle_light, solid_angle_boundaries, solid_angle_brightness, solid_angle_sweep, solid_angle_render]
examples: [poc_illumination_cone_vs_na]
version: 0.6.1
inputs: [normalmap]
pipeline: [solid_angle_light, solid_angle_boundaries, solid_angle_sweep, solid_angle_brightness, solid_angle_render]
alternatives: [light_source, defect_contrast, lighting_sweep, illumination_design, micro_normals, blast_normals]
limits: 照明は各点に同じ円錐が届く遠方場の極限(ケーラー照明・光源を無限遠に置いた照明)、カメラはテレセン(どの画素も真上から同じ円錐)。Fresnel の反射率は小さな角では一定、回折・多重反射・円錐の中の放射輝度のむらは入れていない。粗さは微小面の傾きのガウス分布(σ 30° まで)。
calibration: 円錐の半角 α は照明の開口(絞り)の半径と照明レンズの焦点距離から α = atan(r/f)、観察の半角 β は物体側 NA の asin。境界 |α − β|/2・(α + β)/2 は鏡面の傾きの角度なので尺度の校正は要らないが、α と β の実測(光源像の大きさ・レンズの NA)が要る。
---

# 照明の円錐と観察の NA で、鏡面の小さな傾きを出す・消す(球冠の交わり → 傾きの帯 → 打痕・傷・梨地)

## できること

鏡面に近い金属部品では、浅い打痕(傾き 0.1〜0.5°)やヘアラインの上の傷、梨地のムラが「同軸落射で見えたり見えなかったりする」。どう見えるかは、光源の種類より先に**各点に届く光の円錐の半角 α と向き ψ**、それとカメラが受け取る円錐(物体側 NA、半角 β = asin NA)の関係で決まります。顕微鏡のケーラー照明でいう照明の NA と対物の NA、シュリーレン法のナイフエッジと同じ幾何です。

鏡面での反射は方向の球の上の等長写像なので、面が θ 傾くと反射した円錐は形を保ったまま 2θ 振れ、カメラが記録する明るさは**2 つの球冠の交わり**(閉形式)になります。|2θ| ≤ |α − β| なら片方の円錐がもう片方に収まって明るさは変わらず(その傾きは見えない)、|2θ| ≥ α + β で暗、その間だけ明るさが傾きで変わります。

`solid_angle_light` は円錐(半角・傾き・方位・放射輝度)で照明を決め、`irradiance_map` / `defect_contrast` にもそのまま渡せる光源の dict を返します。`solid_angle_boundaries` は見えない傾き |α − β|/2、暗くなる傾き (α + β)/2、平らな地の明るさと感度を閉形式で返し、`solid_angle_brightness` は傾きごとの明るさを閉形式とレンズの瞳の数値積分(射影立体角の重み)の両方で、粗い面(微小面の傾きの広がり σ)まで返します。`solid_angle_sweep` は α を振った欠陥のコントラスト、`solid_angle_render` は法線マップ(`metalfinish.micro_normals` のヘアライン、`blast_normals` の梨地など)をその照明とレンズで撮った画像です。

PoC `poc_illumination_cone_vs_na` は、閉形式と瞳の数値積分の差(0.002)、画像から測った打痕のコントラストと閉形式の差(0.0004)、ヘアラインの筋は消して傷だけを黒くする α を閉形式で選べること、円錐を β 傾けると傾きの符号が明暗で読めること、うねりと粗さで設計が効かなくなることを採点します。

## What it does

Five ops in `illumdesign` (category `illumination`) for lights defined by the cone of directions they deliver to every point (the far-field / Koehler limit), against a camera of object-side NA. On a specular facet the reflection moves the cone by 2θ without changing it, so the brightness is the intersection of two spherical caps, a closed form: slopes below |α − β|/2 do not show, slopes beyond (α + β)/2 go dark. The ops return the light, the closed-form slope thresholds, the brightness per slope (closed form and a projected-solid-angle pupil integral, with Gaussian micro-facet roughness), the contrast versus the cone half-angle, and an image of a normal map under the light. The PoC checks the closed form against the pupil integral (0.002) and against contrasts measured from rendered images (0.0004), chooses a cone that hides hairline marks while blackening a 4° scratch, reads the slope sign with a tilted cone, and shows waviness and roughness defeating the design.

## 向くところ / 向かないところ

**向く**: 鏡面・光沢面(研磨・ヘアライン・めっき・ガラス・ウェハ)の傾きの欠陥の照明設計 —— 見たい傾きの帯だけを残す α の選び方、消したい模様(研磨目・筋)の傾きの上限からの α の下限、傾きの符号を読むための円錐の傾け方、照明の開口を絞る/広げる/ずらす効果の事前の見積り。

**向かない**: ★照明は遠方場の極限で、近接した拡散板の同軸照明のように場所ごとに円錐の向きが変わる光源は `light_source("coaxial")` と `defect_contrast` の側です。カメラはテレセンを仮定し、通常のレンズの主光線の傾き(視野の端で ψ が実質的に変わる)は入りません(`chief_ray_angle` で傾きを求めて ψ に足す)。拡散面(紙・樹脂の梨地の奥の拡散)の明るさは `diffuse_albedo` の閉形式 sin²α cos γ だけで、多重散乱は入りません。粗い面(σ が (α + β)/2 を越える)ではどの円錐でも傾きの差が微小面の広がりに埋もれ、設計が効きません。

## 推奨パイプライン

`solid_angle_light` → `solid_angle_boundaries` → `solid_angle_sweep` → `solid_angle_brightness` → `solid_angle_render`

観察の NA を決め(β = asin NA)→ `solid_angle_boundaries` で、消したい模様の傾きが |α − β|/2 の内側、見たい欠陥の傾きが (α + β)/2 の外側に来る α の範囲を閉形式で出す → `solid_angle_sweep` で α を振ってコントラストの山を確かめる → `solid_angle_brightness` で粗さ σ を入れて崩れ方を見る → `solid_angle_render` に法線マップ(`micro_normals` / `blast_normals` / 高さの勾配)を渡して画像で確かめる。

## 代替

光源の形(リング・ドーム・同軸・バックライト)と仰角から選ぶなら `illumination_design` / `lighting_sweep` / `defect_contrast`。金属の仕上げの見た目(異方性のハイライト)を描くなら `finish_shade`。

## 限界

- 照明は各点に同じ円錐が届く遠方場の極限、カメラはテレセン。
- Fresnel の反射率は小さな角では一定(`f0`)。回折(瞳が小さいと 1.22λ/NA のぼけ)、多重反射、円錐の中の放射輝度のむらは入れていない。
- 閉形式は瞳を立体角で一様に重みづけた値。レンズの瞳は射影立体角で重みづくので、数値積分との差は NA とともに育つ(NA 0.3 で 0.005 未満)。
- 粗さは微小面の傾きのガウス分布で、σ は 30° まで。

## 実寸校正

境界は傾きの角度なので画像の尺度は要らない。要るのは α と β: α は照明の開口の半径 r と照明レンズの焦点距離 f から atan(r/f)(光源像の大きさを測る)、β は物体側 NA の asin。

## 最初の 1 本

```python
import math
import illumdesign as ID

na = 0.033                                   # 物体側 NA(β = 1.89°)
beta = math.degrees(math.asin(na))
for alpha in (beta, 4.0, 7.0):
    b = ID.solid_angle_boundaries(ID.solid_angle_light(alpha), view_na=na)
    print(round(alpha, 2), round(b["invisible_below_deg"], 3), round(b["dark_beyond_deg"], 3))
# 1.89 0.0 1.891 / 4.0 1.054 2.946 / 7.0 2.554 4.446
r = ID.solid_angle_brightness(ID.solid_angle_light(4.0), view_na=na, slopes_deg=[0.5, 2.0, 4.0])["rows"]
print([round(x["closed_form"], 3) for x in r])   # [1.0, 0.45, 0.0]: 0.5° の筋は消え、4° の傷は黒い
```

走らせて見るなら `py -3.11 examples/poc_illumination_cone_vs_na.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
