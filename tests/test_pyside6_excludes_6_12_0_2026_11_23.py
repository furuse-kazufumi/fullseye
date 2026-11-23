# -*- coding: utf-8 -*-
"""PySide6 6.12.0 は、PySide6 を宣言するどの場所でも除く(2026-11-23、利用者の決定)。

根拠(A/B、同じコード): Linux CI(Python 3.11)で PySide6 6.12.0 だと full suite の 6 組が全部 SIGABRT で
止まり、gates の作業スレッドの試験が ``none_dealloc`` で落ちる。6.11.1 にした下書き #343 では止まらない。

宣言は pyproject の extras(gui ・ all)、``fullseye setup`` の代わりの表、起動とショートカットの案内文、
導入の文書(7 言語)と install/README、SBOM(pyproject から生成)。どれか 1 つでも古い ``>=6.5`` のままだと、
その入口から 6.12.0 が入る。
"""
import json
import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    tomllib = pytest.importorskip("tomli")

ROOT = Path(__file__).resolve().parents[1]
#: 除く版(Linux で SIGABRT)
EXCLUDED_PYSIDE6 = "6.12.0"
#: 宣言の正本(pyproject の gui extra と同じ文字列)
PYSIDE6_SPEC = "PySide6>=6.5,!=%s" % EXCLUDED_PYSIDE6
#: 導入の文書(どれも gui extra の表を持つ)
INSTALL_DOCS = ("INSTALL.md", "INSTALL.en.md", "INSTALL.de.md", "INSTALL.hi.md",
                "INSTALL.ko.md", "INSTALL.tw.md", "INSTALL.zh.md")
#: 版の指定つきの PySide6(``PySide6>=6.5`` など。``PySide6 製`` のような地の文は拾わない)
_PYSIDE_REQ = re.compile(r"PySide6\s*[<>=!~]=?[0-9][0-9.*]*(?:\s*,\s*[<>=!~]=?[0-9][0-9.*]*)*")


def _extras():
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["optional-dependencies"]


def test_every_pyproject_extra_that_names_pyside6_excludes_6_12_0():
    named = {k: [r for r in v if r.replace(" ", "").lower().startswith("pyside6")] for k, v in _extras().items()}
    named = {k: v for k, v in named.items() if v}
    assert set(named) >= {"gui", "all"}, named
    for extra, reqs in named.items():
        assert reqs == [PYSIDE6_SPEC], (extra, reqs)


def test_the_spec_really_refuses_6_12_0_and_allows_6_11_1():
    packaging = pytest.importorskip("packaging.requirements")
    req = packaging.Requirement(PYSIDE6_SPEC)
    assert EXCLUDED_PYSIDE6 not in req.specifier
    assert "6.11.1" in req.specifier and "6.12.1" in req.specifier and "6.5" in req.specifier
    assert "6.4.3" not in req.specifier


def test_setup_fallback_and_install_hints_use_the_same_spec():
    from fullseye import setup_cmd, shortcuts
    assert [r for r in setup_cmd._FALLBACK_REQ["gui"] if r.startswith("PySide6")] == [PYSIDE6_SPEC]
    assert shortcuts.PYSIDE6_REQUIREMENT == PYSIDE6_SPEC
    src = (ROOT / "studio.py").read_text(encoding="utf-8")
    assert 'PYSIDE6_REQUIREMENT = "%s"' % PYSIDE6_SPEC in src
    assert '"PySide6>=6.5"' not in src


@pytest.mark.parametrize("doc", INSTALL_DOCS)
def test_the_install_docs_name_the_spec(doc):
    text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
    found = _PYSIDE_REQ.findall(text)
    assert found and all(f == PYSIDE6_SPEC for f in found), (doc, found)


def test_the_installer_readme_and_shipped_code_have_no_bare_floor():
    for rel in ("install/README.md", "fullseye/setup_cmd.py", "fullseye/shortcuts.py", "studio.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        bad = [f for f in _PYSIDE_REQ.findall(text) if f != PYSIDE6_SPEC]
        assert not bad, (rel, bad)


def test_the_sbom_carries_the_exclusion():
    sbom = json.loads((ROOT / "docs" / "sbom" / "fullseye.cdx.json").read_text(encoding="utf-8"))
    rows = [c for c in sbom["components"] if c.get("name") == "pyside6"]
    assert len(rows) == 1, rows
    props = {p["name"]: p["value"] for p in rows[0].get("properties", [])}
    assert props.get("fullseye:requirement") == PYSIDE6_SPEC, props
