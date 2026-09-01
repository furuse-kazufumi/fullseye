# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""連鎖ファザーの収束フェーズ(--minimize / --replay)の回帰。

拡散(ランダム連鎖)で見つけた発見は、そのままでは 6〜8 op の長い trace を
伴う。デバッグに使えるのは「その署名を出す最小の op 列」なので、収束側に
delta debugging を置いた(2026-09-01)。ここで固定する契約:

  1. 連鎖は **連鎖固有 seed** で回り、findings がその seed を持つ
     (共有 rng だと i 番目だけを後から再走できない = 最小化の前提が崩れる)。
  2. script を渡した run_chain は **その順で強制実行**する。
  3. 最小化は無関係な前段だけを落とし、署名は保存される。
  4. 再現しない発見(seed 欠落・非決定的)には **False を返す**
     — 「短縮できた」と嘘をつくと推測パッチを誘発するため。
"""
import numpy as np
import pytest

pytest.importorskip("torch")   # catalog は torch 依存モジュールを束ねる

from tools.chain_fuzz import (catalog, make_generators, minimize_finding,
                              reproduces, run_chain, signature)


@pytest.fixture(scope="module")
def env():
    return catalog(), make_generators()


def test_chain_seed_is_recorded_on_every_finding(env):
    """発見には必ず seed が載る(= 後から正確に再走できる)。"""
    ops, gens = env
    log = []
    for i in range(40):
        seed = 12_345 + i
        run_chain(ops, gens, np.random.default_rng(seed), 6, log, chain_seed=seed)
    assert log, "40 連鎖で 1 件も発見が無い = 探索が壊れている"
    assert all(f.get("seed") is not None for f in log)
    # seed を渡さない旧来の呼び方でも落ちない(None が載るだけ)
    log2 = []
    run_chain(ops, gens, np.random.default_rng(0), 3, log2)
    assert all("seed" in f for f in log2)


def test_script_forces_the_op_order(env):
    """script を渡すと候補ランダム抽選をせず、その op だけを実行する。"""
    ops, gens = env
    log = []
    trace = run_chain(ops, gens, np.random.default_rng(7), 0, log,
                      chain_seed=7, script=["vol_gaussian", "vol_gaussian"])
    # 成功すれば trace に、失敗すれば log に出る。いずれにせよ他の op は動かない
    assert set(trace) <= {"vol_gaussian"}
    assert all(f["op"] == "vol_gaussian" for f in log)
    # 存在しない op 名は黙って飛ばす(短縮の途中で壊れないこと)
    log3 = []
    run_chain(ops, gens, np.random.default_rng(7), 0, log3, chain_seed=7,
              script=["no_such_op_at_all"])
    assert log3 == []


def test_minimize_reduces_and_preserves_the_signature(env):
    """長い trace を持つ発見が 1 op まで縮み、署名が保存される。"""
    ops, gens = env
    log = []
    for i in range(60):
        seed = 3_000_000 + i
        run_chain(ops, gens, np.random.default_rng(seed), 6, log, chain_seed=seed)
    long_ones = [f for f in log if len(f.get("trace") or []) >= 2]
    assert long_ones, "2 op 以上の trace を持つ発見が無い = 前提が崩れている"
    reduced_any = False
    for f in long_ones[:5]:
        script, ok = minimize_finding(ops, gens, f, verbose=False)
        if not ok:
            continue                      # 非決定的な発見は honest に skip
        assert script[-1] == f["op"], "当該 op は末尾に残る"
        assert len(script) <= len(f["trace"])
        assert reproduces(ops, gens, script, f["seed"], signature(f))
        reduced_any = reduced_any or len(script) < len(f["trace"])
    assert reduced_any, "5 件試して 1 件も短縮できない = 削り込みが効いていない"


def test_arg_binding_rng_is_position_independent(env):
    """引数抽選は「連鎖 seed × op 名 × 出現回数」で決まり、**前段の op 数に
    依存しない**。これが崩れると、無関係な op を 1 つ落としただけで以降の
    抽選が全部ずれ、最小化が再現しなくなる(実測: 分離前 48/65 → 後 58/58)。"""
    ops, gens = env
    # 同じ op を、前に無害な op を挟む/挟まないの 2 通りで実行して比較
    a, b = [], []
    run_chain(ops, gens, np.random.default_rng(11), 0, a, chain_seed=11,
              script=["mat_eigh"])
    run_chain(ops, gens, np.random.default_rng(11), 0, b, chain_seed=11,
              script=["stat_zscore", "mat_eigh"])
    got_a = [signature(f) for f in a if f["op"] == "mat_eigh"]
    got_b = [signature(f) for f in b if f["op"] == "mat_eigh"]
    assert got_a == got_b, "前段の有無で mat_eigh の引数抽選が変わっている"


def test_minimize_is_honest_when_it_cannot_reproduce(env):
    """seed を持たない発見(旧形式 jsonl)は「再現せず」を返す。捏造しない。"""
    ops, gens = env
    stale = {"kind": "SUSPECT", "op": "vol_resize", "exc": "TypeError",
             "msg": "…", "trace": ["vol_resize"]}       # seed 無し
    script, ok = minimize_finding(ops, gens, stale, verbose=False)
    assert (script, ok) == (None, False)
    # trace が空の場合も同様
    assert minimize_finding(ops, gens, {"kind": "SUSPECT", "op": "x", "seed": 1,
                                        "trace": []}, verbose=False) == (None, False)


# --------------------------------------------------------------------------- #
# 拡散側の契約(2026-09-01 追加): 「発見ゼロ」を頑健さと取り違えないこと          #
# --------------------------------------------------------------------------- #
def test_signature_ignores_run_specific_numbers():
    """署名は**メッセージ中の数値を伏せて**比べる。

    良いエラーメッセージほど「負の bin が 127 個、最小 -1.176」のように
    その実行固有の数を含む。素の文字列で同一視すると、同じ 1 件の問題が
    実行のたびに別署名になり、収束(拡散 → 署名でまとめる)が機能しない。
    実測: photon 族を足した波で署名が 99 → 238 に膨れ、増分のほぼ全部が
    この形だった。
    """
    a = {"kind": "CONTRACT", "op": "dtof_depth", "exc": "ValueError",
         "msg": "dtof_depth: hist has 127 negative bin(s) (min -1.17595)"}
    b = dict(a, msg="dtof_depth: hist has 3 negative bin(s) (min -0.0042)")
    c = dict(a, msg="dtof_depth: hist must be 1-D, got shape (4, 4)")
    assert signature(a) == signature(b), "同じ 1 件が数値違いで別署名になっている"
    assert signature(a) != signature(c), "別の問題まで同じ署名に潰している"


def test_op_specific_hints_can_override_a_default_argument(env):
    """既定値つきの引数も **op 名で狙い撃ちすれば**上書きできること。

    既定値がプールの寸法と噛み合わない op は、上書きできないと毎回
    ValueError で弾かれ、**一度も実行されないまま「発見ゼロ」**に数えられる。
    実測: ``lf_from_mla`` の既定 ``angular=(5,5)`` は 32x32 を割り切れず、
    1200 連鎖で一度も走っていなかった(修正後 lightfield 族 16/17 -> 17/17)。
    """
    import inspect

    from tools.chain_fuzz import OP_PARAM_HINTS, _bind_args
    ops, _ = env
    fn = next(o[4] for o in ops if o[0] == "lf_from_mla")
    assert inspect.signature(fn).parameters["angular"].default == (5, 5), \
        "前提が変わった: この検査は既定値つき引数の上書きを見ている"
    assert ("lf_from_mla", "angular") in OP_PARAM_HINTS
    _args, kwargs = _bind_args("lf_from_mla", fn, [np.zeros((32, 32))],
                               np.random.default_rng(0))
    assert kwargs.get("angular") == (4, 4), "既定値が上書きされていない"


def test_every_declared_type_has_a_producer_or_a_seed(env):
    """**誰も産まない型を食う op** は永久に到達不能 = 「発見ゼロ」の偽装。

    型の到達可能性を不動点で解く。初期プール(生成器)の型から出発し、
    入力が全部揃う op の出力型を足していって、増えなくなるまで回す。
    実測(2026-09-01): 434 op 中 ``refine_peak_newton`` 1 件だけが
    ``score`` 型の生産者不在で blocked だった → 種を追加して解消。
    """
    ops, gens = env
    reach = set(gens) | {"any"}
    changed = True
    while changed:
        changed = False
        for _n, _f, ins, out, _fn in ops:
            if all(t in reach for t in ins) and out not in reach:
                reach.add(out)
                changed = True
    blocked = [(n, tuple(ins)) for n, _f, ins, _o, _fn in ops
               if not all(t in reach for t in ins)]
    assert not blocked, (
        "この op は入力型を誰も産まないので永久に実行されない: %s" % blocked)


def test_targeted_diffusion_reaches_more_ops_than_uniform(env):
    """連鎖ごとに目標 op を決める拡散は、一様抽選より多くの op に触ること。

    候補が数百ある中で特定の op が長さ 6 の枠に入る確率は低く、一様だと
    「構造的には到達可能なのに一度も引かれない」op が大量に残る。
    先に試した「まだプールに無い型を産む op を優先」する型空間バイアスは
    **効かなかった**(1500 連鎖で 321 -> 322 op)ので、目標 op へ寄せる方式に
    した。ここでは小さな走行で向きだけを固定する(絶対値は走行条件で動く)。
    """
    ops, gens = env
    def _reach(explore):
        seen = set()
        for i in range(60):
            cs = 991 * 1_000_003 + i
            seen.update(run_chain(ops, gens, np.random.default_rng(cs), 5, [],
                                  chain_seed=cs, explore=explore))
        return seen
    uniform, targeted = _reach(0.0), _reach(0.9)
    assert len(targeted) > len(uniform), (
        "狙いを持った拡散が一様抽選を上回っていない: %d vs %d"
        % (len(targeted), len(uniform)))
