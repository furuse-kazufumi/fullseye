---
op: tb_iqft2
dim: 2d
category: typed
in: qimage
out: qimage
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.8  # fullseye lib version this note was generated for
---

# tb_iqft2 — 2D `typed` op

- **データ種**: `qimage` → `qimage`
- **呼び出し**: `fullseye.apply(img, "tb_iqft2", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Inverse quaternion Fourier transform of a **centred** spectrum. → (H, W, 4).

    The exact inverse of :func:`qft2` **for the same side and the same mu**:
    measured round-trip error ``2.22e-15`` for both sides on a standard-normal
    ``(32, 32, 4)`` field. The kernel is ``exp(+mu * 2*pi*(...))`` applied on the
    side named, and the ``1/(H*W)`` normalisation is carried here, as in
    ``numpy.fft.ifft2``.

    **Using the wrong side does not raise.** ``iqft2(qft2(q, "left"), "right")``
    returns a finite, plausible quaternion image that is simply not ``q``:
    measured ``max|err| = 1.113`` on a random colour image whose own range is
    ``0.9994`` (another seed: 1.063 against 1.0), and — the dangerous case — only ``0.054`` against a range of
    ``1.076`` on a grey-axis-dominated one, which is small enough to survive a
    look at the picture. The ``side`` argument is required at both ends for
    exactly this reason, and the two calls must agree: nothing in the data
    records which transform produced it, so nothing downstream can catch the
    mismatch for you.

    **Raises** ``ValueError``: *spectrum* is not a valid ``(H, W, 4)`` field;
    *side* is not ``'left'`` / ``'right'``; *mu* is not a finite non-zero
    3-vector.

Typed bridge of the quat op ``iqft2`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. This op has no tunable parameter; ``a`` and ``b`` are unused.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`qimage` を入力に取れる)

[identity](../misc/identity.md) · [tb_quaternion_to_rgb](tb_quaternion_to_rgb.md) · [tb_quat_norm](tb_quat_norm.md) · [tb_quat_conjugate_image](tb_quat_conjugate_image.md) · [tb_quat_normalize_image](tb_quat_normalize_image.md) · [tb_monogenic_amplitude](tb_monogenic_amplitude.md) · [tb_monogenic_phase](tb_monogenic_phase.md) · [tb_monogenic_orientation](tb_monogenic_orientation.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_angle_3points](tb_angle_3points.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
