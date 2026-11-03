"""GPU 損益分岐の計測台本 / CPU-vs-GPU crossover harness (GPU 第 5 便).

計測の作法は docs/perf/gpu_crossover_2026-11-02.md に書いてある。要点:

* 同じ前生成の画像を使い、乱数生成は時間に含めない。各点は複数回の中央値。
* CPU = 登録経路そのもの(``api.apply(device="cpu")`` を 1 枚ずつ)。1 回が 90 s を超える点は
  打ち切り、値を外挿しない(``status="cutoff"``)。
* GPU = host→device 転送 + op + device→host 転送(``accel.run_batch`` と同じ道)。
  ``torch.cuda.synchronize`` 込みで測り、転送と kernel の内訳を別に取る。
* GPU は共有資源。``FULLSEYE_GPU_LOCK`` の指すロックが他者のものである間、または UnrealEditor が
  居る間は GPU に触らない。自分のロックは排他的に作り、1 窓 ``--window`` 秒以内で必ず消す。
  窓の途中で UnrealEditor が現れたら、その窓を捨てて譲る。

  py = loco venv の python
  FULLSEYE_GPU_LOCK=<共有ロックのパス> py tools/bench_gpu_crossover.py gpu --out <jsonl>
"""
from __future__ import annotations

import argparse
import atexit
import datetime
import json
import os
import platform
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SIDES = (64, 128, 256, 512, 1024, 2048, 4096)
COUNTS = (1, 4, 16, 100)
VOL_SIDES = (32, 64, 128, 256, 512)
VOL_COUNTS = (1, 4)
CPU_LIMIT_S = 90.0
A, B = 0.5, 0.5

# 族 -> (core op, 入力の種)。代表は「各族から計 15 以上」。sk_tv は scikit-image が要るので別扱い。
FAMILIES = {
    "point": [("threshold", "image"), ("invert", "image"), ("gamma", "image"), ("sigmoid", "image"),
              ("scale_clip", "image")],
    "separable": [("gaussian", "image"), ("mean_box", "image"), ("sobel_mag", "image"), ("dog", "image"),
                  ("unsharp", "image")],
    "nonseparable": [("median", "image"), ("percentile", "image"), ("bilateral", "image"),
                     ("std_filter", "image"), ("laplace", "image")],
    "morphology": [("min_filter", "image"), ("gopen", "image"), ("tophat", "image"),
                   ("erosion_circle", "region"), ("reg_dilate", "region")],
    "frequency": [("lowpass", "image"), ("highpass", "image")],
    "iterative": [("sk_tv", "image"), ("fill_holes", "region"), ("canny", "image"), ("equalize", "image"),
                  ("otsu", "image")],
    "volume": [("vol_gaussian", "volume"), ("vol_median", "volume"), ("vol_erode", "volume"),
               ("vol_threshold", "volume"), ("vol_opening_ball", "volume")],
    "match": [("ncc_locate", "image")],
}

# 現実的な検査パイプライン。all = 全段 GPU 経路あり、mixed = 途中に GPU 経路の無い op が挟まる。
PIPELINES = {
    "scratch_surface": {
        "all": [("gaussian", .3, .5), ("tophat", .5, .5), ("threshold", .55, .5), ("erosion_circle", .2, .5),
                ("dilation_circle", .2, .5)],
        "mixed": [("gaussian", .3, .5), ("clahe", .5, .5), ("tophat", .5, .5), ("threshold", .55, .5),
                  ("erosion_circle", .2, .5), ("dilation_circle", .2, .5)]},
    "edge_dimension": {
        "all": [("median", .3, .5), ("sobel_mag", .5, .5), ("threshold", .35, .5), ("reg_dilate", .3, .5),
                ("fill_holes", .5, .5)],
        "mixed": [("median", .3, .5), ("kirsch_amp", .5, .5), ("threshold", .35, .5), ("reg_dilate", .3, .5),
                  ("fill_holes", .5, .5)]},
    "shading_blob": {
        "all": [("illuminate", .5, .5), ("unsharp", .5, .5), ("equalize", .5, .5),
                ("adaptive_gauss_thresh", .5, .5), ("opening_circle", .3, .5)],
        "mixed": [("illuminate", .5, .5), ("guided_filter", .5, .5), ("equalize", .5, .5),
                  ("adaptive_gauss_thresh", .5, .5), ("opening_circle", .3, .5)]},
    "interleaved_worst": {
        "all": [("gaussian", .3, .5), ("median", .3, .5), ("unsharp", .5, .5), ("sobel_mag", .5, .5),
                ("threshold", .35, .5)],
        "mixed": [("gaussian", .3, .5), ("clahe", .5, .5), ("median", .3, .5), ("kirsch_amp", .5, .5),
                  ("unsharp", .5, .5), ("guided_filter", .5, .5), ("sobel_mag", .5, .5),
                  ("threshold", .35, .5)]},
}
PIPELINE_SIDES = (128, 256, 512, 1024, 2048, 4096)
PIPELINE_COUNTS = (1, 16)


def family_of(op: str) -> str:
    for fam, rows in FAMILIES.items():
        if any(name == op for name, _ in rows):
            return fam
    raise KeyError(op)


def sort_of(op: str) -> str:
    return next(s for rows in FAMILIES.values() for name, s in rows if name == op)


# ---- 前生成の画像 ---------------------------------------------------------------
_POOL: dict = {}


def _image(side: int, seed: int) -> np.ndarray:
    """構造のある検査画像(なだらかな陰影 + 周期 + 円 + 少しの雑音)を [0,1] float64 で作る。"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:side, 0:side].astype(np.float32) / max(side - 1, 1)
    f1, f2 = rng.uniform(2, 6, 2)
    v = 0.45 + 0.2 * np.sin(2 * np.pi * f1 * x + seed) * np.cos(2 * np.pi * f2 * y)
    for _ in range(24):
        cx, cy, r = rng.uniform(.05, .95), rng.uniform(.05, .95), rng.uniform(.01, .08)
        v[(x - cx) ** 2 + (y - cy) ** 2 < r * r] += rng.uniform(-.3, .3)
    v += rng.normal(0, .02, v.shape).astype(np.float32)
    return np.clip(v, 0, 1).astype(np.float64)


def _volume(side: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    z, y, x = np.mgrid[0:side, 0:side, 0:side].astype(np.float32) / max(side - 1, 1)
    v = 0.5 + 0.25 * np.sin(2 * np.pi * 3 * x) * np.cos(2 * np.pi * 2 * y) * np.sin(2 * np.pi * 2 * z + seed)
    v += rng.normal(0, .02, v.shape).astype(np.float32)
    return np.clip(v, 0, 1).astype(np.float64)


def pool(kind: str, side: int, n: int) -> list:
    """同じ前生成の入力を返す(4 種を巡回)。計測の外で作る。"""
    key = (kind, side)
    if key not in _POOL:
        for stale in [k for k in _POOL if k != key]:
            del _POOL[stale]                    # 4096^2 / 512^3 を抱え続けない
        if kind == "volume":
            base = [_volume(side, s) for s in range(2 if side >= 256 else 4)]
        else:
            base = [_image(side, s) for s in range(4)]
            if kind == "region":
                base = [(b > .5).astype(np.float64) for b in base]
        _POOL[key] = base
    base = _POOL[key]
    return [base[i % len(base)] for i in range(n)]


def template() -> np.ndarray:
    return _image(512, 0)[100:131, 100:131].copy()


def grid(op: str):
    if sort_of(op) == "volume":
        return VOL_SIDES, VOL_COUNTS
    return SIDES, COUNTS


# ---- 記録 ------------------------------------------------------------------------
def append(path: Path, rec: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        print(json.dumps(rec, ensure_ascii=False), file=f)


def load(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stamp() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ---- CPU --------------------------------------------------------------------------
def _cpu_call(op, imgs):
    import api
    if op == "ncc_locate":
        for im in imgs:
            api.apply(im, op, A, B, device="cpu", on_error="raise", template=template())
    else:
        for im in imgs:
            api.apply(im, op, A, B, device="cpu", on_error="raise")


def cmd_cpu(ns) -> int:
    """1 op を CPU で全格子。1 回が 90 s を超えたら番犬がプロセスごと落とし、親が打ち切りを記録する。"""
    out = Path(ns.out)
    for op in ns.ops.split(","):
        while True:
            rc = subprocess.call([sys.executable, __file__, "cpu-worker", "--op", op, "--out", str(out)])
            if rc == 0:
                break
            inflight = out.with_suffix(".inflight")
            if rc == 42 and inflight.exists():
                rec = json.loads(inflight.read_text(encoding="utf-8"))
                rec.update(status="cutoff", note="1 回の実行が 90 s を超えたので打ち切った", at=stamp())
                append(out, rec)
                continue
            print("cpu worker failed", op, rc)
            append(out, {"device": "cpu", "op": op, "status": "failed", "rc": rc, "at": stamp()})
            break
    return 0


def cmd_cpu_worker(ns) -> int:
    import api
    import ops as _ops
    op, out = ns.op, Path(ns.out)
    if op not in _ops.RT:
        append(out, {"device": "cpu", "op": op, "status": "unavailable",
                     "note": "この環境の登録簿に無い(scikit-image など)", "at": stamp()})
        return 0
    done = {(r["side"], r["n"]): r for r in load(out)
            if r.get("op") == op and r.get("device") == "cpu" and "side" in r}
    sides, counts = grid(op)
    kind = sort_of(op)
    api.apply(pool("image", 64, 1)[0], "gaussian", A, B, device="cpu")          # 遅延 import を時間の外へ
    _cpu_call(op, pool(kind, sides[0], 1))
    inflight = out.with_suffix(".inflight")
    t1_by_side: dict = {}
    for r in done.values():
        if r["n"] == 1:
            t1_by_side[r["side"]] = r.get("wall_s") or float("inf")
    for side in sides:
        for n in counts:
            if (side, n) in done:
                continue
            key = {"device": "cpu", "op": op, "family": family_of(op), "side": side, "n": n}
            prev = [v for s, v in t1_by_side.items() if s <= side]
            if prev and any(v == float("inf") for v in prev):
                append(out, dict(key, status="cutoff", note="より小さい寸法で 90 s を超えたので実行しなかった", at=stamp()))
                continue
            t1 = t1_by_side.get(side)
            if t1 is not None and t1 * n > CPU_LIMIT_S:
                append(out, dict(key, status="cutoff",
                                 note="1 枚の実測 %.1f s から 90 s 超が確実なので実行しなかった" % t1, at=stamp()))
                continue
            imgs = pool(kind, side, n)
            inflight.write_text(json.dumps(key), encoding="utf-8")
            walls, cpus = [], []
            reps, r = 3, 0
            while r < reps:
                dog = threading.Timer(CPU_LIMIT_S, lambda: os._exit(42))
                dog.daemon = True
                dog.start()
                t0, c0 = time.perf_counter(), time.process_time()
                _cpu_call(op, imgs)
                walls.append(time.perf_counter() - t0)
                cpus.append(time.process_time() - c0)
                dog.cancel()
                if r == 0:
                    reps = 7 if walls[0] < .5 else 5 if walls[0] < 5 else 3 if walls[0] < 30 else 2
                r += 1
            rec = dict(key, status="ok", wall_s=float(np.median(walls)), min_s=float(min(walls)),
                       proc_s=float(np.median(cpus)), reps=len(walls), at=stamp())
            append(out, rec)
            if n == 1:
                t1_by_side[side] = rec["wall_s"]
            print(op, side, n, "%.4f" % rec["wall_s"], flush=True)
    if inflight.exists():
        inflight.unlink()
    return 0


# ---- GPU の貸し借り ----------------------------------------------------------------
def lock_path() -> Path:
    p = os.environ.get("FULLSEYE_GPU_LOCK")
    if not p:
        raise SystemExit("FULLSEYE_GPU_LOCK が無い: 共有ロックを指定せずに GPU を使わない")
    return Path(p)


def unreal_running() -> bool:
    """UnrealEditor が居るか。確かめられないときは「居る」扱い(fail-closed)。tasklist は OEM 符号なので bytes で読む。"""
    try:
        q = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"],
                           capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return True
    return q.returncode != 0 or b"UnrealEditor.exe" in q.stdout


def gpu_state() -> dict:
    q = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                       capture_output=True, text=True, timeout=20)
    util, mem = [int(x) for x in q.stdout.strip().split(",")]
    return {"util_pct": util, "mem_mib": mem}


HANG_GRACE_S = 60.0     # 窓 480 s + 60 s でも 10 分に収まる
UNFOLD_OPS = {"median": 25, "percentile": 75}   # 既定つまみの k=5 unfold が要る倍率(percentile は sort の添字ぶん 3 倍)
VRAM_BUDGET_PX = 6e9    # float32 で 24 GB(WDDM は OOM を出さずページングで止まる)
EXIT_HUNG = 43
CURRENT: dict = {}      # 測っている最中の点(番犬が記録する)
CURRENT_OUT: list = [""]


class Lease:
    """共有 GPU の 1 窓。``with`` を抜ければ必ず自分のロックだけを消す。"""

    def __init__(self, budget_s: float):
        self.path = lock_path()
        # 行の形は「持ち主 ISO 時刻 pid=<pid>」(外の見張りが 12 分を超えたロックの持ち主を止めて消す)
        self.tag = "gpu_cross_%d %s pid=%d" % (os.getpid(), stamp(), os.getpid())
        self.budget_s = budget_s
        self.t0 = 0.0
        self.held = False

    def free(self) -> bool:
        return not self.path.exists() and not unreal_running()

    def acquire(self) -> bool:
        if not self.free():
            return False
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(self.tag)
        self.held = True
        self.t0 = time.monotonic()
        atexit.register(self.release)
        # 1 点が返らなくても(VRAM 溢れのページング)窓を超えない: 番犬がロックを消してプロセスごと落とす。
        self.dog = threading.Timer(self.budget_s + HANG_GRACE_S, self._abort)
        self.dog.daemon = True
        self.dog.start()
        return True

    def _abort(self) -> None:
        if CURRENT:
            CURRENT["status"] = "aborted"
            CURRENT["note"] = "窓の上限を超えても返らなかったので止めた(VRAM 溢れのページングを疑う)"
            CURRENT["at"] = stamp()
            append(CURRENT_OUT[0], dict(CURRENT))
        self.release()
        os._exit(EXIT_HUNG)

    def release(self) -> None:
        if not self.held:
            return
        self.held = False
        self.dog.cancel()
        try:
            if self.path.read_text(encoding="utf-8").strip() == self.tag:
                self.path.unlink()
        except FileNotFoundError:
            pass

    def ok(self) -> bool:
        """この窓を続けてよいか(期限内・ロックが自分のもの・UnrealEditor が居ない)。"""
        if time.monotonic() - self.t0 > self.budget_s:
            return False
        try:
            if self.path.read_text(encoding="utf-8").strip() != self.tag:
                return False
        except FileNotFoundError:
            return False
        return not unreal_running()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
        return False


def windows(ns, work) -> int:
    """``work(lease) -> bool(残りあり)`` を、ロックが空いた窓ごとに回す。"""
    deadline = time.monotonic() + ns.max_wait
    while time.monotonic() < deadline:
        lease = Lease(ns.window)
        if not lease.acquire():
            time.sleep(ns.poll)
            continue
        before = gpu_state()
        with lease:
            print("window start", stamp(), before, flush=True)
            more = work(lease)
            after = gpu_state()
        print("window end", stamp(), after, "more", more, flush=True)
        if not more:
            return 0
        time.sleep(ns.yield_s)                  # 譲る
    print("max-wait で終了(未測定の点が残る)", flush=True)
    return 3


# ---- GPU 格子 ----------------------------------------------------------------------
def _gpu_impl(op):
    """core op 名 -> (batch 関数, up, kernel, down)。"""
    import api
    import accel
    import accel_match
    import accel_vol
    import accel_bridge as bridge
    if op == "ncc_locate":
        return ("match", lambda imgs: accel_match.ncc_locate_batch(imgs, template(), device="cuda"), None)
    if op in bridge._C2VA:
        key = bridge._C2VA[op]
        return ("vol", lambda vols: accel_vol.run_batch_vol(key, vols, A, B, "cuda"),
                (accel_vol._to_vol_batch, accel_vol.VOL_ACCEL[key][0], accel_vol._from_vol_batch))
    key = api._accel_reverse(accel).get(op)
    if key is None:
        raise KeyError("no accel path for %s" % op)
    return ("image", lambda imgs: accel.run_batch(key, imgs, A, B, "cuda"),
            (accel._to_batch, accel.ACCEL[key][0], accel._from_batch))


def _gpu_point(op, side, n, sync):
    import torch
    kind, batch, parts = _gpu_impl(op)
    imgs = pool(sort_of(op), side, n)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    batch(imgs)
    sync()
    first = time.perf_counter() - t0
    walls = []
    while len(walls) < 7 and (len(walls) < 3 or sum(walls) < 2.0):   # 重い点は 3 回で足りる(GPU は共有)
        t0 = time.perf_counter()
        batch(imgs)
        sync()
        walls.append(time.perf_counter() - t0)
    rec = {"first_s": first, "wall_s": float(np.median(walls)), "min_s": float(min(walls)), "reps": len(walls),
           "peak_mib": torch.cuda.max_memory_allocated() / 2 ** 20}
    if parts is not None:
        up_f, fn, down_f = parts
        ups, kers, downs = [], [], []
        for _ in range(3 if rec["wall_s"] < 1.0 else 1):
            t0 = time.perf_counter()
            t = up_f(imgs, "cuda")
            sync()
            t1 = time.perf_counter()
            o = fn(t, A, B, "cuda").clamp(0, 1)
            sync()
            t2 = time.perf_counter()
            down_f(o)
            t3 = time.perf_counter()
            ups.append(t1 - t0)
            kers.append(t2 - t1)
            downs.append(t3 - t2)
            del t, o
        rec.update(up_s=float(np.median(ups)), kernel_s=float(np.median(kers)), down_s=float(np.median(downs)))
    return rec


def cmd_gpu(ns) -> int:
    import torch
    out = Path(ns.out)
    wanted = ns.ops.split(",") if ns.ops else [o for rows in FAMILIES.values() for o, _ in rows]
    todo = []
    for op in wanted:
        sides, counts = grid(op)
        todo += [(op, s, n) for s in sides for n in counts]
    # 4096^2 x 100 は入力だけで 6.7 GB。畳み込みの中間で VRAM(32 GB)を溢れ、OOM にならずページングで
    # 返らなくなった(gaussian)。点演算の threshold だけ測り、他は測らない(GPU は共有)。
    todo = [p for p in todo if not (p[1] == 4096 and p[2] == 100 and p[0] != "threshold")]
    # --skip "512x4,...": 体積 512³ x 4 は vol_median で VRAM を溢れて返らなかった(2026-11-03、番犬で停止)。
    # 同じ寸法の他の体積 op も測らない(1 点で 8 分ロックを握る)。測らなかった点は表に「未測定」と書く。
    skip = {tuple(int(v) for v in item.split("x")) for item in ns.skip.split(",") if item}
    todo = [p for p in todo if (p[1], p[2]) not in skip]
    bad = {}

    def work(lease) -> bool:
        import api
        import accel
        done = {(r["op"], r["side"], r["n"]) for r in load(out) if "side" in r}
        pending = [p for p in todo if p not in done]
        for op, side, n in pending:
            if not lease.ok():
                return True
            key = {"device": "cuda", "op": op, "family": family_of(op), "side": side, "n": n}
            if op == "sk_tv" and "sk_tv" not in accel.ACCEL:
                continue
            if op in UNFOLD_OPS and side * side * n * UNFOLD_OPS[op] > VRAM_BUDGET_PX:
                append(out, dict(key, status="skipped_vram", at=stamp(),
                                 note="unfold(と sort)が入力の %d 倍の VRAM を要し、32 GB を超える見積りなので実行しなかった" % UNFOLD_OPS[op]))
                continue
            if bad.get(op, (10 ** 9, 0))[0] * bad.get(op, (0, 0))[1] <= side * side * n and op in bad:
                append(out, dict(key, status="oom", note="より小さい負荷で VRAM が足りなかったので実行しなかった", at=stamp()))
                continue
            CURRENT.clear()
            CURRENT.update(key)
            CURRENT_OUT[0] = out
            try:
                rec = _gpu_point(op, side, n, torch.cuda.synchronize)
            except torch.OutOfMemoryError as e:
                torch.cuda.empty_cache()
                bad[op] = (side * side, n)
                append(out, dict(key, status="oom", note=str(e)[:160], at=stamp()))
                continue
            except Exception as e:  # noqa: BLE001 - a failing point is a result, not a stop
                append(out, dict(key, status="failed", note="%s: %s" % (type(e).__name__, str(e)[:200]), at=stamp()))
                continue
            if not lease.ok() and lease.t0 and time.monotonic() - lease.t0 <= lease.budget_s:
                print("窓の途中で他者が現れたので、この点は捨てる", op, side, n, flush=True)
                return True
            append(out, dict(key, status="ok", at=stamp(), **rec))
            print(op, side, n, "%.4f" % rec["wall_s"], flush=True)
        return False

    return windows(ns, work)


# ---- 初回起動 ----------------------------------------------------------------------
_COLD = """
import json, sys, time
t0 = time.perf_counter()
sys.path.insert(0, %(root)r)
import numpy as np
import api
t_api = time.perf_counter()
torch_at_import = "torch" in sys.modules
im = np.load(%(path)r)
cold = time.perf_counter()
import torch
t_torch = time.perf_counter()
ok = torch.cuda.is_available()
t_avail = time.perf_counter()
x = torch.zeros(1, device="cuda"); torch.cuda.synchronize()
t_ctx = time.perf_counter()
api.apply(im, "gaussian", .5, .5, device="cuda", on_error="raise"); torch.cuda.synchronize()
t_first = time.perf_counter()
api.apply(im, "gaussian", .5, .5, device="cuda", on_error="raise"); torch.cuda.synchronize()
t_second = time.perf_counter()
api.apply(im, "median", .5, .5, device="cuda", on_error="raise"); torch.cuda.synchronize()
t_other = time.perf_counter()
print(json.dumps(dict(import_api_s=t_api - t0, torch_at_import=torch_at_import, import_torch_s=t_torch - cold,
                      is_available_s=t_avail - t_torch, context_s=t_ctx - t_avail, first_op_s=t_first - t_ctx,
                      second_op_s=t_second - t_first, first_other_op_s=t_other - t_second, cuda=ok)))
"""


def cmd_cold(ns) -> int:
    out = Path(ns.out)
    tmp = Path(ns.tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    paths = {}
    for side in (512, 2048):
        paths[side] = tmp / ("cold_%d.npy" % side)
        np.save(paths[side], _image(side, 0))
    todo = [(side, i) for side in paths for i in range(ns.reps)]

    def work(lease) -> bool:
        done = {(r["side"], r["i"]) for r in load(out)}
        for side, i in todo:
            if (side, i) in done:
                continue
            if not lease.ok():
                return True
            code = _COLD % {"root": str(ROOT), "path": str(paths[side])}
            q = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=240)
            if q.returncode:
                print(q.stderr[-800:], flush=True)
                return False
            rec = json.loads(q.stdout.strip().splitlines()[-1])
            if lease.ok():
                append(out, dict(rec, side=side, i=i, at=stamp()))
                print(side, i, rec, flush=True)
        return False

    return windows(ns, work)


# ---- パイプライン ------------------------------------------------------------------
def _instrument():
    """転送と CPU 区間の時間・回数を数える包み。元に戻す関数を返す。"""
    import accel
    import ops as _ops
    box = {"up_s": 0.0, "down_s": 0.0, "cpu_s": 0.0, "up_n": 0, "down_n": 0, "cpu_n": 0}
    to0, from0, st0 = accel._to_batch, accel._from_batch, _ops.run_stages

    def to(imgs, device):
        t0 = time.perf_counter()
        t = to0(imgs, device)
        box["up_s"] += time.perf_counter() - t0
        box["up_n"] += 1
        return t

    def frm(t):
        t0 = time.perf_counter()
        o = from0(t)
        box["down_s"] += time.perf_counter() - t0
        box["down_n"] += 1
        return o

    def st(items, im):
        t0 = time.perf_counter()
        o = st0(items, im)
        box["cpu_s"] += time.perf_counter() - t0
        box["cpu_n"] += 1
        return o

    accel._to_batch, accel._from_batch, _ops.run_stages = to, frm, st

    def undo():
        accel._to_batch, accel._from_batch, _ops.run_stages = to0, from0, st0

    return box, undo


def _pipe_run(chain, imgs, device):
    import api
    import accel_bridge as bridge
    if device == "cpu":
        for im in imgs:
            api.run_pipeline(im, chain, device="cpu", on_error="raise")
    else:
        bridge.run(chain, imgs, device="cuda")


def _pipe_gpu_point(chain, side, n, sync):
    import accel_bridge as bridge
    imgs = pool("image", side, n)
    _pipe_run(chain, imgs, "cuda")
    sync()
    walls, boxes = [], []
    limit = time.monotonic() + 45
    while len(walls) < 5 and (len(walls) < 3 or time.monotonic() < limit):
        box, undo = _instrument()
        t0 = time.perf_counter()
        try:
            _pipe_run(chain, imgs, "cuda")
            sync()
        finally:
            undo()
        box["wall_s"] = time.perf_counter() - t0
        walls.append(box["wall_s"])
        boxes.append(box)
    med = boxes[int(np.argsort(walls)[len(walls) // 2])]
    cov = bridge.coverage(chain)
    return dict(med, reps=len(walls), n_gpu_segments=cov["n_gpu_segments"], n_gpu_ops=cov["n_gpu"],
                n_cpu_ops=cov["n_cpu"], kernel_s=med["wall_s"] - med["up_s"] - med["down_s"] - med["cpu_s"])


def cmd_pipe_cpu(ns) -> int:
    out = Path(ns.out)
    done = {(r["pipeline"], r["variant"], r["side"], r["n"]) for r in load(out)}
    blown: set = set()
    for name, variants in PIPELINES.items():
        for variant, chain in variants.items():
            for side in PIPELINE_SIDES:
                for n in PIPELINE_COUNTS:
                    if (name, variant, side, n) in done:
                        continue
                    key = {"device": "cpu", "pipeline": name, "variant": variant, "side": side, "n": n}
                    if any(p == (name, variant) and side * side * n >= s for p, s in blown):
                        append(out, dict(key, status="cutoff", note="小さい負荷で 90 s を超えたので実行しなかった", at=stamp()))
                        continue
                    imgs = pool("image", side, n)
                    walls = []
                    for r in range(3):
                        t0 = time.perf_counter()
                        _pipe_run(chain, imgs, "cpu")
                        walls.append(time.perf_counter() - t0)
                        if walls[-1] > CPU_LIMIT_S or (r == 1 and walls[0] > 30):
                            break
                    if max(walls) > CPU_LIMIT_S:
                        blown.add(((name, variant), side * side * n))
                        append(out, dict(key, status="cutoff", note="実行が 90 s を超えた(%.0f s)" % max(walls), at=stamp()))
                        continue
                    append(out, dict(key, status="ok", wall_s=float(np.median(walls)), reps=len(walls), at=stamp()))
                    print(name, variant, side, n, "%.3f" % float(np.median(walls)), flush=True)
    return 0


def cmd_pipe_gpu(ns) -> int:
    import torch
    out = Path(ns.out)
    # 4096^2 x 16 は median の unfold で VRAM を溢れる見積りなので測らない(未測定)
    todo = [(name, v, s, n) for name, vs in PIPELINES.items() for v in vs for s in PIPELINE_SIDES
            for n in PIPELINE_COUNTS if not (s == 4096 and n == 16)]

    def work(lease) -> bool:
        done = {(r["pipeline"], r["variant"], r["side"], r["n"]) for r in load(out)}
        for name, v, s, n in todo:
            if (name, v, s, n) in done:
                continue
            if not lease.ok():
                return True
            key = {"device": "cuda", "pipeline": name, "variant": v, "side": s, "n": n}
            torch.cuda.empty_cache()
            CURRENT.clear()
            CURRENT.update(key)
            CURRENT_OUT[0] = out
            try:
                rec = _pipe_gpu_point(PIPELINES[name][v], s, n, torch.cuda.synchronize)
            except torch.OutOfMemoryError as e:
                torch.cuda.empty_cache()
                append(out, dict(key, status="oom", note=str(e)[:160], at=stamp()))
                continue
            if lease.ok():
                append(out, dict(key, status="ok", at=stamp(), **rec))
                print(name, v, s, n, "%.3f" % rec["wall_s"], flush=True)
        return False

    return windows(ns, work)


RECHECK_SIDES = (128, 256)
RECHECK_REPS = 15


def cmd_pipe_recheck(ns) -> int:
    """小さい寸法の鎖を、同じプロセスで CPU と GPU を交互に 15 回ずつ測り直す(全パイプライン・全変種)。

    pipe-cpu と pipe-gpu は別のプロセス・別の時刻に 3〜5 回で測った。1〜2 ms の点では 10 % 前後の差が
    揺れに埋もれるので、規則の採否を分ける寸法(128, 256)だけ全部を測り直す(選んだ点だけではない)。
    """
    import torch
    out = Path(ns.out)
    sync = torch.cuda.synchronize
    todo = [(name, v, s) for name, vs in PIPELINES.items() for v in vs for s in RECHECK_SIDES]

    def work(lease) -> bool:
        done = {(r["pipeline"], r["variant"], r["side"]) for r in load(out)}
        for name, v, side in todo:
            if (name, v, side) in done:
                continue
            if not lease.ok():
                return True
            chain = PIPELINES[name][v]
            imgs = pool("image", side, 1)
            _pipe_run(chain, imgs, "cpu")
            _pipe_run(chain, imgs, "cuda")
            sync()
            cpu_w, gpu_w = [], []
            for _ in range(RECHECK_REPS):
                t0 = time.perf_counter()
                _pipe_run(chain, imgs, "cpu")
                cpu_w.append(time.perf_counter() - t0)
                t0 = time.perf_counter()
                _pipe_run(chain, imgs, "cuda")
                sync()
                gpu_w.append(time.perf_counter() - t0)
            if lease.ok():
                append(out, {"pipeline": name, "variant": v, "side": side, "n": 1, "status": "ok",
                             "cpu_s": float(np.median(cpu_w)), "gpu_s": float(np.median(gpu_w)),
                             "cpu_min_s": float(min(cpu_w)), "gpu_min_s": float(min(gpu_w)),
                             "reps": RECHECK_REPS, "at": stamp()})
                print(name, v, side, "%.3f ms cpu / %.3f ms gpu" % (np.median(cpu_w) * 1e3, np.median(gpu_w) * 1e3),
                      flush=True)
        return False

    return windows(ns, work)


# ---- 全 accel op の反証掃引(規則が代表の外で遅くならないかを見る) ------------------
SWEEP_SIDES = (128, 256, 512, 1024, 2048)
SWEEP_KNOBS = (0.2, 0.5, 0.9)


def sweep_ops() -> list:
    """accel を持つ core op 全部(登録簿に在るもの)を (op, 入力の種) で返す。"""
    import api
    import accel
    rows = {r["name"]: r for r in api._rows()}
    out = []
    for core in sorted(api._accel_reverse(accel)):
        r = rows.get(core)
        if r and r["in_sort"] in ("image", "region"):
            out.append((core, r["in_sort"]))
    return out


def _sweep_times(op, im, a, device, sync=lambda: None):
    import api
    api.apply(im, op, a, B, device=device, on_error="raise")      # 温め(遅延 import、op 初回)
    sync()
    walls = []
    while len(walls) < 3 or (len(walls) < 5 and sum(walls) < 2.0):
        t0 = time.perf_counter()
        api.apply(im, op, a, B, device=device, on_error="raise")
        sync()
        walls.append(time.perf_counter() - t0)
    return float(np.median(walls)), len(walls)


def cmd_sweep_cpu(ns) -> int:
    """全 accel op を CPU で。番犬で落ちたら親が打ち切りを記録して続ける。"""
    out = Path(ns.out)
    while True:
        rc = subprocess.call([sys.executable, __file__, "sweep-cpu-worker", "--out", str(out)])
        if rc == 0:
            return 0
        inflight = out.with_suffix(".inflight")
        if rc != 42 or not inflight.exists():
            print("sweep worker failed", rc)
            return rc
        append(out, dict(json.loads(inflight.read_text(encoding="utf-8")), status="cutoff", at=stamp(),
                         note="1 回の実行が 90 s を超えたので打ち切った"))


def cmd_sweep_cpu_worker(ns) -> int:
    out = Path(ns.out)
    done = {(r["op"], r["side"], r["a"]) for r in load(out)}
    inflight = out.with_suffix(".inflight")
    for op, kind in sweep_ops():
        for side in SWEEP_SIDES:
            for a in SWEEP_KNOBS:
                if (op, side, a) in done:
                    continue
                key = {"device": "cpu", "op": op, "side": side, "a": a}
                inflight.write_text(json.dumps(key), encoding="utf-8")
                dog = threading.Timer(CPU_LIMIT_S * 3, lambda: os._exit(42))
                dog.daemon = True
                dog.start()
                try:
                    wall, reps = _sweep_times(op, pool(kind, side, 1)[0], a, "cpu")
                    rec = dict(key, status="ok", wall_s=wall, reps=reps, at=stamp())
                except Exception as e:  # noqa: BLE001 - a failing op is a result
                    rec = dict(key, status="failed", note="%s: %s" % (type(e).__name__, str(e)[:160]), at=stamp())
                dog.cancel()
                append(out, rec)
    if inflight.exists():
        inflight.unlink()
    return 0


def cmd_sweep_gpu(ns) -> int:
    import torch
    import gpu_route
    out = Path(ns.out)
    # 掃引は op 単独の損益分岐を測る。鎖の枠だけの手書き経路(GPU_ACCEL_USE.json の use="pipeline")は
    # apply が単独では GPU に送らない(chain_only)ので、ここでは場面の台帳を外して kernel を単独で測る。
    # 外さないと CPU と CPU を比べた行が GPU の行として残る(2026-11-03、179 行を測り直した)。
    gpu_route.clear_cache()
    gpu_route._CACHE["accel_use"] = {}

    cpu_log = {(r["op"], r["side"], r["a"]): r for r in load(out.with_name("sweep_cpu.jsonl")) if r["status"] == "ok"}
    tools_dir = str(ROOT / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    from gen_device_rules import cpu_not_worse

    def settled(op, rows):
        """閾値が決まった op か(CPU が負けた点が 1 つでも出た)。それより大きい寸法は規則に関わらない。"""
        for r in rows:
            c = cpu_log.get((op, r["side"], r["a"]))
            if r["op"] == op and r["status"] == "ok" and c and not cpu_not_worse(c["wall_s"], r["wall_s"]):
                return True
        return False

    def work(lease) -> bool:
        rows = load(out)
        done = {(r["op"], r["side"], r["a"]) for r in rows}
        for op, kind in sweep_ops():
            rows_op = [r for r in rows if r["op"] == op]
            for side in SWEEP_SIDES:
                for a in SWEEP_KNOBS:
                    if settled(op, rows_op):
                        break
                    if (op, side, a) in done:
                        continue
                    if not lease.ok():
                        return True
                    key = {"device": "cuda", "op": op, "side": side, "a": a}
                    CURRENT.clear()
                    CURRENT.update(key)
                    CURRENT_OUT[0] = out
                    try:
                        wall, reps = _sweep_times(op, pool(kind, side, 1)[0], a, "cuda", torch.cuda.synchronize)
                        rec = dict(key, status="ok", wall_s=wall, reps=reps, at=stamp())
                    except Exception as e:  # noqa: BLE001 - a failing op is a result
                        torch.cuda.empty_cache()
                        rec = dict(key, status="failed", note="%s: %s" % (type(e).__name__, str(e)[:160]), at=stamp())
                    if lease.ok():
                        append(out, rec)
                        rows_op.append(rec)
        return False

    return windows(ns, work)


# ---- 規則の before/after(実際の device="auto" を、規則が無かったときの device="cuda" と比べる) -------
BA_SIDES = (90, 128, 181, 256, 362, 512, 724, 1024, 1448, 2048)    # 掃引の間の寸法も測る
BA_PIPE_SIDES = (128, 181, 256, 362, 512, 724, 1024, 1448, 2048)
BA_KNOBS = (0.5, 0.9)

_BA_COLD = """
import json, sys, time
sys.path.insert(0, %(root)r)
import numpy as np
import api
im = np.load(%(path)r)
import torch
device = %(device)r
t0 = time.perf_counter()
for _ in range(%(calls)d):
    api.apply(im, %(op)r, .5, .5, device=device, on_error="raise")
if torch.cuda.is_initialized():
    torch.cuda.synchronize()
print(json.dumps(dict(wall_s=time.perf_counter() - t0, gpu_used=torch.cuda.is_initialized())))
"""


def _pipe_times(chain, im, device, sync):
    import api
    api.run_pipeline(im, chain, device=device, on_error="raise")
    sync()
    walls = []
    while len(walls) < 3 or (len(walls) < 5 and sum(walls) < 2.0):
        t0 = time.perf_counter()
        api.run_pipeline(im, chain, device=device, on_error="raise")
        sync()
        walls.append(time.perf_counter() - t0)
    return float(np.median(walls))


def cmd_before_after(ns) -> int:
    """規則が CPU に回す点だけを測る(GPU に送る点は before と同じ道なので差が出ない)。"""
    import torch
    import device_policy
    out = Path(ns.out)
    sync = torch.cuda.synchronize

    def work(lease) -> bool:
        import api
        done = {(r["kind"], r["name"], r["side"], r.get("a")) for r in load(out)}
        accel_names = api._gpu_op_names()
        import gpu_route
        for op, kind in sweep_ops():
            if gpu_route.route(op, "single") is None:
                # 鎖の枠だけの手書き経路は、単独の呼び出しを規則表ではなく採用の門(5 倍)が CPU に決めている。
                # before(cuda)も after(auto)も同じ CPU の道なので、測っても揺れしか測れない(2026-11-03 に
                # 292 点を測り、同じ道どうしで 8 点が 10 % を超えて食い違った)。単独で CPU になることは
                # tests/test_device_rules.py が経路の判定として決定的に見る。
                continue
            for side in BA_SIDES:
                if device_policy.route([op], (side, side), accelerated=accel_names) != "cpu":
                    continue
                for a in BA_KNOBS:
                    if ("op", op, side, a) in done:
                        continue
                    if not lease.ok():
                        return True
                    im = pool(kind, side, 1)[0]
                    # before = 規則表の無かったとき(明示の cuda)。鎖の枠だけの手書き経路(use="pipeline")は規則表と
                    # 関係なく単独では CPU(chain_only)なので before も CPU —— 単独で 5 倍に届かない GPU の勝ちは
                    # 規則表ではなく採用の門(GPU_ACCEL_USE.json の ratio_single)に記録してある。
                    # 2026-11-03: いったん before だけ場面の台帳を外して kernel を測ったが、それは規則表でなく
                    # 5 倍の門を検査することになり(cv_cc_count が 724 で 1.6 倍勝つ)、この表の門の意味から外れた。
                    before, _ = _sweep_times(op, im, a, "cuda", sync)
                    after, _ = _sweep_times(op, im, a, "auto", sync)
                    if lease.ok():
                        append(out, {"kind": "op", "name": op, "side": side, "a": a, "before_s": before,
                                     "after_s": after, "at": stamp()})
        for name, variants in PIPELINES.items():
            for variant, chain in variants.items():
                names = [s[0] for s in chain]
                for side in BA_PIPE_SIDES:
                    label = "%s/%s" % (name, variant)
                    if ("pipeline", label, side, None) in done:
                        continue
                    if api.resolve_device("auto", stages=names, shape=(side, side)) != "cpu":
                        continue
                    if not lease.ok():
                        return True
                    im = pool("image", side, 1)[0]
                    before = _pipe_times(chain, im, "cuda", sync)
                    after = _pipe_times(chain, im, "auto", sync)
                    if lease.ok():
                        append(out, {"kind": "pipeline", "name": label, "side": side, "before_s": before,
                                     "after_s": after, "at": stamp()})
        tmp = Path(ns.tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        for op, side, calls in (("gaussian", 256, 1), ("gaussian", 256, 20), ("threshold", 1024, 20),
                                ("fill_holes", 1024, 5)):
            for rep in range(3):
                label = "%s x%d" % (op, calls)
                if ("cold", label, side, rep) in done:
                    continue
                if not lease.ok():
                    return True
                kind = sort_of(op)
                path = tmp / ("ba_%s_%d.npy" % (kind, side))
                np.save(path, pool(kind, side, 1)[0])
                times = {}
                for device in ("cuda", "auto"):
                    code = _BA_COLD % {"root": str(ROOT), "path": str(path), "device": device, "calls": calls, "op": op}
                    q = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=240)
                    if q.returncode:
                        print(q.stderr[-600:], flush=True)
                        return False
                    times[device] = json.loads(q.stdout.strip().splitlines()[-1])
                if lease.ok():
                    append(out, {"kind": "cold", "name": label, "side": side, "a": rep,
                                 "before_s": times["cuda"]["wall_s"], "after_s": times["auto"]["wall_s"],
                                 "after_used_gpu": times["auto"]["gpu_used"], "at": stamp()})
        return False

    return windows(ns, work)


SHADOW_SAMPLE = 12


def shadow_sample() -> list:
    """許可リスト(単独 ``ops``)の登録 op のうち入力が image で 2048² で測ったもの、名前順に等間隔で 12 件。"""
    import api
    import gpu_route
    rows = {r["name"]: r for r in api._rows()}
    names = []
    for op in sorted(rows):
        r = gpu_route.route(op, "single")
        if (r is not None and r.kind == "shadow" and r.min_elements == 2048 * 2048
                and rows[op]["in_sort"] == "image"):
            names.append(op)
    step = max(1, len(names) // SHADOW_SAMPLE)
    return names[::step][:SHADOW_SAMPLE]


def cmd_shadow_check(ns) -> int:
    """許可リストの道の before/after: before = 規則の前(GPU 経路の無い op は CPU)、after = ``device="auto"``。

    一辺 2048(倍率を測った大きさ)と 1024(auto が CPU に残す大きさ)で測る。after の経路は
    ``api.last_device_decision()`` を記録する(GPU に行ったと言うのは経路が ``allow_single`` のときだけ)。
    """
    import torch
    out = Path(ns.out)
    sync = torch.cuda.synchronize

    def work(lease) -> bool:
        import api
        done = {(r["name"], r["side"]) for r in load(out)}
        for op in shadow_sample():
            for side in (2048, 1024):
                if (op, side) in done:
                    continue
                if not lease.ok():
                    return True
                im = pool("image", side, 1)[0]
                try:
                    before, _ = _sweep_times(op, im, 0.5, "cpu", sync)
                    after, reps = _sweep_times(op, im, 0.5, "auto", sync)
                    dec = api.last_device_decision() or {}
                    rec = {"kind": "shadow", "name": op, "side": side, "before_s": before, "after_s": after,
                           "path": dec.get("path"), "device": dec.get("device"), "reason": dec.get("reason"),
                           "reps": reps, "status": "ok", "at": stamp()}
                except Exception as e:  # noqa: BLE001 - a failing op is a result
                    rec = {"kind": "shadow", "name": op, "side": side, "status": "failed",
                           "note": "%s: %s" % (type(e).__name__, str(e)[:160]), "at": stamp()}
                if lease.ok():
                    append(out, rec)
                    print(op, side, rec.get("before_s"), rec.get("after_s"), rec.get("path"), flush=True)
        return False

    return windows(ns, work)


def cmd_env(_ns) -> int:
    import scipy
    import cv2
    print(json.dumps({"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                      "cv2": cv2.__version__, "machine": platform.processor(),
                      "logical_cpus": os.cpu_count()}))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("cpu", cmd_cpu), ("cpu-worker", cmd_cpu_worker), ("gpu", cmd_gpu), ("cold", cmd_cold),
                     ("pipe-cpu", cmd_pipe_cpu), ("pipe-gpu", cmd_pipe_gpu), ("env", cmd_env),
                     ("sweep-cpu", cmd_sweep_cpu), ("sweep-cpu-worker", cmd_sweep_cpu_worker),
                     ("sweep-gpu", cmd_sweep_gpu), ("before-after", cmd_before_after),
                     ("pipe-recheck", cmd_pipe_recheck), ("shadow-check", cmd_shadow_check)):
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        p.add_argument("--out", default="")
        p.add_argument("--op", default="")
        p.add_argument("--ops", default="")
        p.add_argument("--tmp", default="")
        p.add_argument("--reps", type=int, default=5)
        p.add_argument("--skip", default="", help="測らない (一辺 x 枚数) の点、例 512x4")
        p.add_argument("--window", type=float, default=480.0, help="1 窓の上限 s(ロックの保持)")
        p.add_argument("--yield-s", dest="yield_s", type=float, default=60.0, help="窓の間に譲る s")
        p.add_argument("--poll", type=float, default=30.0)
        p.add_argument("--max-wait", dest="max_wait", type=float, default=6 * 3600.0)
    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    raise SystemExit(main())
