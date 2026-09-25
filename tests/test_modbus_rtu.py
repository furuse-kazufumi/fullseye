# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Modbus RTU —— 框(アドレス + CRC)と線の口を、ハード無しで全部確かめる門。

★2026-09-25 まで `modbus-rtu` は**名簿に載るだけ**の行で、開こうとすると
「pymodbus を入れて直接使え」と断っていた。だが RTU は Modbus TCP と**同じ PDU**
を別の框で包んだものにすぎず、その PDU の組み立てと解釈は既にこの repo に在って
単体試験も付いていた。**名簿は「持っていないもの」だけでなく、「持っているのに
繋いでいないもの」も隠す。**

ここで見るのは 3 つ:

1. **CRC は公表された検査値と一致する**(CRC-16/MODBUS の ``check=0x4b37``)。
   自作の往復だけだと、反射入力と反射出力を同時に取り違えた実装が緑になる。
2. **框は fail-closed** —— CRC 違い・別アドレス・短すぎる框は、もっともらしい
   バイト列を返さずに落ちる。
3. **往復が本当に動く**(:class:`ModbusRtuLoopback` は実物の框を解いて答える)。
"""
from __future__ import annotations

import pytest

import comm


# --------------------------------------------------------------------------- #
# 1. CRC —— 外の値と突き合わせる                                                #
# --------------------------------------------------------------------------- #
def test_the_crc_matches_the_published_check_value():
    """★CRC catalogue: ``check=0x4b37`` は ASCII "123456789" の CRC-16/MODBUS。"""
    assert comm.modbus_crc16(b"123456789") == 0x4B37


def test_the_crc_of_nothing_is_the_initial_value():
    """空入力は init のまま(0xFFFF)—— 諸元 ``init=0xffff`` の直接の帰結。"""
    assert comm.modbus_crc16(b"") == 0xFFFF


def test_the_crc_notices_a_single_flipped_bit():
    a = comm.modbus_crc16(bytes([0x01, 0x03, 0x00, 0x6B, 0x00, 0x03]))
    b = comm.modbus_crc16(bytes([0x01, 0x03, 0x00, 0x6B, 0x00, 0x02]))
    assert a != b, "1 ビット違いで同じ CRC になっている"


def test_a_frame_carries_its_own_check():
    """框に入れた物は、そのまま開けられること(自分との一貫性)。"""
    pdu = comm.modbus_build_pdu(0x03, 0x006B, 3)
    frame = comm.modbus_rtu_frame(17, pdu)
    assert frame[0] == 17 and frame[1:-2] == pdu
    assert comm.modbus_rtu_unframe(frame, unit=17) == pdu


# --------------------------------------------------------------------------- #
# 2. 框は fail-closed                                                           #
# --------------------------------------------------------------------------- #
def test_a_corrupted_frame_is_refused_not_decoded():
    frame = bytearray(comm.modbus_rtu_frame(1, comm.modbus_build_pdu(0x03, 0, 1)))
    frame[3] ^= 0x01                                   # 線に乗った 1 ビットの化け
    with pytest.raises(comm.CommError) as e:
        comm.modbus_rtu_unframe(bytes(frame), unit=1)
    assert "CRC" in str(e.value)


def test_another_slaves_reply_is_refused():
    """★共有の RS-485 で**本当に起きる**間違い —— 別の装置の返事を読む。"""
    frame = comm.modbus_rtu_frame(2, comm.modbus_build_pdu(0x03, 0, 1))
    with pytest.raises(comm.CommError) as e:
        comm.modbus_rtu_unframe(frame, unit=1)
    assert "address mismatch" in str(e.value)


def test_a_truncated_frame_is_refused():
    with pytest.raises(comm.CommError) as e:
        comm.modbus_rtu_unframe(b"\x01\x03")
    assert "too short" in str(e.value)


# --------------------------------------------------------------------------- #
# 3. 往復                                                                       #
# --------------------------------------------------------------------------- #
@pytest.fixture()
def line():
    dev = comm.ModbusRtuLoopback(unit=1, registers={100: 7, 101: 258},
                                 coils={0: True, 1: False})
    ch = comm.ModbusRtuChannel(transport=dev, unit=1)
    yield ch, dev
    ch.close()


def test_reading_registers_over_the_line(line):
    ch, _dev = line
    assert ch.read("holding", 100, 2) == [7, 258]


def test_reading_coils_over_the_line(line):
    ch, _dev = line
    assert ch.read("coil", 0, 2) == [True, False]


def test_writing_a_coil_reaches_the_device(line):
    ch, dev = line
    assert ch.write("coil", 3, True) is True
    assert dev.coils[3] is True


def test_writing_several_registers_reaches_the_device(line):
    ch, dev = line
    assert ch.write("holding", 200, [11, 22]) is True
    assert (dev.registers[200], dev.registers[201]) == (11, 22)


def test_a_bad_kind_is_refused(line):
    ch, _dev = line
    with pytest.raises(ValueError):
        ch.read("nope", 0, 1)
    with pytest.raises(ValueError):
        ch.write("nope", 0, 1)


def test_a_device_at_another_address_stays_silent(line):
    """★実物と同じ振る舞い —— 自分宛でない框には**黙る**(client は待ちぼうけ)。

    何にでも答える模擬装置は、共有バスで実際に出る不具合を隠してしまう。
    """
    _ch, dev = line
    other = comm.ModbusRtuChannel(transport=dev, unit=9)
    with pytest.raises(comm.CommError) as e:
        other.read("holding", 100, 1)
    assert "timed out" in str(e.value)


def test_an_exception_reply_travels_through_the_frame_and_is_raised():
    """装置が「その機能は無い」と答えたときの道筋を端から端まで見る。

    ★これは框の **`fc & 0x80` の長さ分岐**(応答が 3 バイト本体になる)を通る
    唯一の経路でもある —— 正常応答だけを試していると、例外応答の長さを読み違えた
    実装が、次に装置が拒否した瞬間まで緑のままになる。
    """
    dev = comm.ModbusRtuLoopback(unit=1)
    ch = comm.ModbusRtuChannel(transport=dev, unit=1)
    try:
        pdu = ch._transact(bytes([0x07]))          # 装置が扱わない機能
        assert pdu[0] == 0x87 and pdu[1] == 0x01, (
            "illegal function の応答になっていない: %r" % pdu)
        with pytest.raises(comm.CommError) as e:
            comm.modbus_parse_response(0x07, pdu)
        assert "exception" in str(e.value)
    finally:
        ch.close()


# --------------------------------------------------------------------------- #
# 4. 名簿に繋がっていること                                                      #
# --------------------------------------------------------------------------- #
def test_the_menu_now_says_modbus_rtu_is_implemented():
    caps = {c["name"]: c for c in comm.capabilities()}
    assert caps["modbus-rtu"]["implemented"] is True, (
        "本物のアダプタを足したのに名簿が「開けない」と言っている")
    assert caps["modbus-rtu"]["pip"] == "pyserial", (
        "必要なのは pymodbus ではなく pyserial(実物の線を開くときだけ)")


def test_opening_it_by_name_gives_a_working_channel():
    dev = comm.ModbusRtuLoopback(unit=4, registers={0: 42})
    ch = comm.open_channel("modbus-rtu", transport=dev, unit=4)
    try:
        assert ch.read("holding", 0, 1) == [42]
    finally:
        ch.close()


def test_without_pyserial_a_real_port_names_the_package(monkeypatch):
    """★実物の線を開くときだけ pyserial が要る —— 無ければ名指しで断ること。"""
    import builtins
    real = builtins.__import__

    def no_serial(name, *a, **kw):
        if name == "serial":
            raise ImportError("no module named serial")
        return real(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", no_serial)
    with pytest.raises(comm.CommError) as e:
        comm.ModbusRtuChannel(port="COM_NONEXISTENT")
    assert "pyserial" in str(e.value)


def test_the_device_half_is_one_table_shared_by_both_simulators():
    """★TCP の模擬装置と RTU の装置役が、**同じ PDU 処理**を使っていること。

    2 つ書くと、FC を足したときに片方だけ増える。
    """
    srv = comm.ModbusTcpServer(registers={5: 99})
    pdu = comm.modbus_build_pdu(0x03, 5, 1)
    assert srv._handle(pdu) == comm.modbus_apply_pdu(pdu, srv.coils, srv.registers)
