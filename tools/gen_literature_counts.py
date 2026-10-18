# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""文献層(docs/literature)に書いてある「op ノート N 本」を、docs/ops の実ファイルの数に打ち直す(regen_all の段)。

文献層の本体は RAD コーパス(repo の外)から作るので regen_all の鎖に入れられない(``tools/gen_literature_notes.py`` は
EXCLUDED)。だが **件数はコーパス無しで分かる** —— op を足すたびに 1 つずつ古びていた(INDEX は 3,307 本のまま、実際は
3,322 本)のを、鎖の中で毎回直す。実体は ``gen_literature_notes.restate_counts``。

    py -3.11 tools/gen_literature_counts.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_literature_notes as GL  # noqa: E402


def main() -> int:
    for p in GL.restate_counts():
        print("literature count restated: %s" % os.path.relpath(p, GL._ROOT))
    n_files, n_names = GL.count_op_notes(GL._ROOT)
    print("literature counts: %s notes / %s names" % (f"{n_files:,}", f"{n_names:,}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
