"""Fullseye 3DGS シーン(モデル)レジストリ ―― 散在するモデルを一元管理。

各シーンの XML パス・外部メッシュ dir・既定 framing(lookat/radius/elevation)・カテゴリ・
付随モーション軌道を 1 か所で持つ。外部メッシュが要るモデル(evis 等)は meshdir を注入
した自己完結 XML を `.scene_cache/` に生成して返すので、呼び手はパスを渡すだけでよい。

  scene_registry.entries()          -> [(name, spec, available)]
  scene_registry.resolve("evis")    -> {xml(ロード可能), lookat, radius, elevation_deg, ...}
  scene_registry.motion("evis","walk") -> qpos 軌道 .npy パス(無ければ None)

ユーザー定義は register(name, ...) か scenes.json(imgevolve 直下)で追加できる。
"""
from __future__ import annotations
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
_CACHE = os.path.join(ROOT, ".scene_cache")
_MENAGERIE = "C:/dev/projects/mujoco_menagerie"
_ONO = "C:/dev/projects/onocollo-complete/out/musculo"
_LOCO_MESHES = "C:/dev/venvs/loco/Lib/site-packages/loco_mujoco/environments/data/humanoid"

_DEMO_XML = (
    '<mujoco><worldbody><light pos="0 0 3" dir="0 0 -1"/>'
    '<geom name="floor" type="box" size="1 1 .02" pos="0 0 0" rgba=".4 .45 .5 1"/>'
    '<geom type="sphere" size=".18" pos=".25 0 .25" rgba=".85 .2 .2 1"/>'
    '<geom type="box" size=".12 .12 .12" pos="-.2 .2 .18" rgba=".2 .7 .3 1"/>'
    '<geom type="capsule" size=".08 .12" pos="-.15 -.2 .2" rgba=".25 .35 .85 1"/>'
    '</worldbody></mujoco>')

# framing = lookat(xyz), radius, elevation_deg。category は表示・gait 適用の目安。
_CATALOG = {
    "demo":   {"synthetic": _DEMO_XML, "category": "synthetic",
               "lookat": [0, 0, 0.2], "radius": 1.3, "elevation_deg": 25},
    "go2":    {"xml": f"{_MENAGERIE}/unitree_go2/scene.xml", "category": "quadruped",
               "lookat": [0, 0, 0.18], "radius": 1.3, "elevation_deg": 22, "gait": "trot"},
    "anymal": {"xml": f"{_MENAGERIE}/anybotics_anymal_c/scene.xml", "category": "quadruped",
               "lookat": [0, 0, 0.4], "radius": 1.8, "elevation_deg": 20, "gait": "trot"},
    "spot":   {"xml": f"{_MENAGERIE}/boston_dynamics_spot/scene.xml", "category": "quadruped",
               "lookat": [0, 0, 0.4], "radius": 1.8, "elevation_deg": 20, "gait": "trot"},
    "cassie": {"xml": f"{_MENAGERIE}/agility_cassie/scene.xml", "category": "biped",
               "lookat": [0, 0, 0.6], "radius": 2.2, "elevation_deg": 18},
    "apollo": {"xml": f"{_MENAGERIE}/apptronik_apollo/scene.xml", "category": "humanoid",
               "lookat": [0, 0, 0.8], "radius": 2.6, "elevation_deg": 15},
    "evis":   {"xml": f"{_ONO}/loco/humanoid_muscle_mjxfeet.xml", "meshdir": _LOCO_MESHES,
               "category": "musculo-skeleton", "lookat": [-0.3, 0.13, 0.85],
               "radius": 2.2, "elevation_deg": 12, "view_azimuth": 0.5,
               "motions": {"walk": f"{_ONO}/loco/mjx_loco_free2_view_qpos.npy", "getup": f"{_ONO}/loco/mjx_loco_cpg1_view_qpos.npy"}},
}


def _load_user_catalog():
    """imgevolve/scenes.json があればユーザー定義を統合(同名は上書き)。"""
    p = os.path.join(ROOT, "scenes.json")
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as f:
                _CATALOG.update(json.load(f))
        except (OSError, ValueError):
            pass


_load_user_catalog()


def register(name, **spec):
    """実行時にシーンを追加/上書き。"""
    _CATALOG[name] = spec


def _available(spec):
    if "synthetic" in spec:
        return True
    xml = spec.get("xml")
    return bool(xml and os.path.isfile(xml))


def names():
    return list(_CATALOG)


def entries():
    """[(name, spec, available)] を返す。"""
    return [(n, s, _available(s)) for n, s in _CATALOG.items()]


def _cache_xml(name, content):
    os.makedirs(_CACHE, exist_ok=True)
    p = os.path.join(_CACHE, f"{name}.xml")
    if not os.path.isfile(p) or open(p, encoding="utf-8").read() != content:
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    return p


def _patch_meshdir(xml_path, meshdir):
    """<compiler ...> に meshdir を注入した自己完結 XML をキャッシュに書き出す。"""
    src = open(xml_path, encoding="utf-8").read()
    if "meshdir" in src:
        return xml_path
    patched = src.replace("<compiler ", f'<compiler meshdir="{meshdir}" ', 1)
    if patched == src:                                  # <compiler> が無い場合は先頭に追加
        patched = src.replace("<mujoco>", f'<mujoco><compiler meshdir="{meshdir}"/>', 1)
    return _cache_xml(os.path.basename(xml_path)[:-4] + "_patched", patched)


def resolve(name):
    """名前 or .xml パスを framing 付き spec に解決。ロード可能な xml パスを返す。無ければ None。"""
    if name in _CATALOG:
        s = dict(_CATALOG[name])
        if "synthetic" in s:
            s["xml"] = _cache_xml(name, s.pop("synthetic"))
        elif s.get("meshdir"):
            if not os.path.isfile(s["xml"]):
                return None
            s["xml"] = _patch_meshdir(s["xml"], s["meshdir"])
        elif not os.path.isfile(s.get("xml", "")):
            return None
        s.setdefault("lookat", [0, 0, 0.3]); s.setdefault("radius", 2.0)
        s.setdefault("elevation_deg", 20); s.setdefault("category", "custom")
        s["name"] = name
        return s
    if name.endswith(".xml") and os.path.isfile(name):   # 任意 MJCF パス
        return {"name": name, "xml": name, "lookat": [0, 0, 0.3], "radius": 2.0,
                "elevation_deg": 20, "category": "custom"}
    return None


def motion(name, key=None):
    """シーンの付随モーション軌道 .npy パス。key 省略時は最初の1つ。無ければ None。"""
    s = _CATALOG.get(name)
    if not s or "motions" not in s:
        return None
    motions = s["motions"]
    if key is None:
        key = next(iter(motions))
    p = motions.get(key)
    return p if (p and os.path.isfile(p)) else None


def motions(name):
    """シーンの利用可能モーション名の一覧。"""
    s = _CATALOG.get(name)
    return [k for k, p in (s.get("motions", {}) if s else {}).items() if os.path.isfile(p)]
