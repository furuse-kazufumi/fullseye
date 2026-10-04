# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""driveworld — 教習所コース(drivecourse)を 3-D の世界にする: 路面・縁石・白線・坂・車・信号機・カメラ。

自動運転の PoC は「センサが何を見たか」を採点したいのに、見せる世界の**真値**が無いと採点できない。
このモジュールは規格寸法のコース(:mod:`drivecourse`、道路交通法施行規則 別表第三)を三角形メッシュの
世界にし、面ごとに **ラベル**(路面・縁石・車・信号機 …)と **色** を持たせる。LiDAR(:mod:`lidarsim`)は
この面を撃って点とラベルを返し、カメラ(:func:`world_camera`)は同じ面を色・ラベル・深度の画像にする。
真値は全部この世界の側にある —— 点がどの面から来たか、画素がどの物体か、信号が何色かは、生成時に決まっている。

固有価値(既存との棲み分け, honest):
  * :mod:`render3d` は 1 つのメッシュを深度・法線に描く描画器。ここは**複数の物体を寸法・姿勢で置き、面のラベルと色を
    運ぶ世界の組み立て**(render3d の `attributes=True` の三角形 id から色・ラベル画像を引く)。
  * :mod:`world_render` は四足ロボの地形歩行の GIF。ここは車の教習所(平らな路面・縁石・信号)。
  * 車・信号機・標識のメッシュは Kenney の CC0 キット(Car Kit / City Kit Roads、www.kenney.nl)。CC0 なので同梱できる。
    読込は自前の OBJ 読み(`v x y z r g b` の 6 値、`vt`、`f v/vt/vn`)で、色は UV からテクスチャ(colormap.png)を引く
    (:mod:`mesh` は UV を捨てるので使えない)。

フレーム規約:
  * 世界: x = 前/東, y = 左/北, z = 上(右手系)、メートル。路面は z = 0(坂道の要素だけ z > 0 の斜面を持つ)。
  * Kenney のモデルは y-up なので (x, y, z) → (x, −z, y) で z-up に直し、車は長軸(y-up の z)を x に、前照灯の側を +x に、
    街灯は腕を +x に、信号機は頭を +x に回してから(向きは軸の長さ・左右対称性・灯の色で決め、門にしてある)、**各モデルの箱の寸法を実寸(車長 4.5 m 等)に合わせて
    軸ごとに引き伸ばす**(玩具の比率のままだと車幅が 2.6 m になる)。原点は箱の底面中心。
  * 姿勢 (x, y, yaw) は carpath と同じ(yaw は +x から反時計回り、ラジアン)。

ラベル(int): 0 路面 / 1 縁石 / 2 車 / 3 信号機 / 4 標識 / 5 コーン / 6 障害物 / 7 歩行者 / 8 レール / 9 白線(:data:`LABELS`)。
信号機の灯火は面ラベル 3 のまま、`objects[i]["state"]`("red" / "yellow" / "green")で色だけ変わる(灯火の面は `lamp_faces`)。

限界(self_reported):
  * 縁石は要素の多角形の縁に沿う箱の帯(高さ 0.15 m・幅 0.3 m)で、要素の継ぎ目の辺(別の要素の内側にある辺)には置かない。
    継ぎ目が部分的に重なる配置では縁石が道を横切る —— 配置は要素の幅を揃えて突き合わせること。
  * 坂道は斜面のメッシュを路面の上に重ねる(下の平面は隠れる)。斜面の縁石は無い。
  * 白線は路面から 5 mm 浮いた薄い四角形。カメラには映るが LiDAR の反射強度モデルは無い(ラベルで見分ける)。
  * カメラは render3d の深度描画に色を後付けした Lambert(法線と光の内積)。影・反射・露出は無い。

参考: Kenney (2026) Car Kit 3.1 / City Kit Roads, CC0 1.0. Catmull (1974) z-buffer(render3d)。
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import numpy as np

__all__ = [
    "LABELS", "ASSETS", "CAR_PAINTS", "asset_dir", "read_obj_colored", "load_asset", "place_mesh",
    "world_build", "world_add", "world_camera", "world_bounds", "set_signal_state", "add_asset", "add_signal",
    "camera_pose", "camera_intrinsics", "world_project_points", "overlay_points", "polygon_triangulate", "world_move",
]

LABELS = {0: "ground", 1: "kerb", 2: "car", 3: "traffic_light", 4: "sign", 5: "cone",
          6: "block", 7: "pedestrian", 8: "rail", 9: "line",
          10: "terrain", 11: "puddle", 12: "crosswalk", 13: "tree",      # 10 以降は driveterrain(16 巡目)
          14: "building", 15: "sidewalk", 16: "pole"}                     # 14 以降は drivejapan(実在の町: PLATEAU の建物・街区の歩道・電柱)

#: 同梱する CC0 資産: 名前 → (キット, ファイル, 実寸 (長さ x, 幅 y, 高さ z) [m], ラベル)。
ASSETS = {
    "sedan": ("cars", "sedan.obj", (4.5, 1.8, 1.45), 2),
    "suv": ("cars", "suv.obj", (4.7, 1.9, 1.75), 2),
    "taxi": ("cars", "taxi.obj", (4.5, 1.8, 1.5), 2),
    "police": ("cars", "police.obj", (4.8, 1.85, 1.5), 2),
    "truck": ("cars", "truck.obj", (5.3, 1.9, 1.8), 2),                 # Kenney の truck はピックアップ(生の比 2.95 : 1.5 : 1.3)
    "cone": ("cars", "cone.obj", (0.4, 0.4, 0.5), 5),
    "traffic_light": ("roads", "traffic-light.obj", (1.15, 0.87, 5.0), 3),   # 柱 + 頭(頭は +x に張り出す)、生の比で 5 m に
    "sign_stop": ("roads", "road-sign-stop.obj", (0.35, 0.61, 2.2), 4),
    "street_light": ("roads", "light-curved.obj", (2.0, 0.45, 6.0), 6),      # 腕は +x へ 2 m、生の比で 6 m に
}
#: 寸法は**生のモデルの比を保つ**(軸ごとの寸法合わせは向きが違うと形を潰す —— 2026-09-30 の訂正: 街灯の柱が幅 2.5 m の板、
#: 信号機の頭が平板になっていた)。車だけは実寸(4.5 × 1.8 × 1.45 等)に軸ごとに合わせる(生の比との差は 1.8 倍以内)。
#: 資産ごとの向きの規約: 車は前 = +x、街灯は腕 = +x、信号機は頭 = +x(灯火はその前面)、標識は面の法線 = x。
_ASSET_YAW = {"street_light": -np.pi / 2, "traffic_light": np.pi}       # z-up に直した後に z 軸まわりに回す角(腕・頭を +x へ)
_KIT_DIR = {"cars": "car-kit", "roads": "city-kit-roads"}
_COLORMAP = "colormap.png"

_ROAD_COLOR = (0.40, 0.41, 0.43)
_KERB_COLOR = (0.78, 0.78, 0.74)
_LINE_COLOR = (0.95, 0.95, 0.92)
_RAMP_COLOR = (0.30, 0.31, 0.33)
_LAMP = {"red": (1.0, 0.12, 0.08), "yellow": (1.0, 0.80, 0.10), "green": (0.10, 0.95, 0.40), "off": (0.12, 0.12, 0.12)}


# ─────────────────────────────── 資産の置き場 ────────────────────────────────

def asset_dir() -> Path:
    """CC0 資産のディレクトリ(`<kit>/<file>.obj` と `<kit>/colormap.png`)。

    環境変数 ``FULLSEYE_KENNEY_DIR`` → repo 同梱 ``studio_assets/sample_3d/kenney`` の順に探し、
    どちらにも無ければ FileNotFoundError(黙って箱に置き換えない)。"""
    cands = []
    env = os.environ.get("FULLSEYE_KENNEY_DIR")
    if env:
        cands.append(Path(env))
    cands.append(Path(__file__).resolve().parent / "studio_assets" / "sample_3d" / "kenney")
    for c in cands:
        if (c / _KIT_DIR["cars"] / _COLORMAP).is_file():
            return c
    raise FileNotFoundError("Kenney CC0 資産が見つからない(FULLSEYE_KENNEY_DIR か studio_assets/sample_3d/kenney): %s"
                            % ", ".join(str(c) for c in cands))


# ─────────────────────────────── OBJ(UV つき)の読み ─────────────────────────

def _read_png_rgb(path) -> np.ndarray:
    """PNG → float (H, W, 3) in [0, 1]。imgio があればそれを、無ければ PIL。"""
    try:
        from PIL import Image
        im = np.asarray(Image.open(str(path)).convert("RGB"), np.float64) / 255.0
        return im
    except ImportError:  # pragma: no cover - PIL は repo の依存に入っている
        import imgio
        return np.asarray(imgio.read_image(str(path)), np.float64)[..., :3]


def read_obj_colored(path, texture=None):
    """Wavefront OBJ(`v x y z [r g b]`、`vt u v`、`f v/vt/vn …`、多角形は扇で三角化)を読む。

    Returns ``(V (N,3) float64, F (M,3) int64, color (M,3) float64)``。面の色は UV の重心でテクスチャを引く
    (texture が None、または面に UV が無ければ頂点色、それも無ければ灰 0.7)。壊れた OBJ(頂点なし・面の索引が範囲外)は
    ValueError(fail-closed)。"""
    text = io.open(str(path), encoding="utf-8", errors="replace").read()
    V, VC, VT, faces, fuv = [], [], [], [], []
    for ln in text.splitlines():
        s = ln.split("#")[0].strip()
        if not s:
            continue
        p = s.split()
        if p[0] == "v" and len(p) >= 4:
            V.append([float(p[1]), float(p[2]), float(p[3])])
            VC.append([float(p[4]), float(p[5]), float(p[6])] if len(p) >= 7 else [0.7, 0.7, 0.7])
        elif p[0] == "vt" and len(p) >= 3:
            VT.append([float(p[1]), float(p[2])])
        elif p[0] == "f" and len(p) >= 4:
            vi, ti = [], []
            for tok in p[1:]:
                parts = tok.split("/")
                vi.append(int(parts[0]))
                ti.append(int(parts[1]) if len(parts) > 1 and parts[1] else 0)
            for k in range(1, len(vi) - 1):          # 扇で三角化
                faces.append([vi[0], vi[k], vi[k + 1]])
                fuv.append([ti[0], ti[k], ti[k + 1]])
    if not V or not faces:
        raise ValueError("OBJ に頂点か面が無い: %s" % path)
    Va = np.asarray(V, np.float64)
    n = len(Va)
    Fa = np.asarray(faces, np.int64)
    Fa = np.where(Fa < 0, Fa + n + 1, Fa) - 1          # OBJ は 1 始まり、負は末尾から
    if Fa.min() < 0 or Fa.max() >= n:
        raise ValueError("OBJ の面の索引が頂点の範囲外: %s" % path)
    color = np.asarray(VC, np.float64)[Fa].mean(axis=1)
    if texture is not None and VT:
        T = np.asarray(VT, np.float64)
        U = np.asarray(fuv, np.int64)
        has = (U > 0).all(axis=1) & (U <= len(T)).all(axis=1)
        if has.any():
            tex = np.asarray(texture, np.float64)
            H, W = tex.shape[:2]
            uv = T[U[has] - 1].mean(axis=1)             # 面の UV 重心
            u = np.clip(uv[:, 0] % 1.0, 0, 1) * (W - 1)
            v = (1.0 - np.clip(uv[:, 1] % 1.0, 0, 1)) * (H - 1)
            color[has] = tex[np.rint(v).astype(int), np.rint(u).astype(int), :3]
    return Va, Fa, color


def _yup_to_zup(V: np.ndarray) -> np.ndarray:
    """Kenney(y-up)→ 世界(z-up): (x, y, z) → (x, −z, y)。右手系のまま x 軸まわり +90°。"""
    return np.column_stack([V[:, 0], -V[:, 2], V[:, 1]])


def _orient_car(V: np.ndarray) -> np.ndarray:
    """Kenney の車キットを「長さ = x、前 = +x」に向ける: z-up に直した直後は**長軸が y**(y-up の z)で、前(黄色い前照灯)が −y、
    後ろ(赤い尾灯)が +y。z 軸まわり +90°((x, y) → (−y, x))で前が +x に来る。

    ★2026-09-30 の訂正: それまで「長さは x」と仮定して軸ごとに寸法を合わせていたので、幅 1.5 m が 4.5 m に伸び、長さ 2.55 m が
    1.8 m に潰れ、車が 90° 横向きの別の形になっていた(ユーザー指摘「車の向きを間違えてるように見える」。前日の 180° 回しは
    誤診で、潰れた形を反転しただけ)。門は生のモデルの最長軸が x に来ること + 灯の色の位置で立てる(test_driveworld)。"""
    return np.column_stack([-V[:, 1], V[:, 0], V[:, 2]])


#: 車体色(日本で多い順の目安: 白・黒・シルバー・グレー・青・赤・ベージュ・茶・緑)。表示用の sRGB 値(0〜1)。
#: 塗り替えは車体の面だけ(ガラス・タイヤ・灯火・内装は元の色)で、元のテクスチャの濃淡(明るさの比)を保つ。
CAR_PAINTS = {
    "white": (0.93, 0.93, 0.91), "black": (0.08, 0.08, 0.09), "silver": (0.72, 0.73, 0.75), "grey": (0.42, 0.43, 0.45),
    "blue": (0.14, 0.27, 0.58), "red": (0.74, 0.09, 0.11), "beige": (0.80, 0.72, 0.56), "brown": (0.42, 0.27, 0.18),
    "green": (0.18, 0.40, 0.25),
}
#: 塗装そのものが意味を持つ車(パトカーの白黒・タクシーの行灯と車体色)は塗り替えない。
_LIVERY = ("police", "taxi")


def _rgb_to_hsv(C: np.ndarray) -> np.ndarray:
    """(M, 3) の RGB → (M, 3) の HSV(色相は 0〜1)。numpy だけで(colorsys を行ごとに回さない)。"""
    C = np.asarray(C, np.float64)
    mx, mn = C.max(axis=1), C.min(axis=1)
    d = mx - mn
    h = np.zeros(len(C))
    nz = d > 1e-12
    r, g, b = C[:, 0], C[:, 1], C[:, 2]
    i = nz & (mx == r)
    h[i] = ((g - b)[i] / d[i]) % 6.0
    i = nz & (mx == g) & (mx != r)
    h[i] = (b - r)[i] / d[i] + 2.0
    i = nz & (mx == b) & (mx != r) & (mx != g)
    h[i] = (r - g)[i] / d[i] + 4.0
    s = np.where(mx > 1e-12, d / np.maximum(mx, 1e-12), 0.0)
    return np.column_stack([h / 6.0, s, mx])


def _car_body_mask(mesh: dict) -> np.ndarray:
    """車の資産(:func:`load_asset` の返り値)の**車体の塗装の面**の (M,) bool。

    決め方: 彩度 0.45〜0.80 の面(ガラス・タイヤ・金属は無彩色、灯火は彩度 > 0.8 か前照灯・尾灯の色の判定で外す)を色相 10° の箱に分け、面積が
    最大の箱の ±25° に入る面。実測(2026-09-30): セダン = 0〜10°(車体面積の 26 %)、SUV・ピックアップ = 150°(15 % / 24 %)。
    車体と灯火の色相が近いセダン(尾灯 ≈ 3°)は、尾灯の色の判定(R > 0.6・G < 0.35・B < 0.35)で先に外す。
    車体の面が見つからない(彩度のある面が全体の 5 % 未満)なら ValueError(黙って何も塗らない、を許さない)。"""
    C = np.asarray(mesh["color"], np.float64)
    V, F = np.asarray(mesh["V"], np.float64), np.asarray(mesh["F"], np.int64)
    area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    hsv = _rgb_to_hsv(C)
    lamp = ((C[:, 0] > 0.6) & (C[:, 1] < 0.35) & (C[:, 2] < 0.35)) | ((C[:, 0] > 0.8) & (C[:, 1] > 0.6) & (C[:, 2] < 0.3))
    cand = (hsv[:, 1] > 0.45) & (hsv[:, 1] < 0.80) & ~lamp
    if area[cand].sum() < 0.05 * area.sum():
        raise ValueError("_car_body_mask: 車体の塗装の面が見つからない(彩度のある面 %.1f %%)" % (100.0 * area[cand].sum() / max(area.sum(), 1e-12)))
    bins = (hsv[:, 0] * 36).astype(int) % 36
    w = np.bincount(bins[cand], weights=area[cand], minlength=36)
    h0 = (np.argmax(w) + 0.5) / 36.0
    dh = np.abs(((hsv[:, 0] - h0) + 0.5) % 1.0 - 0.5)
    return cand & (dh <= 25.0 / 360.0)


def _repaint_car(mesh: dict, paint) -> dict:
    """車の資産の車体を ``paint``(:data:`CAR_PAINTS` の名前か (r, g, b))に塗り替えた**新しい** mesh を返す(元は変えない)。

    濃淡の保存: 新しい色 = paint × (その面の明るさ / 車体の面の明るさの中央値)を [0, 1] に切る。``paint`` が None か "original" なら写しを返す。
    パトカー・タクシー(塗装が意味を持つ)は ValueError。未知の色の名前・範囲外の RGB も ValueError。"""
    out = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in mesh.items()}
    if paint is None or paint == "original":
        return out
    if mesh.get("name") in _LIVERY:
        raise ValueError("_repaint_car: %s は塗装が意味を持つので塗り替えない" % mesh.get("name"))
    if isinstance(paint, str):
        if paint not in CAR_PAINTS:
            raise ValueError("_repaint_car: 未知の色 %r(%s)" % (paint, ", ".join(sorted(CAR_PAINTS))))
        rgb = np.asarray(CAR_PAINTS[paint], np.float64)
    else:
        rgb = np.asarray(paint, np.float64)
        if rgb.shape != (3,) or not np.all((rgb >= 0.0) & (rgb <= 1.0)):
            raise ValueError("_repaint_car: paint は色の名前か [0, 1] の (r, g, b)")
    body = _car_body_mask(mesh)
    v = np.asarray(mesh["color"], np.float64).max(axis=1)
    ref = float(np.median(v[body]))
    out["color"][body] = np.clip(rgb[None, :] * (v[body] / ref)[:, None], 0.0, 1.0)
    out["paint"] = paint
    return out


_ASSET_CACHE: dict = {}


def load_asset(name: str, dims=None, *, root=None, paint=None) -> dict:
    """同梱資産をメッシュ dict に: ``{"V", "F", "color", "label", "name", "dims"}``。

    z-up に直し、箱の寸法を ``dims``(既定 = :data:`ASSETS` の実寸)に軸ごとに合わせ、原点を箱の底面中心に置く。
    未知の名前・寸法 ≤ 0 は ValueError。同じ名前は 1 度だけ読む(キャッシュ)。

    ``paint``: 車の車体色(:data:`CAR_PAINTS` の名前か (r, g, b)、None = 元の色)。車体の面だけを塗り替え、ガラス・タイヤ・灯火は元のまま、
    テクスチャの濃淡(明るさの比)は保つ。パトカー・タクシー(塗装が意味を持つ)と車以外は ValueError。"""
    if name not in ASSETS:
        raise ValueError("unknown asset %r (known: %s)" % (name, sorted(ASSETS)))
    kit, fname, dims0, label = ASSETS[name]
    dims = np.asarray(dims0 if dims is None else dims, np.float64)
    if dims.shape != (3,) or not np.all(dims > 0):
        raise ValueError("dims は正の 3 要素: %r" % (dims,))
    root = Path(root) if root is not None else asset_dir()
    key = (str(root), name)
    if key not in _ASSET_CACHE:
        kd = root / _KIT_DIR[kit]
        tex = _read_png_rgb(kd / _COLORMAP)
        V, F, C = read_obj_colored(kd / fname, tex)
        V = _yup_to_zup(V)
        if kit == "cars":
            V = _orient_car(V)
        elif name in _ASSET_YAW:
            V = place_mesh(V, 0.0, 0.0, _ASSET_YAW[name])                  # 街灯の腕(生では +y)・信号機の頭(生では −x)を +x へ
        _ASSET_CACHE[key] = (V, F, C)
    V, F, C = _ASSET_CACHE[key]
    lo, hi = V.min(axis=0), V.max(axis=0)
    ext = np.where(hi - lo > 1e-9, hi - lo, 1.0)
    Vs = (V - (lo + hi) / 2.0) / ext * dims
    Vs[:, 2] -= Vs[:, 2].min()                          # 底面を z = 0 に
    out = {"V": Vs, "F": F.copy(), "color": C.copy(), "label": int(label), "name": name, "dims": dims}
    if paint is not None and paint != "original":
        if kit not in ("cars",) or name == "cone":
            raise ValueError("paint は車にだけ使える(%s)" % name)
        out = _repaint_car(out, paint)
    return out


def place_mesh(V, x: float, y: float, yaw: float, z: float = 0.0) -> np.ndarray:
    """頂点を姿勢 (x, y, yaw[, z]) に置く(z 軸まわり回転 → 平行移動)。"""
    V = np.asarray(V, np.float64)
    c, s = np.cos(yaw), np.sin(yaw)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return V @ R.T + np.array([x, y, z])


# ─────────────────────────────── 多角形の三角化(耳切り)──────────────────────

def _signed_area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def polygon_triangulate(poly) -> np.ndarray:
    """単純多角形(穴なし)を耳切り(Meister 1975 / ear clipping)で三角形の索引 (M, 3) に。

    向きは反時計回りに揃えてから切る(時計回りなら反転)。自己交差や重複点で耳が見つからなくなったら
    ValueError(黙って残りを捨てない)。O(K²) だがコースの多角形は数百点なので十分。"""
    P = np.asarray(poly, np.float64)
    if P.ndim != 2 or P.shape[1] != 2 or len(P) < 3:
        raise ValueError("polygon は (K>=3, 2)")
    if np.allclose(P[0], P[-1]):
        P = P[:-1]
    idx = list(range(len(P)))
    if _signed_area(P) < 0:
        idx = idx[::-1]
    # 重複点(連続する同じ点)を落とす
    keep = []
    for i in idx:
        if not keep or not np.allclose(P[i], P[keep[-1]], atol=1e-12):
            keep.append(i)
    if len(keep) > 1 and np.allclose(P[keep[0]], P[keep[-1]], atol=1e-12):
        keep.pop()
    idx = keep
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    guard = 0
    while len(idx) > 3:
        n = len(idx)
        found = False
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = P[i0], P[i1], P[i2]
            if cross(a, b, c) <= 1e-12:               # 凹の角(または退化)は耳でない
                continue
            others = [j for j in idx if j not in (i0, i1, i2)]
            if others:
                Q = P[others]
                inside = ((cross(a, b, Q.T) >= -1e-12) & (cross(b, c, Q.T) >= -1e-12)
                          & (cross(c, a, Q.T) >= -1e-12))
                if inside.any():
                    continue
            tris.append([i0, i1, i2])
            idx.pop(k)
            found = True
            break
        if not found:
            guard += 1
            if guard > 2:
                raise ValueError("ear clipping failed: polygon is self-intersecting or degenerate")
            # 数値の縁で耳が見つからないときは許容を緩めて 1 度だけやり直す
            continue
    tris.append(list(idx))
    return np.asarray(tris, np.int64)


# ─────────────────────────────── 世界の組み立て ────────────────────────────

def _seq(el: dict, key: str) -> list:
    """要素の任意の並び(stop_lines / signal_poses / rails)。無い・None は空、配列は list に。"""
    v = el.get(key)
    if v is None:
        return []
    return [np.asarray(x, np.float64) for x in v]


def _elements(course) -> list:
    if course.get("kind") == "layout":
        return list(course["elements"])
    return [course]


def world_bounds(course, margin: float = 8.0):
    """コースの多角形を全部含む (xmin, xmax, ymin, ymax) + 余白。"""
    pts = np.vstack([np.asarray(e["polygon"], np.float64) for e in _elements(course)])
    return (float(pts[:, 0].min() - margin), float(pts[:, 0].max() + margin),
            float(pts[:, 1].min() - margin), float(pts[:, 1].max() + margin))


def _empty_world() -> dict:
    return {"V": np.zeros((0, 3)), "F": np.zeros((0, 3), np.int64), "face_label": np.zeros(0, np.int64),
            "face_color": np.zeros((0, 3)), "objects": []}


def world_add(world: dict, V, F, label: int, color, *, name: str = "", pose=None, extra=None) -> int:
    """世界に三角形の束を足す(索引をずらして連結)。返り値 = objects の索引。color は (3,) か (M, 3)。"""
    V = np.asarray(V, np.float64)
    F = np.asarray(F, np.int64)
    if V.ndim != 2 or V.shape[1] != 3 or F.ndim != 2 or F.shape[1] != 3:
        raise ValueError("V は (N,3)、F は (M,3)")
    if len(F) and (F.min() < 0 or F.max() >= len(V)):
        raise ValueError("F の索引が V の範囲外")
    if not np.all(np.isfinite(V)):
        raise ValueError("V に非有限がある")
    color = np.asarray(color, np.float64)
    if color.ndim == 1:
        color = np.broadcast_to(color, (len(F), 3)).copy()
    if color.shape != (len(F), 3):
        raise ValueError("color は (3,) か (M,3)")
    off = len(world["V"])
    f0 = len(world["F"])
    world["V"] = np.vstack([world["V"], V])
    world["F"] = np.vstack([world["F"], F + off])
    world["face_label"] = np.concatenate([world["face_label"], np.full(len(F), int(label), np.int64)])
    world["face_color"] = np.vstack([world["face_color"], color])
    obj = {"name": name, "label": int(label), "faces": (f0, f0 + len(F)), "verts": (off, off + len(V)),
           "pose": None if pose is None else tuple(float(v) for v in pose)}
    if extra:
        obj.update(extra)
    world["objects"].append(obj)
    return len(world["objects"]) - 1


def _band_mesh(P: np.ndarray, closed: bool, width: float, height: float, skip_edges=None):
    """折線 P (K,2) の**外側**(右手側 = 反時計回り多角形の外)に幅 width・高さ height の箱の帯。"""
    n = len(P)
    m = n if closed else n - 1
    V, F = [], []
    for k in range(m):
        if skip_edges is not None and skip_edges[k]:
            continue
        a, b = P[k], P[(k + 1) % n]
        d = b - a
        L = np.hypot(*d)
        if L < 1e-9:
            continue
        nrm = np.array([d[1], -d[0]]) / L            # 反時計回りの外向き法線(右手側)
        a2, b2 = a + nrm * width, b + nrm * width
        base = len(V)
        for (x, y) in (a, b, b2, a2):
            V.append([x, y, 0.0])
        for (x, y) in (a, b, b2, a2):
            V.append([x, y, height])
        # 底 0-3、上 4-7: 側面 4 枚 + 天面
        quads = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
        for q in quads:
            F.append([base + q[0], base + q[1], base + q[2]])
            F.append([base + q[0], base + q[2], base + q[3]])
    if not F:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.asarray(V, np.float64), np.asarray(F, np.int64)


def _subdivide_closed(P: np.ndarray, max_len: float = 1.0) -> np.ndarray:
    """閉多角形の各辺を max_len 以下の小片に割る(共線の点を足すだけで形は変わらない)。
    継ぎ目の検査を小片ごとにするため —— 長い辺(周回コースの 80 m)の中点だけ見ると、連絡路が刺さる場所を見落とす。"""
    out = []
    n = len(P)
    for k in range(n):
        a, b = P[k], P[(k + 1) % n]
        m = max(1, int(np.ceil(np.hypot(*(b - a)) / max_len)))
        for i in range(m):
            out.append(a + (b - a) * (i / m))
    return np.asarray(out, np.float64)


def _edge_is_joint(P: np.ndarray, others: list) -> np.ndarray:
    """各辺(小片)の両端か中点のどれかが別の要素の多角形の内側なら True(継ぎ目の辺 → 縁石を置かない)。

    中点だけ見ると、隣の要素の口に半分かかった小片が縁石になって道を塞ぐ(2026-09-29 に踏んだ: 連絡路の口の
    LiDAR 点が「走れる」セルに落ちた)。端も見れば、置かれる小片は隣の要素に一切かからない —— 継ぎ目に
    小片 1 つ分(≤ joint_step)の隙間が空くが、それは車道の切れ目として無害。"""
    import drivecourse as DC
    n = len(P)
    Q = np.roll(P, -1, axis=0)
    mid = (P + Q) / 2.0
    out = np.zeros(n, bool)
    for e in others:
        out |= DC.course_contains(e, mid) | DC.course_contains(e, P) | DC.course_contains(e, Q)
    return out


def _ramp_mesh(el: dict):
    """坂道要素: profile (s, z) を entry→exit 方向に押し出した斜面(路面ラベル)。"""
    prof = np.asarray(el["profile"], np.float64)
    ex, ey, eyaw = el["entry"]
    w = float(el["width"])
    c, s = np.cos(eyaw), np.sin(eyaw)
    V, F = [], []
    for (sv, zv) in prof:
        for side in (-1.0, 1.0):
            V.append([ex + c * sv - s * side * w / 2, ey + s * sv + c * side * w / 2, zv])
    for k in range(len(prof) - 1):
        a, b, cq, d = 2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2
        F.append([a, b, cq])
        F.append([a, cq, d])
    return np.asarray(V, np.float64), np.asarray(F, np.int64)


def _grid_plane(xmin, xmax, ymin, ymax, step: float = 4.0, z: float = 0.0):
    """(xmin..xmax) × (ymin..ymax) を step の升に割った平面(z 一定)の頂点と三角形。"""
    nx = max(1, int(np.ceil((xmax - xmin) / step)))
    ny = max(1, int(np.ceil((ymax - ymin) / step)))
    xs = np.linspace(xmin, xmax, nx + 1)
    ys = np.linspace(ymin, ymax, ny + 1)
    X, Y = np.meshgrid(xs, ys)                  # (ny+1, nx+1)
    V = np.column_stack([X.ravel(), Y.ravel(), np.full(X.size, float(z))])
    i = np.arange(ny)[:, None] * (nx + 1) + np.arange(nx)[None, :]
    a, b, c, d = i.ravel(), (i + 1).ravel(), (i + nx + 2).ravel(), (i + nx + 1).ravel()
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])])
    return V, F.astype(np.int64)


def world_build(course, *, props=(), kerb_height: float = 0.15, kerb_width: float = 0.3,
                lines: bool = True, ground_margin: float = 8.0, ground_step: float = 4.0,
                joint_step: float = 0.5, asset_root=None) -> dict:
    """コース(要素か layout)から世界を組む。

    路面 = 全体を覆う平面(z = 0、ラベル 0)。各要素の多角形の縁に縁石(ラベル 1、継ぎ目の辺は除く)、
    縁の内側 0.15 m に白線(ラベル 9)。坂道は斜面のメッシュ(ラベル 0)。交差点の ``signal_poses`` には信号機を立て
    (初期状態 "red"、日本式: 向こう側の柱 + アームで車線上に横型 3 灯、roadjp)、``stop_lines`` に停止線、``crosswalks`` に横断歩道の縞。``props`` は ``(asset_name, x, y, yaw)`` か
    ``(asset_name, x, y, yaw[, dims[, paint]])`` の並び(paint = 車の車体色、:data:`CAR_PAINTS`)。返り値 = ``{"V","F","face_label","face_color","objects","bounds","course"}``。"""
    world = _empty_world()
    xmin, xmax, ymin, ymax = world_bounds(course, ground_margin)
    world["bounds"] = (xmin, xmax, ymin, ymax)
    world["course"] = course
    # 路面は 4 m の格子に割る: 描画器はカメラの背後に頂点を持つ三角形を落とすので、1 枚の巨大な三角形だと
    # 車載カメラの視野から路面ごと消える(格子なら消えるのはカメラの真下・背後の升だけ)。
    Vg, Fg = _grid_plane(xmin, xmax, ymin, ymax, step=ground_step)
    world_add(world, Vg, Fg, 0, _ROAD_COLOR, name="ground")
    els = _elements(course)
    for i, el in enumerate(els):
        P = np.asarray(el["polygon"], np.float64)
        if np.allclose(P[0], P[-1]):
            P = P[:-1]
        if _signed_area(P) < 0:
            P = P[::-1]
        P = _subdivide_closed(P, joint_step)
        others = [e for j, e in enumerate(els) if j != i]
        joint = _edge_is_joint(P, others) if others else np.zeros(len(P), bool)
        Vk, Fk = _band_mesh(P, True, kerb_width, kerb_height, skip_edges=joint)
        if len(Fk):
            world_add(world, Vk, Fk, 1, _KERB_COLOR, name="kerb:%s" % el.get("kind", ""))
        if lines:
            # P[::-1] は時計回り → 帯は「右手側」= 多角形の内側に出る。反転後の辺 k' = (P[n-1-k'], P[n-2-k'])
            # は元の辺 (n-2-k') なので、継ぎ目の印は joint[::-1] を 1 つ手前に回す。
            skip_l = np.roll(joint[::-1], -1) if len(joint) else None
            Vl, Fl = _band_mesh(P[::-1].copy(), True, 0.12, 0.005, skip_edges=skip_l)
            if len(Fl):
                world_add(world, Vl, Fl, 9, _LINE_COLOR, name="line:%s" % el.get("kind", ""))
        if el.get("kind") == "slope" and "profile" in el:
            Vr, Fr = _ramp_mesh(el)
            world_add(world, Vr, Fr, 0, _RAMP_COLOR, name="ramp")
        for sl in _seq(el, "stop_lines"):
            a, b = np.asarray(sl, np.float64)
            d = b - a
            L = np.hypot(*d)
            if L > 1e-9:
                nrm = np.array([-d[1], d[0]]) / L * 0.45
                Vs = np.array([[*a, 0.006], [*b, 0.006], [*(b + nrm), 0.006], [*(a + nrm), 0.006]])
                world_add(world, Vs, np.array([[0, 1, 2], [0, 2, 3]]), 9, _LINE_COLOR, name="stop_line")
        cw = float(el.get("crosswalk_width", 4.0))
        for cwl in _seq(el, "crosswalks"):                       # 横断歩道(道路標示 201): 白の縞 0.45 m・間隔 0.45 m、帯の幅 cw
            a, b = np.asarray(cwl, np.float64)
            d = b - a
            L = np.hypot(*d)
            if L > 1e-9:
                u = d / L                                            # 帯を横切る向き(縞はこの向きに並ぶ)
                nrm = np.array([-u[1], u[0]])                        # 帯の幅の向き(= 車の進行方向)
                pos = 0.0
                while pos + 0.45 <= L + 1e-9:
                    p0 = a + u * pos
                    p1 = a + u * (pos + 0.45)
                    Vs = np.array([[*(p0 - nrm * cw / 2), 0.006], [*(p1 - nrm * cw / 2), 0.006],
                                   [*(p1 + nrm * cw / 2), 0.006], [*(p0 + nrm * cw / 2), 0.006]])
                    world_add(world, Vs, np.array([[0, 1, 2], [0, 2, 3]]), 12, _LINE_COLOR, name="crosswalk")
                    pos += 0.9
        for sp in _seq(el, "signal_poses"):
            # 日本式の信号機(roadjp、2026-09-30): 柱は流入路から見て交差点の向こう側の左の角、アームで流入車線の上へ、横型 3 灯(左から青黄赤)。
            # signal_poses の yaw は「灯器が向く向き」(流入方向 + π)なので、add_signal_jp の「進入車の進行方向」には yaw + π を渡す。
            # アーム長 = 柱(車線の左端から 0.5 m 外)から流入車線の中心まで。
            import roadjp
            hw = 0.5 * float(el.get("width", 7.0))
            roadjp.add_signal_jp(world, float(sp[0]), float(sp[1]), float(sp[2]) + np.pi, state="red",
                                 arm=min(3.5, max(1.5, (hw + 0.5) - 0.5 * hw)))
        for r in _seq(el, "rails"):
            a, b = np.asarray(r, np.float64)
            d = b - a
            L = np.hypot(*d)
            if L > 1e-9:
                nrm = np.array([-d[1], d[0]]) / L * 0.07
                Vr = np.array([[*(a - nrm), 0.0], [*(b - nrm), 0.0], [*(b + nrm), 0.0], [*(a + nrm), 0.0],
                               [*(a - nrm), 0.03], [*(b - nrm), 0.03], [*(b + nrm), 0.03], [*(a + nrm), 0.03]])
                Fr = np.array([[4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6]])
                world_add(world, Vr, Fr, 8, (0.45, 0.42, 0.40), name="rail")
    for p in props:
        name, x, y, yaw = p[0], float(p[1]), float(p[2]), float(p[3])
        dims = p[4] if len(p) > 4 else None
        paint = p[5] if len(p) > 5 else None
        add_asset(world, name, x, y, yaw, dims=dims, asset_root=asset_root, paint=paint)
    return world


def add_asset(world: dict, name: str, x: float, y: float, yaw: float, *, dims=None, z: float = 0.0,
              asset_root=None, paint=None) -> int:
    """資産(車・コーン・標識 …)を姿勢に置いて世界に足す。``paint`` = 車の車体色(:func:`load_asset` と同じ)。"""
    m = load_asset(name, dims, root=asset_root, paint=paint)
    return world_add(world, place_mesh(m["V"], x, y, yaw, z), m["F"], m["label"], m["color"],
                     name=name, pose=(x, y, yaw), extra={"dims": tuple(float(v) for v in m["dims"])})


def add_signal(world: dict, x: float, y: float, yaw: float, *, state: str = "red", height: float = 5.0,
               asset_root=None) -> int:
    """信号機を立てる: Kenney の柱 + 灯火 3 つ(自前の円盤、面ラベル 3)。灯火の色は state で決まる。

    灯火は yaw の向き(進入する車から見える向き)を向いた面。objects[i]["lamp_faces"] = {"red": (f0,f1), …}。"""
    if state not in ("red", "yellow", "green", "off"):
        raise ValueError("state は red / yellow / green / off")
    d0 = ASSETS["traffic_light"][2]
    m = load_asset("traffic_light", (d0[0] * height / d0[2], d0[1] * height / d0[2], height), root=asset_root)
    i = world_add(world, place_mesh(m["V"], x, y, yaw), m["F"], 3, m["color"], name="traffic_light",
                  pose=(x, y, yaw), extra={"state": state, "lamp_faces": {}})
    # 灯火: 頭(+x に張り出す箱)の前面のすぐ外に 3 つの円盤を縦に並べる。法線は yaw の向き(進入車の方を向く)
    c, s = np.cos(yaw), np.sin(yaw)
    fwd = np.array([c, s, 0.0])
    left = np.array([-s, c, 0.0])
    head = m["V"][m["V"][:, 2] > 0.7 * height]
    x_front = float(head[:, 0].max()) + 0.02                               # 頭の前面(資産の x の最大)の 2 cm 外
    z_top = float(head[:, 2].max())
    r = 0.15
    n_seg = 12
    ang = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)
    for kind, dz in (("red", -0.20), ("yellow", -0.55), ("green", -0.90)):
        centre = np.array([x, y, z_top + dz]) + fwd * x_front
        # 円盤の頂点(左 × 上の平面に円を描く)
        Vd = [centre] + [centre + left * (r * np.cos(a)) + np.array([0, 0, r * np.sin(a)]) for a in ang]
        Fd = [[0, 1 + k, 1 + (k + 1) % n_seg] for k in range(n_seg)]
        Vd, Fd = np.asarray(Vd, np.float64), np.asarray(Fd, np.int64)
        col = _LAMP[kind] if kind == state else _LAMP["off"]
        j = world_add(world, Vd, Fd, 3, col, name="lamp:%s" % kind, pose=(x, y, yaw))
        world["objects"][i]["lamp_faces"][kind] = world["objects"][j]["faces"]
    return i


def set_signal_state(world: dict, i: int, state: str) -> None:
    """信号機 i の灯火の色を state に(面の色だけ書き換える。幾何は不変)。"""
    if state not in ("red", "yellow", "green", "off"):
        raise ValueError("state は red / yellow / green / off")
    obj = world["objects"][i]
    if obj.get("name") != "traffic_light" or "lamp_faces" not in obj:
        raise ValueError("objects[%d] は信号機でない" % i)
    for kind, (f0, f1) in obj["lamp_faces"].items():
        world["face_color"][f0:f1] = _LAMP[kind] if kind == state else _LAMP["off"]
    obj["state"] = state


def world_move(world: dict, i: int, x: float, y: float, yaw: float, z: float = 0.0) -> None:
    """物体 i(資産で置いたもの)を新しい姿勢 (x, y, yaw) へ動かす(頂点だけ書き換える。面・ラベル・色は不変)。

    対向車を 1 コマずつ進める(15 巡目の TTC)ための op。資産でない物体(縁石・路面・信号機)は ``ValueError``。
    姿勢の意味は :func:`add_asset` と同じ(資産の原点 = 箱の底面中心、yaw は +x から反時計回り)。"""
    obj = world["objects"][i]
    if "dims" not in obj or obj.get("pose") is None:
        raise ValueError("objects[%d] は資産で置いた物体でない(動かせるのは add_asset / props の物体だけ)" % i)
    v0, v1 = obj["verts"]
    x0, y0, yaw0 = obj["pose"]
    c0, s0 = np.cos(-yaw0), np.sin(-yaw0)
    V = world["V"][v0:v1] - np.array([x0, y0, 0.0])                    # 元の姿勢を外して原点へ
    V = V @ np.array([[c0, -s0, 0.0], [s0, c0, 0.0], [0.0, 0.0, 1.0]]).T
    z0 = float(obj.get("z", 0.0))
    V[:, 2] -= z0
    world["V"][v0:v1] = place_mesh(V, float(x), float(y), float(yaw), float(z))
    obj["pose"] = (float(x), float(y), float(yaw))
    obj["z"] = float(z)


# ─────────────────────────────── カメラ ───────────────────────────────────

def camera_pose(eye, target, up=(0.0, 0.0, 1.0)) -> np.ndarray:
    """render3d.look_at の薄い包み(world → camera の 4×4)。"""
    import render3d
    return render3d.look_at(np.asarray(eye, np.float64), np.asarray(target, np.float64), up)


def camera_intrinsics(fov_deg: float, width: int, height: int) -> np.ndarray:
    import render3d
    return render3d.intrinsics_from_fov(float(fov_deg), int(width), int(height))


def world_project_points(points, pose, K):
    """世界の点 (N,3) をカメラ(pose = world→camera 4×4、K 3×3)の画素へ: ``(col, row, depth)`` 各 (N,)。

    render3d と同じ規約(カメラは −Z を見る、行は上が小さい、画素中心は整数座標)。depth ≤ 0 は背後。"""
    P = np.asarray(points, np.float64).reshape(-1, 3)
    pose = np.asarray(pose, np.float64)
    K = np.asarray(K, np.float64)
    Pc = P @ pose[:3, :3].T + pose[:3, 3]
    depth = -Pc[:, 2]
    safe = np.where(depth > 1e-9, depth, np.nan)
    col = K[0, 0] * (Pc[:, 0] / safe) + K[0, 2]
    row = K[1, 2] - K[1, 1] * (Pc[:, 1] / safe)
    return col, row, depth


def overlay_points(image, points, pose, K, colors, *, radius: int = 1, depth_test=None, tol: float = 0.15):
    """カメラ画像 (H,W,3) に世界の点を色つきで打つ(LiDAR の点を車載カメラに重ねる図)。

    ``depth_test`` に :func:`world_camera` の ``depth`` を渡すと、面の深度より ``tol`` (相対) 以上奥の点
    (別の面に隠れている点)は描かない。返り値は新しい配列。"""
    img = np.array(image, np.float64, copy=True)
    H, W = img.shape[:2]
    col, row, depth = world_project_points(points, pose, K)
    C = np.asarray(colors, np.float64)
    if C.ndim == 1:
        C = np.broadcast_to(C, (len(col), 3))
    ok = np.isfinite(col) & np.isfinite(row) & (depth > 0)
    c = np.rint(np.where(ok, col, -1e9)).astype(np.int64)     # 背後(NaN)は範囲外の整数にして落とす
    r = np.rint(np.where(ok, row, -1e9)).astype(np.int64)
    ok &= (c >= -radius) & (c < W + radius) & (r >= -radius) & (r < H + radius)
    if depth_test is not None:
        dt = np.asarray(depth_test, np.float64)
        cc = np.clip(c, 0, W - 1)
        rr = np.clip(r, 0, H - 1)
        ok &= depth <= dt[rr, cc] * (1.0 + tol) + 1e-6
    order = np.argsort(-depth[ok])                 # 遠い点から打つ(近い点が上に来る)
    cs, rs, Cs = c[ok][order], r[ok][order], C[ok][order]
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            x = cs + dx
            y = rs + dy
            m = (x >= 0) & (x < W) & (y >= 0) & (y < H)
            img[y[m], x[m]] = Cs[m]
    return np.clip(img, 0, 1)


def world_camera(world: dict, pose, K, width: int = 640, height: int = 400, *, light=(0.3, -0.5, 0.8),
                 ambient: float = 0.35, sky=(0.62, 0.75, 0.92), ego=None) -> dict:
    """世界をカメラで撮る: ``{"color" (H,W,3), "label" (H,W) int(−1 = 空), "depth" (H,W), "face" (H,W), "shade" (H,W)}``。

    render3d.render_mesh(attributes=True) の三角形 id から面の色・ラベルを引き、色は Lambert
    (``ambient + (1−ambient)·max(n·l, 0)``、n は render3d のカメラ系法線を世界系に戻さず、光をカメラ系で与える)。
    ``ego=(V, F, color)`` を渡すと自車のメッシュも一緒に描く(世界には足さない)。"""
    import render3d
    V, F, C, Lb = world["V"], world["F"], world["face_color"], world["face_label"]
    if ego is not None:
        Ve, Fe, Ce = ego
        F = np.vstack([F, np.asarray(Fe, np.int64) + len(V)])
        V = np.vstack([V, np.asarray(Ve, np.float64)])
        C = np.vstack([C, np.asarray(Ce, np.float64)])
        Lb = np.concatenate([Lb, np.full(len(Fe), 2, np.int64)])
    import warnings
    with warnings.catch_warnings():
        # render3d はカメラの背後の三角形を NaN の箱で落とす(意図した挙動)。その nanmin の警告は情報でない。
        warnings.simplefilter("ignore", RuntimeWarning)
        out = render3d.render_mesh(V, F, pose=np.asarray(pose, np.float64), intrinsics=np.asarray(K, np.float64),
                                   width=int(width), height=int(height), attributes=True)
    face = np.asarray(out["face"])
    hit = face >= 0
    n = out["normals"]
    l = np.asarray(light, np.float64)
    l = l / np.linalg.norm(l)
    shade = ambient + (1.0 - ambient) * np.clip(np.abs(n @ l), 0.0, 1.0)
    color = np.empty((height, width, 3), np.float64)
    color[:] = np.asarray(sky, np.float64)
    color[hit] = C[face[hit]] * shade[hit][:, None]
    label = np.full((height, width), -1, np.int64)
    label[hit] = Lb[face[hit]]
    depth = np.asarray(out["depth"], np.float64)
    # "shade" = Lambert の明るさ(材質を画素ごとに掛け直す driveterrain.world_materials が使う)
    return {"color": np.clip(color, 0, 1), "label": label, "depth": depth, "face": face, "shade": shade}
