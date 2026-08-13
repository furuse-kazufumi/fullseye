"""comm.py — communication transports & industrial protocols (a Channel registry).

The comms half of a machine-vision cell: push an inspection result to a PLC, read
a sensor register, hit a REST endpoint, subscribe to a broker. HALCON stops at raw
socket / serial; Fullseye adds **protocol-level device I/O** — a built-in,
dependency-free Modbus-TCP client (and a simulator to test against), plus a
registry of optional adapters for the rest — so a Studio pipeline can close the
loop with the line.

A Channel is opened from the registry and used uniformly::

    import fullseye
    with fullseye.open_channel("modbus-tcp", host="127.0.0.1", port=1502) as ch:
        ch.write("coil", 0, True)              # fire an ejector / set a lamp
        regs = ch.read("holding", 100, 2)      # read 2 holding registers
    fullseye.capabilities()                    # which protocols are installed / available

Native (stdlib — work out of the box): ``tcp``, ``udp``, ``http``, ``modbus-tcp``.
Optional (need a pip lib; using one without it raises a clear ``pip install X``):
``serial``, ``mqtt``, ``opcua`` and more — see :func:`capabilities`.
"""
from __future__ import annotations

import socket
import struct

__all__ = [
    "Channel", "open_channel", "protocols", "capabilities", "register",
    "TcpChannel", "UdpChannel", "HttpChannel", "ModbusTcpChannel", "ModbusTcpServer",
]


class CommError(RuntimeError):
    """A communication / protocol error."""


# --------------------------------------------------------------------------- #
# Channel base + registry
# --------------------------------------------------------------------------- #
class Channel:
    """Base class for a communication channel. Subclasses implement the subset
    they support; unsupported operations raise ``NotImplementedError``.

    Byte-stream protocols use :meth:`send` / :meth:`receive`; register / discrete-
    I/O protocols (Modbus, OPC-UA, …) use :meth:`read` / :meth:`write`."""

    def open(self):                                    # pragma: no cover - overridden
        return self

    def close(self):                                   # pragma: no cover - overridden
        pass

    def send(self, data):
        raise NotImplementedError("%s has no send()" % type(self).__name__)

    def receive(self, n: int = 4096):
        raise NotImplementedError("%s has no receive()" % type(self).__name__)

    def read(self, kind, addr, count=1):
        raise NotImplementedError("%s has no read()" % type(self).__name__)

    def write(self, kind, addr, value):
        raise NotImplementedError("%s has no write()" % type(self).__name__)

    def __enter__(self):
        # native channels connect in __init__ (connect=True); do not re-open here
        # or a `with` would create a second connection. Construct with connect=False
        # and call .open() explicitly for deferred opening.
        return self

    def __exit__(self, *exc):
        self.close()
        return False


_REGISTRY: dict = {}


def register(name, factory, native=False, pip=None, desc="", kind=None, probe=None):
    """Register a Channel factory under *name*. *factory(**opts)* returns an opened
    Channel. *native* = pure-stdlib; *pip* = the package an optional adapter needs;
    *kind* ∈ {"native","optional","scaffold"} (defaults from *native*); *probe* is
    the import name used to report availability."""
    if kind is None:
        kind = "native" if native else "optional"
    _REGISTRY[name] = {"factory": factory, "native": bool(native), "pip": pip,
                       "desc": desc, "kind": kind, "_probe": probe}


def open_channel(protocol: str, **opts) -> Channel:
    """Open a channel for *protocol* (see :func:`protocols`). Extra keyword args are
    passed to the adapter (e.g. ``host``, ``port``, ``unit``)."""
    if protocol not in _REGISTRY:
        raise KeyError("unknown protocol %r; known: %s" % (protocol, ", ".join(sorted(_REGISTRY))))
    return _REGISTRY[protocol]["factory"](**opts)


def protocols() -> list:
    """All registered protocol names."""
    return sorted(_REGISTRY)


def _importable(mod: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def capabilities() -> list:
    """Per-protocol availability: ``{name, kind, native, available, pip, desc}``.

    ``kind`` ∈ native / optional / scaffold. ``available`` is True for native
    protocols and for optional/scaffold ones whose pip package is importable — so
    you see at a glance what this install can talk to and what a ``pip install``
    would unlock."""
    out = []
    for name in sorted(_REGISTRY):
        e = _REGISTRY[name]
        avail = True if e["native"] else (_importable(e["_probe"]) if e.get("_probe") else False)
        out.append({"name": name, "kind": e.get("kind", "optional"), "native": e["native"],
                    "available": avail, "pip": e["pip"], "desc": e["desc"]})
    return out


# --------------------------------------------------------------------------- #
# Native transports
# --------------------------------------------------------------------------- #
class TcpChannel(Channel):
    """A TCP client socket. ``send`` bytes/str, ``receive`` bytes."""

    def __init__(self, host="127.0.0.1", port=502, timeout=3.0, connect=True):
        self.host, self.port, self.timeout = host, int(port), float(timeout)
        self.sock = None
        if connect:
            self.open()

    def open(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        return self

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.sock.sendall(data)
        return len(data)

    def receive(self, n: int = 4096):
        return self.sock.recv(n)

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None


class UdpChannel(Channel):
    """A UDP socket. ``send`` datagrams to (host, port); ``receive`` one datagram."""

    def __init__(self, host="127.0.0.1", port=0, timeout=3.0, bind=None):
        self.host, self.port, self.timeout = host, int(port), float(timeout)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.timeout)
        if bind is not None:
            self.sock.bind(tuple(bind))

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.sock.sendto(data, (self.host, self.port))

    def receive(self, n: int = 4096):
        data, _addr = self.sock.recvfrom(n)
        return data

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None


class HttpChannel(Channel):
    """A minimal HTTP/REST client (stdlib ``urllib``). ``send`` POSTs the payload;
    :meth:`request` does an arbitrary method. Returns the response body (bytes)."""

    def __init__(self, base_url="http://127.0.0.1", timeout=5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)

    def request(self, method="GET", path="/", data=None, headers=None):
        import urllib.request
        url = self.base_url + (path if path.startswith("/") else "/" + path)
        if isinstance(data, str):
            data = data.encode()
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read()

    def send(self, data, path="/"):
        return self.request("POST", path, data)

    def receive(self, path="/"):
        return self.request("GET", path)


# --------------------------------------------------------------------------- #
# Modbus TCP — pure-Python client (the built-in PLC / I-O differentiator)
# --------------------------------------------------------------------------- #
# Function codes
_FC_READ_COILS = 0x01
_FC_READ_DISCRETE = 0x02
_FC_READ_HOLDING = 0x03
_FC_READ_INPUT = 0x04
_FC_WRITE_COIL = 0x05
_FC_WRITE_REGISTER = 0x06
_FC_WRITE_COILS = 0x0F
_FC_WRITE_REGISTERS = 0x10

_KIND_FC_READ = {"coil": _FC_READ_COILS, "discrete": _FC_READ_DISCRETE,
                 "holding": _FC_READ_HOLDING, "input": _FC_READ_INPUT}


def modbus_build_pdu(fc: int, addr: int, arg) -> bytes:
    """Build a Modbus request PDU (function code + data). Pure — unit-tested.

    *arg* is a count (reads / multi-writes take a count) or a value (single writes)."""
    if fc in (_FC_READ_COILS, _FC_READ_DISCRETE, _FC_READ_HOLDING, _FC_READ_INPUT):
        return struct.pack(">BHH", fc, addr, int(arg))
    if fc == _FC_WRITE_COIL:
        return struct.pack(">BHH", fc, addr, 0xFF00 if arg else 0x0000)
    if fc == _FC_WRITE_REGISTER:
        return struct.pack(">BHH", fc, addr, int(arg) & 0xFFFF)
    if fc == _FC_WRITE_COILS:
        vals = list(arg)
        nbytes = (len(vals) + 7) // 8
        buf = bytearray(nbytes)
        for i, v in enumerate(vals):
            if v:
                buf[i // 8] |= 1 << (i % 8)
        return struct.pack(">BHHB", fc, addr, len(vals), nbytes) + bytes(buf)
    if fc == _FC_WRITE_REGISTERS:
        vals = [int(v) & 0xFFFF for v in arg]
        return struct.pack(">BHHB", fc, addr, len(vals), len(vals) * 2) + b"".join(
            struct.pack(">H", v) for v in vals)
    raise ValueError("unsupported function code 0x%02X" % fc)


def modbus_parse_response(fc: int, pdu: bytes):
    """Parse a Modbus response PDU for request function code *fc*. Pure.

    Returns a list (reads) or True (writes). Raises :class:`CommError` on a Modbus
    exception response (function code with the high bit set)."""
    if not pdu:
        raise CommError("empty Modbus response")
    resp_fc = pdu[0]
    if resp_fc == (fc | 0x80):
        exc = pdu[1] if len(pdu) > 1 else 0
        raise CommError("Modbus exception 0x%02X for FC 0x%02X" % (exc, fc))
    if resp_fc != fc:
        raise CommError("Modbus FC mismatch: sent 0x%02X got 0x%02X" % (fc, resp_fc))
    if fc in (_FC_READ_COILS, _FC_READ_DISCRETE):
        n = pdu[1]
        bits = []
        for byte in pdu[2:2 + n]:
            bits.extend((byte >> i) & 1 for i in range(8))
        return [bool(b) for b in bits]
    if fc in (_FC_READ_HOLDING, _FC_READ_INPUT):
        n = pdu[1]
        data = pdu[2:2 + n]
        return [struct.unpack(">H", data[i:i + 2])[0] for i in range(0, len(data), 2)]
    return True                                        # write echoes -> ok


class ModbusTcpChannel(Channel):
    """A built-in Modbus-TCP client (no third-party library).

    Uniform API: ``read(kind, addr, count)`` with *kind* ∈
    {"coil","discrete","holding","input"} → list; ``write(kind, addr, value)`` with
    *kind* ∈ {"coil","holding"} and *value* a bool/int or a list → True.
    """

    def __init__(self, host="127.0.0.1", port=502, unit=1, timeout=3.0, connect=True):
        self.host, self.port, self.unit = host, int(port), int(unit)
        self.timeout = float(timeout)
        self.sock = None
        self._tid = 0
        if connect:
            self.open()

    def open(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        return self

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def _transact(self, pdu: bytes) -> bytes:
        self._tid = (self._tid + 1) & 0xFFFF
        frame = struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unit) + pdu
        self.sock.sendall(frame)
        header = self._recv_exactly(7)                 # MBAP header
        tid, proto, length, unit = struct.unpack(">HHHB", header)
        body = self._recv_exactly(length - 1)          # length counts the unit byte
        return body

    def _recv_exactly(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise CommError("Modbus connection closed mid-frame")
            buf += chunk
        return buf

    def read(self, kind="holding", addr=0, count=1):
        if kind not in _KIND_FC_READ:
            raise ValueError("read kind must be one of %s" % list(_KIND_FC_READ))
        fc = _KIND_FC_READ[kind]
        resp = self._transact(modbus_build_pdu(fc, addr, count))
        vals = modbus_parse_response(fc, resp)
        return vals[:count]

    def write(self, kind="holding", addr=0, value=0):
        if kind == "coil":
            if isinstance(value, (list, tuple)):
                fc = _FC_WRITE_COILS
            else:
                fc = _FC_WRITE_COIL
        elif kind == "holding":
            if isinstance(value, (list, tuple)):
                fc = _FC_WRITE_REGISTERS
            else:
                fc = _FC_WRITE_REGISTER
        else:
            raise ValueError("write kind must be 'coil' or 'holding'")
        resp = self._transact(modbus_build_pdu(fc, addr, value))
        return modbus_parse_response(fc, resp)


class ModbusTcpServer:
    """A tiny in-process Modbus-TCP **simulator** (threaded) for tests & dev.

    Serves a coil map and a holding-register map so you can exercise a
    pipeline→PLC handshake without hardware. Start it, point a
    :class:`ModbusTcpChannel` at ``(host, port)``, and stop it when done::

        srv = ModbusTcpServer(port=0); srv.start()           # port 0 = auto
        ch = ModbusTcpChannel("127.0.0.1", srv.port)
        ...
        srv.stop()

    Supports FC 1–6, 15, 16. Not a full Modbus stack — a faithful stand-in for the
    common coil/register reads and writes.
    """

    def __init__(self, host="127.0.0.1", port=0, coils=None, registers=None):
        self.host = host
        self.port = int(port)
        self.coils = dict(coils or {})
        self.registers = dict(registers or {})
        self._srv = None
        self._thread = None
        self._stop = False

    def start(self):
        import threading
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((self.host, self.port))
        self.port = self._srv.getsockname()[1]
        self._srv.listen(4)
        self._srv.settimeout(0.3)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        return self

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self._srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                conn.settimeout(1.0)
                try:
                    while not self._stop:
                        header = self._recv(conn, 7)
                        if not header:
                            break
                        tid, proto, length, unit = struct.unpack(">HHHB", header)
                        pdu = self._recv(conn, length - 1)
                        if not pdu:
                            break
                        resp_pdu = self._handle(pdu)
                        frame = struct.pack(">HHHB", tid, 0, len(resp_pdu) + 1, unit) + resp_pdu
                        conn.sendall(frame)
                except (OSError, struct.error):
                    pass

    @staticmethod
    def _recv(conn, n):
        buf = b""
        while len(buf) < n:
            try:
                chunk = conn.recv(n - len(buf))
            except socket.timeout:
                return b""
            if not chunk:
                return b""
            buf += chunk
        return buf

    def _handle(self, pdu: bytes) -> bytes:
        fc = pdu[0]
        try:
            if fc in (_FC_READ_COILS, _FC_READ_DISCRETE):
                addr, count = struct.unpack(">HH", pdu[1:5])
                nbytes = (count + 7) // 8
                buf = bytearray(nbytes)
                for i in range(count):
                    if self.coils.get(addr + i, False):
                        buf[i // 8] |= 1 << (i % 8)
                return struct.pack(">BB", fc, nbytes) + bytes(buf)
            if fc in (_FC_READ_HOLDING, _FC_READ_INPUT):
                addr, count = struct.unpack(">HH", pdu[1:5])
                data = b"".join(struct.pack(">H", self.registers.get(addr + i, 0) & 0xFFFF)
                                for i in range(count))
                return struct.pack(">BB", fc, len(data)) + data
            if fc == _FC_WRITE_COIL:
                addr, val = struct.unpack(">HH", pdu[1:5])
                self.coils[addr] = (val == 0xFF00)
                return pdu[:5]
            if fc == _FC_WRITE_REGISTER:
                addr, val = struct.unpack(">HH", pdu[1:5])
                self.registers[addr] = val
                return pdu[:5]
            if fc == _FC_WRITE_COILS:
                addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
                data = pdu[6:6 + nbytes]
                for i in range(count):
                    self.coils[addr + i] = bool((data[i // 8] >> (i % 8)) & 1)
                return struct.pack(">BHH", fc, addr, count)
            if fc == _FC_WRITE_REGISTERS:
                addr, count, nbytes = struct.unpack(">HHB", pdu[1:6])
                data = pdu[6:6 + nbytes]
                for i in range(count):
                    self.registers[addr + i] = struct.unpack(">H", data[2 * i:2 * i + 2])[0]
                return struct.pack(">BHH", fc, addr, count)
        except struct.error:
            pass
        return struct.pack(">BB", fc | 0x80, 0x01)     # illegal function

    def stop(self):
        self._stop = True
        if self._srv is not None:
            try:
                self._srv.close()
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)


# --------------------------------------------------------------------------- #
# Optional adapters — lazy factories that name the pip package they need
# --------------------------------------------------------------------------- #
def _optional_factory(name, module, pip, builder):
    def factory(**opts):
        import importlib
        try:
            mod = importlib.import_module(module)
        except Exception as e:
            raise CommError("protocol %r needs '%s' (pip install %s): %s"
                            % (name, module, pip, e))
        return builder(mod, **opts)
    return factory


class _SerialChannel(Channel):
    def __init__(self, serial_mod, port="COM1", baudrate=9600, timeout=1.0, **kw):
        self.ser = serial_mod.Serial(port=port, baudrate=int(baudrate), timeout=float(timeout), **kw)

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.ser.write(data)

    def receive(self, n=4096):
        return self.ser.read(n)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


# ---- native transports (real uniform-Channel adapters, work out of the box) -- #
register("tcp", lambda **o: TcpChannel(**o), native=True, desc="raw TCP client socket")
register("udp", lambda **o: UdpChannel(**o), native=True, desc="UDP socket")
register("http", lambda **o: HttpChannel(**o), native=True, desc="HTTP/REST client")
register("modbus-tcp", lambda **o: ModbusTcpChannel(**o), native=True,
         desc="Modbus TCP client (PLC / I-O; built-in, no deps)")
# serial has a real uniform-Channel adapter, gated on pyserial
register("serial",
         _optional_factory("serial", "serial", "pyserial",
                           lambda mod, **o: _SerialChannel(mod, **o)),
         native=False, pip="pyserial", kind="optional", probe="serial",
         desc="RS-232/485 serial port (send/receive)")


# ---- cataloged protocols (comprehensive menu; a first-class Channel adapter is
# on the roadmap — capabilities() reports them so you know the exact lib + kind).
def _cataloged_factory(name, pip, module):
    def factory(**opts):
        avail = _importable(module) if module else False
        if not avail and pip:
            raise CommError("protocol %r needs '%s' (pip install %s)" % (name, module, pip))
        raise CommError(
            "protocol %r is cataloged: install '%s' and use the %r client directly, "
            "or see docs/CONNECTIVITY.md — a first-class Fullseye Channel adapter is "
            "on the roadmap." % (name, pip, module))
    return factory


# (name, module-to-probe, pip, kind, one-line desc)
_CATALOG = [
    # --- IIoT / messaging ---
    ("mqtt", "paho.mqtt.client", "paho-mqtt", "optional", "MQTT pub/sub (IIoT broker)"),
    ("opcua", "asyncua", "asyncua", "optional", "OPC-UA client (industrial servers)"),
    ("sparkplug", "pysparkplug", "pysparkplug", "optional", "Sparkplug B over MQTT"),
    ("websocket", "websocket", "websocket-client", "optional", "WebSocket client"),
    ("zmq", "zmq", "pyzmq", "optional", "ZeroMQ messaging"),
    # --- PLC / fieldbus (register/tag read-write) ---
    ("modbus-rtu", "pymodbus", "pymodbus", "optional", "Modbus RTU (serial) via pymodbus"),
    ("ethernet-ip", "pycomm3", "pycomm3", "optional", "EtherNet/IP + CIP (Allen-Bradley Logix)"),
    ("s7", "snap7", "python-snap7", "optional", "Siemens S7 (S7comm) — DB/Merker/I/O"),
    ("slmp", "pymcprotocol", "pymcprotocol", "optional", "Mitsubishi MC protocol / SLMP (MELSEC)"),
    ("fins", "fins", "fins-driver", "optional", "Omron FINS (CIO/DM areas)"),
    ("bacnet", "BAC0", "BAC0", "optional", "BACnet/IP (building automation)"),
    ("can", "can", "python-can", "optional", "raw CAN bus"),
    # --- scaffold (special hardware / real-time / native SDK) ---
    ("ethercat", "pysoem", "pysoem", "scaffold", "EtherCAT master (RT NIC + slaves; the motion bus)"),
    ("profinet", "pnio_dcp", "pnio-dcp", "scaffold", "PROFINET DCP commissioning (RT via gateway)"),
    ("profibus", "pyprofibus", "pyprofibus", "scaffold", "PROFIBUS DP (RS-485 PHY, GSD)"),
    ("dnp3", "pydnp3", "pydnp3", "scaffold", "DNP3 / IEEE 1815 (SCADA/utility)"),
    ("iec61850", "iec61850", "pyiec61850-ng", "scaffold", "IEC 61850 MMS/GOOSE (substation)"),
    ("cclink", None, None, "scaffold", "CC-Link IE (no pure-python master; reach via SLMP)"),
]
for _name, _module, _pip, _kind, _desc in _CATALOG:
    register(_name, _cataloged_factory(_name, _pip, _module),
             native=False, pip=_pip, kind=_kind, probe=_module, desc=_desc)
