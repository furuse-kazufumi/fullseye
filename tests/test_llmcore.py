# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""llmcore —— LLM に至る系譜の芯。**恒等式が立つものだけ**入れてあるので、門も恒等式で書く。

★この族の主張は「Transformer を実装した」ではなく「**速くする工夫は近似ではなく
恒等式の括り直し**」なので、テストは「動く」ではなく「**一括と一致する**」を見る。
真値が浮動小数の線形代数なら機械精度の許容差、整数なら**許容差なしの一致**。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import llmcore as L  # noqa: E402

_OPS = ("rms_norm", "rope_rotate", "attention_scores", "attention_weights",
        "attention_apply", "attention_softmax", "attention_tiled",
        "attention_linear", "attention_grouped", "kv_cache_decode")

#: 一様乱数にしない —— 構造が無いと注意の重みが全行ほぼ一様になり、
#: 「押しても何も起きない」試験データになる(この repo の規律)。
def _tokens(t=48, d=16, seed=0):
    y, x = np.mgrid[0:t, 0:d].astype(float)
    return (0.5 + 0.4 * np.sin(x / 3.0 + y / 5.0)
            + 0.05 * np.random.default_rng(seed).standard_normal((t, d)))


def _rel(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b)))
                 / max(float(np.max(np.abs(np.asarray(b)))), 1e-300))


# --------------------------------------------------------------------------- #
# 1. softmax と マスク                                                          #
# --------------------------------------------------------------------------- #
def test_rows_sum_to_one_and_masked_entries_are_exactly_zero():
    q, k = _tokens(seed=1), _tokens(seed=2)
    w = L.attention_weights(L.attention_scores(q, k))
    assert np.max(np.abs(w.sum(1) - 1.0)) < 1e-12
    wc = L.attention_weights(L.attention_scores(q, k), "causal")
    cm = np.tril(np.ones(wc.shape, bool))
    #: ★許容差を入れない。-inf の exp は厳密に 0 になる。
    assert np.max(np.abs(wc[~cm])) == 0.0
    assert np.max(np.abs(wc.sum(1) - 1.0)) < 1e-12


def test_sparsity_is_an_integer_invariant():
    """★閉形式が整数なので、浮動小数の許容差が要らない主張になる。"""
    q, k = _tokens(seed=1), _tokens(seed=2)
    s = L.attention_scores(q, k)
    t = s.shape[0]
    assert int((L.attention_weights(s, "causal") > 0).sum()) == t * (t + 1) // 2
    for wnd in (1, 3, 9, 17, t, t + 5):
        got = int((L.attention_weights(s, "window", window=wnd) > 0).sum())
        assert got == sum(min(i + 1, wnd) for i in range(t)), wnd


def test_subtracting_the_max_is_not_decoration():
    """最大値を引かないと exp が倍精度の上限を越えて壊れる —— 引けば壊れない。"""
    q, k = _tokens(seed=1) * 14.0, _tokens(seed=2) * 14.0
    s = L.attention_scores(q, k, scale=1.0)
    assert float(np.max(s)) > 709.0, "この試験が意味を持つには exp が溢れる必要がある"
    with np.errstate(over="ignore", invalid="ignore"):
        naive = np.exp(s) / np.exp(s).sum(1, keepdims=True)
    assert (~np.isfinite(naive)).any(), "素の exp が壊れていないので比較にならない"
    w = L.attention_weights(s)
    assert np.isfinite(w).all()
    assert np.max(np.abs(w.sum(1) - 1.0)) < 1e-12


# --------------------------------------------------------------------------- #
# 2. 速くする工夫 = 恒等式の括り直し                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tile", [1, 2, 3, 7, 16, 48, 64])
def test_tiling_with_online_softmax_is_exact_not_approximate(tile):
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    full = L.attention_softmax(q, k, v)
    assert _rel(L.attention_tiled(q, k, v, tile=tile), full) < 1e-13


@pytest.mark.parametrize("mask,window", [(None, None), ("causal", None), ("window", 5)])
def test_tiling_is_exact_under_every_mask(mask, window):
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    full = L.attention_softmax(q, k, v, mask, window)
    assert _rel(L.attention_tiled(q, k, v, 7, mask, window), full) < 1e-13


def test_linear_attention_is_associativity():
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    assert _rel(L.attention_linear(q, k, v), (q @ k.T) @ v) < 1e-12
    t = q.shape[0]
    ref = (np.tril(np.ones((t, t))) * (q @ k.T)) @ v
    assert _rel(L.attention_linear(q, k, v, causal=True), ref) < 1e-12


def test_the_three_stage_path_equals_the_one_shot_path():
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    w = L.attention_weights(L.attention_scores(q, k))
    assert _rel(L.attention_apply(w, v), L.attention_softmax(q, k, v)) == 0.0


# --------------------------------------------------------------------------- #
# 3. 因果性と KV Cache                                                          #
# --------------------------------------------------------------------------- #
def test_rewriting_the_future_does_not_move_a_single_bit_of_the_past():
    """★同義反復ではない —— 実際に未来を別の乱数に差し替えて測っている。"""
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    t = q.shape[0]
    cut = t // 2
    k2, v2 = k.copy(), v.copy()
    rng = np.random.default_rng(99)
    k2[cut:] = rng.standard_normal((t - cut, k.shape[1]))
    v2[cut:] = rng.standard_normal((t - cut, v.shape[1]))
    a = L.attention_softmax(q, k, v, "causal")
    b = L.attention_softmax(q, k2, v2, "causal")
    assert np.max(np.abs(a[:cut] - b[:cut])) == 0.0, "未来が過去に漏れている"
    assert np.max(np.abs(a[cut:] - b[cut:])) > 1e-3, "後半が動かないなら試験が効いていない"


def test_kv_cache_decoding_matches_the_batch_forward():
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    full = L.attention_softmax(q, k, v, "causal")
    step = np.vstack([L.kv_cache_decode(q[i:i + 1], k[:i + 1], v[:i + 1])
                      for i in range(q.shape[0])])
    assert _rel(step, full) < 1e-13


# --------------------------------------------------------------------------- #
# 4. 位置符号と正規化                                                            #
# --------------------------------------------------------------------------- #
def test_rope_is_a_rotation_so_it_preserves_the_norm():
    q = _tokens(seed=1)
    before = np.linalg.norm(q, axis=1)
    after = np.linalg.norm(L.rope_rotate(q), axis=1)
    assert np.max(np.abs(after - before)) < 1e-12


def test_rope_inner_product_depends_only_on_the_relative_position():
    q, k = _tokens(seed=1), _tokens(seed=2)
    vals = [float(L.rope_rotate(q[0][None, :], positions=[7 + s])[0]
                  @ L.rope_rotate(k[0][None, :], positions=[s])[0]) for s in range(40)]
    assert max(vals) - min(vals) < 1e-12
    #: 差を変えれば値は変わる(変わらないなら上の不変性は自明になってしまう)
    other = float(L.rope_rotate(q[0][None, :], positions=[11])[0]
                  @ L.rope_rotate(k[0][None, :], positions=[0])[0])
    assert abs(other - vals[0]) > 1e-6


def test_attention_is_permutation_equivariant_until_a_position_code_is_added():
    """★位置符号が「何をしているか」を、壊れ方で示す。"""
    q, k, v = _tokens(seed=1), _tokens(seed=2), _tokens(seed=3)
    t = q.shape[0]
    perm = np.random.default_rng(4).permutation(t)
    inv = np.argsort(perm)
    plain = L.attention_softmax(q, k, v)
    shuffled = L.attention_softmax(q[perm], k[perm], v[perm])
    assert np.max(np.abs(shuffled[inv] - plain)) < 1e-12
    r = L.attention_softmax(L.rope_rotate(q), L.rope_rotate(k), v)
    rp = L.attention_softmax(L.rope_rotate(q[perm]), L.rope_rotate(k[perm]), v[perm])
    assert np.max(np.abs(rp[inv] - r)) > 1e-3, "RoPE を入れても順序が効かないなら位置符号が働いていない"


def test_rms_norm_output_has_rms_exactly_one_and_eps_costs_that():
    q = _tokens(seed=1)
    y = L.rms_norm(q)
    assert np.max(np.abs(np.sqrt(np.mean(y * y, axis=1)) - 1.0)) < 1e-12
    y2 = L.rms_norm(q, eps=1e-3)
    off = np.max(np.abs(np.sqrt(np.mean(y2 * y2, axis=1)) - 1.0))
    assert off > 1e-6, "eps を入れても 1 のままなら eps が効いていない"
    w = np.linspace(0.5, 2.0, q.shape[1])
    assert np.allclose(L.rms_norm(q, weight=w), y * w)


# --------------------------------------------------------------------------- #
# 5. GQA の両端                                                                 #
# --------------------------------------------------------------------------- #
def test_grouped_attention_collapses_exactly_onto_mha_and_mqa():
    t, nh, dh = 48, 4, 4
    q = _tokens(t, nh * dh, seed=1)
    k = _tokens(t, nh * dh, seed=2)
    v = _tokens(t, nh * dh, seed=3)
    mha = np.concatenate([L.attention_softmax(q[:, h * dh:(h + 1) * dh],
                                              k[:, h * dh:(h + 1) * dh],
                                              v[:, h * dh:(h + 1) * dh])
                          for h in range(nh)], axis=1)
    assert np.max(np.abs(L.attention_grouped(q, k, v, nh, nh) - mha)) == 0.0
    mqa = np.concatenate([L.attention_softmax(q[:, h * dh:(h + 1) * dh],
                                              k[:, :dh], v[:, :dh]) for h in range(nh)], axis=1)
    assert np.max(np.abs(L.attention_grouped(q, k[:, :dh], v[:, :dh], nh, 1) - mqa)) == 0.0
    mid = L.attention_grouped(q, k[:, :2 * dh], v[:, :2 * dh], nh, 2)
    assert np.max(np.abs(mid - mqa)) > 1e-3, "中間が MQA と同じなら群が効いていない"


# --------------------------------------------------------------------------- #
# 6. fail-closed —— どの入口も op 名を名乗る                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op,call", [
    ("rms_norm", lambda: L.rms_norm(np.zeros((3, 4)))),
    ("rms_norm", lambda: L.rms_norm(np.ones((3, 4)), eps=-1.0)),
    ("rms_norm", lambda: L.rms_norm(np.ones((3, 4)), weight=np.ones(5))),
    ("rope_rotate", lambda: L.rope_rotate(np.ones((4, 5)))),
    ("rope_rotate", lambda: L.rope_rotate(np.ones((4, 4)), positions=[1, 2])),
    ("attention_scores", lambda: L.attention_scores(np.ones((4, 4)), np.ones((4, 6)))),
    ("attention_weights", lambda: L.attention_weights(np.ones((3, 3)), "bogus")),
    ("attention_weights", lambda: L.attention_weights(np.ones((3, 4)))),
    ("attention_apply", lambda: L.attention_apply(np.ones((3, 3)), np.ones((3, 2)))),
    ("attention_apply", lambda: L.attention_apply(-np.eye(3), np.ones((3, 2)))),
    ("attention_softmax", lambda: L.attention_softmax(np.ones((4, 4)), np.ones((4, 4)),
                                                      np.ones((3, 4)))),
    ("attention_tiled", lambda: L.attention_tiled(np.ones((4, 4)), np.ones((4, 4)),
                                                  np.ones((4, 4)), tile=0)),
    ("attention_linear", lambda: L.attention_linear(np.ones((4, 4)), np.ones((3, 4)),
                                                    np.ones((3, 4)), causal=True)),
    ("attention_grouped", lambda: L.attention_grouped(np.ones((4, 8)), np.ones((4, 8)),
                                                      np.ones((4, 8)), 3, 2)),
    ("kv_cache_decode", lambda: L.kv_cache_decode(np.ones((4, 4)), np.ones((4, 4)),
                                                  np.ones((4, 4)))),
])
def test_every_refusal_names_the_op(op, call):
    """★2026-09-24 の外部報告 N213/N214: 同じ族で名乗る op と名乗らない op が混ざっていた。
    新しい族では**全部名乗る**ことを門で固定する。"""
    with pytest.raises(ValueError) as e:
        call()
    assert str(e.value).startswith(op + ":"), str(e.value)


def test_nan_never_slips_through_the_entry():
    bad = np.ones((4, 4))
    bad[1, 1] = np.nan
    with pytest.raises(ValueError):
        L.attention_softmax(bad, np.ones((4, 4)), np.ones((4, 4)))


def test_too_long_a_sequence_is_refused_rather_than_allocating_t_squared():
    tall = np.zeros((L.MAX_TOKENS + 1, 2))
    with pytest.raises(ValueError) as e:
        L.rms_norm(tall)
    assert "MAX_TOKENS" in str(e.value)


# --------------------------------------------------------------------------- #
# 7. 台帳と公開経路                                                             #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsllmcore

    assert opsllmcore.missing() == []
    assert set(opsllmcore.OPSLLMCORE) == set(_OPS)
    assert set(L.__all__) - {"MAX_TOKENS", "MASK_KINDS", "ROPE_BASE"} == set(_OPS)
    assert len(opsllmcore.OPSLLMCORE) == 10 and len(opsllmcore.categories()) == 4


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsllmcore

    for name in opsllmcore.OPSLLMCORE:
        assert hasattr(fs.ledger, name), name


def test_every_parameter_is_documented():
    """★2026-09-24 の実測: 台帳 op の引数の 83 % に説明が無かった(4,486 / 5,407)。
    `param_spec` は UI と MCP の説明面なので、**新しい族は 100 %** から始める。"""
    import opassist

    gaps = [(n, p["name"]) for n in _OPS for p in opassist.param_spec(n) if not p.get("doc")]
    assert gaps == [], "説明の無い引数: %s" % gaps


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "llmcore"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"tokens", "attnmap"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsllmcore

    gens = cf.make_generators()
    for name, meta in opsllmcore.OPSLLMCORE.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            assert s in cf.TYPE_CHECKS and s in gens, (name, s)
    rng = np.random.default_rng(0)
    tok = gens["tokens"](rng)
    assert cf.TYPE_CHECKS["tokens"](tok)
    assert cf.TYPE_CHECKS["attnmap"](gens["attnmap"](rng))
    assert cf.TYPE_CHECKS["tokens"](L.rms_norm(tok))
    assert cf.TYPE_CHECKS["attnmap"](L.attention_scores(tok, tok))


def test_the_seed_has_structure_not_uniform_noise():
    """★一様乱数の種だと注意がどの行もほぼ一様になり、押しても何も起きない。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf

    tok = cf.make_generators()["tokens"](np.random.default_rng(0))
    w = L.attention_weights(L.attention_scores(tok, tok))
    spread = float(w.max() - w.min())
    assert spread > 2.0 / w.shape[1], "注意の重みがほぼ一様 —— 種に構造が無い(%g)" % spread


def test_sample_input_runs_every_op():
    """押せば動くこと(`opassist.sample_input` の種でそのまま走る)。"""
    import opassist

    for name in _OPS:
        args, kwargs = opassist.sample_input(name)
        assert all(a is not None for a in args), name
        out = opassist.call(name, *args, **kwargs) if hasattr(opassist, "call") else None
        del out


def test_no_bridge_was_built_into_the_two_d_registry():
    """★`tokens` / `attnmap` は TYPE_TO_SORT に入れていない —— 橋が架かると
    注意の入力として意味の無い 1 枚の画像が渡され「走ったが全面が同じ値」になる。"""
    import fullseye as fs

    names = {r["name"] for r in fs.list_ops()}
    assert not [n for n in names if n.startswith("tb_") and n[3:] in set(_OPS)]


def test_the_family_guide_exists_and_names_its_own_ops():
    guide = ROOT / "docs" / "ops" / "llmcore" / "guides" / "llmcore.md"
    assert guide.is_file(), guide
    text = guide.read_text(encoding="utf-8")
    named = [n for n in _OPS if n in text]
    assert len(named) >= 3, named
    assert "torch" in text, "torch を使わない理由がガイドに無い"


def test_the_poc_ships_with_the_family():
    poc = ROOT / "examples" / "poc_attention_identities.py"
    assert poc.is_file(), poc
    src = poc.read_text(encoding="utf-8")
    assert "%(" not in src.split('"""')[1], "説明文にテンプレートの差し込みが残っている"
    assert "import torch" not in src
