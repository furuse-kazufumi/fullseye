# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer の anim3d の任意の鍵 camera(コマごとのカメラの注視点と距離、2026-10-25)の門。

* camera を持たないページは前と同じバイト列(塊も置き換えも入らない)、
* 持つページには塊が 1 回、カメラの式は drawAnim(と半透明があれば drawTranslucent)の全か所で置き換わる、
* 値は量子化せず JSON の数で戻る(1 km → 3 m の寄りで揺れない)、
* T の不一致・0 以下・NaN・未知の鍵・欠けた鍵は ValueError(fail-closed)。
"""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

import pocviewer as pv

T_ = pv.viewer_text


def _spec(camera=None, alpha=None):
    cube = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    tri = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
           [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    n = 4
    body = {"name": "box", "pos": cube, "faces": tri, "rgb": [200, 200, 200]}
    if alpha is not None:
        body["alpha"] = alpha
    tab = pv.viewer_anim3d_tab("a", T_("箱", "Box"), "passed", T_("説明", "Text"), np.arange(n) / 10.0, [body],
                               np.zeros((n, 1, 3)), np.tile([1.0, 0, 0, 0], (n, 1, 1)), camera=camera)
    return pv.viewer_spec("cam", T_("見本", "Sample"), T_("副題", "Sub"), T_("操作", "Hint"), [tab])


def _data(html):
    return json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))


CAM = {"dist": np.geomspace(1000.0, 3.0, 4), "target": np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0.5, 0]], float)}


def test_page_without_camera_is_unchanged():
    spec = _spec()
    spec["tabs"][0].pop("camera", None)
    a = pv._build_html(spec, ["ja", "en"])
    b = pv._build_html(_spec(), ["ja", "en"])
    assert a == b
    assert "camNow" not in a and pv._JS_CAM_OLD in a


@pytest.mark.parametrize("alpha", [None, 0.3])
def test_camera_block_and_all_camera_expressions_replaced(alpha):
    html = pv._build_html(_spec(CAM, alpha), ["ja", "en"])
    assert html.count("function camNow") == 1
    assert pv._JS_CAM_OLD not in html
    assert html.count("const C = camNow(tab, S, f);") == (2 if alpha else 1)


def test_camera_values_roundtrip_unquantised():
    d = _data(pv._build_html(_spec(CAM), ["ja", "en"]))
    cam = d["tabs"][0]["camera"]
    assert len(cam["d"]) == 4 and len(cam["t"]) == 4
    assert np.allclose(cam["d"], CAM["dist"], rtol=1e-5)
    assert np.allclose(cam["t"], CAM["target"], atol=1e-6)
    assert cam["d"][-1] == pytest.approx(3.0, rel=1e-6)


@pytest.mark.parametrize("bad", [
    {"dist": np.ones(3), "target": np.zeros((4, 3))},
    {"dist": np.array([1.0, 0.0, 1.0, 1.0]), "target": np.zeros((4, 3))},
    {"dist": np.array([1.0, np.nan, 1.0, 1.0]), "target": np.zeros((4, 3))},
    {"dist": np.ones(4), "target": np.zeros((4, 2))},
    {"dist": np.ones(4)},
    {"dist": np.ones(4), "target": np.zeros((4, 3)), "az": np.zeros(4)},
])
def test_camera_fail_closed(bad):
    with pytest.raises(ValueError):
        pv._build_html(_spec(bad), ["ja", "en"])
