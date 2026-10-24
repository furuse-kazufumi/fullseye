---
op: cubic_photoelastic_birefringence
dim: optics
category: photoelastic
in: image2d × image2d × image2d
out: table
examples: [photoelastic_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# cubic_photoelastic_birefringence — OPTICS `photoelastic` op

- **データ種**: `image2d × image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.cubic_photoelastic_birefringence(sxx, syy, txy, pi11_minus_pi12, pi44, refractive_index, crystal_angle_deg=0.0)` (実装を直接呼ぶなら `import photoelastic; photoelastic.cubic_photoelastic_birefringence(sxx, syy, txy, pi11_minus_pi12, pi44, refractive_index, crystal_angle_deg=0.0)`、台帳から引くなら `opsoptics.get("cubic_photoelastic_birefringence")`)

## 使い方

立方晶 {100} 面(Si ウェハなど)の応力複屈折 Δn と遅相軸 → dict。

Light travels along the [100] normal of a {100} plate. ``crystal_angle_deg``
φ is the angle between the [010] direction and the x axis (Stoehr et al.
2020, Eq. 19). The 4th-order piezo-optic tensor of the cubic crystal is
rotated, ``π'_ijkl = R_im R_jn R_ko R_lp π_mnop``, the impermeability change
is ``ΔB_ij = π'_ijkl σ_kl`` and the in-plane birefringence is
``Δn = (n³/2)(ΔB_II − ΔB_I)`` — which reproduces Eq. (26) of that paper::

    Δn = (n³/4) √( 2((π11−π12)² + π44²)(4τ² + (σx−σy)²)
                   + 2((π11−π12)² − π44²)[((σx−σy)² − 4τ²) cos 4φ
                                          + 4τ(σx−σy) sin 4φ] )

With ``π44 = π11 − π12`` the material is photoelastically isotropic and
``Δn = (n³/2)|π11 − π12|(σ1 − σ2)``. In the sign of
:func:`photoelastic_retardation` (``n_σ1 − n_σ2 = C(σ1 − σ2)``; a change of
impermeability ``ΔB`` changes the index by ``−(n³/2)ΔB``) that is
``C = −n³(π11−π12)/2``, returned as ``isotropic_coefficient``: π11 − π12 > 0
makes σ1 the fast axis, and the value can be passed to
:func:`photoelastic_retardation` as it is.

Coefficients are in Pa⁻¹ (:func:`silicon_piezo_optic_coefficients`).
Returns ``delta_n`` (≥ 0), ``slow_axis_deg`` (direction of the larger
refractive index, (−90, 90]; 0 where Δn = 0 to 1e-12 of that pixel's own
stress scale — the fast axis that ``optics.mueller_element`` and
:func:`photoelastic_polarization_images` take is ``slow_axis_deg + 90``),
``effective_coefficient`` (|Δn|/(σ1−σ2) ≥ 0 [Pa⁻¹], 0 where σ1 = σ2),
``isotropic_coefficient`` (signed, as above) and ``isotropic`` (σ1 = σ2).

**Raises** ``ValueError``: non-finite / empty / non-broadcasting stresses,
|π| outside [1e-15, 1e-9] Pa⁻¹ (a table value in ×10⁻⁷ MPa⁻¹ or in MPa⁻¹
passed as Pa⁻¹), or a refractive index outside [1, 10].

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

- [photoelastic_roundtrip](../../../../examples/photoelastic_roundtrip.py) — `py -3.11 examples/photoelastic_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`photoelastic`)

[brazilian_disc_stress](brazilian_disc_stress.md) · [kirsch_plate_stress](kirsch_plate_stress.md) · [principal_stress](principal_stress.md) · [retardation_from_birefringence](retardation_from_birefringence.md) · [photoelastic_retardation](photoelastic_retardation.md) · [retardation_convert](retardation_convert.md) · [silicon_piezo_optic_coefficients](silicon_piezo_optic_coefficients.md) · [polariscope_intensity](polariscope_intensity.md)

---
*Provenance: photoelastic.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
