"""残 genuine の寄せ集め: Inspection・sheet-of-light・scene flow・GMM・
rectification grid・XLD skeleton(HALCON 複数 chapter genuine, numpy).

統一 I/F の設定オブジェクト(dict handle)として create/apply/find を提供。
image = 2D float64、region = bool 2D、点群 = (N,3)。
"""
from __future__ import annotations

import numpy as np


def _img(a):
    return np.asarray(a, dtype=np.float64)


# ── Inspection: variation/bead/texture/ocv ─────────────────────────────────────── #
def create_bead_inspection_model(reference_path, width=5.0, tol=0.3):
    """接着ビード検査モデル(基準経路 + 幅公差)(create_bead_inspection_model)。
    reference_path: ビード中心線の (row,col) 点列。"""
    return {"path": np.asarray(reference_path, float).reshape(-1, 2),
            "width": float(width), "tol": float(tol)}


def apply_bead_inspection_model(model, image, thresh=0.3):
    """画像中のビードを検査し、経路上での欠損/はみ出しを検出(apply_bead_inspection_model)。"""
    im = _img(image); m = im > thresh
    from scipy.ndimage import distance_transform_edt
    dt = distance_transform_edt(~m)
    path = model["path"]; w = model["width"]
    defects = []
    for row, col in path:
        r = int(np.clip(round(row), 0, im.shape[0] - 1))
        c = int(np.clip(round(col), 0, im.shape[1] - 1))
        if dt[r, c] > w / 2 + model["tol"]:
            defects.append({"row": float(row), "column": float(col), "type": "missing"})
    return {"defects": defects, "num_defects": len(defects),
            "ok": len(defects) == 0}


def create_texture_inspection_model(reference_images, patch=8):
    """テクスチャ検査モデル(正常サンプルの局所統計分布)(create_texture_inspection_model)。"""
    from scipy.ndimage import uniform_filter
    feats = []
    for im in reference_images:
        g = _img(im)
        mean = uniform_filter(g, patch)
        var = uniform_filter(g * g, patch) - mean ** 2
        feats.append(np.stack([mean.ravel(), var.ravel()], axis=-1))
    F = np.vstack(feats)
    return {"mean": F.mean(0), "cov": np.cov(F.T) + 1e-6 * np.eye(2),
            "patch": patch}


def apply_texture_inspection_model(model, image, thresh=3.0):
    """テクスチャ検査モデルで異常(Mahalanobis 距離大)領域を検出(apply_texture_inspection_model)。"""
    from scipy.ndimage import uniform_filter
    g = _img(image); patch = model["patch"]
    mean = uniform_filter(g, patch); var = uniform_filter(g * g, patch) - mean ** 2
    F = np.stack([mean.ravel(), var.ravel()], axis=-1) - model["mean"]
    inv = np.linalg.inv(model["cov"])
    md = np.sqrt(np.einsum("ij,jk,ik->i", F, inv, F)).reshape(g.shape)
    return {"anomaly_map": md, "defects": md > thresh}


def create_ocv_proj(training_images):
    """OCV(光学文字検証)用の平均テンプレートモデル(create_ocv_proj)。"""
    stack = np.stack([_img(im) for im in training_images], axis=0)
    return {"mean": stack.mean(0), "std": stack.std(0) + 1e-6}


# ── Segmentation: GMM 分類 ──────────────────────────────────────────────────── #
def classify_image_class_gmm(feature_images, means, covs, weights=None, thresh=None):
    """ガウス混合モデルで多チャネル特徴画像を画素分類(classify_image_class_gmm)。
    means: (K,D)、covs: (K,D,D)。最尤クラスのラベル画像を返す。"""
    F = feature_images
    if isinstance(F, (list, tuple)):
        F = np.stack([_img(f) for f in F], axis=-1)
    F = _img(F); H, W, D = F.shape
    X = F.reshape(-1, D)
    means = np.asarray(means, float); covs = np.asarray(covs, float)
    K = len(means)
    if weights is None:
        weights = np.ones(K) / K
    logp = np.zeros((len(X), K))
    for k in range(K):
        inv = np.linalg.inv(covs[k]); det = np.linalg.det(covs[k])
        d = X - means[k]
        logp[:, k] = (np.log(weights[k] + 1e-12) - 0.5 * np.log(det + 1e-12)
                      - 0.5 * np.einsum("ij,jk,ik->i", d, inv, d))
    lab = logp.argmax(1)
    return lab.reshape(H, W)


# ── Tools: rectification grid ─────────────────────────────────────────────────── #
def create_rectification_grid(width, height, spacing):
    """整流用の理想格子点(ワールド)を生成(create_rectification_grid)。"""
    nx = int(width / spacing) + 1; ny = int(height / spacing) + 1
    r, c = np.mgrid[0:ny, 0:nx]
    return {"points": np.column_stack([r.ravel() * spacing, c.ravel() * spacing]),
            "nx": nx, "ny": ny, "spacing": spacing}


def find_rectification_grid(image, thresh=0.5, min_area=5):
    """画像から整流格子(交点/ドット)を検出(find_rectification_grid)。"""
    from scipy import ndimage
    m = _img(image) > thresh
    lab, n = ndimage.label(m)
    if n == 0:
        return np.zeros((0, 2))
    centers = ndimage.center_of_mass(m, lab, range(1, n + 1))
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    return np.asarray([c for c, s in zip(centers, sizes) if s >= min_area])


# ── XLD: skeleton / segment attrib / line-scan merge ──────────────────────────── #
def gen_contours_skeleton_xld(region, min_length=3):
    """領域のスケルトンを抽出し輪郭(枝ごと)へ変換(gen_contours_skeleton_xld)。"""
    from skimage.morphology import skeletonize
    m = np.asarray(region, bool)
    sk = skeletonize(m)
    rs, cs = np.where(sk)
    return {"shape": m.shape, "cs": [np.column_stack([rs, cs]).astype(float)] if len(rs) >= min_length else []}


def segment_contour_attrib_xld(contour, image):
    """輪郭を、下地グレー値の属性が急変する点で分割(segment_contour_attrib_xld)。"""
    im = _img(image); out = []
    for a in contour["cs"]:
        rr = np.clip(a[:, 0].round().astype(int), 0, im.shape[0] - 1)
        cc = np.clip(a[:, 1].round().astype(int), 0, im.shape[1] - 1)
        g = im[rr, cc]
        breaks = np.nonzero(np.abs(np.diff(g)) > 0.3)[0] + 1
        prev = 0
        for b in list(breaks) + [len(a)]:
            if b - prev >= 2:
                out.append(a[prev:b])
            prev = b
    return {"shape": contour.get("shape"), "cs": out}


def merge_cont_line_scan_xld(contours_prev, contours_cur, max_dist=3.0):
    """ラインスキャン(帯状取得)の隣接フレーム輪郭端点を連結(merge_cont_line_scan_xld)。"""
    merged = [a.copy() for a in contours_prev.get("cs", [])]
    for cur in contours_cur.get("cs", []):
        best = None; bestd = max_dist
        for i, prev in enumerate(merged):
            d = np.linalg.norm(prev[-1] - cur[0])
            if d < bestd:
                bestd = d; best = i
        if best is not None:
            merged[best] = np.vstack([merged[best], cur])
        else:
            merged.append(cur)
    shape = contours_prev.get("shape", contours_cur.get("shape"))
    return {"shape": shape, "cs": merged}


# ── scene flow(3D 運動場)────────────────────────────────────────────────────── #
def scene_flow_uncalib(img1_l, img1_r, img2_l, img2_r, focal=500.0, baseline=0.1):
    """左右 2 時刻の画像から 3D シーンフロー(未校正近似)を推定(scene_flow_uncalib)。
    視差 → 深度、光学フロー → 画像運動、を組み合わせ 3D 変位場を返す。"""
    from stereo import disparity_map
    from filters_flow import optical_flow_mg
    d1 = disparity_map(img1_l, img1_r); d2 = disparity_map(img2_l, img2_r)
    with np.errstate(divide="ignore", invalid="ignore"):
        Z1 = np.where(d1 > 1e-6, focal * baseline / d1, np.nan)
        Z2 = np.where(d2 > 1e-6, focal * baseline / d2, np.nan)
    flow = optical_flow_mg(img1_l, img2_l, iterations=60)
    return {"dZ": Z2 - Z1, "flow_row": flow["row"], "flow_col": flow["col"]}


def scene_flow_calib(img1_l, img1_r, img2_l, img2_r, cam_par, baseline=0.1):
    """校正済シーンフロー(内部行列で 3D 変位をメトリック化)(scene_flow_calib)。"""
    f = cam_par["fx"] if isinstance(cam_par, dict) else float(cam_par[0][0])
    return scene_flow_uncalib(img1_l, img1_r, img2_l, img2_r, f, baseline)


# ── sheet-of-light(レーザ三角測量プロファイル)──────────────────────────────── #
def create_sheet_of_light_model(camera_par=None, baseline=0.1, angle=0.5):
    """シート光(レーザライン)プロファイル計測モデル(create_sheet_of_light_model)。"""
    return {"cam_par": camera_par, "baseline": baseline, "angle": angle}


def create_sheet_of_light_calib_object(spacing=1.0):
    """シート光校正オブジェクト(既知段差)(create_sheet_of_light_calib_object)。"""
    return {"spacing": spacing}


def measure_profile_sheet_of_light(model, image, thresh=0.3):
    """各列でレーザライン(最大輝度)の行位置=高さプロファイルを抽出
    (measure_profile_sheet_of_light)。"""
    im = _img(image); H, W = im.shape
    profile = np.full(W, np.nan)
    for c in range(W):
        col = im[:, c]
        if col.max() > thresh:
            # 輝度重心でサブピクセル
            w = np.clip(col - thresh, 0, None)
            profile[c] = (np.arange(H) * w).sum() / (w.sum() + 1e-12)
    return profile


def apply_sheet_of_light_calibration(model, profile):
    """プロファイル(画素行)を高さ(メトリック)へ換算(apply_sheet_of_light_calibration)。"""
    prof = np.asarray(profile, float)
    scale = model.get("baseline", 0.1) / np.tan(model.get("angle", 0.5) + 1e-9)
    ref = np.nanmedian(prof)
    return (ref - prof) * scale


def calibrate_sheet_of_light(model, calib_image, known_heights):
    """既知段差からシート光の画素→高さスケールを校正(calibrate_sheet_of_light)。"""
    prof = measure_profile_sheet_of_light(model, calib_image)
    valid = ~np.isnan(prof)
    if valid.sum() < 2:
        return model
    kh = np.asarray(known_heights, float)
    scale = np.polyfit(prof[valid][:len(kh)], kh[:valid.sum()], 1)[0] if len(kh) else 1.0
    m = dict(model); m["pixel_to_height"] = float(scale)
    return m


def create_stereo_model(cam_par_left, cam_par_right, rel_pose):
    """ステレオ計測モデル(左右内部 + 相対姿勢)(create_stereo_model)。"""
    return {"left": cam_par_left, "right": cam_par_right, "rel_pose": rel_pose}


def create_structured_light_model(width=64, height=48, num_patterns=8):
    """構造化光計測モデル(位相シフトパターン設定)(create_structured_light_model)。"""
    return {"width": width, "height": height, "num_patterns": num_patterns}
