"""2026-11-09 op 点検(g0_match)の回帰テスト: NCC の縁・NaN・速さ・回転の四隅。

- [high] ``ops._ncc_map`` / ``ncc_locate`` は窓がはみ出す位置を 0 にし、縁で切れた対象から
  同形の隣へ黙って乗り移る。契約(full-overlap のみ)は残し、はみ出しを扱う
  ``matching.ncc_map_partial`` / ``matching.ncc_locate_ex`` を足した。
- [med] NaN 1 画素で相関マップ全体が 0 → ``FsValueError``(``matching._ncc_map`` と同じ)。
- [med] 直接相関で遅い → ``matching._ncc_map``(FFT)へ寄せた。値は丸め誤差で同じ。
- [med] ``shape_locate`` の回転テンプレートの四隅(0 埋め)が相関に入る → マスクで除く。
  刻みは ``matching.shape_locate_fine`` で指定し、放物線で副刻みへ。
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from scipy import ndimage

import matching
import ops
from fslib import FsValueError


def _twin_scene(shift, seed=0):
    """同形の対象 2 個(左は左端から ``shift`` px 外へ、右は (40, 120))と 39×39 テンプレート。"""
    rng = np.random.default_rng(seed)
    im = np.full((80, 200), 0.2)
    blob = np.zeros((31, 31))
    yy, xx = np.mgrid[-15:16, -15:16]
    blob[(yy ** 2 + xx ** 2) < 13 ** 2] = 1.0
    blob[np.abs(yy) < 3] = 0.6
    tpl = np.pad(blob, 4, constant_values=0.2)

    def put(cy, cx):
        y0, x0 = cy - 19, cx - 19
        ys, xs = slice(max(y0, 0), y0 + 39), slice(max(x0, 0), x0 + 39)
        im[ys, xs] = tpl[ys.start - y0:, xs.start - x0:][: im[ys, xs].shape[0],
                                                         : im[ys, xs].shape[1]]

    put(40, 19 - shift)
    put(40, 120)
    return im + 0.02 * rng.standard_normal(im.shape), tpl


def _direct_ncc_reference(v, T):
    """修正前の ``ops._ncc_map``(ndimage.correlate の直接相関)を最小限で写したもの。"""
    v = np.asarray(v, np.float64) - float(np.mean(v))
    Tz = T - T.mean()
    tnorm = float(np.sqrt(np.sum(Tz * Tz)))
    num = ndimage.correlate(v, Tz, mode="constant")
    m1 = ndimage.uniform_filter(v, size=T.shape, mode="constant")
    m2 = ndimage.uniform_filter(v * v, size=T.shape, mode="constant")
    den = np.sqrt(np.maximum(m2 - m1 * m1, 0.0) * float(T.size)) * tnorm
    out = np.zeros_like(v)
    lo = tuple(s // 2 for s in T.shape)
    hi = tuple(n - (s - 1 - s // 2) for n, s in zip(v.shape, T.shape))
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    out[sl] = num[sl] / den[sl]
    return np.clip(out, -1.0, 1.0)


# ── [high] はみ出し ──────────────────────────────────────────────────────── #
@pytest.mark.parametrize("shift", [2, 5, 10, 15, 19])
def test_partial_ncc_keeps_the_true_score_at_the_border(shift):
    im, tpl = _twin_scene(shift)
    cx = 19 - shift
    # 契約 op は full-overlap のみ(変えていない): 真の位置は 0、ピークは隣
    full = ops._ncc_map(im, tpl)
    assert full[40, cx] == 0.0
    assert np.unravel_index(int(np.argmax(full)), full.shape) == (40, 120)
    # 重なり部分だけの NCC は真の位置で隣と同じ高さ
    part = matching.ncc_map_partial(tpl, im, min_overlap=0.5)
    assert part[40, cx] > 0.99
    near = part[39:42, max(cx - 1, 0):cx + 2]
    assert np.nanmax(near) == pytest.approx(np.nanmax(part[30:50, :60]), abs=1e-12)


def test_partial_ncc_finds_a_lone_target_cut_by_the_border():
    im, tpl = _twin_scene(5)
    im[:, 90:] = 0.2 + 0.02 * np.random.default_rng(1).standard_normal((80, 110))  # 隣を消す
    ops.set_match_template(tpl)
    try:
        legacy = ops._ncc_locate(im, 0.0, 0.0)
    finally:
        ops.set_match_template(None)
    # 契約 op は縁の対象を見つけられない: 調べられる最初の列(19 = 窓の半幅)に張り付き、
    # 真の中心(14)から 5 px ずれた所を低い得点で答える
    assert legacy[2] == 19.0 and legacy[0] < 0.9
    r = matching.ncc_locate_ex(tpl, im, min_overlap=0.75)
    assert r["status"] == "border" and r["flags"] == ["border"]
    assert abs(r["row"] - 40) <= 1 and abs(r["col"] - 14) <= 1
    assert r["score"] > 0.99
    assert r["full_overlap"] is False
    assert r["overlap"] == pytest.approx(34 / 39, abs=1e-12)


def test_partial_ncc_marks_insufficient_overlap_as_nan_not_zero():
    im, tpl = _twin_scene(10)                                # 見えている割合 29/39 = 0.744
    part = matching.ncc_map_partial(tpl, im, min_overlap=0.75)
    assert np.isnan(part[40, 9])
    assert np.isfinite(part[40, 120])
    r = matching.ncc_locate_ex(tpl, im, min_overlap=0.75)
    assert 0.0 < r["unsearched_fraction"] < 1.0
    big = np.ones((50, 50))
    r2 = matching.ncc_locate_ex(big, im[:30, :30], min_overlap=1.0)
    assert r2["status"] == "unsearched" and r2["row"] == -1 and np.isnan(r2["score"])


def test_partial_ncc_equals_full_map_where_the_window_fits():
    rng = np.random.default_rng(0)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    for h, w in [(15, 15), (16, 16), (15, 20), (8, 9)]:
        T = img[40:40 + h, 50:50 + w].copy()
        full = ops._ncc_map(img, T)
        part = matching.ncc_map_partial(T, img, min_overlap=1.0)
        fin = np.isfinite(part)
        assert int(fin.sum()) == (120 - h + 1) * (140 - w + 1)
        assert np.abs(part[fin] - full[fin]).max() < 1e-9


def test_partial_ncc_matches_cv2_in_the_valid_region():
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(0)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    T = img[40:55, 50:65].copy()
    ref = cv2.matchTemplate(img.astype(np.float32), T.astype(np.float32), cv2.TM_CCOEFF_NORMED)
    part = matching.ncc_map_partial(T, img, min_overlap=1.0)
    sub = part[7:7 + ref.shape[0], 7:7 + ref.shape[1]]
    assert np.abs(sub - ref).max() < 1e-4


def test_partial_ncc_rejects_bad_arguments():
    img = np.random.default_rng(0).random((20, 20))
    with pytest.raises(FsValueError):
        matching.ncc_map_partial(np.ones((3, 3)) * np.nan, img)
    with pytest.raises(FsValueError):
        matching.ncc_map_partial(np.zeros((0, 3)), img)
    for bad in (0.0, -0.1, 1.5, float("nan")):
        with pytest.raises(FsValueError):
            matching.ncc_map_partial(img[:5, :5], img, min_overlap=bad)


# ── [med] NaN ───────────────────────────────────────────────────────────── #
def test_ncc_map_rejects_a_nan_pixel_instead_of_zeroing_the_map():
    rng = np.random.default_rng(0)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    T = img[40:55, 50:65].copy()
    bad = img.copy()
    bad[5, 5] = np.nan
    with pytest.raises(FsValueError, match="NaN"):
        ops._ncc_map(bad, T)
    ops.set_match_template(T)
    try:
        with pytest.raises(FsValueError):
            ops._ncc_locate(bad, 0.0, 0.0)
        with pytest.raises(FsValueError):
            ops._shape_locate(bad, 0.0, 0.0)
        # 実行時の入口(RT)は op の失敗を fallback の記録に残す(黙って 0 にしない)
        import fullseye as fs
        fs.clear_fallbacks()
        with pytest.warns(Warning):
            got = ops.RT["ncc_locate"](bad, 0.0, 0.0)
        assert np.array_equal(got, np.zeros(3))
        assert any(e["name"] == "ncc_locate" and "NaN" in e["error"] for e in fs.fallbacks())
    finally:
        ops.set_match_template(None)
    # 欠測として扱う入口では NaN を除いた相関で真の位置が出る
    r = matching.ncc_locate_ex(T, bad)
    assert (r["row"], r["col"]) == (47, 57)
    assert r["score"] > 0.999 and r["nonfinite_pixels"] == 1


# ── [med] 速さ ──────────────────────────────────────────────────────────── #
def test_ncc_map_fft_path_agrees_with_the_direct_reference_and_is_faster():
    rng = np.random.default_rng(0)
    big = rng.random((512, 512))
    T = big[100:163, 100:163].copy()
    t0 = time.perf_counter()
    ref = _direct_ncc_reference(big, T)
    t_ref = time.perf_counter() - t0
    t0 = time.perf_counter()
    got = ops._ncc_map(big, T)
    t_new = time.perf_counter() - t0
    assert np.abs(got - ref).max() < 1e-9
    assert t_new < 0.5 * t_ref, (t_new, t_ref)          # 実測 0.03 s 対 0.5 s


# ── [med] shape_locate の四隅 ────────────────────────────────────────────── #
def _rot_scene(bg, ang, seed=0):
    rng = np.random.default_rng(seed)
    obj = np.full((41, 41), bg)
    yy, xx = np.mgrid[-20:21, -20:21]
    obj[(np.abs(yy) < 14) & (np.abs(xx) < 6)] = 1.0
    obj[(np.abs(yy) < 4) & (xx > 0) & (xx < 16)] = 0.0 if bg else 0.25
    big = np.full((160, 160), bg)
    big[60:101, 60:101] = obj
    rot = ndimage.rotate(big, ang, reshape=False, order=1, cval=bg)
    return rot + 0.01 * rng.standard_normal(big.shape), obj


@pytest.mark.parametrize("ang", [30, 60, 90])
def test_shape_locate_excludes_the_rotated_corners(ang):
    img, obj = _rot_scene(0.5, ang)
    ops.set_match_template(obj)
    try:
        s = ops.RT["shape_locate"](img, 0.0, 0.0)
    finally:
        ops.set_match_template(None)
    assert s[3] == float(ang)
    assert s[0] > 0.95, s                                # 修正前 0.7794(30°)
    assert abs(s[1] - 80) <= 1 and abs(s[2] - 80) <= 1


@pytest.mark.parametrize("ang", [0, 30, 60])
def test_shape_locate_on_a_zero_background_barely_moves(ang):
    img, obj = _rot_scene(0.0, ang)
    legacy = -1.0
    for a in range(0, 360, 30):                          # 修正前の作り(四隅 0 埋め)
        legacy = max(legacy, float(_direct_ncc_reference(img, ndimage.rotate(obj, a, reshape=False)).max()))
    ops.set_match_template(obj)
    try:
        s = ops.RT["shape_locate"](img, 0.0, 0.0)
    finally:
        ops.set_match_template(None)
    assert abs(s[0] - legacy) < 1e-3


def test_shape_locate_fine_resolves_angles_between_the_coarse_steps():
    img, obj = _rot_scene(0.5, 15)
    ops.set_match_template(obj)
    try:
        coarse = ops.RT["shape_locate"](img, 0.0, 0.0)
    finally:
        ops.set_match_template(None)
    assert coarse[3] in (0.0, 30.0)                      # 契約 op は 30° 刻みのまま
    r = matching.shape_locate_fine(obj, img, step_deg=5.0)
    assert abs(r["angle_deg"] - 15.0) < 1.0 and r["score"] > 0.98
    assert abs(r["row"] - 80) <= 1 and abs(r["col"] - 80) <= 1
    r30 = matching.shape_locate_fine(obj, img, step_deg=30.0)
    assert abs(r30["angle_deg"] - 15.0) < abs(coarse[3] - 15.0)
    with pytest.raises(FsValueError):
        matching.shape_locate_fine(obj, img, step_deg=0.0)


# ── 2026-11-09 独立レビューで足した回帰 ─────────────────────────────────── #
def test_ncc_map_is_accurate_on_a_smooth_image_with_a_large_dc_offset():
    """DC 1e5 の滑らかな画像: 中心化してから FFT へ渡さないと誤差 1.16e-4(旧経路 3.8e-8)。"""
    from numpy.lib.stride_tricks import sliding_window_view as swv
    rng = np.random.default_rng(42)
    img = 1e5 + np.cumsum(np.cumsum(rng.random((256, 256)), 0), 1) * 1e-3
    for s in (15, 31):
        T = img[100:100 + s, 120:120 + s].copy()
        Tz = T - T.mean()
        V = swv(img - img.mean(), (s, s))
        Vz = V - V.mean(axis=(2, 3), keepdims=True)
        exact = (np.einsum("ijkl,kl->ij", Vz, Tz)
                 / np.sqrt(np.einsum("ijkl,ijkl->ij", Vz, Vz) * (Tz * Tz).sum()))
        got = ops._ncc_map(img, T)[s // 2:s // 2 + exact.shape[0], s // 2:s // 2 + exact.shape[1]]
        assert np.abs(got - exact).max() < 1e-7, (s, np.abs(got - exact).max())


def test_pipeline_path_nan_keeps_the_match_shape_and_is_recorded():
    """ops.RT(パイプライン経路)の NaN: ncc_locate は 3 要素、shape_locate は 4 要素のまま、記録つき。"""
    import warnings
    import fullseye as fs
    rng = np.random.default_rng(0)
    T = rng.random((9, 9))
    im = rng.random((40, 40))
    good_ncc_len = None
    ops.set_match_template(T)
    try:
        good_shape = ops.RT["shape_locate"](im, 0.0, 0.0)
        good_ncc_len = len(ops.RT["ncc_locate"](im, 0.0, 0.0))
        bad = im.copy()
        bad[3, 3] = np.nan
        fs.clear_fallbacks()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s = ops.RT["shape_locate"](bad, 0.0, 0.0)
            n = ops.RT["ncc_locate"](bad, 0.0, 0.0)
    finally:
        ops.set_match_template(None)
    assert len(good_shape) == 4 and len(s) == 4 and np.array_equal(s, np.zeros(4))
    assert good_ncc_len == 3 and np.array_equal(n, np.zeros(3))
    names = [e["name"] for e in fs.fallbacks()]
    assert "shape_locate" in names and "ncc_locate" in names


def test_ncc_map_partial_needs_nanargmax():
    """素の argmax は NaN(調べていない位置)を拾う。docstring の注意どおり nanargmax で正解。"""
    im, tpl = _twin_scene(10)
    part = matching.ncc_map_partial(tpl, im, min_overlap=0.75)
    assert np.unravel_index(int(np.argmax(part)), part.shape) == (0, 0)   # 罠
    assert np.isnan(part[0, 0])
    r, c = np.unravel_index(int(np.nanargmax(part)), part.shape)
    assert (r, c) == (40, 120)
    assert "nanargmax" in matching.ncc_map_partial.__doc__


def test_ncc_locate_ex_flags_missing_data_and_ambiguity():
    rng = np.random.default_rng(0)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    T = img[40:55, 50:65].copy()
    clean = matching.ncc_locate_ex(T, img)
    assert clean["status"] == "ok" and clean["flags"] == []
    holed = img.copy()
    holed[40:48, :] = np.nan                     # 真の窓の上 8/15 行が欠測
    r = matching.ncc_locate_ex(T, holed)
    assert "missing" in r["flags"] and r["status"] != "ok"
    im, tpl = _twin_scene(0)                     # 同形の双子 = 区別できない
    tw = matching.ncc_locate_ex(tpl, im)
    assert "ambiguous" in tw["flags"]
    # border は単独で(双子の場面は必ず ambiguous なので OR にすると空を通す)
    edge = matching.ncc_locate_ex(T, img[:, 52:])        # 真の窓が左端から 2 px はみ出す
    assert edge["flags"] == ["border"] and (edge["row"], edge["col"]) == (47, 5)
    assert edge["geometric_overlap"] < 1.0


def test_ncc_locate_ex_border_is_geometric_and_missing_only_when_it_matters():
    """2 回目の独立レビュー: 内側の NaN 1 画素を border と呼ばない/隅の NaN で missing を立てない。"""
    rng = np.random.default_rng(3)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    T = img[40:55, 50:65].copy()
    inner = img.copy()
    inner[47, 57] = np.nan                               # 真の窓の中心だけ欠測
    r = matching.ncc_locate_ex(T, inner)
    assert r["flags"] == ["window_missing"] and (r["row"], r["col"]) == (47, 57)
    assert r["geometric_overlap"] == 1.0
    corner = img.copy()
    corner[0, 0] = np.nan                                # 判断に効かない欠測
    r = matching.ncc_locate_ex(T, corner)
    assert r["status"] == "ok" and r["flags"] == [] and r["score"] > 0.999
    strict = matching.ncc_locate_ex(T, inner, min_overlap=1.0)   # 真の位置が調べられない
    assert "missing" in strict["flags"]


@pytest.mark.parametrize("step", [5.0, 7.0, 25.0])
@pytest.mark.parametrize("true", [-4.0, -1.5, 2.0, 4.0])
def test_shape_locate_fine_near_zero_and_angle_range(step, true):
    """刻みが 360 を割り切らなくても 0° 付近を詰める。返る角度は [0, 360)。"""
    img, obj = _rot_scene(0.5, true)
    r = matching.shape_locate_fine(obj, img, step_deg=step)
    assert 0.0 <= r["angle_deg"] < 360.0 and 0.0 <= r["coarse_angle_deg"] < 360.0
    err = ((r["angle_deg"] - true) + 180.0) % 360.0 - 180.0
    assert abs(err) < (1.0 if step <= 7.0 else 2.5), (step, true, r)   # 修正前 step 7・+2° で 0.00°


def test_ncc_locate_ex_missing_ignores_positions_with_few_pixels_left():
    """3 回目の確認: 欠測が 95 % の地では、数画素しか残らない位置が偶然の相関で最良に届き、
    missing が偽陽性になった。計り直すのはテンプレートの半分以上の画素が残る位置だけ。"""
    rng = np.random.default_rng(3)
    img = ndimage.gaussian_filter(rng.random((120, 140)), 1.5)
    T = img[40:55, 50:65].copy()
    holed = img.copy()
    drop = rng.random(holed.shape) > 0.05
    drop[30:65, 40:75] = False                           # 真の対象の周りは無傷
    holed[drop] = np.nan
    r = matching.ncc_locate_ex(T, holed)
    assert (r["row"], r["col"]) == (47, 57) and r["score"] > 0.999
    assert "missing" not in r["flags"], r["flags"]


# ── 4 回目の独立確認: missing の計り直しの下限は min_overlap に連動、下限未満は弱い印 ─── #
def _occluded_true_target(seed, mo):
    """真の対象(15x15)の窓の画素を U(0.05, mo) の割合だけ残す(=通常の探索では調べない)。"""
    g = np.random.default_rng(seed)
    img = ndimage.gaussian_filter(g.random((80, 80)), 1.5)
    tr, tc = int(g.integers(15, 65)), int(g.integers(15, 65))
    T = img[tr - 7:tr + 8, tc - 7:tc + 8].copy()
    s = img.copy()
    win = s[tr - 7:tr + 8, tc - 7:tc + 8]
    win[g.random(win.shape) > g.uniform(0.05, mo)] = np.nan
    return T, s, tr, tc


@pytest.mark.parametrize("mo", [0.3, 0.5])
def test_missing_still_works_when_min_overlap_is_half_or_less(mo):
    """固定の下限 0.5 では min_overlap <= 0.5 のとき missing が一度も立たなかった(58/60 → 0/60)。"""
    hits = sum("missing" in matching.ncc_locate_ex(*_occluded_true_target(9000 + i, mo)[:2],
                                                   min_overlap=mo)["flags"]
               for i in range(30))
    assert hits >= 20, hits                                # 実測 mo=0.3: 56/60、0.5: 52/60


@pytest.mark.parametrize("mo", [0.3, 0.5, 0.75])
def test_a_wrong_answer_never_comes_back_as_ok_when_the_target_was_not_searched(mo):
    for i in range(30):
        T, s, tr, tc = _occluded_true_target(9000 + i, mo)
        r = matching.ncc_locate_ex(T, s, min_overlap=mo)
        wrong = abs(r["row"] - tr) > 1 or abs(r["col"] - tc) > 1
        assert not (wrong and r["status"] == "ok"), (i, r["flags"])


def test_decoy_with_a_heavily_occluded_true_target_is_not_ok():
    """真の対象の残り 30 %(min_overlap=0.75 の下限 0.375 未満): 囮 0.905 が flags なしで返っていた。"""
    base = ndimage.gaussian_filter(np.random.default_rng(7).random((100, 100)), 1.5)
    T2 = base[40:61, 40:61].copy()
    scene = base.copy()
    scene[10:31, 70:91] = 0.7 * T2 + 0.3 * base[10:31, 70:91]
    win = scene[40:61, 40:61]
    win[np.random.default_rng(11).random(win.shape) > 0.3] = np.nan
    r = matching.ncc_locate_ex(T2, scene, min_overlap=0.75)
    assert (r["row"], r["col"]) == (20, 80)                # 囮の位置
    assert r["status"] != "ok" and "missing_low_overlap" in r["flags"]
    r2 = matching.ncc_locate_ex(T2, scene, min_overlap=0.5)   # 下限 0.25 なら計り直せる
    assert "missing" in r2["flags"]


@pytest.mark.parametrize("mo,keep,judged", [(0.75, 6, True), (0.75, 5, False),
                                            (0.5, 4, True), (0.5, 3, False)])
def test_remeasure_floor_boundary(mo, keep, judged):
    """4x4 テンプレート: 下限 = min_overlap / 2(0.375 = 6 画素、0.25 = 4 画素)ちょうどは計り直し、
    1 画素少ないと計り直さず弱い印になる。"""
    b = ndimage.gaussian_filter(np.random.default_rng(5).random((60, 60)), 1.0)
    T = b[20:24, 20:24].copy()
    s = b.copy()
    k = np.zeros(16, bool)
    k[np.random.default_rng(1).permutation(16)[:keep]] = True
    w = s[20:24, 20:24]
    w[~k.reshape(4, 4)] = np.nan
    r = matching.ncc_locate_ex(T, s, min_overlap=mo)
    # flags を先に見る(落ちる理由が挙動の違いになるように。数は .get で読む)
    if judged:
        assert "missing" in r["flags"] and "missing_low_overlap" not in r["flags"], r["flags"]
        assert r.get("rescanned_low_overlap_positions") == 0
    else:
        assert "missing_low_overlap" in r["flags"], r["flags"]
        assert r["flags"][-1] == "missing_low_overlap"           # 補足の印は常に最後
        assert r.get("rescanned_low_overlap_positions") == 1


def _intact_with_nan(i, kind):
    """無傷の真の対象(15x15)+ 離れた所の欠測(5 回目の確認の探針と同じ作り)。"""
    g = np.random.default_rng(30000 + i)
    img = ndimage.gaussian_filter(g.random((100, 120)), 1.5)
    tr, tc = int(g.integers(25, 75)), int(g.integers(25, 95))
    T = img[tr - 7:tr + 8, tc - 7:tc + 8].copy()
    s = img.copy()
    keep = np.zeros(s.shape, bool)
    keep[tr - 17:tr + 18, tc - 17:tc + 18] = True
    if kind == "block20":                                 # テンプレートより大きい欠測ブロック 1 つ
        drop = np.zeros(s.shape, bool)
        r0 = 5 if tr > 50 else 75
        c0 = 5 if tc > 60 else 95
        drop[r0:r0 + 20, c0:c0 + 20] = True
    else:                                                 # 点状の欠測 50 %
        drop = g.random(s.shape) < 0.5
    drop &= ~keep
    s[drop] = np.nan
    return T, s, tr, tc


@pytest.mark.parametrize("kind", ["block20", "speckle50"])
@pytest.mark.parametrize("mo", [0.75, 0.3])
def test_weak_flag_does_not_fire_when_the_answer_is_right(kind, mo):
    """5 回目の確認: 残り 0 画素の位置まで「判定できなかった」と数えていたので、答えが正しくても
    30/30 で status が ok でなかった。"""
    for i in range(10):
        T, s, tr, tc = _intact_with_nan(i, kind)
        r = matching.ncc_locate_ex(T, s, min_overlap=mo)
        assert (r["row"], r["col"]) == (tr, tc)
        assert "missing_low_overlap" not in r["flags"] and r["status"] == "ok", (i, r["flags"])


def test_weak_flag_never_hides_ambiguous():
    """双子 + 欠測ブロック: status は ambiguous のまま(弱い印が前にあると隠していた)。"""
    g = np.random.default_rng(77)
    img = ndimage.gaussian_filter(g.random((100, 120)), 1.5)
    T = img[40:55, 40:55].copy()
    s = img.copy()
    s[70:85, 90:105] = T + 1e-4 * g.standard_normal(T.shape)
    s[5:25, 95:115] = np.nan
    r = matching.ncc_locate_ex(T, s)
    assert r["status"] == "ambiguous", r["flags"]
