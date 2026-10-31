"""平面スカラー場の起伏つまみの門(2026-10-31)。"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pocviewer as pv  # noqa: E402


def _spec(*, relief=True, moving_pos=False, curved=False):
    pos = np.array([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0],
                    [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]])
    if curved:
        pos[-1, 2] = 0.1
    t = np.array([0.0, 1.0])
    body = {"name": "field", "pos": np.repeat(pos[None], 2, axis=0) if moving_pos else pos,
            "faces": np.array([[0, 1, 2], [0, 2, 3]]), "rgb": [40, 120, 220]}
    if relief:
        body.update(val=np.array([0.0, 1.0, 3.0, 2.0]), relief_default=0.0)
    xyz = np.zeros((2, 1, 3)); quat = np.zeros((2, 1, 4)); quat[..., 0] = 1
    tab = pv.viewer_anim3d_tab(
        "plane", pv.viewer_text("平面", "Plane"), "passed", pv.viewer_text("平面。", "A plane."),
        t, [body], xyz, quat, static_reason="The scalar plane is intentionally static in this unit gate.")
    return pv.viewer_spec("relief_gate", pv.viewer_text("起伏", "Relief"),
                          pv.viewer_text("副題", "Subtitle"), pv.viewer_text("操作", "Controls"), [tab])


def test_relief_packs_rgb_as_colour_and_val_only_as_normal_displacement():
    data = pv._pack_spec(_spec(), ["ja", "en"])
    tab, body = data["tabs"][0], data["tabs"][0]["bodies"][0]
    assert tab["relief_default"] == 0.0
    assert body["rgb1"] == [40, 120, 220]
    assert body["relief"] == {"lo": 0.0, "hi": 3.0, "radius": np.sqrt(2), "size": np.sqrt(2)/4}
    decoded = pv._decode_array(data["arrays"][body["val"]])
    assert body["relief_png"] == {"lo": 0.0, "hi": 3.0}
    assert decoded.max() == 255
    assert body["relief"]["size"] * 1.0 == np.sqrt(2)/4  # ×1: 外接半径の 1/4


def test_relief_is_opt_in_so_existing_public_viewers_keep_their_generated_page():
    html = pv._build_html(_spec(relief=False), ["ja", "en"])
    assert "id=\"relief\"" not in html
    assert "__viewerRelief" not in html
    assert "attribute float a_r" not in html


def test_relief_page_has_operation_slider_and_shader_normal_displacement():
    html = pv._build_html(_spec(), ["ja", "en"])
    assert 'id="relief" min="0" max="200"' in html
    assert "attribute float a_r" in html
    assert "a_p+a_n*a_r*u_relief" in html
    assert "__viewerRelief" in html


@pytest.mark.parametrize("kw, message", [
    ({"moving_pos": True}, r"pos \(T,N,3\)"),
    ({"curved": True}, "同一平面"),
])
def test_relief_rejects_time_varying_or_nonplanar_geometry(kw, message):
    with pytest.raises(ValueError, match=message):
        pv._pack_spec(_spec(**kw), ["ja", "en"])


def test_browser_gate_x0_has_zero_pixel_difference_and_x2_stays_within_half_radius(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import headless_chrome
    if not headless_chrome.find_chrome():
        pytest.skip("Chrome が無い")
    page = tmp_path / "relief.html"
    page.write_text(pv._build_html(_spec(), ["ja", "en"]), encoding="utf-8")
    with headless_chrome.HeadlessChrome() as ch:
        ch.open(headless_chrome.file_url(page) + "?tab=plane&lang=ja", width=900, height=900)
        ch.wait_for("window.__viewerRelief && !window.__viewerRelief.vertex('plane',0,1,1).pending")
        ch.eval("window.__viewerRelief.set(0)")
        time.sleep(.2)
        assert ch.eval("window.__viewerRelief.capture()") > 0
        ch.eval("window.__viewerRelief.set(0)")
        diff = ch.eval("window.__viewerRelief.pixelDiff()")
        peak = ch.eval("window.__viewerRelief.vertex('plane',0,1,2)")
    assert diff == {"changed": 0, "max": 0}
    assert peak["normalized"] == 1
    assert np.isclose(peak["distance"], peak["expected"])
    assert np.isclose(peak["distance"], .5*peak["radius"])
    assert peak["negativeVertices"] == 0 and peak["minDistance"] >= 0
