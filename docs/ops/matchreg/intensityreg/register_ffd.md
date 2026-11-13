---
op: register_ffd
dim: matchreg
category: intensityreg
in: image2d × image2d
out: table
gpu: なし
examples: [poc_sheet_deformation_ffd]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# register_ffd — MATCHREG `intensityreg` op

- **データ種**: `image2d × image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.register_ffd(fixed, moving, grid_spacing=8, levels=None, max_iter=150, reg_weight=1.0, normalize=True, init_flow2d=None, membrane_weight=0.0, min_coarse_spacing=2.0)` (実装を直接呼ぶなら `import intensityreg; intensityreg.register_ffd(fixed, moving, grid_spacing=8, levels=None, max_iter=150, reg_weight=1.0, normalize=True, init_flow2d=None, membrane_weight=0.0, min_coarse_spacing=2.0)`、台帳から引くなら `opsmatchreg.get("register_ffd")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3 次 B-spline の自由変形(FFD)で moving を fixed へ非剛体に合わせる。→ table(``kind="registration"``)。

変形を ``grid_spacing`` px 間隔の制御格子の係数 ``C`` で表し(Rueckert et al. 1999)、場は分離可能な
行列積 ``w = By C Bxᵀ``(``By``・``Bx`` は 3 次 B-spline の基底行列)。目的は
``mean((M(p + w) - F)²) + reg_weight · 曲げの罰``(制御格子の 2 階差分の 2 乗和、``∂²/∂y²``・
``∂²/∂x²``・``2 ∂²/∂x∂y``)、勾配は ``Byᵀ (2 r ∇M / N) Bx`` の解析式。最適化は numpy の L-BFGS を
粗から細のピラミッドで(段を上がるたびに場を 2 倍して細かい基底へ最小二乗で写す)。

demons(:func:`deformreg.demons_register`)との違い: demons は画素ごとの場をガウスでならす
(自由度 2HW)、FFD は制御格子の自由度 ``2 · ny · nx`` しか持たず、格子より細かい変形は表せない
代わりに、模様の無い所でも場が格子の補間で埋まる。どちらが良いかは被写体次第で、
:func:`register_accuracy_map` が同じ真値で両方を測れる。

Args:
    fixed: 基準の 2-D 画像。
    moving: 合わせる 2-D 画像(fixed と同じ形)。
    grid_spacing: 制御点の間隔 [px] (全解像で)。
    levels: ピラミッドの段数。``None`` なら最も粗い段が 16 px 以上になる範囲で最大 3 段。
    max_iter: 段ごとの L-BFGS の反復の上限。
    reg_weight: 曲げの罰の重み(0 で無し)。罰は場の 2 階微分 [1/px] の 2 乗の制御点平均なので、
        格子間隔を変えても効きが変わらない。
    normalize: 2 枚とも平均 0・分散 1 にしてから比べる(明るさのアフィンな違いを消す。SSD のまま)。
    init_flow2d: 初期の場(``(2,H,W)``、出力と同じ向き)。``None`` なら 0。
    membrane_weight: 1 階微分の 2 乗(膜のエネルギー)の重み(既定 0 = Rueckert 1999 どおり曲げだけ)。
        ★曲げの罰は一様な傾き(伸び・剪断)を罰しないので、**模様の無い所では場が真の振幅の数倍まで
        暴れうる**(``examples/poc_sheet_deformation_ffd.py`` の 6b 節: 余白で最大 34 px、真値 1.5 px)。
        0.1 でそれが 3.6 px に収まる一方、模様のある所の本物の傾きも罰するので、滑らかな大きな場では
        精度が落ちる(``tests/test_intensityreg.py``)。両立しないので既定は 0 のまま。
    min_coarse_spacing: 粗い段での制御点の間隔の下限 [その段の px]。

Returns:
    dict(``kind="registration"``, ``method="ffd"``)。``warp=None``、``flow2d`` (2,H,W) の ``(dy, dx)``、
    ``metric_name="rms_residual"``(正規化後の残差の rms、罰を含まない)、``grid_shape``(制御格子)、
    ``grid_spacing``。他の鍵は :func:`register_ecc` と同じ。

限界: 微分同相(折り返し無し)は保証しない。模様の無い所・1 方向にしか模様の無い所(縦縞では縦の成分)の
場は罰と補間が決めた値で、データの裏付けは無い —— :func:`register_accuracy_map` の ``by_texture`` で見える。

Raises:
    ValueError: 画像が不正 / 形が違う / 引数が値域外 / ``init_flow2d`` の形が違うか非有限。

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

[register_ecc](register_ecc.md) · [register_mi](register_mi.md) · [registration_to_flow2d](registration_to_flow2d.md) · [register_accuracy_map](register_accuracy_map.md) · [register_capture_range](register_capture_range.md)

---
*Provenance: intensityreg.py — MATCHREG operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
