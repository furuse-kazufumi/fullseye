---
op: deflectometry_screen_pattern
dim: specular
category: deflectometry
in: 
out: images
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.0  # fullseye lib version this note was generated for
---

# deflectometry_screen_pattern — SPECULAR `deflectometry` op

- **データ種**: `なし` → `images`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.deflectometry_screen_pattern(rig=None, period_mm=10.0, n_steps=4, direction='x', kind='fringe', max_side_px=1024)` (実装を直接呼ぶなら `import deflectometry; deflectometry.deflectometry_screen_pattern(rig=None, period_mm=10.0, n_steps=4, direction='x', kind='fringe', max_side_px=1024)`、台帳から引くなら `opsspecular.get("deflectometry_screen_pattern")`)

## 使い方

画面に表示するパターン(画面の画素の格子)。→ 画像のリスト(各 (行, 列)、値 [0, 1])。

``kind="fringe"``: 位相シフト縞 I_n = a + b cos(2π s / ``period_mm`` − 2πn/N)(a = 0.5、b = 0.45、
s は ``direction`` が ``"x"`` なら画面の u、``"y"`` なら v、中心が 0)を ``n_steps`` = N 枚。
``fringe.wrapped_phase`` で復号すると位相 2π s / 周期 がそのまま戻る(同じ符号規約)。
``"uniform"``: 一様な白(0.8)1 枚。``"softbox"``: 片側から明るい大きな面光源 1 枚
(0.75 + 0.2 u / 半幅)—— どちらも「縞を使わない普通の撮り方」の比較用。
画面の画素数は ``screen_size_mm / screen_pixel_mm``。図のために長辺を ``max_side_px`` 画素まで
間引く(値は各画素の中心で評価するので間引いても縞の位相は正しい)。
`deflectometry_render` は同じ輝度の式を連続の座標で評価する(画面の画素の格子は入れない)。

Raises: ``ValueError`` —— 周期が正でない、N < 3(縞のとき)、方向が x / y でない、kind が
fringe / uniform / softbox でない、max_side_px < 8、rig が不正。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`images` を入力に取れる)

[photometric_stereo_robust](../photometric/photometric_stereo_robust.md) · [photometric_residual](../photometric/photometric_residual.md)

## 同カテゴリ(`deflectometry`)

[deflectometry_rig](deflectometry_rig.md) · [deflectometry_render](deflectometry_render.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md) · [slope_to_curvature](slope_to_curvature.md) · [deflectometry_sensitivity](deflectometry_sensitivity.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
