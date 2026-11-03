---
op: features_match
dim: matchreg
category: featmatch
in: table × table
out: table
gpu: なし
examples: [poc_part_locate_features]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# features_match — MATCHREG `featmatch` op

- **データ種**: `table × table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.features_match(features1, features2, ratio=0.8, mutual=True, max_distance=None)` (実装を直接呼ぶなら `import featmatch; featmatch.features_match(features1, features2, ratio=0.8, mutual=True, max_distance=None)`、台帳から引くなら `opsmatchreg.get("features_match")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

2 つの特徴の表を最近傍 + 比の検定(+ 相互最近傍)で照合する。→ table(``kind="feature_matches"``)。

記述子が実数(SIFT)なら L2、2 値(ORB)なら Hamming。1 番目に近い相手が 2 番目より明らかに近い
(L2 は ``d1 < ratio · d2``、2 乗距離では ``ratio²`` で比べる。Hamming は ``d1 < ratio · d2``)
ときだけ残し、``mutual=True`` なら相手の側から見ても最近傍であることを求める。

実数の記述子での規則は :func:`features.match_descriptors` と同じ(同じ入力で同じ組が返ることを
``tests/test_featmatch.py`` が固定している)。違いは距離行列を一括で作ること(GPU の影の経路に
乗る形)と、2 値の記述子を受けること。

Args:
    features1, features2: :func:`features_sift` / :func:`features_orb` の表。記述子の種類が同じであること。
    ratio: 比の検定のしきい値(0 < ratio <= 1、既定 0.8)。
    mutual: 相互最近傍を求めるか。
    max_distance: 距離の上限(L2 は距離そのもの、Hamming はビット数)。``None`` なら無し。

Returns:
    dict(``kind="feature_matches"``)。``idx`` (M,2) / ``pts1`` / ``pts2`` (M,2) の (x, y) /
    ``distance`` (M,)(L2 は距離、Hamming はビット数)/ ``ratio_value`` (M,)(d1/d2)/ ``metric`` /
    ``n1`` / ``n2`` / ``image_shape1`` / ``image_shape2``。

Raises:
    ValueError: 表の種類が違う / 記述子の種類か次元が違う / 引数が値域外。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_part_locate_features](../../../../examples/poc_part_locate_features.py) — `py -3.11 examples/poc_part_locate_features.py`

## 型が繋がる次の op(`table` を入力に取れる)

[ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [registration_to_flow2d](../intensityreg/registration_to_flow2d.md)

## 同カテゴリ(`featmatch`)

[features_sift](features_sift.md) · [features_orb](features_orb.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md) · [features_accuracy_table](features_accuracy_table.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
