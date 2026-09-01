# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Regression guards for the 2026-09-02 audit — "silently wrong number / picture" bugs.

すべて **例外を出さずに間違った値を返していた**型の不具合。各節はまず「元の壊れ方」を
再現できる形で書き、そのうえで直った状態を固定する。

  A1  highpass_image / bandpass_image / fft_image_inv が符号つきの配列を `image` と
      称して返していた(負が約 50% -> 保存・表示で真っ黒に潰れる)。兄弟の
      `ops._highpass` は最初から `_signed01` を通しており、規約が割れていた。
      + 兄弟一掃: **image を出す op は全部 [0,1]** という普遍契約をここで固定する。
  A2  clahe に clip limit が無く `b` が完全に死んでいた(= 実装は AHE で CLAHE ではない)。
  A3  estimate_noise が σ の単位ですらなく、σ>=0.08 で 1.0 に張り付いていた。
  A4  zoom_image_factor / zoom_image_size / rescale_img が同一実装で b が全部死んでいた。
  A5  area_center が中心を返さず、面積でなく面積比(解像度依存)を返していた。
  A6  gabor の `_norm` が向きによる応答の大小を潰していた。
  A11 edges_sub_pix が整数画素座標を返していた(名前に反してサブピクセルでない)。
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage

import ops

RT = ops.RT
BY = ops._BY_NAME


def _photo(n=128, seed=7):
    """構造 + 微小ノイズのある「写真らしい」テスト画像。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.6) ** 2) < (n * 0.2) ** 2
    checker = ((xx.astype(int) // 8 + yy.astype(int) // 8) % 2) * 0.18
    noise = 0.02 * np.random.default_rng(seed).standard_normal((n, n))
    return np.clip(0.3 * (xx / (n - 1)) + 0.4 * disk + checker + noise, 0, 1)


# --------------------------------------------------------------------------- #
# A1: 周波数系 op の符号規約 + image 契約の普遍テスト                          #
# --------------------------------------------------------------------------- #
FREQ_SIGNED = ["highpass_image", "bandpass_image", "fft_image_inv"]


@pytest.mark.parametrize("name", FREQ_SIGNED + ["highpass", "lowpass", "fft_image",
                                                "power_real", "power_byte", "phase_rad"])
def test_frequency_ops_return_unit_range_images(name):
    """周波数ファミリ全員が [0,1]。壊れていた 3 つは負が約 50% を占めていた。"""
    v = _photo()
    for a, b in ((0.0, 0.0), (0.2, 0.5), (0.5, 0.5), (1.0, 1.0)):
        out = np.asarray(RT[name](v.copy(), a, b), np.float64)
        assert np.all(np.isfinite(out)), f"{name} produced NaN/Inf at a={a},b={b}"
        assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9, (
            f"{name}(a={a},b={b}) out of [0,1]: min={out.min():.4f} max={out.max():.4f}")


@pytest.mark.parametrize("name", FREQ_SIGNED)
def test_signed_frequency_ops_keep_the_negative_half(name):
    """符号つき応答は `signed01` 規約 —— 0 が 0.5、負の半分が [0,0.5) に残る。

    単に clip すると負の情報は全部 0 に潰れる(旧挙動と同じ損失)。0.5 の
    両側に実質的な質量があることを確認する。
    """
    out = np.asarray(RT[name](_photo(), 0.2, 0.5), np.float64)
    below = float(np.mean(out < 0.5 - 1e-6))
    above = float(np.mean(out > 0.5 + 1e-6))
    assert below > 0.2 and above > 0.2, (
        f"{name}: 0.5 の両側に応答が残っていない (below={below:.3f}, above={above:.3f})")
    assert float(np.mean(out <= 1e-9)) < 0.05, (
        f"{name}: 画素の {100*float(np.mean(out <= 1e-9)):.1f}% が 0 に潰れている")


@pytest.mark.parametrize("op", [o for o in ops.REGISTRY if o.out_sort == "image"],
                         ids=[o.name for o in ops.REGISTRY if o.out_sort == "image"])
def test_every_image_op_stays_in_the_unit_range(op):
    """★兄弟一掃: `image` を宣言する op は **全員** [0,1] を返す。

    `region` には同じ契約テストが既にあった (`test_op_contracts`) のに `image` には
    無く、そこが A1 の抜け道だった。この掃き出しで見つかったのは 7 op:
    highpass_image / bandpass_image / fft_image_inv(符号規約の割れ)、
    xsp_chamfer_dist(scipy の -1 センチネルをそのまま返す)、
    unsharp / sk_adjust_log / xkor_motion_blur(オーバーシュート)。
    """
    from conftest import copy_input, inputs_for

    for iname, iv in inputs_for(op.in_sort):
        for a, b in ((0.2, 0.5), (0.5, 0.5), (0.8, 0.3)):
            out = op.fn(copy_input(iv), a, b)
            if not isinstance(out, np.ndarray) or not out.size or out.dtype.kind not in "fiu":
                continue
            mn, mx = float(np.min(out)), float(np.max(out))
            assert mn >= -1e-9 and mx <= 1 + 1e-9, (
                f"{op.name} image out of [0,1] on '{iname}' (a={a},b={b}): "
                f"min={mn:.4f} max={mx:.4f}")


def test_chamfer_distance_of_a_full_region_is_not_minus_one():
    """背景が 1 画素も無い入力に scipy は距離でなく -1 を書く。それを素通ししていた。"""
    out = np.asarray(RT["xsp_chamfer_dist"](np.ones((16, 16)), 0.5, 0.5), np.float64)
    assert out.min() >= 0.0, f"chamfer returned negative 'distances': min={out.min()}"
    assert np.allclose(out, 1.0), "背景が無いなら全画素が最遠 = 正規化 1.0"
    empty = np.asarray(RT["xsp_chamfer_dist"](np.zeros((16, 16)), 0.5, 0.5), np.float64)
    assert np.allclose(empty, 0.0)


# --------------------------------------------------------------------------- #
# A2: clahe の clip limit                                                      #
# --------------------------------------------------------------------------- #
def test_clahe_b_is_a_live_clip_limit():
    """旧実装では b=0 と b=1 の差が **きっかり 0.0** だった。"""
    v = _photo(96)
    lo = np.asarray(RT["clahe"](v.copy(), 0.5, 0.0), np.float64)
    hi = np.asarray(RT["clahe"](v.copy(), 0.5, 1.0), np.float64)
    assert float(np.max(np.abs(lo - hi))) > 0.1, "clahe の b がまた効かなくなっている"


def test_clahe_clip_limit_is_monotone_in_contrast():
    """clip limit を上げるほど「元画像から遠い = 強調が強い」方向へ単調に動く。"""
    v = _photo(96)
    base = np.clip(v, 0, 1)
    d = [float(np.mean(np.abs(np.asarray(RT["clahe"](v.copy(), 0.5, b), np.float64) - base)))
         for b in (0.0, 0.2, 0.4, 0.6)]
    assert all(d[i] < d[i + 1] for i in range(len(d) - 1)), f"not monotone in b: {d}"


def test_clahe_b1_is_bit_identical_to_plain_ahe():
    """b=1 は「切り取りが一度も効かない」端で、clip limit 導入前と **ビット一致**。

    上限 = ビン数 256 倍 = 1 ビンが取り得る最大カウントなので、``h - climit <= 0``
    が常に成り立ち再配分が起きない。ここでは clip 無しの CDF を直接組んで照合する。
    """
    v = _photo(96)
    hist = np.histogram(np.clip(v, 0, 1), 256, (0, 1))[0]
    plain = np.cumsum(hist).astype(np.float64)
    plain /= plain[-1]
    limited = ops._clip_limit_cdf(hist, 1.0 * float(v.size))
    assert np.array_equal(plain, limited), "b=1 が素の AHE と一致しない"


def test_clahe_zero_clip_limit_flattens_the_tone_map():
    """b=0(= 平均カウントで切る)はコントラスト強調ゼロ側の端。"""
    v = _photo(96)
    d0 = float(np.mean(np.abs(np.asarray(RT["clahe"](v.copy(), 0.5, 0.0), np.float64) - v)))
    d1 = float(np.mean(np.abs(np.asarray(RT["clahe"](v.copy(), 0.5, 1.0), np.float64) - v)))
    assert d0 < d1 / 2, f"b=0 が強調を抑えていない: {d0:.4f} vs {d1:.4f}"


@pytest.mark.parametrize("b", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_clahe_output_contract_holds_at_every_clip_limit(b):
    """どの clip limit でも [0,1] の有限値、形は不変、最大画素は上位に残る。

    正直な注記: 「画像の最大値が 1.0 に写る」のは **b=1(切り取り無効)のときだけ**。
    切り取った分を全ビンへ再配分する標準 CLAHE では、画像の最大値より上の空ビンにも
    質量が入るので、最大画素の写り先は 1.0 より下になる(実測 b=0 で 0.8290、
    b=0.25 で 0.9051)。これは仕様であってバグではないので、そう書いて固定する。
    """
    v = np.linspace(0.2, 0.8, 64 * 64).reshape(64, 64)
    out = np.asarray(RT["clahe"](v, 0.5, b), np.float64)
    assert out.shape == v.shape and np.all(np.isfinite(out))
    assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9
    idx = np.unravel_index(int(np.argmax(v)), v.shape)
    assert out[idx] >= np.percentile(out, 99), "最大画素が上位 1% に居ない"
    if b == 1.0:
        assert out[idx] == pytest.approx(1.0, abs=1e-9), "b=1 は素の AHE = 最大 -> 1.0"


# --------------------------------------------------------------------------- #
# A3: estimate_noise は σ を返し、飽和しない                                   #
# --------------------------------------------------------------------------- #
def _noise_img(sigma, n=192, seed=3):
    rng = np.random.default_rng(seed)
    return np.clip(0.5 + sigma * rng.standard_normal((n, n)), 0, 1)


def test_estimate_noise_no_longer_saturates_at_one():
    """旧実装は 11 点中 8 点が厳密に 1.0 だった(σ が 3 倍違っても同じ値)。"""
    sig = np.linspace(0.02, 0.22, 11)
    est = [float(RT["estimate_noise"](_noise_img(s), 0.5, 0.5)) for s in sig]
    assert max(est) < 0.9, f"まだ上端に張り付いている: {est}"
    assert all(est[i] < est[i + 1] for i in range(len(est) - 1)), f"not monotone: {est}"
    assert len(set(np.round(est, 6))) == len(est), f"同じ値を返している点がある: {est}"


@pytest.mark.parametrize("sigma", [0.01, 0.05, 0.10, 0.20, 0.30])
def test_estimate_noise_is_in_sigma_units(sigma):
    """返すのは σ そのもの。平坦画像 + ガウス雑音なら真値の ±10% に入る。"""
    est = float(RT["estimate_noise"](_noise_img(sigma), 0.5, 0.5))
    assert abs(est - sigma) < 0.1 * sigma, f"sigma={sigma} -> {est:.5f}"


def test_estimate_noise_of_a_flat_image_is_zero():
    assert float(RT["estimate_noise"](np.full((64, 64), 0.42), 0.5, 0.5)) == pytest.approx(0.0, abs=1e-12)


# --------------------------------------------------------------------------- #
# A4: zoom 三兄弟が別物になり、b が生きている                                  #
# --------------------------------------------------------------------------- #
ZOOMS = ["zoom_image_factor", "zoom_image_size", "rescale_img"]


def test_zoom_siblings_are_not_the_same_implementation():
    """旧実装は 3 つとも geom "zoom" に相乗りで、相互の最大差が 0.0 / 4.9e-14 だった。"""
    v = _photo(96)
    outs = {n: np.asarray(RT[n](v.copy(), 0.9, 0.5), np.float64) for n in ZOOMS}
    zf, zs, ri = outs["zoom_image_factor"], outs["zoom_image_size"], outs["rescale_img"]
    assert zs.shape != zf.shape, "zoom_image_size は目標サイズ指定なので shape が変わる"
    assert zf.shape == ri.shape
    assert float(np.max(np.abs(zf - ri))) > 1e-6, "factor 版と rescale_img がまだ同一"


@pytest.mark.parametrize("name", ZOOMS)
def test_zoom_ops_actually_use_b(name):
    """3 つとも b が完全に死んでいた(b=0 と b=1 の差が 0.0)。"""
    v = _photo(96)
    y0 = np.asarray(RT[name](v.copy(), 0.9, 0.0), np.float64)
    y1 = np.asarray(RT[name](v.copy(), 0.9, 1.0), np.float64)
    if y0.shape != y1.shape:
        return                                    # 目標サイズ版は shape 自体が動く = b は生きている
    assert float(np.max(np.abs(y0 - y1))) > 1e-6, f"{name}: b がまた効いていない"


def test_zoom_image_size_returns_the_requested_size():
    """名前どおり **サイズ** で駆動する: 出力 shape が (H*(0.5+a), W*(0.5+b))。"""
    v = _photo(80)
    H, W = v.shape
    for a, b in ((0.0, 0.0), (0.25, 0.75), (1.0, 1.0)):
        out = np.asarray(RT["zoom_image_size"](v.copy(), a, b), np.float64)
        assert out.shape == (round(H * (0.5 + a)), round(W * (0.5 + b))), (a, b, out.shape)


def test_zoom_image_factor_uses_two_independent_scales():
    """HALCON の ScaleHeight / ScaleWidth。a だけ動かすと縦、b だけ動かすと横が変わる。"""
    n = 96
    yy, xx = np.mgrid[0:n, 0:n]
    stripes_h = (0.5 + 0.4 * np.sin(2 * np.pi * yy / 8.0))     # 横縞 = 行方向に変化
    a_only = np.asarray(RT["zoom_image_factor"](stripes_h.copy(), 1.0, 0.5), np.float64)
    b_only = np.asarray(RT["zoom_image_factor"](stripes_h.copy(), 0.5, 1.0), np.float64)
    # 縦倍率(a)は横縞の周期を変える。横倍率(b)は横縞には効かない。
    assert float(np.max(np.abs(a_only - stripes_h))) > 0.1
    assert float(np.max(np.abs(b_only - stripes_h))) < 1e-6


def test_rescale_img_b_selects_the_interpolation_order():
    """b=0 は最近傍なので入力の値集合の外に新しい値を作らない(補間なし)。"""
    v = np.round(_photo(64) * 4) / 4.0                # 5 段だけの階段画像
    nn = np.asarray(RT["rescale_img"](v.copy(), 0.9, 0.0), np.float64)
    cub = np.asarray(RT["rescale_img"](v.copy(), 0.9, 0.5), np.float64)
    assert len(np.unique(np.round(nn, 9))) <= len(np.unique(v)), "b=0 が最近傍になっていない"
    assert len(np.unique(np.round(cub, 9))) > len(np.unique(v)), "b=0.5 が補間していない"


def test_rescale_img_default_b_is_bit_identical_to_the_old_cubic_default():
    """b=0.5 -> order 3。b が死んでいた頃(ndimage 既定 order=3)とビット一致。"""
    v = _photo(64)
    s = 0.7 + 0.6 * 0.9
    off = (v.shape[0] * (1 - 1 / s) / 2, v.shape[1] * (1 - 1 / s) / 2)
    old = np.clip(ndimage.affine_transform(v, np.array([1 / s, 1 / s]), offset=off,
                                           mode="reflect"), 0, 1)
    assert np.array_equal(old, np.asarray(RT["rescale_img"](v.copy(), 0.9, 0.5), np.float64))


# --------------------------------------------------------------------------- #
# A5: area_center が中心を返し、解像度に依らない                               #
# --------------------------------------------------------------------------- #
def test_area_center_returns_area_and_centre():
    """旧実装は `np.mean(mask)` の 1 スカラ = 中心を返さない・面積でなく面積比。"""
    m = np.zeros((420, 420))
    m[30:90, 30:90] = 1.0
    out = np.asarray(RT["area_center"](m, 0.5, 0.5), np.float64)
    assert out.shape == (3,), "area_center は (面積, 行, 列) の 3 成分"
    assert out[0] == pytest.approx(3600 / 176400.0, rel=1e-9)
    assert out[1] == pytest.approx(59.5 / 419.0, rel=1e-6)
    assert out[2] == pytest.approx(59.5 / 419.0, rel=1e-6)
    assert BY["area_center"].out_sort == "match"


def test_area_center_centre_is_resolution_independent():
    """同じ相対位置・相対サイズなら解像度が倍でもほぼ同じ 3 成分を返す。"""
    a = np.zeros((420, 420)); a[30:90, 30:90] = 1.0
    b = np.zeros((840, 840)); b[60:180, 60:180] = 1.0
    ra = np.asarray(RT["area_center"](a, 0.5, 0.5), np.float64)
    rb = np.asarray(RT["area_center"](b, 0.5, 0.5), np.float64)
    assert np.allclose(ra, rb, atol=2e-3), (ra, rb)


def test_area_center_tracks_the_blob_position():
    m1 = np.zeros((420, 420)); m1[30:90, 30:90] = 1.0
    m2 = np.zeros((420, 420)); m2[300:360, 300:360] = 1.0
    r1 = np.asarray(RT["area_center"](m1, 0.5, 0.5), np.float64)
    r2 = np.asarray(RT["area_center"](m2, 0.5, 0.5), np.float64)
    assert r1[0] == pytest.approx(r2[0])              # 面積は同じ
    assert r2[1] > r1[1] + 0.5 and r2[2] > r1[2] + 0.5


def test_area_center_of_an_empty_region_is_fail_soft():
    out = np.asarray(RT["area_center"](np.zeros((32, 32)), 0.5, 0.5), np.float64)
    assert np.allclose(out, [0.0, 0.5, 0.5]) and np.all(np.isfinite(out))


# --------------------------------------------------------------------------- #
# A6: gabor が向きによる応答の大小を保つ                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["gabor", "gen_gabor"])
def test_gabor_keeps_the_orientation_contrast(name):
    """`_norm`(画像ごとの最大値で割る)は 54.9 倍の差を 1.35 倍に潰していた。"""
    n = 96
    yy, xx = np.mgrid[0:n, 0:n]
    horiz = 0.5 + 0.4 * np.sin(2 * np.pi * yy / 8.0)      # 横縞
    m_para = float(np.mean(RT[name](horiz.copy(), 0.0, 0.5)))   # a=0 -> 縦縞検出器
    m_perp = float(np.mean(RT[name](horiz.copy(), 0.5, 0.5)))   # a=0.5 -> 横縞検出器
    assert m_perp / max(m_para, 1e-12) > 20.0, (
        f"{name}: 向きの識別力が潰れている ({m_perp:.5f} / {m_para:.5f})")


@pytest.mark.parametrize("name", ["gabor", "gen_gabor"])
def test_gabor_orientation_convention_a0_is_vertical_stripes(name):
    """docstring の規約: a=0 (θ=0) が **縦縞** に応答する。"""
    n = 96
    yy, xx = np.mgrid[0:n, 0:n]
    vert = 0.5 + 0.4 * np.sin(2 * np.pi * xx / 8.0)
    assert float(np.mean(RT[name](vert.copy(), 0.0, 0.5))) > \
        20.0 * float(np.mean(RT[name](vert.copy(), 0.5, 0.5)))


@pytest.mark.parametrize("name", ["gabor", "gen_gabor"])
def test_gabor_scale_is_image_independent(name):
    """固定スケール(カーネル L1)なので、同じ模様なら明るさを変えても比例する。

    `_norm` だと画像ごとに割る数が変わるので、この比例関係が壊れていた。
    """
    n = 96
    yy, _ = np.mgrid[0:n, 0:n]
    base = 0.5 + 0.4 * np.sin(2 * np.pi * yy / 8.0)
    half = 0.5 + 0.2 * np.sin(2 * np.pi * yy / 8.0)       # 振幅ちょうど半分
    r_base = float(np.mean(RT[name](base.copy(), 0.5, 0.5)))
    r_half = float(np.mean(RT[name](half.copy(), 0.5, 0.5)))
    assert r_half / r_base == pytest.approx(0.5, rel=1e-6)


# --------------------------------------------------------------------------- #
# A11: edges_sub_pix が本当にサブピクセル                                      #
# --------------------------------------------------------------------------- #
def test_edges_sub_pix_locates_a_known_subpixel_edge():
    """真の位置が列 20.37 のステップエッジ。旧実装は {20.0, 21.0} しか返さなかった。"""
    true_col, n = 20.37, 48
    img = np.clip(np.arange(n)[None, :] * np.ones((n, 1)) - true_col + 0.5, 0, 1)
    pts = np.vstack(RT["edges_sub_pix"](img, 0.2, 0.0)["cs"])
    err = float(np.mean(np.abs(pts[:, 1] - true_col)))
    assert err < 0.1, f"サブピクセル精度が出ていない: 平均絶対誤差 {err:.4f} px"
    assert not np.allclose(pts, np.round(pts)), "座標がまだ整数のまま"


def test_edges_sub_pix_is_finite_on_degenerate_inputs():
    for im in (np.full((16, 16), 0.4), np.zeros((5, 5)), np.array([[0.0, 1.0], [1.0, 0.0]]),
               np.array([[0.5]])):
        out = RT["edges_sub_pix"](im, 0.2, 0.0)
        assert all(np.isfinite(c).all() for c in out["cs"])


# --------------------------------------------------------------------------- #
# 不変量: 進化の既定語彙(候補リスト)が動いていないこと                       #
# --------------------------------------------------------------------------- #
def test_candidate_lists_are_unchanged_by_this_audit():
    """ゲノム -> op の写像は `_candidates(sort)` の **順序と長さ**で決まる。

    この監査では op の追加・削除・並べ替えを一切していないので、既存 sort の
    候補リストは 1 つも動いていないはず。`area_center` は out_sort を feature ->
    match に変えたが、どちらも終端 sort(候補は identity だけ)なので decode の
    連鎖も変わらない。
    """
    for sort in (ops.IMAGE, ops.REGION, ops.CONTOUR, ops.FEATURE, ops.MATCH, ops.VOLUME):
        cands = ops._candidates(sort)
        assert cands, f"{sort} の候補が空"
    assert [o.name for o in ops._candidates(ops.FEATURE)] == ["identity"]
    assert [o.name for o in ops._candidates(ops.MATCH)] == ["identity"]
    # area_center は region 入力のまま = region の候補リストに居続ける
    assert "area_center" in [o.name for o in ops._candidates(ops.REGION)]
