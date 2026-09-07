---
op: rmse
dim: imgmetrics
category: fidelity
in: image2d × image2d
out: scalar
examples: [grasp_pose, image_quality_metrics, physical_ai_perception, poc_ct_fidelity, poc_polarization_specular, poc_registration_basin, poc_structure_4d_deterioration]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# rmse — IMGMETRICS `fidelity` op

- **データ種**: `image2d × image2d` → `scalar`
- **呼び出し**: `import fullseye as fs; fs.ledger.rmse(a, b)` (実装を直接呼ぶなら `import imgmetrics; imgmetrics.rmse(a, b)`、台帳から引くなら `opsimgmetrics.get("rmse")`)

## 使い方

平均二乗誤差の平方根(画素値と同じ単位)。

式: ``sqrt(mse(a, b))``。検証と失敗条件は ``mse`` と同じ ―― 同じ形 / 空でない /
有限、を満たさなければ ``MetricContractError``。次元と dtype は問わない。

- 返り値: Python の ``float``。入力が ``[0, 1]`` の float なら値も ``[0, 1]``、uint8
  なら 0〜255 の尺度。「平均して何階調ずれているか」と読める。
- ``data_range`` に依らない生の量なので、尺度の違う 2 組の rmse を並べても
  比較にならない。正規化した指標が要るなら ``psnr`` か ``ssim``。
- 深度・CT・再投影など「画素値 = 物理量」の場面では、その物理単位そのものになる。

## 詳しい使い方ガイド

- [image_difference_metrics ファミリ ガイド](../guides/image_difference_metrics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [grasp_pose](../../../../examples/grasp_pose.py) — `py -3.11 examples/grasp_pose.py`
- [image_quality_metrics](../../../../examples/image_quality_metrics.py) — `py -3.11 examples/image_quality_metrics.py`
- [physical_ai_perception](../../../../examples/physical_ai_perception.py) — `py -3.11 examples/physical_ai_perception.py`
- [poc_ct_fidelity](../../../../examples/poc_ct_fidelity.py) — `py -3.11 examples/poc_ct_fidelity.py`
- [poc_polarization_specular](../../../../examples/poc_polarization_specular.py) — `py -3.11 examples/poc_polarization_specular.py`
- [poc_registration_basin](../../../../examples/poc_registration_basin.py) — `py -3.11 examples/poc_registration_basin.py`
- [poc_structure_4d_deterioration](../../../../examples/poc_structure_4d_deterioration.py) — `py -3.11 examples/poc_structure_4d_deterioration.py`

## 型が繋がる次の op(`scalar` を入力に取れる)

—

## 同カテゴリ(`fidelity`)

[mse](mse.md) · [psnr](psnr.md) · [ssim](ssim.md) · [ms_ssim](ms_ssim.md) · [ssim_map](ssim_map.md)

---
*Provenance: imgmetrics.py — IMGMETRICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
