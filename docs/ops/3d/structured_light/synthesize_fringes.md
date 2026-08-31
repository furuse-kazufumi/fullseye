---
op: synthesize_fringes
dim: 3d
category: structured_light
in: image2d
out: images
examples: [structured_light]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# synthesize_fringes — 3D `structured_light` op

- **データ種**: `image2d` → `images`
- **呼び出し**: `import fringe; fringe.synthesize_fringes(height, n_steps=4, freq=1.0, phase_gain=1.0, bias=0.5, amplitude=0.5, axis=1, noise=0.0, seed=None, return_phase=False)` (または `ops3d.get("synthesize_fringes")`)

## 使い方

既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [structured_light](../../../../examples_3d/structured_light.py) — `py -3.11 examples_3d/structured_light.py`

## 型が繋がる次の op(`images` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [photometric_stereo](../photometric/photometric_stereo.md) · [wrapped_phase](wrapped_phase.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md) · [carve](../space_carving/carve.md) · [visual_hull](../space_carving/visual_hull.md)

## 同カテゴリ(`structured_light`)

[wrapped_phase](wrapped_phase.md) · [unwrap_phase_2d](unwrap_phase_2d.md) · [graycode_decode](graycode_decode.md) · [decode_fringe](decode_fringe.md)

---
*Provenance: fringe.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
