---
op: delta_e_2000
dim: imgmetrics
category: colordiff
in: lab × lab
out: image2d
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# delta_e_2000 — IMGMETRICS `colordiff` op

- **データ種**: `lab × lab` → `image2d`
- **呼び出し**: `import imgmetrics; imgmetrics.delta_e_2000(lab1, lab2, kL=1.0, kC=1.0, kH=1.0)` (または `opsimgmetrics.get("delta_e_2000")`)

## 使い方

CIEDE2000 色差(CIE 142-2001)。

実装が踏み外しやすい 3 か所 ―― **色相角の平均**(0/360 をまたぐ扱い)、
**275° の回転項**、**彩度ゼロ近傍**(``atan2(0, 0)`` の扱い)―― は
Sharma, Wu & Dalal (2005) の 34 組の検証対で固定してある
(``CIEDE2000_TEST_PAIRS`` / ``tests/test_imgmetrics.py``)。

Parameters
----------
lab1, lab2 : array_like
    最後の軸が ``(L*, a*, b*)`` の配列。ブロードキャストされる。
kL, kC, kH : float
    観察条件のパラメトリック係数。既定は基準条件の 1。

Returns
-------
ndarray
    ΔE00(最後の軸が落ちた形)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](../fidelity/mse.md) · [rmse](../fidelity/rmse.md) · [psnr](../fidelity/psnr.md) · [ssim](../fidelity/ssim.md) · [ms_ssim](../fidelity/ms_ssim.md) · [ssim_map](../fidelity/ssim_map.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md)

## 同カテゴリ(`colordiff`)

[delta_e_76](delta_e_76.md) · [delta_e_map](delta_e_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
