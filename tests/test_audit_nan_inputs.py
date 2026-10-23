"""非有限入力監査の列挙、分類、保存形式を守る。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import audit_nan_inputs as audit  # noqa: E402


def test_classifier_recurses_and_distinguishes_identical_output():
    baseline = {"outer": (np.array([1.0, 2.0]), {"value": 3.0})}
    nested_nan = {"outer": (np.array([1.0, np.nan]), {"value": 3.0})}
    changed = {"outer": (np.array([1.0, 4.0]), {"value": 3.0})}
    assert audit.classify_result(nested_nan, baseline) == "propagates_nan"
    assert audit.classify_result(baseline, baseline) == "silent_identical"
    assert audit.classify_result(changed, baseline) == "silent_finite"


def test_enumeration_covers_the_whole_primary_registry():
    rows = audit.enumerate_ops()
    assert len(rows) >= 900
    assert len(rows) == len({row["name"] for row in rows})
    assert rows
    assert all({"name", "category", "in_sort", "out_sort", "module", "applicable"} <= row.keys()
               for row in rows)


def test_committed_json_schema_and_complete_enumeration():
    data = json.loads(audit.JSON_PATH.read_text(encoding="utf-8"))
    assert set(data) == {"header", "summary", "records"}
    assert data["header"]["registry_entries"] == len(data["records"]) >= 900
    assert set(data["summary"]["counts"]) == {"nan", "inf"}
    assert set(data["summary"]["counts"]["nan"]) == set(audit.OUTCOMES)
    required = {"name", "category", "in_sort", "out_sort", "module",
                "nan_outcome", "inf_outcome", "exceptions", "wrapper_behaviour",
                "warnings", "elapsed"}
    records = data["records"]
    assert records
    assert all(required == set(row) for row in records)
    # live registry は optional backend の有無(Python 版ごとの wheel)で変わる(CI 3.10/3.12 で 3.11 と差)。
    # 台帳に無い op が live に現れたら台帳が古い(落とす)。台帳にあって live に無いのは backend 不在として許す。
    committed = [row["name"] for row in records]
    live = [row["name"] for row in audit.enumerate_ops()]
    extra = sorted(set(live) - set(committed))
    assert not extra, "台帳に無い op が登録表にある(監査を回し直すこと): %s" % extra[:20]
    assert len(set(live) & set(committed)) >= 0.9 * len(committed)
    present = set(live)
    assert [n for n in committed if n in present] == live     # 共通部分の順は登録表の順


def test_markdown_is_generated_only_from_the_json():
    data = json.loads(audit.JSON_PATH.read_text(encoding="utf-8"))
    assert audit.MD_PATH.read_text(encoding="utf-8") == audit.render_markdown(data)
