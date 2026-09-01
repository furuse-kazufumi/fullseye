---
op: delta_e_76
dim: imgmetrics
category: colordiff
in: lab × lab
out: image2d
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# delta_e_76 — IMGMETRICS `colordiff` op

- **データ種**: `lab × lab` → `image2d`
- **呼び出し**: `import imgmetrics; imgmetrics.delta_e_76(lab1, lab2)` (または `opsimgmetrics.get("delta_e_76")`)

## 使い方

CIE76 色差 ―― Lab 空間のユークリッド距離。

単純だが**知覚と合わない**(特に彩度の高い青)ので、比較の基準としてのみ
置いてある。実用は :func:`delta_e_2000`。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](../fidelity/mse.md) · [rmse](../fidelity/rmse.md) · [psnr](../fidelity/psnr.md) · [ssim](../fidelity/ssim.md) · [ms_ssim](../fidelity/ms_ssim.md) · [ssim_map](../fidelity/ssim_map.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md)

## 同カテゴリ(`colordiff`)

[delta_e_2000](delta_e_2000.md) · [delta_e_map](delta_e_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
