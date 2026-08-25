"""形状マッチング一族の回帰テスト(2026-08-25)。

find_shape_model にピラミッドサーチを入れた後、**同じ一族の他の op も無事か**を
点検して見つかった欠陥を固定する。全て実測で再現を確認してから直した。

1. find_shape_models が画像の右下を走査していなかった(中心規約と左上規約の混在)
2. 同上、画像の端では model の半分が外に出た状態で採点され偽陽性 0.73 が出た
3. find_scaled_shape_models が scale を **件数** で選んでいた(2 の偽陽性で誤選択)
4. find_local_deformable_model が "column" を読んでいた(find_shape_model は "col")
   -> 常に None、かつ変形場を **画像の左端** から取っていた
5. find_aniso_shape_model が未検出時に {"found": False} だけを返し KeyError の元
6. NCC 一族の基準点が左上、形状一族が中心で、テンプレート半分ずれていた
"""
from __future__ import annotations

import numpy as np
import pytest

import matching as M
import shapematch as S


def _cross(im, r, c):
    im[r - 10:r + 10, c - 2:c + 2] += 1.0
    im[r - 2:r + 2, c - 10:c + 10] += 1.0
    return im


@pytest.fixture
def tpl():
    return _cross(np.zeros((40, 40)), 20, 20)


def _scene(pos, seed=0, size=200):
    img = np.random.default_rng(seed).normal(0, 0.05, (size, size))
    for p in pos:
        _cross(img, *p)
    return img


# --- 1 & 2: 端の取り逃しと端の偽陽性 ------------------------------------------ #
@pytest.mark.parametrize("pos", [(170, 170), (100, 170), (170, 100), (60, 50)])
def test_find_shape_models_reaches_the_border(tpl, pos):
    """右下の帯 [H-mh, H-mh//2) を走査していなかったので端の物体を取り逃した。"""
    m = S.create_shape_model(tpl)
    res = S.find_shape_models(m, _scene([pos]), min_score=0.4, max_matches=1)
    assert res["num"] == 1
    got = (res["matches"][0]["row"], res["matches"][0]["column"])
    assert abs(got[0] - pos[0]) <= 2 and abs(got[1] - pos[1]) <= 2, got


def test_find_shape_models_has_no_border_false_positive(tpl):
    """物体が無い画像で min_score 0.5 を超える一致が出てはいけない。

    直す前は model が半分はみ出た端の位置で 0.73 が出ていた。"""
    m = S.create_shape_model(tpl)
    img = np.random.default_rng(7).normal(0, 0.05, (200, 200))
    res = S.find_shape_models(m, img, min_score=0.5, max_matches=5)
    assert res["num"] == 0, res["matches"]


def test_find_shape_models_agrees_with_find_shape_model(tpl):
    m = S.create_shape_model(tpl)
    img = _scene([(60, 150)], seed=3)
    a = S.find_shape_model(m, img)
    b = S.find_shape_models(m, img, min_score=0.4, max_matches=1)["matches"][0]
    assert abs(a["row"] - b["row"]) <= 2 and abs(a["col"] - b["column"]) <= 2


# --- 3: scale はスコアで選ぶ --------------------------------------------------- #
def test_find_scaled_shape_models_picks_scale_by_score(tpl):
    sm = S.create_scaled_shape_model(tpl)
    res = S.find_scaled_shape_models(sm, _scene([(60, 150)], seed=1),
                                     min_score=0.6, max_matches=2)
    assert res["scale"] == pytest.approx(1.0)
    assert res["matches"][0]["score"] > 0.9


# --- 4: 鍵名の取り違え --------------------------------------------------------- #
def test_local_deformable_returns_a_column(tpl):
    m = S.create_local_deformable_model(tpl)
    res = S.find_local_deformable_model(m, _scene([(60, 150)], seed=1))
    assert res["column"] is not None
    assert abs(res["row"] - 60) <= 2 and abs(res["column"] - 150) <= 2


def test_local_deformable_flow_is_small_for_an_undeformed_object(tpl):
    """正しい切り出しなら変形はほぼ 0。左端を切り出していた頃は ±1.2 px 出ていた。"""
    m = S.create_local_deformable_model(tpl)
    res = S.find_local_deformable_model(m, _scene([(60, 150)], seed=1))
    f = res["deformation"]
    assert max(np.abs(f["row"]).max(), np.abs(f["col"]).max()) < 0.5


# --- 5: 未検出時も同じ鍵 ------------------------------------------------------- #
def test_find_aniso_returns_full_keys_when_nothing_found(tpl):
    m = S.create_aniso_shape_model(tpl)
    img = np.random.default_rng(5).normal(0, 0.05, (200, 200))
    res = S.find_aniso_shape_model(m, img, min_score=0.999)
    assert res["found"] is False
    for k in ("row", "col", "column", "score"):
        assert k in res


# --- 6: 基準点は中心で揃える --------------------------------------------------- #
def test_ncc_and_shape_families_share_the_same_anchor(tpl):
    img = _scene([(60, 150)], seed=3)
    a = S.find_shape_model(S.create_shape_model(tpl), img)
    b = M.find_ncc_model(M.create_ncc_model(tpl), img)
    c = S.find_ncc_models(M.create_ncc_model(tpl), img, max_matches=1)["matches"][0]
    d = M.best_match(tpl, img)
    for got in [(a["row"], a["col"]), (b["row"], b["col"]),
                (c["row"], c["column"]), (d["row"], d["col"])]:
        assert abs(got[0] - 60) <= 2 and abs(got[1] - 150) <= 2, got


def test_ncc_keeps_the_top_left_available(tpl):
    b = M.find_ncc_model(M.create_ncc_model(tpl), _scene([(60, 150)], seed=3))
    assert abs(b["row_tl"] - 40) <= 2 and abs(b["col_tl"] - 130) <= 2


# --- 鍵名の互換 ---------------------------------------------------------------- #
def test_find_shape_model_exposes_both_col_and_column(tpl):
    r = S.find_shape_model(S.create_shape_model(tpl), _scene([(60, 150)], seed=3))
    assert r["col"] == r["column"]
    flat = S.find_shape_model(S.create_shape_model(tpl),
                              _scene([(60, 150)], seed=3), num_levels=0)
    assert flat["col"] == flat["column"]


# --- 7: スコアの雑音床(MinContrast) ------------------------------------------- #
def test_score_on_pure_noise_is_near_zero(tpl):
    """|cos| は方向がでたらめでも平均 2/pi = 0.637 になる。

    MinContrast を入れる前は純雑音の画像で最良スコアが 0.73-0.75 出ており、
    **この一族の既定 min_score=0.5 は何も棄却できなかった**。
    """
    m = S.create_shape_model(tpl)
    for sd in range(3):
        img = np.random.default_rng(sd).normal(0, 0.05, (200, 200))
        assert S.find_shape_model(m, img, num_levels=0)["score"] < 0.2
        assert S.find_shape_model(m, img)["found"] is False


def test_low_contrast_object_is_still_found(tpl):
    """MinContrast はコントラストの低い本物まで落としてはいけない。"""
    m = S.create_shape_model(tpl)
    for amp in (1.0, 0.6, 0.4, 0.25):
        img = np.random.default_rng(4).normal(0, 0.03, (200, 200))
        img[60 - 10:60 + 10, 150 - 2:150 + 2] += amp
        img[60 - 2:60 + 2, 150 - 10:150 + 10] += amp
        r = S.find_shape_model(m, img)
        assert r["found"] and abs(r["row"] - 60) <= 2 and abs(r["col"] - 150) <= 2
