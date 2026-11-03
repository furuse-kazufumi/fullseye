---
op: register_ecc
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

# register_ecc — MATCHREG `intensityreg` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_ecc(fixed, moving, motion='affine', n_iter=200, eps=1e-06, warp_init=None, levels=1, smooth_sigma=1.1, nonpositive='raise', min_rho=0.0)` (実装を直接呼ぶなら `import intensityreg; intensityreg.register_ecc(fixed, moving, motion='affine', n_iter=200, eps=1e-06, warp_init=None, levels=1, smooth_sigma=1.1, nonpositive='raise', min_rho=0.0)`、台帳から引くなら `opsmatchreg.get("register_ecc")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

強度相関係数(ECC)を最大にするパラメトリックな変換で moving を fixed に合わせる。→ table(``kind="registration"``)。

Evangelidis & Psarakis(2008)の前向き加法の反復: 毎回 moving と勾配を今の変換で標本化し、
急降下画像 ``G = ∇I · ∂W/∂p``(平均を引く)とゼロ平均の 2 枚から、相関係数の 2 次近似の最大へ
``Δp`` を解く。相関係数は明るさの**アフィン**な違い(利得とずれ)に不変 —— 負の利得(白黒の反転)
や折り返しのある対応には効かない(分母が 0 以下になったら ``ValueError``。それには :func:`register_mi`)。

``motion``: ``"translation"``(2)/ ``"euclidean"``(3、回転 + 並進)/ ``"affine"``(6)/
``"homography"``(8)。``levels > 1`` で粗から細のピラミッド(OpenCV の ``findTransformECC`` には無い
追加。初期のずれの許容が広がる —— :func:`register_capture_range` で測れる)。

実測(96×96 の :func:`featmatch.synthetic_scene`、3 次スプラインで合成、``tests/test_intensityreg.py``
が固定): 並進 (2.5, -1.5) px の誤差 < 0.05 px、アフィンの 4 隅誤差 < 0.1 px、OpenCV 5.0 の
``findTransformECC`` と変換の差 < 0.05 px。

Args:
    fixed: 基準(テンプレート)の 2-D 画像。
    moving: 合わせる 2-D 画像(大きさは違ってよい)。
    motion: :data:`ECC_MOTIONS`。
    n_iter: 段ごとの反復の上限。
    eps: 相関係数の変化がこれ未満で収束。
    warp_init: 初期の変換(2×3 / 3×3、fixed → moving)。``None`` なら恒等。
    levels: ピラミッドの段数(1 = 原寸だけ、``None`` なら最も粗い段が 16 px 以上で最大 3 段)。
    smooth_sigma: 前処理のガウスの σ [px] (OpenCV の ``gaussFiltSize=5`` は σ ≈ 1.1)。0 で無し。
    nonpositive: 相関の 2 次近似の分母が 0 以下になったとき(初期値が遠い・撮像が違う)。``"raise"``
        (既定、OpenCV と同じく ``ValueError``)/ ``"step"``(相関を正へ戻す λ を選んで続ける。初期のずれの
        許容が広がることがある —— :func:`register_capture_range` で測れる)。
    min_rho: 収束した相関係数がこれ未満なら ``ValueError``(``"step"`` で白黒反転の組を「合った」と
        返さないための床)。

Returns:
    dict(``kind="registration"``, ``method="ecc"``)。``warp`` (3,3) / ``flow2d`` (2,H,W) の
    ``(dy, dx)`` / ``warped``(fixed の格子へ戻した moving、外側は 0)/ ``valid`` / ``valid_fraction`` /
    ``metric_name="ecc_rho"`` / ``metric``(最後の相関係数)/ ``iterations`` / ``converged`` /
    ``history`` / ``model`` / ``image_shape``。

Raises:
    ValueError: 画像が不正 / ``motion`` が違う / 引数が値域外 / 初期の変換が特異 / 反復が発散 /
        テンプレートが画像の外へ出た / 相関が負で ECC が定義できない(``nonpositive="raise"``)/
        収束した相関が ``min_rho`` 未満。

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

[register_mi](register_mi.md) · [register_ffd](register_ffd.md) · [registration_to_flow2d](registration_to_flow2d.md) · [register_accuracy_map](register_accuracy_map.md) · [register_capture_range](register_capture_range.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
