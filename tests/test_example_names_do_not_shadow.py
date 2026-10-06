# -*- coding: utf-8 -*-
"""examples/ のスクリプト名が、ルートのモジュール名と**被らない**ことの門。

2026-10-07: 全体スイートでだけ公開経路の門(test_public_reachability の 2 本)が落ち、単独では通った。
原因は ``examples/event_camera.py``(フレームからイベント表現を作るデモ)がルートの ``event_camera.py``
(MuJoCo の DVS デモ・unified の op)と同名だったこと。PoC や一部のテストは examples/ を sys.path に足す
ので、その後の ``import event_camera`` は**どちらが先に入ったか**で別物を返し、xdist のワーカーへの
振り分け次第で「公開経路から呼べないモジュールが増えた」「不可視な関数が 844 -> 845」と出ていた。
2026-10-02 にも同じ取り違えで test_sensor_sims が落ちており(test_kendama_combo.py の注記)、
そのときは sys.path を汚す側を直しただけで、名前の衝突そのものは残っていた。

直し方は名前を分けること(デモを ``events_from_frames.py`` へ改名)。この門は再発を止める:
sys.path を汚す経路を 1 本ずつ塞ぐより、**衝突できる名前を作らない**方が確実なので。
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _root_import_names() -> set[str]:
    """ルートから ``import <名前>`` で届くもの: ルートの .py と、__init__.py を持つディレクトリ。"""
    names = {p.stem for p in ROOT.glob("*.py")}
    names |= {p.parent.name for p in ROOT.glob("*/__init__.py")}
    return names


def test_root_has_modules_to_compare_against():
    # 母集団が空なら下の門は何も見ていない(数え損ねを先に止める)
    names = _root_import_names()
    assert len(names) > 300, "ルートのモジュールを数え損ねている: %d" % len(names)
    assert "event_camera" in names and "fullseye" in names


def test_no_example_script_shadows_a_root_module():
    examples = sorted(p.stem for p in (ROOT / "examples").glob("*.py") if p.stem != "__init__")
    assert len(examples) > 100, "examples/ を数え損ねている: %d" % len(examples)
    clash = sorted(set(examples) & _root_import_names())
    assert not clash, (
        "examples/ のスクリプトがルートのモジュールと同名: " + ", ".join(clash) + "\n"
        "  examples/ が sys.path に入った後の import が実行順で別物を返す。スクリプト側を改名すること。")
