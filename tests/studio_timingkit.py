"""Studio timing test helpers / Studio の時間試験用の道具。

「止められない呼び出し」の代わり: 利用者コードを C の待ち(``threading.Lock.acquire``)に置く。
PyThreadState_SetAsyncExc の例外は Python の bytecode に戻るまで届かないので、この待ちはどの OS でも
Studio の見張りから止められない(有限の ``time.sleep`` は遅い CI で見張りの猶予より先に戻ってしまう)。

2026-11-23: 安全弁を ``threading.Timer`` から「待ち自体の上限」(``acquire(True, 上限)``)に替えた。
Linux CI の full suite で test_7_infinite_loop_is_stopped が 1 時間 40 分止まり、faulthandler の記録では
安全弁の Timer のスレッド 2 本が Event の中の lock を取り直せずに止まっていた(放す側が一度も来ない)。
補助のスレッドに頼らず、待ちそのものが上限で必ず戻る形にする。上限の間も C の待ちのまま。
"""
import builtins
import threading


#: 失敗した試験でも待ちを永久に残さない秒数(待ち 1 回の上限) / per-wait failsafe in seconds.
UNSTOPPABLE_FAILSAFE_S = 15.0
#: 利用者コードから試験用 lock を参照する builtins 名 / builtin name for the test lock.
UNSTOPPABLE_BUILTIN = "_fullseye_test_unstoppable_gate"


class _BoundedLock:
    """``acquire()`` が試験の放す時か上限で必ず戻る lock(どちらも C の待ちのまま)。"""

    def __init__(self, inner, limit_s):
        self._inner = inner
        self._limit_s = limit_s

    def acquire(self, blocking=True, timeout=-1):
        if not blocking:
            return self._inner.acquire(False)
        limit = self._limit_s if timeout is None or timeout < 0 else min(timeout, self._limit_s)
        got = self._inner.acquire(True, limit)
        if got:
            self._inner.release()            # 放された門は開いたまま(次の待ちもすぐ通す)
        return got

    def release(self):
        self._inner.release()


class UnstoppableGate:
    """Hold user code in a C wait until the test releases it (or the failsafe passes).

    試験が解放するまで(または上限まで)、利用者コードを C レベルの待機に置く。
    """

    def __init__(self, limit_s=UNSTOPPABLE_FAILSAFE_S):
        self._inner = threading.Lock()
        self._inner.acquire()
        self._release_guard = threading.Lock()
        self._released = False
        self.lock = _BoundedLock(self._inner, limit_s)
        setattr(builtins, UNSTOPPABLE_BUILTIN, self.lock)

    @property
    def expression(self):
        """利用者コード用の待機式 / expression that waits on this gate."""
        return "__import__('builtins').%s.acquire()" % UNSTOPPABLE_BUILTIN

    def source(self, after=""):
        """待機後も続ける利用者コード / user source that continues after the wait."""
        return (
            "import builtins\n"
            "try:\n"
            "    builtins.%s.acquire()\n"
            "except BaseException:\n"
            "    pass\n" % UNSTOPPABLE_BUILTIN
        ) + after

    def release(self):
        """待機を一度だけ解く / release the wait once."""
        with self._release_guard:
            if not self._released:
                self._released = True
                self._inner.release()

    def close(self):
        """待機と builtins の参照を片付ける / release and remove the builtin reference."""
        self.release()
        if getattr(builtins, UNSTOPPABLE_BUILTIN, None) is self.lock:
            delattr(builtins, UNSTOPPABLE_BUILTIN)
