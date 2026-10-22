---
op: deflectometry_sensitivity
dim: specular
category: deflectometry
in: 
out: table
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# deflectometry_sensitivity — SPECULAR `deflectometry` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.deflectometry_sensitivity(rig=None, period_mm=10.0, n_steps=4, noise_sigma=0.004, fringe_amplitude=None, bits=8, diffuse_fraction=0.0)` (実装を直接呼ぶなら `import deflectometry; deflectometry.deflectometry_sensitivity(rig=None, period_mm=10.0, n_steps=4, noise_sigma=0.004, fringe_amplitude=None, bits=8, diffuse_fraction=0.0)`、台帳から引くなら `opsspecular.get("deflectometry_sensitivity")`)

## 使い方

撮る前に、最小検出傾き・高さと傾きの不定性の係数・ピントのぼけを閉形式で出す。→ dict。

返す鍵(角度は rad、長さは mm):
  * ``slope_pixel_bound`` —— 画面の画素ピッチ / (2d)。縞を使わず画面の画素を数えるときの傾きの刻み。
  * ``phase_noise_rad`` —— N ステップの位相雑音 √(2/N)·σ / b。σ は画素の雑音(``bits`` の量子化
    1/(2^bits − 1)/√12 を 2 乗和で足す)、b は縞の振幅(既定 0.45·(1 − k_d)·|M|、M は面にピントの
    ときの画面側の錯乱円 A·d/L の円板の MTF = `deflectometry_render` の既定と同じ条件。★初版は M を
    忘れていて、実測の位相雑音が閉形式の 1.12 倍に出た —— 内訳を追って直した)。
  * ``fringe_amplitude`` —— 上で使った b。
  * ``screen_noise_mm`` —— 画面の座標の雑音 周期·σ_φ / 2π。
  * ``slope_noise_x`` / ``slope_noise_y`` —— σ_u / (2d) と σ_u / (2 d cos θ)(入射面内と直交方向)。
  * ``height_slope_coupling`` —— 面が 1 mm ずれたときの見かけの傾き sin θ / d [rad/mm]。
  * ``blur_screen_focus_surface_mm`` / ``blur_surface_focus_screen_mm`` —— 面にピントを合わせたときの
    画面側の錯乱円 A·d / L と、画面にピントを合わせたときの面側の錯乱円 A·d / (L + d)。
  * ``contrast_focus_surface`` —— 面にピントのとき縞の振幅に掛かる円板の MTF。

Raises: ``ValueError`` —— 周期・振幅が正でない、N < 3、雑音が負、bits が 1〜16 の整数でも None
でもない、k_d が [0, 1) の外、ぼけで縞が消える(MTF がちょうど 0)、rig が不正。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`deflectometry`)

[deflectometry_rig](deflectometry_rig.md) · [deflectometry_screen_pattern](deflectometry_screen_pattern.md) · [deflectometry_render](deflectometry_render.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md) · [slope_to_curvature](slope_to_curvature.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
