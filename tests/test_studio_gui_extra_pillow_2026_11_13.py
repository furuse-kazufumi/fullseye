# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""標準インストールで Studio と見本の画像を開けることを守る回帰試験。

2026-11-24 から PySide6-Essentials と Pillow は標準依存であり、``gui`` / ``pil`` は空の互換別名である。
壊れた標準依存を検出した際は、空の extra ではなく Fullseye 自体の再インストールを案内する。
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


def test_gui_and_pil_are_empty_compatibility_aliases_for_standard_dependencies():
    ex = _extras()
    with open(ROOT / "pyproject.toml", "rb") as f:
        deps = tomllib.load(f)["project"]["dependencies"]
    assert ex["gui"] == [] and ex["pil"] == []
    assert "PySide6-Essentials>=6.5" in deps and "Pillow>=13.0" in deps


def test_setup_does_not_reinstall_standard_compatibility_aliases():
    """``fullseye setup`` は空の互換別名だけで pip を呼ばない。"""
    from fullseye import setup_cmd
    assert setup_cmd.requirements_for(["gui", "pil"]) == []


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
    assert len(dep) == 1 and dep[0]["install"] == "pip install --force-reinstall fullseye", dep


def test_with_an_op_name_the_op_stays_the_subject():
    info = se.explain_failure(ModuleNotFoundError("No module named 'PIL'", name="PIL"), op_name="xpil_offset")
    assert info["cause"]["en"].startswith("The standard dependency Pillow is missing"), info["cause"]
    assert info["cause"]["ja"].startswith("標準依存の Pillow が見つかりません"), info["cause"]
