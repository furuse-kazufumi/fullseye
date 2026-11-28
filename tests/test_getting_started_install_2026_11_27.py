"""GETTING_STARTEDはPyPI利用者の手順を最初に示す。

GETTING_STARTED must lead with the copyable PyPI path in every language.
"""
from pathlib import Path


DOCS = Path(__file__).resolve().parents[1] / "docs"
PAGES = [DOCS / "GETTING_STARTED.md"] + sorted(DOCS.glob("GETTING_STARTED.*.md"))


def test_pypi_install_precedes_checkout_in_every_language():
    assert len(PAGES) == 7
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        public = text.index("pip install fullseye")
        clone = text.index("git clone https://github.com/furuse-kazufumi/fullseye")
        editable = text.index("pip install -e .")
        assert public < clone < editable, page.name
        assert text.index("fullseye --version") < clone, page.name
