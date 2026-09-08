# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""反転色で描く 3 op の門(ユーザー要望 2026-09-08)。

反転色は「地が明るいか暗いか判らなくても見える色で描く」ための古典手だが、
弱点はたった 1 つで、しかも致命的 —— **中間調では反転しても同じ色になる**。
8bit グレーの v=128 に対する補色は v=127 で、WCAG のコントラスト比は 1.014。

ここで測るのは 3 つ:

1. **崖が本当にそこに在るか**(補色が消える階調の帯を、docstring に書いた
   数字と画素で突き合わせる)。数字が独り歩きしないように、この試験は
   WCAG の式を**別に書き下して**照合する —— op 自身の実装で op を測ると
   何も測っていないのと同じ([[feedback_beat_the_null_before_claiming]])。
2. **逃げ道が本当に逃げ道か**(``mode="contrast"`` が全 256 階調で
   コントラスト比 4.58 以上を出すこと)。
3. **見えないまま黙って通さないか**(warn / raise / ignore)。
"""
import warnings

import numpy as np
import pytest

import annotate as A


# --------------------------------------------------------------------------- #
# op の実装とは別に書き下した WCAG(これが「零点」)
# --------------------------------------------------------------------------- #
def _lum(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def _cr(a, b):
    la, lb = _lum(a), _lum(b)
    return (np.maximum(la, lb) + 0.05) / (np.minimum(la, lb) + 0.05)


ALL_LEVELS = np.arange(256) / 255.0


# --------------------------------------------------------------------------- #
# 1. 崖 —— 補色が消える帯
# --------------------------------------------------------------------------- #
def test_the_complement_vanishes_on_mid_grey_exactly_where_the_docstring_says():
    """★docstring の「v ∈ [113, 142] の 30 階調」を画素で確かめる。

    ここが動いたら docstring も動かすこと。数字だけが古くなるのが
    [[feedback_gates_go_stale_not_missing]] の型。
    """
    cr = _cr(ALL_LEVELS, 1.0 - ALL_LEVELS)
    bad = np.where(cr < A.INVERT_MIN_CONTRAST)[0]
    assert (bad.min(), bad.max(), bad.size) == (113, 142, 30)
    assert round(float(cr[128]), 3) == 1.014


def test_visibility_agrees_with_the_wcag_formula_written_out_separately():
    img = np.tile(ALL_LEVELS, (4, 1))                       # (4, 256) 全階調
    rep = A.annotate_invert_visibility(img, np.ones(img.shape, bool))
    want = _cr(img, 1.0 - img)
    assert rep["pixels"] == img.size
    assert np.isclose(rep["min_contrast"], want.min(), rtol=0, atol=1e-12)
    assert np.isclose(rep["median_contrast"], np.median(want), rtol=0, atol=1e-12)
    assert np.isclose(rep["invisible_fraction"], np.mean(want < A.INVERT_MIN_CONTRAST))


def test_contrast_mode_is_a_real_escape_hatch_on_every_grey_level():
    """★逃げ道の保証: どの階調の地でもコントラスト比 4.58 以上。

    連続では ``1.05/(√0.0525) = 4.583``。8bit の格子で最悪なのは v=117。
    """
    img = np.tile(ALL_LEVELS, (4, 1))
    rep = A.annotate_invert_visibility(img, np.ones(img.shape, bool), mode="contrast")
    assert rep["min_contrast"] >= 4.58
    assert rep["invisible_fraction"] == 0.0
    inv = A._inverted(img, "contrast")
    assert set(np.unique(inv)) <= {0.0, 1.0}                # 白か黒しか出ない


# --------------------------------------------------------------------------- #
# 2. 描く —— 領域と線
# --------------------------------------------------------------------------- #
def test_inverting_twice_puts_the_image_back():
    """完全被覆なら反転は自分自身の逆。**線の内側でも成り立つこと**。"""
    rng = np.random.default_rng(0)
    img = rng.random((24, 32))
    m = np.zeros((24, 32), bool)
    m[6:18, 8:24] = True
    once = A.annotate_invert(img, m)
    twice = A.annotate_invert(once, m)
    assert np.allclose(twice, img, atol=1e-12)
    assert not np.allclose(once, img)                        # 何もしていない、ではない


def test_margin_inverts_the_rim_and_leaves_the_inside_alone():
    img = np.zeros((24, 24))
    img[6:18, 6:18] = 1.0
    m = np.zeros((24, 24), bool)
    m[9:15, 9:15] = True
    out = A.annotate_invert(img, m, draw="margin", width=1)
    assert out[12, 12] == 1.0                                 # 中心は素通し
    assert out[9, 9] == 0.0                                   # 縁は反転
    assert out[0, 0] == 0.0                                   # 領域の外は元のまま
    filled = A.annotate_invert(img, m, draw="fill")
    assert filled[12, 12] == 0.0                              # fill との違いが出ている


def test_a_thin_line_is_judged_only_on_the_pixels_it_really_claims():
    """★細い線の端は元から半透明。そこを『見えない』に数えると常に警告になる。"""
    img = np.zeros((16, 40))
    out = A.annotate_invert_path(img, [(2.0, 8.0), (37.0, 8.0)], width=3.0)
    assert out[8, 20] == 1.0                                  # 芯は完全反転
    assert out[2, 20] == 0.0                                  # 離れたところは無傷
    rep = A.annotate_invert_visibility(img, np.ones(img.shape, bool))
    assert rep["pixels"] == img.size                          # 参考: 全面なら全画素
    # 線が claim するのは被覆 0.5 以上の帯だけ(高さ 4 画素 = r+0.5 の切り上げ)
    band = int(np.count_nonzero(np.abs(np.arange(16) - 8.0) <= 1.5))
    assert band == 4


def test_alpha_channel_is_never_inverted():
    """★見えるようにしたつもりが**透明になる**、を起こさない。"""
    img = np.zeros((8, 8, 4))
    img[..., 3] = 1.0
    m = np.ones((8, 8), bool)
    out = A.annotate_invert(img, m)
    assert np.all(out[..., :3] == 1.0)
    assert np.all(out[..., 3] == 1.0)                         # α は 0 に落ちない


# --------------------------------------------------------------------------- #
# 3. 黙って通さない
# --------------------------------------------------------------------------- #
def test_it_warns_when_the_inverted_colour_is_invisible():
    flat = np.full((16, 16), 128 / 255.0)
    m = np.ones((16, 16), bool)
    with pytest.warns(RuntimeWarning, match="invisible"):
        out = A.annotate_invert(flat, m)
    assert float(np.max(np.abs(out - flat))) < 1.0 / 255.0    # 実際、ほぼ何も起きていない


def test_raise_makes_it_fail_closed_and_ignore_stays_quiet():
    flat = np.full((16, 16), 128 / 255.0)
    m = np.ones((16, 16), bool)
    with pytest.raises(ValueError, match="invisible"):
        A.annotate_invert(flat, m, on_invisible="raise")
    with warnings.catch_warnings():
        warnings.simplefilter("error")                          # 警告が出たら失敗
        A.annotate_invert(flat, m, on_invisible="ignore")
    with pytest.raises(ValueError, match="on_invisible"):
        A.annotate_invert(flat, m, on_invisible="quietly")


def test_contrast_mode_does_not_warn_on_the_background_that_kills_complement():
    flat = np.full((16, 16), 128 / 255.0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = A.annotate_invert(flat, np.ones((16, 16), bool), mode="contrast")
    assert set(np.unique(out)) <= {0.0, 1.0}


def test_half_alpha_complement_is_reported_as_invisible_because_it_is():
    """★alpha=0.5 の補色は**必ず**中間調になる —— 道理どおり警告が出ること。"""
    img = np.zeros((16, 16))
    with pytest.warns(RuntimeWarning, match="invisible"):
        out = A.annotate_invert(img, np.ones((16, 16), bool), alpha=0.5)
    assert np.allclose(out, 0.5)


# --------------------------------------------------------------------------- #
# 4. 兄弟コードと同じ規則か(マスクの受け口を 1 か所に寄せた分の門)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad,match", [
    (np.ones((4, 4), bool), "does not match"),
    (np.full((8, 8), np.nan), "non-finite"),
    (np.full((8, 8), 1.5), "within"),
])
def test_overlay_mask_and_invert_reject_the_same_masks(bad, match):
    """★同じ入力を片方だけが通す、が起きないこと(規則は ``_mask_weights`` 1 か所)。"""
    img = np.zeros((8, 8))
    with pytest.raises(ValueError, match=match):
        A.overlay_mask(img, bad)
    with pytest.raises(ValueError, match=match):
        A.annotate_invert(img, bad)


def test_unknown_mode_and_draw_are_refused():
    img = np.zeros((8, 8))
    m = np.ones((8, 8), bool)
    with pytest.raises(ValueError, match="mode"):
        A.annotate_invert(img, m, mode="xor")
    with pytest.raises(ValueError, match="draw"):
        A.annotate_invert(img, m, draw="outline")
