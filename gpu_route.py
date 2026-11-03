# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gpu_route — the one place that knows which GPU path an operator has / 1 op の GPU 経路を決める唯一の場所.

``api.apply`` / ``api.run_pipeline`` / ``api.explain_device`` / MCP(``fullseye_describe``)はここだけを呼ぶ。
GPU の台帳(手書き経路の表、許可リスト、native の実測)を読むのもここだけ。台帳を将来
``fullseye/data/GPU_CATALOG.json``(1 op 1 行)に一本化するときは :func:`_load_sources` を差し替える。

経路の種類 ``kind``:

* ``"accel"``  — 手書きの torch 経路(``accel.ACCEL`` / ``accel_vol.VOL_ACCEL`` / ``accel_match.MATCH_ACCEL``)。
  parity の門(内部差 < 5e-3)を通ったものだけが表に載る。場面は ``single``。ただし実測の台帳
  ``fullseye/data/GPU_ACCEL_USE.json``(領域の解析の族、生成 ``tools/bench_label_ops.py``)で
  ``use="pipeline"``(単独は 5 倍に届かず、常駐で 1 倍以上)の op は ``pipeline``(隣も GPU の段のときだけ)。
* ``"native"`` — op の関数自身が ``device=`` 引数を持つ torch 実装(``match3d`` / ``feat_*`` / ``fuse3d``)。
  **実測があり、一致し(``ok``)、CPU より速い(倍率 >= 1)ものだけ**を返す(実測の無い op は返さない =
  fail-closed)。実測は任意の台帳 ``fullseye/data/GPU_NATIVE.json``(無ければ native は 1 件も返らない)。
* ``"shadow"`` — :mod:`gpu_shadow` の機械的経路(CuPy)。許可リストを写した ``DEVICE_RULES.json`` の
  ``shadow``(生成 ``tools/gen_device_rules.py``)。

使える場面 ``use``: ``"single"``(単独の呼び出し)/ ``"resident"``(GPU に載せたままの連続処理で 5 倍以上)/
``"pipeline"``(常駐で 1〜5 倍)。``context="single"`` は ``use="single"`` の経路だけ、``context="pipeline"``
は全部を候補にする。

優先順位(複数の経路を持つ op。規則はここ :func:`_best` だけに書く):

1. 一致している(parity を通った)経路だけを候補にする。accel は表に載ること自体が一致の証明、
   native は実測の ``ok``、shadow は許可リスト(全画素照合を通ったもの)。
2. 実寸の倍率(転送込み)が分かる候補どうしは倍率の高い方。
3. 倍率の分からない accel(損益分岐は ``DEVICE_RULES.json`` の ``ops`` で大きさごとに測ってあるが、
   実寸 1 点の倍率は無い)は、倍率の分かる候補より優先する。手書き経路は台帳の GPU 欄・損益分岐・
   before/after の全部が前提にしている経路で、ここで別の道に替えると測った規則が当てはまらなくなる。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

_HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE_PATH = os.path.join(_HERE, "fullseye", "data", "GPU_NATIVE.json")
ACCEL_USE_PATH = os.path.join(_HERE, "fullseye", "data", "GPU_ACCEL_USE.json")

KINDS = ("accel", "native", "shadow")
USES = ("single", "resident", "pipeline")
_SHADOW_USE = {"ops": "single", "resident_ops": "resident", "pipeline_ops": "pipeline"}


@dataclass(frozen=True)
class Route:
    """1 op の GPU 経路 1 本。"""

    op: str
    kind: str                      # "accel" | "native" | "shadow"
    use: str                       # "single" | "resident" | "pipeline"
    ratio: float | None = None     # 実寸の倍率(転送込み、CPU 時間 / GPU 時間)。分からなければ None
    min_elements: int | None = None    # 倍率を測った入力の要素数(auto はこれ以上でだけ選ぶ)
    measured_shape: str | None = None
    source: str = ""               # どの台帳から来たか
    extra: dict = field(default_factory=dict, compare=False)

    @property
    def path(self) -> str:
        """``api.explain_device`` の経路名(``accel`` / ``native`` / ``allow_single`` / ``allow_resident`` / ``allow_pipeline``)。"""
        if self.kind == "shadow":
            return "allow_" + self.use
        return self.kind

    def as_dict(self) -> dict:
        return {"op": self.op, "kind": self.kind, "use": self.use, "path": self.path, "ratio": self.ratio,
                "min_elements": self.min_elements, "measured_shape": self.measured_shape, "source": self.source}


# ---- 台帳(ここでだけ読む) -------------------------------------------------------------------
_CACHE: dict = {}


def _accel_names() -> frozenset:
    if "accel" not in _CACHE:
        try:
            import accel_bridge as bridge
            names = frozenset(bridge._C2A) | frozenset(bridge._C2VA) | frozenset(bridge._C2M)
        except ImportError:
            names = frozenset()
        _CACHE["accel"] = names
    return _CACHE["accel"]


def _shadow_rows() -> dict:
    if "shadow" not in _CACHE:
        import device_policy
        table = device_policy.load_rules()
        _CACHE["shadow"] = dict((table or {}).get("shadow", {}).get("ops", {}))
    return _CACHE["shadow"]


def _native_rows() -> dict:
    """``{op: row}`` 実測の行(``tools/bench_device_ops.py`` の ``summary.json`` と同じ形)。無ければ空。"""
    if "native" not in _CACHE:
        rows: dict = {}
        try:
            with open(NATIVE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("rows"), dict):
                data = data["rows"]                    # 見出し(generated_by / method / gate)つきの形
            items = data.values() if isinstance(data, dict) else data
            for row in items:
                if isinstance(row, dict) and row.get("name"):
                    rows[row["name"]] = row
        except (OSError, ValueError):
            rows = {}
        _CACHE["native"] = rows
    return _CACHE["native"]


def _accel_use_rows() -> dict:
    """``{op: row}`` 手書き経路の場面の台帳(領域の解析の族)。無ければ空 = 全部 ``single``。"""
    if "accel_use" not in _CACHE:
        rows: dict = {}
        try:
            with open(ACCEL_USE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            rows = {k: v for k, v in (data.get("ops") or {}).items() if isinstance(v, dict)}
        except (OSError, ValueError, AttributeError):
            rows = {}
        _CACHE["accel_use"] = rows
    return _CACHE["accel_use"]


def _load_sources(op: str) -> list:
    """*op* の経路の候補を全部(一致・速さの判定前)。台帳を差し替えるならここ。"""
    out = []
    if op in _accel_names():
        row = _accel_use_rows().get(op) or {}
        use = "pipeline" if row.get("use") == "pipeline" else "single"
        extra = {k: row[k] for k in ("ratio_single", "ratio_resident") if row.get(k) is not None}
        out.append(Route(op, "accel", use,
                         source="GPU_ACCEL_USE.json" if row else "accel", extra=extra))
    row = _native_rows().get(op)
    if row is not None:
        ok = bool(row.get("ok")) and row.get("status", "measured") == "measured"
        # 出力が定数の測定は一致の証明にならない(判定不能)。他の経路と同じ門で除く
        nonconst = row.get("nonconst", True) is not False
        ratio = row.get("ratio")
        if ok and nonconst and isinstance(ratio, (int, float)) and ratio >= 1.0:
            # 単独の採用は 5 倍以上(掃引・許可リストと同じ門)、1〜5 倍はパイプラインの中だけ
            use = "single" if ratio >= 5.0 else "pipeline"
            out.append(Route(op, "native", use, ratio=round(float(ratio), 3),
                             min_elements=row.get("elems"), source="GPU_NATIVE.json"))
    row = _shadow_rows().get(op)
    if row is not None:
        out.append(Route(op, "shadow", _SHADOW_USE.get(row.get("list"), "single"), ratio=row.get("ratio"),
                         min_elements=row.get("min_elements"), measured_shape=row.get("measured_shape"),
                         source="gpu_auto_allow.json",
                         extra={"ratio_single": row["ratio_single"]} if "ratio_single" in row else {}))
    return out


def _best(candidates: list):
    """優先順位(モジュールの説明 1〜3)を 1 か所で。"""
    if not candidates:
        return None
    accel = [r for r in candidates if r.kind == "accel" and r.ratio is None]
    if accel:
        return accel[0]
    return max(candidates, key=lambda r: (r.ratio is not None, r.ratio or 0.0))


# ---- 公開 ---------------------------------------------------------------------------------
def routes(op_name: str) -> list:
    """*op_name* の一致した経路の全部(場面を問わない)。"""
    return _load_sources(op_name) if isinstance(op_name, str) else []


def route(op_name: str, context: str = "single"):
    """*op_name* を *context*(``"single"`` / ``"pipeline"``)で走らせるときの主な GPU 経路。無ければ ``None``。

    ``"single"`` は ``use == "single"`` の経路だけを候補にする(常駐の枠は単独呼びでは使わない)。
    ``"pipeline"`` は全部を候補にする(常駐・鎖の枠は、隣の段も GPU に載るときだけ使う —— その判定は
    呼ぶ側 ``device_policy.plan_paths`` が段の並びで行う)。
    """
    if context not in ("single", "pipeline"):
        raise ValueError("context must be 'single' or 'pipeline'; got %r" % (context,))
    cands = routes(op_name)
    if context == "single":
        cands = [r for r in cands if r.use == "single"]
    return _best(cands)


def accelerated_names() -> frozenset:
    """手書きの GPU 経路(accel)を持つ op 名の集合(損益分岐の表を引く ``device_policy.route`` が使う)。"""
    return _accel_names()


def runnable(r) -> bool:
    """この経路をこの機械で今走らせられるか(CuPy の有無など)。走らせられないときは CPU で続く。

    accel は torch 側の判定(``api.cuda_available``)を呼ぶ側が先に済ませている。native は
    ``apply`` / ``run_pipeline`` からの実行をまだ繋いでいない(native の op は今は登録簿の外)ので False。
    """
    if r is None:
        return False
    if r.kind == "accel":
        return True
    if r.kind == "shadow":
        if "shadow_usable" not in _CACHE:
            try:
                import gpu_shadow
                _CACHE["shadow_usable"] = bool(gpu_shadow.available())
            except Exception:  # noqa: BLE001 - CuPy の欠如・壊れは「使えない」
                _CACHE["shadow_usable"] = False
        return _CACHE["shadow_usable"]
    return False


def run_single(r, op_name: str, v, a: float, b: float):
    """経路 *r* で 1 op を走らせる(shadow のみ。accel は ``api._try_accel`` が持つ)。"""
    if r is None or r.kind != "shadow":
        raise ValueError("run_single only runs shadow routes; got %r" % (r,))
    import gpu_shadow
    return gpu_shadow.run_allowed(op_name, v, a, b)


def run_chain(stages, imgs):
    """連続する shadow の段を GPU に載せたまま走らせる(``accel_bridge`` の shadow 区間)。"""
    import gpu_shadow
    return gpu_shadow.run_chain(stages, imgs)


def describe(op_name: str) -> dict:
    """AI が事前に選ぶための要約(``fullseye_describe`` の ``gpu_paths``)。

    ``accel`` = 手書き経路の有無、``kinds`` = 一致した経路の path、``primary`` = 単独呼びの主な経路、
    ``routes`` = 全経路(種類・場面・倍率・測った形)、``auto_gpu_min_pixels`` = ``device="auto"`` が
    単独呼びで GPU を選び始める大きさ(``None`` = auto では選ばない)。
    """
    import device_policy
    rs = routes(op_name)
    primary = route(op_name, "single")
    shadow = next((r for r in rs if r.kind == "shadow"), None)
    if primary is None:
        auto_min = None
    elif primary.kind == "accel":
        table = device_policy.load_rules()
        auto_min = (device_policy._op_threshold(table, op_name, 1) or 0) if table else 0
    elif primary.kind == "shadow":
        auto_min = primary.min_elements
    else:
        auto_min = None                      # native は apply からまだ走らない
    return {"accel": any(r.kind == "accel" for r in rs), "kinds": [r.path for r in rs],
            "primary": primary.path if primary else None,
            "allow_list": {"single": "ops", "resident": "resident_ops", "pipeline": "pipeline_ops"}[shadow.use]
            if shadow else None,
            "ratio": primary.ratio if primary else (shadow.ratio if shadow else None),
            "measured_shape": shadow.measured_shape if shadow else None,
            "auto_gpu_min_pixels": auto_min,
            "routes": [r.as_dict() for r in rs]}


def rejection(op_name: str):
    """GPU 経路が無い理由の根拠(台帳で測って不採用になった理由)。測っていない op は ``None``。

    ``accel:<理由>``(``GPU_ACCEL_USE.json`` の ``rejected``: ``mismatch`` / ``constant_output`` /
    ``slower_than_cpu_even_resident``)/ ``native:<理由>``(``GPU_NATIVE.json``: ``mismatch`` / ``constant_output``
    / ``slower`` / 測定の状態 ``timeout`` など)。
    """
    if not isinstance(op_name, str):
        return None
    row = _accel_use_rows().get(op_name)
    if row and not row.get("use") and row.get("rejected"):
        return "accel:" + str(row["rejected"])
    n = _native_rows().get(op_name)
    if n is not None:
        status = n.get("status", "measured")
        if status != "measured":
            return "native:" + str(status)
        if not n.get("ok"):
            return "native:mismatch"
        if n.get("nonconst") is False:
            return "native:constant_output"
        ratio = n.get("ratio")
        if isinstance(ratio, (int, float)) and ratio < 1.0:
            return "native:slower"
    return None


def clear_cache() -> None:
    """台帳の読み込みをやり直す(テスト・台帳の差し替え用)。"""
    _CACHE.clear()
