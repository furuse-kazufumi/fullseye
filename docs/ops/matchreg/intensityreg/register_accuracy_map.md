---
op: register_accuracy_map
dim: matchreg
category: intensityreg
in: image2d × flow2d
out: table
gpu: なし
examples: [poc_sheet_deformation_ffd]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# register_accuracy_map — MATCHREG `intensityreg` op

- **データ種**: `image2d × flow2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_accuracy_map(fixed, true_flow2d, method='ffd', modality='same', noise_sigma=0.0, margin=4, seed=0, method_kwargs=None)` (実装を直接呼ぶなら `import intensityreg; intensityreg.register_accuracy_map(fixed, true_flow2d, method='ffd', modality='same', noise_sigma=0.0, margin=4, seed=0, method_kwargs=None)`、台帳から引くなら `opsmatchreg.get("register_accuracy_map")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

既知の変形場で合成した組で、推定した変形場の誤差を画素ごとに返す(精度の地図)。→ table。

``fixed`` と真の場 ``true_flow2d`` から :func:`synthesize_moving` で moving を作り(3 次スプライン、
明るさの写し、雑音)、``method`` で合わせ、推定の場と真の場の差の長さ(終点誤差 EPE [px])を
画素ごとに返す。答えの真値は合成に使った場そのもので、推定側はそれを知らない。

``method``: ``"ffd"`` / ``"demons"``(:func:`deformreg.demons_register`、場の向きは同じ)/
``"ecc"`` / ``"mi"``(パラメトリック。滑らかな場はアフィンでしか近似できない —— その近似の誤差も
地図に出る)/ ``"phase"``(:func:`aoi.register_image`、並進だけ)。

地図の内訳(どこで壊れるか)として、fixed の勾配の強さの 4 分位ごと・真の変位の大きさの 4 分位ごとの
EPE の中央値を ``by_texture`` / ``by_magnitude`` に返す(模様の無い所で場が決まらないことが数で出る)。
4 群は排他的(``[lo, hi)``、最後の群だけ ``[lo, hi]``)で、``n`` の和は集計した画素の数。同値が境界に
並ぶと群の大きさは 1/4 ずつにならない(全部同じ値なら最後の群に全部)。

Args:
    fixed: 基準の 2-D 画像。
    true_flow2d: 真の場 ``(2,H,W)`` の ``(dy, dx)``(結果と同じ向き)。逆写像が一意であること(勾配 < 1)。
    method: :data:`ACCURACY_METHODS`。
    modality: :data:`MODALITIES`(``"folded"`` は単調でない明るさ = ECC が効かない組)。
    noise_sigma: moving に足すガウス雑音の σ([0, 1] の尺度)。
    margin: 縁から除く画素数。
    seed: 雑音の種。
    method_kwargs: method へ渡す引数(dict)。

Returns:
    dict(``kind="registration_accuracy"``)。``error_map`` (H,W) [px] (集計から外した画素は 0)/
    ``mask``(集計した画素)/ ``epe_mean`` / ``epe_median`` / ``epe_p95`` / ``epe_max`` /
    ``true_flow2d`` / ``est_flow2d`` / ``moving`` / ``by_texture`` / ``by_magnitude`` / ``method`` /
    ``modality`` / ``noise_sigma`` / ``method_info``(method の返りの要約)。

Raises:
    ValueError: 画像・場が不正 / 場の逆写像が一意でない / method・modality が違う / method 自身の拒否。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_sheet_deformation_ffd](../../../../examples/poc_sheet_deformation_ffd.py) — `py -3.11 examples/poc_sheet_deformation_ffd.py`

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](../featmatch/features_match.md) · [ransac_homography](../featmatch/ransac_homography.md) · [ransac_fundamental](../featmatch/ransac_fundamental.md) · [registration_to_flow2d](registration_to_flow2d.md)

## 同カテゴリ(`intensityreg`)

[register_ecc](register_ecc.md) · [register_mi](register_mi.md) · [register_ffd](register_ffd.md) · [registration_to_flow2d](registration_to_flow2d.md) · [register_capture_range](register_capture_range.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
