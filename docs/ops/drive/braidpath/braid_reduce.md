---
op: braid_reduce
dim: drive
category: braidpath
in: signal × scalar
out: signal
examples: [poc_braid_homotopy_classes]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.5.0  # fullseye lib version this note was generated for
---

# braid_reduce — DRIVE `braidpath` op

- **データ種**: `signal × scalar` → `signal`
- **呼び出し**: `import fullseye as fs; fs.ledger.braid_reduce(word, n_strands)` (実装を直接呼ぶなら `import braidpath; braidpath.braid_reduce(word, n_strands)`、台帳から引くなら `opsdrive.get("braid_reduce")`)

## 使い方

組紐語を Dehornoy の取っ手簡約で簡約する。**空の語が返る ⇔ 自明な組紐**(同じ類)。

取っ手 = σⱼ^e u σⱼ^(−e)(u に σⱼ^(±1)・σⱼ₋₁^(±1) が無い)。u の中の σⱼ₊₁^d を σⱼ₊₁^(−e) σⱼ^d σⱼ₊₁^e に替え、外側の
2 文字を消す(関係式だけを使うので組紐は変わらない)。左から最初に閉じる取っ手を選ぶ —— その中には別の取っ手が
無いので Dehornoy の意味で許され、有限回で止まる。返りの語は取っ手を持たず、空でなければ現れる最小の添字の
文字の符号がそろう(σ 正 / σ 負)。

Returns: int の 1-D 配列(簡約した語)。
Raises: ValueError(添字が範囲の外・0)、RuntimeError(語が ``MAX_WORD`` を超えて膨らんだ)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_braid_homotopy_classes](../../../../examples/poc_braid_homotopy_classes.py) — `py -3.11 examples/poc_braid_homotopy_classes.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[flight_vacuum](../ball/flight_vacuum.md) · [magnus_lift_coefficient](../ball/magnus_lift_coefficient.md) · [drag_coefficient_sphere](../ball/drag_coefficient_sphere.md) · [restitution_from_apexes](../ball/restitution_from_apexes.md) · [restitution_from_intervals](../ball/restitution_from_intervals.md) · [fit_parabola](../ball/fit_parabola.md) · [flight_fit](../ball/flight_fit.md) · [fit_aero](../ball/fit_aero.md)

## 同カテゴリ(`braidpath`)

[braid_from_trajectories](braid_from_trajectories.md) · [braid_artin_images](braid_artin_images.md) · [dynnikov_coordinates](dynnikov_coordinates.md) · [dynnikov_act](dynnikov_act.md) · [braid_equivalent](braid_equivalent.md) · [homotopy_class_compare](homotopy_class_compare.md) · [pairwise_winding](pairwise_winding.md) · [homotopy_shortest_paths](homotopy_shortest_paths.md)

---
*Provenance: braidpath.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
