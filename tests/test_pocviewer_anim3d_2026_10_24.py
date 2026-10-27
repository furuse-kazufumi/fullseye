# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""pocviewer の kind "anim3d"(動く 3-D)と無損失 PNG の門(2026-10-24)。

固定するもの:
* 姿勢を詰めて戻すと、位置は量子化の刻みの半分以内、四元数は成分が刻みの半分以内・角度の誤差 < 1e-4 rad。
* 四元数は正規化して符号を揃える(q と -q が同じ整数になる)。ノルム 0 は止まる。
* 物体のメッシュは 1 回だけ(コマ数に比例して増えない)。同じメッシュの物体は配列を共有する。
* 軌跡を body + offset で渡すと、xyz + R(quat) @ offset が刻みの半分以内で戻る。
* T の不一致(xyz / quat / series / panes / 軌跡)、NaN、範囲外の索引、未知の色指定、未知の鍵、
  範囲外の段の時刻・雲のコマ、存在しない物体の名指しは ValueError(黙って通さない)。
* PNG は画素ごとに無損失で、外部の復号器(Pillow があれば)とも一致する。frames の png=True も同じ。
* ページの JS が構文として正しい(node があれば)、外部 URL が無い、公開の入口から呼べる。
* 物体の alpha(2026-10-25): 0 < alpha <= 1 以外・NaN・bool・文字列は ValueError。alpha が 1 か無い場面の
  ページは前と同じ(半透明の塊は入らない)。半透明の物体は JSON に載り、不透明・軌跡・点群の後に描く。
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pocviewer as pv  # noqa: E402

RNG = np.random.default_rng(1024)


def _tx(label: str) -> dict:
    return {l: "%s-%s" % (label, l) for l in pv.LANGS}


def _cube(s=0.5):
    c = np.array([[x, y, z] for x in (-s, s) for y in (-s, s) for z in (-s, s)])
    tri = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                    [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return c, tri


def _rand_quat(shape):
    q = RNG.normal(size=shape + (4,))
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


T, BN = 12, 3


def _tab(**over):
    pos, tri = _cube()
    t = np.cumsum(RNG.uniform(0.02, 0.06, T))                       # 等間隔でない時刻
    xyz = RNG.uniform([-1, -2, 0], [1, 2, 0.5], (T, BN, 3))
    quat = _rand_quat((T, BN)) * RNG.choice([-3.0, 0.5, 2.0], (T, BN, 1))   # 正規化されていない・符号ばらばら
    d = dict(
        t=t, xyz=xyz, quat=quat,
        bodies=[{"name": "a", "pos": pos, "faces": tri, "rgb": [255, 128, 0]},
                {"name": "b", "pos": pos * 2, "faces": tri, "rgb": RNG.integers(0, 256, (8, 3), dtype=np.uint8)},
                {"name": "c", "pos": pos, "faces": tri, "val": RNG.uniform(-1, 1, 8), "label": _tx("c")}],
        cbar={"lo": -1, "hi": 1, "unit": "mm"},
        trails=[{"body": "a", "offset": [0.3, -0.2, 0.1], "color": "#ffd54f", "tail": 0.1, "label": _tx("tr")},
                {"xyz": RNG.uniform(0, 1, (T, 3)), "color": "#4dd0e1"}],
        clouds=[{"k": 0, "pos": RNG.uniform(0, 1, (30, 3))},
                {"k": 5, "pos": RNG.uniform(0, 1, (20, 3)), "rgb": RNG.integers(0, 256, (20, 3), dtype=np.uint8),
                 "point_size": 0.01}],
        events=[{"t": float(t[7]) - 1e-12, "label": _tx("e2")}, {"t": float(t[0]), "label": _tx("e1")}],
        series=[{"label": _tx("s"), "values": RNG.uniform(0, 1, T), "lo": 0, "hi": 1}],
        panes=[{"label": _tx("p"), "frames": RNG.integers(0, 256, (T, 9, 13), dtype=np.uint8),
                "boxes": [{"label": _tx("bx"), "xy": RNG.uniform(0, 9, (T, 2)), "size": [3, 3]}]},
               {"label": _tx("q"), "frames": RNG.integers(0, 256, (T, 7, 5, 3), dtype=np.uint8), "png": False}],
        follow="b")
    d.update(over)
    return pv.viewer_anim3d_tab("an", _tx("an"), "passed", _tx("txt"), **d)


def _spec(tabs):
    return pv.viewer_spec("anim", _tx("title"), _tx("sub"), _tx("hint"), tabs)


def _data(html: str) -> dict:
    m = re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S)
    assert m, "DATA が見つからない"
    return json.loads(m.group(1))


def _canon(q):
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    s = np.sign(q[..., 0])
    for k in (1, 2, 3):
        s = np.where(s == 0, np.sign(q[..., k]), s)
    return q * s[..., None]


def _angle(p, q):
    """回転の差 [rad]。acos を使わない(1 付近で丸めの床)。"""
    p = p / np.linalg.norm(p, axis=-1, keepdims=True)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    q = q * np.where((p * q).sum(-1) < 0, -1.0, 1.0)[..., None]
    return 4 * np.arctan2(np.linalg.norm(p - q, axis=-1), np.linalg.norm(p + q, axis=-1))


# --------------------------------------------------------------------------- 往復
def test_poses_round_trip_within_half_a_step():
    tab = _tab()
    d = _data(pv._build_html(_spec([tab]), ["ja", "en"]))
    tb, A = d["tabs"][0], d["arrays"]
    rx, rq = A[tb["xyz"]], A[tb["quat"]]
    assert rx["t"] == "q16" and rq["t"] == "s16"
    bx, bq = pv._decode_array(rx), pv._decode_array(rq)
    assert bx.shape == (T, BN, 3) and bq.shape == (T, BN, 4)
    assert (np.abs(bx - tab["xyz"]) <= pv._quant_step(rx) / 2 + 1e-12).all()
    want = _canon(tab["quat"])
    assert (np.abs(bq - want) <= pv._quant_step(rq)[0] / 2 + 1e-12).all()
    assert _angle(bq, want).max() < 1e-4
    assert (bq[..., 0] >= 0).all()                                   # 符号を揃えた(w >= 0)
    # 時刻は量子化しない(q16 にしない)。埋めるのは有効 STABLE_DIGITS 桁(BLAS・OS で変わる末尾の桁を落とす)
    assert tb["t"] == [float(v) for v in pv._round_sig(np.asarray(tab["t"], float))]
    assert np.allclose(tb["t"], tab["t"], rtol=5e-9, atol=0.0)     # 9 桁の丸めの誤差の上限 0.5e-8(先頭の桁が 1 のとき)


def test_quaternion_sign_and_scale_do_not_change_the_encoding():
    tab = _tab()
    flipped = dict(tab, quat=-2.5 * np.asarray(tab["quat"]))
    a = _data(pv._build_html(_spec([tab]), "ja"))
    b = _data(pv._build_html(_spec([flipped]), "ja"))
    assert a["arrays"][a["tabs"][0]["quat"]]["b64"] == b["arrays"][b["tabs"][0]["quat"]]["b64"]


def test_meshes_are_stored_once_and_shared_between_bodies():
    d1 = _data(pv._build_html(_spec([_tab()]), "ja"))
    by = d1["tabs"][0]["bodies"]
    assert by[0]["pos"] == by[2]["pos"] and by[0]["faces"] == by[1]["faces"]     # 同じ配列は 1 本
    assert by[0]["pos"] != by[1]["pos"]
    assert by[0]["rgb1"] == [255, 128, 0] and "rgb" in by[1] and "val" in by[2]
    rec = d1["arrays"][by[1]["pos"]]
    assert rec["shape"] == [8, 3]                                    # コマ数に比例しない


def test_trail_from_body_and_offset_is_the_moving_point():
    tab = _tab()
    d = _data(pv._build_html(_spec([tab]), "ja"))
    rec = d["arrays"][d["tabs"][0]["trails"][0]["xyz"]]
    q = _canon(tab["quat"])[:, 0]
    want = tab["xyz"][:, 0] + np.einsum("tij,j->ti", pv._quat_matrix(q), [0.3, -0.2, 0.1])
    assert (np.abs(pv._decode_array(rec) - want) <= pv._quant_step(rec) / 2 + 1e-12).all()
    tr = d["tabs"][0]["trails"]
    assert tr[0]["tail"] == 0.1 and tr[1]["tail"] == 0.0 and tr[0]["label"] == {"ja": "tr-ja"}


def test_quat_matrix_is_a_rotation_and_matches_the_axis_angle_formula():
    q = _canon(_rand_quat((50,)))
    R = pv._quat_matrix(q)
    assert np.allclose(np.einsum("nij,nkj->nik", R, R), np.eye(3), atol=1e-12)
    assert np.allclose(np.linalg.det(R), 1.0)
    a = 0.7                                                          # z 軸まわり 0.7 rad
    Rz = pv._quat_matrix(np.array([np.cos(a / 2), 0, 0, np.sin(a / 2)]))
    assert np.allclose(Rz, [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def test_events_are_sorted_and_mapped_to_frames():
    tab = _tab()
    d = _data(pv._build_html(_spec([tab]), "ja"))
    ev = d["tabs"][0]["events"]
    assert [e["k"] for e in ev] == [0, 7]                            # 時刻順に並べ替え、t[7] の直前 1e-12 は 7
    assert ev[0]["label"]["ja"] == "e1-ja"
    cl = d["tabs"][0]["clouds"]
    assert [c["k"] for c in cl] == [0, 5] and cl[0]["color"] == "#80cbc4" and "rgb" in cl[1]
    assert d["tabs"][0]["follow"] == 1


def test_panes_are_lossless_png_by_default_and_raw_when_asked():
    tab = _tab()
    d = _data(pv._build_html(_spec([tab]), "ja"))
    p0, p1 = d["tabs"][0]["panes"]
    r0, r1 = d["arrays"][p0["frames"]], d["arrays"][p1["frames"]]
    assert r0["t"] == "png" and len(r0["png"]) == T and r1["t"] == "u8"
    assert np.array_equal(pv._decode_array(r0), tab["panes"][0]["frames"])
    assert np.array_equal(pv._decode_array(r1), tab["panes"][1]["frames"])
    assert len(p0["boxes"]) == 1 and len(p0["boxes"][0]["xy"]) == T


# --------------------------------------------------------------------------- PNG
@pytest.mark.parametrize("shape", [(1, 1), (17, 23), (8, 5, 3), (31, 2, 3)])
def test_png_round_trip_is_exact(shape):
    noisy = RNG.integers(0, 256, shape, dtype=np.uint8)
    yy, xx = np.indices(shape[:2])
    smooth = ((xx * 7 + yy * 3) % 256).astype(np.uint8)
    if len(shape) == 3:
        smooth = np.stack([smooth, 255 - smooth, smooth // 2], -1)
    for img in (noisy, smooth):
        b = pv._png_encode(img)
        assert b[:8] == b"\x89PNG\r\n\x1a\n"
        assert np.array_equal(pv._png_decode(b), img)


def test_png_is_decoded_identically_by_an_independent_decoder():
    Image = pytest.importorskip("PIL.Image")
    yy, xx = np.indices((40, 60))
    for img in (((xx + yy) * 3 % 256).astype(np.uint8),
                np.stack([xx * 4 % 256, yy * 6 % 256, (xx * yy) % 256], -1).astype(np.uint8),
                RNG.integers(0, 256, (13, 11, 3), dtype=np.uint8)):
        got = np.asarray(Image.open(io.BytesIO(pv._png_encode(img))))
        assert got.dtype == np.uint8 and np.array_equal(got, img)


def test_png_shrinks_smooth_images_and_rejects_corruption():
    yy, xx = np.indices((96, 128))
    img = ((xx // 8 + yy // 8) % 2 * 200).astype(np.uint8)
    b = pv._png_encode(img)
    assert len(b) * 20 < img.nbytes
    bad = bytearray(b)
    bad[40] ^= 0xFF                                                  # IDAT の中身を壊す
    with pytest.raises(ValueError, match="CRC"):
        pv._png_decode(bytes(bad))
    with pytest.raises(ValueError):
        pv._png_encode(img.astype(np.float32))
    with pytest.raises(ValueError):
        pv._png_decode(b"not a png")


def test_frames_tab_png_option_is_lossless_and_off_by_default():
    fr = RNG.integers(0, 256, (4, 6, 7), dtype=np.uint8)
    on = pv.viewer_frames_tab("f", _tx("f"), "null", _tx("t"), fr, png=True)
    off = pv.viewer_frames_tab("g", _tx("g"), "null", _tx("t"), fr)
    assert "png" not in off                                          # 既定の出力は今までと同じ
    d = _data(pv._build_html(_spec([on, off]), "ja"))
    ra, rb = d["arrays"][d["tabs"][0]["frames"]], d["arrays"][d["tabs"][1]["frames"]]
    assert ra["t"] == "png" and rb["t"] == "u8"
    assert np.array_equal(pv._decode_array(ra), fr) and np.array_equal(pv._decode_array(rb), fr)


def test_s16_encoding_bounds():
    x = np.array([-1.0, -0.5, 0.0, 1e-6, 0.999999, 1.0])
    rec = pv._encode_array(x, "s16")
    assert (np.abs(pv._decode_array(rec) - x) <= pv._quant_step(rec)[0] / 2 + 1e-15).all()
    with pytest.raises(ValueError):
        pv._encode_array([1.5], "s16")
    with pytest.raises(ValueError, match="NaN"):
        pv._encode_array([np.nan], "s16")


# --------------------------------------------------------------------------- fail-closed
def _bad(**over):
    with pytest.raises(ValueError) as ei:
        pv._build_html(_spec([_tab(**over)]), "ja")
    return str(ei.value)


def test_rejects_broken_poses():
    tab = _tab()
    x = np.array(tab["xyz"])
    x[3, 1, 2] = np.nan
    assert "NaN" in _bad(xyz=x)
    x = np.array(tab["xyz"])
    x[2, 0, 0] = np.inf
    assert "NaN" in _bad(xyz=x)
    q = np.array(tab["quat"])
    q[4, 2] = 0.0
    assert "ノルムが 0" in _bad(quat=q) and "(4, 2)" in _bad(quat=q)
    q = np.array(tab["quat"])
    q[0, 0, 1] = np.nan
    assert "NaN" in _bad(quat=q)
    assert "T の不一致" in _bad(xyz=np.asarray(tab["xyz"])[:-1])
    assert "T の不一致" in _bad(quat=np.asarray(tab["quat"])[:, :2])
    assert "狭義の増加" in _bad(t=np.r_[tab["t"][:3], tab["t"][2], tab["t"][4:]])


def test_rejects_t_mismatch_in_series_panes_and_trails():
    tab = _tab()
    assert "series" in _bad(series=[dict(tab["series"][0], values=np.zeros(T - 1))])
    p = dict(tab["panes"][0], frames=np.zeros((T + 1, 4, 4), np.uint8))
    assert "T の不一致" in _bad(panes=[p])
    p = dict(tab["panes"][0], boxes=[dict(tab["panes"][0]["boxes"][0], xy=np.zeros((T - 2, 2)))])
    assert "xy" in _bad(panes=[p])
    assert "T の不一致" in _bad(trails=[{"xyz": np.zeros((T + 3, 3)), "color": "#ffffff"}])


def test_rejects_unknown_colours_keys_and_indices():
    tab = _tab()
    b0 = tab["bodies"][0]
    assert "未知の鍵" in _bad(bodies=[dict(b0, color="red")] + tab["bodies"][1:])
    nob = {k: v for k, v in b0.items() if k != "rgb"}
    assert "rgb か val" in _bad(bodies=[nob] + tab["bodies"][1:])
    assert "rgb か val" in _bad(bodies=[dict(b0, val=np.zeros(8))] + tab["bodies"][1:])
    assert "(3,) か (N,3)" in _bad(bodies=[dict(b0, rgb=[1, 2])] + tab["bodies"][1:])
    assert "0..255" in _bad(bodies=[dict(b0, rgb=[1, 2, 300])] + tab["bodies"][1:])
    assert "範囲外" in _bad(bodies=[dict(b0, faces=[[0, 1, 8]])] + tab["bodies"][1:])
    assert "範囲外" in _bad(bodies=[dict(b0, faces=[[0, -1, 2]])] + tab["bodies"][1:])
    assert "整数でない" in _bad(bodies=[dict(b0, faces=[[0, 1, 2.5]])] + tab["bodies"][1:])
    assert "重複" in _bad(bodies=[b0, dict(b0)] + tab["bodies"][2:])
    assert "cbar" in _bad(cbar=None)
    assert "#rrggbb" in _bad(trails=[dict(tab["trails"][0], color="yellow")])
    assert "#rrggbb" in _bad(clouds=[dict(tab["clouds"][0], color="#12345")])
    assert "片方だけ" in _bad(clouds=[dict(tab["clouds"][1], color="#123456")])
    assert "未知の鍵" in _bad(trails=[dict(tab["trails"][0], width=3)])
    assert "未知の鍵" in _bad(panes=[dict(tab["panes"][0], cmap="jet")])
    assert "bodies に無い" in _bad(trails=[dict(tab["trails"][0], body="zz")])
    assert "bodies に無い" in _bad(follow="zz")
    assert "どちらか 1 つ" in _bad(trails=[dict(tab["trails"][0], xyz=np.zeros((T, 3)))])
    assert "bodies が空" in _bad(bodies=[])


def test_rejects_out_of_range_events_and_clouds():
    tab = _tab()
    assert "範囲" in _bad(events=[{"t": float(tab["t"][-1]) + 1.0, "label": _tx("x")}])
    assert "範囲" in _bad(events=[{"t": float(tab["t"][0]) - 1.0, "label": _tx("x")}])
    assert "有限の数" in _bad(events=[{"t": None, "label": _tx("x")}])
    assert "コマの番号" in _bad(clouds=[{"k": T, "pos": np.zeros((2, 3))}])
    assert "コマの番号" in _bad(clouds=[{"k": 1.5, "pos": np.zeros((2, 3))}])
    assert "狭義の増加" in _bad(clouds=[{"k": 3, "pos": np.zeros((2, 3))}, {"k": 3, "pos": np.zeros((2, 3))}])


def test_missing_translation_in_anim3d_strings_is_named():
    tab = _tab()
    # 時刻の列は共有の乱数で _tab() のたびに変わる。段の時刻を取った列をそのまま渡す
    # (渡さないと 2 回目の列の範囲外になることがあり、実行順しだいで「範囲」の検査に先に落ちた)。
    ev = [{"t": float(tab["t"][1]), "label": {"ja": "だけ"}}]
    with pytest.raises(ValueError, match=r"events\[0\]\.label\.en"):
        pv._build_html(_spec([_tab(events=ev, t=tab["t"])]), ["ja", "en"])
    pv._build_html(_spec([_tab(events=ev, t=tab["t"])]), "ja")                    # 要求していない言語の欠けは問わない


# --------------------------------------------------------------------------- ページ
def test_page_has_the_controls_and_no_external_loads():
    html = pv._build_html(_spec([_tab()]), list(pv.LANGS))
    for sym in ("drawAnim", "sceneAnim", "followTick", "seekFrame", "pngImg", 'id="rate"', 'id="follow"',
                'value="0.25"', 'value="4"', 'id="evp"', 'id="b1"'):
        assert sym in html, sym
    assert "http://" not in html and "https://" not in html
    assert not re.search(r"@import|url\(|\bfetch\(|XMLHttpRequest|\bimport\(", html)


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_the_anim3d_page_script_is_valid_javascript(tmp_path):
    html = pv._build_html(_spec([_tab()]), ["ja", "en"])
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    f = tmp_path / "v.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_the_public_entry_points_expose_viewer_anim3d_tab():
    import api
    import fullseye as fs
    assert fs.viewer_anim3d_tab is pv.viewer_anim3d_tab is api.viewer_anim3d_tab
    assert "viewer_anim3d_tab" in pv.__all__ and "viewer_anim3d_tab" in fs.__all__
    assert "anim3d" in pv.KINDS
    doc = pv.viewer_anim3d_tab.__doc__
    assert "Examples" in doc and "(w, x, y, z)" in doc


def test_the_docstring_example_runs():
    import doctest
    finder, runner = doctest.DocTestFinder(), doctest.DocTestRunner(verbose=False)
    for t in finder.find(pv.viewer_anim3d_tab, "viewer_anim3d_tab", globs={}):
        runner.run(t)
    assert runner.failures == 0 and runner.tries >= 8, (runner.failures, runner.tries)


def test_mcp_tool_accepts_an_anim3d_spec_as_json():
    from fullseye.mcp import Catalog, call_tool
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import ArgError
    spec = json.loads(json.dumps(_spec([_tab()]), default=lambda o: o.tolist()))
    cat, store = Catalog.load(), HandleStore()
    r = call_tool("fullseye_write_viewer", {"spec": spec, "lang": ["ja", "en"]}, cat, store)
    assert r["isError"] is False
    d = _data(open(r["structuredContent"]["path"], encoding="utf-8").read())
    assert d["tabs"][0]["kind"] == "anim3d" and d["tabs"][0]["panes"][0]["boxes"]
    bad = json.loads(json.dumps(spec))
    bad["tabs"][0]["quat"][0][0] = [0, 0, 0, 0]                     # ノルム 0 は -32602
    with pytest.raises(ArgError, match="ノルムが 0"):
        call_tool("fullseye_write_viewer", {"spec": bad, "lang": ["ja"]}, cat, store)


# --------------------------------------------------------------------------- 半透明の物体(alpha)
def _with_alpha(alpha, j=0):
    d = _tab()
    d["bodies"] = [dict(b) for b in d["bodies"]]
    d["bodies"][j]["alpha"] = alpha
    return d


@pytest.mark.parametrize("bad", [0, 0.0, -0.1, 1.0000001, 2, float("nan"), float("inf"), np.nan,
                                 True, False, "0.3", None, [0.3], np.array([0.3])])
def test_alpha_out_of_range_nan_and_wrong_types_are_rejected(bad):
    with pytest.raises(ValueError, match="alpha"):
        pv._build_html(_spec([_with_alpha(bad)]), "ja")


@pytest.mark.parametrize("ok", [0.3, 1e-6, 1, 1.0, np.float32(0.25), np.int64(1)])
def test_alpha_accepts_numbers_in_the_open_closed_unit_interval(ok):
    d = _data(pv._build_html(_spec([_with_alpha(ok)]), "ja"))
    b = d["tabs"][0]["bodies"][0]
    if float(ok) < 1:
        assert b["alpha"] == pytest.approx(float(ok))
    else:
        assert "alpha" not in b                                     # 1 は既定: 載せない


def test_alpha_one_or_absent_leaves_the_page_byte_identical():
    """alpha を使わない場面は、alpha を足す前と同じページ(公開済みのビューアに drift を出さない)。

    差し込みの塊が入らないこと・本体の JS がそのまま入っていることも確かめる(=前と同じ JS)。
    """
    global RNG
    saved = RNG
    try:
        RNG = np.random.default_rng(7)
        plain = pv._build_html(_spec([_tab()]), ["ja", "en"])
        RNG = np.random.default_rng(7)
        one = pv._build_html(_spec([_with_alpha(1.0)]), ["ja", "en"])
    finally:
        RNG = saved
    assert plain == one
    assert "drawTranslucent" not in plain and "depthMask" not in plain and "u_eye" not in plain
    head = pv._JS.split("__DATA__")[0]
    assert head in plain and pv._JS.split("__DATA__")[1] in plain


def test_translucent_body_is_in_the_json_and_drawn_after_trails_and_clouds():
    html = pv._build_html(_spec([_with_alpha(0.3, j=1)]), ["ja", "en"])
    d = _data(html)
    assert [("alpha" in b) for b in d["tabs"][0]["bodies"]] == [False, True, False]
    assert d["tabs"][0]["bodies"][1]["alpha"] == pytest.approx(0.3)
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    assert js.count(pv._JS_ALPHA) == 1
    # 差し込みは drawAnim の定義の後・2-D の前(drawAnim を包むので、定義より後でなければならない)
    assert js.index("function drawAnim(tab)") < js.index("const drawAnimOpaque = drawAnim;") < js.index(pv._JS_ALPHA_ANCHOR)
    # 不透明のパス(不透明の物体 → 軌跡 → 点群)の後に半透明を描く
    body = js[js.index("drawAnim = function(tab)"):js.index("function drawTranslucent")]
    assert body.index("drawAnimOpaque(tab)") < body.index("drawTranslucent(tab, S, L)")
    op = js[js.index("function drawAnim(tab)"):js.index("/* 同じ時間軸の 2-D")]
    assert op.index("/* 物体 */") < op.index("/* 軌跡") < op.index("/* 点群")
    tr = js[js.index("function drawTranslucent"):]
    for sym in ("gl.enable(gl.BLEND)", "gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)", "gl.depthMask(false)",
                "gl.enable(gl.DEPTH_TEST)", "gl.enable(gl.CULL_FACE)", ".sort((p, q) => q.d - p.d)",
                "[gl.FRONT, gl.BACK]", "gl.depthMask(true)", "gl.disable(gl.BLEND)", "gl.disable(gl.CULL_FACE)",
                "gl.uniform1f(ua, it.e.a)"):
        assert sym in tr, sym
    assert tr.index("gl.depthMask(false)") < tr.index("gl.drawElements") < tr.index("gl.depthMask(true)")
    assert "uniform float u_a" in js and "uniform vec3 u_eye" in js


def test_translucent_camera_matches_drawanim():
    """半透明のパスは drawAnim と同じカメラで描く(式が食い違うと重ねた物体がずれる)。"""
    op = pv._JS[pv._JS.index("function drawAnim(tab)"):pv._JS.index("/* 同じ時間軸の 2-D")]
    tr = pv._JS_ALPHA[pv._JS_ALPHA.index("function drawTranslucent"):]
    for line in ("const tg = $('follow').checked ? S.tgt : S.ctr;",
                 "const cd = Math.cos(el), sd = Math.sin(el), ca = Math.cos(az), sa = Math.sin(az);",
                 "const eye = [tg[0] + dist*cd*ca, tg[1] + dist*cd*sa, tg[2] + dist*sd];",
                 "const fy = 0.9, vp = mul(persp(fy, cv.width/cv.height, S.rad*0.02, S.rad*40), look(eye, tg, [0,0,1]));",
                 "let l = [ca*cd*0.5, sa*cd*0.5, sd*0.5 + 0.5]; const ll = Math.hypot(l[0], l[1], l[2]); l = l.map(v => v/ll);"):
        assert line in op and line in tr, line


@pytest.mark.skipif(shutil.which("node") is None, reason="node が無い")
def test_the_translucent_page_script_is_valid_javascript(tmp_path):
    html = pv._build_html(_spec([_with_alpha(0.3)]), ["ja", "en"])
    js = re.search(r"<script>(.*)</script>", html, re.S).group(1)
    f = tmp_path / "v.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr


def test_alpha_is_documented():
    doc = pv.viewer_anim3d_tab.__doc__
    assert '"alpha"' in doc and "0 < alpha <= 1" in doc


# ----------------------------- placed last: they use the shared RNG, the earlier tests depend on its order
def test_identical_pane_frames_are_stored_once_and_indexed():
    """A sensor that only changes at a scan: each distinct frame is stored once, the index restores all T."""
    tab = _tab()
    a, b = (RNG.integers(0, 256, (9, 13, 3), dtype=np.uint8) for _ in range(2))
    seq = np.stack([a if k < 4 else b for k in range(T)])
    seq[T - 1] = a                                                   # an earlier picture coming back
    tab["panes"] = [{"label": _tx("cam"), "frames": seq}, {"label": _tx("off"), "frames": seq, "dedupe": False}]
    d = _data(pv._build_html(_spec([tab]), "ja"))
    p0, p1 = d["tabs"][0]["panes"]
    stored = pv._decode_array(d["arrays"][p0["frames"]])
    assert len(stored) == 2 and len(p0["index"]) == T
    assert np.array_equal(stored[np.asarray(p0["index"])], seq)       # lossless, frame by frame
    assert "index" not in p1 and len(pv._decode_array(d["arrays"][p1["frames"]])) == T


def test_view_target_and_wide_pane_pass_through():
    """view.target (look at the work area) and pane wide (a row of its own) reach the page; bad target refused."""
    tab = _tab()
    tab["view"] = {"az": 0.6, "el": 0.5, "dist": 0.4, "target": [0.1, -0.2, 0.3]}
    tab["panes"] = [dict(tab["panes"][0], wide=True), tab["panes"][1]]
    html = pv._build_html(_spec([tab]), "ja")
    d = _data(html)
    assert d["tabs"][0]["view"]["target"] == [0.1, -0.2, 0.3] and d["tabs"][0]["view"]["dist"] == 0.4
    assert d["tabs"][0]["panes"][0]["wide"] is True and "wide" not in d["tabs"][0]["panes"][1]
    assert "tab.view.target" in html and ".pane.wide" in html
    tab["view"] = {"target": [0.0, 1.0]}
    with pytest.raises(ValueError):
        pv._build_html(_spec([tab]), "ja")
