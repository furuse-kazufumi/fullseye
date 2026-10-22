---
op: thin_film_reflectance
dim: optics
category: appearance
in: signal
out: signal
examples: [appearance_structural_colour, simcal_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# thin_film_reflectance — OPTICS `appearance` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.thin_film_reflectance(nm, thickness_nm=350.0, n_film=1.33, n_sub=1.0, cos_theta=1.0, n_out=1.0, polarization='unpolarized', under_layers=()) -> 'np.ndarray'` (実装を直接呼ぶなら `import matappear; matappear.thin_film_reflectance(nm, thickness_nm=350.0, n_film=1.33, n_sub=1.0, cos_theta=1.0, n_out=1.0, polarization='unpolarized', under_layers=()) -> 'np.ndarray'`、台帳から引くなら `opsoptics.get("thin_film_reflectance")`)

## 使い方

薄膜(厚さ d、屈折率 n_film)の分光反射率。特性行列法の厳密解(多重反射をすべて含む)。

nm:           波長 [nm] (配列可)。
thickness_nm: 膜厚 [nm]。シャボン玉なら 200–800、陽極酸化被膜なら 50–300。nm とブロードキャストできる
              **配列も可**(膜厚の場。例 (H, W, 1) の膜厚と (K,) の波長 → (H, W, K))。
n_film/n_sub: 膜 / 基板の屈折率。実数・**複素数 n + ik**(k ≥ 0、金属の基板や吸収膜)・
              **材料名**(共通の材料表 ``materials``、例 "TI" / "AL" / "SI" —— その波長の n,k を引く)・
              材料レコード(dict)・nm とブロードキャストできる**波長ごとの配列**(膜の分散)のどれでも。
cos_theta:    入射側での入射角の cos(配列可、nm とブロードキャストできる形)。
n_out:        入射側の屈折率(実数か材料名、吸収なし)。
polarization: "unpolarized"(既定、s と p の平均)/ "s" / "p"。
under_layers: 膜と基板の間の層(入射側から順の ``[(屈折率, 厚さ nm), ...]``、屈折率は n_film と同じ書き方)。
              空(既定)なら 1 層の膜。多層の AR 膜・誘電体ミラー・酸化膜の下の窒化膜などに。

返り値: 反射率 R(0–1)。nm・thickness_nm・cos_theta のブロードキャスト形。

★符号の約束: 複素屈折率は N = n + ik、k ≥ 0。N = n − ik と書く文献の値は同じ k を正のまま渡す
(虚部が負の入力は ValueError —— どちらの約束かを推測しない)。

物理: 層ごとの特性行列 [[cos δ, −i sin δ / η], [−i η sin δ, cos δ]]、δ = 2π N d cosθ̃ / λ(複素の Snell で
層の中の cosθ̃ を出し、減衰する枝を取る)、傾いた光学アドミッタンス η = N cosθ̃(s)/ N / cosθ̃(p)。
1 層なら Airy の式 R = |r1 + r2 e^{2iβ}|² / |1 + r1 r2 e^{2iβ}|² と同じ値になる(テストで別に書いた式と比べる)。
λ/4 の奇数倍で反射が極大(n_film > n_sub のとき)になり、**厚みを変えると色が動く**のがシャボン玉の色。
膜厚 0 では R が基板単体のフレネル反射に一致する。計算は ``filmoptics`` の特性行列 1 か所で行う
(``filmoptics.multilayer_reflectance`` と同じ関数)。

★2026-10-14: 以前は 3 つの屈折率を実数に限っていた(複素数は TypeError)。金属の基板を実数で近似すると
(焼けたチタン 90 nm を n_sub = 2.6 で)反射率が 0.15〜0.19 と出て、Ti の n,k なら 0.35〜0.61(380〜780 nm)
—— 色が別物になる、黙った誤り。いまは基板に "TI" と書けば材料表の n,k が入る。

>>> r = thin_film_reflectance([450.0, 550.0, 650.0], 90.0, "TIO2_AMORPHOUS", "TI")
>>> bool(r.min() > 0.3)
True

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

## 背景知識ガイド(この op の手前にある物理・規約)

- [colorimetry](../../2d/guides/colorimetry.md) — 測色と分光の知識 — 色は「分光 × 光源 × 観測者」でしか決まらない
- [mv_illumination_practice](../guides/mv_illumination_practice.md) — 照明の実務知識 — 波長・偏光・点灯方式・外光・安全

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [appearance_structural_colour](../../../../examples/appearance_structural_colour.py) — `py -3.11 examples/appearance_structural_colour.py`
- [simcal_tour](../../../../examples/simcal_tour.py) — `py -3.11 examples/simcal_tour.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[emva_photon_transfer](../sensorchar/emva_photon_transfer.md) · [emva_quantum_efficiency](../sensorchar/emva_quantum_efficiency.md) · [emva_linearity_error](../sensorchar/emva_linearity_error.md) · [emva_snr_curve](../sensorchar/emva_snr_curve.md) · [emva_dark_current](../sensorchar/emva_dark_current.md) · [emva_total_snr](../sensorchar/emva_total_snr.md) · [emva_exposure_for_snr](../sensorchar/emva_exposure_for_snr.md) · [emva_photon_exposure](../sensorchar/emva_photon_exposure.md)

## 同カテゴリ(`appearance`)

[cie_xyz_from_wavelength](cie_xyz_from_wavelength.md) · [spectrum_to_srgb](spectrum_to_srgb.md) · [grating_wavelengths](grating_wavelengths.md) · [grating_rgb](grating_rgb.md) · [thin_film_rgb](thin_film_rgb.md) · [ward_anisotropic](ward_anisotropic.md)

---
*Provenance: matappear.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
