---
op: pixel_shift_resolution_budget
dim: optics
category: pixelshift
in: 
out: table
examples: [poc_pixel_shift, poc_simcal_pixel_shift]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# pixel_shift_resolution_budget — OPTICS `pixelshift` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pixel_shift_resolution_budget(pitch_um, f_number, wavelength_um=0.55, fill_factor=1.0, step_px=0.5)` (実装を直接呼ぶなら `import pixelshift; pixelshift.pixel_shift_resolution_budget(pitch_um, f_number, wavelength_um=0.55, fill_factor=1.0, step_px=0.5)`、台帳から引くなら `opsoptics.get("pixel_shift_resolution_budget")`)

## 使い方

ピクセルシフトで解像が上がるかの閉形式の予算(レンズ律速か画素律速か)。

周波数 f は cyc/px(センサ画素あたり)。

* 画素の開口の MTF: ``|sinc(f · fill)|``(箱の幅 fill 画素)。fill = 1 なら f = 1 で 0。
* 回折の MTF(円形の瞳、収差なし): ``(2/π)(acos x − x√(1 − x²))``、x = f · Q、**Q = λN/p**(Fiete 1999)。
  レンズの遮断は f = 1/Q。
* ナイキスト: 1 枚 = 0.5、標本の間隔 *step_px* のシフト = 0.5 / step_px。1 枚で f > 0.5 の成分は
  f_alias = |f − round(f)| に折り返る(モアレ)。
* **律速の境目は Q = 2**: レンズの遮断 1/Q が 1 枚のナイキスト 0.5 より上(Q < 2)なら、1 枚では折り返しが出て
  シフトで帯域が伸びる(画素律速)。Q ≥ 2 なら 0.5 より上に信号が無く、シフトしても増えない(レンズ律速)。
  ★ただし Q = 2 は「折り返しが出るか」の境目で、``gain``(系の MTF ≥ 0.1 の帯域の比)はもっと手前で 1.0 に
  なる: sinc(0.5)·MTF_diff(0.5 Q) = 0.1 の Q ≈ 1.47(fill = 1)。その間(例 Q = 1.75)は ``regime`` が
  ``"pixel_limited"`` でも ``gain`` は 1.0 —— 折り返しは消えるが、見える細かさは増えない。

返り値の辞書: ``Q``、``lens_cutoff_cyc_px``、``nyquist_single``、``nyquist_shifted``、``aperture_zero_cyc_px``、
``mtf_at_nyquist_single``(開口・レンズ・系の 3 つ)、``mtf_at_nyquist_shifted``(同)、``mtf50_cyc_px`` /
``mtf10_cyc_px``(系の MTF が 0.5 / 0.1 を切る周波数、数値の二分法)、``usable_band_single`` /
``usable_band_shifted``(折り返しを起こさず、系の MTF が 0.1 以上の上限)、``gain``(後者 / 前者)、
``regime``(``"pixel_limited"`` / ``"lens_limited"``)、``lp_per_mm_per_cyc_px``(1 cyc/px = 1000/p lp/mm)。

**Raises** ``ValueError``: pitch_um・f_number・wavelength_um が正の有限でない / fill_factor が (0, 1] でない /
step_px が {1/4, 1/3, 1/2, 1} でない。

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

- [poc_pixel_shift](../../../../examples/poc_pixel_shift.py) — `py -3.11 examples/poc_pixel_shift.py`
- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`pixelshift`)

[pixel_shift_pattern](pixel_shift_pattern.md) · [pixel_shift_capture](pixel_shift_capture.md) · [pixel_shift_merge](pixel_shift_merge.md) · [pixel_shift_motion_mask](pixel_shift_motion_mask.md) · [false_color_metric](false_color_metric.md)

---
*Provenance: pixelshift.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
