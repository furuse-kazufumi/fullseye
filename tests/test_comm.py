"""Tests for the communication layer (comm.py).

The native transports and the built-in Modbus-TCP client are exercised against a
loopback echo server and the in-process Modbus simulator (no hardware). Optional
adapters are checked for a clear 'needs pip install X' error, not a crash."""
import socket
import threading

import pytest

import comm
from comm import ModbusTcpChannel, ModbusTcpServer


# ---- pure Modbus PDU build/parse (exact) --------------------------------- #
def test_modbus_build_read_pdu():
    assert comm.modbus_build_pdu(0x03, 100, 2).hex() == "0300640002"   # FC3 addr100 count2
    assert comm.modbus_build_pdu(0x05, 0, True).hex() == "050000ff00"  # write coil ON


def test_modbus_parse_exception_raises():
    with pytest.raises(comm.CommError):
        comm.modbus_parse_response(0x03, bytes([0x83, 0x02]))          # FC3|0x80, exc 2


def test_modbus_parse_read_registers():
    # FC3 response: fc, byte_count=4, two regs 0x04D2 (1234), 0x162E (5678)
    pdu = bytes([0x03, 0x04, 0x04, 0xD2, 0x16, 0x2E])
    assert comm.modbus_parse_response(0x03, pdu) == [1234, 5678]


# ---- Modbus-TCP client <-> simulator round-trip -------------------------- #
def test_modbus_roundtrip_registers_and_coils():
    srv = ModbusTcpServer(port=0, registers={100: 1234, 101: 5678}).start()
    try:
        with ModbusTcpChannel("127.0.0.1", srv.port) as ch:
            assert ch.read("holding", 100, 2) == [1234, 5678]
            ch.write("holding", 100, 4242)
            assert ch.read("holding", 100, 1) == [4242]
            ch.write("coil", 0, True)
            assert ch.read("coil", 0, 1) == [True]
            ch.write("coil", 5, [True, False, True])           # multiple coils
            assert ch.read("coil", 5, 3) == [True, False, True]
            ch.write("holding", 200, [11, 22, 33])             # multiple registers
            assert ch.read("holding", 200, 3) == [11, 22, 33]
    finally:
        srv.stop()


def test_modbus_read_bad_kind():
    srv = ModbusTcpServer(port=0).start()
    try:
        with ModbusTcpChannel("127.0.0.1", srv.port) as ch:
            with pytest.raises(ValueError):
                ch.read("nope", 0, 1)
    finally:
        srv.stop()


# ---- TCP transport over a loopback echo server --------------------------- #
def test_tcp_channel_send_receive():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def echo():
        conn, _ = srv.accept()
        with conn:
            conn.sendall(conn.recv(64))

    t = threading.Thread(target=echo, daemon=True)
    t.start()
    with comm.TcpChannel("127.0.0.1", port) as ch:
        ch.send(b"ping")
        assert ch.receive(64) == b"ping"
    t.join(timeout=2.0)
    srv.close()


# ---- registry / capabilities --------------------------------------------- #
def test_registry_and_capabilities():
    names = comm.protocols()
    for native in ("tcp", "udp", "http", "modbus-tcp"):
        assert native in names
    caps = {c["name"]: c for c in comm.capabilities()}
    assert caps["modbus-tcp"]["native"] and caps["modbus-tcp"]["available"]
    # an optional adapter is registered and reports its pip package
    assert caps["mqtt"]["native"] is False and caps["mqtt"]["pip"] == "paho-mqtt"


def test_open_unknown_protocol_raises():
    with pytest.raises(KeyError):
        comm.open_channel("does-not-exist")


def test_optional_without_lib_gives_clear_error():
    # 'serial' needs pyserial; if it's absent, opening it must name the package
    caps = {c["name"]: c for c in comm.capabilities()}
    if not caps["serial"]["available"]:
        with pytest.raises(comm.CommError) as ei:
            comm.open_channel("serial", port="COM_NONEXISTENT")
        assert "pyserial" in str(ei.value)


def test_catalog_kinds_and_scaffold():
    caps = {c["name"]: c for c in comm.capabilities()}
    # a broad, honestly-labelled menu: native + optional + scaffold
    assert caps["modbus-tcp"]["kind"] == "native"
    assert caps["ethernet-ip"]["kind"] == "optional" and caps["ethernet-ip"]["pip"] == "pycomm3"
    assert caps["ethercat"]["kind"] == "scaffold"
    kinds = {c["kind"] for c in comm.capabilities()}
    assert kinds == {"native", "optional", "scaffold"}
    assert len(comm.protocols()) >= 20                    # comprehensive


def test_cataloged_protocol_gives_install_hint():
    with pytest.raises(comm.CommError) as ei:
        comm.open_channel("ethernet-ip")                  # not installed here
    assert "pycomm3" in str(ei.value)


def test_facade_exposes_comm():
    import fullseye
    assert hasattr(fullseye, "open_channel") and hasattr(fullseye, "ModbusTcpChannel")
    assert "modbus-tcp" in fullseye.protocols()
    cap = fullseye.capabilities()                          # aggregate comm+acquire+device
    assert set(cap) == {"comm", "acquire", "device"}


# --------------------------------------------------------------------------- #
# 名簿と扉 —— 全数で見る                                                        #
# --------------------------------------------------------------------------- #
#: ★**1 本だけ見る門は、1 本だけしか守らない。** ここには長いあいだ
#: `test_cataloged_protocol_gives_install_hint` が在り、`ethernet-ip` の断り文句
#: **1 本**だけを見ていた。その陰で `cclink` は
#: 「install 'None' and use the None client directly」と答えていた —— pip 名も
#: import 名も持たない 1 行が、場合分けの外に落ちていたからである
#: ([[feedback_one_probe_input_is_not_coverage]])。全数で見る。
#: ★**「相手が居ない」は「扉が無い」ではない**(device 側で先に踏んだ):
#: native な protocol は本当に繋ぎに行くので、`OSError` は扉が在る証拠として通す。
def _assert_every_protocol_has_a_door(names, opener, registry) -> None:
    missing, vague = [], []
    for name in names:
        entry = registry[name]
        try:
            got = opener(name)
        except comm.CommError as e:
            msg = str(e)
            hints = [h for h in (entry.get("_probe"), entry.get("pip")) if h]
            if name not in msg:
                vague.append((name, "断り文句が protocol 名を言わない: %s" % msg))
            elif "None" in msg:
                vague.append((name, "持っていない名前をそのまま書いている: %s" % msg))
            elif hints and not any(h in msg for h in hints):
                vague.append((name, "何を入れればよいか言わない: %s" % msg))
            continue
        except OSError:
            continue                      # 線の先に誰も居ないのは、口が無いのとは別
        except Exception as e:            # noqa: BLE001
            missing.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        try:
            got.close()
        except Exception:
            pass
    assert not missing, (
        "名簿に載っているのに扉が無い protocol: %s —— 開くか CommError で断ること"
        % (missing,))
    assert not vague, "断り文句が何も教えていない: %s" % (vague,)


def test_every_protocol_on_the_menu_has_a_door():
    _assert_every_protocol_has_a_door(comm.protocols(), comm.open_channel, comm._REGISTRY)


def test_a_protocol_without_a_pip_package_is_not_told_to_install_none():
    """★実際に踏んだ形 —— pip 名を持たない protocol の断り文句を読む。"""
    with pytest.raises(comm.CommError) as ei:
        comm.open_channel("cclink")
    msg = str(ei.value)
    assert "None" not in msg, "持っていない名前をそのまま書いている: %s" % msg
    assert "cclink" in msg


def test_the_door_gate_catches_a_refusal_that_says_none():
    """★門を壊して確かめる。"""
    def opener(name):
        raise comm.CommError("protocol %r needs 'None' (pip install None)" % name)

    with pytest.raises(AssertionError) as e:
        _assert_every_protocol_has_a_door(["cclink"], opener, comm._REGISTRY)
    assert "持っていない名前" in str(e.value)


def test_the_door_gate_catches_a_protocol_with_no_entry_point():
    def opener(name):
        raise KeyError(name)

    with pytest.raises(AssertionError) as e:
        _assert_every_protocol_has_a_door(["mqtt"], opener, comm._REGISTRY)
    assert "扉が無い" in str(e.value)
