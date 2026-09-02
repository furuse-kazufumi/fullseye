# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lensimage — image formation through a designed lens: closed-form ground truth.

Every number is an identity, not a golden file: an unaberrated pupil gives the
Airy pattern (first dark ring at 1.22 λF# within 3 %, 83.8 % ± 1 % encircled
energy); the f/4 singlet with 11 waves of spherical aberration has Strehl
< 0.05 (measured 0.011); the paraboloid mirror and every system on axis have
zero distortion while the plano-convex singlet is barrel (−0.065 % at 15°,
pinned); a δ image rendered through the paraboloid *is* the pixel-integrated
Airy PSF; energy is conserved; noise off is deterministic; the defect dataset
keeps its masks aligned with the blurred defects (IoU 0.77 measured, > 0.5
asserted). The ledger half mirrors ``tests/test_raytrace.py`` for the new
``imaging_sim`` category (types, fuzzer reachability, random tables refused).
"""
import json
import os
import re
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import defectgen as DG  # noqa: E402
import lensimage as LI  # noqa: E402
import opsoptics  # noqa: E402
import raytrace as RT  # noqa: E402

INF = float("inf")
SIM_OPS = ["psf_from_opd", "distortion_map", "render_through_lens", "defect_dataset"]


def _small():
    """The singlet stopped to a 1 mm semi-aperture (f/50): diffraction-limited."""
    return RT.lens_system([{"R": 51.68, "t": 5, "n": 1.5168, "ap": 1.0},
                           {"R": INF, "t": None, "n": 1.0}], stop=0)


def _radial_first_zero(psf, dx, r1):
    M = psf.shape[0]
    yy, xx = np.mgrid[:M, :M]
    r = np.hypot(yy - M // 2, xx - M // 2) * dx
    edges = np.arange(0.0, 2.0 * r1, dx)
    prof = []
    for a in edges:
        sel = (r >= a) & (r < a + dx)
        prof.append(psf[sel].mean() if sel.any() else np.inf)
    prof = np.array(prof)
    return edges[int(np.argmin(prof[: int(0.7 * len(edges))]))], r


# --------------------------------------------------------------------------- #
# PSF                                                                          #
# --------------------------------------------------------------------------- #
def test_unaberrated_pupil_gives_the_airy_pattern():
    s = _small()
    para = RT.paraxial_trace(s)
    fno = 1.0 / (2.0 * para["na_image"])
    assert fno == pytest.approx(50.0, abs=1e-9)
    psf, ref, dx, n = LI._psf_core(s, 0.0, 128, None, 16)
    assert dx == pytest.approx(s["wavelength_um"] * fno * 127 / 2032)
    r1 = 1.22 * s["wavelength_um"] * fno
    zero, r = _radial_first_zero(psf, dx, r1)
    assert zero == pytest.approx(r1, rel=0.03)               # measured 0.999 x
    ee = psf[r <= r1].sum() / psf.sum()
    assert ee == pytest.approx(0.838, abs=0.01)              # measured 0.8378
    assert psf.max() / ref.max() == pytest.approx(1.0, abs=1e-5)


def test_psf_from_opd_sums_to_one_and_pixel_integration_conserves_energy():
    s = _small()
    fine = LI.psf_from_opd(s, size=64, oversample=8)
    assert fine.ndim == 2 and fine.sum() == pytest.approx(1.0, abs=1e-12)
    assert fine.shape == (504, 504)
    pix = LI.psf_from_opd(s, size=64, oversample=8, pixel_pitch_um=10.0)
    assert pix.shape[0] % 2 == 1 and pix.sum() == pytest.approx(1.0, abs=1e-12)
    assert pix.shape[0] < fine.shape[0]
    c = pix.shape[0] // 2
    assert pix[c, c] == pix.max()                             # centred on a pixel
    with pytest.raises(ValueError, match="coarser than the pixel pitch"):
        LI.psf_from_opd(s, size=64, oversample=1, pixel_pitch_um=1.0)


def test_f4_singlet_has_strehl_below_0_05_and_auto_sampling_avoids_aliasing():
    sg = RT.lens_system()
    psf, ref, dx, n = LI._psf_core(sg, 0.0, None, None, 4)
    assert n == 194                                           # auto: 44 waves/rho at 0.4 waves/sample
    assert psf.max() / ref.max() == pytest.approx(0.0106, abs=2e-3)
    assert psf.max() / ref.max() < 0.05
    with pytest.raises(ValueError, match="aliased"):
        LI.psf_from_opd(sg, size=32)


def test_psf_field_grid_reports_strehl_and_spot_per_field():
    g = LI.psf_field_grid(RT.example_system("doublet"), fields=(0.0, 4.0))
    assert g["fields"] == [0.0, 4.0] and len(g["psfs"]) == 2
    assert g["strehl"][0] > g["strehl"][1]
    assert g["rms_spot_mm"][0] == pytest.approx(RT.spot_stats(RT.example_system("doublet"))["rms_radius"])
    assert all(abs(p.sum() - 1.0) < 1e-12 for p in g["psfs"])
    assert g["fno"] == pytest.approx(3.865, abs=1e-3)


# --------------------------------------------------------------------------- #
# distortion                                                                   #
# --------------------------------------------------------------------------- #
def test_paraboloid_and_on_axis_have_zero_distortion_singlet_is_barrel():
    dp = LI.distortion_map(RT.example_system("paraboloid"))
    assert max(abs(v) for v in dp["distortion_pct"]) < 1e-6
    assert dp["distortion_pct"][0] == 0.0
    d = LI.distortion_map(RT.lens_system(), fields=[0.0, 5.0, 10.0, 15.0])
    assert d["distortion_pct"][-1] == pytest.approx(-0.0649, abs=3e-3)   # measured 2026-09-03
    assert d["distortion_pct"][-1] < 0.0 and d["distortion_pct"][1] < 0.0
    big = LI.distortion_map(RT.lens_system(), (2048, 2048), 5.5)
    assert big["fields"][-1] == pytest.approx(4.554, abs=1e-2)
    assert big["max_distortion_pct"] == pytest.approx(-0.0059, abs=1e-3)
    dd = LI.distortion_map(RT.example_system("doublet"), fields=[0.0, 15.0])
    assert dd["max_distortion_pct"] == pytest.approx(-0.281, abs=1e-2)


def test_distortion_grid_is_the_identity_on_axis_and_pulls_inward_for_barrel():
    d = LI.distortion_map(RT.lens_system(), (65, 65), 300.0)     # 300 um pixels: 13.7 mm corner
    assert d["grid_rows"].shape == (65, 65)
    assert d["grid_rows"][32, 32] == pytest.approx(32.0) and d["grid_cols"][32, 32] == pytest.approx(32.0)
    # barrel: a real pixel at the corner sees an ideal point *further* out
    assert d["grid_rows"][0, 32] < 0.0 and d["grid_cols"][32, 64] > 64.0
    with pytest.raises(ValueError):
        LI.distortion_map(RT.lens_system(), fields=[0.0])


# --------------------------------------------------------------------------- #
# rendering                                                                    #
# --------------------------------------------------------------------------- #
def test_delta_through_the_paraboloid_is_the_pixel_integrated_airy_psf():
    pb = RT.example_system("paraboloid")
    img = np.zeros((65, 65))
    img[32, 32] = 1.0
    out = LI.render_through_lens(img, pb, 1.0, zones=1, illumination="none")
    pp = LI.psf_from_opd(pb, pixel_pitch_um=1.0, oversample=4)
    c = pp.shape[0] // 2
    np.testing.assert_allclose(out, pp[c - 32:c + 33, c - 32:c + 33], atol=1e-12)
    assert out.sum() == pytest.approx(1.0, abs=0.01)


def test_checkerboard_through_the_paraboloid_is_undistorted_and_energy_is_conserved():
    pb = RT.example_system("paraboloid")
    cb = (np.indices((128, 128)).sum(0) // 16 % 2).astype(np.float64)
    model = LI._lens_model(pb, (128, 128), 5.5, 1, None, None, None, "none")
    np.testing.assert_allclose(LI._remap(cb, model), cb, atol=1e-9)       # zero distortion = identity
    out = LI.render_through_lens(cb, pb, 5.5, zones=1, illumination="none")
    assert np.corrcoef(cb.ravel(), out.ravel())[0, 1] > 0.99
    inner = (slice(8, -8), slice(8, -8))
    assert out[inner].sum() == pytest.approx(cb[inner].sum(), rel=0.01)
    # the 3x3 lattice adds field-dependent coma but never energy
    out3 = LI.render_through_lens(cb, pb, 5.5, zones=3, illumination="none")
    assert out3[inner].sum() == pytest.approx(cb[inner].sum(), rel=0.01)
    assert out3.shape == cb.shape and out3.min() >= 0.0


def test_illumination_and_noise_paths_are_deterministic():
    sg = RT.lens_system()
    img = np.full((48, 48), 0.5)
    a = LI.render_through_lens(img, sg, 5.5, zones=2, noise=True, seed=3)
    b = LI.render_through_lens(img, sg, 5.5, zones=2, noise=True, seed=3)
    c = LI.render_through_lens(img, sg, 5.5, zones=2, noise=True, seed=4)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)
    assert 0.0 <= a.min() and a.max() <= 1.0
    assert np.unique(a).size > 8                                 # quantised, noisy levels
    clean = LI.render_through_lens(img, sg, 5.5, zones=2)
    np.testing.assert_array_equal(clean, LI.render_through_lens(img, sg, 5.5, zones=2))
    # traced illumination falls with field (cos^4 x vignetting), 'none' does not
    rt = LI.render_through_lens(img, sg, 300.0, zones=1, illumination="traced")
    assert rt[24, 24] > rt[0, 0]
    none = LI.render_through_lens(img, sg, 300.0, zones=1, illumination="none")
    assert none[24, 24] == pytest.approx(none[2, 2], rel=1e-6)
    with pytest.raises(ValueError, match="unknown noise key"):
        LI.render_through_lens(img, sg, 5.5, noise={"gain": 2})


# --------------------------------------------------------------------------- #
# dataset                                                                      #
# --------------------------------------------------------------------------- #
def test_defect_dataset_records_are_aligned_reproducible_and_written(tmp_path):
    recs = LI.defect_dataset(3, size=(96, 96), seed=11, out_dir=str(tmp_path))
    assert len(recs) == 3
    ann = json.load(open(tmp_path / "annotations.json", encoding="utf-8"))
    assert len(ann["images"]) == 3 and ann["categories"][0]["name"] == "scratch"
    for i, r in enumerate(recs):
        assert os.path.exists(r["image"]) and os.path.exists(r["mask"])
        assert r["defects"] and all(d["kind"] in LI._KINDS for d in r["defects"])
        for d in r["defects"]:
            x, y, w, h = d["bbox"]
            assert 0 <= x and 0 <= y and x + w <= 96 and y + h <= 96 and d["area"] > 0
        assert set(r["lens"]) == {"efl", "fno", "rms_spot_center", "rms_spot_corner", "max_distortion_pct"}
    mem = LI.defect_dataset(2, size=(64, 64), seed=11)
    mem2 = LI.defect_dataset(2, size=(64, 64), seed=11)
    for a, b in zip(mem, mem2):
        assert a["image"].shape == a["mask"].shape == (64, 64) and a["mask"].dtype == bool
        np.testing.assert_array_equal(a["image"], b["image"])
        np.testing.assert_array_equal(a["mask"], b["mask"])
        assert a["defects"] == b["defects"]
    assert not np.array_equal(mem[0]["image"], LI.defect_dataset(1, size=(64, 64), seed=12)[0]["image"])


def test_scratch_mask_pushed_through_the_distortion_overlaps_the_blurred_scratch():
    dbl = RT.example_system("doublet")
    bg = DG.surface_texture((256, 256), seed=1)
    dimg, dm = DG.defect_scratch((256, 256), length_px=150, width_px=5, angle_deg=30, contrast=-0.4, seed=2)
    comp = DG.composite_defect(bg, dimg, dm)
    r0 = LI.render_through_lens(bg, dbl, 5.5, illumination="none")
    r1 = LI.render_through_lens(comp, dbl, 5.5, illumination="none")
    diff = np.abs(r1 - r0)
    region = diff > 0.5 * diff.max()
    model = LI._lens_model(dbl, (256, 256), 5.5, 3, None, None, None, "traced")
    dmw = LI._remap(dm.astype(np.float64), model, order=0) > 0.5
    iou = (region & dmw).sum() / (region | dmw).sum()
    assert iou == pytest.approx(0.765, abs=0.05)               # measured 2026-09-03
    assert iou > 0.5


# --------------------------------------------------------------------------- #
# fail-closed                                                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    lambda: LI.psf_from_opd({"a": 1}),
    lambda: LI.psf_from_opd(RT.lens_system(), size=4),
    lambda: LI.psf_from_opd(RT.lens_system(), oversample=0),
    lambda: LI.psf_from_opd(RT.lens_system(), field=float("nan")),
    lambda: LI.psf_field_grid(RT.lens_system(), fields=()),
    lambda: LI.distortion_map(RT.lens_system(), image_size=(1, 5)),
    lambda: LI.distortion_map(RT.lens_system(), pixel_pitch_um=-1.0),
    lambda: LI.render_through_lens("img", RT.lens_system()),
    lambda: LI.render_through_lens(np.full((8, 8), -1.0), RT.lens_system()),
    lambda: LI.render_through_lens(np.ones((8, 8)), RT.lens_system(), zones=0),
    lambda: LI.render_through_lens(np.ones((8, 8)), RT.lens_system(), illumination="flat"),
    lambda: LI.render_through_lens(np.ones((8, 8)), RT.lens_system(), noise="yes"),
    lambda: LI.render_through_lens(np.ones((8, 8)), RT.lens_system(), seed=-1),
    lambda: LI.render_through_lens(np.ones((8, 8, 3)), RT.lens_system()),
    lambda: LI.defect_dataset(0),
    lambda: LI.defect_dataset(1, kinds=("hole",)),
    lambda: LI.defect_dataset(1, size=(1, 1)),
    lambda: LI.defect_dataset(1, system=[1, 2, 3]),
    lambda: LI.defect_dataset(1, out_dir=123),
])
def test_bad_inputs_raise_value_error(bad):
    with pytest.raises(ValueError):
        bad()


# --------------------------------------------------------------------------- #
# ledger / fuzzer / facade                                                     #
# --------------------------------------------------------------------------- #
def test_imaging_sim_category_is_registered_with_the_declared_types():
    assert opsoptics.list_ops("imaging_sim") == SIM_OPS
    assert "imaging_sim" in opsoptics.categories()
    for name in SIM_OPS:
        meta = opsoptics.info(name)
        assert meta["module"] == "lensimage" and meta["func"] is getattr(LI, name)
        assert meta["doc"], name
    assert opsoptics.info("psf_from_opd")["in"] == ["table"] and opsoptics.info("psf_from_opd")["out"] == "image2d"
    assert opsoptics.info("distortion_map")["in"] == ["table"] and opsoptics.info("distortion_map")["out"] == "table"
    assert opsoptics.info("render_through_lens")["in"] == ["image2d", "table"]
    assert opsoptics.info("render_through_lens")["out"] == "image2d"
    assert opsoptics.info("defect_dataset")["in"] == [] and opsoptics.info("defect_dataset")["out"] == "table"
    assert opsoptics.missing() == []


def test_imaging_sim_ops_return_their_declared_type_and_reach_the_fuzzer():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import chain_fuzz
    pb = RT.example_system("paraboloid")
    img = np.random.default_rng(0).random((16, 16))
    args = {"psf_from_opd": (pb,), "distortion_map": (pb,), "render_through_lens": (img, pb),
            "defect_dataset": (1, pb, (32, 32))}
    for name in SIM_OPS:
        out_t = opsoptics.info(name)["out"]
        val = opsoptics.call(name, *args[name])
        assert chain_fuzz.TYPE_CHECKS[out_t](val), (name, out_t, type(val).__name__)
    names = {o[0] for o in chain_fuzz.catalog() if o[1] == "optics"}
    assert set(SIM_OPS) <= names
    rng = np.random.default_rng(0)
    assert chain_fuzz.OP_PARAM_HINTS[("defect_dataset", "n")](rng) == 1
    assert chain_fuzz.OP_PARAM_HINTS[("defect_dataset", "size")](rng) == (32, 32)
    # two-input op: the builder pairs a pool image with a real prescription half the time
    pool = {"image2d": [img], "table": [{"x": 1}]}
    seen = set()
    for i in range(20):
        b = chain_fuzz.OP_ARG_BUILDERS["render_through_lens"](pool, np.random.default_rng(i))
        assert isinstance(b, list) and len(b) == 2 and b[0] is img
        seen.add("surfaces" in b[1])
    assert seen == {True, False}


@pytest.mark.parametrize("name", SIM_OPS[:3])
def test_table_consuming_ops_refuse_a_random_table_with_value_error(name):
    rng = np.random.default_rng(7)
    fn = opsoptics.get(name)
    img = rng.random((8, 8))
    for bad in ([1, 2, 3], {"x": 1.0, "y": [1, 2]}, {"stop": 0}, {"surfaces": []},
                rng.random(5).tolist(), {"efl": 100.0, "bfl": 96.7}):
        with pytest.raises(ValueError):
            fn(img, bad) if name == "render_through_lens" else fn(bad)


def test_facade_exports_every_lensimage_op():
    import api
    import fullseye
    for name in SIM_OPS + ["psf_field_grid"]:
        assert name in api.__all__, f"{name} missing from api.__all__"
        assert name in fullseye.__all__, f"{name} missing from fullseye.__all__"
        assert getattr(fullseye, name) is getattr(LI, name)
    assert fullseye.lensimage is LI and api.lensimage is LI


def test_imaging_sim_guide_snippets_run():
    guide = os.path.join(ROOT, "docs", "ops", "optics", "guides", "optics_imaging.md")
    with open(guide, encoding="utf-8") as f:
        md = f.read()
    assert "## 結像シミュレーション(imaging_sim)" in md
    blocks = re.findall(r"```python\n(.*?)```", md, re.S)
    runnable = [b for b in blocks if "import lensimage" in b]
    assert len(runnable) >= 2, "the optics guide lost its imaging_sim snippets"
    for src in runnable:
        exec(compile(src, guide, "exec"), {"__name__": "__guide__"})
