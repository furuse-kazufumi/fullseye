# -*- coding: utf-8 -*-
"""大きい行列分解が、スレッド上限の**外**で走っていないこと。

2026-09-06 の実測: OpenBLAS は論理 CPU 数だけスレッドを立てるが、LAPACK の
分解では一度も勝たない。24 論理 CPU のこの機械で ``svd(64x64)`` は
1 スレッド 0.165ms / 24 スレッド 0.651ms(3.9 倍)。格子 92 升で見ると、
何もしない状態は最適の合計に対して **3975ms 損** し、最悪の升目は 19.91 倍だった。
表と根拠は :mod:`fsthreads` の docstring。

修正は「分解の周りだけ絞る」なので、**絞り忘れた場所があれば効かない**。
仕組みを足しただけで満足すると、経路のほとんどが素通しのまま緑になる
(同型のラッパが 24 家族あって 1 つしか通っていなかった、という前科がある)。
そこでこの門は、代表的な仕事を実際に流し、**上限の外で走った大きい分解**を
数えて台帳と突き合わせる。

台帳は**両方向**に見る:

* 台帳に無い場所が上限の外で分解した -> 失敗(絞り忘れ、または新しい op)
* 台帳にあるのに一度も現れない       -> 失敗(消えた場所が台帳に残っている)

## この門が見ていないもの(正直に)

流すのは **2-D レジストリの op を全部 1 回ずつ**、それだけである。3-D op・
校正・再構成・光学など、引数の組み立てに手間がかかる経路は**通っていない**。
「観測した分解の数」を一緒に固定してあるので、経路が痩せれば数が減って気づける
—— 数字が減ったら「頑健になった」ではなく「流れていない」を先に疑うこと。
"""
from __future__ import annotations

import collections
import warnings

import numpy as np
import pytest

import api
import fsthreads
import ops

#: 探針の大きさ。``_rpca`` は work_max=64 に落としてから分解するので、
#: これより小さくても 64x64 の SVD は出る。実際の使用に近い側へ寄せておく。
_N = 192

#: 上限の外で大きい分解をしてよい場所(理由つき)。**空を目指す**。
#: キーは ``<file>:<関数>``。行番号は編集で動くので使わない。
ALLOWED = {}

#: 観測できた「短辺 >= MIN_N の分解」の最小件数。
#: 経路が痩せて 0 件になれば、この門は何も見ていないのに緑になる。
_MIN_OBSERVED_BIG = 20

_WATCHED = ("svd", "eigh", "eigvalsh", "qr", "pinv", "lstsq", "cholesky", "solve", "inv")


def _img(n):
    """``tests/test_op_probe_ledger.py`` の 2 枚目と同じ式(構造のある入力)。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)


def _where():
    """呼び出し元を ``<file>:<関数>`` で。numpy 内部からは fullseye 側まで遡る。"""
    import os
    import traceback
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fr in reversed(traceback.extract_stack()[:-2]):
        path = os.path.abspath(fr.filename)
        if not path.startswith(repo):
            continue
        rel = os.path.relpath(path, repo)
        head = rel.split(os.sep)[0]
        if head in ("tests", "build"):
            continue
        return f"{os.path.basename(rel)}:{fr.name}"
    return "<outside the repo>"


@pytest.fixture(scope="module")
def survey():
    """レジストリを 1 周し、大きい分解が上限の中で走ったかを場所ごとに数える。"""
    unlimited = collections.Counter()
    limited = collections.Counter()
    small = collections.Counter()
    originals = {n: getattr(np.linalg, n) for n in _WATCHED}

    def wrap(name, orig):
        def watcher(*a, **kw):
            arr = a[0] if a else None
            shape = getattr(arr, "shape", ())
            n = min(shape[-2:]) if len(shape) >= 2 else 0
            if n < fsthreads.MIN_N:
                small[name] += 1
            elif fsthreads.limited():
                limited[_where()] += 1
            else:
                unlimited[_where()] += 1
            return orig(*a, **kw)
        return watcher

    for name, orig in originals.items():
        setattr(np.linalg, name, wrap(name, orig))
    try:
        inputs = _build_inputs(_N)
        for op in ops.REGISTRY:
            v = inputs.get(op.in_sort)
            if v is None:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    api.apply(v, op.name, 0.5, 0.5, on_error="fallback")
            except Exception:                       # noqa: BLE001 - 門の対象外
                continue
    finally:
        for name, orig in originals.items():
            setattr(np.linalg, name, orig)
    return {"unlimited": unlimited, "limited": limited, "small": small}


def _build_inputs(n):
    g = _img(n)
    return {
        "image": g,
        "region": (g > 0.55).astype(np.float64),
        "color": np.stack([g, np.roll(g, 5, 0), np.roll(g, 9, 1)], -1),
        "volume": np.stack([np.roll(_img(n // 4), k, 0) for k in range(10)], 0),
    }


@pytest.mark.skipif(not fsthreads.available(),
                    reason="threadpoolctl が無い環境では上限そのものが no-op")
def test_no_large_decomposition_runs_outside_the_cap(survey):
    """絞り忘れがないこと。新しい大きい分解を足すとここが落ちる。"""
    stray = {k: v for k, v in survey["unlimited"].items() if k not in ALLOWED}
    assert not stray, (
        "上限の外で大きい行列を分解している。短辺 >= %d の分解は "
        "fsthreads.for_decomposition(min(shape)) の中で呼ぶこと"
        "(理由と実測は fsthreads の docstring)。場所と回数: %s"
        % (fsthreads.MIN_N, dict(stray)))


@pytest.mark.skipif(not fsthreads.available(), reason="threadpoolctl が無い")
def test_the_allowlist_has_no_stale_entries(survey):
    """台帳の古さも見る。許可表には必ず両方向の検査を付ける。"""
    seen = set(survey["unlimited"])
    stale = sorted(set(ALLOWED) - seen)
    assert not stale, (
        "台帳に載っているのに一度も現れない場所がある(消えた/絞られた)。"
        "台帳から外すこと: %s" % stale)


@pytest.mark.skipif(not fsthreads.available(), reason="threadpoolctl が無い")
def test_the_survey_actually_saw_large_decompositions(survey):
    """**この門が何も見ていないのに緑になる**のを防ぐ。

    「発見ゼロ」は頑健さの証拠ではない —— 単に流れていないだけかもしれない。
    観測数が減ったらここが落ちて、経路が痩せたことに気づける。
    """
    total_big = sum(survey["limited"].values()) + sum(survey["unlimited"].values())
    assert total_big >= _MIN_OBSERVED_BIG, (
        "短辺 >= %d の分解を %d 件しか観測していない(下限 %d)。門が対象を"
        "見失っている可能性がある —— op が消えた / 探針が小さすぎる / "
        "レジストリが読めていない、を順に疑うこと。内訳: limited=%s"
        % (fsthreads.MIN_N, total_big, _MIN_OBSERVED_BIG, dict(survey["limited"])))


@pytest.mark.skipif(not fsthreads.available(), reason="threadpoolctl が無い")
def test_the_hot_path_is_the_one_that_is_capped(survey):
    """RPCA の ALM ループが上限の中に居ること(全体の 98% を占める場所)。

    ここが外れたら、他がどれだけ整っていても効果はほぼ消える。
    """
    inside = {k for k, v in survey["limited"].items() if v}
    assert any(k.startswith("backends_decomp.py:") for k in inside), (
        "backends_decomp の分解が上限の中で走っていない。"
        "観測できた場所: %s" % sorted(inside))


def test_small_decompositions_are_left_alone(survey):
    """小行列に段を掛けていないこと(掛けると 1.9 倍遅くなる)。"""
    assert sum(survey["small"].values()) > 0, "小さい分解が 1 件も流れていない"
    # 小行列は _where() を呼ばずに数だけ数えている。ここでは
    # 「小さい側が存在する」ことと、段が掛かっていないことを確かめる。
    assert fsthreads.cap_for(fsthreads.MIN_N - 1) is None
