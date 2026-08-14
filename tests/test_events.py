"""Ground-truth tests for events.py — frame->event (neuromorphic) representations.

Each test asserts the op implements the event-camera model its name claims:
ON/OFF polarity by log-intensity change, multi-event counts, the accumulated
event image, event rate/activity, the Surface of Active Events, and contrast
maximisation recovering a known constant global velocity from a short clip.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import events as E


def _edges(n=48):
    img = np.full((n, n), 0.3)
    img[n // 3:2 * n // 3, n // 3:2 * n // 3] = 0.8   # a bright square
    return img


def test_simulate_events_polarity_matches_brightness_change():
    prev = np.full((16, 16), 0.4)
    nxt = prev.copy()
    nxt[4:8, 4:8] = 0.9          # brightening -> ON (+1)
    nxt[10:14, 10:14] = 0.05     # darkening  -> OFF (-1)
    e = E.simulate_events(prev, nxt, thr=0.1)
    assert set(np.unique(e)).issubset({-1.0, 0.0, 1.0})
    assert e[5, 5] == 1.0
    assert e[12, 12] == -1.0
    assert e[0, 0] == 0.0        # static region -> no event


def test_static_frames_produce_no_events():
    f = _edges()
    assert E.event_rate(f, f.copy(), thr=0.1) == 0.0
    assert np.all(E.simulate_events(f, f.copy(), thr=0.1) == 0.0)


def test_event_count_is_signed_and_grows_with_the_jump():
    prev = np.full((8, 8), 0.2)
    small = np.full((8, 8), 0.3)
    big = np.full((8, 8), 0.95)
    cs = np.abs(E.event_count(prev, small, thr=0.05)).max()
    cb = np.abs(E.event_count(prev, big, thr=0.05)).max()
    assert cb > cs                                   # bigger contrast -> more events
    assert E.event_count(prev, big, thr=0.05).min() >= 0   # brightening -> ON only


def test_event_image_is_normalised_and_marks_the_moving_edge():
    prev = _edges()
    nxt = E.warp_frame(prev, 0, 3)                   # move the square right by 3 px
    iwe = E.event_image(prev, nxt, thr=0.1)
    assert iwe.shape == prev.shape
    assert iwe.min() >= 0.0 and iwe.max() <= 1.0
    assert iwe.max() > 0.0                           # something fired
    # activity concentrates at the vertical edges, not the flat interior
    assert iwe[:, prev.shape[1] // 2].mean() < iwe.max()


def test_event_rate_map_is_bounded_and_higher_where_motion_is():
    prev = _edges()
    nxt = E.warp_frame(prev, 2, 0)
    m = E.event_rate_map(prev, nxt, thr=0.1)
    assert m.min() >= 0.0 and m.max() <= 1.0
    assert m.max() > m.mean()


def test_time_surface_decays_with_event_age():
    n = 24
    base = np.full((n, n), 0.3)
    frames = [base.copy() for _ in range(4)]
    frames[1][2:6, 2:6] = 0.9        # an event early (interval 0->1)
    frames[2] = frames[1].copy()
    frames[3] = frames[1].copy()
    frames[3][15:19, 15:19] = 0.9    # an event late (interval 2->3)
    sae = E.time_surface(np.stack(frames), tau=1.0, thr=0.1)
    assert sae.min() >= 0.0 and sae.max() <= 1.0
    recent = sae[16, 16]             # fired in the last interval
    old = sae[3, 3]                  # fired in the first interval
    never = sae[10, 10]
    assert recent > old > never
    assert never == 0.0


def test_time_surface_requires_a_stack():
    with pytest.raises(ValueError):
        E.time_surface(np.zeros((8, 8)))            # 2-D, not a stack
    with pytest.raises(ValueError):
        E.time_surface(np.zeros((1, 8, 8)))         # T<2


def test_warp_frame_shifts_content():
    f = _edges()
    s = E.warp_frame(f, 0, 4)
    # the bright square's left edge moved right by ~4 px
    col_before = f.mean(axis=0)
    col_after = s.mean(axis=0)
    assert np.argmax(col_after > 0.4) > np.argmax(col_before > 0.4)


@pytest.mark.parametrize("vy0,vx0", [(0, 2), (1, 0), (1, -1), (2, 1)])
def test_contrast_maximization_recovers_known_velocity(vy0, vx0):
    n = 56
    base = np.full((n, n), 0.25)
    base[10:40, 10:40] = 0.85
    base += 0.15 * np.sin(np.linspace(0, 8, n))[None, :]   # texture so edges move
    base = np.clip(base, 0, 1)
    T = 5
    frames = [ndimage.shift(base, (t * vy0, t * vx0), order=1, mode="reflect") for t in range(T)]
    out = E.contrast_maximization(np.stack(frames), max_v=4, thr=0.08)
    assert (out["vy"], out["vx"]) == (float(vy0), float(vx0))
    assert out["iwe"].shape == (n, n) and out["iwe"].max() <= 1.0


def test_contrast_maximization_requires_a_stack():
    with pytest.raises(ValueError):
        E.contrast_maximization(np.zeros((8, 8)))


def test_all_finite_and_fail_soft_on_degenerate():
    for shp in [(1, 1), (2, 3), (17, 9)]:
        a = np.clip(np.random.default_rng(0).random(shp), 0, 1)
        b = np.clip(np.random.default_rng(1).random(shp), 0, 1)
        for fn in (E.simulate_events, E.event_count, E.event_image, E.event_rate_map):
            out = np.asarray(fn(a, b), np.float64)
            assert np.isfinite(out).all()
        assert np.isfinite(E.event_rate(a, b))
