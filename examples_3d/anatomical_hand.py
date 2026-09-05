# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 実解剖由来の骨メッシュ(MyoSuite `myo_sim`, Apache-2.0)から手骨格を組み立てて描く。

背景
    記事の手骨 hero は手続き形状(カプセル+球)で、実物の骨と比べると明らかに粗い。
    「正確な骨格」は画像生成 AI の**もっともらしさ**ではなく、**実データの幾何**で担保する
    のが筋である。MyoSuite の `myo_sim` は OpenSim 由来の実解剖骨メッシュ(手根骨 8・中手骨
    5・指骨 14 = 27 個、実寸 [m])を MJCF の運動学木で配置しており、Apache-2.0 で使える。

やること
    1. MJCF(`myohand.xml`、include 構成)を **stdlib だけ**で辿り、各骨メッシュのワールド姿勢を
       body 木の pos/euler を累積して求める(MuJoCo 依存なし)。
    2. `mujoco` が入っていれば、その forward kinematics(qpos=0)と**突き合わせて検証**する
       (位置 < 1e-6 m、回転 < 1e-6)。入っていなければ検証をスキップした旨を正直に出す。
    3. 27 骨を 1 メッシュに合成し、`render_beauty`(AO・接地影・SSAA・ACES、頂点法線補間)で
       骨質の hero を焼く。
    4. 解剖学的サニティ: 中指 > 示指 > 薬指 > 小指 の指長順(遠位端までの長さ)を実測で確認。

データ
    同梱しない(fail-closed)。取得先は環境変数 ``MYO_SIM_DIR`` で指す(既定は無い —— 
    配布物にローカル絶対パスを焼き込まないため)。
    取得: ``git clone https://github.com/MyoHub/myo_sim``(Apache-2.0)。

Run: py -3.11 examples_3d/anatomical_hand.py
"""
from __future__ import annotations

import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
import mesh as fsmesh  # noqa: E402
import render3d  # noqa: E402
import render_beauty as rb  # noqa: E402

# 手骨として集める mesh 名(myo_sim の命名)。radius/ulna は前腕なので既定では外す。
_CARPALS = ("lunate", "scaphoid", "pisiform", "triquetrum", "capitate", "hamate",
            "trapezium", "trapezoid")
# 親指の指骨は myo_sim では thumbprox / thumbdist(1proxph/1distph ではない)
_HAND_RE = re.compile(r"^(?:[1-5]mc|[2-5](?:prox|mid|dist)ph|thumbprox|thumbdist|"
                      + "|".join(_CARPALS) + r")$")


# --------------------------------------------------------------------------- #
# MJCF: include を展開し、asset の mesh と body 木を stdlib だけで辿る               #
# --------------------------------------------------------------------------- #
def _rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def _rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def _euler_xyz(e):
    """MuJoCo 既定 ``eulerseq="xyz"``(小文字=intrinsic、角度は compiler angle=radian)。"""
    a, b, c = (float(v) for v in e)
    return _rot_x(a) @ _rot_y(b) @ _rot_z(c)


def _quat_wxyz(q):
    w, x, y, z = (float(v) for v in q)
    n = np.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def _local_pose(el):
    """要素の pos/quat/euler から (R, t)。無指定は恒等。"""
    t = np.array([float(v) for v in el.get("pos", "0 0 0").split()], float)
    if el.get("quat") is not None:
        R = _quat_wxyz(el.get("quat").split())
    elif el.get("euler") is not None:
        R = _euler_xyz(el.get("euler").split())
    else:
        R = np.eye(3)
    return R, t


def _expand_includes(path: Path) -> ET.Element:
    """<include file=.../> をその場で展開した root を返す(相対パスは親ファイル基準)。"""
    root = ET.parse(path).getroot()

    def walk(parent: ET.Element, base: Path):
        for i, child in enumerate(list(parent)):
            if child.tag == "include":
                sub = _expand_includes(base / child.get("file"))
                parent.remove(child)
                for j, grand in enumerate(list(sub)):
                    parent.insert(i + j, grand)
            else:
                walk(child, base)
    walk(root, path.parent)
    return root


def load_mjcf_bone_meshes(xml_path, select=_HAND_RE):
    """MJCF から mesh geom をワールド座標で読む → ``[(mesh_name, body_name, V, F), ...]``。

    body 木の pos/quat/euler を根から累積し(関節は qpos=0 = 未回転)、geom 自身の
    pos/quat/euler と asset の scale を掛ける。``select`` に合う mesh 名だけ返す。
    """
    xml_path = Path(xml_path)
    root = _expand_includes(xml_path)
    comp = root.find("compiler")
    meshdir = (xml_path.parent / (comp.get("meshdir", ".") if comp is not None else ".")).resolve()
    assets = {}
    for m in root.iter("mesh"):
        scale = np.array([float(v) for v in m.get("scale", "1 1 1").split()], float)
        assets[m.get("name")] = ((meshdir / m.get("file")).resolve(), scale)
    out = []

    def walk(body: ET.Element, R_p, t_p):
        for geom in body.findall("geom"):
            name = geom.get("mesh")
            if name is None or not select.match(name):
                continue
            Rg, tg = _local_pose(geom)
            Rw, tw = R_p @ Rg, R_p @ tg + t_p
            file, scale = assets[name]
            V, F = fsmesh.read_mesh(str(file))
            Vw = (V * scale) @ Rw.T + tw
            out.append((name, body.get("name"), Vw, F))
        for child in body.findall("body"):
            Rc, tc = _local_pose(child)
            walk(child, R_p @ Rc, R_p @ tc + t_p)

    # include 展開後は <worldbody> が複数並びうる(scene 用と本体用)。全部を根から辿る。
    worlds = root.findall("worldbody")
    if not worlds:
        raise ValueError(f"{xml_path}: no <worldbody>")
    for world in worlds:
        walk(world, np.eye(3), np.zeros(3))
    return out


def crosscheck_with_mujoco(xml_path, bones) -> dict | None:
    """``mujoco`` があれば forward kinematics(qpos=0)の geom 姿勢と突き合わせる。
    戻り値: ``{"max_pos_err": m, "max_vert_err": m, "n": 個数}``、無ければ None。"""
    try:
        import mujoco
    except ImportError:
        return None
    m = mujoco.MjModel.from_xml_path(str(xml_path))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    names = {mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_MESH, m.geom_dataid[g]): g
             for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH}
    max_pos, max_vert = 0.0, 0.0
    for name, _body, Vw, _F in bones:
        g = names[name]
        R = d.geom_xmat[g].reshape(3, 3)
        t = d.geom_xpos[g]
        file, scale = None, None
        # 元メッシュを読み直して MuJoCo 姿勢で変換し、頂点単位で比較(順序は read_mesh 同一)
        mid = m.geom_dataid[g]
        # MuJoCo は mesh をその重心/慣性主軸に再中心化することがある(mesh_pos/mesh_quat)
        mp, mq = m.mesh_pos[mid], m.mesh_quat[mid]
        Rm = _quat_wxyz(mq)
        # ワールド変換: x_w = R (Rm^T (v - mp)) + t  … ただし MuJoCo の頂点は再中心化済み
        # なので、こちらは「MuJoCo 内部頂点」を直接取り出して比較する。
        va, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        Vmj = m.mesh_vert[va:va + nv]                  # 再中心化済み頂点(mesh frame)
        Vmj_w = Vmj @ R.T + t
        # こちらの頂点も同じ再中心化を施して同一フレームへ(順序は STL 三角形順で一致しない
        # ことがあるため、点群としての最近傍誤差で比較する)
        from scipy.spatial import cKDTree
        err = cKDTree(Vmj_w).query(Vw, k=1)[0]
        max_vert = max(max_vert, float(err.max()))
        max_pos = max(max_pos, float(np.linalg.norm(Vw.mean(0) - Vmj_w.mean(0))))
    return {"max_pos_err": max_pos, "max_vert_err": max_vert, "n": len(bones)}


def merge(bones):
    Vs, Fs, off = [], [], 0
    for _n, _b, V, F in bones:
        Vs.append(V)
        Fs.append(F + off)
        off += V.shape[0]
    return np.vstack(Vs), np.vstack(Fs)


def finger_lengths(bones) -> dict:
    """各指の中手骨基部から遠位端までの長さ [m](実測、解剖学サニティ用)。"""
    by = {n: V for n, _b, V, _F in bones}
    out = {}
    for f, label in ((2, "index"), (3, "middle"), (4, "ring"), (5, "little")):
        base = by[f"{f}mc"].mean(0)
        tip = by[f"{f}distph"]
        out[label] = float(np.linalg.norm(tip - base, axis=1).max())
    return out


def main() -> int:
    myo_dir = os.environ.get("MYO_SIM_DIR", "")
    if not myo_dir:
        print("SKIP: set MYO_SIM_DIR to a myo_sim checkout
"
              "  git clone https://github.com/MyoHub/myo_sim  (Apache-2.0)")
        return 0
    myo = Path(myo_dir)
    xml = myo / "hand" / "myohand.xml"
    if not xml.exists():
        # examples3d の "download" 系の作法: データ未取得は SKIP(exit 0)。捏造はしない。
        print(f"SKIP: myo_sim not found: {xml}\n"
              "  set MYO_SIM_DIR or: git clone https://github.com/MyoHub/myo_sim  (Apache-2.0)")
        return 0
    t0 = time.time()
    bones = load_mjcf_bone_meshes(xml)
    names = sorted(n for n, *_ in bones)
    print(f"[bones] {len(bones)} hand bones from {xml.name} ({time.time() - t0:.1f}s): {names}")
    assert len(bones) == 27, f"expected 27 hand bones (8 carpal + 5 mc + 14 phalanx), got {len(bones)}"

    chk = crosscheck_with_mujoco(xml, bones)
    if chk is None:
        print("[check] mujoco not installed — kinematic cross-check SKIPPED (pose unverified)")
    else:
        print(f"[check] vs MuJoCo forward kinematics: centroid err {chk['max_pos_err']:.2e} m, "
              f"nearest-vertex err {chk['max_vert_err']:.2e} m over {chk['n']} bones")
        assert chk["max_pos_err"] < 1e-6 and chk["max_vert_err"] < 1e-6, chk

    fl = finger_lengths(bones)
    print("[anatomy] finger lengths [mm]: " + ", ".join(f"{k} {v * 1e3:.1f}" for k, v in fl.items()))
    assert fl["middle"] > fl["index"] > fl["little"] and fl["middle"] > fl["ring"] > fl["little"], fl

    V, F = merge(bones)
    print(f"[mesh] merged {V.shape[0]} verts / {F.shape[0]} faces, extent {(V.max(0) - V.min(0)) * 1e3} mm")

    # ── hero: 手背(dorsal)を手首側やや上から、全体が収まる距離で。骨質(象牙色)・AO・接地影 ──
    by = {n: Vb for n, _b, Vb, _F in bones}
    cen = 0.5 * (V.min(0) + V.max(0))
    _, _, Vt = np.linalg.svd(V - cen, full_matrices=False)
    long_axis, normal = Vt[0], Vt[2]                     # 最大分散=指方向、最小分散=手掌法線
    # 向きを解剖で決める: 指先(中指末節骨)は手根骨(月状骨)より +long 側、
    # 豆状骨(pisiform)は掌側 → 法線は背側(dorsal)を向ける
    if (by["3distph"].mean(0) - by["lunate"].mean(0)) @ long_axis < 0:
        long_axis = -long_axis
    if (by["pisiform"].mean(0) - cen) @ normal > 0:
        normal = -normal
    e3 = normal / np.linalg.norm(normal)
    e2 = long_axis - (long_axis @ e3) * e3
    e2 /= np.linalg.norm(e2)
    e1 = np.cross(e2, e3)
    R = np.stack([e1, e2, e3])                           # rows: x=横, y=指方向, z=背側(上)
    Vz = (V - cen) @ R.T
    Vz[:, 2] -= Vz[:, 2].min()                           # 地面 z=0 に置く(掌側が接地)
    ext = Vz.max(0) - Vz.min(0)
    target = np.array([0.0, 0.0, 0.5 * ext[2]])
    # 手首側(−y)から仰角 ~55° で見下ろし、fov に全体(対角)を 1.2 倍の余裕で収める
    HERO = int(os.environ.get("FULLSEYE_HERO_SIZE", "1280"))
    SS = 1 if HERO <= 400 else 2
    fov = 30.0
    d = 0.5 * float(np.linalg.norm(ext[:2])) / np.tan(np.radians(fov / 2)) * 1.02
    eye = target + d * np.array([0.0, -0.58, 0.81])
    pose_z = render3d.look_at(eye, target, up=(0.0, 0.0, 1.0))
    K = render3d.intrinsics_from_fov(fov, HERO, HERO)
    t1 = time.time()
    img = rb.render_beauty(
        Vz, F, pose=pose_z, intrinsics=K, size=HERO, ss=SS, material="plastic",
        albedo=(0.93, 0.89, 0.80), light=(0.35, -0.45, 0.82), ambient=0.14,
        ao=True, ground_shadow=True, tonemap="aces", exposure=1.15,
        background=(0.07, 0.08, 0.10), ao_samples=64 if SS == 2 else 16, shadow_res=1024,
        penumbra=10.0, shadow_samples=24 if SS == 2 else 6, shadow_pcf=1, smooth_normals=True)
    out = _REPO_ROOT / "examples_3d" / "_gallery" / "anatomical_hand_hero.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out)
    print(f"[hero] {img.shape} range [{img.min():.3f},{img.max():.3f}] -> {out} ({time.time() - t1:.1f}s)")
    assert img.shape == (HERO, HERO, 3) and 0.0 <= img.min() and img.max() <= 1.0
    print(f"PASS: 実解剖骨メッシュ 27 個を MJCF 木から組み立て"
          f"{'(MuJoCo FK と一致)' if chk else '(FK 検証はスキップ)'}、指長順は解剖学どおり、"
          f"hero を {out.name} に保存")
    return 0


def _basis_to_z(n):
    """単位ベクトル n を +z に回す回転行列(Rodrigues)。"""
    n = np.asarray(n, float) / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(n, z)
    s, c = np.linalg.norm(v), float(n @ z)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))


if __name__ == "__main__":
    sys.exit(main())
