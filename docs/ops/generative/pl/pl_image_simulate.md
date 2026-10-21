---
op: pl_image_simulate
dim: generative
category: pl
in: image2d
out: image2d
examples: [poc_si_wafer_pl_defect_visibility]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# pl_image_simulate — GENERATIVE `pl` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.pl_image_simulate(generation, sink=None, *, diffusion_length_px: 'float' = 8.0, optical_psf_px: 'float' = 0.0, noise_rel: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'` (実装を直接呼ぶなら `import pl; pl.pl_image_simulate(generation, sink=None, *, diffusion_length_px: 'float' = 8.0, optical_psf_px: 'float' = 0.0, noise_rel: 'float' = 0.0, seed: 'int' = 0) -> 'np.ndarray'`、台帳から引くなら `opsgenerative.get("pl_image_simulate")`)

## 使い方

励起の場と再結合の場から PL 像を作る(定常拡散方程式の厳密解 + 光学 PSF + 雑音)。

Parameters
----------
generation : array_like
    励起(生成)の場 ``g = G/G₀``(H×W、≥ 0)。一様 1 が「欠陥なしの地」。影の溝は
    ここを 0 にして作る(生成が欠けるだけで再結合は増えない)。
sink : array_like or None
    追加の再結合率の場 ``k = στ``(H×W、≥ 0、無次元)。``None`` は 0。沈みの溝・転位・
    粒界はここを正にして作る。再結合速度 S[長さ/時間]の線なら ``k·w = S·L²/D``(画素
    単位)。
diffusion_length_px : float
    拡散長 ``L = √(Dτ)``[px]。
optical_psf_px : float
    光学系の PSF(ガウシアン σ[px])。0 で無効。拡散 PSF の**後**に掛かる。
noise_rel : float
    加法ガウス雑音の σ(欠陥なしの地 1 に対する相対値)。0 で決定論。
seed : int
    雑音の種。直接解に収まらない像(160,000 画素超)は共役勾配(相対残差 1e-10 固定)。

Returns
-------
numpy.ndarray
    ``(H, W)`` の float64。欠陥なし・一様励起なら厳密に 1。``u = Δn/(G₀τ)``。

Notes
-----
境界は流束 0(Neumann)。だから一様な励起は端まで厳密に一様で、溝の採点に境界の
暗化が混ざらない。方程式が線形なので ``generation`` の重ね合わせは像の重ね合わせ。

Examples
--------
>>> import numpy as np
>>> g = np.ones((1, 201)); g[0, 100] = 0.0            # 幅 1 px の影の溝
>>> u = pl_image_simulate(g, diffusion_length_px=10.0)
>>> rho = 1 + 0.5 / 100 - ((1 + 0.5 / 100) ** 2 - 1) ** 0.5
>>> abs(float(1 - u[0, 100]) - (1 - 2 * rho / (1 + rho))) < 1e-9   # 格子の閉形式
True
>>> round(float(pl_image_simulate(np.ones((8, 8)))[3, 3]), 12)  # 一様 → 1(解法の丸めまで)
1.0

## 詳しい使い方ガイド

- [generative_art ファミリ ガイド](../guides/generative_art.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_si_wafer_pl_defect_visibility](../../../../examples/poc_si_wafer_pl_defect_visibility.py) — `py -3.11 examples/poc_si_wafer_pl_defect_visibility.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[sem_render](../sem/sem_render.md) · [sem_image](../sem/sem_image.md) · [sem_charging_series](../sem/sem_charging_series.md)

## 同カテゴリ(`pl`)

[pl_diffusion_psf](pl_diffusion_psf.md) · [pl_groove_visibility](pl_groove_visibility.md)

---
*Provenance: pl.py — GENERATIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
