# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""幅 390 px の headless Chrome で、pocviewer のページの全タブ × 全言語の横はみ出しを測る(手で回す門)。

    py -3.11 tools/check_page_overflow.py docs/anim3d/itokawa_gravity.html [width]

ページの写しに計測の script を足し、結果を 127.0.0.1 の一時的な HTTP の受け口へ POST させる(Windows の chrome.exe は
起動役がすぐ戻るので標準出力は使えない)。Chrome は finally で必ず止める。
出力: はみ出した (言語, タブ) と、右へはみ出した要素(最大 6 個)。どこかで scrollWidth > clientWidth なら exit 1。
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

def chrome_path():
    """Chrome の実行ファイル(環境変数 FULLSEYE_CHROME、無ければ Windows の既定の場所)。見つからなければ None。"""
    c = os.environ.get("FULLSEYE_CHROME")
    if c and Path(c).exists():
        return c
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            p = Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if p.exists():
                return str(p)
    return None
PROBE = r"""
<script>
setTimeout(() => {
 try {
  const out = [];
  const sel = document.getElementById('lang');
  const langs = Array.from(sel.options).map(o => o.value);
  for (const l of langs) {
    sel.value = l; sel.dispatchEvent(new Event('change'));
    const n = document.querySelectorAll('#tabs .tab').length;
    for (let i = 0; i < n; i++) {
      const b = document.querySelectorAll('#tabs .tab')[i]; const id = b.dataset.id; b.click();
      const cw = document.documentElement.clientWidth, sw = document.documentElement.scrollWidth;
      const bad = [];
      if (sw > cw) {
        document.querySelectorAll('body *').forEach(e => {
          const r = e.getBoundingClientRect();
          if (r.width > 0 && r.right > cw + 1 && bad.length < 6) {
            bad.push((e.id ? '#' + e.id : e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : '')) +
                     ' w=' + Math.round(r.width) + ' r=' + Math.round(r.right) + ' "' + (e.textContent || '').slice(0, 30).replace(/\s+/g, ' ') + '"');
          }
        });
      }
      out.push({l, id, sw, cw, bad});
    }
  }
  fetch('http://127.0.0.1:__PORT__/', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify(out)});
 } catch (e) { fetch('http://127.0.0.1:__PORT__/', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify([{err: String(e)}])}); }
}, 1500);
</script>
"""
GOT = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        GOT["body"] = self.rfile.read(n).decode("utf-8")
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


def check(page, W=390):
    """page を幅 W の iframe に入れて、全言語 × 全タブの (言語, タブ, scrollWidth, clientWidth, はみ出した要素) を返す。"""
    CHROME = chrome_path()
    if CHROME is None:
        raise RuntimeError("Chrome が見つからない(FULLSEYE_CHROME で指定)")
    GOT.clear()
    PAGE = Path(page).resolve()
    html = PAGE.read_text(encoding="utf-8")
    assert html.rstrip().endswith("</html>")
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    probe_html = html.rstrip()[:-len("</html>")] + PROBE.replace("__PORT__", str(port)) + "</html>" + chr(10)
    tmpd = Path(tempfile.mkdtemp(prefix="ovf_"))
    tp0 = tmpd / "probe.html"
    tp0.write_text(probe_html, encoding="utf-8")
    # headless の窓は幅 500 px 前後より狭くならない(実測 511)ので、幅 W の iframe に入れて本当の W で組ませる
    tp = tmpd / "wrap.html"
    tp.write_text('<!doctype html><html><body style="margin:0"><iframe src="probe.html" style="width:%dpx;height:2400px;border:0">'
                  '</iframe></body></html>' % W, encoding="utf-8")
    prof = tmpd / "prof"
    p = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                          "--user-data-dir=" + str(prof), "--window-size=%d,2500" % max(W + 40, 600), tp.as_uri()],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        t0 = time.time()
        while time.time() - t0 < 180 and "body" not in GOT:
            time.sleep(1.0)
    finally:
        if p.poll() is None:
            p.kill()
        ps = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*%s*' } | "
              "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % tmpd.name)
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=60)
        srv.shutdown()
    if "body" not in GOT:
        raise RuntimeError("計測の結果が届かない(ページが読み込めない・script が止まった)")
    rows = json.loads(GOT["body"])
    if rows and "err" in rows[0]:
        raise RuntimeError("計測の script が失敗: %s" % rows[0]["err"])
    return rows


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = check(argv[0], int(argv[1]) if len(argv) > 1 else 390)
    fail = 0
    for row in rows:
        flag = row["sw"] > row["cw"]
        fail += flag
        if flag or os.environ.get("ALL"):
            print(row["l"], row["id"], row["sw"], row["cw"], " | ".join(row["bad"]))
    print("rows", len(rows), "overflow", fail)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
