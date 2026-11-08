# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""検査 PoC 4 本の実データ(公開・再配布可のライセンス)を repo の外へ取得し、SHA-256 で固定する。

Fetch the public, redistributable real datasets used by four inspection PoCs, outside the
repository, and pin each archive by byte count and SHA-256.

使い方 / usage::

    py -3.11 tools/fetch_realinsp_data.py --list
    py -3.11 tools/fetch_realinsp_data.py concrete_crack sipv_el tbm raw_fabrid
    py -3.11 tools/fetch_realinsp_data.py all

``tbm`` は ``tools/fetch_tbm.py``(``poc_real_grain_skiz`` と共用の TBM 取得器)へ委ねる。URL・
バイト数・SHA-256 の正本はそちらに 1 つだけ置き、ここでは読み込んで使う(取得器を 2 本にしない)。

置き場は PoC と同じ規則で決める: ``FULLSEYE_POC_REAL_DATA`` があればその下、無ければ開発の作業木
(``<root>/projects/<checkout>``)の隣の ``<root>/data/fullseye_poc_real``、それ以外はユーザー
キャッシュ。各データは ``<置き場>/<dir>/raw/<書庫>`` に置き、``<置き場>/<dir>/<展開先>`` へ展開する。

=================  ==========================================  =====================  ==========================
名前               データ(配布元)                              ライセンス(配布元の表記)   使う PoC
=================  ==========================================  =====================  ==========================
concrete_crack     Özgenel, Concrete Crack Images for          CC BY 4.0              poc_crack_width
                   Classification(Mendeley 5y9wdsg2zt v2)
sipv_el            Mateo-Romero et al., SIPV-EL                "Creative Commons      poc_solar_el_inspection
                   (Zenodo 14439369)                           Attribution 4.0
                                                               International"
tbm                TBM: Texture Boundary in Metallography      "Creative Commons      poc_metal_grain_size
                   (Zenodo 8386997)                            Attribution 4.0
                                                               International"
raw_fabrid         Pérez-Llorens et al., RAW-FABRID            CC BY 4.0              poc_fabric_defect
                   (Mendeley db6g85xsyg v1)
=================  ==========================================  =====================  ==========================

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。書庫は ``.part`` に書き、バイト数と
SHA-256 が台帳に一致したときだけ本名にする。展開は書庫の外を指す名前・絶対パス・symlink を
拒否する。RAR(concrete_crack)の展開には 7-Zip(``7z``)が要る —— 無ければ理由を言って止める。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import importlib.util
import zipfile
from pathlib import Path, PurePosixPath


def _load_fetch_tbm():
    """隣の ``tools/fetch_tbm.py`` を読み込む(TBM の台帳と取得の正本)。"""
    spec = importlib.util.spec_from_file_location("fetch_tbm", Path(__file__).resolve().with_name("fetch_tbm.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_TBM = _load_fetch_tbm()

#: 名前 -> 取得と展開の台帳。sha256 / bytes は 2026-11-08 に下の URL から取得した実測値
#: (Mendeley の 2 件は配布元が公開している sha256 とも一致、Zenodo の 2 件は md5 とも一致)。
DATASETS = {
    "concrete_crack": {
        "dir": "concrete_crack_ozgenel",
        "url": ("https://data.mendeley.com/public-files/datasets/5y9wdsg2zt/files/"
                "8a70d8a5-bce9-4291-bab9-b48cfb3e87c3/file_downloaded"),
        "file": "Concrete_Crack_Images_for_Classification.rar",
        "bytes": 241_363_336,
        "sha256": "08d7dc505a4f5a0330cee2fa2a1ae4b5b4f98bcffd0549b774caf7959bb1f02f",
        "kind": "rar", "extract_to": "extracted", "members": ("Positive/",),
        "license": "CC BY 4.0",
        "cite": "Özgenel, Ç. F. (2019). Concrete Crack Images for Classification. Mendeley Data, v2. "
                "doi:10.17632/5y9wdsg2zt.2",
    },
    "sipv_el": {
        "dir": "sipv_el",
        "url": "https://zenodo.org/api/records/14439369/files/all_cells.zip/content",
        "file": "all_cells.zip",
        "bytes": 484_606_354,
        "sha256": "3fca8d9a3eb748f55f742b5e3651e9caa4da004c0c86e756d5afb24ad1a3a216",
        "kind": "zip", "extract_to": "extracted", "members": None,
        "extra": [{
            "url": ("https://zenodo.org/api/records/14439369/files/"
                    "features_labels_poli_y_mono_IV.csv/content"),
            "file": "features_labels_poli_y_mono_IV.csv", "bytes": 325_102,
            "sha256": "31497f080963b4a972858be5e53ef6d9e3a721ddef40442245d949b596891e9b"}],
        "license": "Creative Commons Attribution 4.0 International",
        "cite": "Mateo Romero, H. F., Hernández Callejo, L., Alonso Gómez, V., Morales, J. I. SIPV-EL. "
                "Zenodo. doi:10.5281/zenodo.14439369",
    },
    "tbm": {
        "dir": "tbm",
        # 正本は tools/fetch_tbm.py(取得もそちらへ委ねる: "delegate")
        "url": _TBM.TBM_URL,
        "file": "TBM.zip",
        "bytes": _TBM.TBM_BYTES,
        "sha256": _TBM.TBM_SHA256,
        "kind": "zip", "extract_to": ".", "members": ("TBM/",), "delegate": "fetch_tbm",
        "license": "Creative Commons Attribution 4.0 International",
        "cite": "TBM: Texture Boundary in Metallography. Zenodo. doi:10.5281/zenodo.8386997",
    },
    "raw_fabrid": {
        "dir": "raw_fabrid",
        "url": ("https://data.mendeley.com/public-files/datasets/db6g85xsyg/files/"
                "93e17d48-b5e6-45f7-9064-be84cc5fb91c/file_downloaded"),
        "file": "RAW_FABRID.zip",
        "bytes": 4_133_046_386,
        "sha256": "f6b4f82cce2f0220bbab3968a74b5337ebf2bbfd5e33d0548d34e1ebf80f85b9",
        # 256 px のパッチ群(MVTec/、約 2 万枚)は使わないので展開しない
        "kind": "zip", "extract_to": "extracted",
        "members": ("RAW_FABRID/images/", "RAW_FABRID/masks/", "RAW_FABRID/Readme.txt",
                    "RAW_FABRID/RAW_FABRID_HighRes_Metadata.csv", "RAW_FABRID/RAW_FABRID_HighRes_COCO.json"),
        "license": "CC BY 4.0",
        "cite": "Pérez-Llorens, R., Albero-Albero, T., Silvestre-Blanes, J. RAW-FABRID: RAW FABRic Image "
                "Dataset for defect detection. Mendeley Data, v1. doi:10.17632/db6g85xsyg.1",
    },
}


def data_root() -> Path:
    """PoC の ``real_data_root()`` と同じ規則の置き場。"""
    configured = os.environ.get("FULLSEYE_POC_REAL_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real"
    return Path.home() / ".cache" / "fullseye" / "poc_real"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _fetch(url: str, dest: Path, size: int, digest: str) -> None:
    """``dest`` が台帳どおりなら何もしない。無ければ ``.part`` に取って照合してから本名にする。"""
    if dest.is_file() and dest.stat().st_size == size and _sha256(dest) == digest:
        print("  済: %s" % dest.name)
        return
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE ではネットへ出ない: %s" % dest.name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    print("  取得: %s (%s bytes)" % (dest.name, format(size, ",")))
    req = urllib.request.Request(url, headers={"User-Agent": "fullseye-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=600) as resp, part.open("wb") as out:   # noqa: S310 固定 HTTPS
        shutil.copyfileobj(resp, out, length=8 << 20)
    got_size, got = part.stat().st_size, _sha256(part)
    if got_size != size or got != digest:
        raise SystemExit("%s: バイト数 %d / SHA-256 %s が台帳(%d / %s)と違う。展開しない"
                         % (dest.name, got_size, got, size, digest))
    part.replace(dest)


def _check_name(name: str) -> PurePosixPath:
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise SystemExit("書庫の危険なパス: %r" % name)
    return p


def _extract_zip(archive: Path, out: Path, members) -> int:
    n = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            p = _check_name(info.filename)
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise SystemExit("書庫内の symlink は展開しない: %r" % info.filename)
            if info.is_dir() or p.name in (".DS_Store",) or "__MACOSX" in p.parts:
                continue
            if members and not any(str(p).startswith(m) for m in members):
                continue
            target = out.joinpath(*p.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            n += 1
    return n


def _extract_rar(archive: Path, out: Path, members) -> int:
    exe = shutil.which("7z") or shutil.which("7z.exe")
    if exe is None:
        for cand in (Path(os.environ.get("ProgramFiles", "")) / "7-Zip" / "7z.exe",):
            if cand.is_file():
                exe = str(cand)
    if exe is None:
        raise SystemExit("RAR の展開に 7-Zip(7z)が要る。入れてから再実行する")
    listing = subprocess.run([exe, "l", "-slt", str(archive)], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", check=True).stdout
    for line in listing.splitlines():
        if line.startswith("Path = ") and not line.endswith(archive.name):
            _check_name(line[len("Path = "):])
    out.mkdir(parents=True, exist_ok=True)
    args = [exe, "x", "-y", "-o" + str(out), str(archive)]
    if members:
        args += [m.rstrip("/") + "\\*" if os.name == "nt" else m + "*" for m in members]
    subprocess.run(args, check=True, capture_output=True)
    return sum(1 for _ in out.rglob("*") if _.is_file())


def fetch(name: str) -> Path:
    spec = DATASETS[name]
    if spec.get("delegate") == "fetch_tbm":
        # PoC の _tbm_dir と同じ規則: FULLSEYE_TBM_DATA が最優先、無ければ <置き場>/tbm
        tbm = os.environ.get("FULLSEYE_TBM_DATA", "").strip()
        return _TBM.fetch(Path(tbm).expanduser() if tbm else data_root() / spec["dir"])
    base = data_root() / spec["dir"]
    raw = base / "raw"
    print("%s → %s" % (name, base))
    _fetch(spec["url"], raw / spec["file"], spec["bytes"], spec["sha256"])
    for ex in spec.get("extra", []):
        _fetch(ex["url"], raw / ex["file"], ex["bytes"], ex["sha256"])
    out = (base / spec["extract_to"]).resolve()
    marker = base / (".extracted_%s" % spec["sha256"][:16])
    if not marker.is_file():
        ex = _extract_rar if spec["kind"] == "rar" else _extract_zip
        n = ex(raw / spec["file"], out, spec["members"])
        marker.write_text("%d\n" % n, encoding="ascii")
        print("  展開: %d files → %s" % (n, out))
    (base / "SOURCE.txt").write_text(
        "license: %s\ncite: %s\nurl: %s\nsha256: %s\n"
        % (spec["license"], spec["cite"], spec["url"], spec["sha256"]), encoding="utf-8")
    return base


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*", help="取得するデータの名前(all で全部)")
    ap.add_argument("--list", action="store_true", help="台帳を表示して終わる")
    args = ap.parse_args(argv)
    if args.list or not args.names:
        for k, v in DATASETS.items():
            print("%-15s %13s B  %s  (%s)" % (k, format(v["bytes"], ","), v["license"], v["cite"]))
        return 0
    names = list(DATASETS) if args.names == ["all"] else args.names
    bad = [n for n in names if n not in DATASETS]
    if bad:
        raise SystemExit("未登録の名前: %s(登録済み: %s)" % (bad, ", ".join(DATASETS)))
    for n in names:
        fetch(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
