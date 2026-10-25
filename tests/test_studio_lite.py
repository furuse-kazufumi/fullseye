# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_lite(ブラウザ版 Studio-lite v0)の、node 無しで見られる門。

* core の入口が Studio の部品(param_specs / studio.apply_display / engine / studio.validate_pipeline_dict)を呼んでいる
* レシピの往復: core が書く JSON を engine.FullseyeEngine.load と studio.validate_pipeline_dict が読み、同じ結果になる
* Studio が書く bypass 印つきの段を core が読む
* op の台帳 ops_subset.json が registry と整合し(全部 registry にある名前)、空でなく、実測の由来を名乗っている
* 門のレシピ 10 本は全段が台帳にある
* i18n.json は pocviewer.LANGS の 8 言語を全部の文字列で持つ
* index.html / build_bundle.py は外部 URL を読まない(http(s):// を含まない)
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LITE = os.path.join(ROOT, "studio_lite")
if LITE not in sys.path:
    sys.path.insert(0, LITE)

import core  # noqa: E402
import engine  # noqa: E402
import pocviewer  # noqa: E402
import studio  # noqa: E402
import api  # noqa: E402


@pytest.fixture(scope="module")
def subset():
    with open(os.path.join(LITE, "ops_subset.json"), encoding="utf-8") as f:
        d = json.load(f)
    core.set_subset(json.dumps(d))
    return d


@pytest.fixture(scope="module")
def img():
    rng = np.random.default_rng(0)
    yy, xx = np.mgrid[0:96, 0:96] / 96.0
    im = 0.5 + 0.3 * np.sin(2 * np.pi * 3 * xx) * np.cos(2 * np.pi * 2 * yy) + 0.05 * rng.standard_normal((96, 96))
    return np.clip(im, 0, 1).astype(np.float32)


def test_subset_ledger_is_measured_and_in_registry(subset):
    names = {o.name for o in api.REGISTRY}
    assert subset["n"] == len(subset["ops"]) > 100
    assert "compare_outputs" in subset["source"] and "ULP" in subset["criterion"]
    missing = [r["name"] for r in subset["ops"] if r["name"] not in names]
    assert not missing, "台帳にあって registry に無い op: %s" % missing[:10]
    assert all(r["verdict"] in ("bit_identical", "nonarray_equal") or r["verdict"].startswith("within_") for r in subset["ops"])
    loose = [r for r in subset["ops"] if r["verdict"].startswith("within_") and r["verdict"] != "within_1ulp"]
    assert all(r["max_ulp"] <= 4 and r["max_abs"] <= 1e-12 for r in loose), "台帳の緩い側は 4 ULP / 1e-12 まで"


def test_gate_recipes_are_all_in_subset(subset):
    with open(os.path.join(LITE, "gates", "recipes_gate.json"), encoding="utf-8") as f:
        g = json.load(f)
    names = {r["name"] for r in subset["ops"]}
    assert len(g["recipes"]) == 10
    for rc in g["recipes"]:
        bad = [s[0] for s in rc["stages"] if s[0] not in names]
        assert not bad, "%s: 台帳に無い op %s" % (rc["name"], bad)


def test_spec_comes_from_param_specs(subset):
    import param_specs
    sp = json.loads(core.spec("canny"))
    ref = param_specs.spec_for("canny")
    assert sp["a"]["label"] == ref["a"]["label"] and sp["a"]["min"] == ref["a"]["min"]
    assert core.format_knob("canny", "a", 0.4) == param_specs.format_display(ref["a"], 0.4)


def test_render_goes_through_apply_display(subset, img, monkeypatch):
    calls = []
    orig = studio.apply_display

    def spy(val, mode, base=None, **kw):
        calls.append(mode)
        return orig(val, mode, base=base, **kw)
    monkeypatch.setattr(studio, "apply_display", spy)
    for mode in ["gray", "region overlay", "shaded relief", "height (color)", "viridis"]:
        c = core.render(img, mode, base=img)
        assert c["kind"] == "image" and c["h"] == 96 and len(c["rgba"]) == 96 * 96 * 4
    assert calls == ["gray", "region overlay", "shaded relief", "height (color)", "viridis"]
    assert core.display_modes()[:4] == ["gray", "region overlay", "shaded relief", "height (color)"]


def test_recipe_roundtrip_engine_and_studio(subset, img, tmp_path):
    stages = [["gaussian", 0.4, 0.5], ["sobel_amp", 0.5, 0.5], ["otsu", 0.4, 0.5]]
    text = core.recipe_json("edge", json.dumps(stages))
    d = json.loads(text)
    assert d["fullseye_pipeline"] == 1 and d["name"] == "edge" and d["stages"] == stages
    p = tmp_path / "edge.json"
    p.write_text(text, encoding="utf-8")
    eng = engine.FullseyeEngine.load(str(p))
    assert [list(s) for s in studio.validate_pipeline_dict(d)][:3] == [[s[0], float(s[1]), float(s[2])] for s in stages] or \
        [[s[0], s[1], s[2]] for s in studio.validate_pipeline_dict(d)] == [[s[0], float(s[1]), float(s[2])] for s in stages]
    a = np.asarray(eng.run(img))
    b = np.asarray(core.run_chain_raw(img, json.dumps(stages)))
    assert a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b)


def test_studio_bypass_format_is_read_and_unavailable_is_named(subset):
    # 台帳を一時的に「gaussian と otsu だけ」にして、台帳に無い op(canny)が名指しされることを見る
    core.set_subset(json.dumps({"ops": [{"name": "gaussian"}, {"name": "otsu"}]}))
    try:
        r = json.loads(core.load_recipe(json.dumps({"stages": [["gaussian", 0.4, 0.5, True], ["canny", 0.3, 0.3], ["otsu", 0.4, 0.5]]})))
    finally:
        core.set_subset(json.dumps(subset))
    # Studio と同じく bypass 印の段は走らせない(列から外し、名前は bypassed に残す)
    assert r["stages"] == [["canny", 0.3, 0.3], ["otsu", 0.4, 0.5]]
    assert r["bypassed"] == ["gaussian"]
    assert r["unavailable"] == ["canny"]
    with pytest.raises(ValueError):
        core.load_recipe(json.dumps({"stages": [["no_such_op_xyz", 0.5, 0.5]]}))


def test_run_chain_cards_and_errors(subset, img):
    r = core.run_chain(img, json.dumps([["gaussian", 0.4, 0.5], ["otsu", 0.4, 0.5], ["count_obj", 0.5, 0.5]]), "region overlay")
    assert [c["op"] for c in r["cards"]] == [None, "gaussian", "otsu", "count_obj"]
    assert r["cards"][1]["kind"] == "image" and r["cards"][3]["kind"] == "text" and r["error"] is None
    assert all(isinstance(c["ms"], float) for c in r["cards"][1:])
    probs = json.loads(core.diagnose(json.dumps([["otsu", 0.4, 0.5], ["gaussian", 0.4, 0.5]])))
    assert probs and "sort_mismatch" in probs[0]


def test_i18n_has_all_pocviewer_langs():
    with open(os.path.join(LITE, "i18n.json"), encoding="utf-8") as f:
        d = json.load(f)
    assert tuple(d["langs"]) == tuple(pocviewer.LANGS)
    for k, v in d["strings"].items():
        missing = [lang for lang in pocviewer.LANGS if not v.get(lang)]
        assert not missing, "%s に無い言語 %s" % (k, missing)


def test_page_and_builder_fetch_no_external_url():
    for n in ("index.html", "build_bundle.py"):
        with open(os.path.join(LITE, n), encoding="utf-8") as f:
            s = f.read()
        urls = [u for u in re.findall(r"https?://[^\s\"'<>)]+", s) if not re.match(r"https?://(127\.0\.0\.1|localhost)", u)]
        assert not urls, "%s が外部 URL を含む: %s" % (n, urls)
    with open(os.path.join(LITE, "index.html"), encoding="utf-8") as f:
        s = f.read()
    assert "./pyodide/pyodide.mjs" in s and "./fullseye_bundle.zip" in s and "./ops_subset.json" in s
