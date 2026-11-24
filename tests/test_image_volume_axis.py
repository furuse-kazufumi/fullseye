"""2-D op に立体 (8,8,8) を渡す穴の opt-in 門 / opt-in guard for volumes fed to 2-D image ops.

既定の数値は変えない(docs/KNOWN_ISSUES.md §34: `_NDIM_OK["image"] = (2, 3)` は意図的)が、
最終軸が 1/3/4 でない 3-D 配列には op ごとに 1 回の Fullseye 警告を出す。
``extra_checks='on'`` のときは既定方針でも image/region op が入口で断る。
"""
import warnings

import numpy as np
import pytest

import fullseye as fs

VOL = np.random.default_rng(0).random((8, 8, 8))
RGB = np.random.default_rng(1).random((8, 8, 3))


def test_default_is_unchanged_volume_still_passes():
    fs.clear_fallbacks(reset_warnings=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = fs.apply(VOL, "gauss_filter")
    assert out.shape == (8, 8, 8)
    notices = [w for w in caught if issubclass(w.category, fs.FullseyeFallbackWarning)]
    assert len(notices) == 1
    assert "volume needs a volume op" in str(notices[0].message)


def test_opt_in_refuses_a_volume_for_image_and_region_ops():
    with _on():
        with pytest.raises(ValueError, match="3-D array of shape"):
            fs.apply(VOL, "gauss_filter")
        with pytest.raises(ValueError, match="3-D array of shape"):
            fs.apply(VOL > 0.5, "skeleton")


def test_opt_in_keeps_colour_and_gray_images_working():
    with _on():
        assert fs.apply(RGB, "invert", on_error="raise").shape == (8, 8, 3)
        assert fs.apply(RGB[..., :1], "invert", on_error="raise").shape == (8, 8, 1)
        assert fs.apply(RGB[..., 0], "gauss_filter", on_error="raise").shape == (8, 8)


class _on:
    def __enter__(self):
        self._old = fs.set_system("extra_checks", "on")

    def __exit__(self, *a):
        fs.set_system("extra_checks", self._old)
