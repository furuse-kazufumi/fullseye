"""`backends_typed` の出荷側台帳 3 つに**陳腐化の門**を立てる。

門の変異テスト(2026-09-05)で判明: `_OP_BRIDGE_SKIP` / `_OP_SORT_OVERRIDE` /
`OP_TUNABLE_OVERRIDE` は、**実在しない op 名を足しても何も落ちなかった**。
橋渡しループはカタログを走査して台帳を引くだけなので、台帳側の
タイポ・改名後の残骸は**どのカタログ項目にも一致せず、静かに無害化される**。
「見落とし方向(本物を消す)」は既存テストが拾うが、逆方向は誰も見ていなかった。

ここでは「台帳の鍵はすべて、いまカタログに居る op 名である」を要求する。
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest                                              # noqa: E402

bt = pytest.importorskip("backends_typed")


def _catalog_names() -> set[str]:
    cf = bt._catalog_entries()
    return {row[0] for row in cf.catalog()}


def test_bridge_skip_names_only_catalog_ops():
    live = _catalog_names()
    assert len(live) > 100, "カタログが小さすぎる(%d) —— 検査の前提が違う" % len(live)
    stale = sorted(set(bt._OP_BRIDGE_SKIP) - live)
    assert not stale, "_OP_BRIDGE_SKIP にカタログに居ない名前: %s" % stale


def test_sort_override_names_only_catalog_ops_and_valid_sorts():
    live = _catalog_names()
    stale = sorted(set(bt._OP_SORT_OVERRIDE) - live)
    assert not stale, "_OP_SORT_OVERRIDE にカタログに居ない名前: %s" % stale
    import op_probe
    known_sorts = set(op_probe.SORT_TO_GENERATOR) | set(getattr(op_probe, "LOCAL_SORTS", ()))
    bad = {k: v for k, v in bt._OP_SORT_OVERRIDE.items()
           if not (isinstance(v, tuple) and len(v) == 2 and all(s in known_sorts for s in v))}
    assert not bad, "_OP_SORT_OVERRIDE の sort が不正: %s" % bad


def test_tunable_override_names_only_catalog_ops_and_real_parameters():
    """鍵が実在するだけでなく、指定した**引数名がその op の signature に在る**こと。"""
    import inspect
    cf = bt._catalog_entries()
    fns = {row[0]: row[4] for row in cf.catalog()}
    stale = sorted(set(bt.OP_TUNABLE_OVERRIDE) - set(fns))
    assert not stale, "OP_TUNABLE_OVERRIDE にカタログに居ない名前: %s" % stale
    bad = {}
    for name, want in bt.OP_TUNABLE_OVERRIDE.items():
        params = set(inspect.signature(fns[name]).parameters)
        missing = [w for w in want if w not in params]
        if missing:
            bad[name] = missing
    assert not bad, "OP_TUNABLE_OVERRIDE が指す引数が signature に無い: %s" % bad


# --------------------------------------------------------------------------- #
# 登録探針のキャッシュ(2026-09-23)
#
# `import fullseye` の 861 ms のうち 316 ms が「56 本のレシピ op を実際に走らせて
# 動くものだけ登録する」探針だった。判定は (レシピ, バックエンドの版, Python,
# プラットフォーム) だけで決まるので、その指紋を鍵にして覚える。速くするために
# 検査をやめたのではなく、**答えが変わりうるときだけ回す**ようにした ——
# ここではそれが本当かを確かめる。
# --------------------------------------------------------------------------- #
def test_the_probe_cache_gives_the_same_registry_as_probing_for_real():
    """覚えた答えと、実際に探針を回した答えが**一致**すること。

    ここが割れると「速いが間違った登録簿」を配ることになる。cv2 5.0.0 で
    `BRISK_create` が移動したとき、あらゆる画像に 0.0 を返し続ける op を 2 本
    落としたのがこの探針なので、一致はキャッシュを持つための条件そのもの。
    """
    import backends_r3 as B
    import ops as O

    args = (O.Op, O.IMAGE, O.REGION, O.FEATURE, O.CONTOUR, O._norm, O._bin)

    old = os.environ.get("FULLSEYE_BACKEND_PROBE")
    try:
        os.environ["FULLSEYE_BACKEND_PROBE"] = "always"
        real = [o.name for o in B.build(*args)]
        assert B.build.probed is True, "always なのに探針を回していない"
    finally:
        if old is None:
            os.environ.pop("FULLSEYE_BACKEND_PROBE", None)
        else:
            os.environ["FULLSEYE_BACKEND_PROBE"] = old

    cached = [o.name for o in B.build(*args)]
    assert cached == real, (
        "キャッシュ経由の登録が実測と食い違う(覚えた答えが古い): "
        "only-cached=%s only-real=%s"
        % (sorted(set(cached) - set(real)), sorted(set(real) - set(cached))))


def test_the_probe_key_moves_when_a_backend_version_moves():
    """鍵に**バックエンドの版**が入っていること。

    版を無視した鍵だと、ライブラリを入れ替えても古い合否を使い続ける ——
    それは「検査をやめた」のと同じ。ここでは版を 1 つ差し替えて、鍵が動くかを見る。
    """
    import backends_r3 as B

    before = B._probe_key()
    import numpy as _np
    real = _np.__version__
    try:
        _np.__version__ = real + ".test"
        after = B._probe_key()
    finally:
        _np.__version__ = real
    assert after != before, "バックエンドの版を変えても鍵が動かない"
    assert B._probe_key() == before, "版を戻したら鍵も戻ること"


def test_the_probe_cache_is_not_a_repo_artifact():
    """キャッシュは**環境ごとの答え**なので repo に置かない(commit されない)。"""
    import backends_r3 as B

    p = os.path.abspath(B._probe_cache_path())
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    assert not p.startswith(root + os.sep), (
        "探針キャッシュが repo の中を指している(環境依存の生成物は配らない): %s" % p)
