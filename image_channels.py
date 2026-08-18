"""マルチチャネル画像の合成/分解/タイル(HALCON "Image" chapter の genuine 実装, numpy).

単一画像 = 2D float64。マルチチャネル画像 = (H, W, C) float64。
各関数は実 HALCON operator の機能を本物の配列操作で実装する。
halcon_facade_map.json 経由でカバレッジ計上。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


def compose_channels(*channels) -> np.ndarray:
    """複数の 2D チャネルを (H,W,C) の多チャネル画像へ合成(compose2..7)。"""
    return np.stack([_img(c) for c in channels], axis=-1)


def compose2(c1, c2): return compose_channels(c1, c2)
def compose3(c1, c2, c3): return compose_channels(c1, c2, c3)
def compose4(c1, c2, c3, c4): return compose_channels(c1, c2, c3, c4)
def compose5(c1, c2, c3, c4, c5): return compose_channels(c1, c2, c3, c4, c5)
def compose6(*c): return compose_channels(*c)
def compose7(*c): return compose_channels(*c)


def decompose_channels(image):
    """多チャネル画像 (H,W,C) を 2D チャネルのリストへ分解(decompose2..7)。"""
    im = _img(image)
    if im.ndim == 2:
        return [im]
    return [im[..., k] for k in range(im.shape[-1])]


def decompose2(image): return decompose_channels(image)
def decompose3(image): return decompose_channels(image)
def decompose4(image): return decompose_channels(image)
def decompose5(image): return decompose_channels(image)
def decompose6(image): return decompose_channels(image)
def decompose7(image): return decompose_channels(image)


def channels_to_image(channels) -> np.ndarray:
    """2D チャネルのリスト/列を多チャネル画像へ(channels_to_image)。"""
    return np.stack([_img(c) for c in channels], axis=-1)


def image_to_channels(image):
    """多チャネル画像を個々のチャネルへ分ける(image_to_channels)。"""
    return decompose_channels(image)


def add_channels(region_or_gray, image):
    """gray 画像を base 画像へチャネルとして追加(add_channels)。"""
    base = _img(region_or_gray)
    im = _img(image)
    base3 = base[..., None] if base.ndim == 2 else base
    im3 = im[..., None] if im.ndim == 2 else im
    return np.concatenate([base3, im3], axis=-1)


def append_channel(multichannel, image) -> np.ndarray:
    """多チャネル画像に 1 チャネルを追記(append_channel)。"""
    mc = _img(multichannel)
    mc = mc[..., None] if mc.ndim == 2 else mc
    return np.concatenate([mc, _img(image)[..., None]], axis=-1)


def interleave_channels(image, order=None) -> np.ndarray:
    """チャネルを画素インタリーブ配置の 1 本の配列へ(interleave_channels)。"""
    im = _img(image)
    if im.ndim == 2:
        return im.ravel()
    if order is not None:
        im = im[..., list(order)]
    return im.reshape(-1)


def tile_channels(image, num_columns=1, mode="horizontal") -> np.ndarray:
    """多チャネルを 1 枚のグレー画像へタイル配置(tile_channels)。"""
    ch = decompose_channels(image)
    n = len(ch)
    ncol = max(1, int(num_columns))
    nrow = int(np.ceil(n / ncol))
    h, w = ch[0].shape
    canvas = np.zeros((nrow * h, ncol * w))
    for k, c in enumerate(ch):
        r, cc = divmod(k, ncol)
        canvas[r * h:(r + 1) * h, cc * w:(cc + 1) * w] = c
    return canvas


def tile_images(images, num_columns=1) -> np.ndarray:
    """同サイズ画像群をグリッドにタイル(tile_images)。"""
    return tile_channels(np.stack([_img(i) for i in images], axis=-1), num_columns)


def tile_images_offset(images, offsets, out_shape) -> np.ndarray:
    """各画像を offset (row,col) に貼り付けて合成(tile_images_offset)。"""
    H, W = out_shape
    canvas = np.zeros((int(H), int(W)))
    for im, (r0, c0) in zip(images, offsets):
        im = _img(im)
        h, w = im.shape
        r0, c0 = int(r0), int(c0)
        r1, c1 = min(r0 + h, H), min(c0 + w, W)
        canvas[r0:r1, c0:c1] = im[:r1 - r0, :c1 - c0]
    return canvas
