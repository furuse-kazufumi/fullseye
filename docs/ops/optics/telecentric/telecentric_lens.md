---
op: telecentric_lens
dim: optics
category: telecentric
in: 
out: table
examples: [poc_optics_drawings, poc_telecentric_metrology]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# telecentric_lens — OPTICS `telecentric` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.telecentric_lens(kind='object', focal_mm=100.0, magnification=-0.5, na_object=0.01, front_aperture_mm=12.5, stop_shift_mm=0.0, glass='N-BK7', wavelength_um=0.58756)` (実装を直接呼ぶなら `import telecentric; telecentric.telecentric_lens(kind='object', focal_mm=100.0, magnification=-0.5, na_object=0.01, front_aperture_mm=12.5, stop_shift_mm=0.0, glass='N-BK7', wavelength_um=0.58756)`、台帳から引くなら `opsoptics.get("telecentric_lens")`)

## 使い方

同じ単レンズで、絞りの位置だけを変えた 3 種の撮像レンズの処方(``raytrace.lens_system`` の table)。

* ``kind="entocentric"`` —— 通常のレンズ。絞りをレンズの直後(1 mm)に置く。入射瞳はレンズの位置にあり、
  主光線は物体から入射瞳へ向かって傾く(近い物ほど大きく写る)。
* ``kind="object"`` —— 物体側テレセン。絞りを**後側焦点**に置く。入射瞳は無限遠、物体側の主光線は光軸に平行。
* ``kind="bi"`` —— 両側テレセン。後側焦点の絞りの後ろに、前側焦点が絞りに来る 2 枚目のレンズ
  (焦点距離 ``|magnification| × focal_mm``)を置く。物体は 1 枚目の前側焦点、倍率は −f₂/f₁。

*magnification* は横倍率(実像なので負)、*na_object* は物体側の開口数(絞りの半径を近軸の周辺光線から決める)、
*front_aperture_mm* は前玉の半口径(テレセンの視野はこれで決まる)。*stop_shift_mm* は絞りを
設計位置から光軸方向へずらす量(正 = 像側)で、テレセン度の崩れを再現する(Newton の式で入射瞳は前側焦点から
−f²/δ)。レンズは *glass* の等凸単レンズで、縁の厚さが 1 mm 残る中心厚を選ぶ。像面は近軸の像の位置に固定する。

返り値は ``lens_system`` の dict に ``"design"``(種別・焦点距離・絞りの半径・物体距離・面の役割)を足したもの。
絞りの面は平面なので、その ``R`` は ``lens_system`` の規約どおり ``inf``(非有限は契約)。
``raytrace`` のどの op にもそのまま渡せる(ただし入射瞳が無限遠の処方は ``raytrace.chief_ray`` では
狙えないので、主光線は :func:`chief_ray_angle` を使う)。

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

- [poc_optics_drawings](../../../../examples/poc_optics_drawings.py) — `py -3.11 examples/poc_optics_drawings.py`
- [poc_telecentric_metrology](../../../../examples/poc_telecentric_metrology.py) — `py -3.11 examples/poc_telecentric_metrology.py`

## 型が繋がる次の op(`table` を入力に取れる)

[abcd_matrix](../geometric/abcd_matrix.md) · [wavefront_stats](../imaging/wavefront_stats.md) · [sfr_from_edge](../imaging/sfr_from_edge.md) · [paraxial_trace](../design/paraxial_trace.md) · [seidel_coefficients](../design/seidel_coefficients.md) · [spot_stats](../design/spot_stats.md) · [tolerance_analysis](../design/tolerance_analysis.md) · [wavefront_from_opd](../design/wavefront_from_opd.md)

## 同カテゴリ(`telecentric`)

[chief_ray_angle](chief_ray_angle.md) · [magnification_vs_depth](magnification_vs_depth.md) · [telecentricity_error](telecentricity_error.md) · [defocus_spot_vs_depth](defocus_spot_vs_depth.md) · [vignetting_vs_field](vignetting_vs_field.md) · [lens_equivalent_pinhole](lens_equivalent_pinhole.md)

---
*Provenance: telecentric.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
