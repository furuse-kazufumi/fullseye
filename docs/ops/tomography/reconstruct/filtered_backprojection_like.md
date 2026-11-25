---
op: filtered_backprojection_like
dim: tomography
category: reconstruct
in: sinogram × image2d
out: image2d
gpu: なし
examples: [ct_reconstruction]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# filtered_backprojection_like — TOMOGRAPHY `reconstruct` op

- **データ種**: `sinogram × image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.filtered_backprojection_like(sinogram, reference, angles_deg=None, filter_name='ramp', cutoff=1.0, span_deg=None, device='cpu')` (実装を直接呼ぶなら `import tomography; tomography.filtered_backprojection_like(sinogram, reference, angles_deg=None, filter_name='ramp', cutoff=1.0, span_deg=None, device='cpu')`、台帳から引くなら `opstomography.get("filtered_backprojection_like")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

Run FBP on the square grid of ``reference`` / 参照画像と同じ正方格子で FBP を再構成する。

This is the explicit companion to :func:`filtered_backprojection`, whose
established default remains the detector-derived inscribed square. The
sinogram does not contain the source side length, so it cannot recover that
choice on its own. Pass the image that was given to :func:`radon_transform`::

    image = np.zeros((32, 32), np.float64)
    sinogram = radon_transform(image)
    reconstruction = filtered_backprojection_like(sinogram, image)
    assert reconstruction.shape == image.shape

``reference`` is a finite 2-D square image and supplies only the output grid;
its pixel values are deliberately not read. A rectangular reference is
refused rather than silently returning a square whose shape does not match:
2-D FBP currently reconstructs a square grid. This function cannot prove
that *reference* was the image that produced *sinogram*; keep that pairing in
the calling pipeline. All filter, angle, span, device and invalid-sinogram
contracts are those of :func:`filtered_backprojection`.

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [ct_reconstruction](../../../../examples/ct_reconstruction.py) — `py -3.11 examples/ct_reconstruction.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[radon_transform](../forward/radon_transform.md)

## 同カテゴリ(`reconstruct`)

[backproject_sinogram](backproject_sinogram.md) · [filtered_backprojection](filtered_backprojection.md) · [sart_reconstruct](sart_reconstruct.md)

---
*Provenance: tomography.py — TOMOGRAPHY operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
