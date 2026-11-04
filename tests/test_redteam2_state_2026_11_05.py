"""敵対的検証 2026-11-05 第 2 巡(state)の回帰テスト。

T6  GPU の単 op 経路(``api._try_accel`` -> ``accel.run_batch``)と常駐パイプライン
    (``accel.run_pipeline``)、3-D の ``accel_vol`` が、``b > 0.5`` で選ばれる端の扱い・構造要素を
    無視していた。``device="cpu"``(core)と全画像で比べる —— 真値は core そのもの。
    ``accel.parity("cpu")`` 自身が differ と判定する op が採用表に載っていたことも門にする。
T7  ``seed=None`` 既定の合成器 6 本が ``noise > 0`` で呼ぶたびに違う値を返した。
    lockin / photoncount と同じ「noise needs an explicit integer seed」に揃ったことを、
    2 回呼んで一致するか(不変量)と拒否で確かめる。

torch は CPU 経路だけを使う(GPU は使わない)。
"""
import warnings

import numpy as np
import pytest

import ops


def _probe(seed=7, n=64):
    """accel.parity と同じ作りの画像 + 縁に構造(端の扱いの差は縁で出る)。"""
    rng = np.random.default_rng(seed)
    im = np.clip(rng.random((n, n)) * 0.6 + 0.2 * (np.mgrid[0:n, 0:n][1] / n), 0, 1)
    im[:4, :] = 0.95
    im[-4:, :] = 0.05
    return im


_HIGH_B = (0.6, 0.75, 0.9)        # nearest / constant / wrap と 十字 / 円板 / 線


def _knob_b_rows():
    accel = pytest.importorskip("accel")
    if not accel._HAS_TORCH:
        pytest.skip("accel kernels need torch")
    import fast
    rows = [(k, row[1]) for k, row in accel.ACCEL.items() if row[1] in fast._KNOB_B_OPTIONED]
    return accel, rows


# --------------------------------------------------------------------------- T6
def test_t6_accel_run_batch_equals_core_when_b_selects_a_new_option():
    """b > 0.5 でも accel.run_batch の全画像が core と一致する(修正前: median 0.528・gdilate 0.424 …)。"""
    accel, rows = _knob_b_rows()
    # 報告の 7 本(gaussian / mean_box / median / gerode / gdilate / gopen / gclose)を含む 18 行
    assert len(rows) >= 7
    assert {"gaussian", "mean_box", "median", "gerode", "gdilate", "gopen", "gclose"} <= {c for _, c in rows}
    im = _probe()
    checked = 0
    worst = {}
    for name, core in rows:
        for a in (0.0, 0.5, 1.0):
            for b in _HIGH_B:
                ref = np.clip(np.asarray(ops.RT[core](im.copy(), a, b), np.float64), 0, 1)
                got = np.asarray(accel.run_batch(name, [im], a, b, "cpu")[0], np.float64)
                worst[(name, a, b)] = float(np.abs(got - ref).max())
                checked += 1
    assert checked == len(rows) * 9
    bad = {k: v for k, v in worst.items() if v > 0.0}
    assert not bad, bad


def test_t6_low_b_still_runs_the_kernel():
    """修正が GPU 経路を殺していない: b <= 0.5 は kernel のまま(落ちるのは新しい選択肢だけ)。"""
    accel, rows = _knob_b_rows()
    assert len(rows) >= 7
    for name, _core in rows:
        for a in (0.0, 0.5, 1.0):
            for b in (0.0, 0.25, 0.4, 0.5):
                assert not accel._b_falls_back(name, a, b), (name, a, b)
            for b in _HIGH_B:
                assert accel._b_falls_back(name, a, b), (name, a, b)
    # b を使わない op は常に kernel
    assert not accel._b_falls_back("sobel_amp", 0.5, 0.9)
    assert not accel._b_falls_back("no_such_op", 0.5, 0.9)


def test_t6_api_single_op_gpu_path_defers_to_core():
    """api._try_accel(device 指定の単 op 経路)は b の新しい選択肢では kernel を走らせない。"""
    accel, _rows = _knob_b_rows()
    import api
    import fast
    rev = api._accel_reverse(accel)
    regs = sorted(r for r in fast._KNOB_B_OPTIONED if r in rev)
    assert len(regs) >= 7
    im = _probe()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for reg in regs:
            op = api._resolve(reg)
            for b in _HIGH_B:
                assert api._try_accel(op, im.copy(), 0.5, b, "cpu") is api._NOACCEL, (reg, b)
            # 歴史側は従来どおり kernel が答え、core と全画像で一致する(t_accel_full の b=0.5 列)
            g = api._try_accel(op, im.copy(), 0.5, 0.5, "cpu")
            assert g is not api._NOACCEL, reg
            ref = api.apply(im.copy(), reg, 0.5, 0.5)
            assert float(np.abs(np.asarray(g) - ref).max()) < accel.PARITY_TOL, reg


def test_t6_resident_pipeline_honours_b_mid_segment():
    """常駐パイプラインの途中の段でも b の選択が効く(accel_bridge もここを通る)。"""
    accel, _rows = _knob_b_rows()
    im = _probe()
    steps = [("gauss_filter", 0.5, 0.75), ("gdilate", 0.5, 0.9), ("median_image", 0.25, 0.6)]
    ref = im.copy()
    for name, a, b in steps:
        ref = np.clip(ops.RT[accel.ACCEL[name][1]](ref, a, b), 0, 1)
    got = accel.run_pipeline(steps, [im], "cpu")[0]
    # 段の間は float32 で常駐するので丸めの差だけ(修正前は 0.3 超)
    assert float(np.abs(got - ref).max()) < 1e-5


def test_t6_accel_parity_has_no_op_outside_the_gate():
    """accel.parity("cpu") の全行が PARITY_TOL 未満(修正前: 146 本中 5 本が超え、4 本は differ)。"""
    accel, _rows = _knob_b_rows()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rows = accel.parity("cpu")
    assert len(rows) >= 100
    bad = [(r[0], r[3]) for r in rows if not r[3] < accel.PARITY_TOL]
    assert not bad, bad


def test_t6_accel_vol_gaussian_honours_the_border_choice():
    """兄弟: accel_vol の vol_gaussian_g も b > 0.5 の端の扱いを無視していた(修正前 0.42)。"""
    pytest.importorskip("torch")
    import accel_vol
    rng = np.random.default_rng(0)
    v = rng.random((20, 20, 20))
    checked = 0
    for b in _HIGH_B:
        ref = np.clip(ops.RT["vol_gaussian"](v.copy(), 0.5, b), 0, 1)
        got = accel_vol.run_batch_vol("vol_gaussian_g", [v], 0.5, b, "cpu")[0]
        assert float(np.abs(got - ref).max()) == 0.0, b
        piped = accel_vol.run_pipeline_vol([("vol_gaussian_g", 0.5, b)], [v], "cpu")[0]
        assert float(np.abs(piped - ref).max()) < 1e-6, b
        checked += 1
    assert checked == len(_HIGH_B)
    assert not accel_vol._b_falls_back("vol_gaussian_g", 0.5, 0.5)
    assert not accel_vol._b_falls_back("vol_median_g", 0.5, 0.9)


# --------------------------------------------------------------------------- T7
def _t7_cases():
    import acoustics
    import fringe
    import granular
    import scoop
    return {
        "synthesize_bearing_signal": lambda **k: acoustics.synthesize_bearing_signal(duration=0.05, noise_sigma=0.1, **k),
        "synthesize_speed_ramp": lambda **k: acoustics.synthesize_speed_ramp(duration=0.2, noise_sigma=0.1, **k)["signal"],
        "synthesize_fringes": lambda **k: fringe.synthesize_fringes(np.zeros((16, 16)), noise=0.05, **k),
        "heap_synth_cone": lambda **k: granular.heap_synth_cone(30.0, 20.0, noise=0.01, **k)["side"],
        "discharge_synth": lambda **k: np.asarray(granular.discharge_synth(
            0.02, 0.001, 1500.0, 30.0, 1e-3, 1.0, n_frames=2, grid=128, noise=1e-4, **k)["frames"]),
        "scoop_synth_side": lambda **k: scoop.scoop_synth_side(20.0, 10.0, noise=0.01, **k)["side"],
    }


@pytest.mark.parametrize("name", sorted(["synthesize_bearing_signal", "synthesize_speed_ramp", "synthesize_fringes",
                                         "heap_synth_cone", "discharge_synth", "scoop_synth_side"]))
def test_t7_noise_without_a_seed_is_refused(name):
    f = _t7_cases()[name]
    with pytest.raises(ValueError, match="explicit integer seed"):
        f()
    with pytest.raises(ValueError, match="explicit integer seed"):
        f(seed=None)


@pytest.mark.parametrize("name", sorted(["synthesize_bearing_signal", "synthesize_speed_ramp", "synthesize_fringes",
                                         "heap_synth_cone", "discharge_synth", "scoop_synth_side"]))
def test_t7_an_integer_seed_makes_the_noise_reproducible(name):
    """同じ seed で 2 回 = 1 ビットも同じ、違う seed = 違う(雑音が本当に入っている)。"""
    f = _t7_cases()[name]
    x, y, z = np.asarray(f(seed=3)), np.asarray(f(seed=3)), np.asarray(f(seed=4))
    assert x.size > 1
    assert np.array_equal(x, y)
    assert not np.array_equal(x, z)


def test_t7_noise_free_calls_still_need_no_seed():
    import acoustics
    import fringe
    import granular
    import scoop
    a = acoustics.synthesize_bearing_signal(duration=0.05)
    b = acoustics.synthesize_bearing_signal(duration=0.05)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    assert np.array_equal(fringe.synthesize_fringes(np.zeros((8, 8))), fringe.synthesize_fringes(np.zeros((8, 8))))
    assert np.array_equal(granular.heap_synth_cone(30.0, 20.0)["side"], granular.heap_synth_cone(30.0, 20.0)["side"])
    assert np.array_equal(scoop.scoop_synth_side(20.0, 10.0)["side"], scoop.scoop_synth_side(20.0, 10.0)["side"])
    assert acoustics.synthesize_speed_ramp(duration=0.2)["signal"].size > 1
