---
op: iv_richardson_lucy_until
dim: converge
category: stopping
in: image2d
out: table
examples: [converge_tour]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# iv_richardson_lucy_until — CONVERGE `stopping` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.iv_richardson_lucy_until(image=None, psf_sigma=1.5, psf=None, noise='poisson', sigma=None, gain=1.0, tau=1.0, max_iter=2000, plateau_window=25, plateau_rtol=0.0001, keep_history=True, callback=None) -> 'dict'` (実装を直接呼ぶなら `import deconvstop; deconvstop.iv_richardson_lucy_until(image=None, psf_sigma=1.5, psf=None, noise='poisson', sigma=None, gain=1.0, tau=1.0, max_iter=2000, plateau_window=25, plateau_rtol=0.0001, keep_history=True, callback=None) -> 'dict'`、台帳から引くなら `opsconverge.get("iv_richardson_lucy_until")`)

## 使い方

Richardson-Lucy deconvolution stopped by the discrepancy principle (Poisson: Bertero 2010, tau = 1; Gaussian: Morozov); refuses data outside the model's range.

``image``: the blurred, noisy 2-D image. ``psf``: a 2-D PSF (normalised here), or a
Gaussian of ``psf_sigma`` px. The blur is periodic (FFT), so the RL step
x <- x * H^T(y / H x) keeps sum(H x) = sum(y) exactly (Lemma 3.2 of Benvenuto & Piana).

* ``noise="poisson"``: ``image * gain`` must be photon counts (non-negative integers within
  1e-6); stop at the first k with the Poisson discrepancy D_k <= ``tau`` (Benvenuto &
  Piana 2012 eq. (30); tau = 1 as proposed by Bertero et al. 2010).
* ``noise="gaussian"``: ``sigma`` (the noise standard deviation, in image units) is
  required; stop at the first k with ||H x_k - y||^2 / (N sigma^2) <= ``tau`` (Morozov,
  eq. (18)). The image must be non-negative (add the known offset first).

The iteration starts from the flat image of the data's mean (k = 0). Returns ``image``
(x_k in the input units), ``stopped``, ``status``, ``k_stop``, ``discrepancy_history``
(D_0, D_1, ...), ``mass_rel_error_max`` (Lemma 3.2), ``tau`` and ``noise``.

Not stopped -> ``image = None`` and ``status``:

* ``"outside_model_range"`` — the discrepancy levelled off above tau (relative decrease
  below ``plateau_rtol`` per iteration over ``plateau_window`` iterations): y is not in the
  range of the model, so the criterion can never be met (Benvenuto & Piana: the rule is a
  regularisation iff y is in H(C)). Typical causes: the assumed PSF is wider than the real
  blur, a background is missing, the noise level is wrong.
* ``"max_iter"`` — still decreasing when ``max_iter`` ran out.

The last iterate is under ``last_iterate`` (not an estimate). ``callback(k, x_k, D_k)``, if
given, is called after every iteration (x_k in the input units) — for plotting the run.

## 詳しい使い方ガイド

- [convergent_computation ファミリ ガイド](../guides/convergent_computation.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [converge_tour](../../../../examples/converge_tour.py) — `py -3.11 examples/converge_tour.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`stopping`)

—

---
*Provenance: deconvstop.py — CONVERGE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
