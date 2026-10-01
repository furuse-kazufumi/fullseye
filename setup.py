# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""wheel を組むときにだけ、op ヘルプの HTML(15,000 枚超)を 1 つの固め書きの書庫 studio_assets/op_help_html.tar.xz にする。

★2026-10-01: zip は 1 ファイルずつ圧縮するので、似たページの共通部分が消えず HTML だけで 39 MB あった(wheel 70 MB の門を越えた)。
固め書きにすると約 2.5 MB。HTML 自体は package-data から外してあり(pyproject.toml)、書庫は build_lib にだけ作る ——
リポジトリに 2.5 MB のバイナリを毎回 commit しない(履歴が太らない)。読む側は helpstore.html_root() が checkout と wheel を吸収する。
設定の本体は pyproject.toml。このファイルは build_py の差し替えだけを持つ。
"""
import os
import sys

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class build_py(_build_py):
    def run(self):
        super().run()
        import helpstore
        dst = os.path.join(self.build_lib, "studio_assets", "op_help_html.tar.xz")
        n, size = helpstore.pack_archive(helpstore.HELP_DIR, dst)
        print("helpstore: packed %d help pages into %s (%.2f MB)" % (n, dst, size / 1e6))


setup(cmdclass={"build_py": build_py})
