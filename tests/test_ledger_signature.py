"""Ledger wrappers expose the real signature (display-only) / 台帳ラッパーが実体の署名を見せる。

指摘: ``fs.ledger.<op>`` は ``(*args, **kw)`` で、補完や ``inspect.signature`` から引数が分からなかった。
署名は ``__signature__`` の注釈で、呼び出し契約(位置/キーワードの受け方)は変えない。
"""
import inspect

import numpy as np

import fullseye as fs


def test_signature_shows_names_and_defaults():
    sig = inspect.signature(fs.ledger.dem_slope)
    assert list(sig.parameters) == ["dem", "cell_size", "method", "units"]
    assert sig.parameters["units"].default == "degrees"
    assert sig.parameters["cell_size"].default is inspect.Parameter.empty


def test_every_ledger_op_has_a_concrete_signature():
    """全台帳 op: 実体の署名と一致(= 表示が実体と食い違わない)。(*args, **kw) だけのものを残さない。"""
    n = 0
    for name in fs.ledger.__dir__():
        mod, entry, _key = fs.ledger._resolve(name)
        want = inspect.signature(entry["func"])
        got = inspect.signature(getattr(fs.ledger, name))
        assert str(got) == str(want), name
        n += 1
    assert n > 800     # 空走査(vacuous)でないこと


def test_call_contract_unchanged():
    dem = np.random.default_rng(0).random((8, 8))
    a = fs.ledger.dem_slope(dem, 5.0)
    b = fs.ledger.dem_slope(dem, cell_size=5.0, units="degrees")
    c = fs.ledger.dem_slope(dem=dem, cell_size=5.0)
    assert np.array_equal(a, b) and np.array_equal(a, c)
    # 署名は注釈のみ: 余計な引数は実体が拒否する(ラッパーが握りつぶさない)。
    try:
        fs.ledger.dem_slope(dem, 5.0, nonexistent=1)
    except TypeError:
        pass
    else:
        raise AssertionError("unknown kwarg must still raise TypeError")
    assert fs.ledger.dem_slope.raw is fs.ledger._resolve("dem_slope")[1]["func"]
