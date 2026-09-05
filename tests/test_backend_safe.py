"""Contract tests for the shared backend safety net.

``backend_safe.sanitize`` is the single funnel every library-backed operator's
output passes through. Its docstring promises a *finite, sort-valid* result — the
tests below pin the SORT-VALID half (region range), which the 2026-08-16 audit
found was only guaranteed by convention, and re-pin the finiteness half so a
future edit cannot trade one for the other.
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

import backend_safe


# --------------------------------------------------------------------------- #
# M5 — the region {0,1} range contract                                        #
# --------------------------------------------------------------------------- #
def test_finite_out_of_range_float_region_is_coerced_to_01():
    """A finite float region outside {0,1} used to pass straight through.

    ``sanitize`` only checked ``np.all(np.isfinite(...))`` on the success path, so
    a soft mask / label map declared ``out_sort="region"`` was returned untouched
    and every downstream region consumer (blob_count, area_frac, region morphology)
    silently received a non-binary array.
    """
    soft = np.array([[0.3, 2.5], [-1.0, 0.9]])
    out = backend_safe.sanitize(soft, np.zeros((2, 2)), "region")
    assert out.dtype == np.float64
    assert set(np.unique(out).tolist()) <= {0.0, 1.0}
    # binarised at 0.5, the same rule api._coerce_input applies on the input side
    assert np.array_equal(out, np.array([[0.0, 1.0], [0.0, 1.0]]))


def test_integer_and_bool_regions_are_coerced_to_01_float():
    """int/bool region outputs skipped the float branch entirely and hit `return out`."""
    labels = np.array([[0, 2], [3, 0]], np.int32)
    out = backend_safe.sanitize(labels, np.zeros((2, 2)), "region")
    assert out.dtype == np.float64 and set(np.unique(out).tolist()) <= {0.0, 1.0}
    assert np.array_equal(out, np.array([[0.0, 1.0], [1.0, 0.0]]))

    mask = np.array([[True, False], [False, True]])
    out_b = backend_safe.sanitize(mask, np.zeros((2, 2)), "region")
    assert out_b.dtype == np.float64
    assert np.array_equal(out_b, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_valid_region_is_returned_untouched():
    """Every current region op astype()s from bool, so the guard must be an identity."""
    ok = np.array([[0.0, 1.0], [1.0, 0.0]])
    assert backend_safe.sanitize(ok, np.zeros((2, 2)), "region") is ok
    empty = np.zeros((0, 0))
    assert backend_safe.sanitize(empty, np.zeros((2, 2)), "region") is empty


def test_range_guard_does_not_touch_other_sorts():
    """Only `region` declares a {0,1} range — an image/feature must be left alone."""
    img = np.array([[0.3, 2.5], [-1.0, 0.9]])
    assert backend_safe.sanitize(img, np.zeros((2, 2)), "image") is img
    assert backend_safe.sanitize(img, np.zeros((2, 2)), None) is img
    assert backend_safe.sanitize(np.float64(7.5), np.zeros((2, 2)), "feature") == 7.5


def test_region01_leaves_non_array_output_alone():
    """A region op returning a dict/None is a SORT bug; the range guard must not mask it."""
    d = {"shape": (4, 4), "cs": []}
    assert backend_safe.region01(d) is d


def test_nonfinite_region_is_still_scrubbed_and_binary():
    """The finiteness half must keep working, and its result must also be in-contract."""
    out = backend_safe.sanitize(np.array([[np.nan, 2.5], [np.inf, 0.0]]),
                                np.zeros((2, 2)), "region")
    assert np.all(np.isfinite(out))
    assert set(np.unique(out).tolist()) <= {0.0, 1.0}


def test_failed_op_still_degrades_to_an_empty_region():
    """Backward compatibility with the documented fail-open registry contract."""
    empty = backend_safe.sanitize(None, np.zeros((16, 16)), "region")
    assert isinstance(empty, np.ndarray) and empty.shape == (16, 16) and empty.sum() == 0.0


# --------------------------------------------------------------------------- #
# `fallback()` の返り値そのものが有限か —— 2026-09-05 追加。
#
# `guard` は「返り値は有限」と約束しているが、`image`/`volume`/`any`/`color` の
# 退避値は「入力を [0,1] に切り詰めたもの」で、**`np.clip` は NaN を通す**。
# 入力そのものが非有限のとき(欠測を含む観測、空配列の 0/0、NaN を入口で弾いた
# op が投げた例外)だけ、この約束が破れていた。
#
# 変異テスト(WSL, mutmut)でも `fallback()` は生き残りが最も多い関数だった
# (563 変異中 89 がここ)—— 全 op を守る側の関数がいちばん手薄、という形。
# --------------------------------------------------------------------------- #

_NONFINITE_INPUTS = [
    np.full((6, 8), np.nan),
    np.full((6, 8), np.inf),
    np.full((6, 8), -np.inf),
    np.where(np.arange(48).reshape(6, 8) % 3 == 0, np.nan, 0.5),
    np.full((6, 8, 3), np.nan),
    np.full((4, 5, 6), np.inf),
    np.full((6, 8), complex(np.nan, np.inf)),
]


@pytest.mark.parametrize("sort", ["image", "volume", "any", "color", "region",
                                  "feature", "match", None])
@pytest.mark.parametrize("v", _NONFINITE_INPUTS, ids=lambda a: "%s%s" % (a.dtype.kind, a.shape))
def test_the_fallback_value_is_finite_even_when_the_input_is_not(sort, v):
    out = backend_safe.fallback(v, sort)
    a = np.asarray(out)
    a = np.asarray(a.real if a.dtype.kind == "c" else a, dtype=float)
    assert np.all(np.isfinite(a)), "%s の退避値に非有限が残った" % sort


@pytest.mark.parametrize("v", _NONFINITE_INPUTS, ids=lambda a: "%s%s" % (a.dtype.kind, a.shape))
def test_the_contour_fallback_stays_a_contour_for_a_non_finite_input(v):
    """`contour` だけ返り値が dict —— 形が壊れていないことを別に見る。"""
    out = backend_safe.fallback(v, "contour")
    assert isinstance(out, dict) and out["cs"] == []
    assert len(out["shape"]) == 2 and all(int(d) >= 0 for d in out["shape"])


def test_the_color_fallback_is_three_channels_whatever_the_input_shape():
    """変異テストの生き残りが集まっていた枝 —— 実際に呼んで形を確かめる。"""
    assert backend_safe.fallback(np.full((6, 8), np.nan), "color").shape == (6, 8, 3)
    assert backend_safe.fallback(np.full((6, 8, 3), np.inf), "color").shape == (6, 8, 3)
    assert backend_safe.fallback(np.zeros((2, 2, 5)), "color").shape[-1] == 3


def test_the_match_fallback_is_a_three_vector():
    out = np.asarray(backend_safe.fallback(np.full((6, 8), np.nan), "match"), float)
    assert out.shape == (3,) and np.all(out == 0.0)


def test_the_feature_fallback_is_a_finite_scalar_zero():
    out = backend_safe.fallback(np.full((6, 8), np.nan), "feature")
    assert np.ndim(out) == 0 and float(out) == 0.0


def test_require_finite_rejects_non_finite_and_passes_everything_else():
    """入口で弾く道具そのもの。**返すのは元の配列**(コピーでも変換でもない)。"""
    ok = np.linspace(0, 1, 12).reshape(3, 4)
    assert backend_safe.require_finite(ok, "t") is ok
    for bad in (np.full((3, 4), np.nan), np.full((3, 4), np.inf),
                np.where(np.eye(4) > 0, -np.inf, 0.5)):
        with pytest.raises(ValueError):
            backend_safe.require_finite(bad, "t")
    # 整数配列に NaN は存在しない —— 走査せずに通す
    assert backend_safe.require_finite(np.arange(6), "t") is not None


def test_a_guarded_op_that_rejects_a_non_finite_input_still_returns_a_finite_value():
    """入口で弾く → `guard` が台帳に記録 → 有限な退避値、まで通しで確かめる。

    ★これが `xsk2_reconstruction` / `xsk2_h_maxima` の実害の形。全 NaN の画像を
    渡すと `skimage.morphology` のネイティブ側がヒープを壊し、2 つを交互に
    呼んだところで **SIGSEGV でプロセスごと落ちた**(2026-09-05 実測)。
    Python の例外にならないので `guard` では捕まえられない —— 入口で弾く以外にない。
    """
    def rejects(v, a, b):
        return backend_safe.require_finite(v, "rejects")

    g = backend_safe.guard(rejects, "image", name="t_rejects")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", backend_safe.FullseyeFallbackWarning)
        out = np.asarray(g(np.full((5, 5), np.nan), 0.5, 0.5), float)
    assert out.shape == (5, 5) and np.all(np.isfinite(out))
    assert "t_rejects" in backend_safe.fallback_counts()
