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

# 進化 registry(fs.REGISTRY, Op)の out_sort → render_hint
_SORT_RENDER = {"image": "image", "region": "region", "contour": "contour",
                "feature": "scalar", "match": "matches", "volume": "point_cloud",
                "color": "image", "any": "image"}
# 進化 op の category → 名前空間(自然語彙。facade 名前空間と一部共有=同種 op が集まる)
_CAT_NS = {
    "smoothing": "smooth", "edges": "edges", "features": "feature", "gray": "gray",
    "morphology": "morph", "region": "region", "segmentation": "segment",
    "texture": "texture", "frequency": "frequency", "restoration": "restore",
    "arithmetic": "arith", "color": "color", "rank": "rank", "geometry": "geometry",
    "contour": "contour", "xldgeom": "contour", "halcon_ext": "filter",
    "extra": "misc", "misc": "misc", "artificial-life": "misc", "augmentation": "augment",
}
# 知覚 facade モジュール名 → render_hint 既定(モジュール単位のドメイン)
_PERCEP_RENDER = {
    "stereo": "image", "camera": "pose", "pcseg": "point_cloud", "pointcloud": "point_cloud",
    "registration": "pose", "ppf": "pose", "terrain": "image", "locomotion": "scalar",
    "occupancy": "image", "grasp": "pose", "detect": "region", "features": "scalar",
    "flow": "image", "motion": "image", "odometry": "pose", "sceneflow": "image",
    "pose": "pose", "measure": "scalar", "mesh": "point_cloud", "meshrepair": "point_cloud",
    "render3d": "image", "volops": "image", "complexops": "image", "specops": "image",
    "deformreg": "image", "events": "image", "videops": "image", "raster": "image",
}
# 統一 registry に載せる知覚 facade モジュール(algo=off-mission / io 系 / stdlib は除外)
_PERCEP_MODULES = list(_PERCEP_RENDER)


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
        # bare 名は first-wins(facade を最初に登録=genuine を優先、既存挙動維持)
        self._ops.setdefault(op.name, op)
        # 名前空間内も first-wins(層跨ぎの同名衝突を安定化)
        self._ns.setdefault(op.namespace, {}).setdefault(op.name, op)

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
        by_prov = {}
        for o in self._ops.values():
            by_prov[o.provenance] = by_prov.get(o.provenance, 0) + 1
        return {"total": len(self._ops), "namespaces": len(self._ns),
                "by_namespace": by_ns, "by_provenance": by_prov}


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


def _load_facade(reg: Registry) -> None:
    """本セッションの 600 HALCON genuine facade op(provenance=facade)。"""
    facade = json.load(open(_FACADE, encoding="utf-8"))
    facade = {k: v for k, v in facade.items() if not k.startswith("_")}
    stubs = json.load(open(_STUBS, encoding="utf-8"))["operators"]
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
        reg.register(UnifiedOp(name=name, func=func, module=ref, chapter=chapter,
                               namespace=namespace, doc=doc, provenance="facade",
                               render_hint=_render_hint(namespace, name), params=_params_of(func)))


def _make_evolution_caller(fn):
    """進化 op(v,a,b)を自然な ``op(image)`` 呼び出しに包む(F1: 探索用ノブ a/b は自然
    シグネチャに露出しない)。a/b は keyword-only の escape hatch として残す(既定=中立 0.5、
    power user が ``op(image, a=0.2)`` で調整可=表現力は失わない)。"""
    def call(image, *, a: float = 0.5, b: float = 0.5):
        return fn(image, a, b)
    return call


def _load_evolution(reg: Registry) -> None:
    """進化 registry(fs.REGISTRY, 735 Op)を統一 registry へ(provenance=evolution)。
    F1 自然 API 化: 自然シグネチャは ``op(image)`` のみ(a/b は隠す)。長い尾へのアクセスは
    Image チェーン / この caller の keyword-only a/b で確保。"""
    try:
        import fullseye as fs
    except Exception:
        return
    for op in getattr(fs, "REGISTRY", []):
        namespace = _CAT_NS.get(op.category, "filter")
        doc = (op.fn.__doc__ or "").strip().splitlines()
        doc = doc[0].strip() if doc else f"{op.category} op(HALCON: {op.halcon or '-'})"
        # F1: 自然シグネチャは image のみ(探索ノブ a/b は非露出、keyword-only で調整可)
        params = [("image", _inspect.Parameter.empty, "arg")]
        reg.register(UnifiedOp(name=op.name, func=_make_evolution_caller(op.fn),
                               module=f"fs.apply({op.name!r})", chapter=op.category,
                               namespace=namespace, doc=doc, provenance="evolution",
                               render_hint=_SORT_RENDER.get(op.out_sort, "image"), params=params))


def _load_perception(reg: Registry) -> None:
    """知覚 facade モジュール(fs.stereo/pcseg/camera/…)の公開関数を統一 registry へ
    (provenance=perception)。自然シグネチャをそのまま introspection。"""
    try:
        import fullseye as fs
    except Exception:
        return
    for mod_name in _PERCEP_MODULES:
        mod = getattr(fs, mod_name, None)
        if mod is None:
            continue
        exported = getattr(mod, "__all__", None)
        names = exported if exported else [n for n in dir(mod) if not n.startswith("_")]
        for fn_name in names:
            fn = getattr(mod, fn_name, None)
            if not callable(fn) or _inspect.isclass(fn) or _inspect.ismodule(fn):
                continue
            if getattr(fn, "__module__", "") not in (mod_name, getattr(mod, "__name__", "")):
                continue                                   # 再エクスポートされた他モジュール由来は除く
            doc = (fn.__doc__ or "").strip().splitlines()
            doc = doc[0].strip() if doc else f"{mod_name} perception op"
            reg.register(UnifiedOp(name=fn_name, func=fn, module=f"fs.{mod_name}.{fn_name}",
                                   chapter=mod_name, namespace=mod_name, doc=doc,
                                   provenance="perception",
                                   render_hint=_PERCEP_RENDER.get(mod_name, "image"),
                                   params=_params_of(fn)))


def _load_oss(reg: Registry) -> None:
    """OSS アダプタ(F4: OpenCV/skimage を裏に、不在時 numpy フォールバック)を統一 registry へ
    (provenance=oss-adapter)。config オブジェクト class を登録し、backend をメタに記録。"""
    try:
        import oss_adapter as oss
    except Exception:
        return
    for ns, name, cls, hint in getattr(oss, "ADAPTERS", []):
        try:
            backend = cls().backend
        except Exception:
            backend = "?"
        doc = (cls.__doc__ or "").strip().splitlines()
        doc = (doc[0].strip() if doc else name) + f"  [backend={backend}]"
        params = []
        try:
            for pn, p in _inspect.signature(cls).parameters.items():
                params.append((pn, p.default, "arg"))
        except (ValueError, TypeError):
            pass
        reg.register(UnifiedOp(name=name, func=cls, module=f"oss_adapter.{ns}.{name}",
                               chapter=ns, namespace=ns, doc=doc, provenance="oss-adapter",
                               render_hint=hint, params=params))


def _load_sim(reg: Registry) -> None:
    """sim-source アダプタ(F4: 物理シミュが視覚 op に入力を供給)を統一 registry へ
    (provenance=sim-source, namespace=sim)。config class を登録し available をメタに記録。"""
    try:
        import sim_source as sim
    except Exception:
        return
    for ns, name, cls, hint in getattr(sim, "SOURCES", []):
        avail = "available" if getattr(cls, "available", False) else "scaffold"
        doc = (cls.__doc__ or "").strip().splitlines()
        doc = (doc[0].strip() if doc else name) + f"  [sim={cls.backend}, {avail}]"
        params = []
        try:
            for pn, p in _inspect.signature(cls).parameters.items():
                if pn not in ("a", "k", "args", "kwargs"):
                    params.append((pn, p.default, "arg"))
        except (ValueError, TypeError):
            pass
        reg.register(UnifiedOp(name=name, func=cls, module=f"sim_source.{name}",
                               chapter="sim-source", namespace=ns, doc=doc,
                               provenance="sim-source", render_hint=hint, params=params))


def _lazy_call(module, func):
    """build 時に重い依存(gsplat 等)を import しない遅延呼び出し。"""
    def _call(*a, **k):
        import importlib
        return getattr(importlib.import_module(module), func)(*a, **k)
    _call.__doc__ = f"lazy {module}.{func}"
    return _call


# 3DGS / SuGaR / メッシュ再生を統一 op に(provenance=3dgs, namespace=gsplat)。
# 実装は重い(gsplat/CUDA)ため遅延。func は importlib で初回呼び出し時に解決する。
_3DGS_OPS = [
    ("capture_orbit", "sim_source", "capture_orbit_scene",
     "sim シーンをオービット撮影し 3DGS データセット(transforms.json)化", "dataset"),
    ("train_3dgs", "gsplat_train_native", "train",
     "sim シーンを native gsplat で 3DGS 学習(高速)", "gaussians"),
    ("train_3dgs_densify", "gsplat_train_native", "train_densify",
     "densify + SH + antialiased つき 3DGS 学習(高品質)", "gaussians"),
    ("sugar_mesh", "gsplat_sugar", "extract_mesh",
     "3DGS を SuGaR 風に表面整列→Poisson でメッシュ抽出(真値 bbox 検証つき)", "mesh"),
    ("tsdf_mesh", "gsplat_sugar", "depth_tsdf_mesh",
     "sim 完全深度を TSDF 融合し清潔な watertight メッシュ化(GPU 不要・針無し)", "mesh"),
    ("animate_mesh", "sim_source", "launch_animation",
     "qpos 軌道で真値メッシュをアニメ再生(静的地形メッシュの合成も可)", "animation"),
    ("render_walk_gif", "world_render", "render_walk_gif",
     "walker を terrain 上に配置した運動学プレビューを headless で GIF 化(接触なし・"
     "motion/gait を可視化。物理歩行は walk_physics を使う)", "animation"),
    ("walk_physics", "walk_physics", "run_walk_physics",
     "go2 をトルク PD 制御＋閉ループバランス＋mj_step の本物の物理(重力・摩擦・接触・慣性)で"
     "ラフな height field 上を歩かせ、胴体が傾く様子を GIF＋テレメトリ化"
     "(自立/前進/傾きを実測、GPU不要)", "animation"),
    ("jump_physics", "walk_physics", "run_jump_physics",
     "go2 をしゃがみ→爆発伸展→弾道飛行(全足離地=接触0を実測)→着地させる本物の物理ジャンプを"
     "GIF＋高さテレメトリ化(跳躍高/滞空を実測、摩擦・重力込み、GPU不要)", "animation"),
    ("hurdle_physics", "walk_physics", "run_hurdle_physics",
     "go2 が助走→爆発跳躍で障害物(バリア)を越え向こう側へ着地する本物の物理の走幅跳を"
     "GIF＋軌道テレメトリ化(越えたか/自立かを実測、GPU不要)", "animation"),
    ("long_route", "walk_physics", "run_long_route",
     "go2 が粗さの変化する長い起伏地形を本物の物理で長距離(既定100m)歩き切る"
     "(距離/自立を実測、GPU不要)", "animation"),
    ("route_planning", "walk_physics", "run_route_planning",
     "go2 が障害物をレイキャストで先読みし候補方位をピラミッド探索(粗→細)で選び差動旋回で"
     "回避してゴール到達する本物の物理ナビ(俯瞰プラン付き、GPU不要)", "animation"),
    ("figure8", "walk_physics", "run_figure8",
     "差動旋回で 8 の字系の曲線を各サイズで描く旋回制御の練習/較正(俯瞰トラック、GPU不要)", "animation"),
    ("evis_perceive", "evis_fullseye_bridge", "perceive_evis_walk",
     "GPU学習evisのロールアウト(qpos npy)をFullseyeで知覚: RGB|深度|DVSの3面GIF"
     "(ego_body=でロボット視点=頭部搭載RGB/深度/DVSの4面)", "animation"),
    ("g1_perceive_real", "evis_fullseye_bridge", "perceive_g1_real",
     "G1実機センサ仕様で知覚: Livox Mid-360(頭頂360°/-7..+52°)BEV点群 + RealSense D435i"
     "(87°×58°, 0.3-6m帯)RGB/深度の4面GIF。obstacles=Trueで静的障害物注入(qpos再生は正直なまま)",
     "animation"),
    ("pseudo_lidar", "evis_fullseye_bridge", "pseudo_lidar_rays",
     "平面疑似LiDARスキャン(前方弧K本の正規化距離)。歩行方策G1VisionWalkの観測と同一ジオメトリ"
     "のnumpy parity — 方策が食べる入力をツールとして単体計算", "matrix"),
    ("g1_walk_policy", "g1_policy_bridge", "g1_walk_policy",
     "GPU学習済みG1歩行方策(brax ckpt)をWindowsのみで実行: numpy推論(brax数値一致検証済)"
     "+ネイティブMuJoCoロールアウト→距離/生存/横ずれRMS実測+追従カメラ動画。"
     "vision=Trueで疑似LiDAR+障害物。段階API=G1PolicySession", "animation"),
    ("g1_training_curves", "g1_policy_bridge", "training_curves",
     "G1学習ログの進捗行(step/reward/ep_len/perr/crash…)を配列辞書へパース — "
     "GPU機に触れず学習曲線をStudioでプロット", "matrix"),
    ("pick_gif", "pick_render", "render_pick_gif",
     "ロボットアーム(Panda)が実接触・摩擦でキューブを把持し別位置へ設置する pick-and-place を "
     "headless で GIF 化(GPU不要・把持成否は箱の実測高さで判定)", "animation"),
    ("sensor_fusion", "sensor_fusion", "run_fusion_demo",
     "位置センサ(カメラ/GPS)と速度センサ(IMU)を Kalman フィルタで融合し投射体を追跡。"
     "融合 RMSE を各センサ単体と正直に比較した図を生成(GPU不要)", "image"),
    ("bin_pick_gif", "bin_pick", "render_bin_pick_gif",
     "バラ積みされた部品を候補スコアリングで選び 6DoF IK で上面把持し bin から取り出す "
     "bin-picking を headless で GIF 化(GPU不要・成功数は部品が bin を出たかで実測)", "animation"),
    ("lidar_scan", "lidar_sim", "run_lidar_demo",
     "スピニング LIDAR を mj_ray の実レイキャストでシミュレートし点群を生成・可視化"
     "(GPU不要・命中率など実測)", "image"),
    ("focus_stack", "focus_stack", "run_focus_stack_demo",
     "真値深度から被写界深度ボケの焦点スタックを生成し局所シャープネス最大で全焦点合成"
     "(焦点由来深度も復元、GPU不要)", "image"),
    ("event_camera", "event_camera", "run_event_demo",
     "イベントカメラ(DVS)を対数輝度変化モデルで模倣し ON/OFF イベント列を生成。"
     "動くエッジに発火することを実測(GPU不要)", "image"),
    ("stereo_depth", "stereo_sim", "run_stereo_demo",
     "平行2カメラのステレオペアを描画しブロックマッチングで深度推定、真値深度と誤差比較"
     "(既存 stereo.py 使用、GPU不要)", "image"),
    ("polarization", "polar_cam", "run_polar_demo",
     "偏光カメラを Fresnel 順モデル(法線→DoLP/AoLP→4偏光画像→Stokes)で模倣。"
     "無テクスチャ面でも表面方位を偏光が符号化(透過/鏡面把持向け、GPU不要)", "image"),
]


def _load_3dgs(reg: Registry) -> None:
    for name, mod, fn, doc, hint in _3DGS_OPS:
        reg.register(UnifiedOp(name=name, func=_lazy_call(mod, fn),
                               module=f"{mod}.{fn}", chapter="3dgs", namespace="gsplat",
                               doc=doc, provenance="3dgs", render_hint=hint, params=[]))


def build_registry() -> Registry:
    """4 層(facade 600 / 進化 735 / 知覚 facade / OSS アダプタ)を 1 索引に統合(F2/F3/F4)。
    facade を最初に登録=bare 名衝突時は genuine facade を優先(既存挙動維持)。"""
    reg = Registry()
    _load_facade(reg)          # 1. genuine facade(優先)
    _load_evolution(reg)       # 2. 進化 registry(a/b ノブ)
    _load_perception(reg)      # 3. 知覚 facade(自然シグネチャ)
    _load_oss(reg)             # 4. OSS アダプタ(OpenCV/skimage、numpy フォールバック)
    _load_sim(reg)             # 5. sim-source(物理→視覚の入力供給、F4)
    _load_3dgs(reg)            # 6. 3DGS/SuGaR/メッシュ再生(provenance=3dgs)
    return reg


# ── 遅延構築 + 名前空間の遅延公開(F1/F2)─────────────────────────────────────── #
# fullseye パッケージが unified を import し、unified が fullseye.REGISTRY / 知覚 facade を
# 読むため循環する。遅延構築 + publish-before-load で re-entrancy を安全化する。
_registry: Registry | None = None
_ns_cache: dict = {}


def _ensure() -> Registry:
    global _registry
    if _registry is None:
        reg = Registry()
        _registry = reg                      # 層ロード前に publish(再入時は途中の reg を返す)
        _load_facade(reg)
        _load_evolution(reg)
        _load_perception(reg)
        _load_oss(reg)
        _load_sim(reg)
        _load_3dgs(reg)
    return _registry


def _ns_object(name: str) -> _NS:
    reg = _ensure()
    if name not in _ns_cache:
        _ns_cache[name] = _NS(name, {o: reg[o] for o in reg.list(namespace=name)})
    return _ns_cache[name]


def __getattr__(name):  # PEP 562: unified.ops / unified.contour を遅延解決
    if name == "ops":
        return _ensure()
    reg = _ensure()
    if name in reg.namespaces():
        return _ns_object(name)
    raise AttributeError(f"module 'unified' has no attribute {name!r}")


def namespaces() -> dict:
    """{名前空間名: _NS} を返す(Studio/エージェントの列挙用)。"""
    return {ns: _ns_object(ns) for ns in _ensure().namespaces()}


# ── F5 合成: op をパイプライン化して繋ぐ(画像チェーン / 知覚の段組み)──────────── #

def _resolve_op(op) -> "UnifiedOp":
    """op を UnifiedOp に解決: UnifiedOp / registry の op 名 / 生 callable を受ける。"""
    if isinstance(op, UnifiedOp):
        return op
    if callable(op) and not isinstance(op, str):
        return UnifiedOp(
            name=getattr(op, "__name__", "callable"), func=op,
            module=getattr(op, "__module__", "?"), chapter="Pipeline", namespace="pipeline",
            doc=((op.__doc__ or "").strip().split("\n")[0]),
            render_hint="image", params=_params_of(op), provenance="inline")
    reg = _ensure()
    found = reg.get(op)
    if found is None:
        cand = ", ".join(o.name for o in reg.find(str(op))[:5]) or "(なし)"
        raise KeyError(f"pipeline: op {op!r} は registry に無い。候補: {cand}")
    return found


class Pipeline:
    """op を段組みして繋ぐ(F5)。単一 registry(F2)の op を解決し、前段の出力を次段の
    第 1 引数へ流す。各段は F3 メタで introspection 可能(Studio/エージェント共有)。"""

    def __init__(self, stages=None) -> None:
        self._stages: list = []          # [(UnifiedOp, kwargs), ...]
        for s in (stages or []):
            if isinstance(s, tuple):
                self.then(s[0], **(s[1] if len(s) > 1 else {}))
            else:
                self.then(s)

    def then(self, op, **kwargs) -> "Pipeline":
        """段を 1 つ追加(fluent)。op = UnifiedOp / op 名 / 生 callable。"""
        self._stages.append((_resolve_op(op), kwargs))
        return self

    def run(self, x, *, trace: bool = False):
        """入力 x を全段に順に流す。trace=True で各段の中間出力も返す。"""
        vals = [x]
        for op, kw in self._stages:
            x = op(x, **kw)
            vals.append(x)
        return (x, vals) if trace else x

    __call__ = run

    @property
    def render_hint(self) -> str:
        return self._stages[-1][0].render_hint if self._stages else "image"

    @property
    def steps(self) -> list:
        return [(op.name, dict(kw)) for op, kw in self._stages]

    def describe(self) -> dict:
        """F3: パイプライン全体の機械可読メタ(段ごとの op メタ + 束縛 kwargs)。"""
        return {"n_stages": len(self._stages), "render_hint": self.render_hint,
                "chain": " → ".join(f"{op.namespace}.{op.name}" for op, _ in self._stages),
                "stages": [{**op.as_dict(), "bound": {k: repr(v) for k, v in kw.items()}}
                           for op, kw in self._stages]}

    def __len__(self) -> int:
        return len(self._stages)

    def __repr__(self) -> str:
        chain = " → ".join(f"{op.namespace}.{op.name}" for op, _ in self._stages)
        return f"<Pipeline [{chain or 'empty'}]  ({len(self._stages)} stages)>"


def pipeline(*stages) -> "Pipeline":
    """Pipeline を可変長で作る: pipeline('elevation_map', ('step_edges', {'min_rise': 0.008}))。"""
    return Pipeline(list(stages))


class Image:
    """画像チェーン(F5・§7 の "文のように読める" 形): Image(arr).<op>(...).<op>(...)。
    属性は単一 registry の op 名に解決され、現配列へ適用して新しい Image を返す(不変)。
    タプル出力(例: elevation_map→(grid,extent))は先頭 ndarray を鎖の値にする。"""

    def __init__(self, array, _history=None) -> None:
        object.__setattr__(self, "_a", array)
        object.__setattr__(self, "_history", list(_history or []))

    @property
    def value(self):
        """鎖の現在値(ndarray など)。"""
        return object.__getattribute__(self, "_a")

    array = value

    @property
    def history(self) -> list:
        """これまでに適用した op 名の列。"""
        return list(object.__getattribute__(self, "_history"))

    def apply(self, op, **kwargs) -> "Image":
        uop = _resolve_op(op)
        res = uop(object.__getattribute__(self, "_a"), **kwargs)
        arr = res[0] if isinstance(res, tuple) and res and hasattr(res[0], "shape") else res
        return Image(arr, object.__getattribute__(self, "_history") + [uop.name])

    def __getattr__(self, item):
        if item.startswith("_"):
            raise AttributeError(item)
        reg = _ensure()
        uop = reg.get(item)
        if uop is None:
            cand = ", ".join(o.name for o in reg.find(item)[:6]) or "(なし)"
            raise AttributeError(f"Image に op '{item}' は無い。候補: {cand}")

        def _bound(**kwargs):
            return self.apply(uop, **kwargs)
        _bound.__name__ = item
        return _bound

    def __repr__(self) -> str:
        shp = getattr(object.__getattribute__(self, "_a"), "shape", "?")
        hist = " → ".join(object.__getattribute__(self, "_history")) or "raw"
        return f"<Image {shp} via [{hist}]>"


if __name__ == "__main__":
    print("== Fullseye 統一 I/F registry ==")
    ops = _ensure()
    st = ops.stats()
    print(f"総 op {st['total']} / 名前空間 {st['namespaces']}  provenance {st['by_provenance']}")
    for ns, n in st["by_namespace"].items():
        print(f"  fs.{ns:10} {n:3} ops   例: {', '.join(ops.list(namespace=ns)[:3])}")
    print("\n== F2 検索 例: 'circle' ==")
    for o in ops.find("circle")[:6]:
        print(" ", o, "->", o.doc[:48])
    print("\n== F3 メタ 例: gen_circle_contour_xld ==")
    import pprint
    pprint.pprint(ops.describe("gen_circle_contour_xld"))
