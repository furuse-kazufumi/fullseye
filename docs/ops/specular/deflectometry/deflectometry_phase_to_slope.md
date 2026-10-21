---
op: deflectometry_phase_to_slope
dim: specular
category: deflectometry
in: image2d × image2d
out: normalmap
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# deflectometry_phase_to_slope — SPECULAR `deflectometry` op

- **データ種**: `image2d × image2d` → `normalmap`
- **呼び出し**: `import fullseye as fs; fs.ledger.deflectometry_phase_to_slope(phase_x, phase_y, rig=None, period_mm=10.0, z_ref=0.0)` (実装を直接呼ぶなら `import deflectometry; deflectometry.deflectometry_phase_to_slope(phase_x, phase_y, rig=None, period_mm=10.0, z_ref=0.0)`、台帳から引くなら `opsspecular.get("deflectometry_phase_to_slope")`)

## 使い方

画面の絶対位相 2 枚(u 方向・v 方向の縞)→ 面の格子上の法線マップ (H, W, 3)。

``phase_x`` / ``phase_y``: カメラの画素ごとの**絶対**位相 [rad] (次数を確定したもの。
`fringe.absolute_phase` で粗い縞から決める)。画面の座標は u = φ_x·周期 / 2π、v = φ_y·周期 / 2π
(画面の中心が 0)。NaN の画素は無効。

面の格子(`deflectometry_render` と同じ、視野の中心が原点、間隔 field / (W − 1))の各点
P = (x, y, ``z_ref``) をカメラに投影して位相を双線形に読み、画面の点 S を出して、
入射 S→P と反射 P→C から法線を `match3d.normal_from_reflection` で作る(n ∝ 反射 − 入射)。
返り値は ``photometric`` と同じ規約(+z が上、x が列、y が行)なので、そのまま
`photometric.integrate_normals`(高さへ)や `slope_to_curvature`(曲率へ)に流せる。
位相が NaN・視野の外の点は NaN。

★高さと傾きの不定性: 面の高さを ``z_ref``(数か (H, W) の配列)と仮定して法線を出す。本当の面が
Δz ずれていると、法線は Δz sin θ / d だけ(視野の中心で)傾いて出る —— 1 台のカメラと 1 枚の
画面では分けられない(`deflectometry_sensitivity` が係数を返す)。局所の凹みの形はほぼ影響を
受けないが、面全体の傾きと曲がりは位置の不確かさに引きずられる。

Raises: ``ValueError`` —— 位相が 2-D でない・形が違う・無限大を含む、周期が正でない、
``z_ref`` が有限でない・形が違う、rig が不正。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`normalmap` を入力に取れる)

[brdf_blinn_phong](../reflectance/brdf_blinn_phong.md) · [brdf_microfacet](../reflectance/brdf_microfacet.md) · [dichromatic_render](../reflectance/dichromatic_render.md) · [slope_to_curvature](slope_to_curvature.md)

## 同カテゴリ(`deflectometry`)

[deflectometry_rig](deflectometry_rig.md) · [deflectometry_screen_pattern](deflectometry_screen_pattern.md) · [deflectometry_render](deflectometry_render.md) · [slope_to_curvature](slope_to_curvature.md) · [deflectometry_sensitivity](deflectometry_sensitivity.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
