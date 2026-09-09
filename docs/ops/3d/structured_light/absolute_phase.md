---
op: absolute_phase
dim: 3d
category: structured_light
in: image2d × image2d
out: image2d
examples: [structured_light_scan]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# absolute_phase — 3D `structured_light` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.absolute_phase(wrapped, coarse) -> 'np.ndarray'` (実装を直接呼ぶなら `import fringe; fringe.absolute_phase(wrapped, coarse) -> 'np.ndarray'`、台帳から引くなら `ops3d.get("absolute_phase")`)

## 使い方

巻き込み位相を、粗いが絶対的な位相推定で「次数確定」して絶対位相にする。

Φ = wrapped + 2π·round((coarse − wrapped) / 2π)

wrapped: wrapped_phase の出力 (-π,π] の 2D 配列(高精度・絶対次数なし)。
coarse:  同形の 2D 配列。**絶対だが粗い**位相推定 [rad]。Gray code で復号した投影機
         コラム番号を位相に直したもの(2π·freq·col/width)が典型。NaN 可(出力も NaN)。

返り値: 絶対位相 [rad] (2D float64)。無効画素(どちらかが NaN)は NaN。

なぜ必要か(空間アンラップとの違い): `unwrap_phase_2d` は隣接画素を辿って 2π 跳びを
繋ぐので、(a) 大域オフセット +2πm が残り、(b) オクルージョンで切れた島の間では次数が
伝播できない。本 op は画素ごとに独立に次数を決めるため、**島に分かれた場面でも絶対**で、
伝播も要らない。その代わり coarse の誤差が半周期(π)未満であることが要件。

要件(fail-closed): |coarse − Φ_true| < π。これを破ると round が隣の次数を選び、
その画素だけ 2π ぶん(= 縞 1 本ぶんの奥行き)静かにずれる。Gray code の粗さ(±0.5 コラム)
を位相に直した量が半周期を超えないよう、縞本数 freq を選ぶこと
(例: 投影機幅 512 px・freq 24 → 1 周期 21.3 px、Gray の ±0.5 px は余裕で内側)。

Raises: 形状不一致・2D でない・wrapped が (-π,π] を大きく外れる場合に ValueError。

来歴(公開文献): Gray code と位相シフトを併用して絶対位相を得る合成法 —
Sansoni et al., *Appl. Opt.* 38(31) 1999 / Zhang, *Opt. Lasers Eng.* 48 2010(総説)。
Gray code そのものの投影は Inokuchi et al., *ICPR* 1984。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light_scan](../../../../examples_3d/structured_light_scan.py) — `py -3.11 examples_3d/structured_light_scan.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [synthesize_fringes](synthesize_fringes.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
