"""``device="auto"`` の判断 / The measured CPU-vs-GPU routing rule behind ``device="auto"``.

``api.resolve_device`` が「GPU が在る」と判った後にだけ呼ばれ、この仕事を GPU に送る価値があるかを実測の表
(``fullseye/data/DEVICE_RULES.json``、生成は ``tools/gen_device_rules.py``、根拠は
``docs/perf/gpu_crossover_2026-11-02.md``)で決める。

* 規則がするのは 1 つだけ: 「転送込みで GPU が CPU に勝たない」と実測した大きさを CPU に残す。
* 表は常駐後(GPU の初回起動の後)の値で作る。初回起動は 1 プロセス 1 回の固定費なので判断に入れない。
* 判断できないとき(表が無い・壊れている・op が表に無い・大きさが判らない)は GPU を返す。これは規則を
  入れる前の挙動で、黙って CPU へ倒すと大きな画像が遅くなる。
* 表は 1 台の機械の実測である。GPU が弱い機械では境界は大きい側へ動くだけなので、「CPU に残す」判断は
  崩れない。CPU が極端に弱い機械では、小さい画像で GPU の勝ちを取りこぼすことがある。

torch を import しない(表を引くだけ)。空き VRAM を見る :func:`free_vram_mb` だけは、すでに import
された torch / CuPy に問い合わせる(自分では import しない)。

経路(path)と、CPU を選んだ理由(reason)の語彙 / Vocabulary of the decision:

* path: ``accel``(手書きの torch 経路)/ ``allow_single``(許可リスト ``ops``、単独呼びで 5 倍以上)/
  ``allow_resident``(``resident_ops``、GPU に載せたままの連続処理で 5 倍以上)/ ``allow_pipeline``
  (``pipeline_ops``、常駐で 1〜5 倍)/ ``cpu``。
* reason(``cpu`` のとき): ``requested_cpu`` / ``env_cpu``(``FULLSEYE_DEVICE=cpu``)/ ``no_cuda`` /
  ``vram_low`` / ``crossover``(転送込みで GPU が勝たない大きさ)/ ``not_listed``(GPU 経路が無く許可
  リストにも無い)/ ``chain_only``(常駐の枠だけで、単独では採用していない)/ ``no_cupy``(許可リストの
  道を走らせる CuPy が無い)/ ``below_measured_size``(許可リストの倍率を測った大きさ未満)。
"""
from __future__ import annotations

import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATH = os.path.join(_HERE, "fullseye", "data", "DEVICE_RULES.json")
_CACHE: list = []          # [dict | None](読み込みは 1 回)


def load_rules():
    """同梱の規則表を返す(読めないときは ``None`` = 規則なしで GPU のまま)。"""
    if not _CACHE:
        try:
            with open(_PATH, encoding="utf-8") as f:
                table = json.load(f)
            _CACHE.append(table if table.get("schema") == 1 else None)
        except (OSError, ValueError, AttributeError):
            _CACHE.append(None)
    return _CACHE[0]


def _pixels(shape) -> int | None:
    """*shape* の総画素数(判らないときは ``None``)。"""
    try:
        px = 1
        for s in shape:
            px *= int(s)
    except (TypeError, ValueError):
        return None
    return px if px > 0 else None


def _op_threshold(table: dict, op: str, n: int) -> int | None:
    """1 枚あたりの画素数の閾値。これ未満なら CPU。表に無い op は ``None``。"""
    row = table["ops"].get(op) if isinstance(op, str) else None
    if row is None:
        return None
    threshold = row["min_pixels"]
    if n > 1:
        by_n = table["batch"].get(row["family"], {})
        fitting = [int(k) for k in by_n if int(k) <= n]
        if fitting:
            threshold = min(threshold, by_n[str(max(fitting))])
    return threshold


def route(names, shape, n: int = 1, rules: dict | None = None, accelerated=None) -> str:
    """*names*(op 名の列)を *shape* の入力 *n* 枚に流すときの装置 ``"cpu"`` / ``"cuda"`` を返す。

    *accelerated* = GPU 経路を持つ op 名の集合。パイプラインの段のうち、ここに無い段は CPU でしか走らないので
    判断から外す。ここに在るのに表に無い段(まだ測っていない GPU 経路)があれば GPU のまま返す。
    """
    table = rules if rules is not None else load_rules()
    px = _pixels(shape)
    names = list(names)
    if table is None or px is None or not names:
        return "cuda"
    n = max(int(n), 1)
    if len(names) == 1:
        threshold = _op_threshold(table, names[0], n)
    else:
        threshold = _chain_threshold(table, names, n, accelerated)
    if threshold is None or px >= threshold:
        return "cuda"
    return "cpu"


def _chain_threshold(table: dict, names, n: int, accelerated) -> int | None:
    """2 段以上の鎖の閾値(``None`` = 判断しない = GPU のまま)。

    規則は「GPU 経路を持つ全段が単独でも CPU に残る大きさなら、鎖も CPU」(``min_stage``)。鎖は転送が
    1 回に償却されるので単独より GPU 寄りになりうる。だからこの規則は、測った鎖の全点で遅くならなかった
    ときだけ採用される(表の ``pipeline.adopted``、生成は ``tools/gen_device_rules.py``)。採用されて
    いない・GPU 経路を持つのに表に無い段がある・GPU 経路を持つ段が無い、のどれかなら判断しない。
    """
    rule = table.get("pipeline") or {}
    if rule.get("rule") != "min_stage" or not rule.get("adopted"):
        return None
    gpu_stages = [name for name in names if accelerated is None or name in accelerated]
    if not gpu_stages:
        return None
    limits = [_op_threshold(table, name, n) for name in gpu_stages]
    if any(t is None for t in limits):
        return None
    return min(limits)


# ---- 空き VRAM(LLM と同じ GPU を分け合う場面) -------------------------------------------
#: 既定の閾値 MiB。根拠は docs/perf/gpu_crossover_2026-11-02.md の「VRAM の閾値」: CUDA の文脈
#: (torch + CuPy)と、一辺 4096 の 1 枚を 1 op 通すときの作業領域の 90 パーセンタイルの和に余裕を足した値。
DEFAULT_MIN_FREE_MB = 2048
_VRAM_TTL_S = 1.0
_VRAM_CACHE: list = []      # [(monotonic, free_mb | None)]


def min_free_mb() -> int:
    """``FULLSEYE_GPU_MIN_FREE_MB``(整数 MiB、0 で判定しない)。読めない値は既定値。"""
    raw = os.environ.get("FULLSEYE_GPU_MIN_FREE_MB", "").strip()
    if not raw:
        return DEFAULT_MIN_FREE_MB
    try:
        value = int(float(raw))
    except ValueError:
        return DEFAULT_MIN_FREE_MB
    return value if value >= 0 else DEFAULT_MIN_FREE_MB


def _query_free_mb():
    """空き VRAM(MiB、装置全体 = 他のプロセスの使用分を引いた値)。問い合わせられなければ ``None``。"""
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_available():
                free, _total = torch.cuda.mem_get_info()
                return free / 2 ** 20
        except Exception:  # noqa: BLE001 - 問い合わせの失敗は「判定しない」
            pass
    cupy = sys.modules.get("cupy")
    if cupy is not None:
        try:
            free, _total = cupy.cuda.runtime.memGetInfo()
            return free / 2 ** 20
        except Exception:  # noqa: BLE001
            pass
    return None


def free_vram_mb():
    """空き VRAM(MiB)。1 秒だけ覚えておく(呼ぶたびに装置へ問い合わせない)。"""
    now = time.monotonic()
    if _VRAM_CACHE and now - _VRAM_CACHE[0][0] < _VRAM_TTL_S:
        return _VRAM_CACHE[0][1]
    value = _query_free_mb()
    _VRAM_CACHE[:] = [(now, value)]
    return value


def vram_ok():
    """``(GPU を選んでよいか, 空き MiB | None, 閾値 MiB)``。測れないとき・閾値 0 は判定しない(True)。"""
    need = min_free_mb()
    if need <= 0:
        return True, None, need
    free = free_vram_mb()
    if free is None:
        return True, None, need
    return free >= need, round(free, 1), need


# ---- 段ごとの経路(どの経路があるかは gpu_route.route だけが知る) ------------------------------
def plan_paths(names, shape, *, route_of, runnable, auto: bool) -> list:
    """段ごとの ``(path, reason)``。GPU を使ってよい装置であることは呼ぶ側が確かめてある。

    *route_of* = :func:`gpu_route.route`(``(op, context) -> Route | None``)、*runnable* =
    :func:`gpu_route.runnable`。経路の有無と優先順位はそちらが決め、ここは段の並びと大きさだけを見る。

    * 手書きの経路(``accel``)は ``accel``(大きさは損益分岐の表 :func:`route` が別に見る)。
    * 許可リスト(shadow)・native: ``auto`` では入力の要素数が倍率を測った大きさ以上のときだけ
      (それ未満は測っていない = 勝つと言えない)。明示の ``cuda`` では大きさを問わない。
    * 常駐・鎖の枠(``allow_resident`` / ``allow_pipeline``)は隣も許可リストの段のときだけ。単独の
      呼び出しや孤立した段は ``chain_only`` で CPU。
    * 鎖の枠の手書き経路(``accel`` で ``use="pipeline"``、領域の解析の族)は隣も ``accel`` の段のときだけ
      (同じ torch の常駐区間に載る)。孤立すれば ``chain_only`` で CPU。
    """
    names = list(names)
    elements = _pixels(shape) if shape is not None else None
    context = "pipeline" if len(names) > 1 else "single"
    out = []
    chain_slot = []
    for name in names:
        r = route_of(name, context)
        chain_slot.append(r is not None and r.kind == "accel" and r.use in ("resident", "pipeline"))
        if r is None:
            chain = context == "single" and route_of(name, "pipeline") is not None
            out.append(("cpu", "chain_only" if chain else "not_listed"))
        elif r.kind == "accel":
            out.append(("accel", None))
        elif not runnable(r):
            out.append(("cpu", "no_cupy" if r.kind == "shadow" else "native_not_wired"))
        elif auto and (r.min_elements is None or elements is None or elements < r.min_elements):
            out.append(("cpu", "below_measured_size"))
        else:
            out.append((r.path, None))
    first = list(out)
    for i, (path, _r) in enumerate(first):
        if path in ("allow_resident", "allow_pipeline"):
            left = i > 0 and first[i - 1][0].startswith("allow_")
            right = i + 1 < len(first) and first[i + 1][0].startswith("allow_")
            if not (left or right):
                out[i] = ("cpu", "chain_only")
        elif path == "accel" and chain_slot[i]:
            left = i > 0 and first[i - 1][0] == "accel"
            right = i + 1 < len(first) and first[i + 1][0] == "accel"
            if not (left or right):
                out[i] = ("cpu", "chain_only")
    return out
