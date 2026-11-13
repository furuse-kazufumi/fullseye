# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio を README のとおり ``[gui]`` で入れると、見本の画像が開けなかった(2026-11-13、配布物の検証 M1)。

``gui = ["PySide6>=6.5"]`` だけで画像の復号器(Pillow / OpenCV)が入らず、Studio の「最初の 3 手」の 1 手目
(見本の画像を開く)が ``No module named 'PIL'`` で失敗した。そのダイアログの原因の文は op 名の無い失敗で主語が
「?」になっていた("Cause ? needs the optional package Pillow")。
"""
from __future__ import annotations

import importlib.abc
import sys
import tomllib
from pathlib import Path

import sample_images
import studio_errors as se

ROOT = Path(__file__).resolve().parents[1]


class _NotInstalled(importlib.abc.MetaPathFinder):
    """名前の挙がったパッケージを「入っていない」ことにする(本物と同じ ``No module named 'X'`` を上げる)。

    ``sys.modules[name] = None`` だと文面が ``import of X halted`` になり、入っていない環境の文面と違う。
    """

    def __init__(self, *names):
        self.names = set(names)

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in self.names:
            raise ModuleNotFoundError("No module named %r" % fullname, name=fullname)
        return None


def _not_installed(monkeypatch, *names):
    for key in [k for k in sys.modules if k.split(".")[0] in names]:
        monkeypatch.delitem(sys.modules, key)
    monkeypatch.setattr(sys, "meta_path", [_NotInstalled(*names)] + sys.meta_path)


def _extras() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["optional-dependencies"]


def test_the_gui_extra_carries_pillow_with_the_same_floor_as_the_pil_extra():
    ex = _extras()
    pil = [r for r in ex["pil"] if r.lower().startswith("pillow")]
    gui = [r for r in ex["gui"] if r.lower().startswith("pillow")]
    assert len(pil) == 1 and gui == pil, (ex["gui"], ex["pil"])
    assert [r for r in ex["gui"] if r.startswith("PySide6")] == ["PySide6>=6.5"], ex["gui"]


def test_setup_falls_back_to_the_same_gui_requirements_as_the_extra():
    """``fullseye setup`` が配布物のメタデータを読めない時(checkout 直読み)の代わりの表も同じ物を入れる。"""
    from fullseye import setup_cmd
    assert setup_cmd._FALLBACK_REQ["gui"] == _extras()["gui"]


def test_a_missing_decoder_while_opening_a_sample_reads_as_a_sentence_with_a_subject(monkeypatch):
    # 復号器の無い環境を作り、本物の sample_images.load を本物の見本で落とす(例外の文面を写さない)
    _not_installed(monkeypatch, "cv2", "PIL")
    try:
        sample_images.load("coins")
    except Exception as e:                       # noqa: BLE001 - 下で中身を確かめる
        err = e
    else:
        raise AssertionError("cv2 も PIL も無いのに見本が読めた(探針が効いていない)")
    assert "No module named 'PIL'" in str(err), err
    # Studio の load_sample_image が report_error に渡す形(見本の名前 + 空行 + 例外の文)
    info = se.explain_failure(RuntimeError("%s\n\n%s" % ("coins", err)))
    assert info["class"] == "dependency", info["class"]
    en, ja = info["cause"]["en"], info["cause"]["ja"]
    assert "Pillow" in en and "Pillow" in ja, (en, ja)
    assert not en.startswith("?") and "? needs" not in en and not ja.startswith("?"), (en, ja)
    shown = se.format_failure(info, "en")
    assert "Pillow" in shown and "? needs" not in shown, shown
    dep = [e for e in info["evidence"] if e["kind"] == "dependency"]
    assert len(dep) == 1 and dep[0]["install"] == 'pip install "fullseye[pil]"', dep


def test_with_an_op_name_the_op_stays_the_subject():
    info = se.explain_failure(ModuleNotFoundError("No module named 'PIL'", name="PIL"), op_name="xpil_offset")
    assert info["cause"]["en"].startswith("xpil_offset needs the optional package Pillow"), info["cause"]
    assert info["cause"]["ja"].startswith("xpil_offset に必要な"), info["cause"]
