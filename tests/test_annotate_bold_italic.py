# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""合成 Bold / Italic の門(ユーザー要望 2026-09-08)。

    「そもそも文字列を Bold や Italic 等で描画とかもできるのか、
      色付きで描けるのかとかも気になる。」

色は前からできた。字体は入口が ``font_path`` だけだったので、**合成**の
太字(輪郭を太らせる)と斜体(せん断)を足した。

★ここで一番効く門は 2 つ:

1. **既定の経路が 1 画素も変わっていないこと**。字体を足したときに
   「太くも斜めにもしていない図」がずれるのが一番困る。
2. **太さと傾きのぶんが ``measure_text`` の幅・高さに入っていること**。
   入っていないと、板や表の桁は元のままで**字だけがはみ出す** ——
   しかも `text_box` は「はみ出しは例外」の規律なので、静かに歪むのではなく
   関係ない場所で落ちる。
"""
import numpy as np
import pytest

import annotate as A

FS = 20
TXT = "Fullseye Ag"


def _ink(text, **kw):
    """黒地に白で焼いて、インクの重みだけ取り出す。"""
    img = np.zeros((80, 400))
    out = A.text_box(img, text, (20, 20), anchor="lt", font_size=FS, box_alpha=0.0,
                     text_color=(1.0, 1.0, 1.0), color="neutral", **kw)
    return out


# --------------------------------------------------------------------------- #
# 1. 既定は 1 画素も変わらない
# --------------------------------------------------------------------------- #
def test_the_plain_path_is_untouched():
    """★``bold=False, italic=False`` は**専用の経路**を通り、結果が同一。"""
    base = _ink(TXT)
    assert np.array_equal(base, _ink(TXT, bold=False, italic=False))
    assert np.array_equal(base, _ink(TXT, bold=0))
    m0 = A.measure_text(TXT, font_size=FS)
    m1 = A.measure_text(TXT, font_size=FS, bold=False, italic=False)
    assert (m0["width"], m0["height"]) == (m1["width"], m1["height"])


# --------------------------------------------------------------------------- #
# 2. 太字
# --------------------------------------------------------------------------- #
def test_bold_puts_down_more_ink_and_says_so_in_the_measurement():
    plain, bold = _ink(TXT), _ink(TXT, bold=True)
    assert bold.sum() > plain.sum() * 1.15
    m0 = A.measure_text(TXT, font_size=FS)
    mb = A.measure_text(TXT, font_size=FS, bold=True)
    stroke = A._bold_px(m0["font"], True)
    assert stroke >= 1
    assert mb["width"] - m0["width"] == 2 * stroke
    assert mb["height"] - m0["height"] == 2 * stroke


def test_the_stroke_width_follows_the_font_size():
    """小さい字で 1 px、大きい字で太く —— 比で決まるので figure ごとに整う。"""
    got = {s: A._bold_px(A._font(s), True) for s in (10, 14, 27, 40)}
    assert got[10] == 1 and got[14] == 1
    assert got[27] == 2 and got[40] == 3
    assert all(a <= b for a, b in zip(got.values(), list(got.values())[1:]))


def test_an_explicit_pixel_width_is_taken_literally():
    font = A._font(FS)
    assert A._bold_px(font, 3) == 3
    assert A._bold_px(font, 0) == 0 and A._bold_px(font, False) == 0
    with pytest.raises(ValueError, match="bold must be"):
        A._bold_px(font, -1)
    assert _ink(TXT, bold=3).sum() > _ink(TXT, bold=1).sum()


# --------------------------------------------------------------------------- #
# 3. 斜体
# --------------------------------------------------------------------------- #
def test_italic_leans_right_which_means_the_top_is_further_right():
    """★向きを取り違えると「左に倒れた字」になる。重心で向きを測る。"""
    plain, ital = _ink(TXT), _ink(TXT, italic=True)

    def halves(img):
        rows = np.nonzero(img.sum(axis=1) > 1e-9)[0]
        mid = (rows.min() + rows.max()) // 2
        top, bot = img[rows.min():mid + 1], img[mid + 1:rows.max() + 1]
        cx = lambda p: float((p.sum(0) * np.arange(p.shape[1])).sum() / p.sum())  # noqa: E731
        return cx(top), cx(bot)

    pt, pb = halves(plain)
    it, ib = halves(ital)
    assert abs(pt - pb) < 3.0                       # 立った字は上下の重心がほぼ同じ
    assert it - ib > 2.0                            # 斜体は上が右
    assert (it - ib) > (pt - pb) + 2.0


def test_italic_widens_the_measured_box_by_the_lean():
    m0 = A.measure_text(TXT, font_size=FS)
    mi = A.measure_text(TXT, font_size=FS, italic=True)
    lean = A.ITALIC_SHEAR * A._line_height(m0["font"])
    assert mi["width"] - m0["width"] == pytest.approx(int(np.ceil(m0["width"] + lean))
                                                      - m0["width"], abs=1)
    assert mi["height"] == m0["height"]              # 傾けても高さは増えない
    assert 0.15 < A.ITALIC_SHEAR < 0.30              # 8-16 度のあたり


def test_the_lean_grows_with_the_number_of_lines():
    one = A.measure_text("ab", font_size=FS, italic=True)["width"]
    two = A.measure_text("ab\ncd", font_size=FS, italic=True)["width"]
    assert two > one                                  # 行が増えるほど右へ伸びる


# --------------------------------------------------------------------------- #
# 4. 測った幅で判定しているか(はみ出しは黙って切らない)
# --------------------------------------------------------------------------- #
def test_bold_that_no_longer_fits_is_refused_not_clipped():
    """★太らせたぶんが幅に入っていなければ、ここは黙って通ってしまう。"""
    m = A.measure_text(TXT, font_size=FS)
    just = m["width"] + 1
    A.measure_text(TXT, font_size=FS, max_width=just, min_font_size=FS)
    with pytest.raises(ValueError, match="does not fit"):
        A.measure_text(TXT, font_size=FS, max_width=just, min_font_size=FS, bold=3)
    with pytest.raises(ValueError, match="does not fit"):
        A.measure_text(TXT, font_size=FS, max_width=just, min_font_size=FS, italic=True)


def test_a_bold_label_pressed_against_the_edge_raises_instead_of_clipping():
    img = np.zeros((60, 200))
    x = 200 - A.measure_text("edge", font_size=FS)["width"] - 12
    A.text_box(img, "edge", (x, 10), anchor="lt", font_size=FS, pad=5, box_alpha=0.0)
    with pytest.raises(ValueError, match="overflow"):
        A.text_box(img, "edge", (x, 10), anchor="lt", font_size=FS, pad=5,
                   box_alpha=0.0, bold=6)


# --------------------------------------------------------------------------- #
# 5. 経路に沿う文字にも届いているか
# --------------------------------------------------------------------------- #
def test_the_path_renderer_gets_the_same_two_knobs():
    img = np.zeros((120, 400))
    path = [(20.0, 60.0), (380.0, 60.0)]
    plain = A.annotate_text_path(img, TXT, path, font_size=FS, color="neutral")
    bold = A.annotate_text_path(img, TXT, path, font_size=FS, color="neutral", bold=True)
    ital = A.annotate_text_path(img, TXT, path, font_size=FS, color="neutral", italic=True)
    assert bold.sum() > plain.sum() * 1.15
    assert not np.array_equal(ital, plain)
    assert np.array_equal(plain, A.annotate_text_path(img, TXT, path, font_size=FS,
                                                      color="neutral", bold=False))
