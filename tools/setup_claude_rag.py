"""Claude Code 向け RAG セットアップ(checkout 用エントリポイント)。

実体は :mod:`fullseye.rag_setup`(PyPI 配布では ``fullseye-rag`` console script)。
このファイルは checkout から ``py -3.11 tools/setup_claude_rag.py`` で呼ぶための
薄いシムで、リポジトリ root を明示的に固定する(fail-closed: docs/ops の無い
checkout ではインストール拒否 — 壊れた RAG を配らない)。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# re-exports: tools/update_fullseye.py と tests がこのシム経由で使う
from fullseye.rag_setup import (  # noqa: F401
    _REPO_LINE,
    SKILL_NAME,
    default_target,
    uninstall,
)
from fullseye.rag_setup import install as _install
from fullseye.rag_setup import main as _main

SKILL_SRC = REPO / "skills" / SKILL_NAME


def install(target_dir: Path, backup: bool = True) -> Path:
    return _install(target_dir, repo=REPO, _auto_repo=False, backup=backup)


def main(argv=None) -> int:
    return _main(argv)


if __name__ == "__main__":
    sys.exit(main())
