# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer の anim3d の任意の鍵 labels(物体に付いて動く文字のラベル、2026-10-25)の門。

* labels を持たないページは前と同じバイト列、
* 持つページには塊が 1 回・drawAnim の呼び出しが 1 回(半透明・camera と一緒でも)、
* 詰めた値(物体の番号・ローカルの点・全言語の文字)が戻る、
* 未知の鍵・無い物体・形の違う offset・言語の欠けは ValueError(fail-closed)。
"""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

import pocviewer as pv

T_ = pv.viewer_text


def _spec(labels=None, alpha=None, camera=None):
    cube = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    tri = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
           [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    n = 3
    body = {"name": "box", "pos": cube, "faces": tri, "rgb": [200, 200, 200]}
    if alpha is not None:
        body["alpha"] = alpha
    tab = pv.viewer_anim3d_tab("a", T_("箱", "Box"), "passed", T_("説明", "Text"), np.arange(n) / 10.0, [body],
                               np.zeros((n, 1, 3)), np.tile([1.0, 0, 0, 0], (n, 1, 1)), labels=labels, camera=camera)
    return pv.viewer_spec("lab", T_("見本", "Sample"), T_("副題", "Sub"), T_("操作", "Hint"), [tab])


LAB = [{"body": "box", "offset": [0.0, 0.0, 0.6], "text": T_("箱 1 m", "box 1 m")}]


def test_page_without_labels_is_unchanged():
    a = pv._build_html(_spec(), ["ja", "en"])
    spec = _spec()
    spec["tabs"][0].pop("labels", None)
    assert a == pv._build_html(spec, ["ja", "en"])
    assert "drawLabels" not in a


@pytest.mark.parametrize("alpha,cam", [(None, None), (0.3, None), (None, {"dist": np.ones(3), "target": np.zeros((3, 3))})])
def test_labels_block_and_call_once(alpha, cam):
    html = pv._build_html(_spec(LAB, alpha, cam), ["ja", "en"])
    assert html.count("function drawLabels") == 1
    assert html.count("drawLabels(tab, S, f, vp);") == 1


def test_labels_values_roundtrip():
    html = pv._build_html(_spec(LAB), ["ja", "en"])
    d = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    lb = d["tabs"][0]["labels"]
    assert len(lb) == 1 and lb[0]["b"] == 0 and lb[0]["o"] == [0.0, 0.0, 0.6]
    assert lb[0]["x"] == {"ja": "箱 1 m", "en": "box 1 m"}


@pytest.mark.parametrize("bad", [
    [{"body": "nope", "text": T_("a", "a")}],
    [{"body": "box", "offset": [0, 0], "text": T_("a", "a")}],
    [{"body": "box", "text": {"ja": "a"}}],
    [{"body": "box", "text": T_("a", "a"), "color": "#fff"}],
])
def test_labels_fail_closed(bad):
    with pytest.raises(ValueError):
        pv._build_html(_spec(bad), ["ja", "en"])
