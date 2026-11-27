# -*- coding: utf-8 -*-
"""Windows の根付きの形は、どの OS でもプロジェクトの名前として断る(2026-11-23)。

Linux CI で ``test_paths_outside_the_project_are_refused`` が DID NOT RAISE になった。原因は
``resolve_inside`` / ``validate_name`` が ``os.path`` (Linux では posixpath)で絶対・ドライブを見ていた事で、
``C:\\x`` ・ ``C:x`` ・ ``\\\\srv\\share\\x`` ・ ``\\x`` が「プロジェクトの中の、そういう名前のファイル」として通った。
Linux では realpath による中か外かの検査が効いていて外へは出なかった(WSL で確かめた)が、同じ名前は
Windows では根付きになる。字句の拒否を OS に依らない形にした。

ここでは ``studio_project.os.path`` を posixpath に差し替えて、Windows の上でも Linux の意味で検査する
(Linux では差し替えても同じ)。
"""
import os
import posixpath

import pytest

import studio_project as sp

#: Linux の os.path では「普通の名前」に見える、Windows の根付きの形
WINDOWS_ROOTED_FORMS = (
    "C:\\x", "C:x", "c:/x", "\\\\srv\\share\\x", "//srv/share/x", "\\x", "\\\\?\\C:\\x",
)


@pytest.fixture
def posix_semantics(monkeypatch):
    """studio_project の os.path を posixpath にする(Linux の意味)。"""
    monkeypatch.setattr(sp.os, "path", posixpath)
    yield


def test_resolve_inside_refuses_windows_rooted_forms_with_posix_path_semantics(tmp_path, posix_semantics):
    root = posixpath.join(str(tmp_path).replace("\\", "/"), "proj")
    os.makedirs(root)
    for bad in WINDOWS_ROOTED_FORMS:
        with pytest.raises(ValueError):
            sp.resolve_inside(root, bad)
    assert sp.resolve_inside(root, "pipelines/a.json").endswith("/proj/pipelines/a.json")


def test_validate_name_refuses_windows_rooted_forms_with_posix_path_semantics(posix_semantics):
    for bad in WINDOWS_ROOTED_FORMS:
        with pytest.raises(ValueError):
            sp.validate_name(bad)
    assert sp.validate_name("ok name.json") == "ok name.json"


def test_resolve_inside_refuses_windows_rooted_forms_on_this_os(tmp_path):
    root = str(tmp_path / "proj")
    os.makedirs(root)
    for bad in WINDOWS_ROOTED_FORMS:
        with pytest.raises(ValueError):
            sp.resolve_inside(root, bad)
