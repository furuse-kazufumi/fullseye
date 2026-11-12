---
op: hessian_vesselness
dim: reprconv
category: derivative
in: hessian
out: voxel
gpu: なし
examples: [hessian_numpy_chain, type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# hessian_vesselness — REPRCONV `derivative` op

- **データ種**: `hessian` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.hessian_vesselness(hessian, alpha=0.5, beta=0.5, c=None, black_ridges=False)` (実装を直接呼ぶなら `import reprconv; reprconv.hessian_vesselness(hessian, alpha=0.5, beta=0.5, c=None, black_ridges=False)`、台帳から引くなら `opsreprconv.get("hessian_vesselness")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3-D Hessian → Frangi の管らしさ(vesselness)``voxel``、値域 [0, 1]。

固有値を ``|λ1| ≤ |λ2| ≤ |λ3|`` に並べ、``Ra = |λ2|/|λ3|``(板と管を分ける)、
``Rb = |λ1|/sqrt(|λ2 λ3|)``(塊を除く)、``S = sqrt(λ1²+λ2²+λ3²)``(背景の雑音を除く)から

    V = (1 − exp(−Ra²/2α²)) · exp(−Rb²/2β²) · (1 − exp(−S²/2c²))

を返す(Frangi et al. 1998, MICCAI)。明るい管(``black_ridges=False``)では
``λ2 > 0`` か ``λ3 > 0`` の voxel を 0 にする(暗い管なら符号を逆に)。
``c`` の既定は Frangi の勧めどおり ``S`` の最大値の半分。

``vol_frangi`` は体積から Hessian を**自分で作る**(尺度ごとに)のに対し、こちらは
``hessian`` 型を受ける —— Hessian の出どころ(``hessian3d`` / 外部の微分)を選べ、
同じ Hessian から :func:`hessian_determinant` など複数の量を引き出せる。
1 尺度だけ(多尺度の最大は呼ぶ側で取る)。

Args:
    hessian: ``hessian3d`` の 6 成分 (zz, yy, xx, zy, zx, yx)。
    alpha, beta: Frangi の感度(既定 0.5 / 0.5)。> 0。
    c: 構造の強さの感度。None で ``max(S)/2``。> 0。全面 0 の Hessian では 0 を返す。
    black_ridges: True で暗い管(背景より暗い)を拾う。
Returns:
    (D, H, W) float64、[0, 1]。
Raises:
    ValueError: 6 成分でない / 非有限 / alpha・beta・c が正でない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [hessian_numpy_chain](../../../../examples/hessian_numpy_chain.py) — `py -3.11 examples/hessian_numpy_chain.py`
- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md) · [voxel_to_hessian](voxel_to_hessian.md)

## 同カテゴリ(`derivative`)

[gradient_magnitude](gradient_magnitude.md) · [gradient_coherence](gradient_coherence.md) · [voxel_to_hessian](voxel_to_hessian.md) · [hessian_determinant](hessian_determinant.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
