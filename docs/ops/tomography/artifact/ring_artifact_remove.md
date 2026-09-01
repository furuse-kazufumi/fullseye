---
op: ring_artifact_remove
dim: tomography
category: artifact
in: sinogram
out: sinogram
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# ring_artifact_remove — TOMOGRAPHY `artifact` op

- **データ種**: `sinogram` → `sinogram`
- **呼び出し**: `import tomography; tomography.ring_artifact_remove(sinogram, window=5, mode='median')` (または `opstomography.get("ring_artifact_remove")`)

## 使い方

Remove per-detector-bin offsets by flattening the angle-averaged profile.

The mean of a sinogram column over all angles is a smooth function of the
detector position for any object that stays inside the field of view — it is
essentially the object's mass seen from every side. A gain error adds a
*constant* to one column, so it appears in that mean as a spike on a smooth
curve. Smoothing the mean profile and subtracting the difference removes the
spike and leaves the object.

Measured on the Shepp-Logan phantom scaled to a peak line integral of 1.18
(i.e. CT-realistic, see the note below) with ``gain_sigma=0.02``: the
reconstruction's normalised RMS error against the truth goes 0.0250 (clean)
-> 0.0643 (with rings) -> **0.0358** (removed at the default window), so
**72 %** of the damage is undone.

The window is the whole argument, and it was chosen by measurement rather
than by taste. Removed fraction, against the damage the same call does to an
already-clean sinogram:

    window   median: undone / damage    mean: undone / damage
       3       61.0 % / +0.0000           70.4 % / +0.0004
       5       72.3 % / +0.0002           82.6 % / +0.0019
       7       74.3 % / +0.0017           82.4 % / +0.0042
      11       73.6 % / +0.0025           74.0 % / +0.0091
      31       73.3 % / +0.0043           37.4 % / +0.0244
      61       58.2 % / +0.0109            9.0 % / +0.0356

The default is ``window=5, mode="median"`` because it is the setting that
removes most of the rings while doing almost nothing to a sinogram that did
not need it — and *that* is the property that matters, because this operator
will be run on scans whose rings nobody has measured. ``mean`` at the same
window removes 10 points more and costs 10x the collateral damage; wide
windows are worse at both.

Two failure modes are stated rather than hidden. This **cannot** separate a
real object feature that is thin in the detector direction and present at
every angle — the axis of rotation itself is the extreme case — from a gain
error. And *gain_sigma is in line-integral units*, so how much a given gain
error matters depends entirely on how large the line integrals are: on the
same phantom left in raw pixel units (peak line integral 70.9 rather than
1.18) the identical 2 % gain error changes the reconstruction's error by less
than 0.0001 and this operator has nothing to do. That is not a bug in either
place — it is what "2 % of the signal" means when the signal is 60x larger.

:param sinogram: ``(n_angles, n_detectors)``.
:param window: smoothing width in detector bins, an **odd** int ``3 .. n_det``.
:param mode: ``"median"`` (robust, the default) or ``"mean"``.
:returns: ``(n_angles, n_detectors)`` float64 sinogram.
:raises ValueError: on an even or out-of-range window, or an unknown mode.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`sinogram` を入力に取れる)

[backproject_sinogram](../reconstruct/backproject_sinogram.md) · [filtered_backprojection](../reconstruct/filtered_backprojection.md) · [sart_reconstruct](../reconstruct/sart_reconstruct.md) · [beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [metal_trace_interpolate](metal_trace_interpolate.md) · [sinogram_center_of_rotation](../geometry/sinogram_center_of_rotation.md)

## 同カテゴリ(`artifact`)

[beam_hardening_apply](beam_hardening_apply.md) · [beam_hardening_correct](beam_hardening_correct.md) · [ring_artifact_apply](ring_artifact_apply.md) · [metal_trace_interpolate](metal_trace_interpolate.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
