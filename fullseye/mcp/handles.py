# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""画像のハンドル(``fullseye://img/<sha16>``)とサンドボックス。

LLM は**バイト列を見ない**。配列はここに置き、ハンドルだけがプロトコルを行き来する
(MCP-Universe: 歩数とともに入力トークンが急増する —— 画像を本文に載せると 1 枚で直撃)。

fail-closed:
- 読めるのは**根の下**だけ。既定の根は wheel に同梱されるサンプル 12 枚
  (``studio_assets/sample_images``、来歴とライセンス付き)。``FULLSEYE_MCP_ROOT`` で
  足す(``os.pathsep`` 区切り)。``..`` もシンボリックリンクも ``realpath`` で潰してから
  根と比べる。
- 未知のハンドル・追い出されたハンドルは理由つきで拒否する。
- ハンドルは内容の sha256 なので、同じ配列は同じ名前になる(重複して持たない)。
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from collections import OrderedDict

import numpy as np

from .catalog import ROOT

SAMPLE_DIR = os.path.join(ROOT, "studio_assets", "sample_images")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".npy")
PREFIX = "fullseye://img/"


class HandleError(ValueError):
    """ハンドル/パスの拒否。JSON-RPC の -32602 に写す。"""


def default_roots() -> list[str]:
    roots = [SAMPLE_DIR]
    extra = os.environ.get("FULLSEYE_MCP_ROOT", "")
    roots += [p for p in extra.split(os.pathsep) if p.strip()]
    return roots


class HandleStore:
    def __init__(self, roots: list[str] | None = None, *, max_items: int = 256,
                 thumb_dir: str | None = None):
        self.roots = [os.path.realpath(r) for r in (roots if roots is not None else default_roots())]
        self.max_items = int(max_items)
        # ★thumb_dir を渡されたときに作っていなかった(mkdtemp のときだけ存在する)。
        #   小図の保存が FileNotFoundError で落ち、テスト 4 件で発覚(2026-09-15)。
        self.thumb_dir = thumb_dir or tempfile.mkdtemp(prefix="fullseye-mcp-")
        os.makedirs(self.thumb_dir, exist_ok=True)
        self._meta: OrderedDict[str, dict] = OrderedDict()
        self._arr: dict[str, object] = {}
        self._evicted: set[str] = set()
        self._seq = 0

    # ---------------------------------------------------------------- paths
    def _check_path(self, path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise HandleError("path が空")
        real = os.path.realpath(path)
        inside = any(real == r or real.startswith(r + os.sep) for r in self.roots)
        if not inside:
            raise HandleError(
                "根の外のパスは読まない: %s(読めるのは %s の下だけ。"
                "FULLSEYE_MCP_ROOT で根を足せる)" % (path, self.roots))
        if os.path.splitext(real)[1].lower() not in IMAGE_EXT:
            raise HandleError("読める拡張子は %s: %s" % (IMAGE_EXT, path))
        if not os.path.isfile(real):
            raise HandleError("ファイルが無い: %s" % path)
        return real

    def samples(self) -> list[dict]:
        """同梱サンプルの一覧(manifest の来歴つき)。"""
        import json
        man = os.path.join(SAMPLE_DIR, "manifest.json")
        rows = []
        if os.path.exists(man):
            with open(man, encoding="utf-8") as f:
                m = json.load(f)
            items = m if isinstance(m, list) else next(iter(m.values()))
            for it in items:
                p = os.path.join(SAMPLE_DIR, it.get("file", ""))
                if os.path.isfile(p):
                    rows.append({"name": it.get("name"), "path": p,
                                 "source": it.get("source"), "licence": it.get("licence")})
        return rows

    # ---------------------------------------------------------------- store
    @staticmethod
    def _hid(arr: np.ndarray) -> str:
        h = hashlib.sha256()
        h.update(np.ascontiguousarray(arr).tobytes())
        h.update(("%s|%s" % (arr.shape, arr.dtype)).encode())
        return PREFIX + h.hexdigest()[:16]

    def put(self, arr, *, sort: str, provenance: list) -> dict:
        arr = np.asarray(arr)
        hid = self._hid(arr)
        if hid in self._meta:
            self._meta.move_to_end(hid)
            return dict(self._meta[hid], dedup=True)
        self._seq += 1
        meta = {"handle": hid, "sort": sort, "shape": list(arr.shape), "dtype": str(arr.dtype),
                "provenance": list(provenance), "seq": self._seq}
        self._meta[hid] = meta
        self._arr[hid] = arr
        while len(self._meta) > self.max_items:
            old, _ = self._meta.popitem(last=False)
            self._arr.pop(old, None)
            self._evicted.add(old)
        return dict(meta)

    def load(self, path: str, *, color: bool = False) -> dict:
        real = self._check_path(path)
        if real.lower().endswith(".npy"):
            arr = np.load(real)
            sort = "image" if arr.ndim == 2 else "color" if arr.ndim == 3 and arr.shape[-1] == 3 else "any"
        else:
            import imgio
            arr = imgio.load(real, color=color)
            sort = "color" if color else "image"
        return self.put(arr, sort=sort, provenance=[{"load": os.path.relpath(real, ROOT) if real.startswith(ROOT) else real}])

    def get(self, handle: str) -> tuple[dict, np.ndarray]:
        if not isinstance(handle, str) or not handle.startswith(PREFIX):
            raise HandleError("ハンドルは %s<16 hex> の形: %r" % (PREFIX, handle))
        if handle in self._evicted:
            raise HandleError("追い出されたハンドル(保持上限 %d): %s —— 読み直すか作り直す"
                              % (self.max_items, handle))
        meta = self._meta.get(handle)
        if meta is None:
            raise HandleError("知らないハンドル: %s(生きているのは %d 個)" % (handle, len(self._meta)))
        self._meta.move_to_end(handle)
        return dict(meta), self._arr[handle]

    def write_thumb(self, handle: str, rgb: np.ndarray, tag: str) -> str:
        import imgio
        name = "%s.%s.png" % (handle[len(PREFIX):], tag)
        path = os.path.join(self.thumb_dir, name)
        imgio.save(path, rgb)
        return path

    def stats(self) -> dict:
        return {"alive": len(self._meta), "evicted": len(self._evicted),
                "max_items": self.max_items, "roots": self.roots, "thumb_dir": self.thumb_dir}
