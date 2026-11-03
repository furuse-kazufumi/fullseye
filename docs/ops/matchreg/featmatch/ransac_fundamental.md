---
op: ransac_fundamental
dim: matchreg
category: featmatch
in: table
out: table
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# ransac_fundamental — MATCHREG `featmatch` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ransac_fundamental(matches, thresh=1.0, confidence=0.999, max_iters=5000, score='msac', local_optimization=True, min_inliers=15, seed=0)` (実装を直接呼ぶなら `import featmatch; featmatch.ransac_fundamental(matches, thresh=1.0, confidence=0.999, max_iters=5000, score='msac', local_optimization=True, min_inliers=15, seed=0)`、台帳から引くなら `opsmatchreg.get("ransac_fundamental")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

照合の組から頑健に基礎行列 F(``x2ᵀ F x1 = 0``)を推定する。→ table(``kind="fundamental"``)。

8 点の最小標本を正規化 8 点法(:func:`twoview.fundamental_8point`、rank 2 を強制)で当てはめ、
Sampson 距離(エピポーラ線までの幾何距離の 1 次近似)で採点する。採点・適応回数・局所最適化は
:func:`ransac_homography` と同じ。

限界: 平面の場面や純回転では F は一意に決まらない(ホモグラフィ 1 つで説明できる退化)。
その判定はしない —— 姿勢まで欲しいなら :func:`twoview.recover_pose`(平面を拒む)へ。
7 点法は使わない(最小標本は 8)。

Args:
    matches: :func:`features_match` の表。
    thresh: 内れ値の Sampson 距離の上限 [px]。
    confidence, max_iters, score, local_optimization, seed: :func:`ransac_homography` と同じ。
    min_inliers: これ未満なら失敗(``ValueError``)。

Returns:
    dict(``kind="fundamental"``)。``F`` (3,3)(フロベニウスノルム 1、符号は ``F[2,2] >= 0``)/
    ``inliers`` / ``n_inliers`` / ``inlier_ratio`` / ``rms_px``(内れ値の Sampson 距離の rms)/
    ``iterations`` / ``score`` / ``thresh``。

Raises:
    ValueError: 表の種類が違う / 8 組未満 / 非有限 / 引数が値域外 / 内れ値が ``min_inliers`` 未満。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [registration_to_flow2d](../intensityreg/registration_to_flow2d.md)

## 同カテゴリ(`featmatch`)

[features_sift](features_sift.md) · [features_orb](features_orb.md) · [features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [features_accuracy_table](features_accuracy_table.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
