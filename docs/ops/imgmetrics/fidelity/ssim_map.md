---
op: ssim_map
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: image2d
examples: [image_quality_metrics]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.11  # fullseye lib version this note was generated for
---

# ssim_map — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.ssim_map(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03, channel_axis=None, crop_border=True)` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.ssim_map(a, b, data_range=None, win_size=11, sigma=1.5, K1=0.01, K2=0.03, channel_axis=None, crop_border=True)`、台帳から引くなら `opsimgmetrics.get("ssim_map")`)

## 使い方

SSIM の**マップ**(平均を取る前)。どこが似ていないかを絵で見るため。

``channel_axis`` を指定するとチャネルごとに計算し、その平均マップを返す。

計算: 局所平均 ``mu`` と分散・共分散を、幅 ``win_size`` に切った σ = ``sigma`` の
ガウシアン窓(境界は鏡像)で取り、画素ごとに
``((2 mu_a mu_b + C1)(2 s_ab + C2)) / ((mu_a^2 + mu_b^2 + C1)(s_a + s_b + C2))``。
``C1 = (K1 dr)^2``、``C2 = (K2 dr)^2``、``dr`` は ``data_range``。分散は母分散
(``n/(n-1)`` 補正なし)。この平均が ``ssim``。

- ``data_range``: 整数 dtype は自動、float は ``[0, 1]`` のときだけ 1.0 と推定し、
  それ以外は明示必須(``data_range_of`` の契約、外れると ``MetricContractError``)。
- ``win_size``: 3 以上の奇数。各空間軸はこれ以上の長さが必要。
- ``crop_border=True``(既定)は窓半径 ``(win_size-1)//2`` ぶんの縁を落とすので、
  返り値は ``(H - 2p, W - 2p)``。落とした後に何も残らない小画像は例外。
  ``False`` なら入力と同形だが、縁は鏡像埋めの影響を含む。
- 返り値: float64 マップ。1 が局所的に一致、負にもなりうる(構造が反転)。
- 失敗: 形の不一致 / 空 / 非有限 / ``sigma <= 0`` / 偶数か 3 未満の ``win_size``。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [image_entropy](../information/image_entropy.md) · [joint_entropy](../information/joint_entropy.md) · [mutual_information](../information/mutual_information.md)

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [rmse](rmse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
