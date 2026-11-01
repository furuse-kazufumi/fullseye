---
op: pl_diffusion_psf
dim: generative
category: pl
in: 
out: image2d
gpu: なし
examples: [poc_si_wafer_pl_defect_visibility]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# pl_diffusion_psf — GENERATIVE `pl` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.pl_diffusion_psf(diffusion_length_px: 'float' = 8.0, size: 'int | None' = None) -> 'np.ndarray'` (実装を直接呼ぶなら `import pl; pl.pl_diffusion_psf(diffusion_length_px: 'float' = 8.0, size: 'int | None' = None) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("pl_diffusion_psf")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

キャリア拡散の PSF(2 次元のグリーン関数 K₀(r/L)/2πL²、総和 1)を画像で返す。

Parameters
----------
diffusion_length_px : float
    拡散長 ``L = √(Dτ)``[px]。
size : int or None
    核の一辺(奇数)。``None`` なら ``2·ceil(8L)+1``(8L で切ると質量の欠けは
    ``8·K₁(8) ≈ 1.2e-3``)。

Returns
-------
numpy.ndarray
    ``(size, size)`` の float64。中心画素は特異点 ``K₀(0) = ∞`` を**画素と同面積の円で
    平均した値** ``1 − (a/L)K₁(a/L)``(``a = 1/√π``)にして有限にしてある。

Notes
-----
総和は解析的に 1(``∫K₀(r/L)dA = 2πL²``)。半分の質量が入る半径は ``1.2572·L``。
これを ``generation`` に畳むと、欠陥の無い(``k = 0``)ときの ``pl_image_simulate`` と
同じ像になる(境界の扱いを除く)。

Examples
--------
>>> import numpy as np
>>> k = pl_diffusion_psf(6.0)
>>> k.shape
(97, 97)
>>> abs(float(k.sum()) - 1.0) < 5e-3            # 総量 = G·τ
True
>>> bool(k[48, 48] == k.max())                  # 中心が最大
True

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_si_wafer_pl_defect_visibility](../../../../examples/poc_si_wafer_pl_defect_visibility.py) — `py -3.11 examples/poc_si_wafer_pl_defect_visibility.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[sem_render](../sem/sem_render.md) · [sem_image](../sem/sem_image.md) · [sem_charging_series](../sem/sem_charging_series.md) · [pl_image_simulate](pl_image_simulate.md)

## 同カテゴリ(`pl`)

[pl_image_simulate](pl_image_simulate.md) · [pl_groove_visibility](pl_groove_visibility.md)

---
*Provenance: pl.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
