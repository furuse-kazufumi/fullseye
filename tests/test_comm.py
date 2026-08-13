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
