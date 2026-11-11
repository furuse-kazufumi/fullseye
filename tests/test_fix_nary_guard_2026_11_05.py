"""1.0 前の修正 2026-11-05(nary-guard): 多入力の入口すべてに単入力と同じ入力の契約を。

外部監査 F2: uint8 の 32 を 2 枚 ``add_image`` すると strict でも 1.0 を返し、例外も台帳記録も無かった
(期待 = strict なら拒否、正規化するなら 64/255)。``api.apply`` の n 項経路は前の便(#263/#270)で直っている
—— ここでは**全 17 本の n 項 op と全部の入口**でそれを固定し、まだ穴だった 2 つの入口を直した:

* MCP ``fullseye_pipeline`` の ``python`` 実行器の段(型つきの関数を直に呼ぶ。2 入力の
  ``polarization_render`` などと 1 入力の ``fringe_ftp_phase``)が uint8 / 非有限のハンドルを素通しした。
* Studio の 2 枚の知覚パネル(``PerceptionModel``)が両方の枠を ``np.asarray(x, float64)`` で受け、
  uint8 の B を 0..255 のまま [0,1] の A と比べた(オプティカルフロー・ステレオ深度が黙って別の絵になる)。

真値はどれも**同じ値を float64 [0,1] で渡した経路**(独立に x/255 を作って渡す)と比べる。
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pytest

import api
import backend_safe as bs
import imgops_nary


# ----------------------------------------------------------------------------- api / facade
def _nary_ops():
    ops = imgops_nary.build_nary()
    assert len(ops) == 17, len(ops)          # the tier this file pins (grows -> look again)
    return ops


def _float_input(srt, shape=(8, 8)):
    if srt == "region":
        r = np.zeros(shape)
        r[2:5, 2:6] = 1.0
        return r
    return np.linspace(0.1, 0.9, shape[0] * shape[1]).reshape(shape)


def test_audit_f2_reproduction_exact_value_and_strict_refusal():
    u = np.full((2, 2), 32, np.uint8)
    with pytest.raises(ValueError, match=r"float64 in \[0,1\]"):
        api.apply([u, u], "add_image", on_error="raise")
    bs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = api.apply([u, u], "add_image", on_error="fallback")
    assert float(out[0, 0]) == pytest.approx(64 / 255, abs=1e-12)
    recs = [r for r in bs.fallbacks() if r["name"] == "add_image" and r["source"] == "input"]
    assert len(recs) == 2 and all("uint8 -> float64 (/255)" in r["error"] for r in recs)


def test_every_nary_image_input_is_normalised_or_refused_like_a_single_input():
    """各 n 項 op の、dtype 契約の対象(image)の入力 1 本ずつを uint8 にする。

    strict → ValueError、fallback → x/255 を float で渡した結果と一致し、台帳に 1 件。
    畳み込みの核(convol_image の第 2 入力)は画像でなく重みの表なので対象外(型だけ float64)。
    """
    checked = 0
    for o in _nary_ops():
        for pos, srt in enumerate(o.in_sorts):
            if srt != "image" or (o.name == "convol_image" and pos == 1):
                continue
            xs = [_float_input(s) for s in o.in_sorts]
            if o.name == "convol_image":
                xs[1] = np.full((3, 3), 1 / 9)
            u8 = np.round(xs[pos] * 255).astype(np.uint8)
            ref_in = list(xs)
            ref_in[pos] = u8.astype(np.float64) / 255.0
            with pytest.raises(ValueError, match=r"float64 in \[0,1\]"):
                api.apply([*xs[:pos], u8, *xs[pos + 1:]], o.name, on_error="raise")
            bs.clear_fallbacks()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                got = api.apply([*xs[:pos], u8, *xs[pos + 1:]], o.name, on_error="fallback")
            recs = [r for r in bs.fallbacks() if r["source"] == "input"]
            want = api.apply(ref_in, o.name, on_error="raise")
            assert len(recs) == 1, (o.name, pos, recs)
            np.testing.assert_array_equal(np.asarray(got), np.asarray(want), err_msg="%s[%d]" % (o.name, pos))
            checked += 1
    assert checked == 23, checked     # 11 (image,image) x 2 - the convol kernel + 2 (image,region) x 1


def test_every_nary_input_refuses_non_finite_values():
    checked = 0
    for o in _nary_ops():
        for pos in range(o.arity):
            xs = [_float_input(s) for s in o.in_sorts]
            bad = xs[pos].copy()
            bad[1, 1] = np.nan
            xs[pos] = bad
            with pytest.raises(ValueError, match="NaN or infinity"):
                api.apply(xs, o.name)
            checked += 1
    assert checked == 34, checked


def test_facade_and_graph_entrances_share_the_rule():
    import fullseye
    import graphengine
    u = np.full((4, 4), 32, np.uint8)
    with pytest.raises(ValueError, match=r"float64 in \[0,1\]"):
        fullseye.apply([u, u], "add_image", on_error="raise")
    g = graphengine.FullseyeGraph("g")
    g.add("s", "add_image", ["$in", "$b"])
    with pytest.raises(ValueError, match=r"float64 in \[0,1\]"):
        g.run({"$in": u, "$b": u}, terminal="s", on_error="raise")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = g.run({"$in": u, "$b": u}, terminal="s", on_error="fallback")
    assert float(out[0, 0]) == pytest.approx(64 / 255, abs=1e-12)


# ----------------------------------------------------------------------------- MCP python stages
@pytest.fixture
def mcp(tmp_path):
    from fullseye.mcp import Catalog, call_tool
    from fullseye.mcp.handles import SAMPLE_DIR, HandleStore
    import imgio
    yy, xx = np.mgrid[0:32, 0:32]
    fringe = 0.5 + 0.4 * np.cos(2 * np.pi * xx / 8.0)
    q = np.round(fringe * 255).astype(np.uint8)
    np.save(tmp_path / "u8.npy", q)
    np.save(tmp_path / "f64.npy", q.astype(np.float64) / 255.0)
    bad = q.astype(np.float64) / 255.0
    bad[4, 4] = np.nan
    np.save(tmp_path / "nan.npy", bad)
    paths = []
    for k in range(4):
        p = tmp_path / ("shift%d.png" % k)
        imgio.save(str(p), 0.5 + 0.4 * np.cos(2 * np.pi * xx / 8.0 + k * np.pi / 2))
        paths.append(str(p))
    cat = Catalog.load()
    store = HandleStore(roots=[SAMPLE_DIR, str(tmp_path)], thumb_dir=str(tmp_path / "thumbs"))

    def load(name):
        r = call_tool("fullseye_load_image", {"path": str(tmp_path / name), "vision": "none"}, cat, store)
        return r["structuredContent"]["handle"]

    stack = call_tool("fullseye_load_stack", {"paths": paths, "sort": "seq<image>"}, cat, store)
    handles = {k: load(k + ".npy") for k in ("u8", "f64", "nan")}
    handles["stack"] = stack["structuredContent"]["handle"]
    return lambda req: call_tool("fullseye_pipeline", req, cat, store), handles


def _stage(result, n):
    return [s for s in result["structuredContent"]["stages"] if s["stage"] == n][0]


def test_mcp_python_stage_single_input_gets_the_contract(mcp):
    run, h = mcp
    ok = run({"handle": h["f64"], "stages": [{"op": "fringe_ftp_phase"}], "vision": "none"})
    assert ok["isError"] is False and _stage(ok, 1)["status"] == "ok"
    for key, msg in (("u8", r"float64 in \[0,1\].*uint8"), ("nan", "NaN or infinity")):
        r = run({"handle": h[key], "stages": [{"op": "fringe_ftp_phase"}], "vision": "none"})
        s = _stage(r, 1)
        assert r["isError"] is True and s["status"] == "failed", (key, s)
        assert __import__("re").search(msg, s["error"]["message"]), (key, s["error"])
        # the registry stage of the same handle says the same thing (one rule per MCP)
        g = run({"handle": h[key], "stages": [{"op": "gauss_filter"}], "vision": "none"})
        assert __import__("re").search(msg, _stage(g, 1)["error"]["message"]), (key, _stage(g, 1))


# polarization_render takes radiances (>= 0) and refuses the wrapped phase [-pi, pi] of stage 1 on its own,
# so it cannot be the float control here; the helper test below covers its image inputs.
@pytest.mark.parametrize("op", ["phase_correlation_shift", "deflectometry_phase_to_slope"])
def test_mcp_python_stage_two_inputs_get_the_contract(mcp, op):
    """2 入力の型つき段: 第 1 入力 = 読んだハンドル、第 2 入力 = 縞の束から作った位相(float)。"""
    run, h = mcp

    def req(img):
        return {"handle": img, "bindings": {"have:image": img, "have:seq<image>": h["stack"]},
                "outputs": ["stage:2"], "vision": "none",
                "stages": [{"op": "wrapped_phase", "inputs": ["have:seq<image>"]},
                           {"op": op, "inputs": ["have:image", "stage:1"]}]}
    ok = run(req(h["f64"]))
    assert _stage(ok, 1)["status"] == "ok", _stage(ok, 1)
    assert _stage(ok, 2)["status"] == "ok", _stage(ok, 2)
    bad = run(req(h["u8"]))
    s = _stage(bad, 2)
    assert s["status"] == "failed" and "uint8" in s["error"]["message"], s


def test_mcp_python_stage_helper_leaves_untyped_sorts_alone():
    from fullseye.mcp.server import _python_stage_inputs
    pts = np.array([[0.0, 0.0, np.nan]])
    seq = np.zeros((3, 4, 4), np.uint8)
    f32 = np.full((4, 4), 0.5, np.float32)
    out = _python_stage_inputs([pts, seq, f32], ["points", "seq<image>", "image"], "probe")
    assert len(out) == 3
    assert out[0] is pts and out[1] is seq           # not image/color/volume: the typed value is untouched
    assert out[2].dtype == np.float64 and float(out[2][0, 0]) == 0.5   # lossless float32 -> float64
    u8 = np.full((4, 4), 128, np.uint8)
    with pytest.raises(ValueError, match=r"float64 in \[0,1\].*uint8"):
        _python_stage_inputs([np.full((4, 4), 0.5), u8], ["image", "image"], "polarization_render")


# ----------------------------------------------------------------------------- Studio two-frame panel
def _frames():
    yy, xx = np.mgrid[0:48, 0:48]
    a = 0.5 + 0.3 * np.sin(xx / 5.0) * np.cos(yy / 7.0)
    a8 = np.round(a * 255).astype(np.uint8)
    b8 = np.roll(a8, 2, axis=1)
    return a8, b8


@pytest.mark.parametrize("mode", ["optical flow", "stereo depth"])
def test_studio_perception_uint8_frame_matches_the_float_frame(mode, monkeypatch):
    import studio
    monkeypatch.delenv("FULLSEYE_ON_ERROR", raising=False)
    a8, b8 = _frames()
    af, bf = a8 / 255.0, b8 / 255.0
    want = studio.PerceptionModel(frame_b=bf).view(mode, af)
    assert float(np.ptp(want)) > 0.0                 # a real picture, not a constant one
    bs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        got_b = studio.PerceptionModel(frame_b=b8).view(mode, af)
        got_ab = studio.PerceptionModel(frame_b=b8).view(mode, a8)
    np.testing.assert_array_equal(got_b, want)
    np.testing.assert_array_equal(got_ab, want)
    recs = [r for r in bs.fallbacks() if r["name"] == "studio_perception"]
    assert len(recs) == 3, recs                      # B, then A and B: each conversion is recorded


def test_studio_perception_strict_refuses_integer_and_any_policy_refuses_nan(monkeypatch):
    import studio
    a8, b8 = _frames()
    monkeypatch.setenv("FULLSEYE_ON_ERROR", "raise")
    with pytest.raises(ValueError, match=r"float64 in \[0,1\]"):
        studio.PerceptionModel(frame_b=b8).view("optical flow", a8 / 255.0)
    monkeypatch.delenv("FULLSEYE_ON_ERROR")
    bad = b8 / 255.0
    bad[3, 3] = np.nan
    with pytest.raises(ValueError, match="frame B contains NaN"):
        studio.PerceptionModel(frame_b=bad).view("optical flow", a8 / 255.0)
    assert os.environ.get("FULLSEYE_ON_ERROR") is None
