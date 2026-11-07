# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""NACA TN 898(1943 年のタイプ打ちの技術報告)の PDF を NASA NTRS から repo 外へ取得し、SHA-256 で固定する。

使い方::

    py -3.11 tools/fetch_naca_tn898.py            # 既定の置き場へ
    py -3.11 tools/fetch_naca_tn898.py <置き場>    # 置き場を指定(FULLSEYE_NACA_TN898_DATA と同じ意味)

``examples/poc_real_typewritten_ocr.py`` が取得物を読む(無ければ scikit-image の ``page`` の章だけを回し、
NACA の章は記録値を印字する)。NTRS の記録 19930084880 の著作権の欄は "Public Use Permitted"。
容量が 12 MB あるので repo には入れない。置き場の既定は PoC の :func:`naca_cache`。

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。``.part`` に書き、バイト数と SHA-256 が
PoC の台帳(``PDF_BYTES`` / ``PDF_SHA256``)に一致したときだけ本名にする。置き場にすでに違う中身の
ファイルがあれば上書きせず止まる。
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 取得元(NASA 技術報告サーバ NTRS の API。記録 19930084880 の PDF)。
NTRS_PDF_URL = "https://ntrs.nasa.gov/api/citations/19930084880/downloads/19930084880.pdf"


def _poc():
    """台帳(バイト数・SHA-256・置き場)は PoC の 1 か所にだけ置く。"""
    path = ROOT / "examples" / "poc_real_typewritten_ocr.py"
    spec = importlib.util.spec_from_file_location("poc_real_typewritten_ocr", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(dest: Path | None = None) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    poc = _poc()
    if dest is not None:
        os.environ["FULLSEYE_NACA_TN898_DATA"] = str(dest)
    dest = poc.naca_cache()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / poc.PDF_NAME
    if target.exists():
        if target.stat().st_size == poc.PDF_BYTES and _sha256(target) == poc.PDF_SHA256:
            print("ok    %s" % target)
            poc.load_naca_pages(required=True)
            return target
        raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % target)
    part = target.with_name(target.name + ".part")
    request = urllib.request.Request(NTRS_PDF_URL, headers={"User-Agent": "fullseye-realdata/1"})
    with urllib.request.urlopen(request, timeout=300) as resp, part.open("wb") as out:
        if not resp.geturl().startswith("https://"):
            raise SystemExit("https 以外へ転送された: %s" % resp.geturl())
        total = 0
        while True:
            block = resp.read(1 << 16)
            if not block:
                break
            total += len(block)
            if total > poc.PDF_BYTES:
                break
            out.write(block)
    if total != poc.PDF_BYTES or _sha256(part) != poc.PDF_SHA256:
        part.unlink(missing_ok=True)
        raise SystemExit("取得した PDF のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)")
    part.replace(target)
    poc.load_naca_pages(required=True)            # 頁ごとの JPEG の SHA-256 まで照合する
    print("fetch %s (%d bytes)" % (target, poc.PDF_BYTES))
    return target


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
