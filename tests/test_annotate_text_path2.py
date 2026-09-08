# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""経路に沿う文字の「置き場所」を決める 4 つのつまみの門(ユーザー要望 2026-09-08)。

    「文字列のアンカーも設定できるといいな」
    「画像上で文字列を描く位置は結構気にする」
    「そんな長文は描かないけど、改行機能はあると助かる」
    「文字を斜めに書いたり、縦書きにしたりはできるのかな?」

斜めは前からできていた(接線角に 1 字ずつ回す)。足したのは
``anchor`` / ``offset`` / ``\\n`` / ``upright``(縦書き)の 4 つ。

★ここで一番効く門は **行送りの向きが 1 つの規則で説明できること**。
「進行方向の右」だけを決めておくと、横書きは下へ、縦書きは左へ送られて、
どちらも組版どおりになる。2 つの規則を書き分けると、片方だけ直した日に
縦書きが右へ流れる。
"""
import numpy as np
import pytest

import annotate as A

FS = 14
HORZ = [(20.0, 60.0), (320.0, 60.0)]          # 左 -> 右
VERT = [(60.0, 20.0), (60.0, 320.0)]          # 上 -> 下


def _xy(lay, i):
    return np.asarray(lay["chars"][i]["xy"], dtype=np.float64)


def _line(lay, li):
    return [c for c in lay["chars"] if c["line"] == li]


# --------------------------------------------------------------------------- #
# アンカー
# --------------------------------------------------------------------------- #
def test_anchor_places_the_span_where_it_says():
    """start / center / end が、占める弧長 ``span`` の閉形式どおりに置かれる。"""
    got = {}
    for anc in A.TEXT_PATH_ANCHORS:
        lay = A.annotate_text_path_layout("fullseye", HORZ, font_size=FS, anchor=anc)
        first, last = lay["chars"][0], lay["chars"][-1]
        begin = first["s"] - first["advance"] / 2.0
        end = last["s"] + last["advance"] / 2.0
        got[anc] = (begin, end, lay["span"], lay["length"])
    span, total = got["start"][2], got["start"][3]
    assert got["start"][0] == pytest.approx(0.0, abs=1e-9)
    assert got["center"][0] == pytest.approx((total - span) / 2.0, abs=1e-9)
    assert got["end"][1] == pytest.approx(total, abs=1e-9)
    # 3 つとも同じ長さを占める(位置だけが違う)
    assert {round(v[1] - v[0], 9) for v in got.values()} == {round(span, 9)}


def test_start_still_shifts_on_top_of_the_anchor():
    a = A.annotate_text_path_layout("abc", HORZ, font_size=FS, anchor="center")
    b = A.annotate_text_path_layout("abc", HORZ, font_size=FS, anchor="center", start=12.0)
    assert _xy(b, 0)[0] - _xy(a, 0)[0] == pytest.approx(12.0, abs=1e-9)


def test_an_anchor_that_would_run_off_the_path_is_refused():
    with pytest.raises(ValueError, match="outside"):
        A.annotate_text_path_layout("fullseye", HORZ, font_size=FS, anchor="end", start=40.0)
    with pytest.raises(ValueError, match="anchor must be"):
        A.annotate_text_path_layout("abc", HORZ, font_size=FS, anchor="middle")


# --------------------------------------------------------------------------- #
# 法線オフセット
# --------------------------------------------------------------------------- #
def test_offset_moves_to_the_right_of_travel_not_up_or_down():
    """★「進行方向の右」の 1 規則。左→右の経路なら画面の下(y+)。"""
    base = A.annotate_text_path_layout("abc", HORZ, font_size=FS)
    down = A.annotate_text_path_layout("abc", HORZ, font_size=FS, offset=9.0)
    assert np.allclose(_xy(down, 0) - _xy(base, 0), (0.0, 9.0), atol=1e-9)
    # 上→下の経路では、その右は画面の左(x-)
    vb = A.annotate_text_path_layout("abc", VERT, font_size=FS)
    vd = A.annotate_text_path_layout("abc", VERT, font_size=FS, offset=9.0)
    assert np.allclose(_xy(vd, 0) - _xy(vb, 0), (-9.0, 0.0), atol=1e-9)


# --------------------------------------------------------------------------- #
# 改行
# --------------------------------------------------------------------------- #
def test_newlines_make_rows_that_step_by_the_line_height():
    lay = A.annotate_text_path_layout("aa\nbbbb\nc", HORZ, font_size=FS)
    assert lay["lines"] == 3
    assert [len(_line(lay, i)) for i in range(3)] == [2, 4, 1]
    y = [_line(lay, i)[0]["xy"][1] for i in range(3)]
    assert y[1] - y[0] == pytest.approx(lay["line_height"], abs=1e-9)
    assert y[2] - y[1] == pytest.approx(lay["line_height"], abs=1e-9)
    # span は**最も長い行**(2 行目)の幅
    widths = [sum(c["advance"] for c in _line(lay, i)) for i in range(3)]
    assert lay["span"] == pytest.approx(max(widths), abs=1e-9)


def test_each_line_is_anchored_on_its_own():
    """★中央そろえの複数行は、行ごとに中央に来ること(長い行に釣られない)。"""
    lay = A.annotate_text_path_layout("aa\nbbbbbbbb", HORZ, font_size=FS, anchor="center")
    total = lay["length"]
    for i in range(2):
        row = _line(lay, i)
        begin = row[0]["s"] - row[0]["advance"] / 2.0
        end = row[-1]["s"] + row[-1]["advance"] / 2.0
        assert (begin + end) / 2.0 == pytest.approx(total / 2.0, abs=1e-9)


def test_an_empty_row_still_costs_one_line():
    lay = A.annotate_text_path_layout("a\n\nb", HORZ, font_size=FS)
    assert lay["lines"] == 3 and len(lay["chars"]) == 2
    assert _line(lay, 2)[0]["xy"][1] - _line(lay, 0)[0]["xy"][1] == \
        pytest.approx(2.0 * lay["line_height"], abs=1e-9)
    with pytest.raises(ValueError, match="empty"):
        A.annotate_text_path_layout("\n\n", HORZ, font_size=FS)


# --------------------------------------------------------------------------- #
# 縦書き
# --------------------------------------------------------------------------- #
def test_upright_on_a_downward_path_is_vertical_writing():
    lay = A.annotate_text_path_layout("縦書き", VERT, font_size=FS, upright=True)
    assert lay["vertical"] is True
    xs = [c["xy"][0] for c in lay["chars"]]
    ys = [c["xy"][1] for c in lay["chars"]]
    assert len(set(np.round(xs, 9))) == 1                      # 縦一列
    assert ys == sorted(ys)                                    # 上から下へ
    assert all(c["angle_deg"] == 0.0 for c in lay["chars"])    # 字は正立
    # 送りは字幅ではなく**字高**(等幅に並ぶ)
    assert len({round(c["advance"], 9) for c in lay["chars"]}) == 1
    assert np.allclose(np.diff(ys), lay["chars"][0]["advance"], atol=1e-9)


def test_the_second_line_of_vertical_writing_goes_left():
    """★縦書きの 2 行目は**左**へ(進行方向の右 = 画面の左)。"""
    lay = A.annotate_text_path_layout("あい\nうえ", VERT, font_size=FS, upright=True)
    x0 = _line(lay, 0)[0]["xy"][0]
    x1 = _line(lay, 1)[0]["xy"][0]
    assert x1 - x0 == pytest.approx(-lay["line_height"], abs=1e-9)


def test_only_the_characters_that_should_rotate_do():
    lay = A.annotate_text_path_layout("あーい(", VERT, font_size=FS, upright=True)
    ang = {c["char"]: c["angle_deg"] for c in lay["chars"]}
    assert ang["あ"] == 0.0 and ang["い"] == 0.0
    assert ang["ー"] == 90.0 and ang["("] == 90.0
    assert "ー" in A.VERTICAL_ROTATED_CHARS and "あ" not in A.VERTICAL_ROTATED_CHARS


def test_upright_on_a_horizontal_path_is_not_vertical_writing():
    """★``upright`` は「回さない」だけ。横の経路なら送りは字幅のまま。"""
    lay = A.annotate_text_path_layout("abc", HORZ, font_size=FS, upright=True)
    assert lay["vertical"] is False
    assert all(c["angle_deg"] == 0.0 for c in lay["chars"])
    assert len({round(c["advance"], 9) for c in lay["chars"]}) > 1   # 字幅で送る


def test_a_slanted_path_still_rotates_each_glyph():
    """斜めは前からできていた —— 壊していないことを見張る。"""
    lay = A.annotate_text_path_layout("abc", [(0.0, 0.0), (100.0, 100.0)], font_size=FS)
    assert all(c["angle_deg"] == pytest.approx(45.0, abs=1e-9) for c in lay["chars"])


# --------------------------------------------------------------------------- #
# 壊していないこと
# --------------------------------------------------------------------------- #
def test_used_keeps_its_old_meaning_even_though_span_was_added():
    """★``used`` は**送りの合計**のまま(既に使っている人の式を変えない)。

    新しく足したのは ``span`` —— 最後の字の後ろの送りを含まない、実際に
    占める幅。アンカーはこちらで揃える(``used`` で揃えると右へずれる)。
    """
    for sp in (1.0, 1.5):
        lay = A.annotate_text_path_layout("fullseye", HORZ, font_size=FS, spacing=sp)
        w = np.array([A.measure_text(c["char"], font_size=FS, min_font_size=1)["width"]
                      for c in lay["chars"]])
        assert lay["used"] == pytest.approx(float((w * sp).sum()), abs=1e-6)
        assert lay["span"] == pytest.approx(float(w[:-1].sum() * sp + w[-1]), abs=1e-6)
    assert A.annotate_text_path_layout("abc", HORZ, font_size=FS)["span"] <= \
        A.annotate_text_path_layout("abc", HORZ, font_size=FS)["used"] + 1e-9


def test_drawing_accepts_the_same_knobs_and_stays_inside_the_image():
    img = np.zeros((120, 360, 3))
    out = A.annotate_text_path(img, "one\ntwo", HORZ, font_size=FS, anchor="center",
                               offset=-10.0, color="emphasis")
    assert out.shape == img.shape and float(np.abs(out - img).max()) > 0.1
    vert = A.annotate_text_path(np.zeros((360, 120, 3)), "縦書き",
                                [(60.0, 20.0), (60.0, 320.0)], font_size=FS, upright=True)
    assert float(np.abs(vert).max()) > 0.1
