---
id: pl-carrier-diffusion-visibility
title: PL 像で細い溝が見えなくなる理由を、キャリア拡散の PSF と欠陥の種類で切り分ける(Si ウェハ・太陽電池の PL/EL 検査)
title_en: Why a thin groove disappears in a PL image — the carrier-diffusion PSF and the kind of defect decide the visibility (PL/EL inspection of wafers and solar cells)
category: 見つける
ops: [pl_diffusion_psf, pl_image_simulate, pl_groove_visibility, pod_hitmiss_fit]
examples: [poc_si_wafer_pl_defect_visibility]
version: 0.6.1
---

# PL 像で細い溝が見えなくなる理由を、キャリア拡散の PSF と欠陥の種類で切り分ける(Si ウェハ・太陽電池の PL/EL 検査)

## できること

フォトルミネッセンス(PL)像は、励起で作った過剰キャリアが**拡散してから**光ります。だから像には光学の PSF のほかに、拡散長 L = √(Dτ) で決まる**もう 1 つの PSF**(2 次元のグリーン関数 K₀(r/L)/2πL²)が掛かります。`pl_diffusion_psf` はその核を総和 1 で返し、`pl_image_simulate` は励起の場と追加再結合の場から定常拡散方程式を格子で厳密に解いて PL 像を作ります(光学 PSF と雑音は任意)。`pl_groove_visibility` は溝の幅・拡散長・雑音から、**影の溝**(励起や発光の欠け、コントラスト 1 − e^{−w/2L})と**沈みの溝**(再結合の線、Donolato 型 SL/(SL+2D))のコントラスト・CNR・見える/見えないの境界 L* を閉形式で返します。

設計規則はこの 2 つの向きが**逆**なことです: 拡散長の長い良質なウェハほど、影は拡散が埋めて隠れ(w ≪ L で ≈ w/2L)、沈みは供給を上回って吸うので深く広く目立ちます。公開実データ(Si ウェハのレーザー溝、HF 処理後の時間変化)では溝は沈み型の向きでした。埋め込んだ溝の検出確率は `pod_hitmiss_fit` で a90/95 にできます。

## What it does

A PL image glows only after the excess carriers have diffused, so a second PSF — the 2-D Green function K₀(r/L)/2πL², L = √(Dτ) — sits on top of the optical one. `pl_diffusion_psf` returns that kernel (sum 1); `pl_image_simulate` solves the steady-state diffusion equation exactly on the grid from an excitation map and an extra-recombination map (optional optical PSF and noise); `pl_groove_visibility` gives the closed-form contrast, CNR and visibility boundary L* of a shadow groove (missing excitation, 1 − e^{−w/2L}) and a sink groove (a recombination line, Donolato's SL/(SL+2D)). The two move in opposite directions with L: a longer diffusion length hides shadows and reveals sinks. Embedded-groove detection feeds `pod_hitmiss_fit` for a90/95.

## 向くところ / 向かないところ

**向く**: PL/EL 検査(Si ウェハ・太陽電池)の検出限界の設計、「拡散長が変わると欠陥がどう見えるか」の予測、真値つきの合成 PL 像の生成、埋め込み POD。同じ K₀ の核は蛍光の拡散やロックインサーモグラフィの熱拡散(μ = √(2α/ω))にも移せます。

**向かない**: ★面内 2 次元・低注入・定常のモデルです。厚さ方向の分布(裏面の欠陥を表から見るとき)、高注入の非線形、過渡(時間分解 PL)、再吸収は入っていません。★「拡散長が長いほど隠れる」は**影の溝にだけ**当てはまります(`poc_si_wafer_pl_defect_visibility`、実データの溝は逆向きでした)。欠陥が影か沈みかを先に決めてから数えてください。★実データの地の構造は白色雑音より 1 桁以上きつく効きます —— 検出限界は雑音でなく地から見積もること。

## 最初の 1 本

```python
import numpy as np
import plsim

# 幅 3 px の影の溝を、拡散長 L = 10 px で描く。中心のコントラストは閉形式 1 − e^{−w/2L} に乗る。
g = np.ones((1, 401)); g[0, 199:202] = 0.0
u = plsim.pl_image_simulate(g, diffusion_length_px=10.0)
t = plsim.pl_groove_visibility(3.0, 10.0, sink_velocity=0.3, noise_rel=0.01)
print("影の溝 中心コントラスト: 厳密解 %.4f / 連続の閉形式 %.4f / 格子の閉形式 %.4f"
      % (1 - u[0, 200], t["contrast_shadow"], t["contrast_shadow_grid"]))
print("沈みの溝 SL/(SL+2D) = %.4f、見える境界 L*: 影 %.1f px より長いと消え、沈み %.1f px より短いと消える"
      % (t["contrast_sink"], t["L_star_shadow_px"], t["L_star_sink_px"]))
```
