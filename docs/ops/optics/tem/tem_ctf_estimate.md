---
op: tem_ctf_estimate
dim: optics
category: tem
in: image2d
out: table
examples: [poc_tem_ctf_thon_rings]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# tem_ctf_estimate — OPTICS `tem` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.tem_ctf_estimate(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, amplitude_contrast=0.07, phase_shift_deg=0.0, defocus_min_A=3000.0, defocus_max_A=50000.0, k_min=0.03333333333333333, k_max=None, tile=None, overlap=0.5, astigmatism=True, min_rings=3, min_peak_z=8.0, on_fail='raise')` (実装を直接呼ぶなら `import temsim; temsim.tem_ctf_estimate(image, pixel_A=1.0, kv=300.0, cs_mm=2.7, amplitude_contrast=0.07, phase_shift_deg=0.0, defocus_min_A=3000.0, defocus_max_A=50000.0, k_min=0.03333333333333333, k_max=None, tile=None, overlap=0.5, astigmatism=True, min_rings=3, min_peak_z=8.0, on_fail='raise')`、台帳から引くなら `opsoptics.get("tem_ctf_estimate")`)

## 使い方

顕微鏡写真のパワースペクトルの Thon リングから焦点外れ(と非点収差)を推定する(表)。

手順: (1) タイルの平均のパワースペクトル(``tem_power_spectrum`` と同じ)→ 振幅スペクトル √PS。
(2) 動径平均を k について等間隔に取り、k² について不等間隔の標本に Lomb–Scargle(``mathspectral``)を掛けて
リングの周期 1/(λΔf) から初期値。(3) 背景 = u = k² の上でリング 1 周期の移動平均、振れ幅で割って平坦にする。
(4) Δf を格子で掃き(位相が k_max で π/8 ずつ動く刻み)、CTF² との正規化相互相関(CTFFIND4 の採点の考え方)が
最大の所を有界の 1 次元探索で詰める。(5) ``astigmatism=True`` なら 2-D の環の上で (Δf_u, Δf_v, θ) を Nelder–Mead で
詰める(決まった 4 方向から出発、乱数なし)。(6) 不確かさ = タイルを 8 組に分けた jackknife の標準誤差(Δf の平均)。

**拒否**(``on_fail="raise"`` で ValueError、``"report"`` で ``accepted=False`` の表): 相関の最大が掃いた格子の
中央値から MAD の ``min_peak_z`` 倍に届かない(リングが雑音に埋もれた)、帯域 [k_min, k_max] に零点が
``min_rings`` 個無い(周期が決まらない)、最大が探索範囲の端(範囲の外にある疑い)。
返り値: ``defocus_A``(平均)/ ``defocus_u_A`` ≥ ``defocus_v_A`` / ``astig_angle_deg``(Δf_u の軸、0〜180)/
``defocus_sigma_A``(jackknife)/ ``score``(2-D の相関)/ ``score_1d`` / ``peak_z`` / ``n_rings`` /
``fit_resolution_A``(局所の相関が 0.3 を下回る最初の周波数の逆数)/ ``initial_lomb_A`` / ``accepted`` / ``reason`` /
曲線 ``k`` と ``flat``(平坦にした動径平均)と ``model``。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_tem_ctf_thon_rings](../../../../examples/poc_tem_ctf_thon_rings.py) — `py -3.11 examples/poc_tem_ctf_thon_rings.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`tem`)

[tem_wavelength](tem_wavelength.md) · [tem_scherzer](tem_scherzer.md) · [tem_ctf](tem_ctf.md) · [tem_ctf_profile](tem_ctf_profile.md) · [tem_projected_potential](tem_projected_potential.md) · [tem_amorphous_film](tem_amorphous_film.md) · [tem_image_weak_phase](tem_image_weak_phase.md) · [tem_multislice](tem_multislice.md)

---
*Provenance: temsim.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
