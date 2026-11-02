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

torch を import しない(表を引くだけ)。
"""
from __future__ import annotations

import json
import os

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
        # 2 段以上は転送が 1 回に償却されるので、単 op の表ではなくパイプラインの実測の閾値を使う。
        unknown = [name for name in names if _op_threshold(table, name, n) is None
                   and (accelerated is None or name in accelerated)]
        threshold = None if unknown else table["pipeline"]["min_pixels"]
    if threshold is None or px >= threshold:
        return "cuda"
    return "cpu"
