# -*- coding: utf-8 -*-
"""配布物にローカル絶対パスを焼き込まない。

2026-09-05 のセキュリティ監査で、**非公開の兄弟プロジェクト名**が PyPI で配って
いる wheel に載っていることが分かった(`ms_human_700_jaw` / `myo_sim` /
`onocollo-complete`、および raptor と HALCON コーパスの実パス、計 7 ファイル)。

検出器そのものは記事用に既にあったのに、**出荷コードには一度も掛けていなかった**。
「門は事故の起きる場所に立てる」の型。ここで出荷ファイル全体に掛ける。

OS が定める標準フォント置き場だけは正当な絶対パスなので明示的に許す
(`annotate.FONT_CANDIDATES`)。許すものは**列挙**する ―― 黙って通す道は作らない。
"""
from __future__ import annotations

import os
import re
import sys

import pytest

# ★`tomllib` は Python 3.11 から。**モジュール先頭で素の import をすると
# 3.10 で収集が中断し、テストが 1 件も走らない** —— 2026-09-05 に hypothesis で
# 同じことを踏んだ直後に、この検査で再発させた(CI py3.10 が collection error)。
# import 失敗は必ず skip に落とす。
try:
    import tomllib
except ModuleNotFoundError:                                  # pragma: no cover (py<=3.10)
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None

pytestmark = pytest.mark.skipif(
    tomllib is None,
    reason="tomllib/tomli が無い(Python 3.11 未満)。この検査は版に依らないので 1 つで足りる")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_SEP = "[\\\\/]"
_WIN_ABS = re.compile(r"[A-Za-z]:" + _SEP + r"[\w .\-]+" + _SEP + r"[^\s\"'`)\]]*")
_NIX_HOME = re.compile(r"/(?:home|Users)/[\w.\-]+/[^\s\"'`)\]]*")

#: 正当な絶対パス。OS が置き場所を決めているものだけ。
_ALLOWED_PREFIXES = (
    "c:\\windows\\fonts\\",
    "/usr/share/fonts/",
    "/system/library/fonts/",
)


def _shipped_files():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        st = tomllib.load(f)["tool"]["setuptools"]
    out = [os.path.join(ROOT, m + ".py") for m in st["py-modules"]]
    for pkg in st.get("packages", []):
        base = os.path.join(ROOT, *pkg.split("."))
        for dirpath, _dirs, files in os.walk(base):
            out += [os.path.join(dirpath, n) for n in files if n.endswith(".py")]
    return [p for p in out if os.path.exists(p)]


def _offending_paths(text):
    for m in _WIN_ABS.findall(text) + _NIX_HOME.findall(text):
        s = m.strip()
        if not s.lower().startswith(_ALLOWED_PREFIXES):
            yield s


def test_no_shipped_file_carries_a_local_absolute_path():
    """出荷される .py に、この機械固有の絶対パスが残っていない。"""
    files = _shipped_files()
    assert len(files) > 200, "出荷ファイルの列挙に失敗している(母数 %d)" % len(files)
    bad = []
    for path in files:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for hit in _offending_paths(line):
                    bad.append("%s:%d  %s" % (os.path.relpath(path, ROOT), i, hit))
    assert not bad, (
        "配布物にローカル絶対パスが入っている(%d 件)。環境変数か引数で受けること。"
        "\n  " % len(bad) + "\n  ".join(bad[:20]))


def test_no_shipped_file_names_a_private_sibling_project():
    """兄弟プロジェクトのディレクトリ名を配布物に載せない。

    絶対パスでなくても、`projects/<name>` の形は来歴を漏らす。
    """
    pat = re.compile(r"(?:dev|projects)[\\/]([\w.\-]+)")
    public = {"imgevolve", "fullseye", "mujoco_menagerie", "myo_sim"}
    bad = []
    for path in _shipped_files():
        with open(path, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for name in pat.findall(line):
                    if name.lower() not in public and not name.startswith("<"):
                        bad.append("%s:%d  %s" % (os.path.relpath(path, ROOT), i, name))
    assert not bad, (
        "配布物が非公開の兄弟ツリー名を含んでいる(%d 件): \n  " % len(bad)
        + "\n  ".join(bad[:20]))
