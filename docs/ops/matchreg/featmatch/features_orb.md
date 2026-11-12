---
op: features_orb
dim: matchreg
category: featmatch
in: image2d
out: table
gpu: なし
examples: [poc_part_locate_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# features_orb — MATCHREG `featmatch` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.features_orb(image, n_features=1000, n_levels=8, scale_factor=1.2, fast_threshold=0.08, harris_k=0.04)` (実装を直接呼ぶなら `import featmatch; featmatch.features_orb(image, n_features=1000, n_levels=8, scale_factor=1.2, fast_threshold=0.08, harris_k=0.04)`、台帳から引くなら `opsmatchreg.get("features_orb")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

ORB の特徴点と 256 bit の 2 値記述子(Rublee et al. 2011)。→ table(``kind="features"``)。

縮小の段(``scale_factor`` ずつ ``n_levels`` 段)ごとに FAST-9 の角(:func:`features.fast_corners`
を再利用)を拾い、Harris の応答で順位をつけて段ごとの割り当て数だけ残す。向きは半径 15 の円の
輝度重心(Rosin 1999)、記述子はガウス(σ=2)でならした像の上で、向きに合わせて回した 256 組の
明暗比較。

★学習した rBRIEF の対の表は使わない(乱数で固定した対 = steered BRIEF)。OpenCV の ORB の
記述子とは**ビット単位で一致しない**。比べられるのは「照合して推定したホモグラフィの誤差」まで。

座標は原画像の **(x, y)**(段の座標 × 段の倍率)。``scale`` は段の倍率 × 31(パッチの一辺)。

Args:
    image: 2-D の濃淡画像([0, 1] の尺度。``fast_threshold`` がこの尺度)。
    n_features: 全段の合計の上限(段ごとの割り当ては面積に比例する等比数列)。
    n_levels: 段の数。
    scale_factor: 段の縮小率(> 1)。
    fast_threshold: FAST の明暗差のしきい値(既定 0.08 ≈ 20/255)。
    harris_k: Harris の k。

Returns:
    dict(``kind="features"``, ``detector="orb"``)。``descriptors`` は (N,32) uint8
    (256 bit を詰めたもの)、``descriptor_kind="binary"``。他の鍵は :func:`features_sift` と同じ。

Raises:
    ValueError: 2-D でない / 16 px 未満 / 非有限 / 定数画像 / 引数が値域外(``scale_factor <= 1`` など)。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_part_locate_features](../../../../examples/poc_part_locate_features.py) — `py -3.11 examples/poc_part_locate_features.py`

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [registration_to_flow2d](../intensityreg/registration_to_flow2d.md)

## 同カテゴリ(`featmatch`)

[features_sift](features_sift.md) · [features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [features_accuracy_table](features_accuracy_table.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
