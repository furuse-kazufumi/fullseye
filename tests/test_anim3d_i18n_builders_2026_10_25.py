# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anim3d_i18n が examples / examples_3d の作例だけでなく ``tools/build_*`` の生成器も扱える門(2026-10-25)。

題材の動く 3-D は ``tools/build_*_anim3d.py`` に置かれ、既定で ``docs/anim3d/*.html`` を書く。翻訳の層は
それを探せること、走らせても repo に書かないこと(write_viewer は一時フォルダへ、他の書き込みは木の比較で
止める)、``main(argv)`` に引数を渡せること、CLI の ``--missing`` が同じに働くことを確かめる。
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_builders_t", os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


I18N = _load("anim3d_i18n")

#: 題材の生成器の見本: 既定で <root>/docs/anim3d/<id>.html を書き、--id で仕様の id を変え、--stray で
#: 余計なファイルを repo に書く。書いたパスが実在することを main の中で確かめる(作例自身の検査の代わり)。
_BUILDER = textwrap.dedent('''
    import argparse, os, sys
    from pathlib import Path
    import pocviewer as pv

    ROOT = Path(__file__).resolve().parents[1]

    def spec(vid):
        t = pv.viewer_text
        tab = pv.viewer_split_tab("s", t("箱", "Box"), "passed", t("残像 1.2 s", "Trail 1.2 s"),
                                  [[0, 1], [2, 3]], [[3, 2], [1, 0]], t("前", "Before"), t("後", "After"))
        return pv.viewer_spec(vid, t("見本", "Sample"), t("副題", "Sub"), t("回す", "Rotate"), [tab])

    def main(argv=None):
        ap = argparse.ArgumentParser()
        ap.add_argument("--id", default="demo")
        ap.add_argument("--stray", action="store_true")
        a = ap.parse_args(argv)
        out = ROOT / "docs" / "anim3d" / (a.id + ".html")
        path = pv.write_viewer(spec(a.id), str(out), ["ja", "en"])
        assert os.path.isfile(path), path
        if a.stray:
            (ROOT / "stray.txt").write_text("x", encoding="utf-8")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())
''')


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """examples/ と tools/ を持つ小さな repo を ROOT に見せる(翻訳表も ROOT の下)。"""
    (tmp_path / "examples").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "examples" / "ex_sample.py").write_text("def main(argv=None):\n    return 0\n", encoding="utf-8")
    (tmp_path / "tools" / "build_demo_anim3d.py").write_text(_BUILDER, encoding="utf-8")
    (tmp_path / "tools" / "demo_helper.py").write_text(_BUILDER, encoding="utf-8")   # build_ で始まらない
    monkeypatch.setattr(I18N, "ROOT", tmp_path)
    monkeypatch.setattr(I18N, "TABLES", tmp_path / "tools" / "anim3d_i18n_tables")
    return tmp_path


def test_example_script_finds_examples_and_tools_builders_only(repo):
    assert I18N.example_script("ex_sample") == repo / "examples" / "ex_sample.py"
    assert I18N.example_script("build_demo_anim3d") == repo / "tools" / "build_demo_anim3d.py"
    with pytest.raises(FileNotFoundError, match="build_"):
        I18N.example_script("demo_helper")                 # tools/ の build_* 以外は作例ではない
    for bad in ("../tools/build_demo_anim3d", "tools/build_demo_anim3d", "build_demo_anim3d.py", ""):
        with pytest.raises(ValueError):
            I18N.example_script(bad)


def test_builder_is_captured_without_writing_into_the_repo(repo):
    specs = I18N.capture_specs(I18N.example_script("build_demo_anim3d"))
    assert [s["id"] for s in specs] == ["demo"]
    assert not (repo / "docs").exists(), "翻訳の確認で docs/anim3d に書いてしまった"
    texts = {d["en"] for _, d in I18N.iter_texts(specs[0])}
    assert {"Box", "Trail 1.2 s", "Sample"} <= texts


def test_script_args_reach_main_and_viewer_id_picks(repo):
    specs = I18N.capture_specs(I18N.example_script("build_demo_anim3d"), ["--id", "other"])
    assert I18N.pick_spec(specs, "other")["id"] == "other"
    with pytest.raises(ValueError):
        I18N.pick_spec(specs, "demo")


def _git(root, *a):
    subprocess.run(["git", *a], cwd=root, check=True, capture_output=True, stdin=subprocess.DEVNULL)


def test_a_builder_that_writes_into_the_tree_is_stopped(repo):
    (repo / ".gitignore").write_text("__pycache__/" + chr(10), encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    assert I18N._tree_state(repo) == {}
    I18N.capture_specs(I18N.example_script("build_demo_anim3d"))          # write_viewer だけなら木は同じ
    with pytest.raises(RuntimeError, match="stray.txt"):
        I18N.capture_specs(I18N.example_script("build_demo_anim3d"), ["--stray"])


def test_cli_missing_and_check_work_on_a_builder(repo, capsys):
    assert I18N.main(["--missing", "build_demo_anim3d", "--script-arg=--id", "--script-arg=cli"]) == 0
    js = json.loads(capsys.readouterr().out)
    assert js["example"] == "build_demo_anim3d"
    assert js["table"] == "tools/anim3d_i18n_tables/build_demo_anim3d.json"
    assert len(js["strings"]) == js["missing"] and {"Box", "Trail 1.2 s", "Sample"} <= set(js["strings"])
    assert I18N.main(["--check", "build_demo_anim3d"]) == 1                 # 表が無い = 未訳で止まる
    assert "未訳" in capsys.readouterr().err
