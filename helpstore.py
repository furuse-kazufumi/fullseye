# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""helpstore — op ヘルプの HTML(6 言語、1 万 5 千枚超)を、checkout ではディレクトリのまま、wheel では 1 つの固め書きの書庫から読む。

★2026-10-01: wheel が CI の上限 70 MB を越えた(70.2 MB)。中身の 58 MB が ``studio_assets/``、うち HTML が圧縮後 39 MB(展開 102 MB、
15,761 枚)。zip は 1 ファイルずつ圧縮するので、似たページの共通部分が消えない。tar を xz で固め書きにすると **2.6 MB**(15 分の 1)。
ユーザーの選択(2026-10-01)は「中身は 1 枚も減らさず、書庫にして Studio はそこから読む」。

* checkout(と editable install): ``studio_assets/op_help/`` に HTML がそのまま在る → そのディレクトリを返す(何も展開しない)。
* wheel: HTML は同梱せず ``studio_assets/op_help_html.tar.xz`` だけを入れる(``setup.py`` の build_py が組む)。初めて読むときに
  利用者のキャッシュ(``FULLSEYE_CACHE_DIR`` → ``%LOCALAPPDATA%/fullseye`` → ``~/.cache/fullseye``)へ 1 度だけ展開し、そこを返す。
  展開先の名前は書庫の SHA-256 の先頭 16 桁 —— 版が変われば別の場所に展開し直す(古い版の HTML を読まない)。
* 図(``op_help/fig/*.png``)は書庫に入れない(PNG は既に圧縮済みで固め書きの得が無い)—— 図の起点は常にパッケージの中。

書庫は**決定的**に作る(名前の昇順・時刻 0・所有者 0)ので、同じ HTML からは同じバイト列ができる。
"""
from __future__ import annotations

import hashlib
import io
import lzma
import os
import tarfile
import tempfile
import threading

__all__ = ["HELP_DIR", "ARCHIVE", "html_root", "fig_root", "logical_path", "pack_archive"]

_HERE = os.path.dirname(os.path.abspath(__file__))
HELP_DIR = os.path.join(_HERE, "studio_assets", "op_help")
ARCHIVE = os.path.join(_HERE, "studio_assets", "op_help_html.tar.xz")
_LOCK = threading.Lock()
_ROOT = None


def _has_html(d):
    try:
        with os.scandir(d) as it:
            return any(e.is_file() and e.name.endswith(".html") for e in it)
    except OSError:
        return False


def _cache_base():
    env = os.environ.get("FULLSEYE_CACHE_DIR")
    if env:
        return env
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return os.path.join(local, "fullseye")
    return os.path.join(os.path.expanduser("~"), ".cache", "fullseye")


def _safe_members(tf):
    """書庫の中身を検める: 通常ファイルとディレクトリだけ、絶対パス・``..``・リンクは拒否(展開先の外へ書かせない)。"""
    out = []
    for m in tf.getmembers():
        name = m.name.replace("\\", "/")
        if name.startswith("/") or ".." in name.split("/") or ":" in name:
            raise ValueError("helpstore: unsafe path in the help archive: %r" % m.name)
        if not (m.isfile() or m.isdir()):
            raise ValueError("helpstore: only files and directories are allowed in the help archive (%r)" % m.name)
        out.append(m)
    return out


def _extract(archive):
    with open(archive, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:16]
    dest = os.path.join(_cache_base(), "op_help-" + digest)
    if os.path.isfile(os.path.join(dest, ".complete")):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="op_help-tmp-", dir=os.path.dirname(dest))
    with tarfile.open(archive, mode="r:xz") as tf:
        members = _safe_members(tf)
        for m in members:
            target = os.path.join(tmp, *m.name.replace("\\", "/").split("/"))
            if m.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with tf.extractfile(m) as src, open(target, "wb") as dst:
                dst.write(src.read())
    open(os.path.join(tmp, ".complete"), "w").close()
    try:
        os.replace(tmp, dest)                       # 別プロセスと競ったら、先に入れ替えた方を使う
    except OSError:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        if not os.path.isfile(os.path.join(dest, ".complete")):
            raise
    return dest


def html_root():
    """ヘルプ HTML の在る根(``<root>/<op>.html``・``<root>/<dim>/<op>.html``・``<root>/guide_<stem>.html``)。

    checkout は ``studio_assets/op_help``、wheel は書庫を展開したキャッシュ。どちらも無ければ ``HELP_DIR`` を返す
    (読む側は「ファイルが無い」= 生成カードに落ちる、という今までの振る舞いのまま)。
    """
    global _ROOT
    if _ROOT is not None:
        return _ROOT
    with _LOCK:
        if _ROOT is None:
            if _has_html(HELP_DIR) or not os.path.isfile(ARCHIVE):
                _ROOT = HELP_DIR
            else:
                _ROOT = _extract(ARCHIVE)
    return _ROOT


def fig_root():
    """ヘルプの図(``fig/<op>.png``)の根。書庫には入れないので、常にパッケージの中。"""
    return HELP_DIR


def logical_path(path):
    """実体の場所(キャッシュでも)を、パッケージ内の論理的な場所 ``studio_assets/op_help/<rel>`` で言い直す(報告用)。"""
    rel = os.path.relpath(path, html_root()).replace(os.sep, "/")
    return "studio_assets/op_help/" + rel


def pack_archive(src_dir=HELP_DIR, dst=ARCHIVE):
    """``src_dir`` の HTML(直下と 1 段下)を決定的な tar.xz にする。返り値 = (枚数, バイト数)。"""
    names = []
    for dp, _dirs, files in os.walk(src_dir):
        rel_dir = os.path.relpath(dp, src_dir)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        if depth > 1 or os.path.basename(dp) == "fig":
            continue
        for fn in files:
            if fn.endswith(".html"):
                names.append(os.path.normpath(os.path.join(rel_dir, fn)).replace(os.sep, "/"))
    names.sort()
    if not names:
        raise ValueError("helpstore.pack_archive: no .html files under %r" % src_dir)
    buf = io.BytesIO()
    with lzma.LZMAFile(buf, "wb", format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME) as xz:
        with tarfile.open(fileobj=xz, mode="w", format=tarfile.USTAR_FORMAT) as tf:
            for n in names:
                with open(os.path.join(src_dir, *n.split("/")), "rb") as f:
                    data = f.read()
                ti = tarfile.TarInfo(n)
                ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
                tf.addfile(ti, io.BytesIO(data))
    blob = buf.getvalue()
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(blob)
    return len(names), len(blob)
