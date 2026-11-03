# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Dependency-free deterministic tar.xz creation shared by fileio and helpstore.

NumPy を導入しない sdist の隔離環境でも help archive を構築できるよう、
tar.xz 作成の正本だけをこの内部 module に置く。
"""
from __future__ import annotations

import contextlib
import datetime as _datetime
import io
import lzma
import os
import pathlib
import tarfile
from collections.abc import Mapping

_MAX_TOTAL_BYTES = 2 * 1024**3
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL",
                    *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _safe_name(name, op):
    """Return a portable relative member name / 安全な相対 member 名を返す。"""
    if not isinstance(name, str) or not name or "\0" in name:
        raise ValueError(f"{op}: archive member name must be a non-empty string without NUL")
    name = name.replace("\\", "/")
    pure = pathlib.PurePosixPath(name)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"{op}: unsafe archive member name: {name!r}")
    if pure.parts and (":" in pure.parts[0] or pure.parts[0].upper().split(".")[0] in _WINDOWS_DEVICES):
        raise ValueError(f"{op}: unsafe archive member name: {name!r}")
    return pure.as_posix()


def _items(paths_or_items, root, deterministic, op):
    """Normalise inputs with root/link/size gates / 入力を検証して正規化する。"""
    now = int(_datetime.datetime.now(tz=_datetime.timezone.utc).timestamp())
    if isinstance(paths_or_items, Mapping):
        raw_items = list(paths_or_items.items())
    elif (isinstance(paths_or_items, (list, tuple)) and paths_or_items
          and all(isinstance(item, (list, tuple)) and len(item) == 2 for item in paths_or_items)):
        raw_items = list(paths_or_items)
    else:
        raw_items = None
    entries = []
    if raw_items is not None:
        if not raw_items:
            raise ValueError(f"{op}: paths_or_items must not be empty")
        if root is not None:
            raise ValueError(f"{op}: root is only valid for filesystem paths")
        for name, value in raw_items:
            safe = _safe_name(name, op)
            if not isinstance(value, (bytes, bytearray, memoryview, str)):
                raise ValueError(f"{op}: item {name!r} must contain bytes or UTF-8 text")
            data = value.encode("utf-8") if isinstance(value, str) else bytes(value)
            entries.append({"name": safe, "data": data, "size": len(data), "is_dir": False,
                            "mtime": 0 if deterministic else now})
    else:
        values = [paths_or_items] if isinstance(paths_or_items, (str, os.PathLike)) else list(paths_or_items)
        if not values:
            raise ValueError(f"{op}: paths_or_items must not be empty")
        raw_paths = [pathlib.Path(os.fspath(value)).absolute() for value in values]
        if any(path.is_symlink() for path in raw_paths):
            raise ValueError(f"{op}: symbolic links are forbidden")
        if any(not path.exists() for path in raw_paths):
            missing = next(path for path in raw_paths if not path.exists())
            raise ValueError(f"{op}: input path does not exist: {str(missing)!r}")
        if root is None:
            root_path = pathlib.Path(os.path.commonpath([str(path.parent) for path in raw_paths])).resolve()
        else:
            root_path = pathlib.Path(os.fspath(root)).absolute()
            if root_path.is_symlink() or not root_path.is_dir():
                raise ValueError(f"{op}: root must be an existing real directory")
            root_path = root_path.resolve()
        for raw_path in raw_paths:
            try:
                raw_path.resolve().relative_to(root_path)
            except ValueError as exc:
                raise ValueError(f"{op}: path {str(raw_path)!r} is outside root {str(root_path)!r}") from exc
            visit = [raw_path]
            while visit:
                path = visit.pop()
                if path.is_symlink():
                    raise ValueError(f"{op}: symbolic links are forbidden: {str(path)!r}")
                safe = _safe_name(path.resolve().relative_to(root_path).as_posix(), op)
                info = path.stat()
                if path.is_dir():
                    entries.append({"name": safe, "size": 0, "is_dir": True,
                                    "mtime": 0 if deterministic else int(info.st_mtime)})
                    visit.extend(sorted(path.iterdir(), key=lambda child: child.name, reverse=True))
                elif path.is_file():
                    entries.append({"name": safe, "path": str(path), "size": info.st_size,
                                    "is_dir": False, "mtime": 0 if deterministic else int(info.st_mtime)})
                else:
                    raise ValueError(f"{op}: only regular files and directories are allowed: {str(path)!r}")
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)) or len({name.casefold() for name in names}) != len(names):
        raise ValueError(f"{op}: duplicate or case-colliding archive names")
    total = sum(entry["size"] for entry in entries if not entry["is_dir"])
    if total > _MAX_TOTAL_BYTES:
        raise ValueError(f"{op}: input size {total} exceeds {_MAX_TOTAL_BYTES}-byte limit")
    return sorted(entries, key=lambda entry: entry["name"])


@contextlib.contextmanager
def _entry_stream(entry):
    """Open one entry without loading path input / path 入力を全量保持せず開く。"""
    if "data" in entry:
        yield io.BytesIO(entry["data"])
    else:
        with open(entry["path"], "rb") as stream:
            yield stream


def _create(paths_or_items, *, root=None, level=9, deterministic=True, op="archive_create"):
    """Create deterministic tar.xz bytes / 決定的な tar.xz bytes を作る。"""
    entries = _items(paths_or_items, root, deterministic, op)
    out = io.BytesIO()
    preset = level | (lzma.PRESET_EXTREME if level == 9 else 0)
    with lzma.LZMAFile(out, "wb", format=lzma.FORMAT_XZ, preset=preset) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for entry in entries:
                info = tarfile.TarInfo(entry["name"] + ("/" if entry["is_dir"] else ""))
                info.size = 0 if entry["is_dir"] else entry["size"]
                info.type = tarfile.DIRTYPE if entry["is_dir"] else tarfile.REGTYPE
                info.mtime = entry["mtime"]
                info.mode = 0o755 if entry["is_dir"] else 0o644
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                if entry["is_dir"]:
                    archive.addfile(info)
                else:
                    with _entry_stream(entry) as src:
                        archive.addfile(info, src)
    return out.getvalue()
