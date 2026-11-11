# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測のコーンビーム CT(クルミ 1 個、Der Sarkissian ほか 2019)の一部だけを repo 外へ取得する。

Get part of one walnut of the public cone-beam CT collection of Der Sarkissian et al. (2019).

配布物は Zenodo の 1 標本 6 GB の zip で、全部は要らない。zip の中央ディレクトリを HTTP の
Range 要求で読み、使う要素だけを取り出す(1 標本・中段の軌道 tubeV2・4 枚に 1 枚の投影 300 枚・
同じ角度の撮り直し 1 枚・暗電流と白の画像・幾何・配布元の参照再構成 2 種 501 枚ずつ)。合計およそ 1.1 GB。

The Zenodo record ships one walnut as a 6 GB zip. This reads the zip's central directory by
HTTP Range requests and extracts only the members the PoC uses (walnut 1, the middle orbit
tubeV2, every 4th projection = 300 views, dark and flat fields, the geometry, and the two
reference reconstructions of 501 slices each), about 1.1 GB.

使い方 / usage::

    py -3.11 tools/fetch_walnut_cbct.py [置き場]

置き場の既定は :func:`realdata.walnut_cbct_cache`(上書きは ``FULLSEYE_WALNUT_CBCT_DATA``)。

fail-closed:

* CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。
* 各要素は zip の中央ディレクトリの CRC-32 と大きさで照合し、合わなければ捨てて止まる。
* 取り終えたら全要素の (名前, 大きさ, SHA-256) の一覧を書き、その SHA-256 が
  :data:`realdata.WALNUT_CBCT_MANIFEST_SHA256` と一致しなければ止まる。
* 置き場にすでに違う中身の要素があれば上書きしない。

取得は ``curl`` で行う(Zenodo は Python の urllib からの接続に応えないことがある。2026-11-07 に
手元で確認。``CONTRIBUTING.md`` にも Zenodo の API が応えない記録がある)。

ライセンス(配布元の記載のまま、https://zenodo.org/records/2686726 、2026-11-08 に確認。記録の
license id は ``cc-by-4.0``、法的な全文は https://creativecommons.org/licenses/by/4.0/legalcode):

    "Creative Commons Attribution 4.0 International"
    "The Creative Commons Attribution license allows re-distribution and re-use of a licensed work
    on the condition that the creator is appropriately credited."

帰属: Der Sarkissian, Lucka, van Eijnatten, Colacicco, Coban & Batenburg, "A cone-beam X-ray CT data
collection designed for machine learning", Sci. Data 6, 215 (2019), doi:10.1038/s41597-019-0235-y;
data doi:10.5281/zenodo.2686726。図と実行ログには :func:`realdata.walnut_cbct_credit` を載せる。
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import realdata  # noqa: E402


#: 1 要求あたりの試行回数と、失敗のあとの待ち[秒](Zenodo は混むと 429 を返す。待ちは試行ごとに倍)。
CURL_ATTEMPTS, CURL_BACKOFF_S = 8, 15.0


def _curl_range(url: str, a: int, b: int) -> bytes:
    """``url`` のバイト ``a .. b``(両端を含む)を返す。長さが合わなければ例外。

    失敗(429 などの HTTP エラー、途中切れ)は待って取り直す。:data:`CURL_ATTEMPTS` 回で諦める。
    """
    last = ""
    for attempt in range(CURL_ATTEMPTS):
        r = subprocess.run(["curl", "-s", "-L", "--fail", "--proto", "=https",
                            "-r", "%d-%d" % (a, b), url], capture_output=True, timeout=900)
        if r.returncode == 0 and len(r.stdout) == b - a + 1:
            return r.stdout
        last = "exit %d、長さ %d / %d" % (r.returncode, len(r.stdout), b - a + 1)
        time.sleep(CURL_BACKOFF_S * (2 ** min(attempt, 4)))
    raise OSError("curl が %d 回失敗した(%s): %s" % (CURL_ATTEMPTS, last, url))


class _RangeFile(io.RawIOBase):
    """遠くの zip を、末尾だけ手元に持ち、残りは Range 要求で読むファイル。"""

    def __init__(self, url: str, size: int, tail: int = 1 << 21):
        super().__init__()
        self.url, self.size, self.pos = url, size, 0
        self.t0 = max(0, size - tail)
        self.tail = _curl_range(url, self.t0, size - 1)

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        base = {0: 0, 1: self.pos, 2: self.size}[whence]
        self.pos = base + off
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        if self.pos >= self.t0:
            d = self.tail[self.pos - self.t0:self.pos - self.t0 + n]
        else:
            d = _curl_range(self.url, self.pos, self.pos + n - 1)
        self.pos += len(d)
        return d

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def wanted(names: list[str]) -> list[str]:
    """zip の要素名のうち、PoC が使うものだけを返す(数が台帳と合わなければ例外)。"""
    pre = "Walnut%d/" % realdata.WALNUT_CBCT_SAMPLE
    orbit = pre + "Projections/tubeV%d/" % realdata.WALNUT_CBCT_ORBIT
    keep = {orbit + n for n in ("scan_geom_corrected.geom", "di000000.tif", "io000000.tif",
                                "io000001.tif", "scan settings.txt", "data settings XRE.txt")}
    keep |= {orbit + "scan_%06d.tif" % i for i in realdata.walnut_cbct_projection_indices()}
    keep.add(orbit + "scan_%06d.tif" % realdata.WALNUT_CBCT_REPEAT_INDEX)
    for name in realdata.WALNUT_CBCT_RECONSTRUCTIONS:
        keep |= {pre + "Reconstructions/%s_%06d.tiff" % (name, k)
                 for k in range(realdata.WALNUT_CBCT_REFERENCE_SLICES)}
    have = set(names)
    missing = sorted(keep - have)
    if missing:
        raise SystemExit("zip に無い要素が %d 個(先頭 %s)" % (len(missing), missing[:3]))
    return sorted(keep)


def _member_bytes(url: str, info: zipfile.ZipInfo) -> bytes:
    """1 要素を Range で取り、展開して CRC-32 と大きさを照合する。"""
    head = _curl_range(url, info.header_offset, info.header_offset + 29)
    sig, _v, _f, method, _t, _d, _crc, _cs, _us, n_name, n_extra = struct.unpack("<IHHHHHIIIHH", head)
    if sig != 0x04034B50:
        raise OSError("%s: 局所ヘッダの署名が違う" % info.filename)
    start = info.header_offset + 30 + n_name + n_extra
    blob = _curl_range(url, start, start + info.compress_size - 1)
    if method == zipfile.ZIP_DEFLATED:
        raw = zlib.decompress(blob, -15)
    elif method == zipfile.ZIP_STORED:
        raw = blob
    else:
        raise OSError("%s: 圧縮方式 %d は扱わない" % (info.filename, method))
    if len(raw) != info.file_size or (zlib.crc32(raw) & 0xFFFFFFFF) != info.CRC:
        raise OSError("%s: 大きさ / CRC-32 が中央ディレクトリと違う" % info.filename)
    return raw


def fetch(dest: Path | None = None, workers: int = 4) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    if shutil.which("curl") is None:
        raise SystemExit("curl が無い")
    dest = Path(dest) if dest is not None else realdata.walnut_cbct_cache()
    dest.mkdir(parents=True, exist_ok=True)
    url = realdata.WALNUT_CBCT_URL
    zf = zipfile.ZipFile(_RangeFile(url, realdata.WALNUT_CBCT_ZIP_BYTES))
    infos = {i.filename: i for i in zf.infolist()}
    names = wanted(list(infos))
    print("要素 %d 個(zip 全体は %d 個)" % (len(names), len(infos)))

    def one(name: str) -> str:
        target = dest / name
        info = infos[name]
        if target.is_file():
            raw = target.read_bytes()
            if len(raw) == info.file_size and (zlib.crc32(raw) & 0xFFFFFFFF) == info.CRC:
                return "ok"
            raise SystemExit("%s が中央ディレクトリと違う中身で在る。消してから取り直す" % target)
        raw = _member_bytes(url, info)
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_name(target.name + ".part")
        part.write_bytes(raw)
        part.replace(target)
        return "fetch"

    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in ex.map(one, names):
            done += 1
            if done % 100 == 0:
                print("  %d / %d" % (done, len(names)), flush=True)
    manifest = realdata.walnut_cbct_write_manifest(dest, names)
    print("一覧の SHA-256: %s" % manifest)
    realdata.walnut_cbct_root(required=True, root=dest)
    print("置き場: %s" % dest)
    return dest


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
