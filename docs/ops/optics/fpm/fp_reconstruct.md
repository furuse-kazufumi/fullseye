---
op: fp_reconstruct
dim: optics
category: fpm
in: table
out: table
gpu: なし
examples: [poc_fourier_ptychography]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# fp_reconstruct — OPTICS `fpm` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.fp_reconstruct(stack, upsample=None, n_iter=200, pupil_update=True, pupil_start=2, alpha=1.0, beta=1.0, led_correction=False, led_start=3, stall_tol=0.01, stall_window=10, agree_tol=0.08, starts=2, margin_px=None, intensity_correction=False, pupil_degree=4, on_fail='raise')` (実装を直接呼ぶなら `import fourierptycho; fourierptycho.fp_reconstruct(stack, upsample=None, n_iter=200, pupil_update=True, pupil_start=2, alpha=1.0, beta=1.0, led_correction=False, led_start=3, stall_tol=0.01, stall_window=10, agree_tol=0.08, starts=2, margin_px=None, intensity_correction=False, pupil_degree=4, on_fail='raise')`、台帳から引くなら `opsoptics.get("fp_reconstruct")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

低解像の像の組から高解像の振幅と位相を戻す(``table``、kind="fp_result")。収束しなければ拒否する。

逐次の位相回復(Ou ら 2014 の EPRY、ePIE と同じ形): 照明の NA の小さい順に 1 枚ずつ、推定の低解像の場の
振幅を測った振幅に置き換え、その差で物体のスペクトルを ``alpha`` 、瞳を ``beta`` の歩幅で直す
(瞳は ``pupil_start`` 回目から、円の外は 0 に保つ)。

* ``pupil_degree``(既定 4): 瞳の位相の更新を、円の上で直交化した 2〜4 次の多項式(12 個。デフォーカス・非点・
  コマ・球面などの低次の収差)へ射影し、振幅は 1 に保つ。``None`` は画素ごとに自由な EPRY(原論文の形)——
  ★自由な瞳は雑音を吸って残差が下がり続け、停留しない(32 画素・25 枚の合成で 200 回後も 10 回あたり 1 % 超)。

* ``upsample``: 高解像の格子の倍率。None なら照明の NA が入り、画素が λ/(2 NA_syn) 以下になる最小の整数。
* ``led_correction``: ``led_start`` 回目から、像ごとに瞳の中心を ±1 画素の 9 通りで試して残差の最小を取り
  (同点は丸めた値で比べ、候補の宣言順で先のもの)、続けて表の ``led_xyz_mm`` に LED アレイの幾何
  (ずれ x・y、回転、高さ)を最小二乗で当て、中心をその予測に置き直す(Sun ら 2016 の焼きなましを決定的な
  局所探索に替えたもの)。
* ``intensity_correction``: 3 回目から像ごとの明るさの比を推定の平均に合わせる(LED の明るさが分からない
  実データ向け)。照明の NA が最小の像は基準として動かさない —— ★全部を動かすと、推定が明るくなれば測った像も
  明るくし直す正の帰還になり、実データで残差が 200 回で 2 万倍に発散した(瞳を多項式に射影したとき)。
* 収束: 振幅の相対残差の不動点 **かつ** 初期値の違う 2 本(``starts=2``)が ``agree_tol`` 以内で一致。
  残差が下がらない・回数が尽きた・2 本が別の答えに着いた、のどれでも「収束しない」。
  ``on_fail="raise"``(既定)は :class:`FPNotConvergedError`(``MetricContractError``、``record`` に記録)、
  ``"record"`` は記録を返す(``converged=False``)。
* ``starts=1`` は一意性の門を通らない(停留だけで ``converged=True`` になりうる): ``uniqueness_checked`` が False に
  なり、``reason`` に「uniqueness not checked」を足す。
* 残差の上限: 収束の判定は残差の**変化**しか見ない。最後の残差が ``RESIDUAL_WARN``(0.1)を超えたら
  ``residual_warning=True`` にし、``reason`` に警告を足す(判定は変えない)。合成で実測: 収束した復元は 0.004〜0.03
  (rms 0.12 波の収差を含む)、照明の k と無関係な乱数の像は初期値 1 本で停留して 0.17。

返り値: dict(kind="fp_result", converged, reason, n_iter, residual, residual_history,
residual_history_starts, step_history(1 周ごとの物体のスペクトルの相対変化), start_disagreement,
field_second_start, amplitude, phase, field, pupil, pupil_support, na_synthetic
(= NA_obj + 使った照明の NA の最大、対角の LED を含む), na_synthetic_axis(x・y の方向余弦の最大で取った値 = 軸に
沿った棒の分解を決める値), pixel_um, upsample, margin_px, led_centres, led_geometry, intensity_scale,
uniqueness_checked, residual_warning, residual_ceiling)。

Raises: ValueError(表が欠けている・値が範囲外、像のエネルギーが 0(露光で割った後、端を除いた全部の像の和)、
LED の補正で当てはめた幾何が瞳の中心を高解像の格子の外に置いた)。

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

[fp_design](fp_design.md) · [fp_usaf_target](fp_usaf_target.md) · [fp_capture](fp_capture.md) · [fp_stack_from_images](fp_stack_from_images.md) · [fp_element_contrast](fp_element_contrast.md)

---
*Provenance: fourierptycho.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
