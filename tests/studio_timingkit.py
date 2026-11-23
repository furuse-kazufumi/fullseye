"""Studio timing test helpers / Studio の時間試験用の道具。"""
import builtins
import threading


#: 失敗した試験でも待機を永久に残さない秒数 / failsafe release delay.
UNSTOPPABLE_FAILSAFE_S = 15.0
#: 利用者コードから試験用 lock を参照する builtins 名 / builtin name for the test lock.
UNSTOPPABLE_BUILTIN = "_fullseye_test_unstoppable_gate"


class UnstoppableGate:
    """Hold user code in a C wait until the test releases it.

    試験が解放するまで、利用者コードを C レベルの待機に置く。
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.lock.acquire()
        self._release_guard = threading.Lock()
        self._released = False
        setattr(builtins, UNSTOPPABLE_BUILTIN, self.lock)
        self._failsafe = threading.Timer(UNSTOPPABLE_FAILSAFE_S, self.release)
        self._failsafe.daemon = True
        self._failsafe.start()

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
                self.lock.release()
        self._failsafe.cancel()

    def close(self):
        """待機と builtins の参照を片付ける / release and remove the builtin reference."""
        self.release()
        if getattr(builtins, UNSTOPPABLE_BUILTIN, None) is self.lock:
            delattr(builtins, UNSTOPPABLE_BUILTIN)
