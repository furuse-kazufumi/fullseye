# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ``poc_nir_silicon_transmission`` 第 7 章のダイ写真(CC BY 3.0)を repo の外へ取得し、SHA-256 で固定する。

使い方::

    py -3.11 tools/fetch_die_photo.py

置き場は PoC の :func:`die_photo_dir`(上書きは ``FULLSEYE_DIE_PHOTO_DATA``)。URL・バイト数・SHA-256 も
PoC の定数を読む(二重に書かない)。CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。取得中は ``.part`` に
書き、バイト数と SHA-256 の両方が一致したときだけ本来の名前へ移す(fail-closed)。写真は repo に入れない。
出典表示: ZeptoBars (Mikhail Svarichevsky), Wikimedia Commons, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0)
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _poc():
    path = ROOT / "examples" / "poc_nir_silicon_transmission.py"
    spec = importlib.util.spec_from_file_location("poc_nir_silicon_transmission", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        print("CI / FULLSEYE_OFFLINE=1 ではダイ写真を取得しない")
        return 0
    poc = _poc()
    target = poc.die_photo_dir() / poc.DIE_PHOTO_FILE
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == poc.DIE_PHOTO_SHA256:
        print("取得済み:", target)
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(poc.DIE_PHOTO_URL, headers={"User-Agent": "fullseye-realdata/1 (research)"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        blob = resp.read()
    got = hashlib.sha256(blob).hexdigest()
    if len(blob) != poc.DIE_PHOTO_BYTES or got != poc.DIE_PHOTO_SHA256:
        print("取得物が固定した値と違う(%d byte、sha256 %s)。置かない。" % (len(blob), got), file=sys.stderr)
        return 1
    with open(part, "wb") as fh:
        fh.write(blob)
    part.replace(target)
    print("取得:", target, "(%d byte、sha256 %s)" % (len(blob), got))
    print(poc.DIE_PHOTO_CREDIT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
