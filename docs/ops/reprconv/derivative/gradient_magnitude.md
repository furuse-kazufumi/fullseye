---
op: gradient_magnitude
dim: reprconv
category: derivative
in: gradient
out: voxel
gpu: なし
examples: [type_connectivity_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# gradient_magnitude — REPRCONV `derivative` op

- **データ種**: `gradient` → `voxel`
- **呼び出し**: `import fullseye as fs; fs.ledger.gradient_magnitude(gradient)` (実装を直接呼ぶなら `import reprconv; reprconv.gradient_magnitude(gradient)`、台帳から引くなら `opsreprconv.get("gradient_magnitude")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3-D 勾配 ``gradient`` → 勾配の大きさの体積 ``voxel``。``gradient`` 型の出口。

``|∇I| = sqrt(gz² + gy² + gx²)``。``gradient3d`` の形 ``(gmag, gvec)`` は ``gvec`` から
計算し直す(``gmag`` を信じて素通しにしない —— 渡された対が食い違っていても気づけないため)。
``sobel3d`` の形 ``(gz, gy, gx)`` は利得 32 を割ってから計算するので、**どちらの産み手から
来ても真の勾配の大きさ**(1 voxel あたりの濃度変化)になる。

**一方向**(向き 2 自由度を捨てる)。向きを残すなら :func:`gradient_coherence` や
``sobel3d`` の成分そのもの。

★外から来た勾配(微分可能レンダラの出力など)は ``(gmag, gvec)`` の形で渡すこと。
3 本の形は ``sobel3d`` の利得 32 として割るので、利得 1 の 3 本を渡すと 1/32 に出る
(形だけでは利得を見分けられない。型を分けるかは ``docs/TYPE_CONNECTIVITY.md`` の案)。

Args:
    gradient: ``gradient3d`` の ``(gmag, gvec)`` か ``sobel3d`` の ``(gz, gy, gx)``。
Returns:
    (D, H, W) float64。
Raises:
    ValueError: どちらの形でもない / 非有限 / 空。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [type_connectivity_tour](../../../../examples/type_connectivity_tour.py) — `py -3.11 examples/type_connectivity_tour.py`

## 型が繋がる次の op(`voxel` を入力に取れる)

[correlation_score](../score/correlation_score.md)

## 同カテゴリ(`derivative`)

[gradient_coherence](gradient_coherence.md) · [hessian_determinant](hessian_determinant.md) · [hessian_vesselness](hessian_vesselness.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
