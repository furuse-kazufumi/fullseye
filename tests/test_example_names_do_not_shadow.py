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


# --------------------------------------------------------------------------- #
# ★2026-10-07(同日): 範囲を 2 つ広げる。                                         #
# --------------------------------------------------------------------------- #
def test_examples_3d_namesakes_put_the_repo_first():
    """examples_3d/ の 12 本はルートと同名(render_ao.py など)で、しかも同名のモジュールを import する。

    スクリプトとして走らせると examples_3d/ が sys.path[0] になり、``import render_ao`` は**自分自身**を
    読む。いまは 12 本とも import の前に repo 直下を sys.path の先頭へ入れているので正しく動く
    (実行して確かめた)。その守りが外れた同名スクリプトが現れたら落とす。
    """
    import re
    roots = _root_import_names()
    clash = sorted(p for p in (ROOT / "examples_3d").glob("*.py") if p.stem in roots)
    assert len(clash) >= 1, "examples_3d/ の同名を数え損ねている"
    bad = []
    for p in clash:
        src = p.read_text(encoding="utf-8")
        imp = re.search(r"^(?:import %s\b|from %s import)" % (p.stem, p.stem), src, re.M)
        if imp is None:
            continue
        guard = src.find("sys.path.insert(0,")
        if guard < 0 or guard > imp.start():
            bad.append(p.name)
    assert not bad, ("examples_3d/ の同名スクリプトが、repo 直下を sys.path の先頭に入れる前に同名の"
                     "モジュールを import している(自分自身を読む): " + ", ".join(bad))


#: PyPI で広く入っているトップレベル名のうち、ここで実際に踏んだもの。インストール済みの検査は
#: 環境に入っているものしか見られないので、踏んだ名前は環境に依らず名指しで止める。
#: comm = Jupyter / ipykernel の依存。同じ site-packages ではパッケージが勝ち、
#: ``import fullseye`` が ImportError で落ちていた(0.5.0、2026-10-07 に再現)。
_KNOWN_PYPI_TOP_LEVEL = {"comm"}


def _shipped_top_level() -> set[str]:
    import re
    src = re.sub(r"#.*", "", (ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    body = re.search(r"py-modules\s*=\s*\[(.*?)\]", src, re.S)
    assert body, "pyproject.toml に py-modules が無い"
    names = set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', body.group(1)))
    assert len(names) > 300, "py-modules を途中で切っている: %d" % len(names)
    return names


def test_shipped_top_level_names_do_not_collide_with_other_distributions():
    """wheel はルートのモジュールを**トップレベル**で site-packages に置く。他の配布物と同名なら、
    どちらかがもう片方を黙って隠す。stdlib・既知の衝突名・この環境に入っている配布物の名前と照合する。"""
    import importlib.metadata as md
    import sys
    shipped = _shipped_top_level()
    others: dict[str, set[str]] = {}
    for d in md.distributions():
        name = (d.metadata["Name"] or "").lower()
        if name in ("fullseye", "imgevolve"):
            continue
        tops = set((d.read_text("top_level.txt") or "").split())
        for f in d.files or ():
            parts = str(f).replace("\\", "/").split("/")
            if len(parts) > 1 and not parts[0].endswith((".dist-info", ".data", ".egg-info")):
                tops.add(parts[0])
            elif parts[0].endswith(".py"):
                tops.add(parts[0][:-3])
        for t in tops:
            others.setdefault(t, set()).add(name)
    assert len(others) > 20, "インストール済みの配布物を数え損ねている: %d" % len(others)
    clash = sorted(shipped & (set(sys.stdlib_module_names) | _KNOWN_PYPI_TOP_LEVEL | set(others)))
    assert not clash, ("配布するトップレベル名が他と衝突: "
                       + ", ".join("%s(%s)" % (c, ",".join(sorted(others.get(c, {"stdlib/既知"})))) for c in clash))
