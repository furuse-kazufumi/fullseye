"""画素描画・複素/ベクトル場変換(HALCON "Image" chapter genuine, numpy).

領域/画像へのグレー値描画と、複素画像・ベクトル場のチャネル分離/合成。
image = 2D float64、region = bool 2D。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def paint_region(image, region, value=1.0):
    """領域を定数グレー値で塗る(paint_region)。"""
    out = _img(image).copy()
    out[np.asarray(region, bool)] = float(value)
    return out


def paint_gray(image, source, region=None):
    """source 画像のグレー値を(領域内で)image へ転写(paint_gray)。"""
    out = _img(image).copy(); src = _img(source)
    m = np.ones(out.shape, bool) if region is None else np.asarray(region, bool)
    out[m] = src[m]
    return out


def overpaint_gray(image, source, region=None):
    """paint_gray と同義で source を重ね描き(overpaint_gray)。"""
    return paint_gray(image, source, region)


def overpaint_region(image, region, value=1.0):
    """paint_region と同義で領域を重ね塗り(overpaint_region)。"""
    return paint_region(image, region, value)


def real_to_complex(image_real, image_imag):
    """実部/虚部画像を複素画像へ合成(real_to_complex)。"""
    return _img(image_real) + 1j * _img(image_imag)


def complex_to_real(image_complex):
    """複素画像を実部/虚部へ分解(complex_to_real)。"""
    z = np.asarray(image_complex, complex)
    return {"real": z.real.copy(), "imag": z.imag.copy(),
            "abs": np.abs(z), "phase": np.angle(z)}


def real_to_vector_field(image_row, image_col):
    """2 枚の実画像を (H,W,2) ベクトル場へ合成(real_to_vector_field)。"""
    return np.stack([_img(image_row), _img(image_col)], axis=-1)


def vector_field_to_real(vector_field):
    """ベクトル場 (H,W,2) を row/col 成分画像へ分解(vector_field_to_real)。"""
    vf = np.asarray(vector_field, float)
    return {"row": vf[..., 0].copy(), "col": vf[..., 1].copy()}


def gen_image_interleaved(interleaved, width, height, channels=3):
    """画素インタリーブ 1D 配列を (H,W,C) 画像へ復元(gen_image_interleaved)。"""
    a = np.asarray(interleaved, float)
    return a.reshape(int(height), int(width), int(channels))
