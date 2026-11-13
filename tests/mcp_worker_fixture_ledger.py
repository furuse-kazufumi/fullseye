# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tests/test_mcp_isolated_ops_2026_11_13.py が隔離した子プロセスに読ませる、試験用の小さな台帳。

本物の台帳と同じ形(``TABLE[name]["func"]``)。MCP のサーバはクライアントに台帳を選ばせない
(OP_GRAPH の実行先だけを使う)ので、この台帳に届く道は試験の中の :class:`OpWorker` の直接呼び出しだけ。
"""
import os
import time

import numpy as np


def _sleep(seconds=60.0):
    time.sleep(float(seconds))
    return {"slept_s": float(seconds)}


def _allocate(mebibytes=1024):
    block = np.ones(int(mebibytes) << 17, dtype=np.float64)      # 1 MiB = 2**17 個の float64
    time.sleep(1.0)                                              # 見張りが読む間、持ったままにする
    return {"sum": float(block.sum())}


def _write_outside(target):
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("written by the worker")
    return {"written": True}


def _read_outside(target):
    with open(target, encoding="utf-8") as fh:
        return {"text": fh.read()}


def _remove_outside(target):
    os.remove(target)
    return {"removed": True}


def _connect():
    import socket
    with socket.socket() as sock:
        sock.settimeout(0.2)
        sock.connect(("127.0.0.1", 9))
    return {"connected": True}


def _spawn():
    import subprocess
    import sys
    subprocess.run([sys.executable, "-c", "print(1)"], check=True)
    return {"spawned": True}


def _object_result():
    return {"thing": object()}


def _table(scale=2.0):
    return {"height_mm": 3.0 * float(scale), "image": np.linspace(0.0, 1.0, 64 * 48).reshape(64, 48),
            "rows": [{"name": "a", "angle_deg": 10.0}, {"name": "b", "angle_deg": 20.0}],
            "tuple": (1, 2.5, "x"), "flag": True, "nothing": None, "bad": float("nan")}


def _scratch_write():
    with open("inside.txt", "w", encoding="utf-8") as fh:        # 作業フォルダの中は書ける
        fh.write("ok")
    os.remove("inside.txt")
    return {"ok": True}


TABLE = {name: {"func": func} for name, func in {
    "sleep": _sleep, "allocate": _allocate, "write_outside": _write_outside, "read_outside": _read_outside,
    "remove_outside": _remove_outside, "connect": _connect, "spawn": _spawn, "object_result": _object_result,
    "table": _table, "scratch_write": _scratch_write}.items()}
