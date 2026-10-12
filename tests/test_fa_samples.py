# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""The FA (factory-inspection) sample images and the recipes that inspect them.

``tools/gen_fa_samples.py`` computes five inspection scenes from written-down geometry
(height field under an ``illumdesign`` light / the back-lit plate PoC / the weld
radiograph PoC) and ships each with its pixel-exact defect mask. ``recipes.py`` has one
"FA — ..." recipe per scene. These tests pin, on the **shipped PNGs**:

* the renderer is ``illumdesign._radiance`` vectorised (same numbers per pixel);
* every FA manifest entry carries provenance, a description, a truth mask that matches
  its stated pixel count, and names a recipe that names it back;
* each recipe finds its defects -- every truth object hit, no detection that touches no
  defect, overlap numbers no worse than measured on 2026-10-12;
* on the defect-free twin of the scene the same recipe flags nothing (a detector that
  only ever "finds" something would pass the first check and fail this one);
* re-running the generator reproduces the shipped pictures and masks.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pytest
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import api                      # noqa: E402
import gen_fa_samples as G      # noqa: E402
import illumdesign as ID        # noqa: E402
import imgio                    # noqa: E402
import recipes                  # noqa: E402
import sample_images            # noqa: E402

SAMPLE_DIR = os.path.join(ROOT, "studio_assets", "sample_images")
EIGHT = np.ones((3, 3), bool)


def _entries():
    with open(os.path.join(SAMPLE_DIR, "manifest.json"), encoding="utf-8") as f:
        return {e["name"]: e for e in json.load(f)["images"] if e.get("owner") == G.OWNER}


def _truth(name):
    return imgio.load(os.path.join(SAMPLE_DIR, name + ".truth.png")) > 0.5


def _score(region, truth, tol=2):
    """Object- and pixel-level agreement of a detected region with the truth mask."""
    o = np.asarray(region) > 0.5
    tl, tn = ndimage.label(truth, EIGHT)
    ol, on = ndimage.label(o, EIGHT)
    return {
        "truth_objects": tn,
        "hit": sum(1 for i in range(1, tn + 1) if (o & (tl == i)).any()),
        "detections": on,
        "false_detections": sum(1 for j in range(1, on + 1) if not (truth & (ol == j)).any()),
        "iou": float((o & truth).sum() / max(1, (o | truth).sum())),
        # within `tol` px: a 1-px shift of a 3-px-wide scratch must not read as a miss
        "recall_tol": float((truth & ndimage.binary_dilation(o, iterations=tol)).sum() / max(1, truth.sum())),
        "precision_tol": float((o & ndimage.binary_dilation(truth, iterations=tol)).sum() / max(1, o.sum())),
    }


def _recipe_of(name):
    r = recipes.get(_entries()[name]["recipe"])
    assert r is not None and r.get("image") == name
    return [tuple(s) for s in r["stages"]]


# --------------------------------------------------------------------------- #
# the renderer is illumdesign's reflectance, per pixel                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("surface", ["brushed_metal", "satin", {"albedo": 0.12, "roughness": 0.5, "f0": 0.9}])
def test_render_height_field_equals_illumdesign_radiance_per_pixel(surface):
    rng = np.random.default_rng(3)
    h = ndimage.gaussian_filter(rng.standard_normal((24, 30)), 2.0) * 0.05      # slopes of several deg
    rough = np.zeros(h.shape, bool)
    rough[8:12, 10:20] = True
    albedo = np.full(h.shape, 0.3)
    albedo[15:18, 3:9] = 0.05
    px = 0.1
    light = G.ring_light(35.0, n=24)
    img = G.render_height_field(h, px, light, surface, albedo=albedo, rough=rough)
    E, D, I0, m = ID._check_light(light)
    sp = ID._surface_params(surface)
    dr, dc = np.gradient(h, px)
    H, W = h.shape
    for (r, c) in [(0, 0), (5, 7), (9, 12), (16, 4), (23, 29), (12, 15)]:
        n = np.array([-dc[r, c], dr[r, c], 1.0])
        n /= np.linalg.norm(n)
        p = np.array([(c - (W - 1) / 2) * px, ((H - 1) / 2 - r) * px, h[r, c]])
        v = np.array([0.0, 0.0, 300.0]) - p
        v /= np.linalg.norm(v)
        want = ID._radiance(p, n, v, E, D, I0, m, sp, albedo=albedo[r, c], rough=bool(rough[r, c]))
        assert img[r, c] == pytest.approx(want, rel=1e-10, abs=1e-15), (r, c)


def test_render_height_field_refuses_what_it_cannot_do():
    flat = np.zeros((8, 8))
    with pytest.raises(ValueError, match="area sources"):
        G.render_height_field(flat, 0.1, ID.light_source("coaxial"), "satin")
    with pytest.raises(ValueError, match="finite 2-D"):
        G.render_height_field(np.full((8, 8), np.nan), 0.1, G.ring_light(30), "satin")
    with pytest.raises(ValueError, match="px_mm"):
        G.render_height_field(flat, 0.0, G.ring_light(30), "satin")
    with pytest.raises(ValueError, match="shape"):
        G.render_height_field(flat, 0.1, G.ring_light(30), "satin", rough=np.zeros((4, 4), bool))
    with pytest.raises(ValueError, match="black"):
        G.camera_capture(np.zeros((8, 8)), np.random.default_rng(0))


def test_dark_field_makes_a_rough_patch_bright_on_brushed_metal():
    """The physics the scratch scene relies on: under a low ring a rough patch out-shines the flat."""
    h = np.zeros((16, 16))
    rough = np.zeros(h.shape, bool)
    rough[6:10, 6:10] = True
    img = G.render_height_field(h, 0.1, G.ring_light(25.0), "brushed_metal", rough=rough)
    assert img[rough].mean() > 3.0 * img[~rough].mean()


# --------------------------------------------------------------------------- #
# manifest and files                                                            #
# --------------------------------------------------------------------------- #
def test_every_fa_scene_is_shipped_with_provenance_truth_and_a_recipe():
    ent = _entries()
    assert set(ent) == set(G.SCENES), sorted(set(ent) ^ set(G.SCENES))
    assert 4 <= len(ent) <= 8
    for name, e in ent.items():
        for k in ("file", "truth_mask", "source", "licence", "description", "description_ja",
                  "truth", "recipe"):
            assert e.get(k), (name, k)
        assert "own work" in e["licence"] and "photograph" in e["licence"]
        assert sample_images.path(name) and name in sample_images.names()
        truth = _truth(name)
        assert truth.shape == sample_images.load(name).shape
        assert int(truth.sum()) == e["truth"]["pixels"], name
        assert e["truth"].get("mask_rule"), name
        r = recipes.get(e["recipe"])
        assert r is not None and r["image"] == name, name


def test_fa_recipes_and_fa_images_pair_up_one_to_one():
    fa = [r for r in recipes.RECIPES if r["name"].startswith("FA — ")]
    assert sorted(r["image"] for r in fa) == sorted(G.SCENES)
    assert recipes.validate() == []


# --------------------------------------------------------------------------- #
# each recipe finds its defects on the shipped picture                          #
# --------------------------------------------------------------------------- #
def test_scratch_recipe_finds_the_scratch_and_nothing_else():
    s = _score(api.run_pipeline(sample_images.load("metal_hairline_scratch"),
                                _recipe_of("metal_hairline_scratch")), _truth("metal_hairline_scratch"))
    # 2026-10-12: iou 0.714, recall(+-2 px) 0.870, precision(+-2 px) 1.000, 10 dashes, 0 false
    assert s["hit"] == 1 and s["false_detections"] == 0, s
    assert s["precision_tol"] >= 0.98 and s["recall_tol"] >= 0.85 and s["iou"] >= 0.68, s


def test_dent_and_fibre_recipe_finds_both_defects():
    s = _score(api.run_pipeline(sample_images.load("resin_dent_fibre"), _recipe_of("resin_dent_fibre")),
               _truth("resin_dent_fibre"))
    # 2026-10-12: 2/2 hit, 3 detections (the dent's dark and bright half + the fibre), 0 false,
    # iou 0.34 (the dent's truth is a 2-sigma disc, the detector sees its shading lobes)
    assert s["truth_objects"] == 2 and s["hit"] == 2 and s["false_detections"] == 0, s
    assert s["iou"] >= 0.30, s


def test_lot_code_recipe_gives_one_region_per_glyph():
    name = "engraved_lot_code"
    stages = _recipe_of(name)
    img, truth = sample_images.load(name), _truth(name)
    s = _score(api.run_pipeline(img, stages), truth)
    n = _entries()[name]["truth"]["glyph_components"]
    # 2026-10-12: 17/17 glyphs, 17 detections, 0 false, iou 0.886
    assert s["truth_objects"] == n == 17 and s["hit"] == n and s["detections"] == n, s
    assert s["false_detections"] == 0 and s["iou"] >= 0.85, s
    assert api.run_pipeline(img, stages + [("count_obj", 0.5, 0.5)]) == float(n)


def test_hole_recipe_counts_eight_and_the_round_hole_measures_right():
    name = "machined_plate_holes"
    stages = _recipe_of(name)
    img, truth = sample_images.load(name), _truth(name)
    assert api.run_pipeline(img, stages) == 8.0 == _entries()[name]["truth"]["count"]
    region = np.asarray(api.run_pipeline(img, stages[:-1])) > 0.5
    s = _score(region, truth)
    assert s["hit"] == 8 and s["false_detections"] == 0 and s["iou"] >= 0.98, s    # 0.993 measured
    t = _entries()[name]["truth"]["round_hole"]
    lab, _ = ndimage.label(region, EIGHT)
    k = lab[int(round(t["center_row_col"][0])), int(round(t["center_row_col"][1]))]
    d_eq = 2.0 * math.sqrt(float((lab == k).sum()) / math.pi)
    assert abs(d_eq - t["diameter_px"]) < 1.0, (d_eq, t["diameter_px"])


def test_porosity_recipe_finds_every_pore_without_a_false_call():
    s = _score(api.run_pipeline(sample_images.load("weld_xray_porosity"), _recipe_of("weld_xray_porosity")),
               _truth("weld_xray_porosity"))
    # 2026-10-12: 7/7 pores (0.6-2.0 mm), 0 false, iou 0.565. The margin is thin: an offset
    # b of 0.63 adds a false call, 0.70 loses small pores -- that is the honest state of a
    # 0.7 mm pore in the cap under this noise, not a tuning slip.
    assert s["truth_objects"] == 7 and s["hit"] == 7 and s["false_detections"] == 0, s
    assert s["iou"] >= 0.5, s


@pytest.mark.parametrize("name", ["metal_hairline_scratch", "resin_dent_fibre", "weld_xray_porosity"])
def test_recipe_flags_nothing_on_the_defect_free_twin(tmp_path, name):
    sc = G.SCENES[name](defects=False)
    assert not np.asarray(sc["mask"]).any()
    p = str(tmp_path / (name + ".png"))
    imgio.save(p, sc["img"])                          # through 8 bits, like the shipped file
    out = np.asarray(api.run_pipeline(imgio.load(p), _recipe_of(name))) > 0.5
    assert int(out.sum()) == 0, (name, int(out.sum()))


# --------------------------------------------------------------------------- #
# the generator reproduces what is shipped                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", sorted(G.SCENES))
def test_generator_reproduces_the_shipped_picture_and_mask(tmp_path, name):
    sc = G.build(name)
    p = str(tmp_path / "x.png")
    imgio.save(p, sc["img"])
    got, ship = imgio.load(p), sample_images.load(name)
    assert got.shape == ship.shape
    # float rounding may move a pixel across an 8-bit step on another platform
    diff = np.abs(got - ship) > 1.5 / 255
    assert diff.mean() <= 1e-3, (name, float(diff.mean()))
    mism = int((sc["mask"] != _truth(name)).sum())
    assert mism <= max(2, int(1e-3 * sc["mask"].sum())), (name, mism)


def test_generator_list_writes_nothing(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(G, "OUT", str(tmp_path / "out"))
    assert G.main(["--list"]) == 0
    assert not os.path.exists(str(tmp_path / "out"))
    out = capsys.readouterr().out
    assert all(n in out for n in G.SCENES)
    with pytest.raises(KeyError):
        G.build("no_such_scene")


def test_generator_merges_with_the_other_manifest_owners(tmp_path, monkeypatch):
    import gen_sample_images as GI
    out = str(tmp_path / "sample_images")
    monkeypatch.setattr(GI, "OUT", out)
    monkeypatch.setattr(G, "OUT", out)
    monkeypatch.setattr(G, "SCENES", {"engraved_lot_code": G.SCENES["engraved_lot_code"]})
    assert GI.main() == 0
    assert G.main([]) == 0
    assert GI.main() == 0                                   # either order keeps both owners
    with open(os.path.join(out, "manifest.json"), encoding="utf-8") as f:
        names = [e["name"] for e in json.load(f)["images"]]
    assert "engraved_lot_code" in names and "gradient" in names
    assert len(names) == len(set(names))
    assert os.path.exists(os.path.join(out, "engraved_lot_code.truth.png"))
