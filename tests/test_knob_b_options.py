# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2 つ目のノブ(``b``)に選択肢を持たせた op の、互換性と実効性を固定する。

★**この門が守っているのは「過去の結果」**。これらの op の ``b`` は 2026-09-17 まで
「未使用」で、保存済みの進化プログラムが持つ ``b`` の値は事実上ばらばらに散って
いた。だから選択肢を全域に割り当てると**保存済みプログラムが全部壊れる**。
歴史的な挙動を ``b < 0.5`` の帯に置くことで、およそ半数はビット単位で不変になる。

ここで見るのは 3 つ:

1. ``b < 0.5`` が **旧実装とビット一致**する(互換性の約束そのもの)。
2. ``b >= 0.5`` で **本当に変わる**(選択肢が飾りでない)。
3. 変わらない組み合わせがあるなら、それが**原理的に説明できる**もの
   (窓 3 では ``reflect`` と ``nearest`` が一致する)だけであること。
"""
import numpy as np
import pytest
from scipy import ndimage

import ops


BY = {o.name: o for o in ops.REGISTRY}

#: 端の扱いを ``b`` で選ぶ op -> 旧実装(scipy 既定 = reflect)
_BORDER_OPS = {
    "gaussian": lambda v, a: ndimage.gaussian_filter(v, sigma=0.3 + 2.7 * a),
    "mean_box": lambda v, a: ndimage.uniform_filter(v, size=ops._k(a)),
    "median": lambda v, a: ndimage.median_filter(v, size=ops._k(a)),
    "vol_gaussian": None,                       # 3-D。下で別に見る
}

#: 構造要素の形を ``b`` で選ぶ op -> 旧実装(正方形)
_SE_OPS = {
    "gerode": ndimage.grey_erosion,
    "gdilate": ndimage.grey_dilation,
    "gopen": ndimage.grey_opening,
    "gclose": ndimage.grey_closing,
}

#: 歴史側で試す点。★**0.5 を含める** —— 0.5 は「まん中」として既定値に使われて
#: いる(``api.apply`` の既定、studio の中央、保存済みプログラムの初期値)ので、
#: ここが新しい側に落ちると**既定のまま呼んだだけで答えが変わる**。
#: 最初 ``b < 0.5`` で切ったら、gaussian と HALCON 別名の一致検査まで割れた。
_LOW = (0.0, 0.1, 0.25, 0.4, 0.49, 0.4999, 0.5)
#: 新しい側。3 つの選択肢がそれぞれ当たるように選ぶ。
_HIGH = (0.5001, 0.6, 0.7, 0.8, 0.9, 1.0)


def _probe():
    """構造のある画像 —— 端の扱いの差は**縁でしか出ない**ので、縁に構造を置く。"""
    rng = np.random.default_rng(20260917)
    im = np.clip(rng.normal(0.5, 0.15, (96, 96)), 0.0, 1.0)
    im[:6, :] = 0.95                             # 上端に明るい帯
    im[-6:, :] = 0.05                            # 下端に暗い帯
    im[20:50, 20:60] = 0.9
    return im


@pytest.mark.parametrize("name", sorted(set(_BORDER_OPS) - {"vol_gaussian"}) + sorted(_SE_OPS))
def test_the_lower_half_of_b_reproduces_the_old_behaviour_bit_for_bit(name):
    """``b < 0.5`` は旧実装とビット一致すること(保存済みプログラムの約束)。"""
    im = _probe()
    old = _BORDER_OPS.get(name)
    fn = BY[name].fn
    for a in (0.0, 0.2, 0.55, 0.8, 1.0):
        if old is not None:
            want = np.asarray(old(im.copy(), a))
        else:                                    # モルフォロジー: 正方形の旧経路
            want = np.asarray(_SE_OPS[name](im.copy(), size=ops._k(a)))
        for b in _LOW:
            got = np.asarray(fn(im.copy(), a, b))
            assert np.array_equal(got, want), (
                f"{name}: b={b} (a={a}) で旧実装と一致しない —— "
                "b<0.5 の帯は過去の結果を保つ約束なので、ここが割れたら"
                "保存済みの進化プログラムが黙って別の答えを返す")


@pytest.mark.parametrize("name", sorted(set(_BORDER_OPS) - {"vol_gaussian"}) + sorted(_SE_OPS))
def test_the_upper_half_of_b_actually_changes_the_result(name):
    """``b >= 0.5`` で本当に変わること(選択肢が飾りでないこと)。

    ★窓 3 の ``nearest`` だけは ``reflect`` と**原理的に**一致する(はみ出しが
    1 画素なので複製先が同じ)。そこだけは「変わらなくて正しい」ので、
    例外として名指しで許す —— 「たまたま変わらない」を許さないため。
    """
    im = _probe()
    fn = BY[name].fn
    for a in (0.0, 0.55, 1.0):
        k = ops._k(a)
        base = np.asarray(fn(im.copy(), a, 0.0))
        for b in _HIGH:
            got = np.asarray(fn(im.copy(), a, b))
            if np.array_equal(got, base):
                assert name in _BORDER_OPS and k == 3 and ops._border(b) == "nearest", (
                    f"{name}: b={b} (a={a}, 窓 {k}) で結果が変わらない —— "
                    "説明のつかない一致は、ノブが配線されていないか、選択肢が"
                    "実質同じかのどちらか")


def test_the_border_and_shape_maps_are_exactly_as_documented():
    """写像そのものを固定する(帯の境目が動いたら気づけるように)。"""
    for b in (0.0, 0.25, 0.49, 0.4999, 0.5):          # ★0.5 は歴史側(既定値)
        assert ops._border(b) == "reflect"
        assert ops._se(b, 5) is None
    assert [ops._border(b) for b in (0.5001, 0.6)] == ["nearest", "nearest"]
    assert [ops._border(b) for b in (0.7, 0.8)] == ["constant", "constant"]
    assert [ops._border(b) for b in (0.85, 1.0)] == ["wrap", "wrap"]
    # 形: 十字 / 円板 / 水平線。面積の大小で取り違えを検出する。
    cross, disc, line = (ops._se(b, 7) for b in (0.6, 0.7, 0.9))
    # 半径 3 の離散円板は 29 画素(連続面積 pi*3^2 = 28.3 と整合)。37 と書いて
    # 落とした —— 面積は数えるもので、暗算するものではない。
    assert cross.sum() == 13 and disc.sum() == 29 and line.sum() == 7, \
        (int(cross.sum()), int(disc.sum()), int(line.sum()))
    assert cross[3, :].all() and cross[:, 3].all()          # 十字は中央の行と列
    assert line[3, :].all() and not line[0, :].any()        # 水平線は中央の行だけ


def test_a_directional_structuring_element_does_something_a_square_cannot():
    """水平線の構造要素は**横筋を残して縦方向だけ均す**。形を選べる意味はここ。

    正方形では両方向が同時に削られるので、この非対称は作れない —— 選択肢を
    足した理由そのものを数値で押さえる。
    """
    im = np.full((64, 64), 0.2)
    im[30:34, :] = 0.9                            # 横筋(高さ 4)
    im[:, 30:34] = 0.9                            # 縦筋(幅 4)
    square = np.asarray(BY["gopen"].fn(im.copy(), 1.0, 0.0))    # 9x9 正方形
    liney = np.asarray(BY["gopen"].fn(im.copy(), 1.0, 0.9))     # 9 の水平線
    h_sq, v_sq = float(square[32, 10]), float(square[10, 32])
    h_ln, v_ln = float(liney[32, 10]), float(liney[10, 32])
    assert abs(h_sq - v_sq) < 1e-9, "正方形なのに縦横で差が出た(前提が崩れている)"
    assert h_ln > v_ln + 0.5, (
        f"水平線の構造要素で縦横に差が出ていない(横 {h_ln:.3f} / 縦 {v_ln:.3f})")


def test_vol_gaussian_keeps_the_same_promise_in_three_dimensions():
    """3-D 版も同じ約束(``b<0.5`` は旧実装、上半分で変わる)を守ること。"""
    rng = np.random.default_rng(20260917)
    vol = np.clip(rng.normal(0.5, 0.15, (24, 24, 24)), 0.0, 1.0)
    vol[:3] = 0.95
    fn = BY["vol_gaussian"].fn
    for a in (0.2, 0.8):
        want = np.asarray(ndimage.gaussian_filter(vol.copy(), sigma=0.3 + 2.7 * a))
        for b in _LOW:
            assert np.array_equal(np.asarray(fn(vol.copy(), a, b)), want), \
                f"vol_gaussian: b={b} (a={a}) で旧実装と一致しない"
        assert not np.array_equal(np.asarray(fn(vol.copy(), a, 0.9)), want), \
            f"vol_gaussian: b=0.9 (a={a}) で結果が変わらない"


def test_the_default_knob_value_is_on_the_historical_side():
    """★``b = 0.5`` は**必ず**歴史側であること。

    0.5 は「まん中」として至るところで既定値になっている(``api.apply`` の既定、
    studio の中央、保存済みプログラムの初期値)。ここを新しい選択肢に割り当てると
    **何も指定していない呼び出しの答えが変わる** —— 実際、最初に ``b < 0.5`` で
    切ったときは ``gaussian`` と HALCON 別名 ``gauss_filter`` の一致検査が割れた。
    """
    import api
    assert ops._border(0.5) == "reflect" and ops._se(0.5, 7) is None
    im = _probe()
    for name in sorted(set(_BORDER_OPS) - {"vol_gaussian"}) + sorted(_SE_OPS):
        bare = np.asarray(api.apply(im.copy(), name))          # b を指定しない
        half = np.asarray(api.apply(im.copy(), name, 0.5, 0.5))
        assert np.array_equal(bare, half), (
            f"{name}: 既定のまま呼んだ結果と b=0.5 が違う —— "
            "既定値が新しい選択肢の側に落ちている")
