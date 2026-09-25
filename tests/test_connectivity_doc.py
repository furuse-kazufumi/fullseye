# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`docs/CONNECTIVITY.md` が名乗る数を、全部そのまま実装と突き合わせる門。

★2026-09-25 の実測: この文書には**数を名乗る節が 7 つ**あるのに、実装と
突き合わされていたのは **`画像取り込み (acquire)` の 1 つだけ**だった。
その 1 つに門を置いたとき(2026-09-24)何が出たかというと、**表は 9 行のまま
陳腐化しており、しかも 4 件は「対応」と書いてあるのに開けなかった**。
同じ構造の表が隣に 6 つ在って、誰も見ていなかったことになる。

実測では**今日の時点では全部合っている**(comm 23 / acquire 10 / 画素 59 /
SFNC 31 / UVC 49 / 8 軸 / device 12)。つまりここで直すのは「ずれ」ではなく
**門の不在**である —— 合っていることと、次に足す人を止めるものが在ることは別。

★**新しい節を足したら、この門に登録するまで落ちる。** 免除は理由つきで名指しする
(表を空にすると、門は何も見ていないのと同じになる)。
"""
from __future__ import annotations

import io
import json
import os
import re

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import acquire  # noqa: E402
import comm  # noqa: E402
import device  # noqa: E402

DOC = os.path.join(_ROOT, "docs", "CONNECTIVITY.md")
PFNC = os.path.join(_ROOT, "examples", "data", "pfnc_single_plane.json")

#: 見出しが名乗る件数 `(23)` / `(単板 59 形式)` / `(SFNC 31 機能)` / `(8/8)`。
_NUM = re.compile(r"\d+")
#: 表のなかの ``名前`` (バッククォート)
_TICKED = re.compile(r"`([^`]+)`")


#: 表の ✓ / — を真偽に読む。**空欄や別の記号は通さない** —— 読めない印を
#: 「False」と読むと、書き間違えた行が静かに緑になる。
def _tick(cell: str) -> bool:
    cell = (cell or "").strip()
    assert cell in ("\u2713", "\u2014"), "実装欄は ✓ か — のどちらか: %r" % cell
    return cell == "\u2713"


def _text() -> str:
    return io.open(DOC, encoding="utf-8").read()


def _sections(text: str) -> dict:
    """`## ` 見出し -> その節の本文。節の終わりは**次の見出し**である。

    ★特定の見出しの名前を決め打つと、あいだに節を 1 つ足しただけで次の表の行まで
    読んでしまう(acquire の門で実際に踏んだ)。
    """
    out, lines = {}, text.splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    for k, i in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(lines)
        out[lines[i][3:].strip()] = "\n".join(lines[i:end])
    return out


def _rows(section: str) -> list:
    """表の行(見出し行と罫線を除く)をセルの list にして返す。"""
    out = []
    for ln in section.splitlines():
        if not ln.startswith("| ") or "|---" in ln:
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        out.append(cells)
    return out[1:] if out else []          # 先頭は列名の行


def _heading_numbers(heading: str) -> list:
    return [int(x) for x in _NUM.findall(heading)]


# --------------------------------------------------------------------------- #
# 節ごとの突き合わせ                                                             #
# --------------------------------------------------------------------------- #
def _check_comm(heading: str, section: str) -> None:
    caps = {c["name"]: c for c in comm.capabilities()}
    assert _heading_numbers(heading) == [len(caps)], (
        "見出しの件数が実装の %d と食い違う: %r" % (len(caps), heading))
    listed = {r[0]: r for r in _rows(section)}
    assert set(listed) == set(caps), (
        "表と実装でプロトコルの名前が食い違う(表のみ %s / 実装のみ %s)"
        % (sorted(set(listed) - set(caps)), sorted(set(caps) - set(listed))))
    for name, cells in sorted(listed.items()):
        assert cells[1] == caps[name]["kind"], (
            "%s の kind が食い違う: 表 %r / 実装 %r" % (name, cells[1], caps[name]["kind"]))
        #: ★ここは長いあいだ `あり`(= その lib が import できるか)の欄で、
        #:   **機械ごとに違うので門が見られなかった** —— 誰も検査しない欄が表に
        #:   1 列在る状態だった(しかも中身は `kind == native` の写しで、pyserial を
        #:   入れた機械では嘘になる)。2026-09-25 に「実装」(Fullseye 自身が開けるか)
        #:   へ替えた。**版で決まる**ので、どの機械でも同じ答えになる。
        assert _tick(cells[2]) == caps[name]["implemented"], (
            "%s の実装欄が食い違う: 表 %r / 実装 %r"
            % (name, cells[2], caps[name]["implemented"]))
        pip = cells[3] if cells[3] != "—" else None
        assert pip == (caps[name].get("pip") or None), (
            "%s の pip が食い違う: 表 %r / 実装 %r" % (name, pip, caps[name].get("pip")))


def _check_device(heading: str, section: str) -> None:
    caps = {c["name"]: c for c in device.capabilities()}
    assert _heading_numbers(heading) == [len(caps)], (
        "見出しの件数が実装の %d と食い違う: %r" % (len(caps), heading))
    listed = {r[0]: r for r in _rows(section)}
    assert set(listed) == set(caps), (
        "表と実装で driver の名前が食い違う(表のみ %s / 実装のみ %s)"
        % (sorted(set(listed) - set(caps)), sorted(set(caps) - set(listed))))
    for name, cells in sorted(listed.items()):
        assert cells[1] == caps[name]["kind"], (
            "%s の kind が食い違う: 表 %r / 実装 %r" % (name, cells[1], caps[name]["kind"]))
        assert cells[2] == caps[name]["family"], (
            "%s の種別が食い違う: 表 %r / 実装 %r" % (name, cells[2], caps[name]["family"]))
        assert _tick(cells[3]) == caps[name]["implemented"], (
            "%s の実装欄が食い違う: 表 %r / 実装 %r"
            % (name, cells[3], caps[name]["implemented"]))
        pip = cells[4] if cells[4] != "—" else None
        assert pip == (caps[name].get("pip") or None), (
            "%s の pip が食い違う: 表 %r / 実装 %r" % (name, pip, caps[name].get("pip")))


def _check_pixel_formats(heading: str, section: str) -> None:
    with io.open(PFNC, encoding="utf-8") as f:
        formats = json.load(f)["formats"]
    assert _heading_numbers(heading) == [len(formats)], (
        "見出しの形式数が台帳の %d と食い違う: %r" % (len(formats), heading))
    for cells in _rows(section):
        group = cells[0]
        total = [n for n in formats if n.startswith(group)]
        dropped = [n for n in acquire.NOT_CARRIED if n.startswith(group)]
        assert len(total) == int(cells[1]), (
            "%s の規格数が台帳の %d と食い違う: 表 %s" % (group, len(total), cells[1]))
        assert len(dropped) == int(cells[3]), (
            "%s の「外した」が NOT_CARRIED の %d と食い違う: 表 %s"
            % (group, len(dropped), cells[3]))
        assert len(total) - len(dropped) == int(cells[2]), (
            "%s の対応数が %d と食い違う: 表 %s" % (group, len(total) - len(dropped), cells[2]))


def _check_sfnc(heading: str, section: str) -> None:
    n = len(acquire.SFNC_FEATURES)
    assert n in _heading_numbers(heading), (
        "見出しの機能数が実装の %d と食い違う: %r" % (n, heading))


def _check_uvc(heading: str, section: str) -> None:
    n = len(acquire.UVC_CONTROLS)
    assert n in _heading_numbers(heading), (
        "見出しの制御数が実装の %d と食い違う: %r" % (n, heading))


def _check_axes(heading: str, section: str) -> None:
    axes = acquire.COVERAGE_AXES
    rows = _rows(section)
    assert len(rows) == len(axes), (
        "表の軸が %d 本、実装は %d 本" % (len(rows), len(axes)))
    #: 見出しは「8 軸 (8/8)」で 8 が 3 回出る。**どれも軸数**でなければならない。
    assert set(_heading_numbers(heading)) == {len(axes)}, (
        "見出しの数が実装の軸数 %d と食い違う: %r" % (len(axes), heading))
    #: ★入口の名前は**実装の台帳から**引く。表に手で書いた名前が古くなると、
    #:   「証拠が消えた対応済み」になる。
    in_doc = set()
    for cells in rows:
        in_doc |= set(_TICKED.findall(cells[2]))
    in_impl = {name for names in axes.values() for name in names}
    assert in_doc == in_impl, (
        "表の入口と実装の入口が食い違う(表のみ %s / 実装のみ %s)"
        % (sorted(in_doc - in_impl), sorted(in_impl - in_doc)))


#: 節 -> 突き合わせ。見出しの**前方一致**で引く(見出しは件数を含むので完全一致にしない)。
CHECKS = {
    "通信プロトコル (comm)": _check_comm,
    "画素形式": _check_pixel_formats,
    "カメラの機能名": _check_sfnc,
    "webcam の機能名": _check_uvc,
    "取り込み層の 8 軸": _check_axes,
    "デバイス制御 (device)": _check_device,
}

#: 免除は**理由つきで名指し**する。
EXEMPT = {
    "画像取り込み (acquire)":
        "tests/test_acquire_contract.py::test_the_connectivity_doc_lists_exactly_"
        "the_implemented_backends が件数・名前・単位・pip・列挙可否まで見る",
    "使い方(native はすぐ動く)": "手順の説明で、数も表も名乗っていない",
}


def _checker(heading: str):
    for key, fn in CHECKS.items():
        if heading.startswith(key):
            return fn
    return None


@pytest.mark.parametrize("heading", sorted(CHECKS))
def test_each_counted_section_matches_the_implementation(heading):
    sections = _sections(_text())
    found = [h for h in sections if h.startswith(heading)]
    assert len(found) == 1, "見出し %r が %d 個" % (heading, len(found))
    CHECKS[heading](found[0], sections[found[0]])


#: ★門を壊して確かめる —— 「通るだけの門」と「何も見ていない門」は区別できない。
#: (節, 壊し方, 期待する文言)。壊すのは**表の側**で、判定は本物の関数を呼ぶ。
_BREAKS = [
    ("通信プロトコル (comm)", lambda s: "\n".join(
        ln for ln in s.splitlines() if not ln.startswith("| mqtt")), "名前が食い違う"),
    ("通信プロトコル (comm)", lambda s: s.replace("paho-mqtt", "paho-mqtt-x"),
     "pip が食い違う"),
    ("デバイス制御 (device)", lambda s: s.replace("| optional |", "| native |", 1),
     "kind が食い違う"),
    #: ★実際に踏んだ形 —— 名簿には載るが開けない driver を「開ける」と書く。
    ("デバイス制御 (device)",
     lambda s: s.replace("| canopen | optional | motion | \u2014 |",
                         "| canopen | optional | motion | \u2713 |", 1),
     "実装欄が食い違う"),
    ("通信プロトコル (comm)",
     lambda s: s.replace("| mqtt | optional | \u2014 |",
                         "| mqtt | optional | \u2713 |", 1),
     "実装欄が食い違う"),
    ("通信プロトコル (comm)",
     lambda s: s.replace("| mqtt | optional | \u2014 |",
                         "| mqtt | optional | ? |", 1),
     "\u2713 か \u2014"),
    ("画素形式", lambda s: s.replace("| Mono | 15 | 10 | 5 |", "| Mono | 15 | 11 | 4 |"),
     "食い違う"),
    ("取り込み層の 8 軸", lambda s: s.replace("`Camera.close`", "`Camera.shutdown`"),
     "入口が食い違う"),
]


@pytest.mark.parametrize("key,break_it,want", _BREAKS)
def test_the_section_gates_catch_a_table_that_drifted(key, break_it, want):
    sections = _sections(_text())
    heading = next(h for h in sections if h.startswith(key))
    with pytest.raises(AssertionError) as e:
        CHECKS[key](heading, break_it(sections[heading]))
    assert want in str(e.value), str(e.value)


def test_a_heading_that_lies_about_its_count_is_caught():
    """見出しの数だけを書き換えても落ちること(表を直して見出しを忘れる型)。"""
    sections = _sections(_text())
    heading = next(h for h in sections if h.startswith("カメラの機能名"))
    with pytest.raises(AssertionError) as e:
        _check_sfnc(heading.replace(str(len(acquire.SFNC_FEATURES)),
                                    str(len(acquire.SFNC_FEATURES) + 1)), sections[heading])
    assert "機能数" in str(e.value)


def _assert_every_section_is_watched(sections: dict) -> None:
    """★どの節にも門が在るか、理由つきで免除されているか(門の本体)。"""
    orphan = [h for h in sections
              if _checker(h) is None
              and not any(h.startswith(k) for k in EXEMPT)]
    assert not orphan, (
        "この表には門が無い: %s —— CHECKS に足すか、EXEMPT に理由つきで名指しすること"
        % ", ".join(orphan))


def test_every_section_of_the_doc_is_watched():
    _assert_every_section_is_watched(_sections(_text()))


def test_the_orphan_gate_catches_a_new_unwatched_section():
    """★門を壊して確かめる —— 登録していない節を足したら落ちること。"""
    sections = dict(_sections(_text()))
    sections["対応 SDK 一覧 (99)"] = "| a | b |\n|---|---|\n| x | y |"
    with pytest.raises(AssertionError) as e:
        _assert_every_section_is_watched(sections)
    assert "門が無い" in str(e.value)


def test_the_exemptions_name_sections_that_actually_exist():
    """免除の側も実在を確かめる —— 消えた節の免除が残ると、表は長いのに何も見ない。"""
    sections = _sections(_text())
    for key, why in EXEMPT.items():
        assert any(h.startswith(key) for h in sections), "免除に在るが節が無い: %r" % key
        assert why.strip(), "免除の理由が空: %r" % key


# --------------------------------------------------------------------------- #
# facade の説明文が名乗る数                                                      #
# --------------------------------------------------------------------------- #
#: ``fullseye.capabilities()`` の docstring は **wheel に入る**。2026-09-25 まで
#: そこは image sources を **9** と書いており、zed と kinect を数えていなかった。
#: 3 つの数は滅多に動かない(新しい backend は出来事である)ので、数は残して
#: 門で留める —— 動いたときに気づけるほうが役に立つ。
_FACADE_RE = re.compile(
    r"protocols \((\d+)\), image sources \((\d+)\) and device drivers \((\d+)\)")


def _facade_counts(doc: str):
    m = _FACADE_RE.search(doc or "")
    assert m, "capabilities() の説明文が 3 つの数を名乗っていない(言い回しが変わった?)"
    return tuple(int(x) for x in m.groups())


def _assert_the_facade_doc_counts_match(doc: str, live) -> None:
    said = _facade_counts(doc)
    assert said == live, (
        "facade の説明文の数が実装と食い違う: 説明文 %s / 実装 %s "
        "(comm, acquire, device の順)" % (said, live))


def _live_counts():
    import acquire
    return (len(comm.capabilities()), len(acquire.capabilities()),
            len(device.capabilities()))


def test_the_facade_doc_counts_match_the_implementation():
    import fullseye
    _assert_the_facade_doc_counts_match(fullseye.capabilities.__doc__, _live_counts())


def test_the_facade_count_gate_catches_a_stale_number():
    """★門を壊して確かめる —— 1 つずらした説明文は落ちること。

    実際に踏んだのは image sources が 9 のまま残っていた形なので、そこをずらす。
    """
    import fullseye
    live = _live_counts()
    doc = fullseye.capabilities.__doc__.replace(
        "image sources (%d)" % live[1], "image sources (%d)" % (live[1] - 1), 1)
    with pytest.raises(AssertionError) as e:
        _assert_the_facade_doc_counts_match(doc, live)
    assert "食い違う" in str(e.value)


def test_the_facade_count_gate_notices_a_reworded_sentence():
    """★言い回しごと変わったら黙って通さない(数が消えたのを「一致」と読まない)。"""
    with pytest.raises(AssertionError) as e:
        _facade_counts("まったく別の説明文")
    assert "名乗っていない" in str(e.value)



# --------------------------------------------------------------------------- #
# 名簿の `implemented` は、実際の口と一致していること                            #
# --------------------------------------------------------------------------- #
#: ★**名簿が「在る」と言うのと、開けるのは別の問い**だった。2026-09-25 まで
#: `capabilities()` の `available` 1 欄が両方を兼ねており、`dynamixel_sdk` を入れた
#: 機械では `available: True` なのに `open_driver("dynamixel")` は「その SDK を直接
#: 使え」と断った —— 読んだ人は「対応済み」と受け取る。`acquire` は既に
#: `implemented` / `available` を分けて持っていたので、**先に正しかった層の語**に
#: 合わせた。ここではその欄が**実際の口の振る舞いと一致する**ことを見る。
def _assert_the_menu_tells_the_truth_about_opening(rows, opener, refusal_marks) -> None:
    wrong = []
    for row in rows:
        name = row["name"]
        if row["implemented"]:
            continue                      # 開ける側は他の門(扉の門)が見ている
        try:
            got = opener(name)
        except Exception as e:            # noqa: BLE001
            if not any(m in str(e) for m in refusal_marks):
                wrong.append((name, "断り方が想定外: %s" % str(e)[:80]))
            continue
        try:
            got.close()
        except Exception:
            pass
        wrong.append((name, "implemented=False なのに開けた"))
    assert not wrong, (
        "名簿の implemented が実際の口と食い違う: %s" % (wrong,))


def test_the_comm_menu_tells_the_truth_about_opening():
    _assert_the_menu_tells_the_truth_about_opening(
        comm.capabilities(), comm.open_channel,
        ("cataloged", "needs", "no pure-python client"))


def test_the_device_menu_tells_the_truth_about_opening():
    _assert_the_menu_tells_the_truth_about_opening(
        device.capabilities(), device.open_driver,
        ("cataloged", "needs", "no PyPI package"))


def test_every_layer_reports_both_questions():
    """3 層とも「SDK が在るか」と「Fullseye が開けるか」を**別の欄**で答えること。"""
    import acquire as _acq
    for mod in (comm, _acq, device):
        row = mod.capabilities()[0]
        for key in ("available", "implemented"):
            assert key in row, "%s.capabilities() に %r が無い" % (mod.__name__, key)


def test_the_truth_gate_catches_a_menu_that_overstates():
    """★門を壊して確かめる —— 開けないのに「開ける」と名乗る行を落とすこと。"""
    rows = [dict(r) for r in device.capabilities()]
    for r in rows:
        r["implemented"] = False          # 全部「開けない」と名乗らせる
    with pytest.raises(AssertionError) as e:
        _assert_the_menu_tells_the_truth_about_opening(
            rows, device.open_driver, ("cataloged", "needs", "no PyPI package"))
    assert "開けた" in str(e.value)
