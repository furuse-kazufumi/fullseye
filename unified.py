"""Fullseye 統一インターフェース — 単一 registry + introspection メタ + 章別名前空間.

要件定義 docs/UNIFIED_API_REQUIREMENTS.md の F1(統一呼び出し)/ F2(統一発見)/
F3(introspection・メタ・描画ヒント)を、本セッションで実装した 600 の HALCON facade op
(data/halcon_facade_map.json)に対して additive に実現する層。既存 op・進化 registry・
fullseye パッケージ facade を一切変更しない(F7 後方互換)。

  import unified as u
  # F2 発見: 層を跨いだ単一 registry で列挙・検索
  u.ops.find("circle")                 # 名前/doc/章の全文検索
  u.ops.list(namespace="contour")      # 名前空間で絞り込み
  u.ops.describe("gen_circle_contour_xld")   # F3 メタ(params/doc/章/描画ヒント/provenance)
  # F1 自然呼び出し: 章別名前空間 + 自然シグネチャ(進化用 a/b は露出しない)
  c = u.contour.gen_circle_contour_xld(row=50, col=50, radius=10)
  K = u.calib.camera_calibration(obj_pts, image_pts_list)

各 op のシグネチャは実装関数そのものの自然な名前付き引数(inspect で取得)。
描画ヒント(render_hint)は Studio(F6)が 2D/3D 描画を自動選択するためのメタ。
"""
from __future__ import annotations

import inspect as _inspect
import json
import os
from dataclasses import dataclass, field
from typing import Callable

_HERE = os.path.dirname(os.path.abspath(__file__))
_FACADE = os.path.join(_HERE, "data", "halcon_facade_map.json")
_STUBS = os.path.join(_HERE, "data", "halcon_stubs.json")

# HALCON chapter → fullseye 名前空間(短く自然な語彙)。off-mission は無視。
_CHAPTER_NS = {
    "Calibration": "calib",
    "3D Reconstruction": "recon3d",
    "3D Object Model": "object3d",
    "3D Matching": "match3d",
    "Contours": "contour", "XLD": "contour",
    "Filters": "filter",
    "Image": "image",
    "Regions": "region",
    "Morphology": "morph",
    "Matching": "match",
    "Transformations": "transform",
    "Segmentation": "segment",
    "Tools": "tools",
    "1D Measuring": "measure",
    "2D Metrology": "metrology",
    "Inspection": "inspection",
    "Matrix": "matrix",
}
# 描画ヒント(F3→F6): 名前空間 → Studio 既定の可視化種別
_NS_RENDER = {
    "contour": "contour", "region": "region", "morph": "region", "segment": "region",
    "image": "image", "filter": "image",
    "calib": "pose", "transform": "pose",
    "recon3d": "point_cloud", "object3d": "point_cloud", "match3d": "pose",
    "match": "matches", "measure": "scalar", "metrology": "contour",
    "inspection": "image", "tools": "image", "matrix": "matrix",
}
# 名前パターンによる描画ヒントの上書き(章より具体的)
_NAME_RENDER = [
    ("_xld", "contour"), ("contour", "contour"),
    ("region", "region"), ("_pose", "pose"), ("pose_", "pose"),
    ("point_3d", "point_cloud"), ("object_model_3d", "point_cloud"),
    ("disparity", "image"), ("depth", "image"), ("hom_mat", "matrix"),
    ("histo", "scalar"), ("distance", "scalar"), ("feature", "scalar"),
]
# off-mission 章(名前空間割り当てで無視して次善の章を採る)
_OFF = {"Graphics", "Tuple", "System", "Develop", "Control", "File", "Object",
        "Deep Learning", "OCR", "Classification", "Legacy", "Identification",
        "Image Source"}


@dataclass
class UnifiedOp:
    """1 つの視覚 op のメタ(F3)。callable でそのまま実行できる。"""
    name: str                          # HALCON operator 名(= fullseye での呼び名)
    func: Callable
    module: str                        # 実装モジュール.関数(provenance)
    chapter: str                       # 主 HALCON chapter
    namespace: str                     # fullseye 名前空間(fs.<namespace>)
    doc: str                           # 1 行説明
    render_hint: str                   # Studio 描画種別(image/region/contour/pose/point_cloud/matches/scalar/matrix)
    params: list = field(default_factory=list)   # [(name, default, kind), ...] 自然シグネチャ
    provenance: str = "facade"         # genuine numpy facade

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def signature(self) -> str:
        parts = []
        for nm, default, kind in self.params:
            parts.append(nm if default is _inspect.Parameter.empty else f"{nm}={default!r}")
        return f"{self.name}({', '.join(parts)})"

    def as_dict(self) -> dict:
        return {"name": self.name, "namespace": self.namespace, "chapter": self.chapter,
                "doc": self.doc, "render_hint": self.render_hint, "provenance": self.provenance,
                "module": self.module, "signature": self.signature(),
                "params": [{"name": n, "default": (None if d is _inspect.Parameter.empty else repr(d)),
                            "kind": k} for n, d, k in self.params]}

    def __repr__(self) -> str:
        return f"<UnifiedOp {self.namespace}.{self.name}  [{self.render_hint}]>"


def _pick_chapter(chapters) -> str:
    for ch in chapters:
        if ch not in _OFF and ch in _CHAPTER_NS:
            return ch
    for ch in chapters:
        if ch not in _OFF:
            return ch
    return chapters[0] if chapters else "Tools"


def _render_hint(namespace: str, name: str) -> str:
    for pat, hint in _NAME_RENDER:
        if pat in name:
            return hint
    return _NS_RENDER.get(namespace, "image")


def _params_of(func) -> list:
    try:
        sig = _inspect.signature(func)
    except (ValueError, TypeError):
        return []
    out = []
    for nm, p in sig.parameters.items():
        if p.kind in (_inspect.Parameter.VAR_POSITIONAL, _inspect.Parameter.VAR_KEYWORD):
            out.append((("*" + nm) if p.kind == _inspect.Parameter.VAR_POSITIONAL else ("**" + nm),
                        _inspect.Parameter.empty, "var"))
        else:
            out.append((nm, p.default, "arg"))
    return out


class Registry:
    """層を跨いだ単一 op 索引(F2)。名前で引く / 検索する / 名前空間で絞る / メタを返す。"""

    def __init__(self) -> None:
        self._ops: dict[str, UnifiedOp] = {}
        self._ns: dict[str, dict[str, UnifiedOp]] = {}

    def register(self, op: UnifiedOp) -> None:
        self._ops[op.name] = op
        self._ns.setdefault(op.namespace, {})[op.name] = op

    def __getitem__(self, name: str) -> UnifiedOp:
        return self._ops[name]

    def __contains__(self, name: str) -> bool:
        return name in self._ops

    def __len__(self) -> int:
        return len(self._ops)

    def get(self, name: str):
        return self._ops.get(name)

    def namespaces(self) -> list:
        return sorted(self._ns)

    def list(self, namespace: str = None, chapter: str = None) -> list:
        ops = self._ops.values()
        if namespace:
            ops = [o for o in ops if o.namespace == namespace]
        if chapter:
            ops = [o for o in ops if o.chapter == chapter]
        return sorted((o.name for o in ops))

    def find(self, query: str) -> list:
        """名前 / doc / 章 / 名前空間の全文部分一致で検索。"""
        q = query.lower()
        hits = [o for o in self._ops.values()
                if q in o.name.lower() or q in o.doc.lower()
                or q in o.chapter.lower() or q in o.namespace.lower()]
        return sorted(hits, key=lambda o: (o.namespace, o.name))

    def describe(self, name: str) -> dict:
        op = self._ops.get(name)
        return op.as_dict() if op else {}

    def stats(self) -> dict:
        by_ns = {ns: len(ops) for ns, ops in sorted(self._ns.items())}
        return {"total": len(self._ops), "namespaces": len(self._ns), "by_namespace": by_ns}


class _NS:
    """名前空間オブジェクト(F1): u.contour.gen_circle_contour_xld(...) で自然に呼べる。"""

    def __init__(self, name: str, ops: dict) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_ops", ops)

    def __getattr__(self, item):
        ops = object.__getattribute__(self, "_ops")
        if item in ops:
            return ops[item]
        raise AttributeError(f"fullseye '{self._name}' に op '{item}' は無い。"
                             f"候補: {', '.join(sorted(ops)[:8])} …")

    def __dir__(self):
        return sorted(object.__getattribute__(self, "_ops"))

    def __repr__(self) -> str:
        return f"<fullseye.{self._name}: {len(self._ops)} ops>"


def _import(ref: str) -> Callable:
    mod, _, fn = ref.rpartition(".")
    import importlib
    return getattr(importlib.import_module(mod), fn)


def build_registry() -> Registry:
    """facade マップ + stub メタから統一 registry を構築(F2/F3)。"""
    facade = json.load(open(_FACADE, encoding="utf-8"))
    facade = {k: v for k, v in facade.items() if not k.startswith("_")}
    stubs = json.load(open(_STUBS, encoding="utf-8"))["operators"]
    reg = Registry()
    for name, ref in facade.items():
        try:
            func = _import(ref)
        except Exception:
            continue
        meta = stubs.get(name, {})
        chapter = _pick_chapter(meta.get("chapters", []))
        namespace = _CHAPTER_NS.get(chapter, "tools")
        doc = (func.__doc__ or meta.get("short_desc", "") or "").strip().splitlines()
        doc = doc[0].strip() if doc else ""
        op = UnifiedOp(name=name, func=func, module=ref, chapter=chapter,
                       namespace=namespace, doc=doc,
                       render_hint=_render_hint(namespace, name), params=_params_of(func))
        reg.register(op)
    return reg


# ── モジュールロード時に registry を構築し、名前空間を公開(F1/F2)──────────────── #
ops = build_registry()

# 各名前空間を module 属性として公開: unified.contour, unified.calib, ...
_namespaces = {}
for _ns_name in ops.namespaces():
    _obj = _NS(_ns_name, {o: ops[o] for o in ops.list(namespace=_ns_name)})
    _namespaces[_ns_name] = _obj
    globals()[_ns_name] = _obj


def namespaces() -> dict:
    """{名前空間名: _NS} を返す(Studio/エージェントの列挙用)。"""
    return dict(_namespaces)


if __name__ == "__main__":
    print("== Fullseye 統一 I/F registry ==")
    st = ops.stats()
    print(f"総 op {st['total']} / 名前空間 {st['namespaces']}")
    for ns, n in st["by_namespace"].items():
        print(f"  fs.{ns:10} {n:3} ops   例: {', '.join(ops.list(namespace=ns)[:3])}")
    print("\n== F2 検索 例: 'circle' ==")
    for o in ops.find("circle")[:6]:
        print(" ", o, "->", o.doc[:48])
    print("\n== F3 メタ 例: gen_circle_contour_xld ==")
    import pprint
    pprint.pprint(ops.describe("gen_circle_contour_xld"))
