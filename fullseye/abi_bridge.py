# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`fs_apply`(fullseye_abi.h)の python 経路 —— 埋め込み CPython から呼ばれる側。

C ABI の汎用入口 `fs_apply(op, inputs, params_json, ...)` は、ネイティブ実装の無い op を
ここへ回す。Rust 側(`rust/fullseye_core/src/embed.rs`)がハンドルの中身を**コピー**して
辞書に詰め、この :func:`apply` を 1 回呼び、返った辞書からハンドルを作り直す。

設計の要点(memory `project_fullseye_multilang_abi_program` 第 3 期):

- **パラメータの検証と既定値の解決はここ 1 か所。** Rust 側は JSON の構文(RFC 8259)しか
  見ない。検証器は MCP サーバの :func:`fullseye.mcp.server._validate` をそのまま使う
  (fail-closed: 知らないキー / 型違い / 範囲外 / NaN はすべて理由つきで拒否)。
- **来歴を必ず返す。** どの実装(backend)が走ったか、劣化台帳に何が載ったか、失敗なら
  どの状態コードに写すか。黙って代替値を返さない(契約 R-1)。
- **2 つの層。** 契約の 5 op(`fslib`、Rust にネイティブ実装がある = 差分の門)と、
  レジストリの ~900 op(`fullseye.apply`、つまみ a/b)。台帳 op(型つき引数、入力が点群や
  信号)は FsImage / FsRegion のハンドルでは運べないので**今回は対象外**(次段)。

境界を越える表現(Rust ↔ ここ)は全部 bytes と数値の辞書 —— numpy の crate に依存しない:

    image     {"kind": "image", "h", "w", "lo", "hi", "dtype", "pixels": bytes(float64, 行優先)}
    region    {"kind": "region", "h", "w", "runs": bytes(int32 × 3 = row, col_begin, col_end)}
    objectset {"kind": "objectset", "h", "w", "objects": [runs bytes, ...]}   # 契約の並び
    tuple     {"kind": "tuple", "values": [float, ...], "elem": [FS_ELEM_*, ...]}
"""
from __future__ import annotations

import inspect
import json
import traceback

import numpy as np

# --- fullseye_abi.h の値(ヘッダが正本。tests/test_abi_apply.py が照合する) ------------
FS_OK = 0
FS_E_INVALID_ARG = 1
FS_E_TYPE = 2
FS_E_SHAPE = 3
FS_E_RANGE = 4
FS_E_NO_BACKEND = 5
FS_E_UNSUPPORTED = 6
FS_E_OUT_OF_MEMORY = 7
FS_E_DEADLINE = 8
FS_E_INTERNAL = 9
FS_E_NO_PYTHON = 10
FS_E_UNKNOWN_OP = 11
FS_E_BAD_PARAMS = 12
FS_E_PY_EXCEPTION = 13

FS_KIND_NONE, FS_KIND_IMAGE, FS_KIND_REGION, FS_KIND_OBJECTSET, FS_KIND_TUPLE = 0, 1, 2, 3, 4
FS_DTYPE_F64 = 4
FS_ELEM_INT, FS_ELEM_REAL, FS_ELEM_STRING = 1, 2, 3

#: 契約の演算子(ヘッダの `@fslib` タグと同じ集合。テストが照合し、増減したら落ちる)。
#: Rust にネイティブ実装があるのはこの 5 つだけ —— `route_pref=1` と `2` で走らせて
#: 突き合わせるのが「道 3」の門になる。
CONTRACT_OPS = ("gauss", "threshold", "connection", "measure_all", "select_shape")

_SORT_OF_KIND = {"image": "image", "region": "region", "objectset": "objectset", "tuple": "seq"}


class _Refuse(Exception):
    """状態コードつきの拒否。:func:`apply` の返り値に写す(外へは投げない)。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------- #
# JSON → dict(RFC 8259。NaN / Infinity は JSON ではないので拒む)
# --------------------------------------------------------------------------- #
def _reject_constant(name: str):
    raise ValueError("%s は RFC 8259 の JSON ではない(数は有限でなければならない)" % name)


def parse_params(params_json: str | None) -> dict:
    """params_json をオブジェクトとして読む。`5` は int、`5.0` は float のまま
    (Python の json がそう区別する。型の違いは検証器と op にそのまま届く)。"""
    if params_json is None or params_json.strip() == "":
        return {}
    try:
        v = json.loads(params_json, parse_constant=_reject_constant)
    except ValueError as exc:
        raise _Refuse(FS_E_BAD_PARAMS, "params_json が JSON として読めない: %s" % exc) from exc
    if not isinstance(v, dict):
        raise _Refuse(FS_E_BAD_PARAMS,
                      "params_json はオブジェクト({...})でなければならない(%s)" % type(v).__name__)
    return v


# --------------------------------------------------------------------------- #
# パラメータの表(既定値・型・範囲の正本)
# --------------------------------------------------------------------------- #
_PY_TO_JSON = {float: "number", int: "integer", str: "string", bool: "boolean"}


def _contract_schema(name: str) -> dict:
    """`fslib.<name>` の署名から JSON スキーマを組む。先頭の引数は iconic 入力(ハンドル)
    なので除く。既定値の無い引数は required。"""
    import fslib
    fn = getattr(fslib, name)
    props: dict = {}
    required: list = []
    for i, (pname, p) in enumerate(inspect.signature(fn, eval_str=True).parameters.items()):
        if i == 0:
            continue
        ann = p.annotation
        t = _PY_TO_JSON.get(ann, "number")
        spec = {"type": t}
        if t == "string":
            spec["maxLength"] = 64
        if p.default is inspect.Parameter.empty:
            required.append(pname)
        else:
            spec["default"] = p.default
        props[pname] = spec
    return {"type": "object", "properties": props, "required": required,
            "additionalProperties": False}


def _registry_schema() -> dict:
    """レジストリ op のつまみ。MCP の `fullseye_apply` の宣言から **a / b / allow_degraded を
    そのまま**借りる(検証器も同じ)。既定は a = b = 0.5、allow_degraded = False。"""
    from .mcp.server import TOOLS
    src = TOOLS["fullseye_apply"]["inputSchema"]["properties"]
    props = {k: dict(src[k]) for k in ("a", "b", "allow_degraded")}
    props["a"]["default"] = 0.5
    props["b"]["default"] = 0.5
    props["allow_degraded"]["default"] = False
    return {"type": "object", "properties": props, "required": [],
            "additionalProperties": False}


def _resolve(name: str):
    """op 名 → ("contract", fslib 関数) | ("registry", ops.Op)。無ければ FS_E_UNKNOWN_OP。"""
    if name in CONTRACT_OPS:
        import fslib
        return "contract", getattr(fslib, name)
    import ops
    op = ops._BY_NAME.get(name)
    if op is not None:
        return "registry", op
    try:
        from .mcp.catalog import Catalog
        near = Catalog.load(with_facade=False).nearest(name)
    except Exception:                                            # noqa: BLE001
        near = []
    raise _Refuse(FS_E_UNKNOWN_OP,
                  "op %r は契約(%d)にもレジストリにも無い。近い名前: %s"
                  % (name, len(CONTRACT_OPS), near))


def validate(name: str, params_json: str | None) -> dict:
    """検証と既定値の解決(MCP の検証器)。返り値は op に渡す引数の辞書。"""
    from .mcp.server import ArgError, _validate
    tier, _ = _resolve(name)
    schema = _contract_schema(name) if tier == "contract" else _registry_schema()
    args = parse_params(params_json)
    try:
        _validate(schema, args)
    except ArgError as exc:
        raise _Refuse(FS_E_BAD_PARAMS, "op %r: %s" % (name, exc)) from exc
    out = {}
    for k, spec in schema["properties"].items():
        if k in args:
            out[k] = args[k]
        elif "default" in spec:
            out[k] = spec["default"]
    return out


def _note(args: dict) -> str:
    """成功時の message: 解決後のパラメータを Python が見た型つきで(`5` と `5.0` の
    違いが ABI 越しに観測できる)。"""
    return "params: " + ", ".join("%s=%r(%s)" % (k, v, type(v).__name__)
                                  for k, v in args.items()) if args else "params: (none)"


# --------------------------------------------------------------------------- #
# ハンドル表現 ↔ fslib / numpy
# --------------------------------------------------------------------------- #
def _runs_to_mask(h: int, w: int, runs: np.ndarray) -> np.ndarray:
    m = np.zeros(h * w + 1, dtype=np.int32)
    if runs.size:
        np.add.at(m, runs[:, 0] * w + runs[:, 1], 1)
        np.add.at(m, runs[:, 0] * w + runs[:, 2], -1)
    return (np.cumsum(m[:-1]) > 0).reshape(h, w)


def _runs_of(d: dict) -> np.ndarray:
    return np.frombuffer(d["runs"], dtype=np.int32).reshape(-1, 3)


def _to_fslib(d: dict):
    import fslib
    kind = d.get("kind")
    if kind == "image":
        px = np.frombuffer(d["pixels"], dtype=np.float64).reshape(d["h"], d["w"]).copy()
        return fslib.FImage(px, value_range=(float(d["lo"]), float(d["hi"])))
    if kind == "region":
        return fslib.Region(_runs_to_mask(d["h"], d["w"], _runs_of(d)))
    if kind == "objectset":
        h, w = d["h"], d["w"]
        labels = np.zeros((h, w), dtype=np.int32)
        for i, rb in enumerate(d["objects"], 1):
            runs = np.frombuffer(rb, dtype=np.int32).reshape(-1, 3)
            labels[_runs_to_mask(h, w, runs)] = i
        return fslib.ObjectSet(labels, np.arange(1, len(d["objects"]) + 1, dtype=np.int32))
    if kind == "tuple":
        return fslib.Seq.of(d["values"])
    raise _Refuse(FS_E_TYPE, "入力ハンドルの kind %r は扱えない" % (kind,))


def _image_dict(px: np.ndarray, lo: float, hi: float) -> dict:
    a = np.ascontiguousarray(px, dtype=np.float64)
    return {"kind": "image", "h": int(a.shape[0]), "w": int(a.shape[1]),
            "lo": float(lo), "hi": float(hi), "dtype": FS_DTYPE_F64, "pixels": a.tobytes()}


def _region_dict(mask: np.ndarray) -> dict:
    import fslib
    reg = mask if isinstance(mask, fslib.Region) else fslib.Region(np.asarray(mask) > 0.5)
    runs = np.ascontiguousarray(reg.runs(), dtype=np.int32)
    return {"kind": "region", "h": int(reg.shape[0]), "w": int(reg.shape[1]),
            "runs": runs.tobytes()}


def _objectset_dict(objs) -> dict:
    h, w = objs.labels.shape
    return {"kind": "objectset", "h": int(h), "w": int(w),
            "objects": [np.ascontiguousarray(objs.region(i).runs(), dtype=np.int32).tobytes()
                        for i in range(len(objs))]}


def _tuple_dict(values) -> dict:
    v = [float(x) for x in np.asarray(values, dtype=np.float64).ravel()]
    return {"kind": "tuple", "values": v, "elem": [FS_ELEM_REAL] * len(v)}


def _from_fslib(v) -> dict:
    import fslib
    if isinstance(v, fslib.FImage):
        return _image_dict(v.pixels, *v.value_range)
    if isinstance(v, fslib.Region):
        return _region_dict(v)
    if isinstance(v, fslib.ObjectSet):
        return _objectset_dict(v)
    if isinstance(v, (np.ndarray, fslib.Seq)):
        return _tuple_dict(v.values() if isinstance(v, fslib.Seq) else v)
    raise _Refuse(FS_E_UNSUPPORTED, "返り値 %s は ABI のハンドルに写せない" % type(v).__name__)


# --------------------------------------------------------------------------- #
# 例外 → 状態コード
# --------------------------------------------------------------------------- #
def _code_of(exc: Exception) -> int:
    import fslib
    if isinstance(exc, fslib.FsBackendError):
        return FS_E_NO_BACKEND
    if isinstance(exc, fslib.FsValueError):
        return FS_E_INVALID_ARG
    if isinstance(exc, fslib.FsTypeError):
        return FS_E_TYPE
    if isinstance(exc, ImportError):
        return FS_E_NO_BACKEND
    if isinstance(exc, MemoryError):
        return FS_E_OUT_OF_MEMORY
    if isinstance(exc, ValueError):
        return FS_E_INVALID_ARG
    if isinstance(exc, TypeError):
        return FS_E_TYPE
    return FS_E_PY_EXCEPTION


def _exc_text(exc: Exception) -> str:
    return "%s: %s" % (type(exc).__name__, str(exc)[:400])


# --------------------------------------------------------------------------- #
# 2 つの層の実行
# --------------------------------------------------------------------------- #
def _run_contract(name: str, fn, inputs: list, args: dict) -> tuple[list, str, list]:
    import fslib
    if len(inputs) != 1:
        raise _Refuse(FS_E_INVALID_ARG, "%s は入力ハンドル 1 つを取る(%d 個)" % (name, len(inputs)))
    x = _to_fslib(inputs[0])
    # どの backend が走るかは profile が決める(fslib の dispatch と同じ表を引く)
    probe = "measure_all" if name == "select_shape" else name
    backend = fslib.readiness_report([probe], fslib.current_profile()).get(probe) or "?"
    try:
        out = fn(x, **args)
    except Exception as exc:                                     # noqa: BLE001
        raise _Refuse(_code_of(exc), _exc_text(exc)) from exc
    outs = list(out) if isinstance(out, tuple) else [out]
    return [_from_fslib(o) for o in outs], backend, []


def _run_registry(name: str, op, inputs: list, args: dict) -> tuple[list, str, list]:
    import backend_safe
    import fullseye
    import ops
    if len(inputs) != 1:
        raise _Refuse(FS_E_INVALID_ARG, "%s は入力ハンドル 1 つを取る(%d 個)" % (name, len(inputs)))
    d = inputs[0]
    kind = d.get("kind")
    if kind == "image":
        px = np.frombuffer(d["pixels"], dtype=np.float64).reshape(d["h"], d["w"])
        lo, hi = float(d["lo"]), float(d["hi"])
        # レジストリの契約は [0,1] の float64。画像が名乗る値域(R-3)で写す ——
        # 値域 (0,1) なら (px - 0) / 1 で**ビットまで同じ**。
        arr = (px - lo) / (hi - lo) if (lo, hi) != (0.0, 1.0) else px.copy()
        cur = "image"
    elif kind == "region":
        arr = _runs_to_mask(d["h"], d["w"], _runs_of(d)).astype(np.float64)
        cur = "region"
    else:
        raise _Refuse(FS_E_TYPE, "レジストリ op の入力は image か region のハンドル(%r)" % (kind,))
    if op.in_sort not in ("any", cur):
        # MCP の `_check_sort` と同じ立場: 型の不一致は走らせない
        if op.in_sort not in ("image", "region"):
            raise _Refuse(FS_E_UNSUPPORTED,
                          "%s の入力は %s —— ABI のハンドル(image / region)では運べない"
                          % (name, op.in_sort))
        raise _Refuse(FS_E_TYPE, "型の不一致: %s は %s を受けるが、ハンドルは %s"
                      % (name, op.in_sort, cur))
    allow = bool(args.get("allow_degraded", False))
    mark = backend_safe.mark()
    try:
        out = fullseye.apply(arr, name, args["a"], args["b"],
                             on_error=("fallback" if allow else "raise"))
    except Exception as exc:                                     # noqa: BLE001
        raise _Refuse(_code_of(exc), _exc_text(exc)) from exc
    degraded = ["%s@%s: %s" % (e["name"], e["source"], e["error"][:120])
                for e in backend_safe.events_since(mark)]
    inner = getattr(op.fn, "__wrapped__", op.fn)
    backend = getattr(inner, "__module__", None) or "?"
    sort = op.out_sort
    if sort in ("image", "any"):
        if not isinstance(out, np.ndarray) or out.ndim != 2:
            raise _Refuse(FS_E_UNSUPPORTED, "%s の出力 %s は 2-D 画像ではない" % (
                name, getattr(out, "shape", type(out).__name__)))
        if name in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT:
            # 値域は取得層が宣言するもの(R-3)。この op の出力は [0,1] ではなく
            # 物理量で、宣言できる値域を op が持たない —— 画素から推定して名乗るのは
            # 黙った代替値になるので拒む。
            raise _Refuse(FS_E_UNSUPPORTED,
                          "%s の出力の値域は [0,1] ではない(ops.UNIT_RANGE_IS_NOT_THE_CONTRACT)"
                          "ので FsImage の値域を宣言できない" % name)
        return [_image_dict(out, 0.0, 1.0)], backend, degraded
    if sort == "region":
        if not isinstance(out, np.ndarray) or out.ndim != 2:
            raise _Refuse(FS_E_UNSUPPORTED, "%s の出力 %s は 2-D の region ではない" % (
                name, getattr(out, "shape", type(out).__name__)))
        return [_region_dict(out)], backend, degraded
    if sort == "feature":
        try:
            val = float(out)
        except (TypeError, ValueError) as exc:
            raise _Refuse(FS_E_UNSUPPORTED, "%s の出力 %s はスカラーではない"
                          % (name, type(out).__name__)) from exc
        return [_tuple_dict([val])], backend, degraded
    raise _Refuse(FS_E_UNSUPPORTED,
                  "%s の出力の種別 %s は ABI のハンドル(image / region / tuple)に写せない"
                  % (name, sort))


def apply(op: str, inputs: list, params_json: str | None) -> dict:
    """`fs_apply` の python 経路の本体。**例外を外へ出さない** —— 返り値の辞書で状態を返す。

    返り値: ``{"status", "message", "backend", "degraded": [..], "outputs": [dict..]}``。
    ``status != 0`` なら ``outputs`` は空で ``message`` に理由。成功なら ``message`` に
    解決後のパラメータ(型つき)。
    """
    try:
        tier, target = _resolve(op)
        args = validate(op, params_json)
        if tier == "contract":
            outs, backend, degraded = _run_contract(op, target, inputs, args)
        else:
            outs, backend, degraded = _run_registry(op, target, inputs, args)
        return {"status": FS_OK, "message": _note(args), "backend": backend,
                "degraded": degraded, "outputs": outs, "tier": tier}
    except _Refuse as r:
        return {"status": r.code, "message": str(r), "backend": "", "degraded": [],
                "outputs": []}
    except Exception as exc:                                     # noqa: BLE001
        return {"status": FS_E_PY_EXCEPTION,
                "message": "%s\n%s" % (_exc_text(exc), traceback.format_exc()[-1200:]),
                "backend": "", "degraded": [], "outputs": []}


# --------------------------------------------------------------------------- #
# カタログ
# --------------------------------------------------------------------------- #
_KIND_OF_ANN = {"FImage": "image", "Region": "region", "ObjectSet": "objectset"}


def _param_rows(schema: dict) -> list:
    rows = []
    for k, spec in schema["properties"].items():
        row = {"name": k, "type": spec["type"], "required": k in schema["required"]}
        for key in ("default", "minimum", "maximum", "maxLength"):
            if key in spec:
                row[key] = spec[key]
        rows.append(row)
    return rows


def catalog() -> dict:
    """`fs_catalog_json` の中身。op 名・層・経路・入出力の kind・引数の型/既定値。"""
    import fslib
    import ops
    entries = []
    for name in CONTRACT_OPS:
        # `from __future__ import annotations` の下では注釈が文字列になる —— eval_str で
        # 型そのものに戻す(最初これを忘れ、`feature: str` が「数」として検証されていた)。
        sig = inspect.signature(getattr(fslib, name), eval_str=True)
        first = next(iter(sig.parameters.values()))
        ann = getattr(first.annotation, "__name__", str(first.annotation))
        ret = sig.return_annotation
        ret_name = getattr(ret, "__name__", str(ret))
        outs = ["tuple", "tuple", "tuple"] if name == "measure_all" else [_KIND_OF_ANN.get(ret_name, "?")]
        entries.append({"name": name, "tier": "contract", "routes": ["native", "python"],
                        "inputs": [_KIND_OF_ANN.get(ann, "?")], "outputs": outs,
                        "params": _param_rows(_contract_schema(name)),
                        "backends": fslib.backends_for(name) or None})
    reg_schema = _registry_schema()
    rows = _param_rows(reg_schema)
    for op in ops.REGISTRY:
        out_kind = {"image": "image", "any": "image", "region": "region", "feature": "tuple"}.get(op.out_sort)
        entries.append({"name": op.name, "tier": "registry", "routes": ["python"],
                        "inputs": [op.in_sort], "outputs": [out_kind] if out_kind else [],
                        "abi_callable": op.in_sort in ("image", "region", "any") and out_kind is not None
                        and op.name not in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT,
                        "params": rows, "halcon": op.halcon, "category": op.category})
    return {"abi": {"major": 0, "minor": 1}, "n_ops": len(entries),
            "n_native": len(CONTRACT_OPS), "ops": entries}


def catalog_json() -> str:
    return json.dumps(catalog(), ensure_ascii=False)
