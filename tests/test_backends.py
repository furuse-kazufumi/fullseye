"""Detectability tests for the skimage/OpenCV wrapper safety net.

``backends._safe`` swallows every wrapper exception and hands the failure to
``backend_safe.sanitize``. For ``out_sort="image"`` the fallback is the clipped
INPUT, so a wrapper broken by skimage/cv2 API drift is indistinguishable from a
working identity op — evolution, difftest and coverage all see a live op that
does nothing. The 2026-08-16 audit accepted the runtime robustness but required
the degradation to be DETECTABLE; these tests pin both halves.
"""
from __future__ import annotations

import numpy as np
import pytest

import backends


def _boom(v, a, b):
    raise RuntimeError("skimage API drift")


def _img():
    return np.linspace(0.0, 1.0, 16).reshape(4, 4)


# --------------------------------------------------------------------------- #
# M4 — a dead op must be detectable                                           #
# --------------------------------------------------------------------------- #
def test_default_mode_still_degrades_to_the_input():
    """Backward compatibility: the non-strict path is unchanged (identity for image)."""
    v = _img()
    assert np.array_equal(backends._safe(_boom, "image")(v, 0.5, 0.5), v)


def test_strict_mode_reraises_instead_of_masking_a_dead_op():
    """The escape hatch a verifier needs: strict mode surfaces the real exception."""
    v = _img()
    with pytest.raises(RuntimeError, match="skimage API drift"):
        with backends.strict_mode():
            backends._safe(_boom, "image")(v, 0.5, 0.5)
    assert backends.is_strict() is False          # scope restored even after the raise


def test_strict_mode_does_not_disturb_a_healthy_op():
    v = _img()
    w = backends._safe(lambda x, a, b: x * 0.5, "image")
    with backends.strict_mode():
        assert np.allclose(w(v, 0.5, 0.5), v * 0.5)


def test_swallowed_exception_is_recorded():
    """Without strict mode the failure is still visible after the fact."""
    backends.clear_errors()
    assert backends.last_error() is None
    backends._safe(_boom, "image")(_img(), 0.5, 0.5)
    err = backends.last_error()
    assert err is not None
    assert err["out_sort"] == "image"
    assert "skimage API drift" in err["error"]
    assert len(backends.swallowed_errors()) == 1
    backends.clear_errors()


def test_error_ring_is_bounded():
    """The recorder must not grow without bound during a long evolution run."""
    backends.clear_errors()
    w = backends._safe(_boom, "region")
    for _ in range(backends._ERR_MAX + 20):
        w(_img(), 0.5, 0.5)
    assert len(backends.swallowed_errors()) == backends._ERR_MAX
    backends.clear_errors()


def test_set_strict_returns_the_previous_value():
    prev = backends.set_strict(True)
    try:
        assert backends.is_strict() is True
    finally:
        backends.set_strict(prev)
    assert backends.is_strict() is prev
