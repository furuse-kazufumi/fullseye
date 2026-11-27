"""公開ドキュメントに期限切れの件数や存在しないextraを載せない。
Keep public docs free of stale counts and nonexistent install extras.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GETTING_STARTED = [DOCS / "GETTING_STARTED.md"] + sorted(
    DOCS.glob("GETTING_STARTED.*.md")
)
INDEXES = sorted(DOCS.glob("README*.md"))


def test_getting_started_uses_measured_example_without_catalog_snapshots():
    """実例の結果だけ固定し、増減するカタログ件数はAPIで取得させる。
    Fix only the measured example result; obtain changing catalog counts by API.
    """
    assert len(GETTING_STARTED) == 7
    for path in GETTING_STARTED:
        text = path.read_text(encoding="utf-8")
        assert "25.0" in text, path.name
        assert "316.0" not in text, path.name
        assert "860" not in text, path.name
        assert "recipes.names()" in text, path.name


def test_generated_indexes_only_name_declared_extras_and_public_history():
    """索引のコマンドをpyprojectと照合し、非公開の作業メモを除く。
    Check index commands against pyproject and exclude private working notes.
    """
    assert len(INDEXES) == 6
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = metadata["project"]["optional-dependencies"]
    for path in INDEXES:
        text = path.read_text(encoding="utf-8")
        assert "SESSION_SUMMARY.md" not in text, path.name
        assert "| title:" not in text, path.name
        assert "| id:" not in text, path.name
        for extra in re.findall(r"fullseye\[([^\]]+)\]", text):
            assert extra in optional, (path.name, extra)
