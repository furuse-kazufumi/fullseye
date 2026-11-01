# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実機 RGB-D から産業部品の 6 自由度姿勢を出す —— BOP T-LESS。

PrimeSense Carmine 1.09 で撮影された T-LESS の BOP19 test subset を、Fullseye
の既存 op だけで ``depth_to_points -> estimate_normals -> fit_plane_ransac ->
euclidean_clusters -> ppf_model/surface_match`` と通し、公開真値で採点する。
scene 1/image 157(4 個が分離)と scene 8/image 263(6 個、接触・遮蔽あり)を固定し、
``scene_gt_info.json`` の ``visib_fract < 0.5`` は「見えている面が半分未満」として
除外する。この固定 subset は公式 leaderboard 全体と同じ標本ではないため、表では
必ず ``PoC subset`` と明記する。

姿勢誤差(Hodaň et al., BOP Challenge 2020)を自前で計算する。モデル点集合 ``V``、
推定姿勢 ``P_e=(R_e,t_e)``、真値 ``P_g``、物体の対称変換集合 ``S`` に対して::

    MSSD = min_{S in S} max_{x in V} ||P_e x - P_g S x||_2
    MSPD = min_{S in S} max_{x in V} ||proj(P_e x) - proj(P_g S x)||_2
    ADD-S = mean_{x in V} min_{y in V} ||P_e x - P_g y||_2

``models_info.json`` の ``symmetries_discrete`` をそのまま使い、
``symmetries_continuous`` は軸回りを 5 度間隔で離散化する。AR_MSSD は
0.05d..0.50d、AR_MSPD は 5..50 px の 10 閾値における recall の平均。VSD を
実装していないので PoC の公式 AR(3 指標平均)は出さず、公開 leaderboard の AR と
混同しない。回転・並進の生誤差は MSSD を最小にした対称代表で報告する。

比較する公開値(BOP の T-LESS / model-based 6D localization of seen objects):
``Drost-CVPR10-3D-Only`` AR 0.444 / AR_MSSD 0.478 / AR_MSPD 0.480、
``Vidal-Sensors18`` 0.538 / 0.575 / 0.574。PoC が負ける条件を、ICP の有無、
法線の向き、接触クラスタ、遮蔽、深度欠損に分けて数える。

データとライセンス
--------------------
T-LESS は CC BY 4.0。一次配布ページ https://bop.felk.cvut.cz/datasets/ の
T-LESS 欄に ``license: CC BY 4.0`` と明記される。取得は
``py -3.11 tools/fetch_tless.py``。データは repo 外に置き、既定は
``C:/dev/data/realdata/tless``、``FULLSEYE_TLESS_DATA`` で上書きできる。

引用: Hodaň et al., "T-LESS: An RGB-D Dataset for 6D Pose Estimation of
Texture-less Objects", WACV 2017, https://doi.org/10.1109/WACV.2017.8 。
指標: Hodaň et al., "BOP Challenge 2020 on 6D Object Localization",
ECCVW 2020, https://doi.org/10.1007/978-3-030-68223-0_12 。

CI にデータが無いときはダウンロードせず、実行記録 ``RECORDED`` を表示する。
図は ``FULLSEYE_FIGURE_DIR`` があるときだけ書く。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
from match3d import render_point_depth                            # noqa: E402


DATA_ENV = "FULLSEYE_TLESS_DATA"
DEFAULT_DATA = Path("C:/dev/data/realdata/tless")
SCENES = ((1, 157, "分離"), (8, 263, "接触・遮蔽"))
VISIBILITY_MIN = 0.50
ROI = (70, 435, 65, 575)       # marker frame/background only; no GT boxes
DEPTH_RANGE_MM = (500.0, 1200.0)
VOXEL_MM = 4.0
CLUSTER_TOL_MM = 8.0
MODEL_POINTS = 180
SCENE_POINTS = 160

LEADERBOARD = {
    "Drost-CVPR10-3D-Only": {"ar": 0.444, "mssd": 0.478, "mspd": 0.480},
    "Vidal-Sensors18": {"ar": 0.538, "mssd": 0.575, "mspd": 0.574},
}

# 2026-11-01, Python 3.11, archives pinned by tools/fetch_tless.py.
# Updated only from the stdout of this script, never from a caption or hand calculation.
RECORDED = {
    "instances": 10,
    "scenes": 2,
    "ar_mssd": 0.290,
    "ar_mspd": 0.320,
    "synthetic_ar_mssd": 0.880,
    "synthetic_ar_mspd": 0.880,
    "no_icp_ar_mssd": 0.280,
    "raw_normals_ar_mssd": 0.200,
    "scene_1_depth_missing_px": 3678,
    "scene_8_depth_missing_px": 3204,
    "mssd_failure_gt_0_2d": 6,
}


def _json(path: Path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"BOP JSON を読めない: {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"BOP JSON の root は object でなければならない: {path.name}")
    return value


def _ply_vertices_normals(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """T-LESS ASCII PLY の vertex xyz/nxyz だけを fail-closed で読む。"""
    try:
        with path.open("r", encoding="ascii", newline="") as handle:
            header = []
            while True:
                line = handle.readline()
                if not line:
                    raise ValueError("end_header が無い")
                header.append(line.strip())
                if line.strip() == "end_header":
                    break
            if "format ascii 1.0" not in header:
                raise ValueError("この PoC は T-LESS の ASCII PLY だけを受ける")
            rows = [x for x in header if x.startswith("element vertex ")]
            if len(rows) != 1:
                raise ValueError("element vertex が一意でない")
            count = int(rows[0].split()[2])
            properties = [x.split()[-1] for x in header if x.startswith("property ")]
            if properties[:6] != ["x", "y", "z", "nx", "ny", "nz"]:
                raise ValueError(f"先頭 property が xyz/nxyz でない: {properties[:6]}")
            data = np.loadtxt(handle, dtype=np.float64, max_rows=count)
    except OSError as exc:
        raise ValueError(f"PLY を読めない: {path.name}: {exc}") from exc
    if data.ndim != 2 or data.shape[0] != count or data.shape[1] < 6:
        raise ValueError(f"PLY vertex 数/列が header と不一致: {data.shape}, expected {count}")
    points, normals = data[:, :3], data[:, 3:6]
    lengths = np.linalg.norm(normals, axis=1)
    if not np.isfinite(points).all() or not np.isfinite(normals).all() or np.any(lengths < 1e-8):
        raise ValueError(f"PLY vertex/normal に非有限または零法線: {path.name}")
    return points, normals / lengths[:, None]


def _cap(points: np.ndarray, normals: np.ndarray, count: int):
    if len(points) <= count:
        return points, normals
    # PLY/cluster orderだけに依存する決定的な一様抽出。乱数で条件を選ばない。
    idx = np.linspace(0, len(points) - 1, count, dtype=np.int64)
    return points[idx], normals[idx]


def _rotation(axis, angle):
    axis = np.asarray(axis, np.float64)
    axis /= np.linalg.norm(axis)
    x, y, z = axis
    K = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]], np.float64)
    return np.eye(3) + np.sin(angle) * K + (1.0 - np.cos(angle)) * (K @ K)


def symmetry_transforms(model_info: dict, step_deg: float = 5.0):
    """BOP model_info の離散/連続対称性を (R,t) 列へ展開する。"""
    base = [(np.eye(3), np.zeros(3))]
    for flat in model_info.get("symmetries_discrete", []):
        matrix = np.asarray(flat, np.float64)
        if matrix.size != 16:
            raise ValueError("symmetries_discrete は 4x4(flat 16) でなければならない")
        matrix = matrix.reshape(4, 4)
        base.append((matrix[:3, :3], matrix[:3, 3]))
    continuous = model_info.get("symmetries_continuous", [])
    if not continuous:
        return base
    out = []
    for R0, t0 in base:
        partial = [(R0, t0)]
        for item in continuous:
            axis = np.asarray(item["axis"], np.float64)
            offset = np.asarray(item["offset"], np.float64)
            expanded = []
            for Ra, ta in partial:
                for degree in np.arange(0.0, 360.0, step_deg):
                    Rc = _rotation(axis, np.radians(degree))
                    tc = offset - Rc @ offset
                    expanded.append((Ra @ Rc, Ra @ tc + ta))
            partial = expanded
        out.extend(partial)
    return out


def pose_metrics(model_points, R_est, t_est, R_gt, t_gt, K, symmetries):
    """MSSD/MSPD/ADD-S と MSSD-best の回転・並進誤差を返す。"""
    V = np.asarray(model_points, np.float64)
    est = V @ R_est.T + t_est
    uv_est, _ = fs.project_points(est, K)
    candidates = []
    for Rs, ts in symmetries:
        Rgs = R_gt @ Rs
        tgs = R_gt @ ts + t_gt
        truth = V @ Rgs.T + tgs
        mssd = float(np.linalg.norm(est - truth, axis=1).max())
        uv_truth, _ = fs.project_points(truth, K)
        mspd = float(np.linalg.norm(uv_est - uv_truth, axis=1).max())
        delta = R_est @ Rgs.T
        angle = float(np.degrees(np.arccos(np.clip((np.trace(delta) - 1.0) / 2.0, -1, 1))))
        translation = float(np.linalg.norm(t_est - tgs))
        candidates.append((mssd, mspd, angle, translation))
    best_mssd = min(candidates, key=lambda row: row[0])
    mspd = min(row[1] for row in candidates)
    add_s = float(cKDTree(V @ R_gt.T + t_gt).query(est, k=1)[0].mean())
    return {"mssd": best_mssd[0], "mspd": mspd, "add_s": add_s,
            "rot_deg": best_mssd[2], "trans_mm": best_mssd[3]}


def average_recall(rows):
    mssd = []
    mspd = []
    for fraction, pixels in zip(np.arange(0.05, 0.51, 0.05), np.arange(5.0, 51.0, 5.0)):
        mssd.append(np.mean([r["mssd"] <= fraction * r["diameter"] for r in rows]))
        mspd.append(np.mean([r["mspd"] <= pixels for r in rows]))
    return float(np.mean(mssd)), float(np.mean(mspd))


def _flying_pixels(depth_mm: np.ndarray) -> int:
    """4 近傍のうち3点以上と >30 mm 離れる孤立深度を数える。"""
    z = np.asarray(depth_mm, np.float64)
    valid = np.isfinite(z) & (z > 0)
    count = np.zeros(z.shape, np.int8)
    far = np.zeros(z.shape, np.int8)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        shifted = np.roll(z, (dy, dx), axis=(0, 1))
        ok = valid & np.roll(valid, (dy, dx), axis=(0, 1))
        if dy == -1: ok[-1] = False
        if dy == 1: ok[0] = False
        if dx == -1: ok[:, -1] = False
        if dx == 1: ok[:, 0] = False
        count += ok
        far += ok & (np.abs(z - shifted) > 30.0)
    return int(((count >= 3) & (far >= 3)).sum())


def load_scene(root: Path, scene_id: int, image_id: int, label: str):
    scene = root / "test_primesense" / f"{scene_id:06d}"
    key = str(image_id)
    camera = _json(scene / "scene_camera.json")
    ground_truth = _json(scene / "scene_gt.json")
    ground_info = _json(scene / "scene_gt_info.json")
    if key not in camera or key not in ground_truth or key not in ground_info:
        raise ValueError(f"scene {scene_id} image {image_id}: camera/gt/info の key が揃わない")
    cam = camera[key]
    K = np.asarray(cam.get("cam_K"), np.float64)
    if K.size != 9 or not np.isfinite(K).all():
        raise ValueError("cam_K は有限な 3x3 でなければならない")
    K = K.reshape(3, 3)
    scale = float(cam.get("depth_scale", np.nan))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("depth_scale は有限な正数でなければならない")
    rgb = np.asarray(Image.open(scene / "rgb" / f"{image_id:06d}.png").convert("RGB"))
    raw = np.asarray(Image.open(scene / "depth" / f"{image_id:06d}.png"))
    if raw.ndim != 2 or raw.dtype.kind not in "ui" or rgb.shape[:2] != raw.shape:
        raise ValueError(f"RGB/depth の shape/dtype が BOP 契約外: {rgb.shape}, {raw.shape}, {raw.dtype}")
    gt, info = ground_truth[key], ground_info[key]
    if not isinstance(gt, list) or not isinstance(info, list) or len(gt) != len(info):
        raise ValueError("scene_gt と scene_gt_info の instance 数が違う")
    return {"scene": scene_id, "image": image_id, "label": label, "dir": scene,
            "K": K, "scale": scale, "rgb": rgb, "raw": raw, "gt": gt, "info": info}


def prepare_scene(record):
    raw = record["raw"]
    depth = raw.astype(np.float64) * record["scale"]
    zeros = int((raw == 0).sum())
    flying = _flying_pixels(np.where(raw > 0, depth, np.nan))
    valid_depth = np.where(raw > 0, depth, np.nan)
    y0, y1, x0, x1 = ROI
    work = valid_depth.copy()
    mask = np.zeros(work.shape, bool); mask[y0:y1, x0:x1] = True
    work[~mask] = np.nan
    work[(work < DEPTH_RANGE_MM[0]) | (work > DEPTH_RANGE_MM[1])] = np.nan
    dense = fs.depth_to_points(work, record["K"])
    cloud = fs.voxel_downsample(dense, voxel=VOXEL_MM)
    plane, ground = fs.fit_plane_ransac(cloud, thresh=4.0, iters=300, seed=0)
    if plane[2] < 0:
        plane = -plane
    signed = cloud @ plane[:3] + plane[3]
    objects = cloud[(~ground) & (signed < -5.0)]
    clusters = fs.euclidean_clusters(objects, tol=CLUSTER_TOL_MM, min_size=20,
                                      max_size=5000, method="low_memory")
    centroids = np.asarray([objects[index].mean(0) for index in clusters])
    # OBB は配置推定には使わず、分割結果の寸法を真値に依存せず監査するために残す。
    # fs.obb は大点群で重いため、各 cluster を決定的に最大500点へ間引く。
    boxes = []
    for index in clusters:
        points = objects[index]
        sample = points[np.linspace(0, len(points) - 1,
                                    min(500, len(points)), dtype=np.int64)]
        boxes.append(fs.obb(sample))
    return {**record, "depth": valid_depth, "zeros": zeros, "flying": flying,
            "dense_count": len(dense), "cloud_count": len(cloud), "plane": plane,
            "ground_count": int(ground.sum()), "objects": objects,
            "clusters": clusters, "centroids": centroids, "boxes": boxes}


def _match_one(root, scene, instance, cluster_index, model_info, *, seed):
    obj_id = int(instance["obj_id"])
    model_full, normal_full = _ply_vertices_normals(
        root / "models_reconst" / f"obj_{obj_id:06d}.ply")
    model, model_normals = _cap(model_full, normal_full, MODEL_POINTS)
    cluster = scene["objects"][scene["clusters"][cluster_index]]
    cluster = fs.voxel_downsample(cluster, voxel=6.0)
    oriented = fs.estimate_normals(cluster, k=12, viewpoint=np.zeros(3))
    scene_points, oriented = _cap(cluster, oriented, SCENE_POINTS)
    raw_normals = fs.estimate_normals(scene_points, k=12)
    descriptor = fs.ppf_model(model, model_normals, angle_bins=24)
    main = fs.surface_match(descriptor, scene_points, oriented, ref_fraction=0.25,
                            topk=8, refine=True, seed=seed)
    no_icp = fs.surface_match(descriptor, scene_points, oriented, ref_fraction=0.25,
                              topk=8, refine=False, seed=seed)
    raw_normal = fs.surface_match(descriptor, scene_points, raw_normals, ref_fraction=0.25,
                                  topk=8, refine=True, seed=seed)
    R_gt = np.asarray(instance["cam_R_m2c"], np.float64).reshape(3, 3)
    t_gt = np.asarray(instance["cam_t_m2c"], np.float64)
    eval_points, _ = _ply_vertices_normals(root / "models_cad" / f"obj_{obj_id:06d}.ply")
    eval_points = eval_points[np.linspace(0, len(eval_points) - 1,
                                          min(600, len(eval_points)), dtype=np.int64)]
    syms = symmetry_transforms(model_info)
    def score(pose):
        return pose_metrics(eval_points, pose["R"], pose["t"], R_gt, t_gt, scene["K"], syms)
    metrics = score(main)
    metrics_no_icp = score(no_icp)
    metrics_raw_normal = score(raw_normal)

    # Ideal point-depth projection: same camera/pose/model, no sensor noise or missing returns.
    synth_depth = render_point_depth(model_full, scene["K"], scene["raw"].shape,
                                     R=R_gt, t=t_gt)
    synth_points = fs.depth_to_points(synth_depth, scene["K"])
    synth_points = fs.voxel_downsample(synth_points, voxel=6.0)
    synth_normals = fs.estimate_normals(synth_points, k=12, viewpoint=np.zeros(3))
    synth_points, synth_normals = _cap(synth_points, synth_normals, SCENE_POINTS)
    synth_pose = fs.surface_match(descriptor, synth_points, synth_normals,
                                  ref_fraction=0.25, topk=8, refine=True, seed=seed)
    synth_metrics = score(synth_pose)
    return {"pose": main, "metrics": metrics, "no_icp": metrics_no_icp,
            "raw_normal": metrics_raw_normal, "synth": synth_metrics,
            "eval_points": eval_points, "R_gt": R_gt, "t_gt": t_gt,
            "model_points": model_full}


def run_real(root: Path):
    model_infos = _json(root / "models_reconst" / "models_info.json")
    scenes = [prepare_scene(load_scene(root, *spec)) for spec in SCENES]
    rows = []
    seed = 0
    for scene in scenes:
        if len(scene["clusters"]) == 0:
            raise RuntimeError(f"scene {scene['scene']}: 平面除去後の cluster が 0")
        assigned = []
        for index, (instance, info) in enumerate(zip(scene["gt"], scene["info"])):
            visibility = float(info.get("visib_fract", -1.0))
            if not 0.0 <= visibility <= 1.0:
                raise ValueError("visib_fract は [0,1] でなければならない")
            if visibility < VISIBILITY_MIN:
                continue
            t_gt = np.asarray(instance["cam_t_m2c"], np.float64)
            distances = np.linalg.norm(scene["centroids"] - t_gt, axis=1)
            cluster_index = int(np.argmin(distances))
            assigned.append(cluster_index)
            obj_id = int(instance["obj_id"])
            result = _match_one(root, scene, instance, cluster_index,
                                model_infos[str(obj_id)], seed=seed)
            mask_path = scene["dir"] / "mask_visib" / f"{scene['image']:06d}_{index:06d}.png"
            visible_mask = np.asarray(Image.open(mask_path)) > 0
            missing = float(np.mean(scene["raw"][visible_mask] == 0)) if visible_mask.any() else 1.0
            size = model_infos[str(obj_id)]
            thin = float(size["size_z"]) / float(size["diameter"]) < 0.45
            row = {"scene": scene["scene"], "image": scene["image"], "condition": scene["label"],
                   "obj_id": obj_id, "visibility": visibility, "cluster": cluster_index,
                   "cluster_distance": float(distances[cluster_index]), "missing": missing,
                   "thin": thin, "diameter": float(size["diameter"]), **result}
            rows.append(row)
            seed += 1
        counts = np.bincount(assigned, minlength=len(scene["clusters"]))
        for row in rows:
            if row["scene"] == scene["scene"]:
                row["merged"] = bool(counts[row["cluster"]] > 1)
    return scenes, rows


def _overlay(scene, rows):
    image = scene["rgb"].astype(np.float64) / 255.0
    for row in rows:
        if row["scene"] != scene["scene"]:
            continue
        sample = row["eval_points"][::max(1, len(row["eval_points"]) // 120)]
        est = sample @ row["pose"]["R"].T + row["pose"]["t"]
        truth = sample @ row["R_gt"].T + row["t_gt"]
        uv_est, ze = fs.project_points(est, scene["K"])
        uv_gt, zg = fs.project_points(truth, scene["K"])
        ok_e = ze > 0; ok_g = zg > 0
        image = np.asarray(fs.draw_markers(image, uv_gt[ok_g], color="right", size=2, shape="cross"))
        image = np.asarray(fs.draw_markers(image, uv_est[ok_e], color="wrong", size=2, shape="cross"))
    return image


def make_figures(scenes, rows, ar_real, ar_synth):
    if not figs.enabled():
        return
    # (b) is deliberately first: this is the representative figure.
    overlay = _overlay(scenes[0], rows)
    figs.save_grid("pose_overlay", [overlay],
                   ["推定=橙 / 公開真値=青"], title="T-LESS 実機深度の 6 自由度姿勢",
                   ncols=1, caption="scene 1/image 157。PPF+ICP の推定モデル(橙)と BOP 真値(青)。",
                   )
    depth = scenes[0]["depth"]
    figs.save_grid("rgb_depth", [scenes[0]["rgb"], np.nan_to_num(depth)],
                   ["実 RGB", "実機 depth [mm]"], title="PrimeSense Carmine 1.09 の実測入力",
                   ncols=2, gray=[False, False], colorbar=[False, True], unit=["", "mm"],
                   vrange=[None, (650, 950)],
                   caption=f"欠測 {scenes[0]['zeros']} px、孤立飛び候補 {scenes[0]['flying']} px。"
                           " BOP T-LESS, CC BY 4.0。")
    labels = np.arange(len(rows), dtype=float)
    recalls = [float(np.mean([row["metrics"]["mssd"] <= f * row["diameter"]
                              for f in np.arange(0.05, 0.51, 0.05)])) for row in rows]
    figs.save_plot("mssd_by_object", [("MSSD recall", labels, recalls)],
                   xlabel="対象 index(scene/object は表を参照)", ylabel="recall",
                   title="対象ごとの MSSD recall", kinds=["bar"], ylim=(0, 1.05),
                   caption="0.05d..0.50d の 10 閾値平均。接触クラスタで落ちる。")
    figs.save_plot("synthetic_vs_real",
                   [("合成", [0], [ar_synth[0]]), ("実機", [1], [ar_real[0]])],
                   xlabel="0=理想深度 / 1=実機深度", ylabel="AR_MSSD",
                   title="同じモデル・同じ姿勢: 合成から実機で落ちる量",
                   kinds=["bar", "bar"], colors=["right", "wrong"], ylim=(0, 1.0),
                   caption="理想 z-buffer 深度と PrimeSense 深度を同じ PPF+ICP で採点。")
    worst = max(rows, key=lambda row: row["metrics"]["mssd"] / row["diameter"])
    scene = next(item for item in scenes if item["scene"] == worst["scene"])
    fail = _overlay(scene, [worst])
    figs.save_grid("failure", [fail],
                   [f"scene {worst['scene']} / obj {worst['obj_id']} / vis {worst['visibility']:.2f}"],
                   title="失敗例: 接触・遮蔽でクラスタが対象と一致しない", ncols=1,
                   caption="橙=推定、青=真値。MSSD %.1f mm、cluster merged=%s。"
                           % (worst["metrics"]["mssd"], worst["merged"]))


def _print_recorded():
    print("BOP T-LESS 実データが無いためダウンロードせず、2026-11-01 の実行記録を表示")
    print(json.dumps(RECORDED, ensure_ascii=False, indent=2))
    print("\n再現: py -3.11 tools/fetch_tless.py && py -3.11 examples/poc_real_tless_6dof.py")
    print("\nPASS")


def main() -> None:
    root = Path(os.environ.get(DATA_ENV, DEFAULT_DATA))
    required = (root / "test_primesense", root / "models_reconst" / "models_info.json")
    if not all(path.exists() for path in required):
        _print_recorded()
        return
    start = time.perf_counter()
    scenes, rows = run_real(root)
    metrics = [{**row["metrics"], "diameter": row["diameter"]} for row in rows]
    no_icp = [{**row["no_icp"], "diameter": row["diameter"]} for row in rows]
    raw_normals = [{**row["raw_normal"], "diameter": row["diameter"]} for row in rows]
    synth = [{**row["synth"], "diameter": row["diameter"]} for row in rows]
    ar_real = average_recall(metrics)
    ar_no_icp = average_recall(no_icp)
    ar_raw = average_recall(raw_normals)
    ar_synth = average_recall(synth)

    print("BOP T-LESS (CC BY 4.0) 実機 6DoF PoC")
    print("  source https://bop.felk.cvut.cz/datasets/ / Hodaň et al. WACV 2017")
    for scene in scenes:
        eligible = sum(float(x["visib_fract"]) >= VISIBILITY_MIN for x in scene["info"])
        print("  scene %d image %d (%s): depth 欠測 %d / 飛び候補 %d px、"
              "点 %d -> voxel %d -> ground %d -> object %d、cluster %d / 真値対象 %d"
              % (scene["scene"], scene["image"], scene["label"], scene["zeros"],
                 scene["flying"], scene["dense_count"], scene["cloud_count"],
                 scene["ground_count"], len(scene["objects"]), len(scene["clusters"]), eligible))
        print("    cluster sizes:", [len(index) for index in scene["clusters"]])
        print("    cluster OBB full extents [mm]:",
              [np.round(2.0 * np.asarray(box["extents"]), 1).tolist()
               for box in scene["boxes"]])

    print("\n対象ごとの対称性考慮誤差")
    print(" scene obj vis cluster merged MSSD[mm] MSPD[px] ADD-S[mm] R[deg] t[mm]")
    for row in rows:
        m = row["metrics"]
        print(" %5d %3d %.3f %7d %6s %8.2f %8.2f %9.2f %6.1f %5.1f"
              % (row["scene"], row["obj_id"], row["visibility"], row["cluster"],
                 str(row["merged"]), m["mssd"], m["mspd"], m["add_s"],
                 m["rot_deg"], m["trans_mm"]))

    print("\n公開 leaderboard と同じ MSSD/MSPD 閾値の平均 recall")
    print(" method                         official AR  AR_MSSD  AR_MSPD")
    print(" Fullseye PPF+ICP (PoC subset)       n/a      %.3f    %.3f" % ar_real)
    for name, score in LEADERBOARD.items():
        print(" %-31s  %.3f      %.3f    %.3f" % (name, score["ar"], score["mssd"], score["mspd"]))
    print("  注: PoC は10 instance subset、公開値は公式全 test。VSD 未実装なので PoC AR は n/a。")

    print("\n合成 -> 実機 / 切り分け")
    print(" ideal depth      AR_MSSD %.3f / AR_MSPD %.3f" % ar_synth)
    print(" real + ICP       AR_MSSD %.3f / AR_MSPD %.3f" % ar_real)
    print(" real - ICP       AR_MSSD %.3f / AR_MSPD %.3f" % ar_no_icp)
    print(" real raw normals AR_MSSD %.3f / AR_MSPD %.3f" % ar_raw)
    print(" drop synth->real: MSSD %.3f / MSPD %.3f" % (ar_synth[0] - ar_real[0], ar_synth[1] - ar_real[1]))

    failures = [row for row in rows if row["metrics"]["mssd"] > 0.20 * row["diameter"]]
    breakdown = {
        "fail_total": len(failures),
        "cluster_merged": sum(row["merged"] for row in failures),
        "occluded_vis_lt_0.8": sum(row["visibility"] < 0.8 for row in failures),
        "thin_z_over_d_lt_0.45": sum(row["thin"] for row in failures),
        "depth_missing_gt_1pct": sum(row["missing"] > 0.01 for row in failures),
        "symmetric": sum(len(symmetry_transforms(_json(root / "models_reconst" / "models_info.json")[str(row["obj_id"])])) > 1 for row in failures),
    }
    print("\n失敗内訳(MSSD > 0.2d、重複カテゴリ):", json.dumps(breakdown, ensure_ascii=False))
    print("  対象:", [(row["scene"], row["obj_id"], round(row["visibility"], 3),
                       round(row["missing"] * 100, 2), row["merged"]) for row in failures])

    make_figures(scenes, rows, ar_real, ar_synth)
    if figs.errors():
        raise RuntimeError("図の書き出し失敗: " + "; ".join(figs.errors()))
    print("\n所要 %.2f 秒" % (time.perf_counter() - start))
    print("\nPASS")


if __name__ == "__main__":
    main()
