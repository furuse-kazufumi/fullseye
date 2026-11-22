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
import math
import os
import tempfile
from collections import OrderedDict

import numpy as np

from .catalog import ROOT

SAMPLE_DIR = os.path.join(ROOT, "studio_assets", "sample_images")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".npy")
PREFIX = "fullseye://img/"

#: 追い出したハンドルの名前を覚えておく数の下限(実際は ``max(この数, 4 × max_items)``)。これより古い物は
#: 「知らないハンドル」として断る(断る事は同じで、理由の文が違うだけ)。
EVICTED_HISTORY_MIN = 1024
#: ``fullseye_write_viewer`` が書いた HTML を置き場に持つ上限(枚数とバイト)。超えたら古い物から消す。
MAX_VIEWER_FILES = 64
MAX_VIEWER_BYTES = 512 * 1024 * 1024


class HandleError(ValueError):
    """ハンドル/パスの拒否。JSON-RPC の -32602 に写す。"""


def default_roots() -> list[str]:
    roots = [SAMPLE_DIR]
    extra = os.environ.get("FULLSEYE_MCP_ROOT", "")
    roots += [p for p in extra.split(os.pathsep) if p.strip()]
    return roots


def _npy_header(path: str) -> tuple[tuple[int, ...], np.dtype]:
    """``.npy`` の見出し(形と dtype)だけを読む。中身は読まない(pickle も使わない)。読めなければ ValueError。"""
    from numpy.lib import format as npformat
    with open(path, "rb") as fh:
        version = npformat.read_magic(fh)
        if version == (1, 0):
            shape, _fortran, dtype = npformat.read_array_header_1_0(fh)
        elif version in ((2, 0), (3, 0)):
            shape, _fortran, dtype = npformat.read_array_header_2_0(fh)
        else:
            raise ValueError("知らない .npy の版 %r" % (version,))
    return tuple(int(n) for n in shape), np.dtype(dtype)


def _declared_pixels(path: str) -> int | None:
    """画像ファイルの見出しが宣言する画素数(高さ × 幅)。読めなければ None(その時は復号の後の上限が効く)。"""
    import struct
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".npy":
            shape, _dtype = _npy_header(path)
            return math.prod(shape[:2]) if len(shape) >= 2 else math.prod(shape)
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


def _tree_arrays(value) -> tuple[dict[int, np.ndarray], int]:
    """値の中の配列(``id`` → 配列)と、配列でない部分の大きさ(バイト)。dict・list・tuple の入れ子を全部たどる。

    ★2026-11-15(独立レビュー、PR #318): 以前は dict・list を ``len(repr(...))`` で数えていた。repr は大きい配列を
    「...」で省くので、128 MB の配列を入れた表が 271 バイトになり、上限 128 MiB の置き場に 6 つ入れても追い出しが
    起きなかった(実際は 768 MB を持ったまま)。配列は ``nbytes``、文字列は UTF-8 の長さ、他の葉は 8 バイトで数える。
    同じ配列(同じ物)は 1 回だけ。再帰しない(深い入れ子でも RecursionError にならない)。"""
    arrays: dict[int, np.ndarray] = {}
    other = 0
    seen: set[int] = set()
    todo = [value]
    while todo:
        item = todo.pop()
        if isinstance(item, np.ndarray):
            arrays[id(item)] = item
        elif isinstance(item, (dict, list, tuple)):
            if id(item) in seen:
                continue
            seen.add(id(item))
            if isinstance(item, dict):
                for key, sub in item.items():
                    other += len(str(key).encode("utf-8", "replace"))
                    todo.append(sub)
            else:
                todo.extend(item)
        elif isinstance(item, str):
            other += len(item.encode("utf-8", "replace"))
        elif isinstance(item, (bytes, bytearray)):
            other += len(item)
        else:
            other += 8
    return arrays, other


def value_nbytes(value) -> int:
    """値の大きさ(バイト): 入れ子の中の配列の ``nbytes`` の和(同じ配列は 1 回)+ 配列でない部分。

    ハンドル置き場の上限と、pipeline の中間の上限(``server._value_nbytes``)が同じ数え方を使う。"""
    arrays, other = _tree_arrays(value)
    return sum(int(a.nbytes) for a in arrays.values()) + other


class _Key:
    """:func:`_hash_tree` の作業の列で、dict の鍵を値と区別する印。"""
    __slots__ = ("key",)

    def __init__(self, key):
        self.key = key


def _hash_tree(h, value) -> None:
    """値の中身をハッシュに入れる。配列は dtype・形・バイト列ごと(repr で省かない)。dict は鍵の順に依らない。

    ★2026-11-15(独立レビュー、PR #318): 以前は ``json.dumps(..., default=repr)`` で、repr は 1000 要素を超える
    配列を「...」で省く。zeros(5000) と、[2500] だけ 1 にした配列の表が同じハンドルになり(dedup)、2 回目の
    読み出しで前の値(0.0)が返った。型の名前も入れる(list と tuple、1 と 1.0、int の鍵と str の鍵を分ける)。"""
    seen: set[int] = set()
    todo = [value]
    while todo:
        item = todo.pop()
        if isinstance(item, _Key):
            key = item.key
            h.update(("K%s:%r|" % (type(key).__name__, key)).encode("utf-8", "replace"))
        elif isinstance(item, np.ndarray):
            arr = np.ascontiguousarray(item)
            h.update(("A%s|%s|" % (arr.dtype.str, arr.shape)).encode())
            if arr.dtype.kind == "O":
                h.update(repr(arr.tolist()).encode("utf-8", "replace"))      # tolist の repr は省かない
            else:
                h.update(arr.tobytes())
        elif isinstance(item, (dict, list, tuple)):
            if id(item) in seen:
                h.update(b"R|")                                           # 同じ物の 2 回目(循環も止める)
                continue
            seen.add(id(item))
            if isinstance(item, dict):
                h.update(("D%d|" % len(item)).encode())
                for key in sorted(item, key=lambda k: (type(k).__name__, str(k)), reverse=True):
                    todo.append(item[key])
                    todo.append(_Key(key))                                # 列の後ろから取るので、鍵 → 値の順に入る
            else:
                h.update(("%s%d|" % ("L" if isinstance(item, list) else "T", len(item))).encode())
                todo.extend(reversed(item))
        elif isinstance(item, str):
            raw = item.encode("utf-8", "surrogatepass")
            h.update(b"S%d|" % len(raw))
            h.update(raw)
        elif isinstance(item, (bytes, bytearray)):
            h.update(b"B%d|" % len(item))
            h.update(bytes(item))
        else:
            h.update(("V%s:%r|" % (type(item).__name__, item)).encode("utf-8", "replace"))


class HandleStore:
    def __init__(self, roots: list[str] | None = None, *, max_items: int = 256,
                 max_bytes: int | None = None, thumb_dir: str | None = None,
                 max_viewer_files: int = MAX_VIEWER_FILES, max_viewer_bytes: int = MAX_VIEWER_BYTES):
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
        # ★2026-11-15(外部レビュー、Codex): 追い出したハンドルの名前を集合に足し続けていた(max_items=4 で 5,000 回
        #   入れると 4,996 件)。新しい物から max_evicted 件だけ覚える。追い出した時に、そのハンドルの小図も消す
        #   (以前は残り続けた)。名前(sha256 の先頭 64 bit)が同じでも中身の digest が違えば、dedup と答えずに断る。
        self._evicted: OrderedDict[str, str] = OrderedDict()           # 追い出した名前 → 中身の sha256(全桁)
        self.max_evicted = max(EVICTED_HISTORY_MIN, 4 * self.max_items)
        self._digests: dict[str, str] = {}                              # ハンドル → 中身の sha256(全桁)
        self._files: dict[str, set[str]] = {}                           # ハンドル → そのハンドルの小図
        self._viewers: OrderedDict[str, tuple[str, int]] = OrderedDict() # normcase(HTML) → (実際のパス, バイト)(古い順)
        self.max_viewer_files = int(max_viewer_files)
        self.max_viewer_bytes = int(max_viewer_bytes)
        self._seq = 0
        # ★2026-11-15: 上限は「実際に持っているバイト」で数える。pipeline は表を入れた後、表の中の 2-D の配列を
        #   image のハンドルにも入れる(同じ配列)。ハンドルごとに足すと 2 回数え、上限の半分を超える配列の表は、
        #   自分の欄のハンドルを入れた時に追い出される。配列は物ごとに 1 回だけ数える(参照の数を持つ)。
        self._parts: dict[str, tuple[tuple[int, ...], int]] = {}       # ハンドル → (配列の id, 配列でない大きさ)
        self._array_refs: dict[int, list] = {}                         # 配列の id → [配列, 持っているハンドルの数]
        self._held = 0

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
    def _digest(arr, sort: str = "") -> str:
        """中身と型(sort)の sha256(全桁)。ハンドルの名前はこの先頭 16 桁。"""
        h = hashlib.sha256()
        if isinstance(arr, np.ndarray):
            h.update(np.ascontiguousarray(arr).tobytes())
            h.update(("%s|%s|%s" % (arr.shape, arr.dtype, sort)).encode())
        else:
            h.update((type(arr).__name__ + "|" + sort + "|").encode("utf-8"))
            _hash_tree(h, arr)
        return h.hexdigest()

    @staticmethod
    def _hid(arr, sort: str = "") -> str:
        return PREFIX + HandleStore._digest(arr, sort)[:16]

    def _drop(self, handle: str) -> None:
        """ハンドルを追い出す(参照の無くなった配列のバイトを、持っているバイトから引く)。"""
        digest = self._digests.get(handle)
        self._meta.pop(handle, None)
        self._arr.pop(handle, None)
        self._digests.pop(handle, None)
        if digest is not None:
            self._evicted[handle] = digest
        self._evicted.move_to_end(handle)
        while len(self._evicted) > self.max_evicted:
            self._evicted.popitem(last=False)
        # そのハンドルの小図と、生きていないハンドルに書かれた小図(書いた時には追い出されていた物)を消す
        for owner in [handle] + [h for h in self._files if h not in self._meta and h != handle]:
            for path in self._files.pop(owner, ()):
                try:
                    os.remove(path)
                except OSError:
                    pass
        ids, other = self._parts.pop(handle, ((), 0))
        self._held -= other
        for aid in ids:
            ref = self._array_refs.get(aid)
            if ref is None:
                continue
            ref[1] -= 1
            if ref[1] <= 0:
                self._held -= int(ref[0].nbytes)
                del self._array_refs[aid]

    def _new_bytes(self, arrays: dict, other: int) -> int:
        """この値を足すと増えるバイト(置き場がもう持っている配列は数えない)。"""
        return other + sum(int(a.nbytes) for aid, a in arrays.items() if aid not in self._array_refs)

    def put(self, arr, *, sort: str, provenance: list) -> dict:
        if isinstance(arr, (list, tuple)) and sort in {"image","images","seq<image>","points","volume"}:
            arr = np.asarray(arr)
        arrays, other = _tree_arrays(arr)
        size = sum(int(a.nbytes) for a in arrays.values()) + other
        if size > self.max_bytes:                                     # 上限を超える値はハッシュも取らない
            raise HandleError("handle requires %d bytes, above byte limit %d" % (size,self.max_bytes))
        digest = self._digest(arr, sort)
        hid = PREFIX + digest[:16]
        if hid in self._meta:
            if self._digests.get(hid) != digest:
                raise HandleError("ハンドルの名前の衝突: %s に別の中身が既にある(中身の sha256 が違う)。"
                                  "取り違えないよう、入れずに断る" % hid)
            self._meta.move_to_end(hid)
            return dict(self._meta[hid], dedup=True)
        # ★2026-11-22(独立レビュー): 追い出し時に digest を捨てたため、同じ先頭 64 bit の名前を別の中身に使い回せた。
        if hid in self._evicted and self._evicted[hid] != digest:
            raise HandleError("ハンドルの名前の衝突: %s に別の中身が既にある(中身の sha256 が違う)。"
                              "取り違えないよう、入れずに断る" % hid)
        self._evicted.pop(hid, None)        # 作り直したハンドルは生きている(追い出し印を消す)
        while self._meta and self._held + self._new_bytes(arrays, other) > self.max_bytes:
            self._drop(next(iter(self._meta)))
        self._seq += 1
        meta = {"handle": hid, "sort": sort,
                "shape": list(arr.shape) if isinstance(arr, np.ndarray) else None,
                "dtype": str(arr.dtype) if isinstance(arr, np.ndarray) else type(arr).__name__,
                "array": isinstance(arr, np.ndarray),
                "bytes": size,
                "provenance": list(provenance), "seq": self._seq}
        self._meta[hid] = meta
        self._arr[hid] = arr
        self._digests[hid] = digest
        self._held += other
        for aid, item in arrays.items():
            ref = self._array_refs.get(aid)
            if ref is None:
                self._array_refs[aid] = [item, 1]                  # 配列を持つので、生きている間 id は使い回されない
                self._held += int(item.nbytes)
            else:
                ref[1] += 1
        self._parts[hid] = (tuple(arrays), other)
        while len(self._meta) > self.max_items:
            self._drop(next(iter(self._meta)))
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
        if real.lower().endswith(".npy"):
            # ★2026-11-15(外部レビュー、Codex の疑い 1): 画素数(shape[:2])しか見ず、(1, 1, N) の配列は「1 画素」として
            #   全部復号してから置き場の上限で断った(数でない dtype も全部読んでから断った)。見出しの dtype と全体の
            #   バイト(要素の数 × itemsize)を、復号する前に見る。
            try:
                shape, dtype = _npy_header(real)
            except Exception as exc:                            # noqa: BLE001 - 中身は untrusted
                raise HandleError("読めない画像: %s(.npy の見出しが読めない: %s)"
                                  % (self.display_path(real), str(exc)[:200])) from None
            if dtype.kind not in "biufc":
                raise HandleError("読めない画像: %s(数値の配列でない .npy、dtype=%s。復号しない)"
                                  % (self.display_path(real), dtype))
            nbytes = math.prod(shape) * dtype.itemsize
            if nbytes > self.max_bytes:
                raise HandleError("配列が大きすぎる: %s は %d バイトで、置き場の上限 %d バイトを超える(復号しない)"
                                  % (self.display_path(real), nbytes, self.max_bytes))
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
        self._files.setdefault(handle, set()).add(path)                # 追い出す時に消す
        return path

    def write_viewer(self, name: str, text: str) -> str:
        """``<name>.html`` を作業ディレクトリに書く(名前の検査は呼び出し側)。

        新しい物から :attr:`max_viewer_files` 枚・:attr:`max_viewer_bytes` バイトまでを持ち、超えたら古い物から消す。
        同じ名前は書き換え。1 枚で枠を超える物は書かずに断る(HandleError → -32602)。"""
        data = text.encode("utf-8")
        if len(data) > self.max_viewer_bytes:
            raise HandleError("ビューアが %d バイトで、置き場の枠 %d バイトを超える(書かない)"
                              % (len(data), self.max_viewer_bytes))
        path = os.path.join(self.thumb_dir, name + ".html")
        # ★2026-11-22(独立レビュー): Windows で大文字小文字だけ違う名前を別の台帳行にし、
        #   古い行を追い出す時に新しい行と同じ実体を消した。normcase した鍵で書き換えにする。
        key = os.path.normcase(path)
        previous = self._viewers.pop(key, None)
        if previous is not None and previous[0] != path:
            try:
                os.remove(previous[0])
            except OSError:
                pass
        while self._viewers and (len(self._viewers) >= self.max_viewer_files
                                 or sum(row[1] for row in self._viewers.values()) + len(data) > self.max_viewer_bytes):
            _old_key, (old, _size) = self._viewers.popitem(last=False)
            try:
                os.remove(old)
            except OSError:
                pass
        with open(path, "wb") as fh:
            fh.write(data)
        self._viewers[key] = (path, len(data))
        return path

    def stats(self) -> dict:
        return {"alive": len(self._meta), "evicted": len(self._evicted),
                "bytes":self._held,"max_bytes":self.max_bytes,
                "max_items": self.max_items, "roots": self.roots, "thumb_dir": self.thumb_dir}
