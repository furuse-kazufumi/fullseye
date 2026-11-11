---
op: gradient_coherence
dim: reprconv
category: derivative
in: gradient
out: voxel
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# gradient_coherence — REPRCONV `derivative` op

- **データ種**: `gradient` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.gradient_coherence(gradient, sigma=1.5, eps=1e-12)` (実装を直接呼ぶなら `import reprconv; reprconv.gradient_coherence(gradient, sigma=1.5, eps=1e-12)`、台帳から引くなら `opsreprconv.get("gradient_coherence")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3-D 勾配 → 構造テンソルの**面らしさ**(コヒーレンス)``voxel``、値域 [0, 1]。

各 voxel で勾配の外積 ``g gᵀ`` をガウス ``sigma`` で平均した構造テンソル ``J`` を作り、
固有値 ``μ1 ≥ μ2 ≥ μ3 ≥ 0`` から ``(μ1 − μ2) / (μ1 + μ2 + μ3 + eps)`` を返す
(Westin の線形異方性を構造テンソルに当てたもの。Bigün & Granlund 1987、Westin 2002)。
近傍の勾配が 1 方向にそろう(層・板・界面)と 1 に近づき、向きがばらばら(等方的な
ざらつき・塊)だと 0 に近づく。**勾配の大きさには依らない**(比なので)。
平らで勾配の無い所は分母が ``eps`` だけになり 0 を返す。

``gradient`` 型を一級の入力として受けるので、勾配の出どころ(``gradient3d`` /
``sobel3d`` / 外部の微分可能レンダラ)を問わない。

Args:
    gradient: ``gradient3d`` の ``(gmag, gvec)`` か ``sobel3d`` の ``(gz, gy, gx)``。
    sigma: 構造テンソルを平均するガウスの標準偏差 [voxel]。> 0。
    eps: 分母の下駄(勾配ゼロの所で 0 を返すため)。> 0。
Returns:
    (D, H, W) float64、[0, 1]。
Raises:
    ValueError: 形が違う / 非有限 / sigma <= 0 / eps <= 0。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md) · [voxel_to_hessian](voxel_to_hessian.md)

## 同カテゴリ(`derivative`)

[gradient_magnitude](gradient_magnitude.md) · [voxel_to_hessian](voxel_to_hessian.md) · [hessian_determinant](hessian_determinant.md) · [hessian_vesselness](hessian_vesselness.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
