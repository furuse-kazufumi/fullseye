from __future__ import annotations
import hashlib, importlib.util, json, pathlib, re, sys
import numpy as np
import pytest
ROOT=pathlib.Path(__file__).resolve().parents[1]; BUILDER="build_usound_anim3d"
PAGE=ROOT/"docs"/"view2026"/"anim3d"/"ultrasound_bmode_anim3d.html"
def _load(name):
 p=ROOT/"tools"/(name+".py"); s=importlib.util.spec_from_file_location(name+"_usound_t",p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
@pytest.fixture(scope="module")
def built():
 if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
 b=_load(BUILDER); r=b.compute(); g=b.gates(r); return b,r,g,b.build_spec(r,g)
def test_rf_and_beamforming_are_observation_driven(built):
 b,r,_g,_s=built
 assert r["rf"].shape==(24,1320) and len(r["x"])>100
 assert r["good"].shape==(768,224) and not np.array_equal(r["good"],r["bad"])
 assert (r["zs"][1]-r["zs"][0])<b.C0/b.FC/8 and (r["xs"][1]-r["xs"][0])<b.C0/b.FC/4
def test_image_measurements_pass_numeric_gates(built):
 b,r,g,_s=built
 assert g["ax_diff"]<.30*g["ax_closed"]
 assert np.all(np.abs(g["lat_obs"]-g["lat_closed"])<.30*g["lat_closed"])
 assert g["gooderr"]<b.C0/b.FC and g["speed_diff"]<2*(r["zs"][1]-r["zs"][0])
 assert len(r["mg"])==3 and len(r["mb"])==3
 assert g["scatterers_per_cell"]>=10 and r["cyst_count"]>100 and r["bg_count"]>100
 assert abs(g["cnr"]-g["cnr_theory"])<.35*g["cnr_theory"]
def test_lessons_checks_and_intentional_limit(built):
 _b,_r,_g,spec=built
 assert [t["id"] for t in spec["tabs"]]==["echo","rf","image","limits"]
 assert all(len(t["t"])==36 and len(t["checks"])>=4 for t in spec["tabs"])
 assert all(set(t["lesson"])=={"question","choices","answer","explain","formula","limit"} for t in spec["tabs"])
 failed=[x for x in spec["tabs"][-1]["checks"] if not x["ok"]]
 assert len(failed)==1 and "bone" in failed[0]["what"]["en"]
def test_eight_language_page_is_complete_small_and_reproducible():
 I=_load("anim3d_i18n"); spec=I.pick_spec(I.capture_specs(I.example_script(BUILDER)),None); table=I.load_table(BUILDER)
 problems,unused=I.audit(spec,table); assert len(table["strings"])>=50 and problems==[] and unused==[]
 html=PAGE.read_text(encoding="utf-8"); want=I.pv._build_html(I.translate(spec,table),list(I.LANGS),detect_lang=True)
 I.check_same_page(html,want,PAGE,BUILDER); want2=I.pv._build_html(I.translate(spec,table),list(I.LANGS),detect_lang=True)
 assert hashlib.sha256(want.encode()).digest()==hashlib.sha256(want2.encode()).digest()
 assert len(html.encode())<600_000
 data=json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ",html,re.S).group(1)); assert data["langs"]==list(I.LANGS)
 public=html.split("const D = ",1)[1].split("\nconst $ = ",1)[0]
 assert not re.search(r"https?://|www\.|[A-Z]:[/\\]",public) and "**" not in public
