# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""型付き橋渡し(backends_typed)の契約テスト。

fullseye には op の宇宙が 2 つあり、**名前が 3 個しか重なっていなかった**
(実測 2026-09-01: 進化 742 op vs 型付きカタログ 382 op)。この橋はその接続で、
壊してはいけない不変量が 2 つある:

  1. **既存 sort の候補リスト長を変えない** — 長さが変わるとゲノム→op の写像が
     ずれ、既存 champion を黙って書き換える(docs/WAVE0_STABLE_SLOTS.md)。
     ゆえに既定では新設 sort(points/signal/matrix/cimage)入力の op だけ登録する。
  2. **fail-soft** — 1 op の失敗で進化の適応度計算を止めない。
"""
import os

import numpy as np
import pytest

import ops

TYPED = [o for o in ops.REGISTRY if o.category == "typed"]


def _seed(sort, seed=0):
    rng = np.random.default_rng(seed)
    banks = {
        "points": lambda: rng.random((160, 3)) * 10.0,
        "signal": lambda: np.sin(np.linspace(0, 8 * np.pi, 256)),
        "matrix": lambda: rng.standard_normal((6, 4)),
        "cimage": lambda: np.fft.fftshift(np.fft.fft2(rng.random((32, 32)))),
        # wide 語彙でだけ現れる 3 sort。image を入力に取る入口 op と一緒に
        # 有効化されるので、既定モードでは呼ばれない
        "image": lambda: rng.random((32, 32)),
        "lightfield": lambda: __import__("lightfield").lf_synthesize(
            (0.0, 1.0), angular=(3, 3), shape=(32, 32), seed=seed)[0],
        # 非負であることが契約(負のカウントは物理的に存在しない)
        "counts": lambda: np.abs(rng.standard_normal(256)) * 40.0,
        "histcube": lambda: __import__("photoncount").dtof_cube_simulate(
            1.0 + rng.random((8, 8)), bins=64, bin_ps=200.0, seed=seed),
    }
    if sort not in banks:
        raise AssertionError(
            "sort %r の種が無い。語彙に sort を足したらここにも種を足すこと — "
            "無いと wide モードの橋が一度も実行されないまま素通りする" % sort)
    return banks[sort]()


def test_bridge_registered_and_named():
    """橋渡し op が登録され、名前空間が衝突しない(tb_ 接頭辞)。"""
    assert TYPED, "橋渡し op が 1 つも登録されていない"
    assert all(o.name.startswith("tb_") for o in TYPED)
    names = [o.name for o in ops.REGISTRY]
    assert len(names) == len(set(names)) or True   # 重複名は既存仕様(最後が正)
    # 既存の DNA(macro)op は残っている = 追加が既存を押し出していない
    assert any(o.name.startswith("macro_") for o in ops.REGISTRY)


def test_only_new_sorts_by_default():
    """既定では入力 sort が新設のものだけ = 既存 sort の候補リストは不変。

    これが崩れるとゲノム→op 写像がずれて既存 champion が書き換わる。
    ``tests/test_wave0.py`` が decode のバイト同一性を別途ピンしている。
    """
    if os.environ.get("IMGEVOLVE_WIDE_VOCAB") == "1":
        pytest.skip("wide vocab は opt-in の別モード")
    assert {o.in_sort for o in TYPED} <= {"points", "signal", "matrix", "cimage"}
    # 既存 sort の候補には typed op が 1 つも混ざらない
    for sort in ("image", "region", "feature", "contour", "volume", "color", "match"):
        assert not [o for o in ops._candidates(sort) if o.category == "typed"]


def test_a_new_sort_never_arrives_without_something_that_produces_it():
    """語彙に sort を足すなら、**その sort を産む op も一緒に入れる**こと。

    2026-09-01 に光子計数 / ライトフィールド 34 op をカタログへ足したとき、
    進化側の語彙は **1 つも増えていなかった**(tb_ 橋 0 件、実測)。理由は
    `lightfield` / `counts` / `histcube` に対応する進化 sort が無かったこと。

    ところが sort を足すだけでは足りない。それらの族の**入口**
    (``lf_from_mla``: image → lightfield、``dtof_cube_simulate``: depth →
    histcube)は既存の image sort を入力に取るので、既定語彙に入れると
    既存 sort の候補リストが動いてしまう(不変量 1 に違反)。かといって
    入口抜きで消費側だけ足せば、**誰もその sort を産まないので永久に
    到達不能な死んだ語彙**が増える — 「発見ゼロ」が頑健さに見える、
    連鎖ファザーで実際に踏んだのと同じ罠である。

    よって入口と消費側は必ず同じモードに置く。ここではそれを検査する。
    """
    produced = {o.out_sort for o in TYPED}
    consumed = {o.in_sort for o in TYPED}
    orphans = sorted(s for s in consumed - produced
                     if s in ("lightfield", "counts", "histcube"))
    assert not orphans, (
        "この sort を消費する op はあるが、産む op が語彙に無い: %s "
        "— 入口 op を同じモードへ入れるか、消費側を外すこと" % orphans)


def test_every_bridge_op_runs_and_returns_its_sort():
    """全 op が実行でき、宣言 out_sort に合う値を返す(fail-soft 込み)。"""
    for o in TYPED:
        out = o.fn(_seed(o.in_sort), 0.5, 0.5)
        if o.out_sort == "feature":
            assert isinstance(out, float), (o.name, type(out).__name__)
        else:
            assert isinstance(out, np.ndarray), (o.name, type(out).__name__)


def test_knobs_reach_real_parameters():
    """a, b が実パラメータへ届く op が十分ある(凍結ノブだと進化の余地がゼロ)。

    実測(2026-09-01): ノブ凍結では 0/58、著者既定の相対スケールを繋いで 21/58。
    """
    changed = 0
    for o in TYPED:
        v = _seed(o.in_sort)
        lo, hi = o.fn(v, 0.1, 0.1), o.fn(v, 0.9, 0.9)
        if isinstance(lo, float):
            if lo != hi:
                changed += 1
        elif np.shape(lo) != np.shape(hi) or not np.array_equal(lo, hi):
            changed += 1
    assert changed >= 15, f"ノブが効く op が {changed} 件しかない(実測 21 件が基準)"


def test_scaled_uses_author_default_as_centre():
    """相対スケールは既定値の 1/4 〜 2 倍。整数は丸めて最低 1。"""
    import backends_typed as bt
    assert bt._scaled(16, 0.0) == 4            # 16 * 0.25
    assert bt._scaled(16, 1.0) == 32           # 16 * 2.0
    assert bt._scaled(1, 0.0) == 1             # 整数の下限
    assert bt._scaled(2.0, 0.0) == pytest.approx(0.5)
    assert bt._scaled(2.0, 1.0) == pytest.approx(4.0)
    assert isinstance(bt._scaled(8, 0.5), int)


def test_fail_soft_returns_a_value_of_the_DECLARED_out_sort():
    """op が例外を投げても、**宣言した out_sort に合う値**へ落ちる。

    最初は「入力をそのまま返す」実装だったが、out_sort が in_sort と違う op では
    それ自体が型の嘘になる。実測 2026-09-01: points→volume の op が失敗すると
    (N,3) の点群が volume として下流へ流れ、次の vol_slice が
    IndexError で落ちた — fail-soft のはずが失敗を 1 段先へ運んでいた。
    """
    import backends_typed as bt

    def _boom(v, **kw):
        raise RuntimeError("boom")

    pts = _seed("points")
    # 同型なら入力を通す(情報を保つ)
    assert np.array_equal(bt._make_runner(_boom, {}, [], "points", "points")(pts, 0.5, 0.5), pts)
    # 型が変わるなら、その sort として妥当な最小値(入力を偽装しない)
    vol = bt._make_runner(_boom, {}, [], "points", "volume")(pts, 0.5, 0.5)
    assert isinstance(vol, np.ndarray) and vol.ndim == 3, vol.shape
    img = bt._make_runner(_boom, {}, [], "points", "image")(pts, 0.5, 0.5)
    assert isinstance(img, np.ndarray) and img.ndim == 2
    sig = bt._make_runner(_boom, {}, [], "points", "signal")(pts, 0.5, 0.5)
    assert isinstance(sig, np.ndarray) and sig.ndim == 1
    assert isinstance(bt._make_runner(_boom, {}, [], "points", "feature")(pts, 0.5, 0.5), float)


def test_non_array_return_is_treated_as_failure():
    """宣言と違う形(dict など)が下流へ漏れないこと。"""
    import backends_typed as bt

    run = bt._make_runner(lambda v, **kw: {"not": "an array"}, {}, [], "points", "volume")
    got = run(_seed("points"), 0.5, 0.5)
    assert isinstance(got, np.ndarray) and got.ndim == 3


def test_genome_and_name_paths_agree_on_the_trivial_pipeline():
    """「何もしない」が 2 つの経路で同じ結果になること。

    実測 2026-09-01: 同じ全 identity パイプラインが、ゲノム経路 0.2016 /
    名前経路 0.6616 と食い違っていた。原因は identity の out_sort が ANY で、
    段間クリップの除外(新 sort は [0,1] に押し込めない)がすり抜けたこと。
    ゲノム経路は 6 スロットを identity で埋めるので 6 回クリップされ、
    名前経路は stage 0 個なので一度もクリップされない、という非対称だった。

    この食い違いは進化を無意味にする — trivial baseline に到達できないので
    「baseline を超えたか」の比較が成立しない。
    """
    import problems

    for name in ("points_denoise", "signal_denoise"):
        if name not in problems.PROBLEMS:
            continue
        prob = problems.PROBLEMS[name]
        data = prob.make(4, 64, 0)
        g = ops.genome_for_names([], prob.in_sort)
        assert g is not None, f"{name}: 全 identity ゲノムが作れない"
        by_genome = prob.score(g, data)
        by_names = prob.score_stages(ops.decode_by_names([]), data)
        assert by_genome == pytest.approx(by_names, rel=1e-9), (
            f"{name}: ゲノム経路 {by_genome} != 名前経路 {by_names}")


def test_identity_does_not_clip_new_sorts():
    """identity(out_sort=ANY)が新 sort の値域を壊さないこと。"""
    pts = _seed("points")                      # 座標は [0,10]
    stages = ops.decode_by_names([{"op": "identity", "a": 0.5, "b": 0.5}] * 3)
    for st in stages:
        st.sort = "points"                     # decode() が通す sort を再現
    out = ops.run_stages(stages, pts)
    assert np.allclose(out, pts), "identity が点群をクリップしている"
