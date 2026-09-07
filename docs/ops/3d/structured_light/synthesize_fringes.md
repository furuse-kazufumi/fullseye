---
op: synthesize_fringes
dim: 3d
category: structured_light
in: image2d
out: images
examples: [structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# synthesize_fringes — 3D `structured_light` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import fringe; fringe.synthesize_fringes(height, n_steps=4, freq=1.0, phase_gain=1.0, bias=0.5, amplitude=0.5, axis=1, noise=0.0, seed=None, return_phase=False)` (または `ops3d.get("synthesize_fringes")`)
- **台帳経由の戻り値**: `fullseye.ledger.synthesize_fringes(...)` は**宣言 out 型 `images` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.synthesize_fringes.raw(...)`、または `fringe.synthesize_fringes` を直接呼ぶ。

## 使い方

既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。

モデル: 総位相 φ(x,y) = φ_carrier + phase_gain·height。搬送波 φ_carrier は視野を横切る線形
ランプ(freq 周期)。各フレームは I_n = bias + amplitude·cos(φ - δ_n), δ_n = 2πn/N。
この符号規約により wrapped_phase(...) は総位相 φ をそのまま復元する。

height:      2D 配列(計測対象の高さ場、任意単位)。
n_steps:     位相シフト枚数 N(>=3)。
freq:        視野幅を横切る搬送波の周期数(縞本数)。0 なら搬送波なし(height のみ)。
phase_gain:  高さ→位相の変換ゲイン(rad/単位)。復号側の較正 k = 1/phase_gain に対応。
bias:        平均輝度 a(既定 0.5)。
amplitude:   縞振幅 b(既定 0.5)。bias±amplitude が [0,1] に収まると自然。
axis:        搬送波の方向(1 = 列方向 x に沿う既定、0 = 行方向 y)。
noise:       付加ガウスノイズの標準偏差(0 で無ノイズ)。
seed:        ノイズ用乱数シード。
return_phase: True なら (images, total_phase) を返す(テスト・デバッグ用)。

返り値: (N, H, W) float 配列(値域 [0,1] にクリップ)。return_phase=True なら位相も。

## 背景知識ガイド(この op の手前にある物理・規約)

- [depth_sensors](../guides/depth_sensors.md) — 深度センサの知識 — 測距原理・実機の値・欠測の出方

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`

## 型が繋がる次の op(`images` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [photometric_stereo](../photometric/photometric_stereo.md) · [wrapped_phase](wrapped_phase.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [carve](../space_carving/carve.md) · [visual_hull](../space_carving/visual_hull.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [absolute_phase](absolute_phase.md) · [triangulate_column](triangulate_column.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
