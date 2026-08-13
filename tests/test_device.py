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


def test_facade_exposes_device():
    import fullseye
    assert hasattr(fullseye, "DigitalIO") and hasattr(fullseye, "signal_result")
