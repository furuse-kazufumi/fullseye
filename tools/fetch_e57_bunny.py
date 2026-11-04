# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""libE57 の公開試験点群(bunny × 6 型 + PTS 文字版)を repo 外へ取得し、SHA-256 で固定する。

使い方::

    py -3.11 tools/fetch_e57_bunny.py

``examples/poc_real_file_formats.py`` の E57 の章が、取得物があればこれを読む(無ければ同梱の
イトカワ形状で代える)。データの再配布の条件は配布元に書かれていないので repo には入れない。
既定の置き場は :func:`realdata.e57_bunny_cache`(上書きは ``FULLSEYE_E57_BUNNY_DATA``)。

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。各ファイルは ``.part`` に書き、
バイト数と SHA-256 が台帳 :data:`realdata.E57_BUNNY_FILES` に一致したときだけ本名にする。
置き場にすでに違う中身のファイルがあれば上書きせず止まる。
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import realdata  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(dest: Path | None = None) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    dest = Path(dest) if dest is not None else realdata.e57_bunny_cache()
    dest.mkdir(parents=True, exist_ok=True)
    for name, (size, digest) in realdata.E57_BUNNY_FILES.items():
        target = dest / name
        if target.exists():
            if target.stat().st_size == size and _sha256(target) == digest:
                print("ok    %s" % name)
                continue
            raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % target)
        part = target.with_name(target.name + ".part")
        request = urllib.request.Request(realdata.E57_BUNNY_URL % name,
                                         headers={"User-Agent": "fullseye-realdata/1"})
        with urllib.request.urlopen(request, timeout=120) as resp, part.open("wb") as out:
            if not resp.geturl().startswith("https://"):
                raise SystemExit("https 以外へ転送された: %s" % resp.geturl())
            total = 0
            while True:
                block = resp.read(1 << 16)
                if not block:
                    break
                total += len(block)
                if total > size:
                    break
                out.write(block)
        if total != size or _sha256(part) != digest:
            part.unlink(missing_ok=True)
            raise SystemExit("%s のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)" % name)
        part.replace(target)
        print("fetch %s (%d bytes)" % (name, size))
    realdata.e57_bunny_files(required=True)
    print("置き場: %s" % dest)
    return dest


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
