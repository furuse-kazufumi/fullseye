"""Eight-language and byte-reproducibility gates for organ_volume.html."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILDER = "build_organvol_anim3d"
PAGE = ROOT / "docs" / "anim3d" / "organ_volume.html"


def _load(name):
    s = importlib.util.spec_from_file_location(name + "_organvol_t", ROOT / "tools" / (name + ".py"))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


I18N = _load("anim3d_i18n")


def test_table_and_page_are_complete_and_reproducible():
    spec = I18N.pick_spec(I18N.capture_specs(I18N.example_script(BUILDER)), None)
    table = I18N.load_table(BUILDER)
    problems, unused = I18N.audit(spec, table)
    assert len(table["strings"]) >= 50
    assert problems == [] and unused == []
    html = PAGE.read_text(encoding="utf-8")
    want = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    I18N.check_same_page(html, want, PAGE, BUILDER)
    want2 = I18N.pv._build_html(I18N.translate(spec, table), list(I18N.LANGS), detect_lang=True)
    assert hashlib.sha256(want.encode()).digest() == hashlib.sha256(want2.encode()).digest()
    assert len(html.encode("utf-8")) <= 3_300_000
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
    assert data["langs"] == list(I18N.LANGS)
    assert not re.search(r"https?://|www\.|[A-Z]:[/\\]", html.split("const D = ", 1)[1].split("\nconst $ = ", 1)[0])
