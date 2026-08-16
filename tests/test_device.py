"""Tests for the device-control layer (device.py) — the vision->line loop.

The memory backend needs no hardware; the modbus backend is exercised against the
in-process Modbus simulator from comm.py. GPIO is hardware-only and not tested here."""
import time

import comm
import device
from device import DigitalIO


def test_memory_set_get():
    io = DigitalIO("memory")
    assert io.get(0) is False
    io.set(0, True)
    assert io.get(0) is True
    io.set(0, False)
    assert io.get(0) is False


def test_pulse_leaves_output_low():
    io = DigitalIO("memory")
    io.pulse(3, ms=1)
    assert io.get(3) is False                    # a one-shot returns to low


def test_signal_result_drives_pass_fail():
    io = DigitalIO("memory")
    device.signal_result(io, True)               # PASS
    assert io.get(0) is True and io.get(1) is False
    device.signal_result(io, False)              # FAIL
    assert io.get(0) is False and io.get(1) is True


def test_signal_verdict_one_hot_all_states():
    io = DigitalIO("memory")
    for status in device._VERDICT_COILS:
        assert device.signal_verdict(io, status) == status
        for st, pin in device._VERDICT_COILS.items():
            assert io.get(pin) is (st == status)     # exactly one coil high per verdict


def test_signal_verdict_error_and_timeout_never_read_as_pass():
    """Fail-closed: a vision error or a deadline timeout must clear the OK coil."""
    io = DigitalIO("memory")
    device.signal_verdict(io, "ok")
    assert io.get(0) is True                          # ok coil high
    for bad in ("error", "timeout", "ng"):
        device.signal_verdict(io, bad)
        assert io.get(0) is False                     # ok coil cleared for every non-ok verdict


def test_signal_verdict_accepts_a_verdict_object_and_rejects_unknown():
    import pytest

    class _V:                                         # duck-typed fsruntime.Verdict
        status = "ng"
    io = DigitalIO("memory")
    assert device.signal_verdict(io, _V()) == "ng"
    assert io.get(1) is True and io.get(0) is False
    with pytest.raises(ValueError):
        device.signal_verdict(io, "bogus")           # unmapped -> raise, never all-low
    with pytest.raises(ValueError):
        device.signal_verdict(io, 123)               # not a status/Verdict


def test_signal_verdict_over_modbus_simulator():
    srv = comm.ModbusTcpServer(port=0).start()
    try:
        with DigitalIO("modbus", host="127.0.0.1", port=srv.port) as io:
            device.signal_verdict(io, "timeout")
            assert io.get(3) is True                  # timeout coil high
            assert not any(io.get(p) for p in (0, 1, 2))
    finally:
        srv.stop()


def test_wait_input_true_and_timeout():
    io = DigitalIO("memory", initial={5: True})
    assert device.wait_input(io, 5, True, timeout=0.1) is True
    assert device.wait_input(io, 6, True, timeout=0.05) is False   # never set -> timeout


def test_modbus_backend_over_simulator():
    srv = comm.ModbusTcpServer(port=0).start()
    try:
        with DigitalIO("modbus", host="127.0.0.1", port=srv.port) as io:
            io.set(10, True)
            assert io.get(10) is True
            device.signal_result(io, False, pass_pin=0, fail_pin=1)
            assert io.get(0) is False and io.get(1) is True
    finally:
        srv.stop()


def test_unknown_backend_raises():
    import pytest
    with pytest.raises(ValueError):
        DigitalIO("nope")


def test_driver_capabilities_catalog():
    caps = {c["name"]: c for c in device.capabilities()}
    assert caps["io-memory"]["kind"] == "native" and caps["io-memory"]["available"]
    assert caps["dynamixel"]["kind"] == "optional" and caps["dynamixel"]["pip"] == "dynamixel-sdk"
    assert caps["ur-rtde"]["family"] == "robot"          # Physical-AI robots catalogued
    assert caps["franka"]["kind"] == "scaffold"


def test_facade_exposes_device():
    import fullseye
    assert hasattr(fullseye, "DigitalIO") and hasattr(fullseye, "signal_result")
