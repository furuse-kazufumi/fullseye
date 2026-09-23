# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsgenerative(錯視 / 無限描画 / 循環動画)の門。

★この族の採点は「絵がきれいか」ではない。**絵が否定している不変量**を数で
確かめる —— 目地は厳密に平行か、2 マスは厳密に同値か、規則 90 の行は
二項係数の偶奇か、継ぎ目は本当に無いか。だから全部の門が「画像を見ないで」
通せる(見て確かめる門は 1 つも無い)。
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import illusion as IL                                            # noqa: E402
import perpetual as PP                                           # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 錯視 —— 目が否定している不変量が、数として成り立っているか                    #
# --------------------------------------------------------------------------- #
def test_every_illusion_draws_something_that_is_not_flat():
    """「走った」≠「意味のある出力」。全面同色の錯視は錯視ではない。"""
    for name, (gen, _q, _n) in sorted(IL.ILLUSIONS.items()):
        img = getattr(IL, gen)()
        assert img.ndim == 3 and img.shape[2] == 3, name
        assert np.isfinite(img).all(), name
        assert 0.0 <= img.min() and img.max() <= 1.0, name
        assert img.std() > 0.02, "%s は平坦すぎる(std=%.4f)" % (name, img.std())


def test_cafe_wall_mortar_rows_are_exactly_horizontal():
    """目地は厳密な水平線 —— 傾いて見えるのは目のほうである。"""
    size, rows = 40, 8
    img = IL.illusion_cafe_wall(size=size, rows=rows, cols=10, mortar=2.0)
    g = img[..., 0]
    for k in range(1, rows):
        band = g[k * size - 1:k * size + 1, :]
        # 目地の帯は行ごとに**完全に一定**(= 傾き 0)
        assert band.std(axis=1).max() == 0.0, "目地 %d 行目が一定でない" % k


def test_muller_lyer_shafts_have_identical_length():
    """2 本の軸は厳密に等長 —— そして**素朴に測ると一致しない**。

    ★矢羽根を付けた図で「行の黒い区間」を測ると 223 と 225 になる(矢羽根の
    反エイリアスの裾が軸の端に乗る)。**錯視は人間の目だけを騙すのではない**
    —— 素朴な計測もこの図では 2 画素ずれる。軸そのものが等しいことは、
    矢羽根を外した図が**画素単位で同一**であることで示す。
    """
    L = 220.0
    bare = IL.illusion_muller_lyer(length=L, head=0.0)     # 軸だけ
    full = IL.illusion_muller_lyer(length=L)               # 矢羽根つき
    d = bare[..., 0] < 0.5
    rows = [np.flatnonzero(d[r]) for r in (80, 180)]
    assert len(rows[0]) and len(rows[1])
    assert rows[0][0] == rows[1][0] and rows[0][-1] == rows[1][-1],         "軸だけの図で端がずれている: %r / %r" % (rows[0][[0, -1]], rows[1][[0, -1]])
    assert np.array_equal(d[80], d[180]), "2 本の軸が画素単位で一致しない"

    # ★ head を変えると画布の幅も変わる(矢羽根の置き場が要る)ので、
    #   2 枚を直接重ねることはできない。軸の**長さ**で比べる。
    assert int(np.ptp(rows[0])) == int(round(L)) + 3,         "軸だけの図の長さが指定と違う: %d" % int(np.ptp(rows[0]))

    # そして素朴な計測は、その同じ図で食い違う —— これがこの族の言いたいこと
    fd = full[..., 0] < 0.5
    naive = [int(np.ptp(np.flatnonzero(fd[r]))) for r in (80, 180)]
    assert naive[0] != naive[1], "素朴な計測が一致してしまった(図が壊れている)"
    assert abs(naive[0] - naive[1]) <= 6, "ずれが大きすぎる: %r" % (naive,)


def test_checker_shadow_patches_are_bit_identical():
    """影の外の暗マスと影の中の明マスは**厳密に同値**(差が 0)。"""
    s = 46
    img = IL.illusion_checker_shadow(size=s, n=8)
    vals = []
    for (r, c) in IL.CHECKER_PATCHES:
        blk = img[r * s + 6:(r + 1) * s - 6, c * s + 6:(c + 1) * s - 6]
        # ★ std() は平均を引くので、定数でも 1 ulp 残る(実測 5.6e-17)。
        #   「全部同じ値」を厳密に言うなら ptp(最大 − 最小)。
        assert np.ptp(blk) == 0.0, "マス (%d,%d) が平坦でない" % (r, c)
        vals.append(float(blk.mean()))
    assert vals[0] == vals[1], "2 マスの値が違う: %r" % (vals,)


def test_simultaneous_contrast_patches_are_bit_identical():
    img = IL.illusion_simultaneous_contrast()
    h, w = img.shape[:2]
    a = img[h // 2, w // 4]
    b = img[h // 2, 3 * w // 4]
    assert np.array_equal(a, b), "左右のパッチが違う: %r vs %r" % (a, b)
    # 周りは違っていなければならない(同じなら錯視になっていない)
    assert not np.array_equal(img[10, w // 4], img[10, 3 * w // 4])


def test_kanizsa_has_no_edge_along_the_illusory_contour():
    """錯覚輪郭の上では、画像は背景の定数(勾配が厳密に 0)。"""
    size = 420
    img = IL.illusion_kanizsa(size=size)
    g = img[..., 0]
    c = size * 0.5
    R = size * 0.30
    # 三角形の 1 辺の中点付近 —— パックマンから十分離れた場所を見る
    y0, x0 = c + R * 0.5, c - R * 0.25
    win = g[int(y0) - 6:int(y0) + 6, int(x0) - 6:int(x0) + 6]
    # ★ ptp なら厳密。本物の辺があれば 0.85 前後になる量なので、門は十分厳しい。
    assert np.ptp(win) == 0.0, "辺の上に本物の勾配がある(ptp=%.4f)" % np.ptp(win)


def test_ground_truth_covers_every_illusion_and_asserts_zero():
    gt = IL.illusion_ground_truth()
    assert set(gt["name"]) == set(IL.ILLUSIONS)
    assert np.all(gt["value"] == 0.0), "不変量の真値はすべて 0 のはず"
    for gen in gt["generator"]:
        assert callable(getattr(IL, gen, None)), gen
    with pytest.raises(ValueError):
        IL.illusion_ground_truth("not_an_illusion")


# --------------------------------------------------------------------------- #
# 2. 無限描画 —— 絵とは独立に成り立つ恒等式                                       #
# --------------------------------------------------------------------------- #
def test_the_identities_hold_to_machine_precision():
    """6 本の恒等式。これが通らないなら絵の見た目は関係ない。"""
    I = PP.perpetual_identities()
    assert len(I["system"]) == 8
    # ★許容を 1 つにまとめない。閉形式で厳密に出るものと、**再帰で誤差が積もる**
    #   ものを同じ物差しで見ると、どちらかの門が甘くなる。接触だけは深さ 5 の
    #   再帰の末端なので相対 1e-5(実測 9.2e-07)。
    loose = {"apollonian_tangency": 1e-5}
    for s, ident, res in zip(I["system"], I["identity"], I["residual"]):
        assert res < loose.get(s, 1e-12), "%s: %s の残差 %.3e" % (s, ident, res)


def test_rule_90_is_pascal_mod_two_and_does_not_overflow():
    """★二項係数を積むと C(62,31)*31 が int64 を黙って溢れる。リュカで避ける。"""
    r = PP.perpetual_identities("elementary_ca_rule90")
    assert float(r["residual"][0]) == 0.0
    # 64 行より深くても成り立つ(溢れていたら 1.0 になる深さ)
    for n in (62, 63, 70, 100):
        row = [1 if (n & k) == k else 0 for k in range(n + 1)]
        assert sum(row) == 2 ** bin(n).count("1"), n


def test_langtons_ant_builds_a_highway_with_period_104():
    assert PP.LANGTON_HIGHWAY_PERIOD == 104
    r = PP.perpetual_identities("langtons_ant")
    assert float(r["residual"][0]) == 0.0


def test_the_highway_adds_exactly_twelve_cells_per_period():
    """★「104 歩で 52 マス」と見当で書いたら実測 0.114/歩 と合わなかった。

    測り直すと**正味の増加はちょうど 12 マス**(整数、10 周期でも 120)。
    周期の中で塗っては消すので、正味はずっと少ない。
    """
    r = PP.perpetual_identities("langtons_ant_growth")
    assert float(r["residual"][0]) == 0.0


def test_every_generator_produces_a_picture_with_structure():
    names = [n for n in PP.__all__
             if n.startswith("perpetual_") and n not in
             ("perpetual_state", "perpetual_step", "perpetual_render",
              "perpetual_loop", "perpetual_loop_seam", "perpetual_identities")]
    assert len(names) == 11
    for n in names:
        img = getattr(PP, n)()
        assert img.ndim == 3 and img.shape[2] == 3, n
        assert np.isfinite(img).all(), n
        assert img.std() > 0.02, "%s は平坦(std=%.4f)" % (n, img.std())


# --------------------------------------------------------------------------- #
# 3. 無限に回せる状態 —— 止めどきを op が決めない                                 #
# --------------------------------------------------------------------------- #
def test_state_can_be_stepped_any_number_of_times():
    s = PP.perpetual_state("langtons_ant", size=61)
    assert s["steps"] == 0
    s = PP.perpetual_step(s, 100)
    s = PP.perpetual_step(s, 400)
    assert s["steps"] == 500
    img = PP.perpetual_render(s)
    assert img.ndim == 3 and img.std() > 0.02


def test_stepping_in_two_halves_equals_stepping_once():
    """状態機械であること: 100 + 100 と 200 が同じ絵になる。"""
    a = PP.perpetual_render(PP.perpetual_step(
        PP.perpetual_state("langtons_ant", size=61), 200))
    b = PP.perpetual_state("langtons_ant", size=61)
    b = PP.perpetual_step(PP.perpetual_step(b, 100), 100)
    assert np.array_equal(a, PP.perpetual_render(b))


def test_a_foreign_table_is_refused_with_a_clear_message():
    """★宣言型 table は広い。無関係な表は KeyError でなく明示拒否にする。"""
    for bad in ({}, {"system": "nope"}, {"a": 1}):
        with pytest.raises(ValueError, match="not a perpetual state"):
            PP.perpetual_step(bad, 1)
        with pytest.raises(ValueError, match="not a perpetual state"):
            PP.perpetual_render(bad)


# --------------------------------------------------------------------------- #
# 4. 循環動画 —— 継ぎ目が無いことを、比が 1 であることで示す                       #
# --------------------------------------------------------------------------- #
def test_every_loop_is_seamless_by_construction():
    """★比が **0 ではなく 1 に近い**のが正解。0 は「動きが止まっている」。"""
    for kind in sorted(PP.LOOPS):
        v = PP.perpetual_loop(kind, frames=12, size=120)
        m = PP.perpetual_loop_seam(v)
        assert 0.75 < float(m["ratio"][0]) < 1.35, \
            "%s の継ぎ目の比 %.3f(1 から離れている)" % (kind, m["ratio"][0])
        assert float(m["typical"][0]) > 1e-4, "%s は動いていない" % kind


def test_loop_rejects_something_that_is_not_a_video():
    with pytest.raises(ValueError):
        PP.perpetual_loop_seam(np.zeros((4, 4, 3)))
    with pytest.raises(ValueError):
        PP.perpetual_loop("no_such_loop")


# --------------------------------------------------------------------------- #
# 5. 台帳と公開経路(登録面を 1 つ落とすと静かに消える)                            #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsgenerative as og

    assert og.missing() == []
    public = {n for n in (list(IL.__all__) + list(PP.__all__))
              if callable(getattr(IL, n, None) or getattr(PP, n, None))}
    assert set(og.OPSGENERATIVE) == public
    assert len(og.OPSGENERATIVE) == 30
    assert set(og.categories()) == {"illusion", "perpetual", "stream", "loop"}


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsgenerative as og

    for name in og.OPSGENERATIVE:
        assert hasattr(fs.ledger, name), name


def test_op_find_reaches_the_family():
    import opassist

    assert len(opassist.op_find("illusion")) >= 12
    assert len(opassist.op_find("perpetual")) >= 15


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "generative"]
    assert len(rows) == 30
    assert {r[3] for r in rows} == {"rgb", "rgbvideo", "table"}


def test_the_fuzzer_can_actually_compute_the_state_ops():
    """★「登録したのに一度も計算しない」を避ける(MSA の 9 op で踏んだ穴)。

    宣言 in が ``table`` の op はプールの任意の表では必ず拒否されるので、
    引数ビルダが無いと**走ったことにはなるが計算していない**。
    """
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    for name in ("perpetual_step", "perpetual_render", "perpetual_loop_seam"):
        assert name in cf.OP_ARG_BUILDERS, name
    rng = np.random.default_rng(0)
    args, kwargs = cf.OP_ARG_BUILDERS["perpetual_step"]({}, rng)
    out = PP.perpetual_step(*args, **kwargs)
    assert out["steps"] >= 1
    args, kwargs = cf.OP_ARG_BUILDERS["perpetual_loop_seam"]({}, rng)
    assert float(PP.perpetual_loop_seam(*args, **kwargs)["ratio"][0]) > 0.0
    # 既存の型なので述語と種はすでにある(新語を作っていないことの確認)
    assert "rgb" in cf.TYPE_CHECKS and "rgbvideo" in cf.TYPE_CHECKS


def test_the_family_is_cheap_enough_for_ci():
    """★PoC の所要時間は CI の合否そのもの。全生成器を 1 周して秒を測る。"""
    import time

    t0 = time.time()
    for _name, (gen, _q, _n) in sorted(IL.ILLUSIONS.items()):
        getattr(IL, gen)()
    for n in ("perpetual_ten_print", "perpetual_truchet", "perpetual_elementary_ca",
              "perpetual_langtons_ant", "perpetual_chaos_game", "perpetual_apollonian",
              "perpetual_ifs_attractor", "perpetual_plasma"):
        getattr(PP, n)()
    assert time.time() - t0 < 12.0, "生成器 1 周が遅すぎる"


def test_every_apollonian_circle_is_inside_the_outer_disc():
    """★平方根の枝を選び損ねると、外円の**外へ逃げる円の鎖**が出る。

    絵としては「フラクタルっぽい」ので見ただけでは欠陥と分からない。実際に
    出したので、数で止める —— すべての円は外円に含まれていなければならない。
    """
    circles, made = PP._apollonian_circles(5)
    R = 1.0
    for (k, y, x) in [c for c in circles if c[0] > 0] + [u for u, _p, _e in made]:
        r = 1.0 / k
        assert np.hypot(y, x) + r <= R + 1e-6,             "外へ逃げた円: 中心 (%.3f, %.3f) 半径 %.3f" % (y, x, r)
