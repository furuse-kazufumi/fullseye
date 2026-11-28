"""INSTALLのextras表をpyproject.tomlの宣言と機械的に照合する。

Compare every localized INSTALL extras table mechanically with pyproject.toml.
"""
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES = [DOCS / "INSTALL.md"] + sorted(DOCS.glob("INSTALL.*.md"))
BLOCK = re.compile(r"<!-- extras-table:start -->(.*?)<!-- extras-table:end -->", re.DOTALL)
ROW = re.compile(r"^\| `([^`]+)` \| (.*?) \|$", re.MULTILINE)


def _documented(path: Path) -> dict[str, list[str]]:
    """表を{extra: 依存文字列}へ戻す。 / Parse one table into dependency strings."""
    match = BLOCK.search(path.read_text(encoding="utf-8"))
    assert match, path.name
    out = {}
    for name, cell in ROW.findall(match.group(1)):
        out[name] = [] if cell == "—" else re.findall(r"`([^`]+)`", cell)
    return out


def test_every_install_extras_table_matches_pyproject():
    expected = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    assert len(PAGES) == 7
    for page in PAGES:
        assert _documented(page) == expected, page.name
