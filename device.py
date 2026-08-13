"""device.py — device control: digital I/O and closing the vision loop to the line.

The control half HALCON leaves to a separate PLC/PC. A Fullseye pipeline decides
pass/fail (or a position); ``device.py`` turns that decision into an action on the
cell — set an output, pulse an ejector, wait for a trigger — over the transports in
:mod:`comm` (Modbus coils) or embedded-Linux GPIO.

    import fullseye
    io = fullseye.DigitalIO("modbus", host="127.0.0.1", port=1502)   # a PLC's coils
    ok = eng.run(frame).mean() > 0.5          # some inspection verdict
    fullseye.signal_result(io, ok)            # drive PASS / FAIL outputs
    fullseye.pulse(io, pin=3, ms=50)          # kick the reject ejector

Backends: ``"memory"`` (in-process, for tests/dev), ``"modbus"`` (PLC coils via the
built-in Modbus-TCP client), ``"gpio"`` (Raspberry Pi / Jetson / SBC — optional,
needs ``periphery`` or ``RPi.GPIO`` or ``gpiod``).
"""
from __future__ import annotations

import time

__all__ = ["DigitalIO", "pulse", "signal_result", "wait_input"]


class DigitalIO:
    """A set of digital outputs/inputs addressed by integer *pin*.

    ``set(pin, on)`` / ``get(pin) -> bool`` / ``pulse(pin, ms)``. Backends:

    - ``"memory"`` — a dict, for tests and dry-runs (no hardware).
    - ``"modbus"`` — pins are Modbus coil addresses on a PLC (via :mod:`comm`).
    - ``"gpio"``   — GPIO lines on an SBC (optional: ``periphery`` / ``RPi.GPIO`` / ``gpiod``).
    """

    def __init__(self, backend="memory", **opts):
        self.backend = backend
        self.opts = opts
        self._state = {}                       # memory backend
        self._ch = None                        # modbus channel
        self._gpio = None                      # gpio handles {pin: line}
        self._open()

    def _open(self):
        if self.backend == "memory":
            self._state = dict(self.opts.get("initial", {}))
        elif self.backend == "modbus":
            import comm
            host = self.opts.get("host", "127.0.0.1")
            port = int(self.opts.get("port", 502))
            unit = int(self.opts.get("unit", 1))
            self._ch = comm.ModbusTcpChannel(host, port, unit=unit)
        elif self.backend == "gpio":
            self._open_gpio()
        else:
            raise ValueError("unknown DigitalIO backend %r" % (self.backend,))

    def _open_gpio(self):  # pragma: no cover - needs SBC hardware
        self._gpio = {}
        try:
            from periphery import GPIO  # noqa: F401
            self._gpio_kind = "periphery"
        except Exception:
            try:
                import RPi.GPIO as RG
                RG.setmode(RG.BCM)
                self._gpio_kind = "rpi"
                self._rpi = RG
            except Exception as e:
                raise RuntimeError(
                    "gpio backend needs one of: periphery / RPi.GPIO / gpiod: %s" % e)

    # ------------------------------------------------------------------- I/O --
    def set(self, pin: int, on: bool = True):
        """Drive output *pin* high/low. Returns self for chaining."""
        pin = int(pin)
        if self.backend == "memory":
            self._state[pin] = bool(on)
        elif self.backend == "modbus":
            self._ch.write("coil", pin, bool(on))
        elif self.backend == "gpio":  # pragma: no cover
            self._gpio_write(pin, on)
        return self

    def get(self, pin: int) -> bool:
        """Read input/output *pin*."""
        pin = int(pin)
        if self.backend == "memory":
            return bool(self._state.get(pin, False))
        if self.backend == "modbus":
            return bool(self._ch.read("coil", pin, 1)[0])
        if self.backend == "gpio":  # pragma: no cover
            return self._gpio_read(pin)
        return False

    def pulse(self, pin: int, ms: float = 50.0):
        """Set *pin* on, wait *ms*, set it off — a one-shot (eject / strobe / trigger)."""
        self.set(pin, True)
        time.sleep(max(0.0, float(ms)) / 1000.0)
        self.set(pin, False)
        return self

    def _gpio_write(self, pin, on):  # pragma: no cover
        if self._gpio_kind == "periphery":
            from periphery import GPIO
            line = self._gpio.get(pin) or self._gpio.setdefault(pin, GPIO(pin, "out"))
            line.write(bool(on))
        else:
            self._rpi.setup(pin, self._rpi.OUT)
            self._rpi.output(pin, bool(on))

    def _gpio_read(self, pin):  # pragma: no cover
        if self._gpio_kind == "periphery":
            from periphery import GPIO
            line = self._gpio.get(pin) or self._gpio.setdefault(pin, GPIO(pin, "in"))
            return bool(line.read())
        self._rpi.setup(pin, self._rpi.IN)
        return bool(self._rpi.input(pin))

    def close(self):
        if self.backend == "modbus" and self._ch is not None:
            self._ch.close(); self._ch = None
        elif self.backend == "gpio" and self._gpio:  # pragma: no cover
            for line in self._gpio.values():
                try:
                    line.close()
                except Exception:
                    pass
            self._gpio = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


# --------------------------------------------------------------------------- #
# vision → line helpers
# --------------------------------------------------------------------------- #
def pulse(io: DigitalIO, pin: int, ms: float = 50.0):
    """One-shot an output (eject / strobe). Convenience over :meth:`DigitalIO.pulse`."""
    return io.pulse(pin, ms)


def signal_result(io: DigitalIO, ok: bool, pass_pin: int = 0, fail_pin: int = 1):
    """Drive PASS/FAIL outputs from an inspection verdict.

    Sets *pass_pin* = ok and *fail_pin* = not ok — the standard vision→PLC
    handshake (the PLC reads these to route the part). Returns *ok*."""
    io.set(pass_pin, bool(ok))
    io.set(fail_pin, not bool(ok))
    return bool(ok)


def wait_input(io: DigitalIO, pin: int, state: bool = True,
               timeout: float = 5.0, poll: float = 0.01) -> bool:
    """Block until input *pin* reads *state* (a part-present / trigger signal).

    Returns True when the state is seen, False on *timeout* (seconds). *poll* is
    the polling interval."""
    deadline = timeout
    waited = 0.0
    while waited <= deadline:
        if io.get(pin) == bool(state):
            return True
        time.sleep(max(0.0, float(poll)))
        waited += max(1e-6, float(poll))
    return io.get(pin) == bool(state)
