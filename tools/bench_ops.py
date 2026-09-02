# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""bench_ops — op の速度・メモリ・契約を同じ物差しで測る恒久ベンチ harness。

``docs/design/PERF_MEMORY_VIDEO_SURVEY.md`` §4 の推奨 (h) の実装。調査で使った
使い捨て profiler(``scratchpad/prof_ops.py``)を repo に据えたもので、以後の
高速化(cv2 twin / GPU 常駐 / タイル / 動画パイプライン)が「本当に速くなったか」
「壊れていないか」を **同じ 1 本の物差し**で言うための土台。

測るもの(1 行 = 1 つの ``(op, size, dtype, image)``):

* ``ms``          — repeat 回の **中央値**(最小値ではない: 外れ値に強く、熱ぶれを隠さない)
* ``mpx_s``       — 画素スループット(Mpx/s)。1080p 30 fps 予算 = 62 Mpx/s
* ``tm_peak_x``   — tracemalloc ピーク ÷ 入力バイト(numpy 配列だけを正確に見る)
* ``rss_peak_x``  — RSS ピーク増分 ÷ 入力バイト(ポーリング。**10 ms 未満の op は取りこぼす** —
                    C 内部バッファを見るための第 2 の目であって、tm と互いの穴を埋める)
* ``out_dtype`` / ``out_shape`` — 契約の記録(uint8 を入れると壊れる op を可視化する)
* ``fallbacks``   — ``backend_safe`` の ledger(:func:`backend_safe.mark` /
                    :func:`backend_safe.events_since`)で数えた **1 呼び出しあたり**の降格件数
* ``input_mutated`` / ``shares_mem`` — 入力破壊と in/out のメモリ共有(将来の in-place 配線の見張り)

honest な限界(§5.1 と同じ):

* **熱定常ではない**。絶対値は ±30〜70 % の幅で読む。だから harness は
  **同一 run 内の相対値**(``ratio_vs_core``)を必ず出す — cv2 twin 対 core、
  GPU 対 CPU は同じ run の中で比べる。run をまたいだ比較は ``--baseline`` の
  許容幅(既定 30 %)がその幅を吸収する前提。
* ``median`` / ``percentile`` は **入力の内容で 10 倍変わる**(scipy の選択
  アルゴリズムが同値の多さに依存)。そこで入力は既定で **ノイズ入り**(最悪側)
  と **量子化**(同値だらけ = 速い側)の 2 本を必ず測る。片方だけだと退行検出が嘘になる。

使い方::

    py -3.11 tools/bench_ops.py --set core --sizes 512 --dtypes float64 --repeat 3
    py -3.11 tools/bench_ops.py --ops gaussian,median,cv_median --sizes 2048,1080p
    py -3.11 tools/bench_ops.py --sizes 512,2048,1080p --write-baseline bench/bench_ops_baseline.json
    py -3.11 tools/bench_ops.py --baseline bench/bench_ops_baseline.json --tolerance 0.30

``--baseline`` を渡すと保存済み JSON と突き合わせ、``--tolerance``(既定 0.30 =
30 % 遅くなったら)を超えた行を表にして **exit code 1** で終わる(CI 用)。
キーは ``"gaussian|2048|float64"`` の形で安定(既定でない画像種だけ 4 番目の
成分が付く: ``"median|2048|float64|quantised"``)。
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as _dt
import difflib
import gc
import hashlib
import json
import os
import platform
import statistics
import sys
import threading
import time
import tracemalloc
import warnings
from typing import Any, Callable, Iterable, Sequence

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import api                                                     # noqa: E402
import backend_safe as bs                                      # noqa: E402
import ops                                                     # noqa: E402

# --------------------------------------------------------------------------- #
# honest な但し書き(JSON header に必ず載る)                                   #
# --------------------------------------------------------------------------- #
CAVEAT = (
    "Measured on a NON thermally steady machine: absolute ms/Mpx/s carry a "
    "+-30..70% spread between runs (docs/FSCRIPT_MEASUREMENTS.md §0-a saw 1.7x "
    "between a cold and a warm box). Trust the SAME-RUN relative numbers "
    "(ratio_vs_core) and the structure of the breakdown, not the absolute value. "
    "rss_peak_x is a ~0.4 ms polling thread and MISSES ops shorter than ~10 ms; "
    "tm_peak_x only sees numpy allocations, not C-internal buffers."
)

DEFAULT_OUT = os.path.join("out", "bench_ops.json")
DEFAULT_TOLERANCE = 0.30
DEFAULT_IMAGES = ("noisy", "quantised")
SEED = 7

# 512x512 を超えるサイズでは時間予算に入らない op(調査 §1.1 の「重い op」)。
# 行は消さずに ``skipped`` 理由つきで残す(消すと「発見ゼロ」に化けるため)。
HEAVY = frozenset({
    "shape_locate", "ncc_locate", "sk_tv", "sk_nlm", "cv_nlmeans", "bilateral",
    "cv_bilateral", "edges_sub_pix", "sk_find_contours", "lines_gauss", "sk_canny",
    "xkor_bilateral",
})
HEAVY_MAX_PX = 1024 * 1024

# --------------------------------------------------------------------------- #
# op セット — 調査 §1.1 の主表と同じ顔ぶれ(core = ops.py/backends_auto の既定実装、  #
# cv = OpenCV/skimage/kornia ラッパ)。名前は起動時に registry で実在検証する。      #
# --------------------------------------------------------------------------- #
CORE_OPS: tuple[str, ...] = (
    # filter
    "gaussian", "gauss_filter", "mean_box", "median", "percentile", "sobel_mag",
    "unsharp", "std_filter", "log", "bilateral",
    # morphology
    "gerode", "gopen", "tophat", "opening_circle", "fill_holes",
    "reg_erode", "reg_dilate",
    # threshold / segmentation
    "threshold", "otsu", "dyn_threshold",
    # region props / features
    "area_frac", "blob_count", "count_obj", "circularity", "remove_small",
    "select_largest", "dist_transform",
    # fft
    "lowpass", "highpass", "fft_image",
    # geometry
    "rotate_img", "rotate_image", "rescale_img", "affine_warp", "zoom_image_size",
    # colour
    "cfa_to_rgb", "rgb1_to_gray", "trans_from_rgb", "principal_comp",
    # edges
    "canny", "corner_response", "edges_sub_pix", "lines_gauss",
    # gray
    "equalize", "clahe", "gamma", "invert", "identity",
    # matching(template を要する。heavy guard で 512² のみ)
    "ncc_locate", "shape_locate",
)

CV_OPS: tuple[str, ...] = (
    "cv_gaussian", "cv_box", "cv_median", "cv_bilateral", "cv_scharr", "cv_open",
    "cv_erode", "cv_tophat", "cv_sharpen", "cv_otsu", "cv_adaptive_mean",
    "cv_canny", "cv_clahe", "cv_corner_harris", "cv_dist",
    "sk_butterworth", "sk_canny", "sk_tv", "sk_find_contours", "xkor_gaussian",
)

SETS: dict[str, tuple[str, ...]] = {
    "core": CORE_OPS,
    "cv": CV_OPS,
    "all": CORE_OPS + CV_OPS,
}

MATCH_OPS = frozenset({"ncc_locate", "shape_locate"})


# --------------------------------------------------------------------------- #
# 入力(決定論的)                                                             #
# --------------------------------------------------------------------------- #
def scene(h: int, w: int, kind: str = "noisy", seed: int = SEED) -> np.ndarray:
    """決定論的な合成シーンを float64 [0,1] で返す。

    ``kind``:

    * ``"noisy"``     — 円板 60 個 + 照明勾配 + 3 % ガウスノイズ。**必須**の入力:
      ノイズがあると ``median``/``percentile`` は最悪側(2048² で 1.8 s)に落ちる。
      実画像はこちら側なので、ここを測らないベンチは退行を見逃す(§5.1)。
    * ``"quantised"`` — 同じ画をノイズ無しで 16 階調に量子化したもの。同値が多く
      選択アルゴリズムが速くなる側(同じ ``median`` が 10 倍速い)。
    * ``"constant"``  — 定数 0.42。縮退入力(op が入力に依存せず定数を返していないか、
      および分岐の無い最短経路の下限を見る)。
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    if kind == "constant":
        return np.full((h, w), 0.42)
    img = 0.25 + 0.1 * xx / max(1, w - 1)
    r = max(4, min(h, w) // 40)
    for _ in range(60):
        cy, cx = rng.integers(r, h - r), rng.integers(r, w - r)
        img = np.where((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r, 0.85, img)
    from scipy import ndimage                              # scipy は必須依存
    img = ndimage.gaussian_filter(img, 1.0)
    if kind == "noisy":
        img = img + 0.03 * rng.standard_normal((h, w))
    elif kind == "quantised":
        img = np.floor(np.clip(img, 0, 1) * 15.0) / 15.0   # 16 階調 = 同値だらけ
    else:
        raise ValueError("unknown image kind %r (noisy|quantised|constant)" % (kind,))
    return np.clip(img, 0, 1)


def input_for(sort: str, kind: str, h: int, w: int, dtype: str) -> np.ndarray:
    """op の入力 sort に合わせた入力配列(image / region / color)。"""
    base = scene(h, w, kind)
    if sort == "region":
        x = (base > 0.5).astype(np.float64)
    elif sort == "color":
        x = np.stack([base, np.roll(base, 5, 1), np.roll(base, -5, 0)], -1)
    else:                                                   # image / any / その他
        x = base
    if dtype == "uint8":
        x = np.clip(x * 255.0, 0, 255).astype(np.uint8)
    elif dtype == "float32":
        x = x.astype(np.float32)
    elif dtype != "float64":
        raise ValueError("unsupported dtype %r" % (dtype,))
    return np.ascontiguousarray(x)


# --------------------------------------------------------------------------- #
# サイズ / dtype のパース                                                       #
# --------------------------------------------------------------------------- #
_NAMED_SIZES = {
    "720p": (720, 1280),
    "1080p": (1080, 1920),
    "1440p": (1440, 2560),
    "4k": (2160, 3840),
}
_DTYPE_ALIASES = {"f64": "float64", "float64": "float64", "double": "float64",
                  "u8": "uint8", "uint8": "uint8",
                  "f32": "float32", "float32": "float32"}


def parse_size(token: str) -> tuple[int, int, str]:
    """``"512"`` / ``"1080p"`` / ``"1920x1080"`` -> ``(h, w, label)``。"""
    t = token.strip().lower()
    if t in _NAMED_SIZES:
        h, w = _NAMED_SIZES[t]
        return h, w, t
    if "x" in t:
        a, _, b = t.partition("x")
        w, h = int(a), int(b)                               # "WxH" の慣習
        return h, w, t
    n = int(t)
    if n <= 0:
        raise ValueError("size must be positive: %r" % (token,))
    return n, n, str(n)


def parse_dtype(token: str) -> str:
    t = token.strip().lower()
    if t not in _DTYPE_ALIASES:
        raise ValueError("unknown dtype %r (float64|uint8|float32)" % (token,))
    return _DTYPE_ALIASES[t]


# --------------------------------------------------------------------------- #
# op の解決(fail-closed)                                                      #
# --------------------------------------------------------------------------- #
def registry_names() -> list[str]:
    return [o.name for o in ops.REGISTRY]


def resolve_ops(names: Iterable[str]) -> list[str]:
    """名前列を検証して返す。**未知の op があれば近い名前を挙げて例外**(fail-closed)。"""
    known = registry_names()
    kset = set(known)
    out, bad = [], []
    for n in names:
        n = n.strip()
        if not n:
            continue
        if n in kset:
            out.append(n)
        elif api.find_op(n) is not None:                    # HALCON 別名で当たる
            out.append(api.find_op(n).name)
        else:
            bad.append(n)
    if bad:
        lines = []
        for n in bad:
            near = difflib.get_close_matches(n, known, n=6, cutoff=0.5)
            lines.append("  %r -> did you mean: %s" % (n, ", ".join(near) if near else "(no near match)"))
        raise ValueError("unknown op name(s):\n%s" % "\n".join(lines))
    return out


def resolve_set(name: str) -> tuple[list[str], list[str]]:
    """名前付きセット -> ``(measurable names, absent names)``。

    ユーザーが打った ``--ops`` は fail-closed(打ち間違いを黙って落とさない)。対して
    **セットは任意バックエンドを含む**(``cv_*`` は opencv、``sk_*`` は scikit-image、
    ``xkor_*`` は kornia)ので、その op が registry に居ないのは「打ち間違い」ではなく
    「そのバックエンドが入っていない」= 正常な劣化。落とさず、**何を測らなかったかを
    返して header に残す**(黙って縮めると「退行ゼロ」に化ける)。
    """
    if name not in SETS:
        raise ValueError("unknown set %r (%s)" % (name, "|".join(sorted(SETS))))
    known = set(registry_names())
    present = [n for n in SETS[name] if n in known]
    absent = [n for n in SETS[name] if n not in known]
    if not present:
        raise ValueError("set %r has no measurable op in this install (absent: %s)"
                         % (name, ", ".join(absent)))
    return present, absent


# --------------------------------------------------------------------------- #
# twin(cv2)/ accel の対応 — repo に実在する対応だけを使う                       #
# --------------------------------------------------------------------------- #
def cv_twin(name: str) -> tuple[str | None, list[str]]:
    """core op ``name`` の OpenCV twin を registry から引く。

    対応表は **発明しない**: registry の :class:`ops.Op` が持つ HALCON 名
    (``Op.halcon``)が core と cv2 ラッパで共有されているのが repo の実在する
    対応関係(``gaussian``/``cv_gaussian`` = ``gauss_filter``、``median``/
    ``cv_median`` = ``median_image`` …、``backends.py`` の登録表)。空の HALCON 名は
    「別名なし」を意味するので除外し、in/out sort が一致するものだけを twin とする
    (``edges_image`` は ``cv_scharr``(image)と ``cv_canny``(region)の両方が名乗る)。

    返り値 ``(twin_name_or_None, all_candidates)``。候補が複数のときは registry の
    登録順で先頭を採り、候補一覧も返して曖昧さを隠さない。
    """
    op = api.find_op(name)
    if op is None or not op.halcon:
        return None, []
    cand = [o.name for o in ops.REGISTRY
            if o.halcon == op.halcon and o.name != op.name
            and o.name.startswith("cv_")
            and o.in_sort == op.in_sort and o.out_sort == op.out_sort]
    return (cand[0] if cand else None), cand


def accel_cores() -> dict[str, str]:
    """``{core op name: accel key}``。``accel.ACCEL`` は ``key -> (fn, core, halcon)``。

    torch が無い / accel が壊れている環境では空辞書(GPU 比較を諦めるだけ)。
    """
    try:
        import accel                                        # torch を引きうる(任意依存)
    except Exception:                                       # noqa: BLE001
        return {}
    try:
        return {core: key for key, (_fn, core, _hal) in accel.ACCEL.items()}
    except Exception:                                       # noqa: BLE001
        return {}


def op_module(op) -> str:
    """op を実装しているモジュール名(guard ラッパを剥がす)。"""
    f = op.fn
    while hasattr(f, "__wrapped__"):
        f = f.__wrapped__
    return getattr(f, "__module__", "?")


# --------------------------------------------------------------------------- #
# RSS ポーリング(psutil があれば使う。無くても Windows/POSIX で動く)            #
# --------------------------------------------------------------------------- #
def _rss_reader() -> Callable[[], int] | None:
    """現在の RSS(bytes)を返す callable、取れなければ None。"""
    try:
        import psutil                                       # 任意依存
        proc = psutil.Process()
        return lambda: int(proc.memory_info().rss)
    except Exception:                                       # noqa: BLE001
        pass
    if sys.platform == "win32":
        try:
            class _PMC(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            _get = _k32.K32GetProcessMemoryInfo
            _handle = _k32.GetCurrentProcess()

            def _read() -> int:
                pmc = _PMC()
                pmc.cb = ctypes.sizeof(_PMC)
                if not _get(_handle, ctypes.byref(pmc), pmc.cb):
                    return 0
                return int(pmc.WorkingSetSize)

            _read()                                         # 一度呼んで実在確認
            return _read
        except Exception:                                   # noqa: BLE001
            pass
    try:
        import resource                                     # POSIX

        def _read_ru() -> int:
            mult = 1 if sys.platform == "darwin" else 1024
            return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * mult

        return _read_ru
    except Exception:                                       # noqa: BLE001
        return None


class _RssPoller(threading.Thread):
    """0.4 ms 刻みで RSS を見張る。**10 ms 未満の op は取りこぼす**(header の caveat)。"""

    def __init__(self, read: Callable[[], int]):
        super().__init__(daemon=True)
        self._read = read
        self.peak = 0
        self.stop = False

    def run(self) -> None:
        while not self.stop:
            try:
                r = self._read()
            except Exception:                               # noqa: BLE001
                return
            if r > self.peak:
                self.peak = r
            time.sleep(0.0004)


def _digest(x: np.ndarray) -> str:
    return hashlib.blake2b(np.ascontiguousarray(x).tobytes(), digest_size=16).hexdigest()


# --------------------------------------------------------------------------- #
# 1 行の測定                                                                    #
# --------------------------------------------------------------------------- #
def row_key(name: str, size_label: str, dtype: str, image: str = "noisy") -> str:
    """ベースライン用の安定キー ``"gaussian|2048|float64"``。

    既定でない画像種のときだけ 4 番目の成分が付く(``"median|2048|float64|quantised"``)
    ので、既定の 3 成分キーは画像種を増やしても不変。
    """
    base = "%s|%s|%s" % (name, size_label, dtype)
    return base if image == DEFAULT_IMAGES[0] else base + "|" + image


def measure_op(name: str, x: np.ndarray, *, warm: int = 1, repeat: int = 3,
               device: str = "cpu", template: np.ndarray | None = None,
               rss_read: Callable[[], int] | None = None) -> dict[str, Any]:
    """``api.apply`` の実経路で 1 つの op を測る。例外は握り潰さず row に載せる。

    呼び出し回数 = ``warm``(捨て)+ 1(メモリ計測、時間には数えない)+ ``repeat``。
    メモリ計測を時間サンプルから外すのは、tracemalloc が計測対象の実行時間を
    数倍に膨らませるため(混ぜると ms が嘘になる)。
    """
    def call(v):
        return api.apply(v, name, 0.5, 0.5, device=device, template=template)

    gc.collect()
    for _ in range(max(0, warm)):
        call(x)

    # --- メモリ(tracemalloc = numpy 配列 / RSS = C 内部バッファも含む)------- #
    gc.collect()
    poller = None
    rss0 = 0
    if rss_read is not None:
        rss0 = rss_read()
        poller = _RssPoller(rss_read)
        poller.start()
    mark = bs.mark()
    tracemalloc.start()
    tracemalloc.reset_peak()
    out = call(x)
    _cur, tm_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    events = bs.events_since(mark)
    rss_peak = 0
    if poller is not None:
        poller.stop = True
        poller.join()
        rss_peak = max(0, poller.peak - rss0)

    # --- 時間(中央値)------------------------------------------------------- #
    samples = []
    for _ in range(max(1, repeat)):
        t0 = time.perf_counter()
        call(x)
        samples.append(time.perf_counter() - t0)
    ms = statistics.median(samples) * 1e3

    npx = int(np.prod(x.shape[:2]))
    nbytes = int(x.nbytes)
    return {
        "ms": round(ms, 4),
        "ms_min": round(min(samples) * 1e3, 4),
        "ms_max": round(max(samples) * 1e3, 4),
        "repeat": int(max(1, repeat)),
        "mpx_s": round(npx / ms / 1e3, 2) if ms > 0 else None,
        "npx": npx,
        "in_bytes": nbytes,
        "tm_peak_mb": round(tm_peak / 2 ** 20, 3),
        "tm_peak_x": round(tm_peak / nbytes, 3) if nbytes else None,
        "rss_peak_mb": round(rss_peak / 2 ** 20, 3) if rss_read is not None else None,
        "rss_peak_x": (round(rss_peak / nbytes, 3) if (rss_read is not None and nbytes) else None),
        "out_dtype": str(getattr(out, "dtype", type(out).__name__)),
        "out_shape": (list(out.shape) if isinstance(out, np.ndarray) else None),
        "shares_mem": bool(isinstance(out, np.ndarray) and np.shares_memory(out, x)),
        "fallbacks": len(events),
        "fallback_msg": (events[0].get("error", "")[:160] if events else ""),
    }


def bench_row(name: str, size: tuple[int, int, str], dtype: str, image: str, *,
              warm: int, repeat: int, device: str, rss_read, accel_map: dict[str, str],
              template_cache: dict) -> dict[str, Any]:
    """1 つの ``(op, size, dtype, image)`` を測って row dict を返す(例外も row になる)。"""
    h, w, size_label = size
    op = api.find_op(name)
    row: dict[str, Any] = {
        "key": row_key(name, size_label, dtype, image),
        "name": name, "size": size_label, "shape": [h, w], "dtype": dtype, "image": image,
    }
    if op is None:                                          # resolve_ops を通っていれば起きない
        row["error"] = "unknown op"
        return row
    row.update({"in_sort": op.in_sort, "out_sort": op.out_sort, "module": op_module(op),
                "category": op.category, "halcon": op.halcon,
                "guarded": bool(getattr(op.fn, "__fullseye_guarded__", False))})
    twin, cands = cv_twin(name)
    if twin:
        row["twin"] = twin
        if len(cands) > 1:
            row["twin_candidates"] = cands
    if name in accel_map:
        row["accel_key"] = accel_map[name]

    if name in HEAVY and h * w > HEAVY_MAX_PX:
        row["skipped"] = "heavy op above %d px (time budget); measured at <=1024^2 only" % HEAVY_MAX_PX
        return row

    sort = op.in_sort if op.in_sort in ("image", "region", "color") else "image"
    try:
        x = input_for(sort, image, h, w, dtype)
    except Exception as e:                                  # noqa: BLE001
        row["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        return row

    template = None
    if name in MATCH_OPS:
        tkey = (sort, image, h, w)
        if tkey not in template_cache:
            ref = input_for(sort, image, h, w, "float64")
            side = max(4, min(48, h // 4, w // 4))          # 小さな画像でも空テンプレにしない
            y0, x0 = h // 4, w // 4
            template_cache[tkey] = np.ascontiguousarray(ref[y0:y0 + side, x0:x0 + side])
        template = template_cache[tkey]

    before = _digest(x)
    try:
        row.update(measure_op(name, x, warm=warm, repeat=repeat, device=device,
                              template=template, rss_read=rss_read))
    except Exception as e:                                  # noqa: BLE001
        row["error"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        return row
    row["input_mutated"] = _digest(x) != before

    # 同一 run 内の GPU 対 CPU(熱ぶれを跨がない比較)
    if device != "cpu" and name in accel_map:
        try:
            cpu = measure_op(name, x, warm=warm, repeat=repeat, device="cpu",
                             template=template, rss_read=None)
            row["core_ref"] = "cpu:" + name
            row["core_ref_ms"] = cpu["ms"]
            row["ratio_vs_core"] = round(cpu["ms"] / row["ms"], 3) if row["ms"] else None
        except Exception as e:                              # noqa: BLE001
            row["core_ref_error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return row


def link_twin_ratios(rows: Sequence[dict]) -> None:
    """同一 run の core 行と cv2 twin 行を突き合わせて ``ratio_vs_core`` を入れる(in-place)。

    熱ぶれ(§5.1)は run をまたぐと 1.7 倍まで動くので、twin の効きは **同じ run の中**
    でしか主張しない。``ratio_vs_core`` は「core の ms ÷ この行の ms」= この行が
    core の何倍速いか。
    """
    index = {(r["name"], r["size"], r["dtype"], r.get("image")): r for r in rows}
    for r in rows:
        twin = r.get("twin")
        if not twin or "ms" not in r:
            continue
        t = index.get((twin, r["size"], r["dtype"], r.get("image")))
        if t is None or "ms" not in t or not t["ms"] or "ratio_vs_core" in t:
            continue                                         # 既に GPU 比が入っている行は触らない
        ratio = round(r["ms"] / t["ms"], 3)                  # twin が core の何倍速いか
        t["core_ref"] = r["name"]
        t["core_ref_ms"] = r["ms"]
        t["ratio_vs_core"] = ratio
        r["twin_ratio_vs_core"] = ratio


# --------------------------------------------------------------------------- #
# run                                                                          #
# --------------------------------------------------------------------------- #
def _versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0], "numpy": np.__version__}
    for mod in ("scipy", "cv2", "skimage", "torch"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:                                   # noqa: BLE001
            out[mod] = "absent"
    return out


def _cpu_name() -> str:
    return (os.environ.get("PROCESSOR_IDENTIFIER")
            or platform.processor() or platform.machine() or "unknown")


def build_header(*, names: Sequence[str], sizes: Sequence[tuple[int, int, str]],
                 dtypes: Sequence[str], images: Sequence[str], warm: int, repeat: int,
                 device: str) -> dict[str, Any]:
    return {
        "date": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "tool": "tools/bench_ops.py",
        "versions": _versions(),
        "cpu": _cpu_name(),
        "platform": platform.platform(),
        "registry_ops": len(ops.REGISTRY),
        "warm": warm,
        "repeat": repeat,
        "device": device,
        "ops": list(names),
        "sizes": [s[2] for s in sizes],
        "dtypes": list(dtypes),
        "images": list(images),
        "caveat": CAVEAT,
    }


def run(names: Sequence[str], sizes: Sequence[tuple[int, int, str]], dtypes: Sequence[str],
        images: Sequence[str] = DEFAULT_IMAGES, *, warm: int = 1, repeat: int = 3,
        device: str = "cpu", verbose: bool = True) -> dict[str, Any]:
    """全組み合わせを測って ``{"header":…, "rows":[…], "summary":{…}}`` を返す。"""
    rss_read = _rss_reader()
    # accel(= torch)の import は ~700 ms かかるので、GPU 比較を実際にやる run でだけ引く。
    accel_map = accel_cores() if device != "cpu" else {}
    rows: list[dict[str, Any]] = []
    template_cache: dict = {}
    t0 = time.time()
    for size in sizes:
        for dtype in dtypes:
            for image in images:
                for name in names:
                    row = bench_row(name, size, dtype, image, warm=warm, repeat=repeat,
                                    device=device, rss_read=rss_read, accel_map=accel_map,
                                    template_cache=template_cache)
                    rows.append(row)
                    if verbose:
                        print(format_row(row), flush=True)
    link_twin_ratios(rows)
    header = build_header(names=names, sizes=sizes, dtypes=dtypes, images=images,
                          warm=warm, repeat=repeat, device=device)
    header["rss_source"] = ("psutil/ctypes poll" if rss_read is not None
                            else "unavailable (no psutil, no platform reader)")
    header["elapsed_s"] = round(time.time() - t0, 1)
    errs = [r for r in rows if "error" in r]
    summary = {
        "rows": len(rows),
        "measured": sum(1 for r in rows if "ms" in r),
        "skipped": sum(1 for r in rows if "skipped" in r),
        "errors": len(errs),
        "error_names": sorted({r["name"] for r in errs}),
        "fallback_rows": sum(1 for r in rows if r.get("fallbacks")),
        "mutating_rows": sorted({r["name"] for r in rows if r.get("input_mutated")}),
        "sharing_rows": sorted({r["name"] for r in rows if r.get("shares_mem")}),
    }
    return {"header": header, "rows": rows, "summary": summary}


def format_row(row: dict) -> str:
    if "error" in row:
        return "%-20s %-6s %-8s %-9s  ERROR  %s" % (
            row["name"], row["size"], row["dtype"], row.get("image", ""), row["error"])
    if "skipped" in row:
        return "%-20s %-6s %-8s %-9s  skipped (%s)" % (
            row["name"], row["size"], row["dtype"], row.get("image", ""), row["skipped"])
    return ("%-20s %-6s %-8s %-9s %9.2f ms %8.1f Mpx/s  tm x%-6s rss x%-6s out=%-9s fb=%d%s"
            % (row["name"], row["size"], row["dtype"], row.get("image", ""), row["ms"],
               row["mpx_s"] or 0.0, row["tm_peak_x"], row["rss_peak_x"], row["out_dtype"],
               row["fallbacks"],
               ("  %.1fx vs %s" % (row["ratio_vs_core"], row["core_ref"])
                if row.get("ratio_vs_core") else "")))


# --------------------------------------------------------------------------- #
# ベースライン                                                                  #
# --------------------------------------------------------------------------- #
def baseline_from(report: dict) -> dict[str, Any]:
    """report -> ベースライン JSON(header + キーごとの数値)。"""
    metrics = {}
    for r in report["rows"]:
        if "ms" not in r:
            continue
        metrics[r["key"]] = {"ms": r["ms"], "mpx_s": r["mpx_s"], "tm_peak_x": r["tm_peak_x"],
                             "out_dtype": r["out_dtype"], "fallbacks": r["fallbacks"]}
    return {"header": report["header"], "metrics": metrics}


def load_baseline(path: str) -> dict[str, dict]:
    """ベースライン JSON を ``{key: {...}}`` に正規化(full report 形式も受ける)。"""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data.get("metrics"), dict):
        return data["metrics"]
    if isinstance(data.get("rows"), list):
        return {r["key"]: r for r in data["rows"] if isinstance(r, dict) and "ms" in r}
    raise ValueError("%s is not a bench_ops baseline (no 'metrics' and no 'rows')" % path)


def compare_baseline(report: dict, base: dict[str, dict],
                     tolerance: float = DEFAULT_TOLERANCE) -> dict[str, Any]:
    """現行 run をベースラインと突き合わせる。

    ``regressions`` = ``ms`` が ``(1 + tolerance)`` 倍を超えた行。``improvements`` は
    その逆側(``1/(1+tolerance)`` 未満)。``missing`` はベースラインに無い行、
    ``vanished`` はベースラインにあって今回測れなかった行(= 消えた op / 落ちた op:
    静かに無視すると「退行ゼロ」に化けるので必ず数える)。
    """
    hi, lo = 1.0 + tolerance, 1.0 / (1.0 + tolerance)
    regressions, improvements, missing, compared = [], [], [], []
    seen = set()
    for r in report["rows"]:
        if "ms" not in r:
            continue
        b = base.get(r["key"])
        if b is None:
            missing.append(r["key"])
            continue
        seen.add(r["key"])
        bms = float(b["ms"])
        ratio = (r["ms"] / bms) if bms else float("inf")
        item = {"key": r["key"], "baseline_ms": round(bms, 4), "current_ms": r["ms"],
                "ratio": round(ratio, 3),
                "out_dtype": r["out_dtype"], "baseline_out_dtype": b.get("out_dtype")}
        compared.append(item)
        if ratio > hi:
            regressions.append(item)
        elif ratio < lo:
            improvements.append(item)
    vanished = sorted(set(base) - seen)
    dtype_changed = [c for c in compared
                     if c["baseline_out_dtype"] and c["out_dtype"] != c["baseline_out_dtype"]]
    regressions.sort(key=lambda c: -c["ratio"])
    improvements.sort(key=lambda c: c["ratio"])
    return {"tolerance": tolerance, "compared": len(compared), "regressions": regressions,
            "improvements": improvements, "missing": missing, "vanished": vanished,
            "dtype_changed": dtype_changed}


def format_comparison(cmp_: dict) -> str:
    lines = ["", "baseline comparison (tolerance %+.0f%%, %d keys compared)"
             % (cmp_["tolerance"] * 100, cmp_["compared"])]
    if cmp_["regressions"]:
        lines.append("  REGRESSIONS (%d):" % len(cmp_["regressions"]))
        lines.append("    %-44s %10s %10s %7s" % ("key", "base ms", "now ms", "ratio"))
        for c in cmp_["regressions"]:
            lines.append("    %-44s %10.2f %10.2f %6.2fx" %
                         (c["key"], c["baseline_ms"], c["current_ms"], c["ratio"]))
    else:
        lines.append("  no regression beyond tolerance")
    if cmp_["improvements"]:
        lines.append("  improvements (%d): %s" % (
            len(cmp_["improvements"]),
            ", ".join("%s %.2fx" % (c["key"], c["ratio"]) for c in cmp_["improvements"][:10])))
    if cmp_["dtype_changed"]:
        lines.append("  OUTPUT DTYPE CHANGED (%d): %s" % (
            len(cmp_["dtype_changed"]),
            ", ".join("%s %s->%s" % (c["key"], c["baseline_out_dtype"], c["out_dtype"])
                      for c in cmp_["dtype_changed"][:10])))
    if cmp_["vanished"]:
        lines.append("  in baseline but NOT measured now (%d): %s"
                     % (len(cmp_["vanished"]), ", ".join(cmp_["vanished"][:10])))
    if cmp_["missing"]:
        lines.append("  measured now but NOT in baseline (%d): %s"
                     % (len(cmp_["missing"]), ", ".join(cmp_["missing"][:10])))
    return "\n".join(lines)


def format_summary(report: dict) -> str:
    s = report["summary"]
    rows = [r for r in report["rows"] if "ms" in r and r.get("mpx_s")]
    rows.sort(key=lambda r: r["mpx_s"])
    lines = ["", "summary: %d rows, %d measured, %d skipped, %d errors, %d rows with fallbacks"
             % (s["rows"], s["measured"], s["skipped"], s["errors"], s["fallback_rows"])]
    if s["error_names"]:
        lines.append("  errored ops: %s" % ", ".join(s["error_names"]))
    if s["mutating_rows"]:
        lines.append("  INPUT MUTATED by: %s" % ", ".join(s["mutating_rows"]))
    if s["sharing_rows"]:
        lines.append("  output shares memory with input: %s" % ", ".join(s["sharing_rows"]))
    if rows:
        lines.append("  slowest by Mpx/s: %s"
                     % ", ".join("%s %.2f" % (r["key"], r["mpx_s"]) for r in rows[:5]))
    twins = [r for r in report["rows"] if r.get("ratio_vs_core")]
    twins.sort(key=lambda r: -r["ratio_vs_core"])
    if twins:
        lines.append("  same-run ratio_vs_core (this row is Nx faster than its core): %s"
                     % ", ".join("%s %.2fx vs %s" % (r["key"], r["ratio_vs_core"], r["core_ref"])
                                 for r in twins[:8]))
    lines.append("  " + CAVEAT)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bench_ops",
        description="fullseye op benchmark harness: time / memory / contract, with a JSON baseline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    p.add_argument("--ops", help="comma-separated op names (overrides --set)")
    p.add_argument("--set", dest="opset", default="all", choices=sorted(SETS),
                   help="named op set (default: all)")
    p.add_argument("--sizes", default="512,2048,1080p",
                   help="comma-separated sizes: N (square), WxH, or 720p/1080p/1440p/4k")
    p.add_argument("--dtypes", default="float64", help="comma-separated: float64,uint8,float32")
    p.add_argument("--images", default=",".join(DEFAULT_IMAGES),
                   help="input content: noisy,quantised,constant (median is 10x content dependent)")
    p.add_argument("--warm", type=int, default=1, help="warm-up calls per row (default 1)")
    p.add_argument("--repeat", type=int, default=3, help="timed calls per row, median (default 3)")
    p.add_argument("--out", default=DEFAULT_OUT, help="write the full report JSON here")
    p.add_argument("--baseline", help="compare against this baseline JSON; exit 1 on regression")
    p.add_argument("--write-baseline", dest="write_baseline",
                   help="write the run as a baseline JSON at this path")
    p.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE,
                   help="regression threshold as a fraction (default 0.30 = 30%% slower)")
    p.add_argument("--device", default="cpu", help="cpu | cuda (cuda needs torch+accel)")
    p.add_argument("--quiet", action="store_true", help="do not print each row as it is measured")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    warnings.simplefilter("ignore")
    args = build_parser().parse_args(argv)
    absent: list[str] = []
    try:
        if args.ops:
            names = resolve_ops(args.ops.split(","))
        else:
            names, absent = resolve_set(args.opset)
        sizes = [parse_size(t) for t in args.sizes.split(",") if t.strip()]
        dtypes = [parse_dtype(t) for t in args.dtypes.split(",") if t.strip()]
        images = [t.strip() for t in args.images.split(",") if t.strip()]
        for im in images:
            if im not in ("noisy", "quantised", "constant"):
                raise ValueError("unknown image kind %r (noisy|quantised|constant)" % im)
        if "noisy" not in images:
            raise ValueError("the noisy image is mandatory: median/percentile are 10x content "
                             "dependent and a bench without it hides the worst case (survey §5.1)")
    except ValueError as e:
        print("bench_ops: %s" % e, file=sys.stderr)
        return 2
    if not names or not sizes or not dtypes:
        print("bench_ops: nothing to measure", file=sys.stderr)
        return 2

    report = run(names, sizes, dtypes, images, warm=args.warm, repeat=args.repeat,
                 device=args.device, verbose=not args.quiet)
    print(format_summary(report))

    if args.out:
        _write_json(args.out, report)
        print("report -> %s" % args.out)
    if args.write_baseline:
        _write_json(args.write_baseline, baseline_from(report))
        print("baseline -> %s (%d keys)"
              % (args.write_baseline, len(baseline_from(report)["metrics"])))
    rc = 0
    if args.baseline:
        try:
            base = load_baseline(args.baseline)
        except (OSError, ValueError) as e:
            print("bench_ops: cannot read baseline: %s" % e, file=sys.stderr)
            return 2
        cmp_ = compare_baseline(report, base, args.tolerance)
        print(format_comparison(cmp_))
        report["comparison"] = cmp_
        if args.out:
            _write_json(args.out, report)
        if cmp_["regressions"]:
            rc = 1
    if report["summary"]["errors"]:
        print("bench_ops: %d row(s) errored (see the report JSON)"
              % report["summary"]["errors"], file=sys.stderr)
    return rc


def _write_json(path: str, obj: Any) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    raise SystemExit(main())
