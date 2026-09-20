# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""eyebrain(複眼 → 脳)の門: 合成の代替で経路を全部通し、対応・刺激・波・絵の性質を固定する。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import eyebrain  # noqa: E402


@pytest.fixture(scope="module")
def eb(tmp_path_factory):
    """キャッシュが無いディレクトリを指して合成の代替を作る(手元の MaleCNS キャッシュに依存しない)。"""
    d = tmp_path_factory.mktemp("no_cache")
    return eyebrain.load(str(d))


def test_synthetic_surrogate_has_columns_and_maps_every_ommatidium(eb):
    assert eb.provenance.startswith("synthetic")
    assert eb.n == eb.W.shape[0] == eb.P.shape[0] == len(eb.node_col)
    assert len(eb.columns) == 300
    assert eb.ommatidium_to_column.shape == (len(eb.lattice["uv"]),)
    assert eb.ommatidium_to_column.min() >= 0 and eb.ommatidium_to_column.max() < len(eb.columns)
    assert eb.column_to_ommatidium.shape == (len(eb.columns),)
    # 視葉のノードは全部どれかの柱に、視葉外は −1
    eye = np.isfinite(eb.hexes[:, 0])
    assert (eb.node_col[eye] >= 0).all() and (eb.node_col[~eye] == -1).all()


def test_neighbourhood_is_hex_distance(eb):
    k = int(np.argmin(np.linalg.norm(eb.columns - eb.columns.mean(axis=0), axis=1)))
    assert len(eb.column_neighbourhood(k, 0)) == 1
    assert len(eb.column_neighbourhood(k, 1)) == 7          # 中央の柱 + 6 近傍
    assert len(eb.column_neighbourhood(k, 2)) == 19


def test_stimulus_for_column_hits_only_that_neighbourhood(eb):
    k = 10
    stim = eb.stimulus_for_column(k, radius=1, amp=2.0)
    near = set(eb.column_neighbourhood(k, 1).tolist())
    assert stim.shape == (eb.n,)
    assert set(np.unique(eb.node_col[stim > 0]).tolist()) <= near
    assert stim.max() == 2.0 and (stim[eb.node_col < 0] == 0).all()


def test_image_stimulus_follows_the_bar(eb):
    """縦縞を左右に動かすと、刺激される柱の重心が同じ向きに動く(像 → 個眼 → 柱 の向きが保たれる)。"""
    xs = []
    for lo in (20, 60, 100):
        img = np.zeros((128, 128)); img[:, lo:lo + 12] = 1.0
        sig = eb.eye_signal(img)
        assert sig.shape == (len(eb.lattice["uv"]),) and 0.0 <= sig.min() and sig.max() <= 1.0
        stim = eb.stimulus_from_signal(sig)
        assert (stim > 0).sum() > 0 and set(np.unique(eb.node_col[stim > 0]).tolist()) <= set(eb.ommatidium_to_column[sig > 0].tolist())
        xs.append(float(np.asarray(eb.lattice["az_rad"])[sig > 0.5].mean()))       # 点いた個眼の方位角
    assert xs[0] < xs[1] < xs[2]                                                  # 像の右 = 方位角の正


def test_large_and_colour_images_are_reduced_before_the_eye(eb):
    """512² や RGB の像も通る(fly_hex_resample の重み行列の上限に当たらないよう面積平均で縮める)。"""
    big = np.zeros((512, 512)); big[:, 200:260] = 1.0
    small = np.zeros((128, 128)); small[:, 50:65] = 1.0
    a, b = eb.eye_signal(big), eb.eye_signal(small)
    assert a.shape == b.shape and np.corrcoef(a, b)[0, 1] > 0.9
    rgb = np.dstack([big, big * 0.5, big * 0.2])
    assert np.allclose(eb.eye_signal(rgb), a)


def test_wave_response_peak_excludes_the_stimulus_and_colors_saturate_it(eb):
    stim = eb.stimulus_for_column(5, radius=1)
    X = eb.run_wave(stim, steps=12)
    assert X.shape == (12, eb.n) and np.isfinite(X).all()
    pk = eb.response_peak(X, stim)
    assert 0.0 < pk < np.abs(X).max()                      # 刺激ノードの方が強い
    cols = eb.frame_colors(X[3], stim, pk)
    assert cols.shape == (eb.n, 3) and cols.min() >= 0.0 and cols.max() <= 1.0
    assert np.allclose(cols[stim > 0], eyebrain.STIM_COLOR)
    # shuffle も同じ入口で回る
    Xs = eb.run_wave(stim, steps=12, shuffle=True)
    assert Xs.shape == X.shape and not np.allclose(Xs, X)
    assert eb.response_peak(np.zeros((3, eb.n)), stim) == 0.0


def test_eye_view_and_cursor_lookup_round_trip(eb):
    img = eb.eye_view(None, 200, highlight=eb.column_neighbourhood(3, 1))
    assert img.shape == (200, 200, 3) and img.min() >= 0.0 and img.max() <= 1.0
    xy = eb.lattice_xy(200)
    for o in (0, 17, len(xy) - 1):
        assert eb.ommatidium_at(xy[o, 0], xy[o, 1], 200) == o
        assert eb.column_at(xy[o, 0], xy[o, 1], 200) == int(eb.ommatidium_to_column[o])


def test_cache_npz_is_loaded_when_present(tmp_path):
    d = eyebrain.synthetic_eye_brain(n_eye_cols=40, k_per_col=2, n_hub=60, n_bg=200)
    np.savez_compressed(os.path.join(tmp_path, eyebrain.CACHE_FILE), **d)
    eb2 = eyebrain.load(str(tmp_path))
    assert not eb2.provenance.startswith("synthetic") and eb2.n == d["W"].shape[0]
