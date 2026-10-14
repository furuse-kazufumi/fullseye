---
id: polarisation-specular-removal
title: 偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)
title_en: Remove specular reflection from a four-angle polariser sweep (dielectrics vs metals)
category: 光と色
ops: [polarization_dolp_map, polarization_separate, polarization_stokes, specular_diffuse_split]
examples: [example_polarization_metal, poc_polarization_specular, specular_photometric]
version: 0.2.0
inputs: [polsweep, rgbimage]
pipeline: [polarization_dolp_map, polarization_separate, polarization_stokes, stokes_analyze, specular_diffuse_split]
alternatives: [fresnel_conductor, fresnel_dielectric, brewster_angle_deg, specular_free_transform, specular_coefficient_map]
limits: 分離が厳密なのは「鏡面が完全直線偏光」のとき = 誘電体の Brewster 角近傍だけ。金属は鏡面が部分偏光で、偏光度 p の残り (1−p)·S が **diffuse に残る**(`example_polarization_metal` が閉形式と一致させて示す)。法線入射では鏡面も無偏光で全部 diffuse。順序違いは等間隔角度では**検出できない**(全順列で違反率 0、実測)。
calibration: 画素校正は不要。`max_violation_frac` は雑音床で決める —— 違反は無偏光成分 D が 2〜3σ を切る画素で起き、その割合が目安(実測表は `specular_photometric.md`)。
---

# 偏光 4 方向で鏡面反射を除く(誘電体と金属で分ける)

## できること

偏光板を 0/45/90/135° に回した 4 枚(または DoFP センサの 4 画素)から、画素ごとに Malus の正弦波を当てはめ、**無偏光成分**(2·I_min)と**直線偏光成分**(I_max − I_min)に分けます。前者を拡散・後者を鏡面と呼ぶのは物理的仮定で、それが成り立つ誘電体と成り立たない金属を、この項目は分けて扱います。

## What it does

Fit Malus's law per pixel to a 0/45/90/135° polariser sweep and split the radiance into its unpolarised part (2·I_min) and its linearly polarised part (I_max − I_min). Calling those "diffuse" and "specular" is a physical assumption that holds for dielectrics near Brewster's angle and fails for metals; this entry keeps the two cases apart.

## 向くところ / 向かないところ

**向く**: 誘電体(塗装・樹脂・ガラス・濡れた面)で、入射角を Brewster 角(`brewster_angle_deg`、n=1.5 で 56.3°)の近くに置けるとき。テクスチャがあっても多材質でも効く(色による分離と違い光源色が要らない)。

**向かない**: ★**金属**。鏡面反射の偏光度 p は `fresnel_conductor` の (R_s − R_p)/(R_s + R_p) で 1 に届かず、(1−p)·S が diffuse に残る —— 「鏡面を除いた」つもりの像にハイライトが残る。★法線入射(p → 0)。★フレーム列と角度列の対応は配列から検証できない(等間隔角度の並べ替えは別の方位の正しい掃引に見え、違反率 0 のまま通る —— 2026-09-15 に全順列で実測)。

## 推奨パイプライン

`polarization_dolp_map` → `polarization_separate` → `polarization_stokes` → `stokes_analyze` → `specular_diffuse_split`

`polarization_dolp_map` で**偏光板を付ける価値があるか**を先に見る(DoLP ≈ 0 なら露出を 1 段失うだけ)→ `polarization_separate` で (diffuse, specular) → `polarization_stokes` → `stokes_analyze` で場面の偏光度と方位を数字に。金属で残った鏡面は色の経路 `specular_diffuse_split`(二色性モデル、RGB 入力)で追う —— 2 つの経路は相補で、代替ではない。

## 代替

材質が分かっているなら先に `fresnel_dielectric` / `fresnel_conductor` で s/p の反射率を計算し、p = (R_s − R_p)/(R_s + R_p) から**残る鏡面の量を予測**する。色の経路は `specular_free_transform` / `specular_coefficient_map`。

## 限界

- 誘電体でも入射角が Brewster 角から離れると p < 1 で残る(n=1.5: 56° で p=1、30° で p≈0.6、0° で 0)。
- `max_violation_frac` の既定 0 は fail-closed だが、**暗い画素**(無偏光成分 D が雑音の 2〜3σ 以下)では雑音だけで当てはめ最小値が負になる。勾配シーンの実測(絶対雑音 σ、4 角度): σ=0.01 で違反率 1.5 %(D<2σ の画素 3.9 %)、σ=0.02 で 2.5 %(7.0 %)、σ=0.05 で 5.8 %(17.2 %)。表は [`specular_photometric.md`](../ops/specular/guides/specular_photometric.md)。
- 順序違いは違反率では捕まらない(上記)。角度の記録はメタデータで守る。

## 実寸校正

画素 → mm は不要。校正に相当するのは**偏光板の角度の原点**(方位は原点に相対)と `max_violation_frac`(暗部の雑音床から決める。3 σ を切る画素の割合を見積もり、その程度に置く)。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

d = np.full((64, 64), 0.4); s = np.zeros((64, 64)); s[24:40, 24:40] = 0.5
frames = fs.ledger.polarization_render(d, s, (0, 45, 90, 135), azimuth_deg=30.0)
print("DoLP max", float(np.asarray(fs.ledger.polarization_dolp_map(frames)).max()))
diffuse, specular = fs.ledger.polarization_separate.raw(frames)
print("残った鏡面", float(np.abs(diffuse - d).max()))     # 誘電体の仮定どおりなら ~0
```

## 裏づけ

- op: `polarization_separate`(分離)、`polarization_dolp_map`(価値の判定)、`polarization_stokes` / `stokes_analyze`(Stokes)、`fresnel_conductor`(金属の p)
- 例: [`example_polarization_metal`](../../examples/example_polarization_metal.py)(金属で残る鏡面を閉形式と一致させる)、[`poc_polarization_specular`](../../examples/poc_polarization_specular.py)、[`specular_photometric`](../../examples/specular_photometric.py)
