"""repo の全 .py が無効なエスケープ(``"A\\B"`` の ``\\B`` 等)を含まないこと。

★2026-10-24: Python 3.12 以降、文字列中の無効なエスケープは ``SyntaxWarning`` になり
(3.11 以前は ``DeprecationWarning``)、将来の版では ``SyntaxError`` になる。docstring の
``A\\B``・``a \\ b``・``Hybrid A\\*`` 等が 7 か所あった(ブラウザ版の実現性調査で 3.14 で発見)。
直し方は ``\\\\`` への二重化で、文字列の値(= op の説明・opdocs の指紋)は変えない。

検査は全 .py を ``compile`` し、出た警告のうち SyntaxWarning と「invalid escape」の
DeprecationWarning を数える。範囲が黙って縮まないよう、数えたファイル数に下限を置く。
"""
from __future__ import annotations

import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "build", "dist", ".tox",
             ".pytest_cache", ".mypy_cache", ".ruff_cache"}
#: 2026-10-24 時点で 1994 本。大きく下回ったら走査の範囲が壊れている。
MIN_FILES = 1500


def _py_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.py"):
        rel = p.relative_to(ROOT).parts
        if any(part in SKIP_DIRS or part.startswith(".pytest") for part in rel[:-1]):
            continue
        out.append(p)
    return sorted(out)


def _escape_warnings(path: Path) -> list[str]:
    src = path.read_bytes()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(src, str(path), "exec", dont_inherit=True)
    bad = []
    for w in caught:
        msg = str(w.message)
        if issubclass(w.category, SyntaxWarning) or (
                issubclass(w.category, DeprecationWarning) and "invalid escape" in msg):
            bad.append("%s:%s: %s" % (path.relative_to(ROOT).as_posix(), w.lineno, msg))
    return bad


def test_scope_is_not_empty():
    assert len(_py_files()) >= MIN_FILES


def test_no_invalid_escape_sequences_anywhere():
    bad = []
    for p in _py_files():
        bad.extend(_escape_warnings(p))
    assert not bad, "無効なエスケープ(\\\\ に二重化するか raw 文字列に):\n" + "\n".join(bad)


def test_the_gate_catches_an_invalid_escape(tmp_path):
    """門を壊して確かめる: 無効エスケープを含む源を compile すると、この検査が拾う。"""
    p = tmp_path / "bad.py"
    p.write_text('"""A' + chr(92) + 'B"""\n', encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        compile(p.read_bytes(), str(p), "exec", dont_inherit=True)
    assert any(issubclass(w.category, (SyntaxWarning, DeprecationWarning)) and "escape" in str(w.message)
               for w in caught)
