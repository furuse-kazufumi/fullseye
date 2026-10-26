# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""パルスオキシメータの動く 3-D 教材の物理門・8 言語門。"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import numpy as np
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[1]
BUILDER="build_pulseox_anim3d"
PAGE=ROOT/"docs"/"view2026"/"anim3d"/"pulseox_anim3d.html"

def _load(name):
    p=ROOT/"tools"/(name+".py"); s=importlib.util.spec_from_file_location(name+"_pulseox_t",p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

@pytest.fixture(scope="module")
def built():
    sys.path.insert(0,str(ROOT)) if str(ROOT) not in sys.path else None
    b=_load(BUILDER); r=b.compute(); g=b.gates(r); return b,r,g,b.build_spec(r,g)

def test_noisy_time_series_is_independent_and_recovers_ratio(built):
    b,r,g,_=built
    assert len(r["sat"])==49 and len(b._signal(.9,"red",np.linspace(0,2*np.pi,240)))==240
    assert g["r_max_error"]<.03
    assert not np.array_equal(r["extracted"],r["theory"])

def test_calibration_recovers_synthetic_truth_within_one_percent(built):
    _b,r,g,_=built
    assert len(r["estimate"])==49
    assert g["spo2_max_error"]<=.01

def test_closed_inverse_and_numerical_solution_agree(built):
    b,r,g,_=built
    assert g["inverse_error"]<1e-9
    assert max(abs(b.closed_r(b.inverse_numeric(x))-x) for x in r["theory"])<1e-12

def test_lessons_checks_and_limit_are_structural(built):
    _b,_r,g,spec=built
    assert [t["id"] for t in spec["tabs"]]==["finger","pulse","calibration","limits"]
    assert spec["tabs"][-1]["badge"]=="limit"
    for tab in spec["tabs"]:
        assert len(tab["t"])==49 and len(tab["checks"])>=3
        assert set(tab["lesson"])=={"question","choices","answer","explain","formula","limit"}
    failed=[x for x in spec["tabs"][-1]["checks"] if not x["ok"]]
    assert len(failed)==1 and "COHb" in failed[0]["what"]["en"]
    assert g["co_read"]>g["co_true"]

I18N=_load("anim3d_i18n")

def test_eight_language_page_is_complete_and_reproducible():
    spec=I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)),None)
    table=I18N.load_table(BUILDER); problems,unused=I18N.audit(spec,table)
    assert len(table["strings"])>=50 and problems==[] and unused==[]
    html=PAGE.read_text(encoding="utf-8")
    want=I18N.pv._build_html(I18N.translate(spec,table),list(I18N.LANGS),detect_lang=True)
    I18N.check_same_page(html,want,PAGE,BUILDER)
    want2=I18N.pv._build_html(I18N.translate(spec,table),list(I18N.LANGS),detect_lang=True)
    assert hashlib.sha256(want.encode()).digest()==hashlib.sha256(want2.encode()).digest()
    assert len(html.encode())<3_300_000
    data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1))
    assert data["langs"]==list(I18N.LANGS)
    public=html.split("const D = ",1)[1].split("\nconst $ = ",1)[0]
    assert not re.search(r"https?://|www\.|[A-Z]:[/\\]",public) and "**" not in public
