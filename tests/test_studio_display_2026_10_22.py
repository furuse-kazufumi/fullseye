"""Studio slice 9: display ranges are view state, not data changes."""
import numpy as np
import pytest

import imgio
import studio_display as display


def test_auto_each_and_shared_ranges_keep_comparisons_honest():
    a = np.array([[0.0, 1.0, 2.0]])
    b = np.array([[1.0, 2.0, 3.0]])
    each = display.resolve_range([a, b], display.DisplayRange())
    assert [(r.lo, r.hi) for r in each] == [(0, 2), (1, 3)]
    assert not np.array_equal(display.to_display(a, each[0])[0][0, 1],
                              display.to_display(b, each[1])[0][0, 0])
    shared = display.resolve_range([a, b], display.DisplayRange(mode="shared"))
    assert shared.lo == 0 and shared.hi == 3
    assert np.array_equal(display.to_display(a, shared)[0][0, 1],
                          display.to_display(b, shared)[0][0, 0])


def test_nonfinite_and_clipped_counts_and_warning():
    image = np.array([[-1.0, 0.0, 2.0, np.nan, np.inf, -np.inf]])
    rng = display.DisplayRange("manual", 0, 1, colormap="viridis")
    rgb, info = display.to_display(image, rng)
    assert (info.nan_count, info.inf_count, info.under_count, info.over_count) == (1, 2, 1, 1)
    assert np.all(rgb[0, 3:] == np.array([255, 0, 255]))
    assert info.warning == "レンジ外 2 画素(下 1 / 上 1) / NaN 1 / Inf 2 画素"
    assert "元データは変更していません" in info.note

    metadata = display.range_info(image, rng)
    assert metadata == info
    target = np.zeros((1, 6, 3), dtype=np.uint8)
    assert display.mark_nonfinite(target, image) is target
    assert np.all(target[0, :3] == 0)
    assert np.all(target[0, 3:] == np.array([255, 0, 255]))


def test_constant_and_manual_validation_fail_closed():
    resolved = display.resolve_range([np.full((2, 2), 7)], display.DisplayRange("shared"))
    assert resolved.constant and resolved.lo == resolved.hi == 7
    rgb, _ = display.to_display(np.full((2, 2), 7), resolved)
    assert np.all(rgb == 128)
    for rng in (display.DisplayRange("manual", 1, 1),
                display.DisplayRange("manual", np.nan, 2),
                display.DisplayRange("mystery"), display.DisplayRange(colormap="hot")):
        with pytest.raises(ValueError):
            display.resolve_range([np.zeros((1, 1))], rng)


def test_readout_uses_original_value_and_handles_bounds():
    image = np.array([[0.4213, np.nan]], dtype=np.float64)
    rng = display.DisplayRange("manual", 0, 1)
    got = display.pixel_readout(image, rng, 0, 0)
    assert got["value"] == 0.4213 and got["display_value"] == 108
    assert got["dtype"] == "float64" and "元データではありません" in got["note"]
    assert display.pixel_readout(image, rng, 0, 1)["value"] == "NaN"
    assert display.pixel_readout(image, rng, 4, 0) is None


def test_save_raw_display_and_both_without_overwrite(tmp_path):
    image = np.array([[0, 257], [65535, 3]], dtype=np.uint16)
    rng = display.DisplayRange("manual", 0, 65535, colormap="viridis")
    assert display.save_outputs(image, rng, tmp_path / "raw", "raw") == [tmp_path / "raw.npy"]
    assert np.array_equal(np.load(tmp_path / "raw.npy"), image)
    assert np.load(tmp_path / "raw.npy").dtype == image.dtype
    display.save_outputs(image, rng, tmp_path / "shown", "display")
    assert imgio.load(str(tmp_path / "shown.png"), color=True).shape == (2, 2, 3)
    on_screen = np.array([[[1, 2, 3], [4, 5, 6]],
                          [[7, 8, 9], [10, 11, 12]]], dtype=np.uint8)
    display.save_outputs(image, rng, tmp_path / "screen", "display", display_rgb=on_screen)
    loaded = np.rint(imgio.load(str(tmp_path / "screen.png"), color=True) * 255).astype(np.uint8)
    assert np.array_equal(loaded, on_screen)
    paths = display.save_outputs(image, rng, tmp_path / "both", "both")
    assert paths == [tmp_path / "both.npy", tmp_path / "both.png"]
    with pytest.raises(ValueError, match="already exists"):
        display.save_outputs(image, rng, tmp_path / "both", "both")
    with pytest.raises(ValueError, match="unknown save choice"):
        display.save_outputs(image, rng, tmp_path / "x", "jpeg")


def test_gui_controls_are_view_only(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window()
    controls = win._display_range_controls
    assert "colormap" not in controls
    before_generation = win._run_controller.generation
    controls["shared"].click()
    app.processEvents()
    resolved = win._display_range([np.array([[0.0]]), np.array([[10.0]])])
    assert resolved.mode == "shared" and (resolved.lo, resolved.hi) == (0, 10)
    assert not win._state["dirty"]
    assert win._run_controller.generation == before_generation
    text = win._format_display_readout(
        np.array([[0.4213]], dtype=np.float64), display.DisplayRange("manual", 0, 1), 0, 0)
    assert text == "値 0.4213 (float64) / 表示 108 / レンジ 0〜1"
    win.quiesce(); win.close_guard = lambda: True; win.close(); app.processEvents()


def test_gui_region_overlay_uses_apply_display_with_resolved_range(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    image = np.linspace(0, 1, 48 * 48).reshape(48, 48)
    model = studio.PipelineModel(image)
    model.add_stage("threshold")
    calls = []
    original = studio.apply_display

    def recording_apply(value, mode, **kwargs):
        calls.append((value, mode, kwargs))
        return original(value, mode, **kwargs)

    monkeypatch.setattr(studio, "apply_display", recording_apply)
    win, _ = studio.build_window(model)
    win._set_display_mode("region overlay")
    app.processEvents()
    value, mode, kwargs = calls[-1]
    resolved = win._display_range([value])
    assert mode == "region overlay"
    assert kwargs["vmin"] == resolved.lo and kwargs["vmax"] == resolved.hi
    assert kwargs["draw"] == win._state["draw"]
    assert win._display_range_controls["warning"].text() == "このモードは表示レンジを使いません"
    win.quiesce(); win.close_guard = lambda: True; win.close(); app.processEvents()


def test_gui_jet_uses_existing_display_renderer(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    import studio

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    image = np.linspace(0, 1, 48 * 48).reshape(48, 48)
    win, _ = studio.build_window(studio.PipelineModel(image))
    win._set_display_mode("jet")
    app.processEvents()
    resolved = win._display_range([image])
    gray, _ = display.to_display(image, resolved)
    assert win._state["result"].shape == gray.shape
    assert not np.array_equal(win._state["result"], gray)
    win.quiesce(); win.close_guard = lambda: True; win.close(); app.processEvents()
