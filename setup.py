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
import shutil

from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_REL_ARCHIVE = os.path.join("studio_assets", "op_help_html.tar.xz")


def _has_html(d):
    return os.path.isdir(d) and any(f.endswith(".html") for f in os.listdir(d))


class build_py(_build_py):
    """wheel に書庫を入れる。HTML があれば詰め、無ければ sdist に同梱された書庫を使う。

    ★2026-10-03: v0.3.0 の公開が止まった。``python -m build`` は **sdist を作ってから、その sdist を
    展開した木で wheel を作る**。HTML は package-data から外してあるので sdist に入らず、
    展開した木で pack_archive が「HTML が無い」で落ちた。CI の wheel 検査は ``--wheel``(checkout から
    直接)だったので、この道を一度も通っていなかった。sdist の側で書庫を同梱し、ここはそれを使う。
    """

    def run(self):
        super().run()
        import helpstore
        dst = os.path.join(self.build_lib, _REL_ARCHIVE)
        if _has_html(helpstore.HELP_DIR):
            n, size = helpstore.pack_archive(helpstore.HELP_DIR, dst)
            print("helpstore: packed %d help pages into %s (%.2f MB)" % (n, dst, size / 1e6))
        elif os.path.isfile(helpstore.ARCHIVE):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(helpstore.ARCHIVE, dst)
            print("helpstore: copied the sdist's archive into %s" % dst)
        else:
            raise SystemExit("helpstore: no op_help HTML and no %s —— 書庫の無い wheel は作らない" % _REL_ARCHIVE)


class sdist(_sdist):
    """sdist に書庫を同梱する(HTML 15,000 枚は入れない。wheel はこれから組まれる)。"""

    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        import helpstore
        dst = os.path.join(base_dir, _REL_ARCHIVE)
        n, size = helpstore.pack_archive(helpstore.HELP_DIR, dst)
        print("helpstore: packed %d help pages into the sdist (%.2f MB)" % (n, size / 1e6))


setup(cmdclass={"build_py": build_py, "sdist": sdist})
