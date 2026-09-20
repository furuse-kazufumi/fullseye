---
op: tb_fly_hex_quantize
dim: 2d
category: typed
in: signal
out: signal
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.1  # fullseye lib version this note was generated for
---

# tb_fly_hex_quantize — 2D `typed` op

- **データ種**: `signal` → `signal`
- **呼び出し**: `fullseye.apply(img, "tb_fly_hex_quantize", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)

## 使い方

Quantize an ommatidial signal the way the eye does: log-compress, then n bits per ommatidium.

    A compound eye is a quantizer by construction: ~800 ommatidia per eye at 4.6 deg spacing,
    photoreceptors that log-compress intensity and adapt to the mean, and lamina cells (L1/L2)
    that split the deviation into ON and OFF channels. This op reproduces that budget so a
    downstream model (reservoir, retinotopy test) can be asked how many bits it really needs.

    Parameters
    ----------
    signal : (n,) float
        Per-ommatidium intensities >= 0 (``fly_hex_resample`` output).
    bits : int
        1..8 levels = 2**bits (``mode="onoff"`` ignores it: the output is the signed pair below).
    mode : str
        ``"log"``: log1p-compress relative to the mean, shift the darkest ommatidium to 0, then
        uniform levels over the compressed range; ``"linear"``: uniform levels over [0, max]; ``"onoff"``: deviation from the mean
        relative to ``contrast`` clipped to [-1, 1] and returned as ``2 * n`` values ``[ON..., OFF...]``
        (ON = positive part, OFF = negative part), each >= 0.
    contrast : float
        Michelson-style contrast that saturates the ON/OFF channels (``mode="onoff"`` only).

    Returns
    -------
    (n,) float in [0, 1] (levels / (2**bits - 1)); for ``"onoff"`` (2n,) in [0, 1].

    Notes
    -----
    Non-finite or negative inputs are refused. A constant signal quantizes to all-zeros
    (``"log"`` / ``"onoff"``) — there is no contrast to encode.

Typed bridge of the flyvision op ``fly_hex_quantize`` into the 2-D evolution registry: the same implementation, called under the ``op(v, a, b)`` convention. ``a`` drives ``bits`` (default 3) and ``b`` drives ``contrast`` (default 0.2).

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

次の例は元の台帳 op `fly_hex_quantize` を呼ぶもの。この橋渡し op は同じ実装を `fn(v, a, b)` 規約に合わせただけなので、挙動はそのまま当てはまる(呼び出し形だけ違う)。
- [poc_eye_to_brain](../../../../examples/poc_eye_to_brain.py) — `py -3.11 examples/poc_eye_to_brain.py`

## 型が繋がる次の op(`signal` を入力に取れる)

[identity](../misc/identity.md) · [tb_create_funct_1d_array](tb_create_funct_1d_array.md) · [tb_smooth_funct_1d_gauss](tb_smooth_funct_1d_gauss.md) · [tb_smooth_funct_1d_mean](tb_smooth_funct_1d_mean.md) · [tb_derivate_funct_1d](tb_derivate_funct_1d.md) · [tb_integrate_funct_1d](tb_integrate_funct_1d.md) · [tb_zero_crossings_funct_1d](tb_zero_crossings_funct_1d.md) · [tb_abs_funct_1d](tb_abs_funct_1d.md)

## 同カテゴリ(`typed`)

[tb_points_to_voxel](tb_points_to_voxel.md) · [tb_estimate_point_normals](tb_estimate_point_normals.md) · [tb_iss_keypoints](tb_iss_keypoints.md) · [tb_project_points](tb_project_points.md) · [tb_render_point_depth](tb_render_point_depth.md) · [tb_statistical_outlier_removal](tb_statistical_outlier_removal.md) · [tb_radius_outlier_removal](tb_radius_outlier_removal.md) · [tb_voxel_grid_downsample](tb_voxel_grid_downsample.md)

---
*Provenance: ops.py — 2D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
