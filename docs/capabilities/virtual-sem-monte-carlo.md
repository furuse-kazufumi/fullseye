---
id: virtual-sem-monte-carlo
title: 仮想 SEM —— 電子と固体の相互作用をモンテカルロで解き、加速電圧・検出器・帯電で像と線幅がどう変わるかを実測値で採点しながら見る
title_en: A virtual SEM — solve the electron-solid interaction by Monte Carlo and see, scored against measured data, how voltage, detector and charging change the image and the measured line width
category: 測る
ops: [sem_electron_mc, sem_yield_curve, sem_se_universal_curve, sem_line_profile, sem_cd_measure, sem_image, sem_charging_series, sem_se_escape_fraction, material_electron_properties]
examples: [poc_virtual_sem_kv_cd_bse]
version: 0.6.1
inputs: [image2d, pairs]
pipeline: [material_electron_properties, sem_electron_mc, sem_line_profile, sem_cd_measure, sem_image]
alternatives: [sem_render, sem_yield_curve, sem_charging_series]
limits: 重元素(W・Au)の δ(E) の形は普遍曲線より裾が厚く合わない(SE2 が主、未解決)。δmax は Lin & Joy の表の約 0.8 倍。帯電の負の側は現象論。像は画素ごとの直接 MC なので高加速・大きな像は遅い。「低加速ほど側壁の上を測る」は側壁 88 度で成り立ち 80 度では逆(`poc_virtual_sem_kv_cd_bse`)。
calibration: 高さ場・線幅・画素は nm のまま入れる。材料は `material_electron_properties` の名前で引き、表に無い材料の λ・ε は推定と明記される。実機と合わせるなら既知の材料(Si・Au)の η と δ を同じ加速電圧で測って比べる。
---

# 仮想 SEM —— 電子と固体の相互作用をモンテカルロで解き、加速電圧・検出器・帯電で像と線幅がどう変わるかを実測値で採点しながら見る

## できること

一次電子を固体の中で 1 個ずつ追うモンテカルロ(Joy の単散乱モデル。弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo 1989)で、反射電子係数 η・二次電子収率 δ・到達深さを `sem_electron_mc` が、δ(E) の形を `sem_yield_curve` が出します。材料の Z・A・密度・二次電子の定数は、光学と同じ材料表の `material_electron_properties` から引きます。CD-SEM の線プロファイルは `sem_line_profile`(台形の断面、埋もれた矩形も)で、線幅は `sem_cd_measure`(しきい値法・最大傾斜法)で測ります。高さ場と材料の地図からは `sem_image` が画素ごとに電子を撃って像を作り(レンズ内 SE / 側方 SE / 反射電子)、`sem_charging_series` が絶縁物の帯電をコマ送りにします。外部真値の門は 4 本: η(Z, E) が Joy のデータベースの実測の幅に入る / 傾けた試料の η(θ) が Arnal の式 / 到達深さが Kanaya-Okayama / δ の形と Emax が Lin & Joy 2005。

## What it does

A Monte Carlo that tracks primary electrons one by one in the solid (Joy's single-scattering model with Browning's 1994 Mott-fit elastic cross-section and the Joy-Luo stopping power). `sem_electron_mc` returns the backscatter coefficient, the secondary-electron yield and the penetration depth; `sem_yield_curve` sweeps the voltage. Material Z, A, density and secondary-electron constants come from the same material table the optics use (`material_electron_properties`). `sem_line_profile` scans a line with a trapezoidal cross-section (buried rectangles allowed) and `sem_cd_measure` measures its width by threshold or maximum slope. `sem_image` fires electrons into every pixel of a height field with a material map (in-lens SE, side SE, backscatter detector) and `sem_charging_series` steps insulator charging frame by frame. Four external-truth gates: backscatter coefficients inside measured bands, Arnal's tilt law, the Kanaya-Okayama range, and the Lin & Joy 2005 universal yield curve and Emax.

## 向くところ / 向かないところ

**向く**: 加速電圧・検出器の選び方を数で決める(埋もれた異物の情報深さ、SE と反射電子の使い分け)、CD-SEM の線幅の偏りが側壁角と電圧でどう動くかの見積もり、帯電の向き(低加速は正で自己調整、高加速は負で溜まる)の説明、真値つきの合成 SEM 像。

**向かない**: ★**W・Au などの重元素の δ(E) の形は普遍曲線より裾が厚く合いません**(SE2 が主になる。未解決のまま数で固定)。★δmax は Lin & Joy の表の約 0.8 倍で低めです(λ・ε は表のまま、合わせていない)。★二次電子は輸送せず脱出確率の期待値で数え、脱出の λ・ε は表面の層の材料で決めます(埋もれた材料は沈着エネルギーと反射電子を通してだけ効く)。★帯電の負の側は現象論(着地エネルギーの低下・ビームの曲がり・漏れの物理は入れない)。★像は画素ごとの直接 MC なので、高加速・大きな像は遅い(20 kV・48×48 画素・40 電子で数十秒)。★実画像との照合は未実施です(線幅の真値つきの CC BY の CD-SEM 像が見つかっていない)。

## 最初の 1 本

```python
import numpy as np
import semsim

# Si と Au に 20 keV の電子を撃つ。η を実測(Si 0.159〜0.194、Au 0.485〜0.516。門は実測の幅 ± 0.04)と比べる。
for m in ("SI", "AU"):
    r = semsim.sem_electron_mc(m, 20.0, tol=0.02, batch=1000, max_electrons=3000)
    print("%s: η = %.3f ± %.3f、最大の深さ %.2f R_KO" % (m, r["eta"], r["eta_ci95"],
                                                    r["depth_max_nm"] / r["range_ko_nm"]))

# PMMA の線(底辺 40 nm、側壁 88 度)を 1 kV と 20 kV で走査して、しきい値法で線幅を測る。
for kv in (1.0, 20.0):
    p = semsim.sem_line_profile("PMMA", "SI", kv, width_nm=40, height_nm=40, sidewall_deg=88,
                                x_half_range_nm=50, x_step_nm=2, electrons_per_point=300)
    w = semsim.sem_cd_measure(p["profile"], method="threshold", smooth_nm=1.5)["width_nm"]
    print("%2.0f kV: 線幅 %.1f nm(底辺 40.0、上辺 %.1f)" % (kv, w, p["width_top_nm"]))
```

## 推奨パイプライン

`material_electron_properties` → `sem_electron_mc` → `sem_line_profile` → `sem_cd_measure` → `sem_image`

`material_electron_properties` で材料の組成・密度・二次電子の定数を確かめ(推定の値か Lin & Joy の表の値か)→ `sem_electron_mc` で η・δ・到達深さを外の実測と比べてから → `sem_line_profile` で測りたい線の断面を走査し → `sem_cd_measure` で線幅を出して真の上辺・底辺と比べる(`sem_cd_measure` は実機で測った線プロファイル(``pairs``)にもそのまま掛かる) → 2-D の見え方が要るなら `sem_image` で同じ部品を撮る。

## 代替

閉形式の真値つきの縁効果だけ要るなら `sem_render`(sec θ + PSF、速い)。電圧を振った η・δ の曲線は `sem_yield_curve`、絶縁物の時間変化は `sem_charging_series`(正の帯電の電位は `sem_se_escape_fraction` の閉形式で別に解ける)。

## 限界

重元素(W・Au)の δ(E) の形は普遍曲線より裾が厚く合いません(SE2 が主、未解決)。δmax は表の約 0.8 倍。帯電の負の側は現象論。「低加速ほど側壁の上を測る」は側壁 88 度で成り立ち、80 度では差が小さく向きも逆です(`poc_virtual_sem_kv_cd_bse`)。

## 実寸校正

高さ場・線幅・画素は nm のまま入れます。実機と合わせるなら、既知の材料(Si・Au)の η と δ を同じ加速電圧で測って `sem_electron_mc` と比べ、ずれを検出器の利得として持ちます。

## 裏づけ

- op: `sem_electron_mc`、`sem_yield_curve`、`sem_line_profile`、`sem_cd_measure`、`sem_image`、`sem_charging_series`、`material_electron_properties`
- 例: [`poc_virtual_sem_kv_cd_bse`](../../examples/poc_virtual_sem_kv_cd_bse.py)
- 門: `tests/test_semsim_mc.py`(η の実測・Arnal・Kanaya-Okayama・Lin & Joy 2005、壊して確かめる探針 3 本)
