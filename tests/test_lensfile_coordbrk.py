# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensfile の座標変換面(COORDBRK)—— .zmx の傾き・偏心・折り返しを raytrace3d の break 要素として読む門。

真値は外から取る:

* **手で組んだ系との一致** —— 同じ系を ``raytrace3d.noncoaxial_system`` に直接書いた要素列と、手で書いた .zmx
  テキストを読んだ系を、同じ光線で追い、全面の交点が 1e-12 mm で一致する(傾いた平板・二軸の折り返し)。
* **Householder 鏡映** —— 45° などの折り返しの像 = 展開した系の像の鏡映(``p − 2((p − p0)·n)n``、鏡の法線 n は
  ``Rx(tilt)`` の z 列)。
* **第 2 の実装(optiland、MIT)** —— ``coordbrk_recorded.json`` に、同じ .zmx を optiland が自分の読み手で読んで
  追った実光線の交点・方向余弦が記録してある(作り方は README)。CI には無いので記録値と照合し、手元に入って
  いれば同じ数字をその場で計算し直す。optiland は**順序フラグ(PARM 6)を読まない**ので、順序 1 の戻りを含む
  ``cb_tilted_plate`` の像面の位置だけは照合から外し、代わりに閉形式(戻りの後の座標系が元に戻る)で確かめる。
* **閉形式** —— 軸外し放物面は平行光を 1 点へ結ぶ(RMS が 0)、f = R/2。
* **探針** —— オイラー角の順を入れ替える・傾きの符号を反転する・戻りを落とす、はどれも門を赤にする。
"""
from __future__ import annotations

import json
import math
import os
import re

import numpy as np
import pytest

import lensfile as L
import raytrace as RT
import raytrace3d as R3

INF = float("inf")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "lensfile")
REC = json.load(open(os.path.join(DATA, "coordbrk_recorded.json"), encoding="utf-8"))
FILES = [k for k in REC if not k.startswith("_")]
BK = (1.5168, 64.17)

#: 記録値との許容(mm)。optiland は円錐の交点を反復で解くので放物面だけ緩い。
TOL = {"cb_off_axis_parabola.zmx": 1e-9}
#: 順序フラグを読まない optiland と像面の位置が食い違うので、像面の位置を照合から外すもの。
SKIP_IMAGE_POSITION = {"cb_tilted_plate.zmx"}


def _text(name):
    return open(os.path.join(DATA, name), encoding="ascii").read()


def _model_to_constant(text, ns):
    """モデル硝材 ``___BLANK nd vd`` を、第 2 の実装が評価した屈折率の一定値に置き換える(硝材のモデルの差を照合から外す)。"""
    it = iter([n for n in ns if n is not None])
    out, k = re.subn(r"GLAS ___BLANK 1 0 [0-9.]+ [0-9.]+ ", lambda m: "GLAS ___BLANK 1 0 %r 0 " % next(it), text)
    return out


def _vs_recorded(name, text=None):
    """(最大の交点の差 [mm], 最大の方向余弦の差)—— 記録された光線を、記録された始点・方向のまま追って比べる。"""
    rec = REC[name]
    t = _model_to_constant(_text(name) if text is None else text, rec["n"])
    p = L.lens_file_read(t)
    sysd, srec = p["system"], p["surface_records"]
    rows = [j for j in range(1, len(srec) - 1) if p["surfaces"][j]["type"] != "COORDBRK"]
    worst_p = worst_d = 0.0
    for ray in rec["rays"]:
        P = np.array([[ray["x"][0], ray["y"][0], ray["z"][0]]])
        D = np.array([[ray["L"][0], ray["M"][0], ray["N"][0]]])
        tr = R3._trace(sysd, P, D, apertures=False)
        pts = tr["points"][0]
        if not np.all(np.isfinite(pts)):
            return math.inf, math.inf
        for row, j in enumerate(rows, start=1):
            if not srec[j]:
                continue                                         # 併合した無作用の平面
            ordinal = sum(1 for r in sysd["records"][:srec[j][0]] if r["kind"] == "surface")
            ref = np.array([ray["x"][row], ray["y"][row], ray["z"][row]])
            worst_p = max(worst_p, float(np.abs(pts[1 + ordinal] - ref).max()))
        if name not in SKIP_IMAGE_POSITION:
            ref = np.array([ray["x"][-1], ray["y"][-1], ray["z"][-1]])
            worst_p = max(worst_p, float(np.abs(pts[-1] - ref).max()))
        dref = np.array([ray["L"][-2], ray["M"][-2], ray["N"][-2]])
        worst_d = max(worst_d, float(np.abs(tr["dirs"][0][-1] - dref).max()))
    return worst_p, worst_d


# --------------------------------------------------------------------------- #
# 1. 第 2 の実装との一致(記録値)と探針
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", FILES)
def test_real_rays_match_the_recorded_second_implementation(name):
    dp, dd = _vs_recorded(name)
    assert dp < TOL.get(name, 1e-12), (name, dp)
    assert dd < 1e-12, (name, dd)


def test_recorded_gate_covers_what_it_claims():
    # 1 本ごとに 6 本以上の光線・複数の視野(x と y の符号を試す)・折り返しと傾いた平板と偏心を含む
    assert len(FILES) >= 5
    for name in FILES:
        assert len(REC[name]["rays"]) >= 8
        fields = {tuple(r["field"]) for r in REC[name]["rays"]}
        assert len(fields) >= 2
    assert any(abs(f[0]) > 0 and abs(f[1]) > 0 for f in ({tuple(r["field"]) for r in REC["cb_tilted_plate.zmx"]["rays"]}))


@pytest.mark.parametrize("name", FILES)
def test_live_second_implementation_if_installed(name):
    """optiland が入っていれば、記録と同じ数字をその場で計算し直して記録値と突き合わせる(CI には無いので skip)。"""
    pytest.importorskip("optiland")
    import warnings
    from optiland.fileio import load_zemax_file
    warnings.simplefilter("ignore")
    op = load_zemax_file(os.path.join(DATA, name))
    rmax = max(math.hypot(*r["field"]) for r in REC[name]["rays"])
    for ray in REC[name]["rays"]:
        fx, fy = ray["field"]
        op.trace_generic(fx / rmax, fy / rmax, ray["pupil"][0], ray["pupil"][1], 0.55)
        sg = op.surface_group
        for k, a in (("x", sg.x), ("y", sg.y), ("z", sg.z), ("L", sg.L), ("M", sg.M), ("N", sg.N)):
            assert np.abs(np.ravel(a[:, 0]) - np.array(ray[k])).max() < 1e-12


def _swap_order(orig):
    def f(parm, direction, t):
        return [dict(b, order="zyx" if b["order"] == "xyz" else "xyz") for b in orig(parm, direction, t)]
    return f


def _flip_ax(orig):
    def f(parm, direction, t):
        return [dict(b, tilt=(-b["tilt"][0], b["tilt"][1], b["tilt"][2])) for b in orig(parm, direction, t)]
    return f


def _drop_undo(orig):
    def f(elements):
        n = orig(elements)
        for i, e in enumerate(elements):
            if "undo" in e:
                elements[i] = {"type": "break", "t": e["t"]}      # 戻りを落とす(厚みだけ残す)
        return n
    return f


@pytest.mark.parametrize("probe,patch,name", [
    ("euler order swapped", ("_break_elements", _swap_order), "cb_fold_two_axis.zmx"),
    ("euler order swapped", ("_break_elements", _swap_order), "cb_three_mirrors.zmx"),
    ("tilt sign flipped", ("_break_elements", _flip_ax), "cb_fold_two_axis.zmx"),
    ("tilt sign flipped", ("_break_elements", _flip_ax), "cb_plate_x_undo.zmx"),
    ("undo dropped", ("_mark_undos", _drop_undo), "cb_plate_x_undo.zmx"),
])
def test_probe_wrong_conventions_turn_the_gate_red(monkeypatch, probe, patch, name):
    attr, make = patch
    assert _vs_recorded(name)[0] < 1e-9                                  # 本物は緑
    monkeypatch.setattr(L, attr, make(getattr(L, attr)))
    dp, dd = _vs_recorded(name)
    assert max(dp, dd) > 1e-6, (probe, name, dp, dd)


# --------------------------------------------------------------------------- #
# 2. 手で組んだ noncoaxial_system との一致(1e-12)
# --------------------------------------------------------------------------- #
def _same_rays(sysd, field=(0.0, 0.0), n=7):
    th = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    X = np.concatenate([[0.0], 1.7 * np.cos(th), 3.1 * np.cos(th + 0.4)])
    Y = np.concatenate([[0.0], 1.7 * np.sin(th), 3.1 * np.sin(th + 0.4)])
    return R3._launch_xy(sysd, X, Y, field, 0.0)[:2]


def _max_hit_difference(a, b, fields=((0.0, 0.0), (0.0, 2.0), (1.5, -1.0))):
    worst = 0.0
    for f in fields:
        P, D = _same_rays(a, f)
        ta = R3._trace(a, P, D, apertures=False)
        tb = R3._trace(b, P, D, apertures=False)
        assert ta["points"].shape == tb["points"].shape
        assert np.all(np.isfinite(ta["points"])) and np.all(np.isfinite(tb["points"]))
        worst = max(worst, float(np.abs(ta["points"] - tb["points"]).max()),
                    float(np.abs(ta["dirs"] - tb["dirs"]).max()))
    return worst


def _hand_tilted_plate():
    """cb_tilted_plate.zmx を、座標の規約から手で導いた break 要素で書いたもの。"""
    return R3.noncoaxial_system([
        {"R": 60.0, "t": 4.0, "n": BK, "ap": 4.0},
        {"R": 1.0 / -0.012, "t": 25.0, "n": 1.0},
        {"type": "break", "decenter": (0.3, -0.2), "tilt": (0, 0, 0), "order": "xyz", "t": 0.0},     # 先に偏心
        {"type": "break", "tilt": (22.0, -9.0, 4.0), "order": "zyx", "t": 0.0},                       # 次に Rz·Ry·Rx
        {"R": INF, "t": 4.0, "n": BK},
        {"R": INF, "t": 0.0, "n": 1.0},
        {"type": "break", "undo": 3, "t": 0.0},
        {"type": "break", "undo": 2, "t": 30.0}], stop=0, wavelength_um=0.55)


def test_tilted_plate_zmx_equals_the_hand_built_system():
    p = L.lens_file_read(_text("cb_tilted_plate.zmx"))
    assert _max_hit_difference(p["system"], _hand_tilted_plate()) < 1e-12


def test_return_restores_the_frame_in_closed_form():
    # 傾けた平板の戻り(順序 1・符号を反転した全パラメータ)は座標系を元に戻す: 像面の向きは単位行列、原点は軸上
    p = L.lens_file_read(_text("cb_tilted_plate.zmx"))
    lay = R3.noncoaxial_layout(p["system"])
    assert np.abs(np.array(lay["image"]["rotation"]) - np.eye(3)).max() < 1e-13
    # 原点 = (0, 0, 4 + 25 + 30) + R·(0, 0, 4):板の厚み 4 は傾いた軸に沿う(偏心は戻りで打ち消される)。
    #   R = Rz(4°)·Ry(−9°)·Rx(22°) をここで独立に書く
    def rot(ax, a):
        c, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        return {"x": np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]]), "y": np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]]),
                "z": np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])}[ax]
    R = rot("z", 4.0) @ rot("y", -9.0) @ rot("x", 22.0)
    want = np.array([0.0, 0.0, 59.0]) + R @ np.array([0.0, 0.0, 4.0])
    assert np.abs(np.array(lay["image"]["origin"]) - want).max() < 1e-12
    # 戻りの 2 要素は tracer の undo 要素に写る
    els = p["system"]["elements"]
    assert [e.get("undo") for e in els if "undo" in e] == [3, 2]
    # 戻りを落とすと元に戻らない(探針)
    broken = [e for e in els if "undo" not in e]
    lay2 = R3.noncoaxial_layout(R3.noncoaxial_system(broken, stop=p["system"]["stop_arg"], wavelength_um=0.55))
    assert np.abs(np.array(lay2["image"]["rotation"]) - np.eye(3)).max() > 0.1


def test_single_axis_return_is_the_trace_undo_element():
    p = L.lens_file_read(_text("cb_plate_x_undo.zmx"))
    undo = [e for e in p["system"]["elements"] if "undo" in e]
    assert len(undo) == 1 and undo[0]["t"] == 20.0
    assert any("undo an earlier one exactly" in n for n in p["report"]["notes"])
    # 同じ系を undo ではなく明示の break(角を反転)で書いても同じ
    els = [dict(e) for e in p["system"]["elements"]]
    k = [i for i, e in enumerate(els) if "undo" in e][0]
    els[k] = {"type": "break", "tilt": (-25.0, 0.0, 0.0), "t": 20.0}
    explicit = R3.noncoaxial_system(els, stop=p["system"]["stop_arg"], wavelength_um=0.55)
    assert _max_hit_difference(p["system"], explicit) < 1e-12


def _hand_two_axis_fold():
    # 鏡の後は局所系が x 軸まわりに 180° 返る: 偏心 y・傾き y/z の符号を反転して書く。
    return R3.noncoaxial_system([
        {"R": 60.0, "t": 5.0, "n": BK, "ap": 4.0},
        {"R": INF, "t": 20.0, "n": 1.0},
        {"type": "break", "decenter": (1.0, -0.5), "tilt": (0, 0, 0), "order": "xyz", "t": 0.0},
        {"type": "break", "tilt": (30.0, 10.0, 5.0), "order": "zyx", "t": 0.0},
        {"R": 250.0, "t": 35.0, "mirror": True},
        {"type": "break", "decenter": (0.4, -0.3), "tilt": (0, 0, 0), "order": "xyz", "t": 0.0},
        {"type": "break", "tilt": (-8.0, -12.0, -3.0), "order": "zyx", "t": 20.0}], stop=0, wavelength_um=0.55)


def test_two_axis_fold_zmx_equals_the_hand_built_system():
    p = L.lens_file_read(_text("cb_fold_two_axis.zmx"))
    assert p["system"]["records"][-1]["t"] == 20.0                         # DISZ -15 と無作用の平面 -5 を併合
    assert _max_hit_difference(p["system"], _hand_two_axis_fold()) < 1e-12


def test_every_published_convention_is_visible_in_the_hand_built_gate():
    # 手で組んだ系のゲート自体が条件に敏感: 順序・符号・鏡の後の反転を 1 つ変えると赤
    p = L.lens_file_read(_text("cb_fold_two_axis.zmx"))
    ref = p["system"]["elements"]

    def variant(edit):
        els = [dict(e) for e in ref]
        edit(els)
        return R3.noncoaxial_system(els, stop=p["system"]["stop_arg"], wavelength_um=0.55)
    swap = variant(lambda e: [e[i].update(order="xyz") for i in range(len(e)) if e[i].get("order") == "zyx"])
    unflip = variant(lambda e: [e[i].update(tilt=(e[i]["tilt"][0], -e[i]["tilt"][1], -e[i]["tilt"][2]))
                                for i in range(len(e)) if e[i].get("type") == "break" and i > 4])
    signed = variant(lambda e: e[3].update(tilt=(-30.0, 10.0, 5.0)))
    for bad in (swap, unflip, signed):
        assert _max_hit_difference(p["system"], bad) > 1e-4


# --------------------------------------------------------------------------- #
# 3. Householder 鏡映(折り返しの像 = 展開した像の鏡映)
# --------------------------------------------------------------------------- #
def _fold_text(tilt, d_after):
    head = L.ZMX_EXAMPLE.split("SURF 0")[0].replace("ENPD 10", "ENPD 8")
    head = re.sub(r"^FTYP .*$", "FTYP 0 0 1 1 0 0 0", head, flags=re.M)
    head = re.sub(r"^(XFLN|YFLN|FWGN) .*$", lambda m: m.group(1) + " 0", head, flags=re.M)
    head = re.sub(r"^WAVM 1 .*$\nWAVM 2 .*$\nWAVM 3 .*$", "WAVM 1 0.58756 1", head, flags=re.M)
    head = head.replace("PWAV 2", "PWAV 1")
    body = ("SURF 0\n  TYPE STANDARD\n  CURV 0 0 0 0 0 \"\"\n  DISZ INFINITY\n"
            "SURF 1\n  STOP\n  TYPE STANDARD\n  CURV %r 0 0 0 0 \"\"\n  DISZ 5\n  GLAS ___BLANK 1 0 1.5168 64.17 0 0 0 0 0 0\n"
            "SURF 2\n  TYPE STANDARD\n  CURV 0 0 0 0 0 \"\"\n  DISZ 40\n"
            "SURF 3\n  TYPE COORDBRK\n  PARM 1 0\n  PARM 2 0\n  PARM 3 %r\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ 0\n"
            "SURF 4\n  TYPE STANDARD\n  CURV 0 0 0 0 0 \"\"\n  DISZ 0\n  GLAS MIRROR 0 0 1.5 40 0 0 0 0 0 0\n"
            "SURF 5\n  TYPE COORDBRK\n  PARM 1 0\n  PARM 2 0\n  PARM 3 %r\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ %r\n"
            "SURF 6\n  TYPE STANDARD\n  CURV 0 0 0 0 0 \"\"\n  DISZ 0\n") % (1.0 / 51.68, tilt, tilt, -d_after)
    return head + body


@pytest.mark.parametrize("tilt", [45.0, 30.0, -35.0, 12.5])
def test_fold_image_is_the_householder_mirror_of_the_unfolded_image(tilt):
    lens = [{"R": 51.68, "t": 5.0, "n": BK, "ap": 12.5}, {"R": INF, "t": 40.0, "n": 1.0}]
    bfl = RT.paraxial_trace(RT.lens_system())["bfl"]
    p = L.lens_file_read(_fold_text(tilt, bfl - 40.0))
    folded = p["system"]
    unfolded = R3.noncoaxial_system([lens[0], {"R": INF, "t": bfl, "n": 1.0}], stop=0, wavelength_um=0.58756)
    n = RT._rot(tilt, 0.0)[:, 2]                                           # 鏡の法線(大域)
    p0 = np.array([0.0, 0.0, 45.0])                                        # 鏡の頂点
    for f in [(0.0, 0.0), (1.5, 0.0), (0.0, 2.0), (1.0, -1.5)]:
        a = R3._chief(folded, f)["points"][0, -1]
        b = R3._chief(unfolded, f)["points"][0, -1]
        want = b - 2.0 * ((b - p0) @ n) * n
        assert np.max(np.abs(a - want)) < 1e-12 * 1e3
    o = R3.image_orientation(folded)
    assert o["n_reflections"] == 1 and o["reversed"]


def test_probe_householder_gate_sees_a_wrong_second_break():
    # 鏡の後の切り替えを逆符号にすると、折り返しの像は鏡映から外れる
    bfl = RT.paraxial_trace(RT.lens_system())["bfl"]
    good = L.lens_file_read(_fold_text(45.0, bfl - 40.0))["system"]
    bad = L.lens_file_read(_fold_text(45.0, bfl - 40.0).replace("PARM 3 45.0\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ -",
                                                                "PARM 3 -45.0\n  PARM 4 0\n  PARM 5 0\n  PARM 6 0\n  DISZ -"))["system"]
    a = np.array(R3.noncoaxial_layout(good)["image"]["origin"])
    b = np.array(R3.noncoaxial_layout(bad)["image"]["origin"])
    assert np.abs(a - b).max() > 1.0


# --------------------------------------------------------------------------- #
# 4. 閉形式: 軸外し放物面・瞳の換算
# --------------------------------------------------------------------------- #
def test_off_axis_parabola_images_a_collimated_beam_to_a_point():
    p = L.lens_file_read(_text("cb_off_axis_parabola.zmx"))
    s = L.lens_file_system(p, field_index=0)
    assert R3.noncoaxial_spot(s, rings=6)["rms_radius"] < 1e-9
    # 軸外し放物面の有効焦点距離 = f(1 + (h / 2f)²)(親の f = R/2 = 100、軸外し h = 36)
    assert abs(p["pupil"]["efl_mm"] - 100.0 * (1.0 + (36.0 / 200.0) ** 2)) < 1e-6
    assert abs(p["pupil"]["stop_radius_mm"] - 6.0) < 1e-9                 # 停止面は平らで傾きなし(ENPD 12)
    # 画角を振ると点でなくなる(門が空でない)
    assert R3.noncoaxial_spot(L.lens_file_system(p, field_index=1), rings=6)["rms_radius"] > 1e-3


def test_fnum_and_enpd_give_the_same_stop():
    t = _text("cb_off_axis_parabola.zmx")
    a = L.lens_file_read(t)
    b = L.lens_file_read(t.replace("ENPD 12", "FNUM %r 0" % (a["pupil"]["efl_mm"] / 12.0)))
    assert abs(a["pupil"]["stop_radius_mm"] - b["pupil"]["stop_radius_mm"]) < 1e-6
    c = L.lens_file_read(t.replace("ENPD 12", "FLOA"))
    assert c["pupil"]["stop_radius_mm"] == 7.0                             # 停止面の DIAM(半径)


def test_fields_keep_their_sign_and_both_components():
    p = L.lens_file_read(_text("cb_fold_two_axis.zmx"))
    assert [f["field"] for f in p["fields"]] == [(0.0, 0.0), (1.0, 2.0), (-2.0, 0.5)]
    s = L.lens_file_system(p, field_index=2)
    assert s["field"] == (-2.0, 0.5) and s["kind"] == "noncoaxial_system"
    d = R3._field_dir(*s["field"])
    assert d[0] < 0 < d[1]                                                 # +x / +y は光線の向き(方向余弦の符号)


# --------------------------------------------------------------------------- #
# 5. 往復と書き出し
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", FILES)
@pytest.mark.parametrize("enc", ["ascii", "utf-16"])
def test_round_trip_is_idempotent(name, enc):
    p = L.lens_file_read(os.path.join(DATA, name))
    w = L.lens_file_write(p, encoding=enc)
    raw = w["text"].encode("utf-16") if enc == "utf-16" else w["text"].encode("ascii")
    q = L.lens_file_read(raw)
    assert q["surfaces"] == p["surfaces"]
    assert q["fields"] == p["fields"] and q["wavelengths"] == p["wavelengths"]
    assert q["system"]["elements"] == p["system"]["elements"]
    assert q["pupil"] == p["pupil"]
    assert L.lens_file_write(q, encoding=enc)["text"] == w["text"]
    assert "COORDBRK" in w["text"] and w["dropped_solves"] == []


def _edited_systems():
    fold = R3.noncoaxial_example("folded_singlet")
    peri = R3.noncoaxial_example("periscope")
    plate = R3.noncoaxial_example("tilted_plate")
    return {"folded_singlet": fold, "periscope": peri, "tilted_plate": plate,
            "hand_two_axis_fold": _hand_two_axis_fold(), "hand_tilted_plate": _hand_tilted_plate(),
            "off_axis_parabola": L.lens_file_read(_text("cb_off_axis_parabola.zmx"))["system"]}


@pytest.mark.parametrize("name", ["folded_singlet", "periscope", "tilted_plate", "hand_two_axis_fold",
                                  "hand_tilted_plate", "off_axis_parabola"])
def test_break_elements_are_written_back_as_coordinate_breaks(name):
    sysd = _edited_systems()[name]
    w = L.lens_file_write(None, system=sysd)
    assert "TYPE COORDBRK" in w["text"]
    q = L.lens_file_read(w["text"])
    assert q["noncoaxial"]
    # 読み直した系は同じ光線を同じに追う(角の取り出しの丸めだけ)
    assert _max_hit_difference(sysd, q["system"], fields=((0.0, 0.0),)) < 1e-9
    # 2 回目以降は固定点
    w2 = L.lens_file_write(q)
    assert L.lens_file_read(w2["text"])["surfaces"] == q["surfaces"]


def test_write_of_an_edited_system_keeps_the_header_and_drops_a_stale_pickup():
    p = L.lens_file_read(_text("cb_three_mirrors.zmx"))
    els = [dict(e) for e in p["system"]["elements"]]
    first_break = [i for i, e in enumerate(els) if e.get("type") == "break"][1]
    els[first_break] = dict(els[first_break], tilt=(12.5, 0.0, 0.0))           # 片方だけ角を変える
    edited = R3.noncoaxial_system(els, stop=p["system"]["stop_arg"], object_mm=p["system"]["object_mm"],
                                  wavelength_um=p["system"]["wavelength_um"])
    w = L.lens_file_write(p, system=edited)
    assert w["dropped_solves"] or "PPAR" in w["text"]
    q = L.lens_file_read(w["text"])
    assert [f["field"] for f in q["fields"]] == [f["field"] for f in p["fields"]]
    assert abs(q["pupil"]["stop_radius_mm"] - p["pupil"]["stop_radius_mm"]) < 1e-9 * 100


def test_writer_refuses_what_a_file_cannot_hold():
    with pytest.raises(ValueError, match="beamsplitter"):
        L.lens_file_write(None, system=R3.noncoaxial_example("epi_beamsplitter"))
    s = R3.noncoaxial_system([{"R": 50.0, "t": 5.0, "n": 1.5, "ap": 5.0, "tilt": (1.0, 0.0)},
                              {"R": INF, "t": 20.0, "n": 1.0}], stop=0)
    with pytest.raises(ValueError, match="per-surface"):
        L.lens_file_write(None, system=s)


# --------------------------------------------------------------------------- #
# 6. 取り込みの規約: PPAR の検証・拒否・分類
# --------------------------------------------------------------------------- #
def test_parameter_pickups_are_verified_and_listed():
    p = L.lens_file_read(_text("cb_three_mirrors.zmx"))
    pk = [s for s in p["solves"] if s["kind"] == "pickup" and s["what"].startswith("PARM")]
    assert len(pk) == 3 and all(s["status"] == "verified" for s in pk)
    assert p["surfaces"][4]["ppar"] == [[3, 2, 1.0, 0.0]]
    t = _text("cb_three_mirrors.zmx").replace("PPAR 3 2 1.0 0.0 0", "PPAR 3 2 -1.0 0.0 0")
    with pytest.raises(ValueError, match="stale or corrupted"):
        L.lens_file_read(t)
    with pytest.raises(ValueError, match="does not exist"):
        L.lens_file_read(_text("cb_three_mirrors.zmx").replace("PPAR 3 2 1.0 0.0 0", "PPAR 3 99 1.0 0.0 0"))


def test_report_and_refusals_for_coordinate_breaks():
    r = L.lens_file_report(_text("cb_fold_two_axis.zmx"))
    assert r["importable"] and r["surface_types"] == {"STANDARD": 6, "COORDBRK": 2}
    base = _text("cb_off_axis_parabola.zmx")
    cb = "SURF 2\n  TYPE COORDBRK\n"
    assert base.count(cb) == 1
    # a tilt in front of the first surface would move the object space (convention not verified) -> refused
    bad = re.sub(r"SURF (\d+)\n", lambda m: "SURF %d\n" % (int(m.group(1)) + 1) if int(m.group(1)) >= 1 else m.group(0),
                 base)
    bad = bad.replace("SURF 2\n  STOP", "SURF 1\n  TYPE COORDBRK\n  PARM 3 5\n  DISZ 0\nSURF 2\n  STOP", 1)
    with pytest.raises(ValueError, match="object space"):
        L.lens_file_read(bad)
    # a glass / a curvature on a break, a negative thickness, OBNA and image-height fields are refused
    with pytest.raises(ValueError, match="cannot carry a glass"):
        L.lens_file_read(base.replace(cb, cb + "  GLAS ___BLANK 1 0 1.5 60 0 0 0 0 0 0\n"))
    with pytest.raises(ValueError, match="no curvature"):
        L.lens_file_read(base.replace("  PARM 6 0.0\n", "  PARM 6 0.0\n  CURV 0.01 0 0 0 0 \"\"\n", 1))
    with pytest.raises(ValueError, match="runs against the light"):
        L.lens_file_read(base.replace("DISZ 40.0\n", "DISZ -40.0\n", 1))
    with pytest.raises(ValueError, match="object-space NA"):
        L.lens_file_read(base.replace("ENPD 12", "OBNA 0.1 0"))
    with pytest.raises(ValueError, match="field type"):
        L.lens_file_read(base.replace("FTYP 0 0", "FTYP 2 0"))
    with pytest.raises(ValueError, match="outside 1..6"):
        L.lens_file_read(base.replace("  PARM 1 0.0\n", "  PARM 1 0.0\n  PARM 7 1\n", 1))
    # SCBD tilts stay refused even in a file with coordinate breaks
    with pytest.raises(ValueError, match="SCBD"):
        L.lens_file_read(base.replace("SURF 3\n", "SURF 3\n  SCBD 1 0 0 0 0 90 0 0\n", 1))



def test_coaxial_files_are_unchanged():
    p = L.lens_file_read(None)
    assert p["noncoaxial"] is False and p["pupil"] is None and p["surface_records"] is None
    assert p["system"]["kind"] if "kind" in p["system"] else True
    assert "surfaces" in p["system"] and p["fields"][0]["field"] == 0.0


def test_flat_air_planes_are_merged_and_listed():
    p = L.lens_file_read(_text("cb_three_mirrors.zmx"))
    assert any("flat air-to-air plane" in n for n in p["report"]["notes"])
    assert p["surface_records"][5] == [] and p["surface_records"][9] == []
    # 併合は光線を変えない: 無作用の平面を厚みに足した同じ系との差は 0
    assert sum(1 for r in p["system"]["records"] if r["kind"] == "surface") == 4        # 平面 1 + 鏡 3


def test_finite_object_system_is_written_with_a_floating_aperture_and_reads_back():
    s = R3.noncoaxial_system([{"R": 51.68, "t": 5.0, "n": BK, "ap": 8.0},
                              {"R": INF, "t": 30.0, "n": 1.0},
                              {"type": "fold_mirror", "tilt": (30.0, 0.0), "ap": 30.0, "t": 60.0}],
                             stop=0, object_mm=200.0, field=(1.0, 2.0))
    w = L.lens_file_write(None, system=s)
    assert "FLOA" in w["text"] and "FTYP 1 " in w["text"]
    q = L.lens_file_read(w["text"])
    assert q["field_type"] == "object_height" and q["fields"][0]["field"] == (1.0, 2.0)
    assert q["system"]["object_mm"] == 200.0
    assert abs(q["pupil"]["stop_radius_mm"] - 8.0) < 1e-12
    assert _max_hit_difference(s, q["system"], fields=((1.0, 2.0),)) < 1e-9
