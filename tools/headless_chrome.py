# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""headless Chrome を DevTools プロトコル(CDP)で動かす最小の道具(標準ライブラリだけ・websocket も自前)。

門(ブラウザの描画と numpy の描画の突き合わせ)とスクショに使う。使い方::

    with HeadlessChrome() as ch:                      # 抜けると必ず閉じる(try/finally + 残ったプロセスを殺す)
        ch.open("file:///.../view.html?gate=1", width=320, height=240)
        ch.wait_for("window.__gs && window.__gs.ready", timeout=60)
        png = ch.screenshot()                         # PNG のバイト列
        n = ch.eval("window.__gsStats.buffers")

★Windows の chrome.exe は起動すると自分を起こし直して親がすぐ終わる(``--screenshot`` の出力は親が終わった後に
書かれる、2026-10-25 実測)。だから終わりを待たず、``DevToolsActivePort``(``--remote-debugging-port=0`` が
プロファイルの下に書く)を待って繋ぐ。閉じるときは Browser.close を送り、残ったプロセスはプロファイルの
ディレクトリ名でコマンドラインを引いて殺す(他人の Chrome は触らない)。
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str | None:
    """Chrome / Chromium の実行ファイル(環境変数 ``FULLSEYE_CHROME`` が最優先)。無ければ None。"""
    env = os.environ.get("FULLSEYE_CHROME")
    if env and os.path.exists(env):
        return env
    for c in _CANDIDATES:
        if os.path.exists(c):
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        p = shutil.which(n)
        if p:
            return p
    return None


class _WS:
    """RFC 6455 の最小の client(テキストの送受信だけ、マスクつき送信、分割フレームの結合)。"""

    def __init__(self, url: str, timeout: float = 60.0):
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key))
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake closed")
            buf += chunk
        head, self._rest = buf.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("websocket handshake failed: %r" % head[:200])

    def _read(self, n: int) -> bytes:
        out = self._rest[:n]
        self._rest = self._rest[n:]
        while len(out) < n:
            chunk = self.sock.recv(max(65536, n - len(out)))
            if not chunk:
                raise ConnectionError("websocket closed")
            out += chunk
        if len(out) > n:
            self._rest = out[n:] + self._rest
            out = out[:n]
        return out

    def send(self, text: str) -> None:
        data = text.encode()
        hdr = bytearray([0x81])
        n = len(data)
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        hdr += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data)) if n < 4096 else _xor(data, mask)
        self.sock.sendall(bytes(hdr) + masked)

    def recv(self) -> str:
        parts = []
        while True:
            b0, b1 = self._read(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            if b1 & 0x80:
                self._read(4)                       # サーバはマスクしない(しても読み捨てない作法は不要)
            payload = self._read(n)
            if op == 0x8:
                raise ConnectionError("websocket closed by peer")
            if op in (0x9, 0xA):                    # ping / pong は無視
                continue
            parts.append(payload)
            if b0 & 0x80:
                return b"".join(parts).decode("utf-8", "replace")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def _xor(data: bytes, mask: bytes) -> bytes:
    import numpy as np
    a = np.frombuffer(data, np.uint8)
    m = np.resize(np.frombuffer(mask, np.uint8), a.size)
    return (a ^ m).tobytes()


class HeadlessChrome:
    """1 つのタブを持つ headless Chrome。``with`` で使う(抜けると閉じ、プロファイルを消す)。"""

    def __init__(self, exe: str | None = None, *, swiftshader: bool = True, timeout: float = 60.0):
        self.exe = exe or find_chrome()
        if not self.exe:
            raise FileNotFoundError("Chrome / Chromium not found (set FULLSEYE_CHROME)")
        self.timeout = timeout
        self.swiftshader = swiftshader
        self.prof = None
        self.ws = None
        self._id = 0
        self.console = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def start(self) -> None:
        self.prof = tempfile.mkdtemp(prefix="fs_chrome_")
        args = [self.exe, "--headless=new", "--remote-debugging-port=0", "--user-data-dir=" + self.prof,
                "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--allow-file-access-from-files", "about:blank"]
        if self.swiftshader:
            args[1:1] = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
        kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        self.proc = subprocess.Popen(args, **kw)
        port_file = Path(self.prof) / "DevToolsActivePort"
        t0 = time.time()
        while not (port_file.exists() and port_file.read_text(errors="replace").strip()):
            if time.time() - t0 > self.timeout:
                raise TimeoutError("Chrome did not open its DevTools port")
            time.sleep(0.05)
        port = int(port_file.read_text().split()[0])
        t0 = time.time()
        while True:
            try:
                tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=5).read())
                page = [t for t in tabs if t.get("type") == "page"]
                if page:
                    break
            except OSError:
                pass
            if time.time() - t0 > self.timeout:
                raise TimeoutError("no page target")
            time.sleep(0.05)
        self.ws = _WS(page[0]["webSocketDebuggerUrl"], timeout=self.timeout)
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self, method: str, **params):
        self._id += 1
        my = self._id
        self.ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("method") == "Runtime.consoleAPICalled":
                self.console.append(" ".join(str(a.get("value", a.get("description", ""))) for a in m["params"].get("args", [])))
            elif m.get("method") == "Runtime.exceptionThrown":
                self.console.append("EXC " + json.dumps(m["params"].get("exceptionDetails", {}))[:400])
            if m.get("id") == my:
                if "error" in m:
                    raise RuntimeError("%s: %s" % (method, m["error"]))
                return m.get("result", {})

    def open(self, url: str, *, width: int = 1280, height: int = 800, mobile: bool = False) -> None:
        self.call("Emulation.setDeviceMetricsOverride", width=int(width), height=int(height), deviceScaleFactor=1,
                  mobile=bool(mobile))
        if mobile:
            self.call("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=2)
        self.call("Page.navigate", url=url)

    def eval(self, expr: str):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError("JS: %s" % json.dumps(r["exceptionDetails"])[:500])
        return r.get("result", {}).get("value")

    def wait_for(self, expr: str, timeout: float = 60.0, poll: float = 0.1):
        t0 = time.time()
        while True:
            try:
                v = self.eval("(() => { try { return !!(%s); } catch (e) { return false; } })()" % expr)
            except RuntimeError:
                v = False
            if v:
                return True
            if time.time() - t0 > timeout:
                raise TimeoutError("timed out waiting for %s (console: %s)" % (expr, self.console[-5:]))
            time.sleep(poll)

    def screenshot(self) -> bytes:
        r = self.call("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        return base64.b64decode(r["data"])

    def close(self) -> None:
        try:
            if self.ws is not None:
                try:
                    self._id += 1
                    self.ws.send(json.dumps({"id": self._id, "method": "Browser.close", "params": {}}))
                except OSError:
                    pass
                self.ws.close()
        finally:
            self.ws = None
            try:
                if getattr(self, "proc", None) is not None:
                    try:
                        self.proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.proc.kill()
                _kill_by_profile(self.prof)
            finally:
                if self.prof:
                    for _ in range(20):
                        try:
                            shutil.rmtree(self.prof)
                            break
                        except OSError:
                            time.sleep(0.25)
                self.prof = None


def _kill_by_profile(prof: str | None) -> None:
    """プロファイルのディレクトリ名をコマンドラインに持つプロセスだけを殺す(他人の Chrome は触らない)。"""
    if not prof:
        return
    tag = os.path.basename(prof)
    if sys.platform.startswith("win"):
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*%s*' } "
              "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" % tag)
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    else:
        subprocess.run(["pkill", "-f", tag], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=30)


def file_url(path) -> str:
    return Path(path).resolve().as_uri()
