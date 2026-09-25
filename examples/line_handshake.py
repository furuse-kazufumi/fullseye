# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""line_handshake — 検査の判定を PLC の線に出す。TCP でも、シリアル(RTU)でも。

    py -3.11 examples/line_handshake.py

【この例が示すこと】
検査は「良否を決める」までで終わりではなく、**線の向こうの機械がそれを受け取って
初めて**仕事になる。ここではハードを 1 つも使わずに、その最後の一歩を通す:

1. 合成の部品を 1 枚検査して ok / ng を決める
2. 判定を **Modbus TCP** のコイルへ one-hot で出す(内蔵の PLC シミュレータ)
3. 同じ判定を **Modbus RTU**(シリアル線)へ出す(内蔵の装置役。実物の線も
   ``port="COM3"`` に替えるだけで、上の呼び方は 1 文字も変わらない)
4. ★**線が嘘をついたとき何が起きるか** —— 1 ビット化けた框と、別の装置の返事。
   どちらも「それらしい数」を返さずに落ちることを確かめる

4 がこの例の眼目である。現場で人を困らせるのは正常系ではなく、**間違った数が
正しい顔をして返ってくる**ことだから。

EXTEND: `fullseye.drivers()` / `fullseye.protocols()` が名簿で、`open_driver` /
`open_channel` がその名前で開く口。開けないものは何を入れればよいかを名指しで返す。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402

#: Verdict -> コイル番号(device.signal_verdict の既定と同じ one-hot)
_COILS = {"ok": 0, "ng": 1, "error": 2, "timeout": 3}


def inspect_one(bright: int, seed: int = 0) -> str:
    """64x64 の板。明部が 400 px 前後なら ok、外れたら ng。

    ★板にセンサ雑音を載せてある。**完全に平らな合成画像は現実の入力ではない**から。

    ついでに、このサンプルを書いたときに平らな板を素直に作ったことで `otsu` の
    欠陥が出た —— しきい値を argmax ビンの**中点**で取っていたので、背景の山を
    含むビンの画素が前景に混ざり、板の全画素が前景になっていた。2026-09-26 に
    直してある(堅牢性台帳 `otsu-threshold-at-the-bin-midpoint`)。雑音を載せた
    入力では「だいたい合って」いたので、30 年分の試験が全部通していた。
    """
    rng = np.random.default_rng(seed)
    im = 0.30 + 0.02 * rng.standard_normal((64, 64))
    k = int(round(bright ** 0.5)) // 2
    im[32 - k:32 + k, 32 - k:32 + k] = 0.9
    im = np.clip(im, 0.0, 1.0)
    area = float((fs.apply(im, "otsu") > 0.5).sum())
    verdict = fs.judge({"area": area}, {"area": {"nominal": 400.0, "tol": 60.0}})
    return verdict.status


def over_modbus_tcp(status: str) -> dict:
    """内蔵の PLC シミュレータへ、one-hot でコイルを立てる。"""
    srv = fs.ModbusTcpServer(port=0).start()
    try:
        io = fs.open_driver("io-modbus", host="127.0.0.1", port=srv.port)
        try:
            fs.signal_verdict(io, status)
        finally:
            io.close()
        return {st: bool(srv.coils.get(pin, False)) for st, pin in _COILS.items()}
    finally:
        srv.stop()


def over_modbus_rtu(status: str) -> dict:
    """同じ判定を、シリアル線の框(アドレス + CRC)に載せて出す。"""
    dev = fs.ModbusRtuLoopback(unit=1)
    ch = fs.ModbusRtuChannel(transport=dev, unit=1)
    try:
        for st, pin in _COILS.items():
            ch.write("coil", pin, st == status)
    finally:
        ch.close()
    return {st: bool(dev.coils.get(pin, False)) for st, pin in _COILS.items()}


def when_the_line_lies() -> list:
    """★線が嘘をついたときに、**黙って数を返さない**ことを確かめる。"""
    out = []

    #: (a) 線の上で 1 ビット化ける。
    frame = bytearray(fs.modbus_rtu_frame(1, fs.modbus_build_pdu(0x03, 0, 1)))
    frame[3] ^= 0x01
    try:
        fs.modbus_rtu_unframe(bytes(frame), unit=1)
        out.append(("1 ビット化けた框", "素通りした(まずい)"))
    except fs.CommError as e:
        out.append(("1 ビット化けた框", str(e)))

    #: (b) 共有の RS-485 で、別の装置の返事を読んでしまう。
    dev = fs.ModbusRtuLoopback(unit=1, registers={0: 1234})
    other = fs.ModbusRtuChannel(transport=dev, unit=9, timeout=0.01)
    try:
        other.read("holding", 0, 1)
        out.append(("別の装置に話しかけた", "答えが返ってきた(まずい)"))
    except fs.CommError as e:
        out.append(("別の装置に話しかけた", str(e)))
    finally:
        other.close()
    return out


def main() -> int:
    for bright, want in ((400, "ok"), (900, "ng")):
        status = inspect_one(bright)
        assert status == want, "明部 %d px の判定が %s(期待 %s)" % (bright, status, want)
        tcp = over_modbus_tcp(status)
        rtu = over_modbus_rtu(status)
        assert tcp == rtu, "TCP と RTU で出た信号が違う: %s / %s" % (tcp, rtu)
        assert tcp[status] is True and sum(tcp.values()) == 1, (
            "one-hot になっていない: %s" % tcp)
        print("明部 %3d px -> %-2s  コイル %s  (TCP と RTU で一致)"
              % (bright, status, "".join("1" if tcp[s] else "0" for s in _COILS)))

    print()
    print("線が嘘をついたとき:")
    for what, said in when_the_line_lies():
        assert "まずい" not in said, "%s: %s" % (what, said)
        print("  %-22s -> %s" % (what, said))

    print()
    caps = fs.capabilities()
    print("名簿と、そのうち Fullseye 自身が開けるもの:")
    for layer in ("comm", "acquire", "device"):
        rows = caps[layer]
        n = sum(1 for r in rows if r["implemented"])
        print("  %-8s %2d / %2d" % (layer, n, len(rows)))
    print("  (開けない行も、何を入れればよいかは名指しで返ります)")
    print()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
