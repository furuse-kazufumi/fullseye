# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PLATEAU の配布 zip(数 GB)から必要な CityGML だけを HTTP Range で取り出す(全体を落とさない)。

zip の中央ディレクトリは末尾にあるので、(1) 末尾 2 MB を Range で取り EOCD(ZIP64 なら ZIP64 EOCD)を読む、(2) 中央ディレクトリ全体を
Range で取り、名前が合う項目を選ぶ、(3) 各項目のローカルヘッダ + 圧縮データを Range で取り zlib(raw deflate)で伸長する。
データは国土交通省 Project PLATEAU(公共データ利用規約 PDL1.0 = CC BY 4.0 互換)。出典表示: 「出典: 国土交通省 Project PLATEAU」。

Run: py -3.11 plateau_fetch.py <zip-url> <name-substring> <outdir>   例: ... 53394611_bldg C:/dev/data/plateau/chuo_2025
"""
from __future__ import annotations

import struct
import sys
import urllib.request
import zlib
from pathlib import Path


def _get(url: str, start: int, end: int) -> bytes:
    """[start, end] の閉区間を Range で取る。206 でなければ ValueError(全体が返るのは拒む)。"""
    req = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (start, end), "User-Agent": "fullseye-plateau-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status != 206:
            raise ValueError("server did not honour Range (status %d)" % r.status)
        return r.read()


def _size(url: str) -> int:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "fullseye-plateau-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if r.headers.get("Accept-Ranges", "").lower() != "bytes":
            raise ValueError("server does not advertise Accept-Ranges: bytes")
        return int(r.headers["Content-Length"])


def central_directory(url: str):
    """(項目の list, 全体サイズ)。項目 = {"name", "method", "csize", "usize", "offset"}。"""
    total = _size(url)
    tail_len = min(total, 2 * 1024 * 1024)
    tail = _get(url, total - tail_len, total - 1)
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise ValueError("EOCD not found in the last %d bytes" % tail_len)
    n_entries, cd_size, cd_off = struct.unpack("<HII", tail[i + 10:i + 20])
    if n_entries == 0xFFFF or cd_size == 0xFFFFFFFF or cd_off == 0xFFFFFFFF:
        j = tail.rfind(b"PK\x06\x07", 0, i)          # ZIP64 EOCD locator
        if j < 0:
            raise ValueError("ZIP64 locator not found")
        z64_off = struct.unpack("<Q", tail[j + 8:j + 16])[0]
        k = z64_off - (total - tail_len)
        rec = tail[k:k + 56] if k >= 0 else _get(url, z64_off, z64_off + 55)
        if rec[:4] != b"PK\x06\x06":
            raise ValueError("ZIP64 EOCD record not found")
        n_entries, cd_size, cd_off = struct.unpack("<QQQ", rec[32:56])
    cd = _get(url, cd_off, cd_off + cd_size - 1)
    entries, p = [], 0
    while p + 46 <= len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        method, csize, usize, nlen, xlen, clen = struct.unpack("<H", cd[p + 10:p + 12])[0], *struct.unpack("<II", cd[p + 20:p + 28]), *struct.unpack("<HHH", cd[p + 28:p + 34])
        off = struct.unpack("<I", cd[p + 42:p + 46])[0]
        name = cd[p + 46:p + 46 + nlen].decode("utf-8", "replace")
        extra = cd[p + 46 + nlen:p + 46 + nlen + xlen]
        if 0xFFFFFFFF in (csize, usize, off):
            q = 0
            while q + 4 <= len(extra):
                hid, hlen = struct.unpack("<HH", extra[q:q + 4])
                if hid == 0x0001:
                    vals, r = [], q + 4
                    for v in (usize, csize, off):
                        if v == 0xFFFFFFFF:
                            vals.append(struct.unpack("<Q", extra[r:r + 8])[0]); r += 8
                        else:
                            vals.append(v)
                    usize, csize, off = vals
                    break
                q += 4 + hlen
        entries.append({"name": name, "method": method, "csize": csize, "usize": usize, "offset": off})
        p += 46 + nlen + xlen + clen
    if len(entries) != n_entries:
        raise ValueError("central directory parsed %d entries, expected %d" % (len(entries), n_entries))
    return entries, total


def fetch_entry(url: str, e: dict, out: Path) -> Path:
    head = _get(url, e["offset"], e["offset"] + 29)
    if head[:4] != b"PK\x03\x04":
        raise ValueError("local header not found for %s" % e["name"])
    nlen, xlen = struct.unpack("<HH", head[26:30])
    start = e["offset"] + 30 + nlen + xlen
    data = _get(url, start, start + e["csize"] - 1)
    if e["method"] == 8:
        data = zlib.decompress(data, -15)
    elif e["method"] != 0:
        raise ValueError("unsupported compression method %d for %s" % (e["method"], e["name"]))
    if len(data) != e["usize"]:
        raise ValueError("size mismatch for %s: %d != %d" % (e["name"], len(data), e["usize"]))
    dst = out / Path(e["name"]).name
    dst.write_bytes(data)
    return dst


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    url, needle, out = argv[1], argv[2], Path(argv[3])
    out.mkdir(parents=True, exist_ok=True)
    entries, total = central_directory(url)
    print("zip %.2f GB, %d entries" % (total / 1e9, len(entries)))
    # 名前の一致は gml 本体だけ(appearance のテクスチャ数千枚と、サイズ 0 のディレクトリ項目は除く)
    hits = [e for e in entries if needle in Path(e["name"]).name and e["name"].lower().endswith(".gml") and e["csize"] > 0]
    for e in hits:
        print("  %s  %.1f MB (stored %.1f MB)" % (e["name"], e["usize"] / 1e6, e["csize"] / 1e6))
    if not hits:
        sample = [e["name"] for e in entries if "/bldg/" in e["name"]][:5]
        raise SystemExit("no entry matches %r; bldg samples: %s" % (needle, sample))
    for e in hits:
        print("saved", fetch_entry(url, e, out))
    with open(out / "PROVENANCE.txt", "a", encoding="utf-8") as f:       # 追記(取り直すたびに履歴が残る)
        f.write("source zip: %s\nentries: %s\nlicense: Project PLATEAU (MLIT), PDL1.0 (CC BY 4.0 compatible). 出典: 国土交通省 Project PLATEAU\n"
                % (url, ", ".join("%s (%d bytes)" % (e["name"], e["usize"]) for e in hits)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
