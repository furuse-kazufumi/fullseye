---
op: seg_membrane_response
dim: emproof
category: response
in: image2d
out: image2d
examples: [poc_em_second_opinion]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.2  # fullseye lib version this note was generated for
---

# seg_membrane_response — EMPROOF `response` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.seg_membrane_response(image, sigma: 'float' = 1.5, normalize: 'bool' = True) -> 'np.ndarray'` (実装を直接呼ぶなら `import emproof; emproof.seg_membrane_response(image, sigma: 'float' = 1.5, normalize: 'bool' = True) -> 'np.ndarray'`、台帳から引くなら `opsemproof.get("seg_membrane_response")`)

## 使い方

EM 断面の**暗い線**(細胞膜)の応答 [0, ∞)。ガウス平滑した Hessian の固有値 λ1 ≥ λ2 から
``max(λ1 − |λ2|, 0)`` (Steger の線検出の閉形式、σ² で尺度正規化)。

暗い線の上では横断方向の 2 階微分が大きく正(λ1)、線に沿う方向は 0(λ2)なので λ1 − |λ2| が立つ。
暗い**塊**(ミトコンドリア内部・シナプス小胞)は λ1 ≈ λ2 > 0 で打ち消し合って 0 に近い ―― 膜だけを
拾う。``normalize=True`` で断面の 99.5 percentile を 1 にする(``seg_*`` の閾値はその尺度で書く)。
scikit-image があるならレジストリの ``sk_frangi``(``fs.apply(img, "sk_frangi", a=0.5, b=0.5)``)も
同じ席に使える(試作はそちらで AUC を測った)。

Parameters
----------
image : (H, W) float
    生 EM(明るい = 細胞質、暗い = 膜)。範囲は問わない(勾配の比だけを見る)。
sigma : float
    平滑の σ [px]。膜の太さの半分程度(CREMI 4 nm/px なら 1.5〜2.5)。

## 詳しい使い方ガイド

- [emproof ファミリ ガイド](../guides/emproof.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_em_second_opinion](../../../../examples/poc_em_second_opinion.py) — `py -3.11 examples/poc_em_second_opinion.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[seg_membrane_chord_score](../suspect/seg_membrane_chord_score.md) · [seg_boundary_membrane_gap](../suspect/seg_boundary_membrane_gap.md)

## 同カテゴリ(`response`)

—

---
*Provenance: emproof.py — EMPROOF operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
