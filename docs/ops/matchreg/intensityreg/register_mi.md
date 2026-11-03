---
op: register_mi
dim: matchreg
category: intensityreg
in: image2d × image2d
out: table
gpu: なし
examples: [poc_multimodal_mi_registration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.9.0  # fullseye lib version this note was generated for
---

# register_mi — MATCHREG `intensityreg` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_mi(fixed, moving, model='affine', bins=32, metric='nmi', levels=None, max_iter=2000, warp_init=None, min_overlap=0.25)` (実装を直接呼ぶなら `import intensityreg; intensityreg.register_mi(fixed, moving, model='affine', bins=32, metric='nmi', levels=None, max_iter=2000, warp_init=None, min_overlap=0.25)`、台帳から引くなら `opsmatchreg.get("register_mi")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

(正規化)相互情報量を最大にする剛体 / 相似 / アフィンで moving を fixed に合わせる。→ table(``kind="registration"``)。

撮像の違う組(可視と赤外、CT と MR、照明の向きの違う 2 枚)では明るさの対応が線形でも単調でも
ないので、相関(:func:`register_ecc`)や SSD は使えない。相互情報量は「fixed の明るさを知ると
moving の明るさがどれだけ当てられるか」なので、対応が**一対一でなくても**(折り返しがあっても)
合わせられる(Viola & Wells 1997、Maes et al. 1997)。既定の目的は重なりの大きさに鈍い正規化版
``(H(A)+H(B))/H(A,B)``(Studholme 1999、1〜2)。

同時ヒストグラムは fixed を硬いビン、moving を隣り合う 2 ビンへ線形に振り分け(変換のパラメータに
対して連続)、moving の外へ出た画素は数えない。最適化は Powell 法(微分を使わない)を粗から細の
``levels`` 段で。変数は回転・伸縮を画像の半径倍して画素の単位にそろえてある。

★:func:`imgmetrics.mutual_information` は**指標**(硬いビン 2 つ、ビットで返す)で、ここの目的関数は
振り分けのある別の推定量。合わせ終わった組を ``imgmetrics`` で測ると ``metric`` と少し違う。

Args:
    fixed: 基準の 2-D 画像。
    moving: 合わせる 2-D 画像(撮像が違ってよい)。
    model: :data:`MI_MODELS`。
    bins: ヒストグラムのビン数(2 以上)。
    metric: ``"nmi"``(既定)/ ``"mi"``(ビット)。
    levels: ピラミッドの段数。``None`` なら最も粗い段が 16 px 以上になる範囲で最大 3 段。
    max_iter: 段ごとの Powell の反復の上限。
    warp_init: 初期の変換(2×3 / 3×3、fixed → moving、射影の行は 0)。
    min_overlap: 重なりの割合がこれ未満の変換は目的関数を最悪にする(外へ逃げる解を防ぐ)。

Returns:
    dict(``kind="registration"``, ``method="mi"``)。鍵は :func:`register_ecc` と同じ。``metric_name`` は
    ``"nmi"`` / ``"mi_bits"``、加えて ``mi_bits`` / ``nmi``(全解像の最後の値)。

Raises:
    ValueError: 画像が不正 / ``model`` / ``metric`` が違う / 引数が値域外 / 初期の変換が射影 /
        合わせ終わっても重なりが ``min_overlap`` 未満。

## 詳しい使い方ガイド

- [matching_registration ファミリ ガイド](../guides/matching_registration.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_multimodal_mi_registration](../../../../examples/poc_multimodal_mi_registration.py) — `py -3.11 examples/poc_multimodal_mi_registration.py`

## 型が繋がる次の op(`table` を入力に取れる)

[features_match](../featmatch/features_match.md) · [ransac_homography](../featmatch/ransac_homography.md) · [ransac_fundamental](../featmatch/ransac_fundamental.md) · [registration_to_flow2d](registration_to_flow2d.md)

## 同カテゴリ(`intensityreg`)

[register_ecc](register_ecc.md) · [register_ffd](register_ffd.md) · [registration_to_flow2d](registration_to_flow2d.md) · [register_accuracy_map](register_accuracy_map.md) · [register_capture_range](register_capture_range.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
