"""合成 OCT 教材の物理・画像測定・8 言語生成物の門。"""
from __future__ import annotations
import importlib.util, json, os, re
import numpy as np
import pytest

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER="build_oct_anim3d"; PAGE=os.path.join(ROOT,"docs","view2026","anim3d","oct_retina_anim3d.html")
def _load(path,name):
    s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
OCT=_load(os.path.join(ROOT,"tools","build_oct_anim3d.py"),"oct_builder_test")
I18N=_load(os.path.join(ROOT,"tools","anim3d_i18n.py"),"oct_i18n_test")

@pytest.fixture(scope="module")
def result(): return OCT.compute()

def test_two_bandwidths_are_measured_from_inverse_fft(result):
    g=result["g"]
    assert len(g["resolution_measured"]) >= 2
    assert np.max(np.abs(g["resolution_measured"]-g["resolution_closed"])) <= 1.5
    assert g["resolution_measured"][1] < g["resolution_measured"][0]

def test_source_is_defined_in_wavelength_then_k_linearized():
    for band in OCT.BANDS_NM:
        lam,source=OCT.source_spectrum(band)
        assert np.allclose(np.diff(lam),np.diff(lam)[0])
        above=np.flatnonzero(source>=.5)
        measured_band=lam[above[-1]]-lam[above[0]]
        assert abs(measured_band-band) <= 2*np.diff(lam)[0]
        k,linear,dz=OCT.k_linearize(lam,source)
        assert np.allclose(np.diff(k),np.diff(k)[0])
        assert dz == pytest.approx(np.pi/(len(k)*(k[1]-k[0])))

def test_boundaries_are_measured_from_noisy_bscan(result):
    g=result["g"]
    assert result["bscan"].shape==(OCT.SPECTROMETER_PIXELS//2+1,OCT.NX)
    assert result["measured"].shape==(3,OCT.NX)
    assert g["thickness_max_error"] <= 10.0
    assert g["pit_error"] <= 8.0

def test_depth_sampling_comes_from_k_range_and_rolloff_is_measured(result):
    g=result["g"]
    assert 0.5 < result["dz"] < 1.0
    assert len(g["rolloff_measured"])==2
    assert g["rolloff_measured"][1] < g["rolloff_measured"][0]
    assert g["rolloff_error"] < .02
    assert g["rolloff_measured"][1] < .95

def test_four_lessons_one_real_failed_limit_and_size(result):
    spec=OCT.build_spec(result); tabs=spec["tabs"]
    assert len(tabs)==4 and all(t.get("lesson") for t in tabs)
    failed=[c for t in tabs for c in t.get("checks",[]) if not c["ok"]]
    assert len(failed)==1 and tabs[-1]["badge"]=="limit"
    html=I18N.pv._build_html(spec,["ja","en"])
    assert len(html.encode("utf-8")) <= 600000
    assert not re.search(r"https?://|www\.",html)

@pytest.fixture(scope="module")
def translated():
    spec=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    return spec,I18N.load_table(BUILDER)

def test_translation_table_is_complete(translated):
    spec,table=translated
    assert len({d["en"] for _,d in I18N.iter_texts(spec)}) >= 50
    problems,unused=I18N.audit(spec,table)
    assert problems==[] and unused==[]

def test_committed_page_is_eight_language_byte_build(translated):
    spec,table=translated
    with open(PAGE,encoding="utf-8") as f: html=f.read()
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    want=I18N.pv._build_html(I18N.translate(spec,table),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,want,PAGE,BUILDER)
