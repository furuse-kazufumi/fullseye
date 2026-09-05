# -*- coding: utf-8 -*-
"""BLAS スレッド上限層の検査。

守りたいのは 4 つ:

1. **段数表が実測どおりに引ける** —— 境界の上下で違う値が出る。表を書き換えたら
   ここが落ちる(``fsthreads`` の docstring にある 92 升の計測が根拠)。
2. **本当に効く** —— 文脈の中で BLAS のスレッド数が実際に減っていること。
   宣言だけの設定は嘘なので、``threadpoolctl`` に現在値を訊いて確かめる。
3. **必ず戻る** —— 例外で抜けても、入れ子でも、元のスレッド数に復帰する。
   ここが漏れると、ライブラリが利用者のプロセスを黙って 1 スレッドに落とす。
4. **無い環境で静かに何もしない** —— ``threadpoolctl`` が入っていなくても
   結果は同じで、例外も出ない。

★2026-09-06 の実測メモ: 「絞ると結果が変わるか」は **変わる**(下位ビット)。
1t と 24t で ``svd(64x64)`` は bitwise 一致しない(最大差 3.6e-16)。だから
ここでは bitwise 一致を要求せず、``allclose`` で見る。**ただしそれは今も同じ**
—— スレッド数は論理 CPU 数から決まるので、上限を固定しないほうが機械ごとに
違う値を出している。
"""
from __future__ import annotations

import concurrent.futures
import os

import numpy as np
import pytest

import fsthreads as T


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """環境変数を既定へ。通し数も 0 に戻す。"""
    monkeypatch.delenv(T.ENV, raising=False)
    T.reset_counters()
    yield
    T.reset_counters()


# =========================================================================
# 1. 段数表
# =========================================================================

def test_the_tier_table_is_well_formed():
    """最後の行は「それ以上すべて」でなければならない。

    ここが崩れると :func:`cap_for` が表を抜けて ``AssertionError`` になる ——
    段を足すときにいちばん踏みやすい形なので、表そのものを検査する。
    """
    assert T.TIERS, "段数表が空"
    assert T.TIERS[-1][0] is None, "最後の行は (None, 上限) でなければならない"
    limits = [lim for lim, _ in T.TIERS[:-1]]
    assert all(isinstance(x, int) and x > 0 for x in limits)
    assert limits == sorted(limits), "閾値が昇順でない(順序を間違えると静かに違う段を選ぶ)"
    caps = [cap for _, cap in T.TIERS]
    assert caps == sorted(caps), "上限が昇順でない(大きい行列ほど許すはず)"
    assert T.MIN_N < T.TIERS[0][0], "MIN_N が最初の段より大きいと最初の段が死ぬ"


@pytest.mark.parametrize("n,expect", [
    (0, None), (1, None), (3, None), (31, None),        # 小さすぎて触らない
    (32, 1), (48, 1), (64, 1), (511, 1),                # 1 スレッド段
    (512, 4), (1023, 4),                                 # 4 スレッド段
    (1024, 8), (4096, 8), (100000, 8),                   # 8 スレッド段
])
def test_cap_for_follows_the_measured_tiers(n, expect):
    assert T.cap_for(n) == expect


def test_the_boundaries_are_exclusive_on_the_low_side():
    """``<512`` は 511 を含み 512 を含まない。境界の取り違えは静かに効く。"""
    assert T.cap_for(T.MIN_N - 1) is None and T.cap_for(T.MIN_N) == 1
    first = T.TIERS[0][0]
    assert T.cap_for(first - 1) != T.cap_for(first)


# =========================================================================
# 2. 短辺で選ぶ(長辺ではない)
# =========================================================================

@pytest.mark.parametrize("shape,expect", [
    ((3,), 0),                       # 1 次元は対象外
    ((7,), 0),
    ((64, 64), 64),
    ((16384, 3), 3),                 # ★縦長: 長辺で選ぶと 8 スレッドを許してしまう
    ((3, 16384), 3),
    ((100, 4096, 5), 5),             # 束ねた分解は最後の 2 軸だけ見る
])
def test_short_side_is_the_short_side(shape, expect):
    assert T.short_side(np.zeros(shape)) == expect


def test_a_tall_thin_matrix_is_not_treated_as_a_big_one():
    """``16384x3`` は「大きい行列」ではなく幅 3 の QR。

    長辺で段を選ぶと 8 スレッドを許し、実測で ``(16384,10)`` は 1.6 倍遅くなる。
    """
    assert T.cap_for(T.short_side(np.zeros((16384, 3)))) is None


def test_short_side_tolerates_things_without_a_shape():
    assert T.short_side(None) == 0
    assert T.short_side([[1, 2], [3, 4]]) == 0        # list には shape が無い


# =========================================================================
# 3. 環境変数
# =========================================================================

def test_the_default_is_auto():
    assert T.policy() == ("auto", None)


def test_off_leaves_the_threads_alone(monkeypatch):
    monkeypatch.setenv(T.ENV, "off")
    assert T.policy() == ("off", None)
    assert T.cap_for(64) is None
    assert T.cap_for(100000) is None


def test_a_fixed_number_overrides_the_tiers(monkeypatch):
    monkeypatch.setenv(T.ENV, "2")
    assert T.policy() == ("fixed", 2)
    assert T.cap_for(64) == 2
    assert T.cap_for(100000) == 2
    assert T.cap_for(T.MIN_N - 1) is None, "固定値でも小行列には触らない"


@pytest.mark.parametrize("raw", ["yes", "1.5", "many", "-", "auto2"])
def test_a_typo_fails_closed_instead_of_looking_like_it_took_effect(monkeypatch, raw):
    monkeypatch.setenv(T.ENV, raw)
    with pytest.raises(ValueError, match="is not understood"):
        T.policy()


def test_zero_and_negative_are_refused_with_a_pointer_to_off(monkeypatch):
    for raw in ("-1", "-8"):
        monkeypatch.setenv(T.ENV, raw)
        with pytest.raises(ValueError, match="use 'off'"):
            T.policy()


def test_the_env_var_is_read_again_when_it_changes(monkeypatch):
    """解釈は憶えるが、**生の文字列がキー**なので変更は次の呼び出しから効く。"""
    monkeypatch.setenv(T.ENV, "off")
    assert T.cap_for(64) is None
    monkeypatch.setenv(T.ENV, "auto")
    assert T.cap_for(64) == 1


def test_case_and_whitespace_do_not_change_the_meaning(monkeypatch):
    monkeypatch.setenv(T.ENV, "  OFF  ")
    assert T.policy() == ("off", None)


# =========================================================================
# 4. 文脈が**実際に**効く / 必ず戻る
# =========================================================================

needs_ctl = pytest.mark.skipif(
    not T.available(), reason="threadpoolctl が無い(この層は何もしない)")


def test_it_says_plainly_whether_it_can_do_anything():
    assert isinstance(T.available(), bool)
    if T.available():
        assert isinstance(T.current_threads(), int)
    else:
        assert T.current_threads() is None


@needs_ctl
def test_the_context_actually_lowers_the_thread_count():
    """宣言ではなく**現在値**で確かめる。効かない設定は嘘なので。"""
    outside = T.current_threads()
    with T.for_decomposition(64) as applied:
        assert applied is True
        assert T.current_threads() == 1
        assert T.limited() is True
    assert T.current_threads() == outside
    assert T.limited() is False


@needs_ctl
def test_a_small_matrix_is_not_touched_at_all():
    outside = T.current_threads()
    with T.for_decomposition(3) as applied:
        assert applied is False
        assert T.current_threads() == outside
        assert T.limited() is False, "触っていないのに『絞った』と数えてはいけない"


@needs_ctl
def test_it_restores_even_when_the_body_raises():
    outside = T.current_threads()
    with pytest.raises(RuntimeError):
        with T.for_decomposition(64):
            raise RuntimeError("boom")
    assert T.current_threads() == outside
    assert T.limited() is False


@needs_ctl
def test_nesting_unwinds_in_order():
    outside = T.current_threads()
    with T.for_decomposition(2048):                    # 8 スレッド段
        outer = T.current_threads()
        with T.for_decomposition(64):                  # 1 スレッド段
            assert T.current_threads() == 1
        assert T.current_threads() == outer
    assert T.current_threads() == outside


@needs_ctl
def test_blas_threads_takes_the_number_it_is_given():
    """利用者向けの入口は段数表を通さない —— 渡した数がそのまま入る。"""
    with T.blas_threads(2):
        assert T.current_threads() == 2


def test_blas_threads_refuses_zero():
    with pytest.raises(ValueError, match="needs n >= 1"):
        with T.blas_threads(0):
            pass


@needs_ctl
def test_off_really_leaves_the_process_alone(monkeypatch):
    monkeypatch.setenv(T.ENV, "off")
    outside = T.current_threads()
    with T.for_decomposition(64) as applied:
        assert applied is False
        assert T.current_threads() == outside


# =========================================================================
# 5. 無い環境で静かに何もしない
# =========================================================================

def test_without_threadpoolctl_the_layer_is_a_no_op(monkeypatch):
    """依存が無くても**例外を出さず、結果も変えない**。

    ``threadpoolctl`` は本体依存だが、剥がした環境でも動く設計を保つ
    (剥がされているのに気づかず落ちる、が最悪なので)。
    """
    monkeypatch.setattr(T, "_CONTROLLER", None)
    monkeypatch.setattr(T, "_TRIED", True)
    assert T.available() is False
    assert T.current_threads() is None
    with T.for_decomposition(1024) as applied:
        assert applied is False
        assert T.limited() is False
    a = np.random.default_rng(0).standard_normal((64, 64))
    assert np.allclose(T.svd(a, full_matrices=False)[1],
                       np.linalg.svd(a, full_matrices=False)[1])


def test_the_counters_separate_did_and_did_not(monkeypatch):
    T.reset_counters()
    with T.for_decomposition(3):
        pass
    with T.for_decomposition(1024):
        pass
    c = T.counters()
    assert c["skipped"] >= 1
    if T.available():
        assert c["limited"] == 1
    else:
        assert c["limited"] == 0


# =========================================================================
# 6. 包みが numpy と同じ答えを返す
# =========================================================================

_RNG = np.random.default_rng(20260906)
_A = _RNG.standard_normal((80, 60))
_SQ = _A[:60] @ _A[:60].T + 60 * np.eye(60)
_Y = _RNG.standard_normal(80)


def test_svd_matches_numpy():
    u, s, vt = T.svd(_A, full_matrices=False)
    U, S, VT = np.linalg.svd(_A, full_matrices=False)
    assert np.allclose(s, S, rtol=0, atol=1e-10)
    assert np.allclose(np.abs(u), np.abs(U), atol=1e-8)     # 符号は任意
    assert np.allclose(np.abs(vt), np.abs(VT), atol=1e-8)


def test_svd_values_only_matches_numpy():
    assert np.allclose(T.svd(_A, compute_uv=False), np.linalg.svd(_A, compute_uv=False))


def test_eigh_and_eigvalsh_match_numpy():
    w, _ = T.eigh(_SQ)
    assert np.allclose(w, np.linalg.eigh(_SQ)[0], atol=1e-9)
    assert np.allclose(T.eigvalsh(_SQ), np.linalg.eigvalsh(_SQ), atol=1e-9)


def test_qr_matches_numpy():
    q, r = T.qr(_A)
    assert np.allclose(q @ r, _A, atol=1e-10)
    assert q.shape == np.linalg.qr(_A)[0].shape


def test_pinv_matches_numpy():
    assert np.allclose(T.pinv(_A), np.linalg.pinv(_A), atol=1e-10)
    assert np.allclose(T.pinv(_A, rcond=1e-12), np.linalg.pinv(_A, rcond=1e-12), atol=1e-10)


def test_lstsq_matches_numpy():
    got = T.lstsq(_A, _Y)[0]
    assert np.allclose(got, np.linalg.lstsq(_A, _Y, rcond=None)[0], atol=1e-9)


@needs_ctl
def test_the_wrappers_engage_the_limit_for_a_big_matrix():
    """包みが**自分で短辺を測って**段を掛けていること。"""
    big = _RNG.standard_normal((600, 600))          # 短辺 600 -> 4 スレッド段
    T.reset_counters()
    T.svd(big, full_matrices=False)
    assert T.counters()["limited"] == 1, "大きい行列なのに段が掛かっていない"

    T.reset_counters()
    T.svd(_RNG.standard_normal((8, 8)))
    assert T.counters()["limited"] == 0, "小行列に段を掛けている(丸損)"


# =========================================================================
# 7. 並行実行 —— **contextvars では逃げられない**ことを明示的に固定する
# =========================================================================

@needs_ctl
def test_the_depth_flag_is_per_thread_even_though_the_cap_is_not():
    """上限そのものはプロセス共有。**計数だけ**はスレッドごとに独立させている。

    ここを共有にすると、門(絞り忘れの検出)が別スレッドの文脈を見て
    「絞ってある」と誤判定する。上限を per-thread にできないのは
    BLAS 側の制約で、それは :mod:`fsthreads` の docstring に書いてある。
    """
    def worker():
        return T.limited()

    with T.for_decomposition(1024):
        assert T.limited() is True
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            assert ex.submit(worker).result() is False


def test_the_module_documents_that_it_cannot_be_thread_local():
    """弱点を docstring から消したらここが落ちる(消したくなる種類の記述なので)。"""
    doc = T.__doc__ or ""
    assert "スレッドごとに独立にできない" in doc
    assert "FULLSEYE_BLAS_THREADS" in doc


def test_the_module_records_why_it_is_not_a_system_parameter():
    """``set_system`` に載せられない理由を、表ではなく本文で持っておく。"""
    doc = T.__doc__ or ""
    assert "set_system" in doc and "下位ビット" in doc

    import fssystem
    assert "blas_threads" not in fssystem.SYSTEM_PARAMS, (
        "スレッド数が fssystem の表に入っている —— あの表は『厳しくする方向のみ』か"
        "『数値に影響しない』専用で、スレッド数は下位ビットを動かす")


def test_the_environment_is_clean_after_the_module_is_used():
    """この層は**自分の文脈の外**でスレッド数を変えない。"""
    before = T.current_threads()
    with T.for_decomposition(1024):
        pass
    assert T.current_threads() == before
    assert os.environ.get(T.ENV) is None
