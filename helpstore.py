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

import atexit
import hashlib
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid

__all__ = ["HELP_DIR", "ARCHIVE", "html_root", "fig_root", "logical_path", "pack_archive"]

_HERE = os.path.dirname(os.path.abspath(__file__))
HELP_DIR = os.path.join(_HERE, "studio_assets", "op_help")
ARCHIVE = os.path.join(_HERE, "studio_assets", "op_help_html.tar.xz")
_LOCK = threading.Lock()
_ROOT = None
#: 書庫 SHA-256 からキャッシュ名へ使う 16 進文字数。/ Hex characters used in an archive cache key.
CACHE_DIGEST_HEX_CHARS = 16
_CACHE_NAME = re.compile(r"op_help-[0-9a-f]{%d}\Z" % CACHE_DIGEST_HEX_CHARS)
#: 別版の help キャッシュを最後の利用から保持する日数。/ Days to retain another version's cache after use.
CACHE_RETENTION_DAYS = 30
_SECONDS_PER_DAY = 24 * 60 * 60
_INUSE_LOCK = threading.Lock()
_INUSE_HANDLES = {}


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


def _try_file_lock(handle):
    """1 byte の排他ロックを非ブロッキングで試す。/ Try a non-blocking one-byte exclusive lock."""
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock_file(handle):
    """取得済みの 1 byte ロックを外す。失敗は終了処理を妨げない。/ Best-effort unlock."""
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except (OSError, ValueError):
        pass


def _close_inuse(handle, marker):
    """使用中印のロックと handle を閉じ、印を消す。/ Close and remove an in-use marker."""
    _unlock_file(handle)
    try:
        handle.close()
    except OSError:
        pass
    try:
        os.unlink(marker)
    except OSError:
        pass


def _release_inuse_caches():
    """終了時にこのプロセスの使用中印をすべて外す。/ Release this process's cache markers at exit."""
    with _INUSE_LOCK:
        held = list(_INUSE_HANDLES.values())
        _INUSE_HANDLES.clear()
    for handle, marker in held:
        _close_inuse(handle, marker)


atexit.register(_release_inuse_caches)


def _hold_cache_inuse(dest):
    """キャッシュを使う間、版ごとの印をロックして process 終了まで保持する。

    印を cache 内に作る → OS lock を取る → 元の名前に印と ``.complete`` がまだ在る、と順に確認する。
    掃除による rename と競合して確認に失敗した印は即座に外す。Create, lock, then validate the marker
    and completion file under the original directory name; retain the handle at module scope until process exit.
    """
    key = os.path.normcase(os.path.abspath(dest))
    with _INUSE_LOCK:
        held = _INUSE_HANDLES.get(key)
        if held is not None:
            if os.path.isfile(held[1]) and os.path.isfile(os.path.join(dest, ".complete")):
                return True
            _INUSE_HANDLES.pop(key, None)
            _close_inuse(*held)
        try:
            handle = tempfile.NamedTemporaryFile(
                mode="w+b", prefix=".inuse-%d-" % os.getpid(), dir=dest, delete=False
            )
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise OSError("helpstore: cannot create an in-use marker in %r: %s" % (dest, exc)) from exc
        marker = handle.name
        try:
            handle.write(b"0")
            handle.flush()
            if not _try_file_lock(handle):
                raise OSError("helpstore: cannot lock the in-use marker in %r" % dest)
            if not os.path.isfile(marker) or not os.path.isfile(os.path.join(dest, ".complete")):
                _close_inuse(handle, marker)
                return False
        except OSError:
            _close_inuse(handle, marker)
            raise
        _INUSE_HANDLES[key] = (handle, marker)
        return True


def _cache_held_here(path):
    """この process が既に保持する cache か。/ Return whether this process holds the cache."""
    key = os.path.normcase(os.path.abspath(path))
    with _INUSE_LOCK:
        return key in _INUSE_HANDLES


def _inuse_markers_are_stale(path):
    """全使用中印を非ブロッキングで lock し、落ちた process の古い印だけなら消す。

    1 つでも lock できない印、または安全に調べられない印があれば ``False``。Return ``True`` only
    when every marker can be locked without blocking; unlocked markers are crash leftovers and are removed.
    """
    acquired = []
    try:
        with os.scandir(path) as entries:
            markers = [entry.path for entry in entries
                       if entry.name.startswith(".inuse-") and entry.is_file(follow_symlinks=False)]
    except OSError:
        return False
    for marker in markers:
        try:
            handle = open(marker, "r+b")
        except FileNotFoundError:
            continue
        except OSError:
            for old_handle, _old_marker in acquired:
                _unlock_file(old_handle)
                old_handle.close()
            return False
        if not _try_file_lock(handle):
            handle.close()
            for old_handle, _old_marker in acquired:
                _unlock_file(old_handle)
                old_handle.close()
            return False
        acquired.append((handle, marker))
    for handle, marker in acquired:
        _unlock_file(handle)
        handle.close()
        try:
            os.unlink(marker)
        except FileNotFoundError:
            pass
        except OSError:
            return False
    return True


def _remove_stale_cache(path, name):
    """未使用の期限切れ cache を原子的に退避してから消す。/ Atomically quarantine then delete a stale cache.

    使用中印を全部 lock できた後に別名へ ``os.replace`` し、rename 直前の競合を拾うため退避先でもう一度
    印を調べる。使用中なら元の名前へ戻し、取れた印だけなら crash leftovers として消してから cache を消す。
    """
    if _cache_held_here(path) or not _inuse_markers_are_stale(path):
        return
    delete_path = os.path.join(os.path.dirname(path), "op_help-tmp-del-" + uuid.uuid4().hex)
    try:
        os.replace(path, delete_path)
    except OSError as exc:
        print("helpstore: could not remove old help cache %s: %s" % (name, exc), file=sys.stderr)
        return
    if not _inuse_markers_are_stale(delete_path):
        try:
            os.replace(delete_path, path)
        except OSError as exc:
            print("helpstore: could not restore in-use help cache %s: %s" % (name, exc), file=sys.stderr)
        return
    try:
        shutil.rmtree(delete_path)
        print("helpstore: removed old help cache %s" % name, file=sys.stderr)
    except OSError as exc:
        print("helpstore: could not remove old help cache %s: %s" % (name, exc), file=sys.stderr)


def _extract(archive):
    import fileio

    with open(archive, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:CACHE_DIGEST_HEX_CHARS]
    dest = os.path.join(_cache_base(), "op_help-" + digest)
    now = time.time()
    try:
        with os.scandir(_cache_base()) as entries:
            old = [e for e in entries if e.is_dir(follow_symlinks=False)
                   and e.path != dest and _CACHE_NAME.fullmatch(e.name)
                   and _cache_expired(e.path, now)]
    except OSError:
        old = []
    for entry in old:
        _remove_stale_cache(entry.path, entry.name)
    while True:
        marker = os.path.join(dest, ".complete")
        if os.path.isfile(marker) and _hold_cache_inuse(dest):
            try:
                os.utime(marker, None)
            except OSError:
                pass
            return dest
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="op_help-tmp-", dir=os.path.dirname(dest))
        # The help cache keeps only its cache-key and inter-process replacement
        # policy here; archive validation and extraction use the promoted fileio op.
        # キャッシュ固有処理だけを残し、書庫の安全契約は共通 op へ委譲する。
        try:
            fileio.archive_extract(archive, tmp)
        except ValueError as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            raise ValueError(f"helpstore: unsafe path or invalid help archive: {exc}") from exc
        with open(os.path.join(tmp, ".complete"), "w"):
            pass
        try:
            os.replace(tmp, dest)                   # 別プロセスと競ったら、先に入れ替えた方を使う
        except OSError:
            shutil.rmtree(tmp, ignore_errors=True)
            if not os.path.isfile(os.path.join(dest, ".complete")):
                raise


def _cache_expired(path, now):
    """最後の利用印が保持日数より古いキャッシュだけを返す。/ Return only stale caches."""
    marker = os.path.join(path, ".complete")
    try:
        last_used = os.path.getmtime(marker if os.path.isfile(marker) else path)
    except OSError:
        return False
    return now - last_used > CACHE_RETENTION_DAYS * _SECONDS_PER_DAY


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
    paths = [os.path.join(src_dir, *name.split("/")) for name in names]
    # The dependency-free canonical writer is also used by fileio.archive_create;
    # sdist builds run before NumPy (and therefore fileio) is installable.
    # NumPy 導入前の sdist 構築でも、fileio と同じ正本 writer を使う。
    import _archive_tarxz
    blob = _archive_tarxz._create(paths, root=src_dir, deterministic=True)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(blob)
    return len(names), len(blob)
