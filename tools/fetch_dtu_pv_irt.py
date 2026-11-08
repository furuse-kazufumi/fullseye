# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""DTU の PV 発電所のドローン熱画像(CC BY 4.0)を repo 外へ取得し、SHA-256 で固定して展開する。

使い方::

    py -3.11 tools/fetch_dtu_pv_irt.py [置き場]

``examples/poc_pv_thermal_survey.py`` の実データの章がこれを読む(無ければその章だけ飛ばし、
合成の章は全部走る)。既定の置き場は :func:`realdata.dtu_pv_irt_cache`(上書きは
``FULLSEYE_PV_IRT_DATA``)。展開には 7-Zip(``7z`` が PATH にあるか、``FULLSEYE_7Z`` でその実行
ファイルを指す)を使い、温度の ``.raw`` と表示用の ``.png``、IV 曲線の ``.csv`` だけを取り出す
(EL の ``.nef`` は使わない)。

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。取得物は ``.part`` に書き、バイト数と
SHA-256 が :data:`realdata.DTU_PV_IRT_SHA256` に一致したときだけ本名にする。置き場にすでに違う
中身のアーカイブがあれば上書きせず止まる。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import realdata  # noqa: E402

#: ライセンス: figshare API(https://api.figshare.com/v2/articles/29665346)の license 欄の文言は
#: "CC BY 4.0"(url https://creativecommons.org/licenses/by/4.0/)。配布ページ本体は 2026-11-08 に 403 で読めず、
#: 展開物の README にもライセンスの記述は無い。図と印字の帰属表記は realdata.dtu_pv_irt_credit()、改変(面積平均・
#: 中央値からの差・色付け・判定の枠)は PoC の図のキャプションに書く。
#: figshare の固定ファイル番号(DTU Data の記事 29665346 の ``IRT DATASET.7z``)。
DTU_PV_IRT_URL = "https://ndownloader.figshare.com/files/56632355"
ARCHIVE = "IRT_DATASET.7z"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _seven_zip() -> str:
    exe = os.environ.get("FULLSEYE_7Z", "").strip() or shutil.which("7z") or shutil.which("7za")
    if not exe:
        raise SystemExit("7-Zip が見つからない。PATH に 7z を置くか FULLSEYE_7Z で実行ファイルを指す")
    return exe


def fetch(dest: Path | None = None) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    dest = Path(dest) if dest is not None else realdata.dtu_pv_irt_cache()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / ARCHIVE
    if target.exists():
        if target.stat().st_size != realdata.DTU_PV_IRT_BYTES or _sha256(target) != realdata.DTU_PV_IRT_SHA256:
            raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % target)
        print("ok    %s" % ARCHIVE)
    else:
        part = target.with_name(target.name + ".part")
        request = urllib.request.Request(DTU_PV_IRT_URL, headers={"User-Agent": "fullseye-realdata/1"})
        with urllib.request.urlopen(request, timeout=300) as resp, part.open("wb") as out:
            if not resp.geturl().startswith("https://"):
                raise SystemExit("https 以外へ転送された: %s" % resp.geturl())
            total = 0
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                total += len(block)
                if total > realdata.DTU_PV_IRT_BYTES:
                    break
                out.write(block)
        if total != realdata.DTU_PV_IRT_BYTES or _sha256(part) != realdata.DTU_PV_IRT_SHA256:
            part.unlink(missing_ok=True)
            raise SystemExit("%s のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)" % ARCHIVE)
        part.replace(target)
        print("fetch %s (%d bytes)" % (ARCHIVE, total))
    out_dir = dest / "extracted"
    if not (out_dir / "IRT DATASET").is_dir():
        subprocess.run([_seven_zip(), "x", str(target), "-o" + str(out_dir), "-r", "-y",
                        "*.raw", "*.png", "*.csv"], check=True, stdout=subprocess.DEVNULL)
    root = realdata.dtu_pv_irt_root(required=True)
    n = sum(1 for _ in root.glob("*/*/IRT/*.raw"))
    print("置き場: %s(温度の .raw %d 枚)" % (root, n))
    return root


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
