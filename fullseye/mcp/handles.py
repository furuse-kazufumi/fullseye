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
- ハンドルは内容と型(sort)の sha256 なので、同じ配列・同じ型は同じ名前になる(重複して持たない)。
  型を混ぜないのは、二値画像に threshold を掛けた region が入力の image と同じバイト列になり、
  同じハンドル(sort=image)が返って次段の region op が型の不一致で拒否されていたから(2026-10-11)。
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


def _declared_pixels(path: str) -> int | None:
    """画像ファイルの見出しが宣言する画素数(高さ × 幅)。読めなければ None(その時は復号の後の上限が効く)。"""
    import struct
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".npy":
            arr = np.load(path, mmap_mode="r", allow_pickle=False)
            return int(np.prod(arr.shape[:2], dtype=np.int64)) if arr.ndim >= 2 else int(arr.size)
        with open(path, "rb") as fh:
            head = fh.read(33)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            width, height = struct.unpack(">II", head[16:24])
            return int(width) * int(height)
        try:
            from PIL import Image
        except ImportError:
            return None
        with Image.open(path) as im:                     # 遅延: 見出しだけを読む
            return int(im.size[0]) * int(im.size[1])
    except Exception:                                    # noqa: BLE001 - 見出しが読めない物は復号の側の検査に任せる
        return None


class HandleStore:
    def __init__(self, roots: list[str] | None = None, *, max_items: int = 256,
                 max_bytes: int | None = None, thumb_dir: str | None = None):
        from fssystem import get_system
        self.roots = [os.path.realpath(r) for r in (roots if roots is not None else default_roots())]
        self.max_items = int(max_items)
        self.max_bytes = int(max_bytes if max_bytes is not None else get_system("mcp_handle_max_bytes"))
        # ★thumb_dir を渡されたときに作っていなかった(mkdtemp のときだけ存在する)。
        #   小図の保存が FileNotFoundError で落ち、テスト 4 件で発覚(2026-09-15)。
        self.thumb_dir = thumb_dir or tempfile.mkdtemp(prefix="fullseye-mcp-")
        os.makedirs(self.thumb_dir, exist_ok=True)
        if thumb_dir is None:
            # ★2026-11-13(報告 10 / S7): 自分で作った一時フォルダはサーバの終了後も残っていた。
            #   この置き場が捨てられる時(終了時を含む)に消す。渡されたフォルダは消さない。
            import shutil
            import weakref
            self._cleanup = weakref.finalize(self, shutil.rmtree, self.thumb_dir, True)
        self._meta: OrderedDict[str, dict] = OrderedDict()
        self._arr: dict[str, object] = {}
        self._evicted: set[str] = set()
        self._seq = 0

    # ---------------------------------------------------------------- paths
    def display_path(self, path: str) -> str:
        """Return an MCP-safe path label without exposing host roots or home dirs."""
        try:
            real = os.path.realpath(path)
            for root in self.roots:
                if real == root:
                    return "<root>"
                if real.startswith(root + os.sep):
                    return "<root>/" + os.path.relpath(real, root).replace(os.sep, "/")
        except (ValueError, OSError):
            # ★2026-11-13(報告 10 / S7): path=NUL などの装置名で relpath が ValueError を投げ、-32603 になっていた
            real = str(path)
        return "<outside>/" + (os.path.basename(real.replace("\\", "/").rstrip("/")) or "?")

    def _inside_roots(self, path: str) -> bool:
        try:
            real = os.path.realpath(path)
        except (ValueError, OSError):
            return False
        return any(real == r or real.startswith(r + os.sep) for r in self.roots)

    def _check_path(self, path: str) -> str:
        if not isinstance(path, str) or not path.strip():
            raise HandleError("path が空")
        try:
            if os.path.isabs(path):
                real = os.path.realpath(path)
            else:
                candidates=[os.path.realpath(os.path.join(root,path)) for root in self.roots]
                real=next((p for p in candidates if os.path.isfile(p)), candidates[0] if candidates else os.path.realpath(path))
        except (ValueError, OSError):
            raise HandleError("読めないパス: %s(読めるのは <root> の下だけ)" % self.display_path(path)) from None
        inside = any(real == r or real.startswith(r + os.sep) for r in self.roots)
        if not inside:
            raise HandleError(
                "根の外のパスは読まない: %s(読めるのは <root> の下だけ。"
                "FULLSEYE_MCP_ROOT で根を足せる)" % self.display_path(real))
        if os.path.splitext(real)[1].lower() not in IMAGE_EXT:
            raise HandleError("読める拡張子は %s: %s%s" % (IMAGE_EXT, self.display_path(real), self._nearby(path)))
        if not os.path.isfile(real):
            raise HandleError("ファイルが無い: %s%s" % (self.display_path(real), self._nearby(path)))
        return real

    def root_files(self, limit: int = 200) -> list[str]:
        """同梱サンプル以外の根(``FULLSEYE_MCP_ROOT``)にある読めるファイルの名前(根からの相対、最大 200 件)。

        並べるのは根の直下と、その 1 段下のディレクトリの中まで(根 + 1 段)。名前が ``.`` で始まるファイルと
        ディレクトリは出さない。

        ★2026-11-08(AI が組んだ検査の PoC、作者と独立の検証): ``list_samples`` が同梱サンプルしか返さず、
        課題で渡された開発用画像は名前を推測するしかなかった(32B の模型が load_image を 20 回推測で外した回がある)。
        Readable files under the non-sample roots, relative to their root (never a host path).
        """
        sample = os.path.realpath(SAMPLE_DIR)
        out: list[str] = []
        for root in self.roots:
            if root == sample or not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                rel = os.path.relpath(dirpath, root)
                depth = 0 if rel == "." else rel.count(os.sep) + 1        # 根 = 0、1 段下 = 1
                # ★2026-11-13(報告 10 / S4): 根の中のジャンクション・リンクの先(根の外)の名前を並べていた
                #   (中身は _check_path が断るが、名前が漏れる)。実体が根の外の物は辿らず、並べない。
                dirnames[:] = sorted(d for d in dirnames if not d.startswith(".")
                                     and self._inside_roots(os.path.join(dirpath, d))) if depth < 1 else []
                for fn in sorted(filenames):
                    if (not fn.startswith(".") and os.path.splitext(fn)[1].lower() in IMAGE_EXT
                            and self._inside_roots(os.path.join(dirpath, fn))):
                        out.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))
                        if len(out) >= limit:
                            return out
        return out

    def _nearby(self, path) -> str:
        """拒否の文に添える「読める名前」(近い順に 8 件まで)。根の外の名前やホストのパスは出さない。"""
        import difflib
        names = self.root_files() + [r["name"] for r in self.samples() if r.get("name")]
        if not names:
            return ""
        key = os.path.basename(str(path))
        near = difflib.get_close_matches(key, names, n=8, cutoff=0.0)
        return "。読める名前(近い順): %s" % ", ".join(near)

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
                                 "source": it.get("source"), "licence": it.get("licence"),
                                 "description": it.get("description"),
                                 "has_truth": bool(it.get("truth_mask"))})
        return rows

    # ---------------------------------------------------------------- store
    @staticmethod
    def _hid(arr, sort: str = "") -> str:
        h = hashlib.sha256()
        if isinstance(arr, np.ndarray):
            h.update(np.ascontiguousarray(arr).tobytes())
            h.update(("%s|%s|%s" % (arr.shape, arr.dtype, sort)).encode())
        else:
            import json
            try:
                payload = json.dumps(arr, sort_keys=True, ensure_ascii=False, default=repr)
            except (TypeError, ValueError):
                payload = repr(arr)
            h.update((type(arr).__name__ + "|" + sort + "|" + payload).encode("utf-8"))
        return PREFIX + h.hexdigest()[:16]

    def put(self, arr, *, sort: str, provenance: list) -> dict:
        if isinstance(arr, (list, tuple)) and sort in {"image","images","seq<image>","points","volume"}:
            arr = np.asarray(arr)
        hid = self._hid(arr, sort)
        self._evicted.discard(hid)          # 作り直したハンドルは生きている(追い出し印を消す)
        if hid in self._meta:
            self._meta.move_to_end(hid)
            return dict(self._meta[hid], dedup=True)
        size = int(arr.nbytes) if isinstance(arr,np.ndarray) else len(repr(arr).encode("utf-8"))
        if size > self.max_bytes:
            raise HandleError("handle requires %d bytes, above byte limit %d" % (size,self.max_bytes))
        while self._meta and sum(m.get("bytes",0) for m in self._meta.values()) + size > self.max_bytes:
            old, _ = self._meta.popitem(last=False)
            self._arr.pop(old, None); self._evicted.add(old)
        self._seq += 1
        meta = {"handle": hid, "sort": sort,
                "shape": list(arr.shape) if isinstance(arr, np.ndarray) else None,
                "dtype": str(arr.dtype) if isinstance(arr, np.ndarray) else type(arr).__name__,
                "array": isinstance(arr, np.ndarray),
                "bytes": size,
                "provenance": list(provenance), "seq": self._seq}
        self._meta[hid] = meta
        self._arr[hid] = arr
        while len(self._meta) > self.max_items:
            old, _ = self._meta.popitem(last=False)
            self._arr.pop(old, None)
            self._evicted.add(old)
        return dict(meta)

    def load(self, path: str, *, color: bool = False, force_color: bool = False) -> dict:
        named=next((r["path"] for r in self.samples() if r["name"]==path),None)
        if named is not None: path=named
        real = self._check_path(path)
        note = None
        # ★2026-11-13(報告 10 / S3): 20,000×20,000 の PNG を全部復号(4 秒・1.2 GB)してから画素の上限で断っていた。
        #   見出し(PNG の IHDR、Pillow の遅延の open、npy の見出し)で画素数を先に見る。
        from fssystem import get_system
        max_pixels = int(get_system("mcp_stack_max_pixels"))
        declared = _declared_pixels(real)
        if declared is not None and declared > max_pixels:
            raise HandleError("画素が多すぎる: %s は %d 画素で、上限 mcp_stack_max_pixels=%d を超える(復号しない)"
                              % (self.display_path(real), declared, max_pixels))
        # ★2026-10-11: 根の中の壊れた png・object 配列の npy は ValueError 等を HandleError に
        # 写さず投げ、dispatch を抜けてサーバのループが死んでいた。読めない中身は理由つきで断る
        # (-32602)。npy は pickle を決して許さない。
        try:
            if real.lower().endswith(".npy"):
                arr = np.load(real, allow_pickle=False)
                if not isinstance(arr, np.ndarray) or arr.dtype.kind not in "biufc":
                    raise ValueError("数値の配列でない(dtype=%s)"
                                     % getattr(arr, "dtype", type(arr).__name__))
                sort = "image" if arr.ndim == 2 else "color" if arr.ndim == 3 and arr.shape[-1] == 3 else "any"
            else:
                import imgio
                arr = imgio.load(real, color=(color or force_color))
                is_gray = (arr.ndim == 2 or
                           (arr.ndim == 3 and arr.shape[-1] == 3 and
                            np.array_equal(arr[..., 0], arr[..., 1]) and
                            np.array_equal(arr[..., 1], arr[..., 2])))
                if is_gray and not force_color:
                    if arr.ndim == 3:
                        arr = arr[..., 0]
                    sort = "image"
                    note = "ファイルは灰色なので image で読んだ"
                else:
                    sort = "color" if arr.ndim == 3 and arr.shape[-1] == 3 else "image"
                    note = None
        except HandleError:
            raise
        except Exception as exc:                                # noqa: BLE001 - 中身は untrusted
            raise HandleError("読めない画像: %s(%s: %s)"
                              % (self.display_path(real), type(exc).__name__, str(exc)[:200])) from None
        meta = self.put(arr, sort=sort, provenance=[{"load": self.display_path(real)}])
        if note:
            meta["note"] = note
            self._meta[meta["handle"]]["note"] = note
        return meta

    def get(self, handle: str) -> tuple[dict, object]:
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
                "bytes":sum(m.get("bytes",0) for m in self._meta.values()),"max_bytes":self.max_bytes,
                "max_items": self.max_items, "roots": self.roots, "thumb_dir": self.thumb_dir}
