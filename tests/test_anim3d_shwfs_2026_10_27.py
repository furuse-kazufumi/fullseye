# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Shack-Hartmann moving 3-D physics, lesson, size and translation gates."""
from __future__ import annotations
import importlib.util, json, os, re, sys
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_shwfs_anim3d"
PAGE=os.path.join(ROOT,"docs","view2026","anim3d","shack_hartmann_anim3d.html")
def _load(name):
    p=os.path.join(ROOT,"tools",name+".py"); s=importlib.util.spec_from_file_location(name+"_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    if ROOT not in sys.path: sys.path.insert(0,ROOT)
    B=_load(BUILDER); r=B.compute(); g=B.gates(r); return B,r,g,B.build_spec(r,g)

def test_centroids_are_measured_from_seeded_noisy_images(built):
    B,r,_g,_=built
    assert len(r["x"])>=20 and r["mosaics"].shape[0]==len(r["strength"])
    assert r["mosaics"].shape[-1]==3 and np.ptp(r["mosaics"])>100
    assert np.max(np.abs(r["recovered"]-r["truth"]))>1e-4
    assert B.SUB_N==32 and B.PAD_N>=4*B.SUB_N
    # A high-order term changes the diffraction shape, not merely a prescribed Gaussian centre.
    rng=np.random.default_rng(1); flat=np.zeros(len(B.SYN_MODES)); bent=flat.copy(); bent[-1]=.25
    _x,_y,a=B._diffraction_image(flat,0,0,1e6,rng,noise=False)
    _x,_y,b=B._diffraction_image(bent,0,0,1e6,rng,noise=False)
    assert np.linalg.norm(a/a.sum()-b/b.sum())>.05

def test_zernike_recovery_passes_independent_image_gate(built):
    _B,r,g,_=built
    assert r["recovered"].shape==r["truth"].shape and r["recovered"].shape[1]==8
    assert g["coeff_rms"]<.025 and g["wavefront_rms"]<.025
    assert g["low_error"]>g["matched_error"]
    assert g["matched_error"]<g["noise_allow"] and g["rich_error"]<g["noise_allow"]

def test_photon_noise_tracks_inverse_square_root(built):
    _B,r,g,_=built
    assert len(r["levels"])>=6 and np.all(np.diff(r["levels"])>0)
    assert r["noise"][-1]<r["noise"][0]
    assert -.70<g["photon_slope"]<-.30

def test_fixed_window_exposes_dynamic_range_limit(built):
    _B,r,g,_=built
    assert np.count_nonzero(r["dynamic"]>0)>=2
    assert 2.0<g["dynamic_limit"]<4.0 and g["dynamic_over"]>1

def test_lesson_checks_and_limit_are_structural(built):
    _B,_r,_g,spec=built; tabs=spec["tabs"]
    assert [t["id"] for t in tabs]==["principle","array","recover","limits"]
    assert [t["badge"] for t in tabs]==["passed","passed","passed","limit"]
    for t in tabs:
        assert set(t["lesson"])=={"question","choices","answer","explain","formula","limit"}
        assert len(t["checks"])>=3 and len(t["axis"]["values"])==len(t["t"])
    assert all(all(c["ok"] for c in t["checks"]) for t in tabs[:3])
    assert len([c for c in tabs[-1]["checks"] if not c["ok"]])==1

def test_page_is_small_synthetic_and_public_safe(built):
    B,_r,_g,spec=built; html=B.pv._build_html(spec,["ja","en"])
    assert len(html.encode())<600_000 and "fixed-seed synthetic" in html
    assert "http://" not in html and "https://" not in html and "**" not in html

I18N=_load("anim3d_i18n")
@pytest.fixture(scope="module")
def spec_table():
    s=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    return s,I18N.load_table(BUILDER)

def test_i18n_table_has_no_missing_or_unused_entries(spec_table):
    s,t=spec_table
    assert len({d["en"] for _,d in I18N.iter_texts(s)})>=55
    problems,unused=I18N.audit(s,t); assert problems==[] and unused==[]

def test_committed_page_is_rebuilt_eight_language_page(spec_table):
    s,t=spec_table
    with open(PAGE,encoding="utf-8") as f: html=f.read()
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    want=I18N.pv._build_html(I18N.translate(s,t),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,want,PAGE,BUILDER)
