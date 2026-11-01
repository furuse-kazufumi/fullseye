# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実機 RGB-D から産業部品の 6 自由度姿勢を出す —— BOP T-LESS。

PrimeSense Carmine 1.09 で撮影された T-LESS の BOP19 test subset を、Fullseye
の既存 op だけで ``depth_to_points -> estimate_normals -> fit_plane_ransac ->
euclidean_clusters -> ppf_model/surface_match`` と通し、公開真値で採点する。BOP19
test_primesense の全20場面から、各場面で画像IDが最小の1枚を決定的に選ぶ。
``scene_gt_info.json`` の ``visib_fract < 0.5`` は「見えている面が半分未満」として
除外し、残る全対象を採点する。この20画像 subset は公開 leaderboard の全画像と
同じ標本ではないため、表では必ず ``PoC 20-scene subset`` と明記する。

クラスタ分割への依存を切り分けるため、主経路に加えて、RANSAC 平面除去後の場面
点群全体へクラスタ分割せず ``surface_match`` する対照群も同じ対象で採点する。
180/160点から2000/2000点まで密度を掃引し、1対象10秒以内で AR_MSSD 最大だった
1000/1000点、voxel 2 mm、ref_fraction 0.25、angle_bins 24、ICP 100反復を採用した。
主経路は8.291秒/対象、AR_MSSD 0.197 / AR_MSPD 0.220。旧180/160点の
0.162/0.185は間引き条件を明記して比較表に残す。

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

from dataclasses import dataclass
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
SWEEP_ENV = "FULLSEYE_TLESS_SWEEP"
DEFAULT_DATA = Path("C:/dev/data/realdata/tless")
SCENE_IDS = tuple(range(1, 21))
VISIBILITY_MIN = 0.50
ROI = (70, 435, 65, 575)       # marker frame/background only; no GT boxes
DEPTH_RANGE_MM = (500.0, 1200.0)
VOXEL_MM = 4.0
CLUSTER_TOL_MM = 8.0
MODEL_POINTS = 1000
SCENE_POINTS = 1000


@dataclass(frozen=True)
class MatchConfig:
    """PPF の密度・投票・後段 ICP だけを一組にした掃引設定。"""

    name: str
    model_points: int
    scene_points: int
    voxel_mm: float
    ref_fraction: float = 0.25
    angle_bins: int = 24
    icp_passes: int = 1


SPARSE_CONFIG = MatchConfig("density_180_160_v6", 180, 160, 6.0)
ADOPTED_CONFIG = MatchConfig("adopted_1000_1000_v2_icp100", 1000, 1000, 2.0,
                             ref_fraction=0.25, angle_bins=24, icp_passes=2)
SWEEP_CONFIGS = {
    config.name: config for config in (
        SPARSE_CONFIG,
        MatchConfig("density_500_500_v3", 500, 500, 3.0),
        MatchConfig("density_1000_1000_v2", 1000, 1000, 2.0),
        MatchConfig("density_2000_2000_v2", 2000, 2000, 2.0),
        MatchConfig("ref_0_5", 1000, 1000, 2.0, ref_fraction=0.5),
        MatchConfig("ref_1_0", 1000, 1000, 2.0, ref_fraction=1.0),
        MatchConfig("angle_30", 1000, 1000, 2.0, angle_bins=30),
        MatchConfig("icp_100", 1000, 1000, 2.0, icp_passes=2),
    )
}
DEFAULT_CONFIG = ADOPTED_CONFIG

# 2026-11-01, Python 3.11。各値は _run_sweep_setting の stdout から転記。
# 2000 点は全体2時間でも完走せず、再試行も scene 1 の4対象で31分超だった。
DENSITY_SWEEP = (
    {"model": 180, "scene": 160, "voxel": 6.0, "ar_mssd": 0.1621212121,
     "ar_mspd": 0.1848484848, "seconds": 0.2539355720},
    {"model": 500, "scene": 500, "voxel": 3.0, "ar_mssd": 0.1803030303,
     "ar_mspd": 0.2128787879, "seconds": 1.4225707318},
    {"model": 1000, "scene": 1000, "voxel": 2.0, "ar_mssd": 0.1962121212,
     "ar_mspd": 0.2166666667, "seconds": 8.3804363826},
    {"model": 2000, "scene": 2000, "voxel": 2.0, "ar_mssd": None,
     "ar_mspd": None, "seconds": 54.6},
)

LEADERBOARD = {
    "Drost-CVPR10-3D-Only": {"ar": 0.444, "mssd": 0.478, "mspd": 0.480},
    "Vidal-Sensors18": {"ar": 0.538, "mssd": 0.575, "mspd": 0.574},
}

# 2026-11-01, Python 3.11, archives pinned by tools/fetch_tless.py.
# Updated only from the stdout of this script, never from a caption or hand calculation.
RECORDED = {
    "instances": 132,
    "scenes": 20,
    "model_points": 1000,
    "scene_points": 1000,
    "voxel_mm": 2.0,
    "ref_fraction": 0.25,
    "angle_bins": 24,
    "icp_iterations": 100,
    "ar_mssd": 0.197,
    "ar_mspd": 0.220,
    "synthetic_ar_mssd": 0.985,
    "synthetic_ar_mspd": 0.985,
    "no_icp_ar_mssd": 0.346,
    "no_icp_ar_mspd": 0.338,
    "raw_normals_ar_mssd": 0.132,
    "raw_normals_ar_mspd": 0.161,
    "no_cluster_ar_mssd": 0.111,
    "no_cluster_ar_mspd": 0.113,
    "primary_seconds_per_instance": 8.291,
    "diagnostic_elapsed_seconds": 7189.2,
    "mssd_failure_gt_0_2d": 109,
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


def first_bop19_scene_specs(root: Path):
    """抽出済みBOP19 subsetの各場面から最小画像IDを1枚だけ選ぶ。"""
    specs = []
    for scene_id in SCENE_IDS:
        scene = root / "test_primesense" / f"{scene_id:06d}"
        camera = _json(scene / "scene_camera.json")
        try:
            image_ids = sorted(int(key) for key in camera)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"scene {scene_id}: image ID が整数でない") from exc
        if not image_ids:
            raise ValueError(f"scene {scene_id}: BOP19 image が無い")
        specs.append((scene_id, image_ids[0], "各場面のBOP19先頭画像"))
    return specs


def prepare_scene(record, config: MatchConfig = DEFAULT_CONFIG):
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
    # 旧 180/160 条件は前回と同じ 4 mm の平面・cluster 入力を保つ。照合 voxel
    # が 3/2 mm の条件だけ、その密度を失わないよう前処理側も同じ幅まで細かくする。
    cloud = fs.voxel_downsample(dense, voxel=min(VOXEL_MM, config.voxel_mm))
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
    whole = fs.voxel_downsample(objects, voxel=config.voxel_mm)
    whole_normals = fs.estimate_normals(whole, k=12, viewpoint=np.zeros(3))
    whole, whole_normals = _cap(whole, whole_normals, config.scene_points)
    return {**record, "depth": valid_depth, "zeros": zeros, "flying": flying,
            "dense_count": len(dense), "cloud_count": len(cloud), "plane": plane,
            "ground_count": int(ground.sum()), "objects": objects,
            "clusters": clusters, "centroids": centroids, "boxes": boxes,
            "whole_points": whole, "whole_normals": whole_normals}


def _finish_icp(pose, model, scene_points, config: MatchConfig):
    """surface_match の50反復後へ、採用設定なら同じICPをもう50反復つなぐ。"""
    if config.icp_passes == 1:
        return pose
    from registration import icp
    R, t, _aligned, rmse = icp(model, scene_points, init=(pose["R"], pose["t"]),
                               trim=0.2, max_iter=50)
    return {**pose, "R": R, "t": t, "rmse": float(rmse)}


def _match_one(root, scene, instance, cluster_index, model_info, *, seed,
               config: MatchConfig = DEFAULT_CONFIG, diagnostics: bool = True):
    obj_id = int(instance["obj_id"])
    model_full, normal_full = _ply_vertices_normals(
        root / "models_reconst" / f"obj_{obj_id:06d}.ply")
    model, model_normals = _cap(model_full, normal_full, config.model_points)
    cluster = scene["objects"][scene["clusters"][cluster_index]]
    cluster = fs.voxel_downsample(cluster, voxel=config.voxel_mm)
    oriented = fs.estimate_normals(cluster, k=12, viewpoint=np.zeros(3))
    scene_points, oriented = _cap(cluster, oriented, config.scene_points)
    match_start = time.perf_counter()
    descriptor = fs.ppf_model(model, model_normals, angle_bins=config.angle_bins)
    main = fs.surface_match(descriptor, scene_points, oriented, ref_fraction=config.ref_fraction,
                            topk=8, refine=True, seed=seed)
    main = _finish_icp(main, model, scene_points, config)
    cluster_match_seconds = time.perf_counter() - match_start
    R_gt = np.asarray(instance["cam_R_m2c"], np.float64).reshape(3, 3)
    t_gt = np.asarray(instance["cam_t_m2c"], np.float64)
    eval_points, _ = _ply_vertices_normals(root / "models_cad" / f"obj_{obj_id:06d}.ply")
    eval_points = eval_points[np.linspace(0, len(eval_points) - 1,
                                          min(600, len(eval_points)), dtype=np.int64)]
    syms = symmetry_transforms(model_info)
    def score(pose):
        return pose_metrics(eval_points, pose["R"], pose["t"], R_gt, t_gt, scene["K"], syms)
    metrics = score(main)
    basic = {"pose": main, "metrics": metrics,
             "cluster_match_seconds": cluster_match_seconds,
             "eval_points": eval_points, "R_gt": R_gt, "t_gt": t_gt,
             "model_points": model_full}
    if not diagnostics:
        return basic

    raw_normals = fs.estimate_normals(scene_points, k=12)
    no_icp = fs.surface_match(descriptor, scene_points, oriented,
                              ref_fraction=config.ref_fraction,
                              topk=8, refine=False, seed=seed)
    raw_normal = fs.surface_match(descriptor, scene_points, raw_normals,
                                  ref_fraction=config.ref_fraction,
                                  topk=8, refine=True, seed=seed)
    raw_normal = _finish_icp(raw_normal, model, scene_points, config)
    match_start = time.perf_counter()
    no_cluster = fs.surface_match(descriptor, scene["whole_points"], scene["whole_normals"],
                                  ref_fraction=config.ref_fraction,
                                  topk=8, refine=True, seed=seed)
    no_cluster = _finish_icp(no_cluster, model, scene["whole_points"], config)
    no_cluster_match_seconds = time.perf_counter() - match_start
    metrics_no_icp = score(no_icp)
    metrics_raw_normal = score(raw_normal)
    metrics_no_cluster = score(no_cluster)

    # Ideal point-depth projection: same camera/pose/model, no sensor noise or missing returns.
    synth_depth = render_point_depth(model_full, scene["K"], scene["raw"].shape,
                                     R=R_gt, t=t_gt)
    synth_points = fs.depth_to_points(synth_depth, scene["K"])
    synth_points = fs.voxel_downsample(synth_points, voxel=config.voxel_mm)
    synth_normals = fs.estimate_normals(synth_points, k=12, viewpoint=np.zeros(3))
    synth_points, synth_normals = _cap(synth_points, synth_normals, config.scene_points)
    synth_pose = fs.surface_match(descriptor, synth_points, synth_normals,
                                  ref_fraction=config.ref_fraction, topk=8,
                                  refine=True, seed=seed)
    synth_pose = _finish_icp(synth_pose, model, synth_points, config)
    synth_metrics = score(synth_pose)
    return {**basic, "no_icp": metrics_no_icp,
            "raw_normal": metrics_raw_normal, "synth": synth_metrics,
            "no_cluster": metrics_no_cluster,
            "no_cluster_match_seconds": no_cluster_match_seconds}


def run_real(root: Path, config: MatchConfig = DEFAULT_CONFIG, *, diagnostics: bool = True):
    model_infos = _json(root / "models_reconst" / "models_info.json")
    scenes = [prepare_scene(load_scene(root, *spec), config)
              for spec in first_bop19_scene_specs(root)]
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
                                model_infos[str(obj_id)], seed=seed, config=config,
                                diagnostics=diagnostics)
            mask_path = scene["dir"] / "mask_visib" / f"{scene['image']:06d}_{index:06d}.png"
            visible_mask = np.asarray(Image.open(mask_path)) > 0
            missing = float(np.mean(scene["raw"][visible_mask] == 0)) if visible_mask.any() else 1.0
            size = model_infos[str(obj_id)]
            thin = float(size["size_z"]) / float(size["diameter"]) < 0.45
            symmetric = len(symmetry_transforms(model_infos[str(obj_id)])) > 1
            row = {"scene": scene["scene"], "image": scene["image"], "condition": scene["label"],
                   "obj_id": obj_id, "visibility": visibility, "cluster": cluster_index,
                   "cluster_distance": float(distances[cluster_index]), "missing": missing,
                   "thin": thin, "symmetric": symmetric,
                   "diameter": float(size["diameter"]), **result}
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


def _metric_rows(rows, field):
    return [{**row[field], "diameter": row["diameter"]} for row in rows]


def _groups(rows, field):
    return {value: [row for row in rows if row[field] == value]
            for value in sorted({row[field] for row in rows})}


def _failure_rows(rows):
    return [row for row in rows if row["metrics"]["mssd"] > 0.20 * row["diameter"]]


def _failure_breakdown(rows):
    failures = _failure_rows(rows)
    return {
        "fail_total": len(failures),
        "cluster_merged": sum(row["merged"] for row in failures),
        "occluded_vis_lt_0.8": sum(row["visibility"] < 0.8 for row in failures),
        "thin_z_over_d_lt_0.45": sum(row["thin"] for row in failures),
        "depth_missing_gt_1pct": sum(row["missing"] > 0.01 for row in failures),
        "symmetric": sum(row["symmetric"] for row in failures),
    }


def _save_labeled_bars(name, series, labels, *, xlabel, ylabel, title, caption,
                       size, xlim, ylim=(0.0, 1.0), font_size=9):
    """examplefig の棒グラフへ、同じ値から作ったラベルを棒上に置く。"""
    image = figs.render_plot(series, xlabel=xlabel, ylabel=ylabel, title=title,
                             size=size, xlim=xlim, ylim=ylim,
                             kinds=["bar"] * len(series),
                             colors=["right", "emphasis", "wrong", "neutral"][:len(series)])
    width, height = size
    rect = (72, 44, width - 96, height - 108)
    # render_plot は明示 ylim にも上下6%の余白を足す。
    pad = 0.06 * (ylim[1] - ylim[0])
    ylo, yhi = ylim[0] - pad, ylim[1] + pad
    for (_, xs, ys), texts in zip(series, labels):
        for x, y, value in zip(np.asarray(xs), np.asarray(ys), texts):
            px = rect[0] + (float(x) - xlim[0]) / (xlim[1] - xlim[0]) * rect[2]
            py = rect[1] + (yhi - float(y)) / (yhi - ylo) * rect[3] - 3
            image = np.asarray(fs.text_box(image, str(value), (px, py), anchor="cb",
                                           font_size=font_size, min_font_size=7,
                                           pad=1, box_alpha=0.82, border=0))
    figs.save(name, image, caption)


def _save_metric_comparison(ar_real, ar_synth):
    """図04を数値目盛りでなく4つの指標名を横軸にして保存する。"""
    values = np.asarray([ar_synth[0], ar_synth[1], ar_real[0], ar_real[1]])
    labels = ["合成 MSSD", "合成 MSPD", "実機 MSSD", "実機 MSPD"]
    width, height = 720, 420
    rect = (72, 44, width - 96, height - 118)
    image = np.ones((height, width, 3), np.float64)
    axes = fs.axes_transform(rect, (-0.6, 3.6), (-0.06, 1.06))
    yticks = np.arange(0.0, 1.01, 0.2)
    image = np.asarray(fs.grid_lines(image, axes, xticks=[], yticks=yticks, alpha=0.25))
    image = np.asarray(fs.axes_frame(image, axes, width=1))
    image = np.asarray(fs.ticks(image, axes, xticks=[], yticks=yticks,
                                tick_len=5, font_size=10))
    for index, (label, value, color) in enumerate(zip(
            labels, values, ("right", "emphasis", "wrong", "neutral"))):
        image = np.asarray(fs.plot_series(image, axes, [index], [value], kind="bar",
                                          color=color, bar_width=0.16))
        px, py = fs.data_to_pixel(axes, index, value)
        image = np.asarray(fs.text_box(image, f"{value:.3f}", (px, py - 3),
                                       anchor="cb", font_size=9, pad=1,
                                       box_alpha=0.82, border=0))
        image = np.asarray(fs.text_box(image, label, (px, rect[1] + rect[3] + 10),
                                       anchor="ct", font_size=10, pad=1,
                                       box_alpha=0.0, border=0))
    image = np.asarray(fs.text_box(image, "同じモデル・姿勢: 合成 / 実機 × MSSD / MSPD",
                                   (10, 8), anchor="lt", font_size=13))
    image = np.asarray(fs.text_box(image, "平均 recall", (10, height - 10),
                                   anchor="lb", font_size=11))
    figs.save("synthetic_vs_real", image,
              "合成 MSSD %.3f / 合成 MSPD %.3f / 実機 MSSD %.3f / 実機 MSPD %.3f。"
              % (*ar_synth, *ar_real))


def _save_density_sweep():
    """図06: scene点数に対するAR_MSSDと秒/対象（2000点は時間下限）。"""
    width, height = 760, 430
    rect = (78, 46, width - 170, height - 116)
    image = np.ones((height, width, 3), np.float64)
    x = np.asarray([row["scene"] for row in DENSITY_SWEEP], np.float64)
    ar = np.asarray([np.nan if row["ar_mssd"] is None else row["ar_mssd"]
                     for row in DENSITY_SWEEP], np.float64)
    seconds = np.asarray([row["seconds"] for row in DENSITY_SWEEP], np.float64)
    left = fs.axes_transform(rect, (100.0, 2100.0), (0.15, 0.205))
    right = fs.axes_transform(rect, (100.0, 2100.0), (0.0, 60.0))
    xticks = x
    yticks = np.arange(0.15, 0.201, 0.01)
    image = np.asarray(fs.grid_lines(image, left, xticks=xticks, yticks=yticks, alpha=0.25))
    image = np.asarray(fs.axes_frame(image, left, width=1))
    image = np.asarray(fs.ticks(image, left, xticks=xticks, yticks=yticks,
                                tick_len=5, font_size=9, label_fmt="{:g}"))
    image = np.asarray(fs.plot_series(image, left, x[:3], ar[:3], kind="line",
                                      color="right", width=2, marker_size=4))
    image = np.asarray(fs.plot_series(image, right, x, seconds, kind="line",
                                      color="wrong", width=2, marker_size=4))
    for value in (0.0, 15.0, 30.0, 45.0, 60.0):
        px, py = fs.data_to_pixel(right, 2100.0, value)
        image = np.asarray(fs.text_box(image, f"{value:g}", (px + 8, py),
                                       anchor="lm", font_size=9, pad=1,
                                       box_alpha=0.0, border=0))
    image = np.asarray(fs.text_box(image, "密度 vs AR と時間", (10, 8),
                                   anchor="lt", font_size=13))
    image = np.asarray(fs.text_box(image, "scene 点数   |   左: AR_MSSD   |   右: 秒/対象",
                                   (10, height - 10), anchor="lb", font_size=11))
    image = np.asarray(fs.legend_box(
        image, [("right", "AR_MSSD"), ("wrong", "秒/対象（2000点は下限）")],
        (rect[0] + 8, rect[1] + 8), anchor="lt", markers=True, font_size=10))
    figs.save("density_vs_ar_time", image,
              "180/160、500/500、1000/1000は132対象の完走値。"
              "2000/2000は2時間で未完走のため54.6秒/対象以上、ARは未記録。")


def make_figures(scenes, rows, ar_real, ar_synth):
    if not figs.enabled():
        return
    # (b) is deliberately first: this is the representative figure.
    overlay = _overlay(scenes[0], rows)
    figs.save_grid("pose_overlay", [overlay],
                   ["推定=橙 / 公開真値=青"], title="T-LESS 実機深度の 6 自由度姿勢",
                   ncols=1, caption="scene %d/image %d。PPF+ICP の推定モデル(橙)と BOP 真値(青)。"
                   % (scenes[0]["scene"], scenes[0]["image"]),
                   )
    depth = scenes[0]["depth"]
    figs.save_grid("rgb_depth", [scenes[0]["rgb"], np.nan_to_num(depth)],
                   ["実 RGB", "実機 depth [mm]"], title="PrimeSense Carmine 1.09 の実測入力",
                   ncols=2, gray=[False, False], colorbar=[False, True], unit=["", "mm"],
                   vrange=[None, (650, 950)],
                   caption=f"欠測 {scenes[0]['zeros']} px、孤立飛び候補 {scenes[0]['flying']} px。"
                           " BOP T-LESS, CC BY 4.0。")
    object_groups = _groups(rows, "obj_id")
    obj_ids = np.asarray(list(object_groups), dtype=float)
    obj_mssd = np.asarray([average_recall(_metric_rows(group, "metrics"))[0]
                           for group in object_groups.values()])
    obj_counts = [f"{value:.2f} n={len(group)}"
                  for value, group in zip(obj_mssd, object_groups.values())]
    _save_labeled_bars(
        "mssd_by_object", [("AR_MSSD", obj_ids, obj_mssd)], [obj_counts],
        xlabel="obj_id", ylabel="AR_MSSD", title="対象別の平均 MSSD recall（棒上は値と件数）",
        size=(960, 440), xlim=(float(obj_ids.min()) - 0.8, float(obj_ids.max()) + 0.8),
        caption="20場面の標本を obj_id ごとに平均。棒上は AR_MSSD と対象件数 n。",
        font_size=8)
    _save_metric_comparison(ar_real, ar_synth)
    worst = max(rows, key=lambda row: row["metrics"]["mssd"] / row["diameter"])
    scene = next(item for item in scenes if item["scene"] == worst["scene"])
    fail = _overlay(scene, [worst])
    figs.save_grid("failure", [fail],
                   [f"scene {worst['scene']} / obj {worst['obj_id']} / vis {worst['visibility']:.2f}"],
                    title="失敗例: MSSD が 0.2d を超えた対象", ncols=1,
                   caption="橙=推定、青=真値。MSSD %.1f mm、cluster merged=%s。"
                           % (worst["metrics"]["mssd"], worst["merged"]))
    _save_density_sweep()


def _print_recorded():
    print("BOP T-LESS 実データが無いためダウンロードせず、2026-11-01 の実行記録を表示")
    print(json.dumps(RECORDED, ensure_ascii=False, indent=2))
    print("\n再現: py -3.11 tools/fetch_tless.py && py -3.11 examples/poc_real_tless_6dof.py")
    print("\nPASS")


def _run_sweep_setting(root: Path, config: MatchConfig) -> None:
    """単一設定を固定 subset 全体で採点し、手計算を挟まない JSON を出す。"""
    start = time.perf_counter()
    scenes, rows = run_real(root, config, diagnostics=False)
    elapsed = time.perf_counter() - start
    ar_mssd, ar_mspd = average_recall(_metric_rows(rows, "metrics"))
    result = {
        "setting": config.name,
        "model_points": config.model_points,
        "scene_points": config.scene_points,
        "voxel_mm": config.voxel_mm,
        "ref_fraction": config.ref_fraction,
        "angle_bins": config.angle_bins,
        "icp_iterations": 50 * config.icp_passes,
        "scenes": len(scenes),
        "instances": len(rows),
        "ar_mssd": ar_mssd,
        "ar_mspd": ar_mspd,
        "elapsed_seconds": elapsed,
        "seconds_per_instance": elapsed / len(rows),
        "ppf_seconds_per_instance": (
            sum(row["cluster_match_seconds"] for row in rows) / len(rows)),
    }
    print("SWEEP_RESULT " + json.dumps(result, ensure_ascii=False, sort_keys=True))
    print("\nPASS")


def main() -> None:
    root = Path(os.environ.get(DATA_ENV, DEFAULT_DATA))
    required = (root / "test_primesense", root / "models_reconst" / "models_info.json")
    if not all(path.exists() for path in required):
        _print_recorded()
        return
    sweep_name = os.environ.get(SWEEP_ENV, "").strip()
    if sweep_name:
        if sweep_name not in SWEEP_CONFIGS:
            raise ValueError("未知の掃引設定 %r（%s）" %
                             (sweep_name, ", ".join(sorted(SWEEP_CONFIGS))))
        _run_sweep_setting(root, SWEEP_CONFIGS[sweep_name])
        return
    start = time.perf_counter()
    scenes, rows = run_real(root, DEFAULT_CONFIG)
    metrics = _metric_rows(rows, "metrics")
    no_icp = _metric_rows(rows, "no_icp")
    raw_normals = _metric_rows(rows, "raw_normal")
    synth = _metric_rows(rows, "synth")
    no_cluster = _metric_rows(rows, "no_cluster")
    ar_real = average_recall(metrics)
    ar_no_icp = average_recall(no_icp)
    ar_raw = average_recall(raw_normals)
    ar_synth = average_recall(synth)
    ar_no_cluster = average_recall(no_cluster)

    print("BOP T-LESS (CC BY 4.0) 実機 6DoF PoC")
    print("  source https://bop.felk.cvut.cz/datasets/ / Hodaň et al. WACV 2017")
    print("  setting model/scene %d/%d, voxel %.1f mm, ref %.2f, angle %d, ICP %d"
          % (DEFAULT_CONFIG.model_points, DEFAULT_CONFIG.scene_points,
             DEFAULT_CONFIG.voxel_mm, DEFAULT_CONFIG.ref_fraction,
             DEFAULT_CONFIG.angle_bins, 50 * DEFAULT_CONFIG.icp_passes))
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

    print("\n対象別集計（失敗内訳は MSSD > 0.2d、重複カテゴリ）")
    print(" obj   n AR_MSSD AR_MSPD fail merged occ thin missing sym")
    for obj_id, group in _groups(rows, "obj_id").items():
        ar = average_recall(_metric_rows(group, "metrics"))
        failure = _failure_breakdown(group)
        print(" %3d %3d   %.3f   %.3f %4d %6d %3d %4d %7d %3d"
              % (obj_id, len(group), ar[0], ar[1], failure["fail_total"],
                 failure["cluster_merged"], failure["occluded_vis_lt_0.8"],
                 failure["thin_z_over_d_lt_0.45"], failure["depth_missing_gt_1pct"],
                 failure["symmetric"]))

    print("\n場面別集計")
    print(" scene image   n cluster AR_MSSD AR_MSPD fail")
    for scene_id, group in _groups(rows, "scene").items():
        scene = next(value for value in scenes if value["scene"] == scene_id)
        ar = average_recall(_metric_rows(group, "metrics"))
        print(" %5d %5d %3d %7d   %.3f   %.3f %4d"
              % (scene_id, scene["image"], len(group), len(scene["clusters"]),
                 ar[0], ar[1], len(_failure_rows(group))))

    print("\n公開 leaderboard と同じ MSSD/MSPD 閾値の平均 recall")
    print(" method                         official AR  AR_MSSD  AR_MSPD")
    print(" Fullseye cluster PPF+ICP (20 scenes) n/a      %.3f    %.3f" % ar_real)
    print(" Fullseye scene PPF+ICP (no cluster)  n/a      %.3f    %.3f" % ar_no_cluster)
    print(" Fullseye PPF+ICP (previous 10)       n/a      0.290    0.320")
    for name, score in LEADERBOARD.items():
        print(" %-31s  %.3f      %.3f    %.3f" % (name, score["ar"], score["mssd"], score["mspd"]))
    print("  注: PoC は20場面の先頭画像 subset、公開値は公式全 test。VSD 未実装なので PoC AR は n/a。")

    print("\n合成 -> 実機 / 切り分け")
    print(" ideal depth      AR_MSSD %.3f / AR_MSPD %.3f" % ar_synth)
    print(" real + ICP       AR_MSSD %.3f / AR_MSPD %.3f" % ar_real)
    print(" real - ICP       AR_MSSD %.3f / AR_MSPD %.3f" % ar_no_icp)
    print(" real raw normals AR_MSSD %.3f / AR_MSPD %.3f" % ar_raw)
    print(" real no cluster  AR_MSSD %.3f / AR_MSPD %.3f" % ar_no_cluster)
    print(" drop synth->real: MSSD %.3f / MSPD %.3f" % (ar_synth[0] - ar_real[0], ar_synth[1] - ar_real[1]))

    failures = _failure_rows(rows)
    breakdown = _failure_breakdown(rows)
    print("\n失敗内訳(MSSD > 0.2d、重複カテゴリ):", json.dumps(breakdown, ensure_ascii=False))
    print("  対象:", [(row["scene"], row["obj_id"], round(row["visibility"], 3),
                       round(row["missing"] * 100, 2), row["merged"]) for row in failures])

    make_figures(scenes, rows, ar_real, ar_synth)
    if figs.errors():
        raise RuntimeError("図の書き出し失敗: " + "; ".join(figs.errors()))
    elapsed = time.perf_counter() - start
    clustered_match = sum(row["cluster_match_seconds"] for row in rows)
    no_cluster_match = sum(row["no_cluster_match_seconds"] for row in rows)
    print("\n所要 %.2f 秒 / %d 対象 = %.3f 秒/対象" % (elapsed, len(rows), elapsed / len(rows)))
    print("surface_match 計時: cluster %.2f 秒 (%.3f/対象) / no cluster %.2f 秒 (%.3f/対象)、差 %+0.2f 秒"
          % (clustered_match, clustered_match / len(rows), no_cluster_match,
             no_cluster_match / len(rows), no_cluster_match - clustered_match))
    print("\nPASS")


if __name__ == "__main__":
    main()
