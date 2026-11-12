---
op: features_accuracy_table
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

# features_accuracy_table — MATCHREG `featmatch` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.features_accuracy_table(image, detector='sift', conditions=None, tol_px=2.0, ransac_thresh=2.0, seed=0, detector_kwargs=None)` (実装を直接呼ぶなら `import featmatch; featmatch.features_accuracy_table(image, detector='sift', conditions=None, tol_px=2.0, ransac_thresh=2.0, seed=0, detector_kwargs=None)`、台帳から引くなら `opsmatchreg.get("features_accuracy_table")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

既知の変換で合成した組で、特徴点の再現率・照合精度・ホモグラフィの誤差を条件ごとに表で返す。→ table。

``image`` を条件ごとの既知のホモグラフィ ``H_true``(中心まわりの回転・拡大・遠近)で写し
(3 次スプライン補間 —— 照合側と違う補間で、補間の型が一致する甘さを避ける)、照明(利得・
ガンマ)・ぼけ・雑音を足した 2 枚目を作る。2 枚とも検出 → 記述 → :func:`features_match` →
:func:`ransac_homography` を走らせ、**合成に使った真の H** で答え合わせする:

* ``repeatability`` —— 2 枚の共通の領域にある 1 枚目の点のうち、``H_true`` で写した位置から
  ``tol_px`` 以内に 2 枚目の点があるものの割合(Mikolajczyk & Schmid 2005 の考え方を点の距離で。
  領域の重なりではない)。
* ``precision`` —— 照合の組のうち ``|H_true p1 - p2| < tol_px`` のものの割合。
* ``matching_score`` —— 正しい照合の数 / 共通の領域にある 1 枚目の点の数。
* ``corner_error_px`` —— 推定した H と真の H で 4 隅を写したときの距離の平均(HPatches)。
  RANSAC が合意に届かなければ ``homography_ok=False`` で ``corner_error_px=None``。

答えの真値は合成のパラメータそのもので、推定側はそれを知らない(使った式で答え合わせする門
ではない)。限界: 平面の射影変換だけ(視差・遮蔽・鏡面反射は入らない)。照明はこの画像全体に
一様(局所の影は入らない)。

Args:
    image: 2-D の濃淡画像 [0, 1]。模様の乏しい画像では行がほとんど 0 になる(それも結果)。
    detector: ``"sift"`` / ``"orb"``。
    conditions: ``None`` なら :data:`DEFAULT_CONDITIONS`。条件名の並び(既定の名前から選ぶ)か、
        ``(名前, {rotate_deg, scale, perspective, gain, gamma, blur_sigma, noise_sigma})`` の並び。
    tol_px: 正しい対応とみなす距離 [px]。
    ransac_thresh: :func:`ransac_homography` の ``thresh``。
    seed: 雑音と RANSAC の乱数の種。
    detector_kwargs: 検出器へ渡す追加の引数(dict)。

Returns:
    dict(``kind="feature_accuracy"``)。``rows``(条件ごとの dict の list)/ ``columns`` /
    ``detector`` / ``tol_px`` / ``image_shape`` / ``n_conditions`` /
    ``worst``(``corner_error_px`` が最大か失敗した条件の名前)。

Raises:
    ValueError: 画像が不正 / 検出器の名前が違う / 条件の名前・鍵・値が不正。

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

[features_sift](features_sift.md) · [features_orb](features_orb.md) · [features_match](features_match.md) · [ransac_homography](ransac_homography.md) · [ransac_fundamental](ransac_fundamental.md)

---
*Provenance: featmatch.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
