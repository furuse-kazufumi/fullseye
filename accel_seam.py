"""型付き op の計算核を差し替える継ぎ目(stdlib のみ、torch を import しない)。

型付き op(``tomography.radon_transform`` など)は入力検証が本体で、計算核はその奥の 1 関数に
閉じている。GPU 版のために検証ごと書き写すと検証が 2 重になって必ず割れるので、**検証は core の
1 か所のまま、核だけ** ``contextvars`` で差し替える。文脈が空のとき(既定)core は従来どおり numpy で
走り、この継ぎ目のコストは ``ContextVar.get`` 1 回。

    with accel_seam.use({"tomography.project": kernel}):
        sino = tomography.radon_transform(image)

差し替えは呼び出し文脈に閉じるのでスレッド間で漏れない。入口は ``accel_typed.call``。
"""
from __future__ import annotations

import contextlib
import contextvars

_KERNELS: contextvars.ContextVar = contextvars.ContextVar("fullseye_accel_kernels", default=None)


def kernel(name):
    """差し替えられた核を返す。文脈が空・未登録なら ``None``(= core の numpy 経路を走る)。"""
    table = _KERNELS.get()
    return None if table is None else table.get(name)


@contextlib.contextmanager
def use(table):
    """``table``(核の名前 -> 関数)をこの文脈の間だけ有効にする。"""
    token = _KERNELS.set(dict(table))
    try:
        yield
    finally:
        _KERNELS.reset(token)
