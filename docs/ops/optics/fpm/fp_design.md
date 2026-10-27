---
op: fp_design
dim: optics
category: fpm
in: 
out: table
examples: [poc_fourier_ptychography]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fp_design — OPTICS `fpm` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fp_design(na_obj=0.1, wavelength_um=0.532, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13, magnification=4.0, camera_pixel_um=5.2, target_na=None, field_of_view_um=None, boundary_tolerance_na=0.005)` (実装を直接呼ぶなら `import fourierptycho; fourierptycho.fp_design(na_obj=0.1, wavelength_um=0.532, led_pitch_mm=4.0, led_distance_mm=70.0, n_side=13, magnification=4.0, camera_pixel_um=5.2, target_na=None, field_of_view_um=None, boundary_tolerance_na=0.005)`、台帳から引くなら `opsoptics.get("fp_design")`)

## 使い方

FP の性能を**撮る前に**閉形式で(``table``): 合成 NA・遮断周期・重なり率・LED の数・画素の標本化。

正方格子(``n_side`` × ``n_side``、ピッチ ``led_pitch_mm``)の LED を試料から ``led_distance_mm`` 下に置き、
中心の LED を光軸に合わせた構成。

* 照明の NA: 軸上の端の LED で NA_ill = e/√(e² + h²)(e = (n_side − 1)/2 · ピッチ)、対角の角でも返す。
* 合成 NA = NA_obj + NA_ill(軸)。棒が軸に沿った USAF チャートの分解能を決めるのは軸の値(対角の LED は
  x だけの周波数を瞳に入れない)。コヒーレントの遮断周期 λ/NA_syn(対物だけなら λ/NA_obj)、半周期 λ/(2 NA_syn)。
* 重なり率: 中心の LED とその隣の瞳の円(半径 NA_obj/λ、中心間隔 = sinθ の差/λ)の交わりの面積 / 円の面積
  = (2/π)[acos a − a√(1 − a²)]、a = d/(2r)。中心が最も小さく(sinθ の刻みは外ほど狭い)、端の値も返す。
  ``overlap_ok`` = 中心の値 ≥ 0.35(Sun ら 2016 の下限)。
* 標本化: 物体側の画素 Δx = camera_pixel_um / magnification が λ/(2 NA_obj) 以下(R_cam = λ·M/(2 NA_obj Δx_cam)
  ≥ 1)。強度の帯域で見たナイキスト λ/(4 NA_obj) も返す(FP は場を戻すので λ/(2 NA_obj) で足りる)。
* 上げ倍率: 高解像の画素が λ/(2 NA_syn) 以下になる最小の整数。
* 境の LED: 照明の NA が NA_obj と ``boundary_tolerance_na`` 以内の LED の数(``boundary_leds``)。その像は
  明視野と暗視野の境で、瞳の縁が照明の 0 次を切るかどうかが k の丸め 1 画素で入れ替わる —— 実測では重なり 39 % の
  構成がこれ 1 つで収束しなくなった(256 画素の視野で。LED の距離を 70 → 76 mm にずらすと収束。384 画素の視野では
  境のままでも収束した —— 起きうるが必ずではない)。``boundary_ok`` = 0 枚。
* ``target_na``: その合成 NA に要る格子の一辺・LED の総数・照明の NA が足りる LED の数。
* ``field_of_view_um``: 空間帯域幅積(視野 / 半周期)²。

返り値: dict(kind="fp_design", na_synthetic, na_illumination_max_axis, coherent_cutoff_period_um,
overlap_ratio_centre, overlap_ratio_edge, overlap_ok, n_leds, n_brightfield, boundary_leds, boundary_ok,
object_pixel_um, r_cam,
pixel_sampling_ok, upsample_needed, …)。

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

- [poc_fourier_ptychography](../../../../examples/poc_fourier_ptychography.py) — `py -3.11 examples/poc_fourier_ptychography.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`fpm`)

[fp_usaf_target](fp_usaf_target.md) · [fp_capture](fp_capture.md) · [fp_stack_from_images](fp_stack_from_images.md) · [fp_reconstruct](fp_reconstruct.md) · [fp_element_contrast](fp_element_contrast.md)

---
*Provenance: fourierptycho.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
