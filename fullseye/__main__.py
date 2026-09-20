# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``python -m fullseye ...`` runs the ``fullseye`` command-line tool (the same entry point as the
``fullseye`` console script: ``imgevolve.main``). ``python -m fullseye --help`` lists the commands.

★2026-09-20(GenSpark 第 42 報 N150 / 第 55 報): ``python -m fullseye`` が「No module named fullseye.__main__」で
止まっていた。console script が PATH に無い環境(venv を activate していない、Windows の Scripts 未登録)で
``py -3.11 -m fullseye`` は最も確実な呼び方なので、パッケージに入口を持たせる。
"""
from __future__ import annotations

import sys

from imgevolve import main

if __name__ == "__main__":
    sys.exit(main())
