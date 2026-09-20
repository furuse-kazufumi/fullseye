# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""chain_fuzz(--cover-all, 300 連鎖、2026-09-20)の分類 15 件を固定する回帰。

分類と根:

* SUSPECT 8(camera_rays / covers_sensor / defocus_blur / diffraction_blur / from_xld /
  light_wavelengths / optscene_depth / random_defects)— sort ``table`` は
  **list-of-rows と spec dict の両方**を指す(``vol_edge_probe`` は行のリスト、
  ``optical_camera`` は dict)。fuzz が前者を後者の席に入れると、消費 op は
  ``camera["K"]`` で ``TypeError: list indices must be integers`` /
  ``'list' object has no attribute 'get'`` と落ちていた —— 例外は出るが op 名も原因も
  言わない。消費側で dict を検査し、**op 名入りの ValueError** で止める。
* NONFINITE 6 — 全部「非有限が契約」だった: lens_system / example_system / bend_singlet は
  処方の ``object_mm = inf``(無限遠が既定値、replay で 1 つの inf と確認)、
  triangulate_column(未確定画素 = NaN)、m3c2_distance(点不足 = nan)、
  piv_cross_correlate(峰の立たない窓 = nan、``valid_fraction`` 併記)。
  chain_fuzz の NONFINITE_BY_CONTRACT に理由つきで載せた。
* TYPEMISS 1 — peak_subbin は台帳 out が ``measurement`` だが indices (k,) に対して
  (k,) の配列を返す → ``signal``。register_light は ``table`` 宣言で鍵の str → ``text``。
"""
import inspect
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

ROWS = [{"t": 0.0, "value": 1.0}, {"t": 1.0, "value": 2.0}]      # vol_edge_probe 型の行リスト


def _cases():
    import optscene as o
    import fourierdesc as fd
    img = np.zeros((8, 8))
    plane = o.scene_plane()
    return [
        ("camera_rays", lambda: o.camera_rays(ROWS)),
        ("defocus_blur", lambda: o.defocus_blur(img, img, ROWS)),
        ("diffraction_blur", lambda: o.diffraction_blur(img, ROWS)),
        ("optscene_depth", lambda: o.optscene_depth([plane], ROWS)),
        ("optscene_mask", lambda: o.optscene_mask([plane], ROWS, 0)),
        ("optscene_defect_mask", lambda: o.optscene_defect_mask([plane], ROWS)),
        ("optscene_instances", lambda: o.optscene_instances([plane], ROWS)),
        ("render_optscene", lambda: o.render_optscene([plane], ROWS, o.light_spec())),
        ("render_studio", lambda: o.render_studio([plane], ROWS)),
        ("inspection_dataset", lambda: o.inspection_dataset([plane], ROWS, o.light_spec())),
        ("linescan_capture", lambda: o.linescan_capture([plane], ROWS, o.light_spec())),
        ("covers_sensor", lambda: o.covers_sensor(ROWS, o.sensor_spec())),
        ("covers_sensor", lambda: o.covers_sensor(o.lens_spec(f_number=4.0), ROWS)),
        ("light_wavelengths", lambda: o.light_wavelengths(ROWS)),
        ("random_defects", lambda: o.random_defects(ROWS)),
        ("surface_defect", lambda: o.surface_defect(ROWS, img)),
        ("surface_finish", lambda: o.surface_finish(ROWS)),
        ("from_xld", lambda: fd.from_xld(ROWS)),
    ]


@pytest.mark.parametrize("op, call", _cases(), ids=[c[0] + "_" + str(i) for i, c in enumerate(_cases())])
def test_table_consumers_refuse_a_list_of_rows_with_the_op_name(op, call):
    """行リストを spec dict の席に入れたら、op 名入りの ValueError(TypeError/AttributeError
    ではなく)。fuzz の分類では ValueError だけが CONTRACT(白)になる。"""
    with pytest.raises(ValueError, match=op):
        call()


def test_a_wrong_kind_of_spec_is_refused_too():
    """dict であっても種類が違えば止める(lens の席に sensor、primitive の席に光源)。"""
    import optscene as o
    with pytest.raises(ValueError, match="covers_sensor: lens must be a lens_spec"):
        o.covers_sensor(o.sensor_spec(), o.sensor_spec())
    with pytest.raises(ValueError, match="random_defects: primitive"):
        o.random_defects(o.light_spec())
    with pytest.raises(ValueError, match="camera_rays: camera is missing key"):
        o.camera_rays({"K": np.eye(3)})


def test_the_happy_paths_still_run():
    import optscene as o
    import fourierdesc as fd
    cam = o.optical_camera(resolution=(12, 10))
    z = o.optscene_depth([o.scene_plane()], cam)
    assert z.shape == (10, 12)
    wl, w = o.light_wavelengths(o.light_spec(), samples=3)
    assert len(wl) == 3 and abs(float(np.sum(w)) - 1.0) < 1e-12
    xy = fd.from_xld({"shape": "xld", "cs": [np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])]})
    assert xy.shape == (3, 2)
    with pytest.raises(ValueError, match="from_xld: i must be"):
        fd.from_xld({"shape": "xld", "cs": [xy]}, 3)


def test_peak_subbin_and_register_light_ledger_out_match_what_they_return():
    pytest.importorskip("torch")
    import chain_fuzz
    import dsp
    import optscene as o
    meta = {e[0]: e for e in chain_fuzz.catalog()}
    assert meta["peak_subbin"][3] == "signal"
    x = np.exp(-0.5 * ((np.arange(64) - 20.3) / 2.0) ** 2) + np.exp(-0.5 * ((np.arange(64) - 45.6) / 2.0) ** 2)
    out = dsp.peak_subbin(x, np.array([20, 46]))
    assert chain_fuzz.TYPE_CHECKS["signal"](out) and out.shape == (2,)
    assert isinstance(dsp.peak_subbin(x, 20), float)          # scalar in, scalar out は変えない
    assert meta["register_light"][3] == "text"
    key = o.register_light("TestMaker", "TM-1")
    try:
        assert chain_fuzz.TYPE_CHECKS["text"](key) and key == "TestMaker TM-1"
    finally:
        o._LIGHT_CATALOG.pop(key, None)          # プロセス内カタログを汚さない(他テストが実在ベンダのみを数える)


def test_nonfinite_allowlist_additions_are_documented_and_really_nonfinite():
    """allowlist に載せた op は (1) docstring が非有限を契約として書いている (2) 実際に
    その非有限を返す —— 直って有限になったら外す(載せっぱなしは本物の NaN を隠す)。"""
    pytest.importorskip("torch")
    import chain_fuzz
    import lensopt
    import metrics3d
    import pivops
    import raytrace
    import fringe
    assert chain_fuzz.NONFINITE_BY_CONTRACT_PRESCRIPTION <= chain_fuzz.NONFINITE_BY_CONTRACT
    assert chain_fuzz.NONFINITE_BY_CONTRACT_MEASURE <= chain_fuzz.NONFINITE_BY_CONTRACT
    docs = {"lens_system": raytrace.lens_system, "example_system": raytrace.example_system,
            "bend_singlet": lensopt.bend_singlet, "triangulate_column": fringe.triangulate_column,
            "m3c2_distance": metrics3d.m3c2_distance, "piv_cross_correlate": pivops.piv_cross_correlate}
    for name, fn in docs.items():
        text = (inspect.getdoc(fn) or "") + inspect.getsource(fn)
        assert ("inf" in text.lower()) or ("nan" in text.lower()), name
    assert raytrace.lens_system()["object_mm"] == float("inf")
    assert raytrace.example_system()["object_mm"] == float("inf")
    assert lensopt.bend_singlet()["system"]["object_mm"] == float("inf")
    flow, info = pivops.piv_cross_correlate(np.ones((64, 64)), np.ones((64, 64)))
    assert np.isnan(flow).all() and info["valid_fraction"] == 0.0


def test_the_eight_suspect_replays_are_white_now():
    """fuzz が出した seed と op 列をそのまま再走し、SUSPECT が出ないこと(CONTRACT は可)。"""
    pytest.importorskip("torch")
    import chain_fuzz as cf
    ops, gens = cf.catalog(), cf.make_generators()
    seeds = {"camera_rays": 144338, "covers_sensor": 145954, "defocus_blur": 145247,
             "diffraction_blur": 145348, "from_xld": 189182, "light_wavelengths": 146459,
             "optscene_depth": 144843, "random_defects": 144035}
    bad = []
    for op, seed in seeds.items():
        log = []
        cf.run_chain(ops, gens, np.random.default_rng(seed), 2, log, chain_seed=seed,
                     script=["vol_edge_probe", op])
        bad += [(op, f["kind"], f.get("msg")) for f in log if f["kind"] == "SUSPECT"]
    assert not bad, bad
