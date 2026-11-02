#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Score every GPU-tier operator on the mechanical GPU path (:mod:`gpu_shadow`).

GPU 向き op(``gpu_tier`` = required / suitable)を 1 件ずつ手書きせず、既存の numpy/scipy
実装を CuPy 配列で走らせて採点する。段階は 4 つで、どれも JSONL に追記し再開できる。

    py tools/gpu_auto_sweep.py cpu    --jobs 6                  # GPU を使わない下見
    py tools/gpu_auto_sweep.py parity --gpu-lock <file>         # 小入力で CPU と比較
    py tools/gpu_auto_sweep.py scale_cpu --jobs 3               # 実寸の CPU 基準線(GPU 不要)
    py tools/gpu_auto_sweep.py scale  --gpu-lock <file>         # 実寸で転送込みの倍率
    py tools/gpu_auto_sweep.py report                           # 分類・許可リスト・文書

* ``cpu``: op を CPU で走らせ、呼び出した本体ライブラリ(cv2 / skimage …)と、入力を 2 倍に
  したときの Python 行数の伸びを記録する。入力に比例して行数が増える op は GPU へ送っても
  転送が増えるだけなので、後で python_loop に分類する。
* ``parity``: 同じ入力・同じ種で CPU と GPU を実行し、例外 / NaN / 内部差を見る。出力が
  定数の op は一致とみなさない(``vacuous``)。
* ``scale_cpu`` / ``scale``: 一致した op だけ実寸で測る。CPU の基準線と間引いた出力を先に
  ロックの外で作り、GPU の時間だけロックの中で測る。GPU の時間は host→device 転送・計算・
  device→host 転送のすべてを含む(``.get()`` が同期になる)。

Fail-soft: 1 op のハングや落下はドライバが子プロセスを殺して先へ進む。GPU の取り合いは
ロックファイルで防ぐ: 自分の名前でロックを作り 1 回 10 分未満で必ず消す。他人のロックと
``UnrealEditor`` が居る間は GPU を使わず待つ。
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import math
import os
import random
import re
import subprocess
import sys
import threading
import time
import traceback
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "out" / "gpu_auto_sweep"
TIER_BRANCH = "feat/gpu-programme-2-2026-11-02"
#: 内部差の合格線(出力の振れ幅に対する比)。``accel`` の faithful 基準と同じ 5e-3。
TOL = 5e-3
#: 採用の下限(転送込み)。
MIN_RATIO = 5.0
#: 実寸。画像 2048²、体積 256³、信号 2**20。
REAL = {"grid2": 2048, "grid3": 256, "signal": 1 << 20, "matrix": 1024, "points": 200_000,
        "video_xy": 512, "lf_xy": 256}
#: これらの本体が op の中で呼ばれたら「包み」の候補。
WATCH = ("cv2", "skimage", "PIL", "sklearn", "pywt", "mahotas", "SimpleITK", "torch", "kornia")
#: 空間軸の決まった sort。(ndim, 空間軸)の組。
GRID_SORTS = {
    "image": None, "image2d": None, "region": None, "depth": None, "mask": None,
    "color": None, "rgbimage": None, "rgb": None, "rgba": None, "rgba_premul": None,
    "lab": None, "normalmap": None, "pointmap": None, "qimage": None, "cimage": None,
    "volume": None, "voxel": None, "sdf": None, "rgbvolume": None, "flow2d": None,
    "flow_dense": None, "curvature": None, "gradient": None, "hessian": None,
    "coordgrid": None, "any": None, "frame": None,
}


# ---- targets ------------------------------------------------------------------- #
def load_targets() -> list:
    """``gpu_tier`` が required / suitable の索引行。master の索引に無ければ第 2 便から読む。"""
    idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    rows = idx["ops"]
    if not any("gpu_tier" in r for r in rows):
        cache = OUT / "tier_index.json"
        if not cache.exists():
            OUT.mkdir(parents=True, exist_ok=True)
            blob = subprocess.run(["git", "show", TIER_BRANCH + ":docs/OP_INDEX.json"], cwd=ROOT,
                                  capture_output=True, check=True).stdout
            cache.write_bytes(blob)
        rows = json.loads(cache.read_text(encoding="utf-8"))["ops"]
    return [r for r in rows if r.get("gpu_tier") in ("required", "suitable")]


def read_rows(stage: str) -> dict:
    """段の全行を op 名で引く。子プロセスごとのファイルを更新順に重ねる(後勝ち)。

    Windows の追記は原子的でないので、並列の子が 1 つのファイルへ書くと行が壊れる
    (実測で 3 行失った)。ファイルを分け、途中で殺された行は読み飛ばす。
    """
    out: dict = {}
    for path in sorted(OUT.glob(stage + "_[0-9]*.jsonl"), key=lambda p: p.stat().st_mtime):
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out[r["name"]] = r
                except (ValueError, KeyError):
                    pass              # 途中で殺された行
    return out


def done_names(stage: str) -> set:
    return set(read_rows(stage))


def append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


# ---- inputs -------------------------------------------------------------------- #
class Env:
    """op 名 → 呼び出し方と入力。chain_fuzz の生成器と引数ビルダをそのまま使う。"""

    def __init__(self):
        import chain_fuzz
        import imgops_nary
        import numpy as np
        import op_probe
        import ops
        import typed_catalog
        self.np, self.cf, self.probe, self.ops = np, chain_fuzz, op_probe, ops
        self.nary = {o.name: o for o in imgops_nary.build_nary()}
        self.cat = {c[0]: c for c in typed_catalog.catalog()}
        self.ordered = list(typed_catalog.catalog())
        self.gens = self._structured_gens()
        self.raw_gens = chain_fuzz.make_generators()
        self.recipe = chain_fuzz.type_recipes(self.ordered, self.raw_gens)

    def _structured_gens(self) -> dict:
        """乱数の代わりに構造のある入力を流す生成器表(無い sort は chain_fuzz のまま)。"""
        P, np = self.probe, self.np
        g = dict(self.cf.make_generators())

        def noisy(make):
            def f(rng):
                v = make()
                return np.clip(v + 0.02 * rng.standard_normal(v.shape), 0.0, 1.0)
            return f
        g["image2d"] = noisy(lambda: P.structured_image(32))
        g["voxel"] = noisy(lambda: P.structured_volume(16))
        g["signal"] = noisy(lambda: P.structured_signal(256))
        g["video"] = noisy(P.structured_video)
        g["points"] = lambda rng: P.structured_points(160)
        g["qimage"] = lambda rng: P.structured_qimage()
        g["cimage"] = lambda rng: P.structured_cimage()
        g["lightfield"] = lambda rng: P.structured_lightfield()
        return g

    def kind(self, name: str):
        if name in self.ops.RT:
            return "registry"
        if name in self.nary:
            return "nary"
        if name in self.cat:
            return "ledger"
        return None

    def fn(self, name: str):
        k = self.kind(name)
        if k == "registry":
            return self.ops.RT[name]
        if k == "nary":
            return self.nary[name].fn
        return self.cat[name][4]

    def sorts(self, name: str) -> list:
        k = self.kind(name)
        if k == "registry":
            return [self.ops._BY_NAME[name].in_sort]
        if k == "nary":
            return list(self.nary[name].in_sorts)
        return list(self.cat[name][2])

    def probes(self, name: str) -> list:
        """[(args, kwargs), ...]。先頭が構造入力。作れなければ空。"""
        k = self.kind(name)
        np = self.np
        seed = zlib.crc32(name.encode("utf-8"))
        if k == "registry":
            sort = self.sorts(name)[0]
            ovr = self.probe.OP_PROBE_OVERRIDE.get(name)
            if ovr is not None:
                vs = [ovr[0]()]
            else:
                pair = self.probe.sample_pair(sort, np.random.default_rng(seed))
                vs = list(reversed(pair))
            if not vs:
                return []
            out = [((vs[0], 0.5, 0.5), {}), ((vs[0], 0.3, 0.7), {})]
            out += [((v, 0.5, 0.5), {}) for v in vs[1:]]
            return out
        if k == "nary":
            rng = np.random.default_rng(seed)
            vals = [self.probe.sample_input(s, rng, structured=True) for s in self.sorts(name)]
            if any(v is None for v in vals):
                return []
            # 2 枚が同一だと差を取る op が定数になる
            vals = [v if i == 0 else np.roll(v, 3 * i, axis=0) for i, v in enumerate(vals)]
            return [((vals, 0.5, 0.5), {}), ((vals, 0.3, 0.7), {})]
        if k == "ledger":
            return self._ledger_probes(name, seed)
        return []

    def _ledger_probes(self, name: str, seed: int) -> list:
        """``chain_fuzz`` の 1 手を走らせ、対象 op に渡る引数をそのまま捕まえる。"""
        got = []
        self.last_err = None
        for gens in (self.gens, self.raw_gens):
            hit = self._capture(name, gens, seed)
            if hit is not None:
                got.append(hit)
        return got

    def _capture(self, name, gens, seed):
        cf, np = self.cf, self.np
        row = self.cat[name]
        real = row[4]
        box = {}

        def spy(*a, **k):
            # 走らない入力は捕まえない(次の種へ)。走る入力だけが比較の材料になる
            ca, ck = copy.deepcopy(a), copy.deepcopy(k)
            try:
                real(*copy.deepcopy(a), **copy.deepcopy(k))
            except Exception as e:  # noqa: BLE001
                box["err"] = e
                raise
            box["a"] = (ca, ck)
            raise _Captured()
        try:
            import functools
            functools.update_wrapper(spy, real)
        except (AttributeError, TypeError):
            pass
        ops = [(row[0], row[1], row[2], row[3], spy) if c[0] == name else c for c in self.ordered]
        script = cf.cover_script(row, self.recipe)
        if script is None:
            return None
        for k in range(6):
            s = (seed + k * 101) & 0x7fffffff
            log: list = []
            try:
                cf.run_chain(ops, gens, np.random.default_rng(s), 0, log, chain_seed=s,
                             script=script)
            except _Captured:
                pass
            except Exception:  # noqa: BLE001 - レシピの途中の op の失敗は次の種へ
                continue
            if "a" in box:
                return box["a"]
        if "err" in box:
            self.last_err = box["err"]
        return None


class _Captured(BaseException):
    """chain_fuzz の ``except Exception`` を抜けるための合図。"""


def _spatial_axes(a, sort):
    """配列の空間軸。空間の無い(小さい固定形の)配列は None。"""
    n = a.ndim
    if n == 1:
        return (0,) if a.size >= 32 else None
    if n == 2:
        if sort == "points" or a.shape[1] <= 8:
            return None
        return (0, 1)
    if n == 3:
        if a.shape[2] <= 4:
            return (0, 1)
        if sort == "video":
            return (1, 2)
        return (0, 1, 2)
    if n == 4:
        if a.shape[3] <= 4 and sort in ("rgbvideo", "rgbvolume"):
            return (1, 2) if sort == "rgbvideo" else (0, 1, 2)
        return (2, 3)
    return None


def _zoom_axes(a, axes, target, np):
    """*axes* の長さを *target* へ線形補間する(補間で構造を保つ)。cv2 は使わない。"""
    from scipy import ndimage
    if a.dtype.kind == "c":
        return _zoom_axes(a.real, axes, target, np) + 1j * _zoom_axes(a.imag, axes, target, np)
    z = [1.0] * a.ndim
    for ax in axes:
        z[ax] = target / float(a.shape[ax])
    order = 0 if a.dtype.kind in "biu" else 1
    b = ndimage.zoom(a.astype(np.float64) if order else a, z, order=order, grid_mode=False)
    return b.astype(a.dtype) if a.dtype.kind in "biu" or order == 0 else b


def scale_value(v, sort, size_for, seen, np):
    """1 つの葉を拡大する。``seen`` は最初に見た空間形(同じ形の葉を揃えて拡大する)。"""
    if isinstance(v, np.ndarray):
        if v.dtype.kind not in "biufc":
            return v
        if sort is None:
            # kwargs 側の配列: 主入力と同じ空間形のものだけ揃える
            if seen.get("shape") is None or v.ndim < len(seen["axes"]):
                return v
            ax = seen["axes"]
            if tuple(v.shape[i] for i in ax) != seen["shape"]:
                return v
            return _zoom_axes(v, ax, seen["target"], np)
        ax = _spatial_axes(v, sort)
        if ax is None:
            return v
        target = size_for(len(ax), sort)
        if seen.get("shape") is None:
            seen.update(shape=tuple(v.shape[i] for i in ax), axes=ax, target=target)
        return _zoom_axes(v, ax, target, np)
    if isinstance(v, list):
        return [scale_value(x, sort, size_for, seen, np) for x in v]
    if isinstance(v, tuple):
        return tuple(scale_value(x, sort, size_for, seen, np) for x in v)
    if isinstance(v, dict):
        return {k: scale_value(x, sort, size_for, seen, np) for k, x in v.items()}
    return v


def scale_args(env, name, args, kwargs, size_for):
    """入力を *size_for* の大きさへ。何も拡大できなければ None(固定形の op)。"""
    np = env.np
    sorts = env.sorts(name)
    seen: dict = {}
    if env.kind(name) in ("registry", "nary"):
        head = args[0] if env.kind(name) == "registry" else args[0]
        new = scale_value(head, sorts[0], size_for, seen, np)
        if not seen:
            return None
        return (new,) + tuple(args[1:]), dict(kwargs)
    out = []
    for i, v in enumerate(args):
        s = sorts[i] if i < len(sorts) else None
        if s == "points" or s in ("table", "mesh", "pose", "measurement"):
            out.append(v)
            continue
        out.append(scale_value(v, s if s in GRID_SORTS or s in ("signal", "video", "lightfield",
                                                                "beatcube", "matrix", "images",
                                                                "sinogram", "volseq")
                               else None, size_for, seen, np))
    if not seen:
        return None
    kw = {k: scale_value(v, None, size_for, seen, np) for k, v in kwargs.items()}
    return tuple(out), kw


def double_size(a_len, sort, base=None):
    """2 倍入力の大きさ(行数の伸びを測る)。"""
    return 0


# ---- comparison ---------------------------------------------------------------- #
def leaves(x, np, path=""):
    """出力の数値の葉を (path, 値) で列挙。数値でない葉はそのまま返す。"""
    if isinstance(x, dict):
        for k in sorted(x, key=str):
            yield from leaves(x[k], np, "%s.%s" % (path, k))
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            yield from leaves(v, np, "%s[%d]" % (path, i))
    else:
        yield path, x


def compare(c, g, np, tol=TOL) -> dict:
    """CPU 出力 *c* と GPU 出力 *g* の比較。差は葉ごとに振れ幅で正規化する。"""
    lc, lg = list(leaves(c, np)), list(leaves(g, np))
    if len(lc) != len(lg):
        return {"ok": False, "why": "structure: %d vs %d leaves" % (len(lc), len(lg))}
    worst, nonconst, nnum = 0.0, False, 0
    for (p, a), (q, b) in zip(lc, lg):
        if p != q:
            return {"ok": False, "why": "structure: %s vs %s" % (p, q)}
        if isinstance(a, (str, bytes, type(None), bool)) and not isinstance(b, np.ndarray):
            if a != b:
                return {"ok": False, "why": "value at %s" % p}
            continue
        try:
            aa, bb = np.asarray(a), np.asarray(b)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "why": "opaque at %s: %s" % (p, e)}
        if aa.dtype.kind not in "biufc":
            if aa.dtype.kind == "O" or bb.dtype.kind not in "biufcUS":
                continue          # 数えない(不透明な葉)
            if aa.dtype.kind in "US" and not np.array_equal(aa, bb):
                return {"ok": False, "why": "value at %s" % p}
            continue
        if bb.dtype.kind not in "biufc":
            return {"ok": False, "why": "type at %s: %s vs %s" % (p, aa.dtype, bb.dtype)}
        if aa.shape != bb.shape:
            return {"ok": False, "why": "shape at %s: %s vs %s" % (p, aa.shape, bb.shape)}
        nnum += 1
        if aa.size == 0:
            continue
        aa = aa.astype(np.complex128 if aa.dtype.kind == "c" else np.float64)
        bb = bb.astype(np.complex128 if bb.dtype.kind == "c" else np.float64)
        na, nb = ~np.isfinite(aa), ~np.isfinite(bb)
        if not np.array_equal(na, nb):
            return {"ok": False, "why": "nan-mask at %s: cpu %d gpu %d"
                    % (p, int(na.sum()), int(nb.sum()))}
        keep = ~na
        if aa.ndim >= 2 and min(aa.shape[:2]) >= 16:   # 内部だけ比べる(端の規約は別問題)
            m = max(4, min(aa.shape[:2]) // 16)
            mask = np.zeros(aa.shape, bool)
            mask[m:-m, m:-m] = True
            keep &= mask
        if not keep.any():
            continue
        ca, cb = aa[keep], bb[keep]
        span = float(np.abs(ca - ca.flat[0]).max()) * 2.0 if ca.size > 1 else 0.0
        span = max(span, float(np.ptp(np.abs(ca))) if ca.size > 1 else 0.0)
        if ca.size > 1 and span > 0:
            nonconst = True
        scale = max(span, float(np.abs(ca).max()) * (1.0 if ca.size == 1 else 0.0), 1e-6)
        d = float(np.abs(ca - cb).max())
        worst = max(worst, d / scale)
    return {"ok": worst < tol, "rel": worst, "nonconst": nonconst, "numeric": nnum,
            "why": None if worst < tol else "rel %.3g" % worst}


def digest(x, np) -> str:
    """出力の要約(プローブ間で出力が変わるか=定数でないかを見る)。"""
    h = 0
    for p, v in leaves(x, np):
        try:
            a = np.round(np.asarray(v, dtype=np.complex128), 9)
            h = zlib.crc32(a.tobytes(), h)
        except (TypeError, ValueError):
            h = zlib.crc32(repr(v).encode("utf-8", "replace")[:200], h)
    return "%08x" % h


def where_failed(exc) -> dict:
    """例外の位置: 最後の project 枠と、最後の第三者ライブラリ枠。"""
    tb = traceback.extract_tb(exc.__traceback__)
    proj, lib = None, None
    for fr in tb:
        fn = fr.filename.replace("\\", "/")
        if fn.startswith(str(ROOT).replace("\\", "/")) and "/tools/" not in fn \
                and not fn.endswith("gpu_shadow.py"):
            proj = "%s:%d" % (os.path.basename(fn), fr.lineno)
        elif "site-packages" in fn:
            lib = fn.split("site-packages/")[-1].split("/")[0]
    return {"at": proj, "lib": lib}


def classify_exc(exc) -> str:
    """GPU 経路の例外を理由に分ける。文面は CuPy 13 の実物。"""
    msg = str(exc)
    w = where_failed(exc)
    t = type(exc).__name__
    if t == "OutOfMemoryError":
        return "oom"
    if "Expected Ptr<cv::UMat>" in msg or "cv2." in msg or "cv::" in msg or w["lib"] == "cv2":
        return "wrapper_cv2"
    if w["lib"] in ("skimage", "PIL", "sklearn", "pywt", "mahotas", "SimpleITK", "kornia",
                    "torch"):
        return "wrapper_" + w["lib"]
    if "Implicit conversion to a NumPy array" in msg:
        return "implicit_numpy"
    if "Unsupported type" in msg:
        return "numpy_cupy_mix"
    if t == "AttributeError":
        return "missing_attr"
    if "Implicit conversion" in msg or "__array__" in msg:
        return "implicit_numpy"
    if "unhashable" in msg:
        return "unhashable_array"
    if t in ("NotImplementedError",):
        return "not_implemented"
    if t == "TypeError":
        return "type_error"
    if t == "ValueError":
        return "value_error"
    if t == "IndexError":
        return "index_error"
    return t


# ---- worker stages ------------------------------------------------------------- #
def _seed(np):
    np.random.seed(20261102)
    random.seed(20261102)


def _project_prefix():
    return str(ROOT)


def count_lines(call) -> int:
    """project 内の Python 行数(numpy の中は数えない)。"""
    n = [0]
    pre = _project_prefix()

    def tr(frame, event, arg):
        if event == "call":
            return tr if frame.f_code.co_filename.startswith(pre) else None
        if event == "line":
            n[0] += 1
        return tr
    sys.settrace(tr)
    try:
        call()
    except Exception:  # noqa: BLE001 - 行数だけ欲しい
        pass
    finally:
        sys.settrace(None)
    return n[0]


def libs_used(call) -> dict:
    """呼ばれた本体ライブラリの回数(cv2 は C 関数、他は Python 枠で見える)。"""
    c: collections.Counter = collections.Counter()
    cv2 = sys.modules.get("cv2")
    cv2_ids = {id(v) for v in vars(cv2).values() if callable(v)} if cv2 else set()

    def prof(frame, event, arg):
        if event == "c_call":
            if id(arg) in cv2_ids:          # cv2 の関数は __module__ が None
                c["cv2"] += 1
        elif event == "call":
            fn = frame.f_code.co_filename.replace("\\", "/")
            if "site-packages/" in fn:
                top = fn.split("site-packages/")[-1].split("/")[0]
                if top in WATCH:
                    c[top] += 1
    sys.setprofile(prof)
    try:
        call()
    except Exception:  # noqa: BLE001
        pass
    finally:
        sys.setprofile(None)
    return dict(c)


def nelem(args, np) -> int:
    n = 0
    for _p, v in leaves(args, np):
        if isinstance(v, np.ndarray):
            n += v.size
    return n


def stage_cpu(env, name: str) -> dict:
    np = env.np
    row = {"name": name, "stage": "cpu", "kind": env.kind(name)}
    if row["kind"] is None:
        return dict(row, status="no_backend")
    try:
        probes = env.probes(name)
    except Exception as e:  # noqa: BLE001
        return dict(row, status="no_probe", err=repr(e)[:200])
    if not probes:
        err = getattr(env, "last_err", None)
        if err is not None:
            return dict(row, status="cpu_exception", err=repr(err)[:200], **where_failed(err))
        return dict(row, status="no_probe")
    fn = env.fn(name)
    args, kw = probes[0]
    row["n_probes"] = len(probes)
    _seed(np)
    t0 = time.perf_counter()
    try:
        out = fn(*copy.deepcopy(args), **copy.deepcopy(kw))
    except Exception as e:  # noqa: BLE001
        w = where_failed(e)
        return dict(row, status="cpu_exception", err=repr(e)[:200], **w)
    row["t_small"] = time.perf_counter() - t0
    row["status"] = "ok"
    row["elems"] = nelem(args, np)
    row["libs"] = libs_used(lambda: fn(*copy.deepcopy(args), **copy.deepcopy(kw)))
    if row["t_small"] < 3.0:
        row["lines"] = count_lines(lambda: fn(*copy.deepcopy(args), **copy.deepcopy(kw)))
        try:
            first = next(v for _p, v in leaves(args, np) if isinstance(v, np.ndarray) and v.ndim)
            dbl = lambda n, s: 2 * max(first.shape)     # noqa: E731
            sc = scale_args(env, name, args, kw, dbl)
        except (StopIteration, Exception):  # noqa: BLE001
            sc = None
        if sc is not None:
            row["elems2"] = nelem(sc[0], np)
            row["lines2"] = count_lines(lambda: fn(*sc[0], **sc[1]))
    return row


def _gpu_env():
    import gpu_shadow as G
    sh = G.get_shadow()
    return G, sh


def stage_parity(env, name: str, G, shadow_cat) -> dict:
    np = env.np
    row = {"name": name, "stage": "parity", "kind": env.kind(name)}
    probes = env.probes(name)
    if not probes:
        return dict(row, status="no_probe")
    cfn, gfn = env.fn(name), shadow_cat(name)
    if gfn is None:
        return dict(row, status="no_shadow")
    res, digests, stats = [], [], None
    ran = 0
    for args, kw in probes:
        a2, k2 = copy.deepcopy(args), copy.deepcopy(kw)
        _seed(np)
        try:
            c = cfn(*a2, **k2)
        except Exception:  # noqa: BLE001 - CPU が拒否する入力は比べない
            continue
        ran += 1
        G.STATS.reset()
        _seed(np)
        a3, k3 = G.to_gpu(copy.deepcopy(args)), G.to_gpu(copy.deepcopy(kw))
        try:
            g = G.to_cpu(gfn(*a3, **k3))
        except Exception as e:  # noqa: BLE001
            w = where_failed(e)
            return dict(row, status="gpu_exception", reason=classify_exc(e), err=str(e)[:220],
                        exc=type(e).__name__, stats=G.STATS.as_dict(), **w)
        stats = G.STATS.as_dict()
        r = compare(c, g, np)
        digests.append(digest(c, np))
        res.append(r)
        if not r["ok"]:
            return dict(row, status="mismatch", why=r["why"], stats=stats)
    if not ran:
        return dict(row, status="cpu_exception")
    nonconst = any(r.get("nonconst") for r in res)
    varies = len(set(digests)) > 1
    numeric = any(r.get("numeric") for r in res)
    status = "match" if numeric and (nonconst or varies) else "vacuous"
    return dict(row, status=status, rel=max(r.get("rel", 0.0) for r in res), probes=ran,
                nonconst=nonconst, varies=varies, stats=stats)


def real_size(n_axes, sort):
    if n_axes == 1:
        return REAL["signal"]
    if n_axes == 3:
        return REAL["grid3"]
    if sort == "video":
        return REAL["video_xy"]
    if sort in ("lightfield",):
        return REAL["lf_xy"]
    if sort == "matrix":
        return REAL["matrix"]
    return REAL["grid2"]


def thin(x, np, limit=4096):
    """実寸の出力を間引いて残す(全部残すと 1000 op × 32 MB になる)。形は 2 回とも同じ規則。"""
    if isinstance(x, dict):
        return {k: thin(v, np, limit) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [thin(v, np, limit) for v in x]
    if isinstance(x, np.ndarray) and x.size > limit and x.ndim:
        step = max(2, int(math.ceil((x.size / float(limit)) ** (1.0 / min(x.ndim, 3)))))
        idx = tuple(slice(None, None, step) if i < 3 else slice(None) for i in range(x.ndim))
        return x[idx].copy()
    return x


def stage_scale_cpu(env, name: str, cpu_budget: float) -> dict:
    """実寸の CPU 基準線。GPU を使わないのでロックの外で走らせる。"""
    import pickle
    np = env.np
    row = {"name": name, "stage": "scale_cpu", "kind": env.kind(name)}
    args, kw = env.probes(name)[0]
    sc = scale_args(env, name, args, kw, real_size)
    if sc is None:
        return dict(row, status="fixed_input")
    sargs, skw = sc
    row["elems"] = nelem(sargs, np)
    row["shape"] = next((v.shape for _p, v in leaves(sargs, np)
                         if isinstance(v, np.ndarray)), None)
    cfn = env.fn(name)
    t_cpu = []
    c = None
    try:
        for _ in range(2):
            a, k = copy.deepcopy(sargs), copy.deepcopy(skw)
            _seed(np)
            t0 = time.perf_counter()
            c = cfn(*a, **k)
            t_cpu.append(time.perf_counter() - t0)
            if t_cpu[-1] > cpu_budget:
                break
    except Exception as e:  # noqa: BLE001
        return dict(row, status="cpu_exception_at_scale", err=repr(e)[:200])
    d = OUT / "thin"
    d.mkdir(exist_ok=True)
    with (d / (name + ".pkl")).open("wb") as f:
        pickle.dump(thin(c, np), f)
    return dict(row, status="measured", t_cpu=min(t_cpu))


def stage_scale(env, name: str, G, shadow_cat, base: dict) -> dict:
    """実寸の GPU 時間。転送 → 計算 → 転送(``.get()`` が同期)をすべて含む。"""
    import pickle
    np = env.np
    row = {"name": name, "stage": "scale", "kind": env.kind(name),
           "shape": base.get("shape"), "elems": base.get("elems"), "t_cpu": base.get("t_cpu")}
    args, kw = env.probes(name)[0]
    sargs, skw = scale_args(env, name, args, kw, real_size)
    # 転送だけで下限が決まる op は測らない(往復の帯域を上限 16 GB/s と置いても 5 倍に届かない)
    nbytes = sum(v.nbytes for _p, v in leaves((sargs, skw), np) if isinstance(v, np.ndarray))
    if base["t_cpu"] < MIN_RATIO * 2.0 * nbytes / 16e9:
        return dict(row, status="transfer_bound", nbytes=nbytes)
    gfn = shadow_cat(name)
    with (OUT / "thin" / (name + ".pkl")).open("rb") as f:
        c = pickle.load(f)
    import cupy
    # 準備運転: CuPy のカーネルコンパイルを測定に混ぜない
    try:
        G.to_cpu(gfn(*G.to_gpu(copy.deepcopy(args)), **G.to_gpu(copy.deepcopy(kw))))
    except Exception as e:  # noqa: BLE001
        return dict(row, status="gpu_exception_at_scale", reason=classify_exc(e), err=str(e)[:220])
    t_gpu = []
    g = None
    try:
        for _ in range(3):
            a, k = copy.deepcopy(sargs), copy.deepcopy(skw)
            G.STATS.reset()
            _seed(np)
            t0 = time.perf_counter()
            g = G.to_cpu(gfn(*G.to_gpu(a), **G.to_gpu(k)))
            t_gpu.append(time.perf_counter() - t0)
            # CPU の半分より遅ければ 5 倍には届かない。残りの反復でロックを占有しない
            if t_gpu[-1] > 20.0 or t_gpu[-1] > 0.5 * base["t_cpu"]:
                break
    except Exception as e:  # noqa: BLE001
        return dict(row, status="gpu_exception_at_scale", reason=classify_exc(e),
                    err=str(e)[:220], **where_failed(e))
    stats = G.STATS.as_dict()
    cupy.get_default_memory_pool().free_all_blocks()
    r = compare(c, thin(g, np), np)
    tc, tg = base["t_cpu"], min(t_gpu)
    return dict(row, status="measured" if r["ok"] else "mismatch_at_scale", t_gpu=tg,
                ratio=tc / tg if tg > 0 else None, rel=r.get("rel"), why=r.get("why"),
                nonconst=r.get("nonconst"), stats=stats)


def worker(a) -> int:
    """names ファイルの op を順に処理する。各 op の前に ``START name`` を書く。"""
    os.environ.setdefault("IMGEVOLVE_STRICT_BACKENDS", "1")
    os.environ.setdefault("FULLSEYE_QUIET_FALLBACK", "1")
    cwd = OUT / "cwd"
    cwd.mkdir(parents=True, exist_ok=True)
    os.chdir(cwd)
    import warnings
    warnings.simplefilter("ignore")
    names = Path(a.names).read_text(encoding="utf-8").split()
    out = Path(a.out)
    env = Env()
    G, shadow_cat = None, None
    bases = read_rows("scale_cpu") if a.stage in ("scale", "scale_cpu") else {}
    if a.stage in ("parity", "scale"):
        G, sh = _gpu_env()
        ops_s = sh.load("ops")
        nary_s = {o.name: o.fn for o in sh.load("imgops_nary").build_nary()}
        cat_s = {c[0]: c[4] for c in sh.load("typed_catalog").catalog()}

        def shadow_cat(n):
            return ops_s.RT.get(n) or nary_s.get(n) or cat_s.get(n)
    print("READY", flush=True)
    stop = Path(a.stop) if a.stop else None
    for i, name in enumerate(names):
        if stop is not None and stop.exists():
            print("STOPPED", flush=True)
            return 0
        print("START " + name, flush=True)
        t0 = time.time()
        try:
            if a.stage == "cpu":
                row = stage_cpu(env, name)
            elif a.stage == "parity":
                row = stage_parity(env, name, G, shadow_cat)
            elif a.stage == "scale_cpu":
                row = stage_scale_cpu(env, name, a.cpu_budget)
                prev = bases.get(name, {}).get("t_cpu")
                if prev is not None and row.get("t_cpu") is not None:
                    row["t_cpu"] = min(prev, row["t_cpu"])   # 速い方 = 倍率が低く出る方を残す
                    row["rechecked"] = True
            else:
                row = stage_scale(env, name, G, shadow_cat, bases[name])
        except Exception as e:  # noqa: BLE001
            row = {"name": name, "stage": a.stage, "status": "tool_error", "err": repr(e)[:300],
                   "tb": traceback.format_exc(limit=-3)[-600:]}
        row["wall"] = round(time.time() - t0, 3)
        row["gen"] = int(os.environ.get("GPU_SWEEP_GEN", "0"))
        append(out, row)
        print("DONE " + name, flush=True)
        if G is not None and i % 8 == 7:
            import gc

            import cupy
            gc.collect()
            cupy.get_default_memory_pool().free_all_blocks()
    print("ALLDONE", flush=True)
    return 0


# ---- GPU lock ------------------------------------------------------------------ #
def unreal_running() -> bool:
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"],
                           capture_output=True, timeout=20)
        return b"UnrealEditor" in r.stdout       # 文面は OEM コードページなのでバイトで見る
    except (OSError, subprocess.SubprocessError):
        return True               # 確かめられないなら使わない(fail-closed)


class GpuLock:
    """他人のロックは待つ・消さない。自分のロックは必ず消す。"""

    def __init__(self, path, owner):
        self.path, self.owner, self.held = (Path(path) if path else None), owner, False

    def acquire(self, max_wait: float) -> bool:
        if self.path is None:
            return True
        t0 = time.time()
        while time.time() - t0 < max_wait:
            if self.path.exists():
                time.sleep(2)
                continue
            if not unreal_running():
                try:
                    fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    time.sleep(5)
                    continue
                with os.fdopen(fd, "w") as f:
                    f.write("%s %s\n" % (self.owner, time.strftime("%Y-%m-%dT%H:%M:%S")))
                self.held = True
                return True
            time.sleep(3)
        return False

    def still_mine(self) -> bool:
        if self.path is None:
            return True
        try:
            return self.path.read_text().startswith(self.owner) and not unreal_running()
        except OSError:
            return False

    def release(self) -> None:
        if self.path is not None and self.held:
            try:
                if self.path.read_text().startswith(self.owner):
                    self.path.unlink()
            except OSError:
                pass
            self.held = False


# ---- driver -------------------------------------------------------------------- #
class Slot:
    """1 子プロセス。stdout の START/DONE を見張り、1 op の時間切れで殺す。"""

    def __init__(self, stage, names, a, tag):
        self.stage, self.names, self.a, self.tag = stage, list(names), a, tag
        self.path = OUT / ("%s_%s.jsonl" % (stage, tag))
        self.current, self.since, self.done, self.finished = None, time.time(), 0, False
        self.proc = None

    def spawn(self, stop_file):
        nf = OUT / ("names_%s_%s.txt" % (self.stage, self.tag))
        nf.write_text("\n".join(self.names), encoding="utf-8")
        cmd = [sys.executable, str(Path(__file__).resolve()), "_worker", "--stage", self.stage,
               "--names", str(nf), "--out", str(self.path), "--cpu-budget", str(self.a.cpu_budget)]
        if stop_file:
            cmd += ["--stop", str(stop_file)]
        env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONIOENCODING="utf-8")
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, env=env, cwd=str(ROOT))
        self.current, self.since = None, time.time()
        self.ready = False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            line = line.strip()
            if line == "READY":
                self.ready, self.since = True, time.time()
            elif line.startswith("START "):
                self.current, self.since = line[6:], time.time()
            elif line.startswith("DONE "):
                nm = line[5:]
                if nm in self.names:
                    self.names.remove(nm)
                self.current, self.since = None, time.time()
                self.done += 1
            elif line in ("ALLDONE", "STOPPED"):
                self.finished = True

    def alive(self):
        return self.proc is not None and self.proc.poll() is None


def _gen() -> int:
    return int(os.environ.get("GPU_SWEEP_GEN", "0"))


def drive(stage, names, a, deadline=None, stop_file=None) -> int:
    """names を jobs 本へ分けて流す。時間切れの op は行を書いて飛ばす。"""
    names = list(names)
    if not names:
        return 0
    random.Random(7).shuffle(names)     # 重い族が 1 本の子に固まらない
    jobs = max(1, a.jobs)
    slots = [Slot(stage, names[i::jobs], a, "%d_%d" % (os.getpid(), i)) for i in range(jobs)]
    for s in slots:
        s.spawn(stop_file)
    finished = 0
    last = time.time()
    while True:
        time.sleep(1.0)
        now = time.time()
        pending = False
        for s in slots:
            if s.finished and not s.alive():
                continue
            if s.alive():
                pending = True
                limit = a.startup if s.current is None else a.timeout
                if now - s.since > limit:
                    who = s.current
                    s.proc.kill()
                    s.proc.wait()
                    if who is not None:
                        append(s.path, {"name": who, "stage": stage, "gen": _gen(), "status": "timeout",
                                        "kind": None, "limit": limit})
                        if who in s.names:
                            s.names.remove(who)
                    s.finished = False
                    if s.names and not (stop_file and Path(stop_file).exists()):
                        s.spawn(stop_file)
            elif not s.finished:
                # 子が落ちた(ネイティブのクラッシュ等): 犯人を記録して続ける
                who = s.current
                if who is not None:
                    append(s.path, {"name": who, "stage": stage, "gen": _gen(), "status": "crash", "kind": None})
                    if who in s.names:
                        s.names.remove(who)
                if s.names and not (stop_file and Path(stop_file).exists()):
                    s.spawn(stop_file)
                    pending = True
                else:
                    s.finished = True
        if not pending and all(s.finished or not s.names for s in slots):
            break
        if now - last > 60:
            last = now
            print("[%s] %s done=%d left=%d" % (time.strftime("%H:%M:%S"), stage,
                                               sum(s.done for s in slots),
                                               sum(len(s.names) for s in slots)), flush=True)
        if deadline is not None and now > deadline and stop_file:
            Path(stop_file).touch()
        if deadline is not None and now > deadline + a.hard_extra:
            for s in slots:
                if s.alive():
                    s.proc.kill()
                    who = s.current
                    if who is not None:
                        append(s.path, {"name": who, "stage": stage, "gen": _gen(), "status": "timeout",
                                        "kind": None, "limit": "hold"})
            break
    return sum(s.done for s in slots)


#: ``--recheck`` の値(倍率の下限)。空なら通常の基準線。
RECHECK: list = []
#: ``--redo`` の値。shim を直したあと、この status の行だけ測り直す(新しい行が勝つ)。
REDO: list = []


def targets_for(stage) -> list:
    all_names = [r["name"] for r in load_targets()]
    done = done_names(stage)
    if stage == "scale_cpu" and RECHECK:
        # 並列・他作業と同時に測った基準線は CPU を遅く見せる。採用圏の op だけ 1 本で測り直す
        sca, base = read_rows("scale"), read_rows("scale_cpu")
        return [n for n in all_names if (sca.get(n, {}).get("ratio") or 0.0) >= RECHECK[0]
                and not base.get(n, {}).get("rechecked")]
    if stage == "scale_cpu":
        par = read_rows("parity")
        cpu = read_rows("cpu")
        return [n for n in all_names if par.get(n, {}).get("status") == "match"
                and n not in done and not is_python_loop(cpu.get(n, {}))]
    if stage == "scale":
        base = read_rows("scale_cpu")
        return [n for n in all_names if base.get(n, {}).get("status") == "measured"
                and n not in done]
    if stage == "parity":
        # Python ループ律速の op は GPU で測る前に結論が出ている。CPU で走らない op も比べられない
        cpu = read_rows("cpu")
        rows = read_rows("parity")
        redo = set(REDO)
        gen = int(os.environ.get("GPU_SWEEP_GEN", "0"))
        return [n for n in all_names
                if (n not in done or (rows[n].get("status") in redo
                                      and rows[n].get("gen", 0) < gen))
                and cpu.get(n, {}).get("status") == "ok" and not is_python_loop(cpu[n])]
    return [n for n in all_names if n not in done]


def is_python_loop(c: dict) -> bool:
    """入力に比例して Python の行が増える op。

    2 倍入力の行数の伸びから「要素 1 個あたりの行数」を出す。0.05 行/要素 は 2048² で
    20 万行 = 1 行ごとに GPU へ命令を送る勘定で、実寸で勝てない。固定形の入力は伸びが
    測れないので、1000 要素以上の入力に限り 1 回の行数と要素数の比で判定する。
    """
    ln, e = c.get("lines"), c.get("elems")
    if not ln or not e:
        return False
    l2, e2 = c.get("lines2"), c.get("elems2")
    if l2 is not None and e2 and e2 > e:
        return (l2 - ln) / float(e2 - e) >= 0.05
    return e >= 1000 and ln / float(e) >= 0.5      # 3×3 の行列に 30 行は比例の証拠にならない


def run_gpu_stage(stage, a) -> int:
    owner = "gpu_auto_%d" % os.getpid()
    lock = GpuLock(a.gpu_lock, owner)
    total_turns = 0
    while True:
        names = targets_for(stage)
        if a.limit:
            names = names[:a.limit]
        if not names:
            print("[%s] nothing left" % stage)
            return 0
        if a.max_turns and total_turns >= a.max_turns:
            print("[%s] stopped after %d turns, %d left" % (stage, total_turns, len(names)))
            return 3
        if not lock.acquire(a.max_wait):
            print("[%s] GPU busy for %.0f s, %d left" % (stage, a.max_wait, len(names)))
            return 4
        total_turns += 1
        stop = OUT / ("stop_%s" % owner)
        stop.unlink(missing_ok=True)
        print("[%s] lock held by %s, %d left" % (time.strftime("%H:%M:%S"), owner, len(names)),
              flush=True)
        t0 = time.time()
        watcher_stop = threading.Event()

        def watch():
            while not watcher_stop.wait(20):
                if not lock.still_mine():
                    stop.touch()      # 譲る: UnrealEditor が来た / ロックが変わった
                    return
        threading.Thread(target=watch, daemon=True).start()
        try:
            drive(stage, names, a, deadline=t0 + a.hold, stop_file=stop)
        finally:
            watcher_stop.set()
            lock.release()
            stop.unlink(missing_ok=True)
        print("[%s] released after %.0f s" % (time.strftime("%H:%M:%S"), time.time() - t0),
              flush=True)
        if a.limit:
            return 0
        time.sleep(a.yield_s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cpu", "parity", "scale_cpu", "scale", "report", "_worker",
                                    "status"])
    ap.add_argument("--stage")
    ap.add_argument("--names")
    ap.add_argument("--out")
    ap.add_argument("--stop")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=90.0, help="seconds per op")
    ap.add_argument("--startup", type=float, default=180.0, help="seconds for a worker to start")
    ap.add_argument("--cpu-budget", type=float, default=60.0)
    ap.add_argument("--gpu-lock", default=os.environ.get("FULLSEYE_GPU_LOCK"))
    ap.add_argument("--hold", type=float, default=480.0, help="seconds per lock hold")
    ap.add_argument("--hard-extra", type=float, default=100.0)
    ap.add_argument("--yield-s", type=float, default=30.0)
    ap.add_argument("--max-wait", type=float, default=3600.0)
    ap.add_argument("--max-turns", type=int, default=0)
    ap.add_argument("--redo", default="", help="comma list of parity statuses to measure again")
    ap.add_argument("--gen", type=int, default=0, help="generation of this redo pass (>=1)")
    ap.add_argument("--recheck", type=float, default=0.0,
                    help="scale_cpu: remeasure ops at or above this ratio; keeps the faster time")
    a = ap.parse_args(argv)
    REDO[:] = [x for x in a.redo.split(",") if x]
    if a.recheck:
        RECHECK[:] = [a.recheck]
    if a.gen:
        os.environ["GPU_SWEEP_GEN"] = str(a.gen)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "_worker":
        return worker(a)
    if a.cmd in ("cpu", "scale_cpu"):
        names = targets_for(a.cmd)
        if a.limit:
            names = names[:a.limit]
        print("%s stage: %d ops" % (a.cmd, len(names)), flush=True)
        drive(a.cmd, names, a)
        return 0
    if a.cmd in ("parity", "scale"):
        return run_gpu_stage(a.cmd, a)
    if a.cmd == "status":
        import gpu_auto_report as R
        return R.status(OUT, load_targets())
    import gpu_auto_report as R
    return R.report(OUT, load_targets(), ROOT, is_python_loop, TOL, MIN_RATIO)


if __name__ == "__main__":
    raise SystemExit(main())
