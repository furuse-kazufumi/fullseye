---
op: flow_to_rgbimage
dim: reprconv
category: flow
in: flow_dense
out: rgbimage
examples: [representation_conversion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# flow_to_rgbimage — REPRCONV `flow` op

- **データ種**: `flow_dense` → `rgbimage`
- **呼び出し**: `import reprconv; reprconv.flow_to_rgbimage(flow, index=None, scale=None)` (または `opsreprconv.get("flow_to_rgbimage")`)

## 使い方

密なシーンフローの 1 スライス → 色相=向き・明度=速さの ``rgbimage``。

光学フローの標準的な可視化(色相環)を 3-D フローの z スライスに当てる:
``hue = atan2(dy, dx)``(度で 0-360)、``value = |(dy, dx)| / scale``、
彩度は 1。**dz は捨てる** —— 面内成分だけの図であることを明示する
(捨てた成分を色に混ぜると「見えている色が何の量か」が誰にも言えなくなる)。

**一方向**。色相環の凡例は図の側で必ず一緒に焼くこと(色の意味が書いていない
フロー図は、綺麗なだけで読めない)。

Args:
    flow: (3, D, H, W)。
    index: 取り出す z スライス(既定 = 中央)。
    scale: 明度 1.0 に対応する面内速さ(既定 = そのスライスの最大値。
        0 なら全面黒を返す)。
Returns:
    (H, W, 3) float64、値域 [0, 1]。
Raises:
    ValueError: 密フローでない / index が範囲外 / scale <= 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_conversion](../../../../examples/representation_conversion.py) — `py -3.11 examples/representation_conversion.py`

## 型が繋がる次の op(`rgbimage` を入力に取れる)

—

## 同カテゴリ(`flow`)

[flow_magnitude](flow_magnitude.md) · [flow_speed](flow_speed.md) · [flow_apply](flow_apply.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
