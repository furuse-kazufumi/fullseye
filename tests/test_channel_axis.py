# -*- coding: utf-8 -*-
"""カラー画像を「3 本目の空間軸」として扱う op を見える状態に保つ門。

`api._NDIM_OK["image"] = (2, 3)` は 3-D をわざと通しています。ところが中の
実装は `ndimage.*` を素通しするので、`(H, W, 3)` は**高さ 3 の体積**として
扱われ、近傍演算が色を跨ぎます。

## どう数えたか(探針を 1 度作り直している)

最初の探針は「R にだけエッジを置き、出力の G が 0 でなければ漏れ」でした。
**これは誤り**です —— `invert` は 0 を 1 に写すので、漏れが無くても G の出力は
1.0 になります。点ごとの op と近傍演算を区別できていませんでした。

作り直した探針は**因果の形**です:

* R と G は**両方の入力で 0 と 1 を含む**よう固定する(正規化は配列全体の
  最大で割るので、min/max が動くと漏れが無くても R が動いてしまう)。
* **B の中身だけ**を `(0,1)` の内側で 2 通りに変える。
* それで **R の出力が動いたら**、色を跨いでいる。

2026-09-06 の全数計測(882 op のうち RGB の形のまま返る 472 op):

    跨がない 372 / **跨いだ 100** / 形が変わる 370 / 例外 43

跨いだ 100 の宣言入力型は image 78 / region 11 / volume 4 / color 3 /
rgbimage 2 / video 2。**volume・color・rgbimage・video は 3-D を受けるのが
仕様なので正しい**。image と region の **89 本が不具合**です。

## いまの扱い(既定の数値は 1 つも変えていない)

★ **カラー画像に対して正しい呼び方が現時点で存在しません**。まとめて渡すと
色が混ざり、チャネルごとに 3 回呼ぶと自己正規化する op が各チャネルを自分の
最大で割って**チャネル間の比を壊します**(灰色エッジ法の角度誤差が自前
Sobel 1.03 度 → 画像ごと 4.17 度 → ch ごと 27.86 度、ゼロ点 29.14 度)。

既定は数値を変えず、`FullseyeFallbackWarning` を op ごとに 1 回だけ出して台帳に
記録する。`extra_checks="on"` または `on_error="raise"` では入口で拒否する。
2.0 では既定も拒否へ切り替える予定。選択肢と測定値は
`docs/KNOWN_ISSUES.md` §34。
"""
from __future__ import annotations

import numpy as np
import pytest
import warnings

import api
import fullseye as fs
import ops


def _color(bmid=0.40):
    """R と G は 0 と 1 を含み、B だけが内側で変わる検査画像。"""
    h = w = 16
    r = np.zeros((h, w)); r[:, w // 2:] = 1.0
    g = np.zeros((h, w)); g[:h // 2, :] = 1.0
    b = np.full((h, w), 0.40)
    if bmid != 0.40:
        b[4:12, 4:12] = bmid
    return np.dstack([r, g, b])


#: 台帳から少数を抜いて速く回す。全数の掃引は重い(882 op x 2 回)ので
#: `KNOWN_ISSUES` の数字を更新するときだけ手で回す。
_LEAKY_SAMPLE = ["gauss_filter", "mean_image", "median", "max_filter",
                 "std_filter", "dog", "sk_frangi", "bothat"]
_CLEAN_SAMPLE = ["threshold", "sqrt_image", "abs_image", "gamma"]


@pytest.mark.parametrize("name", _LEAKY_SAMPLE)
def test_channel_unsafe_ops_are_listed(name):
    """漏れると分かっている op が台帳に載っていること。"""
    assert name in api._CHANNEL_UNSAFE_OPS, (
        "%s は色を跨ぐのに _CHANNEL_UNSAFE_OPS に無い" % name)


@pytest.mark.parametrize("name", _LEAKY_SAMPLE)
def test_raise_policy_refuses_a_colour_image(name):
    """``on_error="raise"`` では拒否すること(fail-closed 側の出口)。"""
    with pytest.raises(ValueError, match="cross colour channels"):
        fs.apply(_color(), name, on_error="raise")


@pytest.mark.parametrize("name", _LEAKY_SAMPLE)
def test_default_policy_still_returns_and_records(name):
    """既定では**従来どおり動く**(既存の数値を変えない)が、台帳に残ること。"""
    fs.clear_fallbacks()
    out = np.asarray(fs.apply(_color(), name))
    assert out.shape[:2] == (16, 16), out.shape
    assert name in fs.fallback_counts(), "%s: 記録されていない" % name


def test_default_rgb_warning_is_once_and_keeps_the_historical_numbers():
    """§34: 既定は 1 回だけ警告し、計算結果そのものは動かさない。"""
    rgb = _color()
    expected = np.asarray(ops.RT["gauss_filter"](rgb, 0.5, 0.5))
    fs.clear_fallbacks(reset_warnings=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        got = np.asarray(fs.apply(rgb, "gauss_filter"))
        again = np.asarray(fs.apply(rgb, "gauss_filter"))
    notices = [w for w in caught if issubclass(w.category, fs.FullseyeFallbackWarning)]
    assert len(notices) == 1
    text = str(notices[0].message)
    assert "gauss_filter" in text
    assert "Process each channel separately" in text
    assert "convert the image to grayscale" in text
    assert np.array_equal(got, expected)
    assert np.array_equal(again, expected)
    assert fs.fallback_counts()["gauss_filter"] == 2


def test_extra_checks_refuses_a_colour_image_even_under_default_policy():
    """§34 の opt-in は、既定の fail-soft 方針より優先して拒否する。"""
    with fs.system(extra_checks="on"):
        with pytest.raises(ValueError, match="cross colour channels"):
            fs.apply(_color(), "gauss_filter")


@pytest.mark.parametrize("name", _LEAKY_SAMPLE + _CLEAN_SAMPLE)
def test_two_dimensional_input_is_never_refused(name):
    """2-D は ``raise`` でも通ること —— 門が本業を邪魔していないこと。"""
    gray = np.zeros((16, 16)); gray[:, 8:] = 1.0
    fs.apply(gray, name, on_error="raise")


@pytest.mark.parametrize("name", _CLEAN_SAMPLE)
def test_clean_ops_are_not_listed(name):
    """色を跨がない op を巻き込んでいないこと。"""
    assert name not in api._CHANNEL_UNSAFE_OPS
    fs.apply(_color(), name, on_error="raise")


def test_the_listed_sample_really_leaks():
    """台帳が実測に基づいていること —— サンプルで**実際に漏れる**ことを確かめる。

    台帳は 2026-09-06 の全数計測の写しなので、写し間違いや実装の変化で
    実態とずれうる。少数でよいので毎回**測り直して**突き合わせる。
    """
    a, b = _color(0.40), _color(0.60)
    for name in _LEAKY_SAMPLE:
        oa = np.asarray(fs.apply(a, name), np.float64)
        ob = np.asarray(fs.apply(b, name), np.float64)
        d = float(np.nanmax(np.abs(np.nan_to_num(oa[..., 0] - ob[..., 0]))))
        assert d > 1e-9, (
            "%s: B の中身だけを変えたのに R が動かない = 漏れていない。"
            "台帳から外すこと。" % name)


def test_the_clean_sample_really_does_not_leak():
    """逆側も測る —— 台帳に無い op が本当に漏れていないこと。"""
    a, b = _color(0.40), _color(0.60)
    for name in _CLEAN_SAMPLE:
        oa = np.asarray(fs.apply(a, name), np.float64)
        ob = np.asarray(fs.apply(b, name), np.float64)
        d = float(np.nanmax(np.abs(np.nan_to_num(oa[..., 0] - ob[..., 0]))))
        assert d <= 1e-9, "%s: 漏れている。台帳に足すこと(実測 %.4g)" % (name, d)


def test_counts_match_the_recorded_measurement():
    """機械的に列挙した台帳が、測定済みの 89 本を下回らないこと。"""
    names = tuple(sorted(api._CHANNEL_UNSAFE_OPS))
    assert len(names) >= 89
    assert set(names) == api._CHANNEL_UNSAFE_IMAGE_OPS | api._CHANNEL_UNSAFE_REGION_OPS
    assert all(api.find_op(name) is not None for name in names)
