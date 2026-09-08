# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""タブ区切り → 表として描く op の門(ユーザー要望 2026-09-08)。

    「タブ区切りの文字列なら、表形式で描画もあるといいね。」
    「複数行なら、表のカラムの間隔はデフォルトでは自動調整してもらえると助かる。」
    「もちろんフォントサイズを考慮して。」
    「表は半透明で描くこともできるといいね。」

★この op で一番壊れやすいのは「**桁幅を文字数で数える**」。和文 1 字は
英数字 2 字ぶんの幅があるので、数えた瞬間に和英混在の表が崩れる。だから
ここでは「実フォントで測った幅と一致すること」を門にしている。

★2 番目は「**layout が言う場所と、実際にインクが乗る場所がずれる**」。
配置を table で返す設計は、返した数字を誰も突き合わせないと意味がない。
"""
import numpy as np
import pytest

import annotate as A

FS = 14
TSV = "項目\t値\n面積\t12.50\n周長\t9.75"


def _w(s, **kw):
    return A.measure_text(s, font_size=FS, **kw)["width"]


# --------------------------------------------------------------------------- #
# 1. 桁幅は「測る」—— 数えない
# --------------------------------------------------------------------------- #
def test_column_width_is_the_measured_maximum_not_a_character_count():
    lay = A.annotate_table_layout("ab\tx\n面積\ty", (0, 0), font_size=FS)
    assert lay["col_w"][0] == max(_w("ab"), _w("面積"))
    assert lay["col_w"][1] == max(_w("x"), _w("y"))
    # 和文 2 字と英数 2 字は**同じ字数でも幅が違う**(数えていたら等しくなる)
    assert _w("面積") > _w("ab")


def test_a_bold_header_makes_its_own_column_wider():
    """見出しを太らせたぶんも桁幅に入る(入らないと見出しがはみ出す)。"""
    plain = A.annotate_table_layout("value\tx\na\tb", (0, 0), font_size=FS)
    hdr = A.annotate_table_layout("value\tx\na\tb", (0, 0), font_size=FS, header=True)
    assert hdr["col_w"][0] > plain["col_w"][0]
    assert hdr["col_w"][0] == max(_w("value", bold=True), _w("a"))


def test_the_default_column_gap_scales_with_the_font_size():
    """★「もちろんフォントサイズを考慮して」—— 桁間も行高に比例する。"""
    gaps = {}
    for fs in (10, 14, 20, 28):
        lay = A.annotate_table_layout(TSV, (0, 0), font_size=fs)
        gaps[fs] = lay["col_gap"]
        want = int(round(lay["row_h"] * A._COL_GAP_RATIO))
        assert lay["col_gap"] == want, (fs, lay["col_gap"], want)
    assert gaps[28] > gaps[20] > gaps[14] > gaps[10]
    assert 1.6 < gaps[28] / gaps[14] < 2.4                 # おおむね比例
    # 明示すればそのまま
    assert A.annotate_table_layout(TSV, (0, 0), font_size=FS, col_gap=3)["col_gap"] == 3


# --------------------------------------------------------------------------- #
# 2. そろえ方
# --------------------------------------------------------------------------- #
def test_auto_alignment_right_aligns_only_the_columns_that_are_numbers():
    lay = A.annotate_table_layout("名前\t値\t備考\nA\t1.5\tok\nB\t-22.25\tn/a",
                                  (0, 0), font_size=FS, header=True)
    assert lay["align"] == ["left", "right", "left"]
    # 見出しを外さないと「値」が数でないので左に落ちる —— header=False はそうなる
    assert A.annotate_table_layout("名前\t値\nA\t1.5", (0, 0), font_size=FS)["align"] \
        == ["left", "left"]


@pytest.mark.parametrize("cell,numeric", [
    ("1.5", True), ("-3", True), ("+0.25", True), ("1,234", True), ("±0.5", True),
    ("12 %", True), ("1e-3", True),
    ("N/A", False), ("12 mm", False), ("", False), ("OK", False), ("—", False),
])
def test_what_counts_as_a_number(cell, numeric):
    assert A._looks_numeric(cell) is numeric


def test_right_aligned_cells_all_end_on_the_same_edge():
    lay = A.annotate_table_layout("v\n1.5\n22.25\n333.125", (0, 0), font_size=FS,
                                  header=True)
    assert lay["align"] == ["right"]
    ends = {c["xy"][0] + c["width"] for c in lay["cells"] if c["row"] > 0}
    assert len(ends) == 1
    assert ends.pop() == lay["col_x"][0] + lay["col_w"][0]


def test_explicit_alignment_per_column_and_its_errors():
    lay = A.annotate_table_layout("aaa\tbbb\tccc\nx\ty\tz", (0, 0), font_size=FS,
                                  align=("left", "center", "right"))
    row1 = sorted([c for c in lay["cells"] if c["row"] == 1], key=lambda c: c["col"])
    assert row1[0]["xy"][0] == lay["col_x"][0]
    assert row1[2]["xy"][0] + row1[2]["width"] == lay["col_x"][2] + lay["col_w"][2]
    mid = lay["col_x"][1] + (lay["col_w"][1] - row1[1]["width"]) // 2
    assert row1[1]["xy"][0] == mid
    with pytest.raises(ValueError, match="align has 3 entries"):
        A.annotate_table_layout("a\tb\nx\ty", (0, 0), align=("left", "right", "left"))
    with pytest.raises(ValueError, match="align must be"):
        A.annotate_table_layout("a\tb\nx\ty", (0, 0), align="justify")


# --------------------------------------------------------------------------- #
# 3. 歯抜けは黙って埋めない
# --------------------------------------------------------------------------- #
def test_a_ragged_row_is_refused_and_the_message_says_which_one():
    """★埋めると表は出るが**数字が隣の見出しの下に並ぶ**。最悪の壊れ方。"""
    with pytest.raises(ValueError, match="row 1 has 3 columns"):
        A.annotate_table_layout("a\tb\nx\ty\tz\nq", (0, 0))
    with pytest.raises(ValueError, match="row 1 has 3 column"):
        A.annotate_table_layout("a\tb\nx\ty\tz", (0, 0))
    with pytest.raises(ValueError, match="empty"):
        A.annotate_table_layout("", (0, 0))
    # 末尾の改行は落とす(書き出した文字列をそのまま渡せるように)
    assert A.annotate_table_layout("a\tb\nx\ty\n", (0, 0))["nrows"] == 2


# --------------------------------------------------------------------------- #
# 4. layout の言うとおりの場所にインクが乗るか
# --------------------------------------------------------------------------- #
def test_the_ink_lands_inside_the_cells_the_layout_promised():
    img = np.zeros((160, 420))
    lay = A.annotate_table_layout(TSV, (20, 20), font_size=FS, header=True)
    out = A.annotate_table(img, TSV, (20, 20), font_size=FS, header=True, box_alpha=0.0)
    x0, y0, w, h = lay["rect"]
    ink = out > 0.05
    rows, cols = np.nonzero(ink)
    assert rows.min() >= y0 and rows.max() < y0 + h
    assert cols.min() >= x0 and cols.max() < x0 + w
    # 板の外は 1 画素も触らない
    outside = ink.copy()
    outside[y0:y0 + h, x0:x0 + w] = False
    assert not outside.any()


def test_the_anchor_moves_the_whole_table():
    lay_lt = A.annotate_table_layout(TSV, (30, 40), font_size=FS)
    lay_rb = A.annotate_table_layout(TSV, (30, 40), font_size=FS, anchor="rb")
    w, h = lay_lt["rect"][2], lay_lt["rect"][3]
    assert lay_lt["rect"][:2] == (30, 40)
    assert lay_rb["rect"][:2] == (30 - w, 40 - h)
    assert lay_rb["rect"][2:] == (w, h)


def test_a_table_that_does_not_fit_raises_instead_of_clipping():
    img = np.zeros((40, 60))
    with pytest.raises(ValueError, match="does not fit"):
        A.annotate_table(img, TSV, (5, 5), font_size=FS)


# --------------------------------------------------------------------------- #
# 5. 半透明の板
# --------------------------------------------------------------------------- #
def test_the_plate_is_translucent_by_default_and_lets_the_picture_through():
    """★「表は半透明で描くこともできるといいね」—— 混ぜ方は ``_blend`` の正典。"""
    img = np.full((160, 420), 0.5)
    lay = A.annotate_table_layout(TSV, (20, 20), font_size=FS)
    x0, y0, w, h = lay["rect"]
    out = A.annotate_table(img, TSV, (20, 20), font_size=FS)
    plate = float(np.mean(A._PLATE_RGB))
    corner = out[y0 + 1, x0 + 1]                       # 字の無い板の隅
    assert corner == pytest.approx(0.5 * (1 - 0.72) + plate * 0.72, abs=1e-9)
    assert out[y0 - 1, x0 - 1] == 0.5                  # 板の外は素通し

    solid = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=1.0)
    assert solid[y0 + 1, x0 + 1] == pytest.approx(plate, abs=1e-9)
    none = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0,
                            text_color=(0.0, 0.0, 0.0))
    assert none[y0 + 1, x0 + 1] == 0.5                 # 板なしなら地のまま
    with pytest.raises(ValueError, match="box_alpha"):
        A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=1.5)


def test_unreadable_text_on_a_transparent_plate_is_refused():
    """板を消して明るい地に置くと、既定の明るい文字は溶ける —— そこで落ちる。"""
    img = np.full((160, 420), 0.98)
    with pytest.raises(ValueError, match="contrast"):
        A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0,
                         text_color=(1.0, 1.0, 1.0))


# --------------------------------------------------------------------------- #
# 6. 見出しと罫
# --------------------------------------------------------------------------- #
def test_the_header_row_is_bold_and_gets_a_rule_under_it():
    lay = A.annotate_table_layout(TSV, (20, 20), font_size=FS, header=True)
    assert all(c["bold"] for c in lay["cells"] if c["row"] == 0)
    assert not any(c["bold"] for c in lay["cells"] if c["row"] > 0)
    assert lay["row_y"][0] < lay["rule_y"] < lay["row_y"][1]
    assert A.annotate_table_layout(TSV, (20, 20), font_size=FS)["rule_y"] is None

    img = np.zeros((160, 420))
    plain = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0)
    hdr = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0, header=True)
    assert hdr.sum() > plain.sum()                     # 太字 + 罫のぶん増える
    ry = lay["rule_y"]
    assert hdr[ry].sum() > plain[ry].sum() + 10.0      # 罫が本当に引かれている


def test_grid_draws_lines_between_the_columns_and_rows():
    img = np.zeros((160, 420))
    lay = A.annotate_table_layout(TSV, (20, 20), font_size=FS)
    off = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0, grid=False)
    on = A.annotate_table(img, TSV, (20, 20), font_size=FS, box_alpha=0.0, grid=True)
    gx = lay["col_x"][1] - int(round(lay["col_gap"] / 2.0))
    assert on[:, gx].sum() > off[:, gx].sum() + 5.0
    assert on.sum() > off.sum()


# --------------------------------------------------------------------------- #
# 7. 台帳から呼べるか(公開層の 4 段)
# --------------------------------------------------------------------------- #
def test_the_new_ops_are_reachable_from_every_public_tier():
    import fullseye as fs
    import opsannotate
    for name in ("annotate_table", "annotate_table_layout", "annotate_invert",
                 "annotate_invert_path", "annotate_invert_visibility"):
        assert hasattr(fs, name), name
        assert name in opsannotate.OPSANNOTATE, name
        assert opsannotate.get(name) is not None, name
