"""発表用の図は後段の画素複製でなく、全要素を同率で描く。"""
from __future__ import annotations

import numpy as np
import pytest

import examplefig as figs


def _plot(scale: int) -> np.ndarray:
    x = np.linspace(0.0, 10.0, 101)
    return np.asarray(figs.render_plot(
        [("sin", x, np.sin(x)), ("cos", x, np.cos(x))],
        xlabel="x axis", ylabel="y axis", title="Scale test 0123456789",
        xlim=(0.0, 10.0), ylim=(-1.0, 1.0), scale=scale,
    ))


def _foreground_match(a: np.ndarray, b: np.ndarray) -> float:
    """白地を除いた画素の一致率。白地だけで合格する比較にしない。"""
    foreground = (np.min(a, axis=2) < 0.99) | (np.min(b, axis=2) < 0.99)
    return float(np.mean(np.all(np.isclose(a[foreground], b[foreground], atol=1 / 255), axis=1)))


def test_scale_two_is_redrawn_not_nearest_neighbour_enlarged():
    one, two = _plot(1), _plot(2)
    nearest = one.repeat(2, axis=0).repeat(2, axis=1)
    assert two.shape == (one.shape[0] * 2, one.shape[1] * 2, 3)
    assert _foreground_match(two, nearest) < 0.9


def test_tick_digit_height_is_proportional_to_scale():
    heights = []
    for scale in (1, 2):
        image = _plot(scale)
        # 描画枠の下端は論理座標 y=296。10 px 下から始まる x 目盛り数字だけを見る。
        band = image[(296 + 10) * scale:(296 + 21) * scale]
        rows = np.flatnonzero(np.min(band, axis=2).min(axis=1) < 0.5)
        heights.append(int(rows[-1] - rows[0] + 1))
    assert heights[0] >= 6
    assert heights[1] == pytest.approx(2 * heights[0], abs=2)


def test_unchanged_save_plot_call_uses_default_scale_two(tmp_path, monkeypatch):
    monkeypatch.setenv(figs.ENV_DIR, str(tmp_path))
    monkeypatch.delenv(figs.ENV_SCALE, raising=False)
    figs.reset()
    path = figs.save_plot("legacy_call", [("", [0, 1], [0, 1])], size=(300, 200))
    assert path is not None
    from PIL import Image
    with Image.open(path) as image:
        assert image.size == (600, 400)


def test_environment_can_select_scale_one(monkeypatch):
    monkeypatch.setenv(figs.ENV_SCALE, "1")
    assert figs.render_table(["name", "value"], [["a", "1"]]).shape[0] == 104


def test_grid_enlargement_uses_bicubic_not_pixel_repetition():
    src = np.zeros((5, 5, 3), dtype=np.float64)
    src[2, 2] = 1.0
    enlarged = figs._upscale([src], 3)[0]
    nearest = src.repeat(3, axis=0).repeat(3, axis=1)
    assert enlarged.shape == nearest.shape
    assert not np.array_equal(enlarged, nearest)
    assert np.any((enlarged > 0.0) & (enlarged < 1.0))
