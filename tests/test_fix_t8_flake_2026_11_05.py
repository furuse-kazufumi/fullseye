"""1.0 前の修正 2026-11-05(t8-flake): T8 と T6 の順序依存。

T8 — threadpoolctl 3.8 の「制御スレッド」で BLAS の上限が黙って外れた。

CI(shard 5/6)で ``test_t8_blas_cap_is_restored_after_contexts_interleave_across_threads`` が
``{'A_inside_with_B': 4, 'B_after_A_left': 4}`` で落ちた。偶発ではない —— 同じ日に出た
threadpoolctl 3.8.0 から、pthreads / Windows 版 OpenBLAS の上限は**最初に設定したスレッド**
(制御スレッド)からしか変えられず、他のスレッドの設定は黙って捨てられる。``fsthreads`` は
limiter を文脈の外で持つので制御が解放されず:

* 主スレッドで一度でも使った後は、別スレッドの文脈が全部素通し(上限 2 が掛からず 4 のまま =
  CI の値。24 論理 CPU の手元では 24)。しかも ``as`` は ``True`` と答えた。
* 生きている worker が先に制御を握ると、**全部抜けた後もプロセスが 1 スレッドに固まった**(24 -> 1)。
* 利用者自身の ``with threadpool_limits(...)`` も、別スレッドからは効かなくなった。

ここの主張はどれも threadpoolctl の版によらない不変量(3.6 / 3.7 では元から成り立つ)。
3.8 で修正前の ``fsthreads`` に当てると落ちる。
"""
import concurrent.futures
import threading

import pytest

import fsthreads as T

_needs_ctl = pytest.mark.skipif(not T.available(), reason="threadpoolctl is not installed")


@pytest.fixture
def start():
    assert T._ACTIVE == [] and T._HELD["limiter"] is None, "前のテストが上限の台帳を残している"
    n = T.current_threads()
    if n is None or n < 4:
        pytest.skip(f"needs a BLAS with >= 4 threads to tell the caps apart (has {n})")
    yield n
    assert T._ACTIVE == [] and T._HELD["limiter"] is None
    assert T.current_threads() == n


def _in_thread(fn):
    out = {}

    def run():
        out["v"] = fn()
    t = threading.Thread(target=run)
    t.start()
    t.join(20)
    assert not t.is_alive()
    return out["v"]


@_needs_ctl
def test_a_context_in_another_thread_works_after_the_main_thread_used_the_layer(start):
    """CI の条件: 主スレッドが先に上限を掛けた(= 3.8 で制御スレッドになった)後の別スレッド。"""
    with T.blas_threads(1) as ok:
        assert ok is True and T.current_threads() == 1
    assert T.current_threads() == start

    def worker():
        with T.blas_threads(2) as ok:
            return ok, T.current_threads()
    assert _in_thread(worker) == (True, 2)
    assert T.current_threads() == start


@_needs_ctl
def test_the_t8_interleave_holds_after_the_main_thread_used_the_layer(start):
    """T8 と同じ A/B の入れ子を、主スレッドが先に使った状態で 3 回。"""
    with T.for_decomposition(64):
        pass
    a_in, b_in, a_out = threading.Event(), threading.Event(), threading.Event()
    seen = {}

    def A():
        with T.blas_threads(1):
            a_in.set()
            assert b_in.wait(10)
            seen["A_inside_with_B"] = T.current_threads()
        a_out.set()

    def B():
        assert a_in.wait(10)
        with T.blas_threads(2):
            b_in.set()
            assert a_out.wait(10)
            seen["B_after_A_left"] = T.current_threads()

    reps = 0
    for _rep in range(3):
        seen.clear()
        a_in.clear(); b_in.clear(); a_out.clear()
        ta, tb = threading.Thread(target=A), threading.Thread(target=B)
        ta.start(); tb.start(); ta.join(20); tb.join(20)
        assert not ta.is_alive() and not tb.is_alive()
        assert seen == {"A_inside_with_B": 2, "B_after_A_left": 2}, seen
        assert T.current_threads() == start
        reps += 1
    assert reps == 3


@_needs_ctl
def test_a_live_worker_that_entered_first_does_not_freeze_the_process(start):
    """生きている worker が先に入り、主スレッドが後から入って最後に抜ける(修正前 3.8: 全部抜けても 1)。"""
    import threadpoolctl
    release = getattr(getattr(threadpoolctl, "OpenBLASController", None), "clear_controlling_thread", None)
    if release is not None:
        release(force=True)       # 条件を作る: 3.8 では誰も制御を握っていない状態から worker が先に掛ける
    go_in, go_out = threading.Event(), threading.Event()

    def held():
        with T.blas_threads(1):
            go_in.set()
            assert go_out.wait(10)
        return T.current_threads()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:   # 抜けた後も worker は生きている
        fut = ex.submit(held)
        assert go_in.wait(10)
        with T.blas_threads(3) as ok:
            assert ok is True
            assert T.current_threads() == 3           # 最後に入った文脈の上限
            go_out.set()
            assert fut.result(20) == 3                # worker が抜けても主スレッドの 3 が残る
            assert T.current_threads() == 3
        assert T.current_threads() == start           # 全部抜けたら元に戻る
        # worker がまだ生きている間に、別スレッドからも元の値が読める
        assert ex.submit(T.current_threads).result(20) == start


@_needs_ctl
def test_the_layer_does_not_keep_other_threads_from_using_threadpoolctl(start):
    """この層を使った後も、利用者が別スレッドで自分の ``threadpool_limits`` を使える。"""
    from threadpoolctl import threadpool_limits
    with T.blas_threads(1):
        pass

    def worker():
        with threadpool_limits(limits=1, user_api="blas"):
            return T.current_threads()
    assert _in_thread(worker) == 1
    assert T.current_threads() == start


@_needs_ctl
def test_applied_is_false_when_the_cap_does_not_take_hold(start, monkeypatch):
    """BLAS が設定を黙って捨てる場合、``as`` は ``True`` と答えない(修正前: 常に True)。"""
    ctl = T._controller()
    blas = [lc for lc in ctl.lib_controllers if lc.user_api == "blas"]
    assert len(blas) >= 1
    for lc in blas:
        monkeypatch.setattr(lc, "set_num_threads", lambda n: None)     # 黙って捨てる BLAS
    with T.blas_threads(1) as ok:
        assert T.current_threads() == start           # 本当に効いていない
        assert ok is False
    with T.for_decomposition(64) as ok:
        assert ok is False
    assert T._ACTIVE == [] and T._HELD["limiter"] is None
    monkeypatch.undo()
    with T.blas_threads(1) as ok:                     # 戻せば効く(上の False は実測で決まっている)
        assert ok is True and T.current_threads() == 1


# --------------------------------------------------------------------------- T6(同じファイル、同じ日)
# 全数テスト(手元 -n 16)で 1 回: ``test_t6_api_single_op_gpu_path_defers_to_core`` が median_image で
# ``_NOACCEL`` を受けて落ちた。原因は GPU の遮断器 ``api._GPU_OPEN``(プロセスで 1 つ): 同じワーカーで先に
# 走った ``test_api_device.py::test_apply_device_graceful``(CUDA の無い機械で device="cuda")が
# median_image を開け、誰も閉じなかった。2 本を順に回すと毎回再現する(偶発ではなく順序依存)。

def test_t6_still_holds_when_an_earlier_test_left_the_breaker_open():
    """遮断器が開いた状態から T6 を回しても通り、遮断器はその状態のまま返る(修正前: AssertionError)。"""
    accel = pytest.importorskip("accel")
    if not accel._HAS_TORCH:
        pytest.skip("accel kernels need torch")
    import api
    import fast
    import test_redteam2_state_2026_11_05 as r2
    rev = api._accel_reverse(accel)
    regs = sorted(r for r in fast._KNOB_B_OPTIONED if r in rev)
    assert len(regs) >= 7 and "median_image" in regs
    api._GPU_OPEN.update(regs)              # 先のテストが全部開けたまま残した、を作る
    before = set(api._GPU_OPEN)
    r2.test_t6_api_single_op_gpu_path_defers_to_core()
    assert set(api._GPU_OPEN) == before     # T6 は自分の外の状態を変えない
    # ここで開けた分は conftest の後始末が戻す(次の test が確かめる)


def test_the_breaker_guard_puts_the_breakers_back():
    """conftest の後始末: 中で開けた遮断器は、抜けると入ったときの中身に戻る。"""
    import api
    from conftest import _API_BREAKERS, _api_breakers_restored
    assert _API_BREAKERS == ("_GPU_OPEN", "_FAST_OPEN")
    outer = {k: set(getattr(api, k)) for k in _API_BREAKERS}
    with _api_breakers_restored():
        for k in _API_BREAKERS:
            getattr(api, k).add("median_image")
            getattr(api, k).add("t8_flake_probe")
    for k in _API_BREAKERS:
        assert set(getattr(api, k)) == outer[k], k
        assert "t8_flake_probe" not in getattr(api, k)


def test_a_device_cuda_failure_does_not_leak_into_the_next_test_part_1():
    """順序依存の再現の前半: CUDA の無い機械で device="cuda" を頼むと遮断器が開く(仕様どおり)。"""
    import api
    import numpy as np
    x = np.clip(np.random.default_rng(0).random((48, 48)), 0, 1)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        api.apply(x, "median_image", 0.5, 0.4, device="cuda")
    try:
        import accel
    except ImportError:
        return                             # accel が無い = GPU 経路そのものが無い(遮断器は開かない)
    if getattr(accel, "_HAS_TORCH", False) and not api.cuda_available():
        assert "median_image" in api._GPU_OPEN   # torch はあるが CUDA が無い = 手元の再現条件


def test_a_device_cuda_failure_does_not_leak_into_the_next_test_part_2():
    """後半: 前のテストが開けた遮断器は残っていない(xdist で別ワーカーに分かれても成り立つ)。"""
    import api
    assert "median_image" not in api._GPU_OPEN
