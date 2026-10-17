---
id: noncoaxial-optics
title: 非共軸の光学系(折り返しミラー・半透鏡・傾いた平板・シャインプルーフ・ゴースト)
title_en: Non-coaxial optics (fold mirrors, beamsplitters, tilted plates, Scheimpflug and ghosts)
category: 光と色
ops: [noncoaxial_system, noncoaxial_example, noncoaxial_layout, noncoaxial_trace, noncoaxial_spot, image_orientation, beamsplitter_branches, tilted_plate_shift, scheimpflug_tilt, surface_reflectance, ghost_analysis, ghost_image, ghost_path, noncoaxial_drawing]
examples: [poc_noncoaxial_optics]
version: 0.6.1
inputs: [table]
pipeline: [noncoaxial_system, noncoaxial_trace, image_orientation, ghost_analysis, noncoaxial_drawing]
alternatives: [lens_system, spot_stats, tilted_plate_shift, scheimpflug_tilt, surface_reflectance, lens_section_drawing]
limits: ゴーストは 2 回反射まで(3 回以上・散乱・鏡筒の迷光は持たない)。各面の反射率は視野の主光線の入射角での無偏光の値で、半透鏡の膜は与えた R(角度・波長の依存なし)。光線の狙いは絞りの点への Newton 法(狙えない光線は無効として数える)。近軸量(EFL・瞳)は共軸の処方から変換した系だけで、ほかは実光線の近軸極限で焦点を求める。
calibration: 長さは mm、角度は度。処方の数値がそのまま実寸で、校正は要らない。
---

# 非共軸の光学系(折り返しミラー・半透鏡・傾いた平板・シャインプルーフ・ゴースト)

## できること

`raytrace` の処方は光軸が 1 本の直線の共軸系でした。`raytrace3d` は面ごとに 3-D の姿勢(回転と原点)を持たせ、座標の切り替え(偏心してから x → y → z の順に回す。`undo` で逆順に戻す)、元の座標系への戻り、折り返しミラー(`fold_mirror`、45° で 90° 折れる)、傾いた平行平板や楔、平板の半透鏡(透過と反射の 2 本の枝)を組めます。面の式(円錐 + 偶数次の非球面)と屈折・反射の式は `raytrace` のままで、共軸の処方を変換した系は `raytrace.trace_rays` と 1e-12 で同じ交点・光路長になります。

`image_orientation` は反射の回数と像の裏返り・回転を、`beamsplitter_branches` は半透鏡の 2 本の枝の像を、`tilted_plate_shift` は傾いた平板の横ずれ・焦点ずれ・非点隔差を閉形式で、`scheimpflug_tilt` は傾いた物面に対する像面の傾き(tanθ' = m·tanθ)とヒンジを閉形式と実光線で返します。`surface_reflectance` は材料表の屈折率と膜(`filmoptics` の特性行列)から面の残留反射率を出し、`ghost_analysis` は全ての 2 面の組のゴーストの焦点・像面上の大きさ・相対強度(エネルギー比・点光源と広い光源の照度比)を表で、`ghost_image` は像面の照度の図で返します。`optdraw.noncoaxial_drawing` は折り返した系を実寸の断面図・設置図にします。

PoC `poc_noncoaxial_optics` は、同軸落射の半透鏡の裏面が作るゴーストが鏡面の部品に偽の凹みを写す様子を計算し、入射角に合わせた膜と楔の板で消えることを、外の真値(Householder の鏡映、Smith / Coddington の平板の式、Fresnel、OSS の optiland との照合)で確かめます。

## What it does

Thirteen ops in `raytrace3d` (category `noncoaxial` of `opsoptics`) give every surface of a sequential system a 3-D pose: coordinate breaks (decenter, then rotate about x, the new y, the new z; `undo` reverses one), returns to an earlier frame, fold mirrors, tilted or wedged plates and plate beamsplitters with a transmit and a reflect branch. Surfaces and the refraction / reflection law are `raytrace`'s own, so a coaxial prescription traces identically (1e-12). Ops report image orientation (reflections, handedness), both beamsplitter branches, closed-form tilted-plate shift and astigmatism, the Scheimpflug image tilt with a real-ray check, residual surface reflectance from the material table and thin-film stacks, and every two-reflection ghost (focus, size on the sensor, energy and irradiance ratios) as a table and an image. `optdraw.noncoaxial_drawing` draws folded systems to scale.

## 向くところ / 向かないところ

**向く**: 同軸落射・折り返し・プリズムの代わりの鏡を含む検査光学系の配置の検討、半透鏡や窓・保護ガラスのゴーストと偽の欠陥の見積り、反射防止膜の効き目の比較、傾いた面を撮るシャインプルーフ配置の設計、装置の外形(占有の幅と高さ)の図。

**向かない**: ★3 回以上の反射・散乱・鏡筒の内面の迷光は扱いません(逐次の光線追跡で、2 回反射のゴーストだけ)。半透鏡の膜は与えた反射率で、角度・波長・偏光の依存は持ちません(面の膜は `filmoptics` で角度つき)。非共軸の系の最適化・公差解析は `lensopt` / `tolerance_analysis` が共軸の処方にしか効きません。

## 推奨パイプライン

`noncoaxial_system` → `noncoaxial_trace` → `image_orientation` → `ghost_analysis` → `noncoaxial_drawing`

要素の列(面・折り返し・平板・座標の切り替え)から `noncoaxial_system` で系を組み → `noncoaxial_trace` で視野ごとの実光線の束と像面の点 → `image_orientation` で像の向き(鏡の数で裏返る)→ `ghost_analysis` で 2 回反射のゴーストの表(半透鏡・窓の面の膜を変えて比べる)→ `noncoaxial_drawing` で設置図。

## 代替

共軸のレンズだけなら `lens_system` と `spot_stats`(近軸量・Seidel・公差まで揃う)。平板やシャインプルーフの数字だけなら `tilted_plate_shift` / `scheimpflug_tilt`(閉形式)。膜の分光反射率は `filmoptics.multilayer_reflectance`、共軸の断面図は `lens_section_drawing`。

## 限界

- ゴーストは 2 回反射まで。像面の照度の図は視野 0 の点像のゴーストの形を使う。
- 半透鏡の膜は与えた反射率(角度・波長に依らない)。各面の反射率は主光線の入射角での無偏光の値。
- 光線の狙いは絞りの点への Newton 法。狙えない光線(ケラレ・全反射)は無効として数える。

## 実寸校正

処方の数値(mm・度)がそのまま実寸。図(`noncoaxial_drawing`)も実寸の mm で描く。

## 最初の 1 本

```python
import raytrace3d as R3

s = R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": "BK7", "ap": 12.5},
                 {"R": float("inf"), "t": 40.0, "n": 1.0},
                 {"type": "fold_mirror", "tilt": (45.0, 0.0), "ap": 30.0, "t": None}], stop=0)
print(R3.image_orientation(s)["reversed"])          # True(鏡 1 枚で像は裏返る)
g = R3.ghost_analysis(R3.noncoaxial_example("epi_beamsplitter"))
print(g["ghosts"][0]["label"], round(g["ghosts"][0]["energy_ratio"], 4))   # BS:front/BS:back 0.0265
```
