---
op: ransac_homography
dim: matchreg
category: featmatch
in: table
out: table
gpu: なし
examples: [poc_part_locate_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# ransac_homography — MATCHREG `featmatch` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.ransac_homography(matches, thresh=2.0, confidence=0.999, max_iters=5000, score='msac', local_optimization=True, min_inliers=8, seed=0, model='projective')` (実装を直接呼ぶなら `import featmatch; featmatch.ransac_homography(matches, thresh=2.0, confidence=0.999, max_iters=5000, score='msac', local_optimization=True, min_inliers=8, seed=0, model='projective')`、台帳から引くなら `opsmatchreg.get("ransac_homography")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

照合の組から頑健にホモグラフィ(pts1 → pts2、(x, y) の同次座標)を推定する。→ table(``kind="homography"``)。

4 点の最小標本を引き、前向きの転送誤差 ``|H p1 - p2|`` で採点する。既定の採点は MSAC
(打ち切り二乗 ``min(r², thresh²)`` の和、Torr & Zisserman 2000)で、内れ値の数だけ数える
素の RANSAC(``score="ransac"``)より閾値の近くの点の扱いが滑らか。必要な試行回数は
内れ値の割合から都度見積もり(``confidence``)、良い仮説が出るたびに内れ値で当てはめ直す
(``local_optimization``、LO-RANSAC)。行列の当てはめは正規化 DLT(``twoview._homography_dlt``、
Hartley の正規化)を再利用し、退化した標本(3 点が一直線)は捨てる。

★既存の ``mosaic.proj_match_points_ransac`` は (row, col) の点・正規化なしの DLT・固定回数で、
これは (x, y)・正規化 DLT・適応回数・MSAC・LO。座標の順が逆なので混ぜないこと。

★**自由度の少ない模型**(``model="translation"`` 1 点 / ``"similarity"`` 2 点 / ``"affine"`` 3 点)を
選べる。返りはどれも 3×3。正しい組が狭い帯にしか無い(貼り合わせの重なりが細い)とき、8 自由度の
射影はその帯の組には合うのに帯の外へ大きく外挿を外す(``examples/poc_part_locate_features.py`` の
5 節: 重なり 80 px・正しい組 9 で、射影は原点の並進を 15 px 外し、相似は 0.1 px 以内)。

Args:
    matches: :func:`features_match` の表。
    thresh: 内れ値の転送誤差の上限 [px]。
    confidence: 外れ値を含まない標本を少なくとも 1 回引く確率(< 1)。
    max_iters: 試行回数の上限。
    score: ``"msac"`` / ``"ransac"``。
    local_optimization: 内れ値で当てはめ直すか。
    min_inliers: これ未満の内れ値しか集まらなければ失敗(``ValueError``)。
    seed: 標本の乱数の種(同じ種で同じ結果)。
    model: ``"projective"``(既定、8 自由度)/ ``"affine"`` / ``"similarity"`` / ``"translation"``。

Returns:
    dict(``kind="homography"``)。``H`` (3,3)(``H[2,2] = 1``)/ ``model`` / ``inliers`` (M,) bool /
    ``n_inliers`` / ``inlier_ratio`` / ``rms_px``(内れ値の転送誤差の rms)/ ``iterations`` /
    ``score`` / ``thresh`` / ``image_shape1`` / ``image_shape2``。

Raises:
    ValueError: 表の種類が違う / 模型の最小標本より少ない / 非有限 / 引数が値域外 / 内れ値が ``min_inliers`` 未満
        (「いちばんましな H」を成功として返さない)。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_part_locate_features](../../../../examples/poc_part_locate_features.py) — `py -3.11 examples/poc_part_locate_features.py`

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](features_match.md) · [ransac_fundamental](ransac_fundamental.md) · [registration_to_flow2d](../intensityreg/registration_to_flow2d.md)

## 同カテゴリ(`featmatch`)

[features_sift](features_sift.md) · [features_orb](features_orb.md) · [features_match](features_match.md) · [ransac_fundamental](ransac_fundamental.md) · [features_accuracy_table](features_accuracy_table.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
