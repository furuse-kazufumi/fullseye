from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _audit_module():
    path = ROOT / "tools" / "audit_file_formats.py"
    spec = importlib.util.spec_from_file_location("audit_file_formats", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_file_format_report_is_generated_and_current():
    audit = _audit_module()
    report = audit.build_report()
    assert report == (ROOT / "docs" / "FILE_FORMATS.md").read_text(encoding="utf-8")
    assert "| `.ply` |" in report
    assert "mesh.read_mesh" in report


def test_file_format_counts_come_from_rows():
    audit = _audit_module()
    rows = audit._source_inventory()
    assert len(rows) >= 20
    assert rows[".stl"]["read"]
    assert rows[".stl"]["write"]
