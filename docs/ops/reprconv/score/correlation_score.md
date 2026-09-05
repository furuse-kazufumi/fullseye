---
op: correlation_score
dim: reprconv
category: score
in: voxel × voxel
out: score
examples: [representation_conversion, representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# correlation_score — REPRCONV `score` op

- **データ種**: `voxel × voxel` → `score`
- **呼び出し**: `import reprconv; reprconv.correlation_score(voxel_a, voxel_b)` (または `opsreprconv.get("correlation_score")`)

## 使い方

2 つの ``voxel`` → 正規化相互相関の ``score`` volume。**この型の唯一の入口**。

``score`` は ``refine_peak_newton`` が食う型だが、**台帳のどの op も
``score`` を産まなかった**(実測。生成器の種を置いてようやく到達していた)。
ここでは FFT による循環相互相関を返す:

    score[s] = sum_x (a[x] - mean_a) * (b[x + s] - mean_b) / (N * std_a * std_b)

したがって ``b`` が ``a`` を ``s0`` だけ ``np.roll`` したものなら、
ピークは**厳密に** ``s0`` に立つ(閉形式の真値。テストがこれを使う)。
循環相関なので端は巻き込む —— **打ち切り相関ではない**ことを明記しておく。

Args:
    voxel_a: (D, H, W)。
    voxel_b: (D, H, W)、``voxel_a`` と同形。
Returns:
    (D, H, W) float64、値域は概ね [-1, 1] (完全一致で 1.0)。
Raises:
    ValueError: 3-D でない / 形が違う / 定数体積(標準偏差 0)/ 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`
- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`score` を入力に取れる)

[score_to_position](score_to_position.md) · [score_to_image2d](score_to_image2d.md)

## 同カテゴリ(`score`)

[score_to_position](score_to_position.md) · [score_to_image2d](score_to_image2d.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
