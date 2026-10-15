---
id: industrial-oct
title: 工業用 OCT(干渉スペクトル → k 線形化 → 分散補償 → A / B スキャン → 群屈折率で層厚)
title_en: Industrial OCT (spectral interferogram, k-linearisation, dispersion compensation, A/B-scans, layer thickness via the group index)
category: 測る
ops: [oct_design, oct_dispersion_broadening, oct_interferogram, oct_bscan_simulate, oct_from_spectra, oct_k_linearize, oct_dispersion_estimate, oct_dispersion_compensate, oct_ascan, oct_bscan, oct_layer_thickness, oct_bscan_boundaries, oct_bscan_flatten]
examples: [poc_industrial_oct]
version: 0.6.1
inputs: [matrix, signal]
pipeline: [oct_design, oct_from_spectra, oct_bscan, oct_bscan_boundaries, oct_bscan_flatten, oct_layer_thickness]
alternatives: [oct_interferogram, oct_bscan_simulate, oct_ascan, oct_dispersion_estimate, material_group_index, csi_design]
limits: 散乱は 1 回散乱(Beer–Lambert)の模型まで(多重散乱の背景は無い)。点像の幅の 1.4 倍(÷ n_g)より薄い層・雑音の 12 dB 上に立たない下の面・谷から 1 dB 立たない面は拒否。自己相関の幽霊は位相をずらした 2 枚か試料腕だけのスペクトルが無いと消えない。
calibration: 深さの刻みは分光器の波長の較正(画素ごとの波長)で決まり、物理厚は光学厚 ÷ 群屈折率。群屈折率は材料表の名前か、厚さの既知の試料で校正した値を使う(位相屈折率で割ると 1〜2 % 厚く出る)。
---

# 工業用 OCT(干渉スペクトル → k 線形化 → 分散補償 → A / B スキャン → 群屈折率で層厚)

## できること

塗装・コンフォーマルコート・接着層・多層フィルムの**層の並び**と、層の中の空洞・剥離を、壊さずに深さ方向で見ます。分光器型(SD-OCT)は 1 回の露光の干渉スペクトルを、波長掃引型(SS-OCT)は掃引の時間波形を、波数 k に等間隔に並べ直して FFT すると、深さごとの反射の振幅(A スキャン)になります。横に走査すると断面(B スキャン)です。

`oct_design` は撮る前の閉形式です: 軸分解能 (2 ln 2/π) λ0²/Δλ、深さ範囲 λ0²/(4δλ)、感度の roll-off(画素の箱の |sinc| と分光器の分解能のガウス、掃引は瞬時線幅のガウス)、ショット雑音律の SNR、横分解能 (4λ/π)(f/d) と焦点深度。`oct_interferogram` と `oct_bscan_simulate` は層の並び(屈折率と分散は材料表 `materials`)から干渉スペクトルを作り、場の和の |E|² なので相互相関・自己相関・DC がすべて入ります。処理は `oct_k_linearize` → `oct_dispersion_compensate`(係数は `oct_dispersion_broadening` の閉形式か `oct_dispersion_estimate` の鏡の位相・鋭さ最大)→ `oct_ascan`(窓・DC 除去・直交の組で鏡像を分ける)→ `oct_bscan`。計測は `oct_layer_thickness`(界面のピーク → 光学厚 → 群屈折率で物理厚、分離できなければ拒否)と `oct_bscan_boundaries`(断面像の界面を動的計画法で辿る)、`oct_bscan_flatten`(表面に沿って平らに並べて横に平均)です。装置や公開データの生のスペクトルは `oct_from_spectra` で入ります。

PoC `poc_industrial_oct` は、公開の自動車塗装の生スペクトル(CC BY 4.0)を Fullseye の op だけで処理し、透明層の厚さが論文の OCT と 2 µm 以内・顕微鏡と 4 µm 以内、着色層は 4 枚中 3 枚が顕微鏡と 2.5 µm 以内であることを採点します。合成では、群屈折率で割った厚さが真値と 0.05 µm 以内、軸分解能・SNR・roll-off・分散の広がりが閉形式と合うこと、鏡像・自己相関・折り返し・薄い層・散乱の限界を数で示します。

## What it does

Thirteen ops in `octscan` for optical coherence tomography of coatings, conformal coats, adhesive layers and multilayer films: closed-form design numbers before measuring (axial resolution, depth range, sensitivity roll-off, shot-noise-limited SNR, lateral resolution and depth of focus), a simulator of spectral interferograms from a layer stack whose indices and dispersion come from the material table (field sum, so cross-correlation, autocorrelation and DC terms are all present; spectrometer or swept source), k-linearisation, numerical dispersion compensation with closed-form or estimated coefficients, A-scans with windowing, DC removal and full-range quadrature, B-scans, and measurement: interface peaks to optical and physical thickness through the group index (refusing layers that cannot be separated or seen), dynamic-programming boundary tracing on cross-section images, surface flattening, and an entry point for raw spectra from instruments and public data. The PoC processes public raw spectra of automotive paint panels (CC BY 4.0) and compares the layer thicknesses with the paper's ultrasonic and microscope values.

## 向くところ / 向かないところ

**向く**: 透明・半透明の層(クリア塗装、コンフォーマルコート、接着層、樹脂フィルム、錠剤のコーティング)の厚さの分布と、層の中の空洞・剥離・異物の検出。光源の帯域・分光器の画素数・ビームの絞りを決める前の見積り(どの厚さまで分離でき、どの深さまで見えるか)。分散の不一致の許容と補償。

**向かない**: 強く散乱する層(白い塗装の二酸化チタン、充填剤の多い樹脂)の**下**の面は信号が雑音に沈みます —— op は「谷から立つ山が無い」として拒否します。点像の幅の 1.4 倍(÷ 群屈折率)より薄い層は、2 本のピークが重なって厚さが偏るので拒否します(サブ µm の膜厚は分光反射の領分)。多重散乱による深い所の背景、偏光、試料の傾きによる結合の低下(鏡面反射の向き)は模型に入っていません。

## 推奨パイプライン

`oct_design` → `oct_from_spectra` → `oct_bscan` → `oct_bscan_boundaries` → `oct_bscan_flatten` → `oct_layer_thickness`

`oct_design` で光源と分光器から分解能・深さ範囲・roll-off を先に出す → `oct_from_spectra` で装置の生のスペクトル(A ライン × 画素)と画素ごとの波長を表にする → `oct_bscan`(k 線形化・窓・DC 除去・FFT。参照腕だけのスペクトルが無ければ `dc="smooth"`)で断面像 → `oct_bscan_boundaries` で表面を辿る → `oct_bscan_flatten`(断面の表 —— `oct_bscan` の素の返り値 —— と表面の行)で表面に沿って横に平均 → `oct_layer_thickness` で界面のピークを群屈折率で厚さに。列ごとの分布が要るなら、平均の位置の ±数 µm の窓で `oct_bscan_boundaries(reference_rows=表面, offset_px=…)` を引き直す。

## 代替

合成で装置を設計するなら `oct_interferogram`(1 本)と `oct_bscan_simulate`(断面)。1 本の A スキャンなら `oct_ascan` に直接。分散の不一致があるときは `oct_dispersion_estimate`(鏡なら `"mirror"`、試料なら `"sharpness"`)の係数を `oct_bscan` の `a2`・`a3`・`k_center` に。群屈折率は `material_group_index`(材料表)。表面の高さだけなら白色干渉の `csi_design` と CSI の op。

## 限界

- 散乱は 1 回散乱(Beer–Lambert の減衰 + 点散乱体)の模型。多重散乱で深い所の背景が持ち上がる効果は無い。
- 薄い層は点像の幅の 1.4 倍(÷ 群屈折率)より薄いと拒否(840/50 nm・hann 窓で PMMA なら約 6.8 µm)。
- 自己相関の幽霊(層の上下の面どうしの干渉)は参照腕を強くすると弱まるが、位相をずらした 2 枚の差か試料腕だけのスペクトルが無いと消えない。実測の PoC でも透明層の光学厚の深さに水平な線として出る。
- 実測の章の屈折率(透明層 1.56・着色層 1.64)は論文がテラヘルツ帯の別測定から借りた値で、近赤外の群屈折率ではない。ファイルと論文の表の見本の対応は論文に無く、透明層の厚さで推定した。

## 実寸校正

深さの刻みは分光器の**波長の較正**(画素ごとの波長)で決まる —— 較正がずれると k 線形化が崩れ、深いほど点像が広がる(PoC: 線形化しないと 1500 µm で 3 倍超)。物理厚は光学厚 ÷ **群屈折率**(位相屈折率で割ると PMMA・PC・PS で 0.9〜1.9 % 厚く出る)。群屈折率は材料表の名前か、厚さの既知の試料(段差・断面の顕微鏡)で校正した値を使う。横の刻みは走査の振れ角と焦点距離、または既知の的で確かめる。

## 最初の 1 本

```python
import octscan as O

# 撮る前の閉形式: 840/50 nm・2048 画素の分光器型
d = O.oct_design(840.0, 50.0, 2048, grid="k", n_group=1.5, beam_waist_um=6.0)
print(round(d["axial_resolution_air_um"], 2), round(d["depth_range_air_um"]))   # 6.23 2236

# PMMA 25 µm / ポリカーボネート 40 µm の 2 層を測る(群屈折率は材料表から)
film = {"layers": [{"material": "PMMA", "thickness_um": 25.0},
                   {"material": "POLYCARBONATE", "thickness_um": 40.0}],
        "substrate": {"n": 1.51, "n_group": 1.53}, "surface_um": 300.0}
a = O.oct_ascan(O.oct_interferogram(film, grid="k", noise=False), window="hann", zero_pad=8)
L = O.oct_layer_thickness(a, n_group=["PMMA", "POLYCARBONATE"], n_interfaces=3, z_range_um=(200, 500))
print(L["thickness_um"].round(2))                                                # [25.   40.01]
```

走らせて見るなら `py -3.11 examples/poc_industrial_oct.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
