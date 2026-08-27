# -*- coding: utf-8 -*-
"""事例: 30%外れ値下での頑健プリミティブ適合(平面/球/円柱)。

現場の点群(LiDAR/ToF/ステレオ)は、影・反射・別物体の混入で必ず外れ値を含む。
全点を使う素朴な最小二乗(LS)は、たった数%の外れ値でも法線や中心が引きずられる。
RANSAC は「少数サンプルで仮説を立て、多数決(inlier数)で最良を選ぶ」ことで外れ値を
排除する。ここでは既知の真値プリミティブに30%(円柱は25%)の外れ値を混ぜ、
RANSAC が真値を復元し、かつ素朴LSより明確に優れることを数値で確認する。
"""
import numpy as np
import ransac_fit as R


def _u(v):
    """単位ベクトル化。"""
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _angle_deg(a, b):
    """2方向のなす角(度、符号非依存 0..90)。"""
    c = abs(float(_u(a) @ _u(b)))
    return float(np.degrees(np.arccos(np.clip(c, 0.0, 1.0))))


# 1) 平面: 30% 外れ値
def make_plane(seed=0, n=600, outlier_frac=0.30, noise=0.01):
    """真の平面 normal·x = offset の上の点 + 空間全体に散る外れ値。"""
    rng = np.random.default_rng(seed)
    normal = _u([0.3, -0.5, 1.0]); offset = 0.7
    e1 = _u(np.cross(normal, [1, 0, 0])); e2 = np.cross(normal, e1)
    n_out = int(n * outlier_frac); n_in = n - n_out
    uv = rng.uniform(-5, 5, (n_in, 2))
    inl = normal * offset + uv[:, :1] * e1 + uv[:, 1:] * e2 + rng.normal(0, noise, (n_in, 3))
    out = rng.uniform(-5, 5, (n_out, 3))          # 平面と無関係な外れ値
    P = np.vstack([inl, out]); is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], normal, is_out[perm]


def ls_plane_normal(P):
    """素朴LS平面法線 = 全点の共分散の最小固有ベクトル(外れ値に弱いベースライン)。"""
    c = P.mean(0)
    _, v = np.linalg.eigh((P - c).T @ (P - c))
    return _u(v[:, 0])


# 2) 球: 30% 外れ値
def make_sphere(seed=0, n=600, outlier_frac=0.30, noise=0.01):
    """真の中心/半径の球面上の点 + 中心付近に散る外れ値。"""
    rng = np.random.default_rng(seed)
    center = np.array([1.2, -0.7, 2.0]); radius = 1.5
    n_out = int(n * outlier_frac); n_in = n - n_out
    v = rng.normal(0, 1, (n_in, 3)); v /= np.linalg.norm(v, axis=1, keepdims=True)
    inl = center + radius * v + rng.normal(0, noise, (n_in, 3))
    out = center + rng.uniform(-4, 4, (n_out, 3))
    P = np.vstack([inl, out]); is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], center, radius, is_out[perm]


def ls_sphere(P):
    """素朴LS球(代数フィット、全点)。返り (center, radius)。外れ値に弱いベースライン。"""
    A = np.hstack([2.0 * P, np.ones((len(P), 1))]); b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]; r = float(np.sqrt(max(sol[3] + c @ c, 0.0)))
    return c, r


# 3) 円柱: 25% 外れ値(点法線が必要)
def make_cylinder(seed=0, n=800, outlier_frac=0.25, noise=0.01):
    """真の軸/半径の円柱面上の点 + 外向き法線 + 外れ値(法線もランダム)。"""
    rng = np.random.default_rng(seed)
    axis = _u([0.2, 0.3, 1.0]); radius = 1.2; axis_pt = np.array([0.5, -0.4, 0.0])
    e1 = _u(np.cross(axis, [1, 0, 0])); e2 = np.cross(axis, e1)
    n_out = int(n * outlier_frac); n_in = n - n_out
    th = rng.uniform(0, 2 * np.pi, n_in); h = rng.uniform(-4, 4, n_in)
    radial = np.cos(th)[:, None] * e1 + np.sin(th)[:, None] * e2
    inl = axis_pt + radius * radial + h[:, None] * axis + rng.normal(0, noise, (n_in, 3))
    n_inl = radial + rng.normal(0, noise, (n_in, 3)); n_inl /= np.linalg.norm(n_inl, axis=1, keepdims=True)
    out = axis_pt + rng.uniform(-4, 4, (n_out, 3))
    n_out_v = rng.normal(0, 1, (n_out, 3)); n_out_v /= np.linalg.norm(n_out_v, axis=1, keepdims=True)
    P = np.vstack([inl, out]); Nrm = np.vstack([n_inl, n_out_v])
    is_out = np.zeros(n, bool); is_out[n_in:] = True
    perm = rng.permutation(n)
    return P[perm], Nrm[perm], axis, radius, is_out[perm]


def ls_cylinder_axis(Nrm):
    """素朴LS円柱軸 = 全法線のSVDの最小特異方向(法線⟂軸)。外れ値法線に弱いベースライン。"""
    Nn = Nrm / np.linalg.norm(Nrm, axis=1, keepdims=True)
    _, _, vt = np.linalg.svd(Nn, full_matrices=False)
    return _u(vt[-1])


# 実行 + GT 検証
thresh = 0.05

# --- 平面 ---
P, gt_n, is_out = make_plane(0)
params, mask, info = R.ransac_plane(P, thresh=thresh)
ang_ransac = _angle_deg(params["normal"], gt_n)
ang_ls = _angle_deg(ls_plane_normal(P), gt_n)
excl = float((~mask[is_out]).mean())          # 外れ値を False にできた割合
kept = float(mask[~is_out].mean())            # 真の inlier を拾えた割合
print("[平面] RANSAC法線誤差 = %.3f deg / 素朴LS法線誤差 = %.3f deg" % (ang_ransac, ang_ls))
print("       inlier_ratio=%.3f  外れ値排除率=%.3f  inlier保持率=%.3f  degenerate=%s"
      % (info["inlier_ratio"], excl, kept, info["degenerate"]))
assert ang_ransac < 2.0, ang_ransac                     # RANSAC は真法線を復元
assert ang_ransac < 0.25 * ang_ls                       # 素朴LSより明確に優位
assert excl > 0.8 and kept > 0.9                        # 外れ値を排除・真値を保持
assert info["degenerate"] is False

# --- 球 ---
P, gt_c, gt_r, is_out = make_sphere(0)
params, mask, info = R.ransac_sphere(P, thresh=thresh)
c_err = float(np.linalg.norm(params["center"] - gt_c))
r_err = float(abs(params["radius"] - gt_r))
ls_c, ls_r = ls_sphere(P)
c_err_ls = float(np.linalg.norm(ls_c - gt_c)); r_err_ls = float(abs(ls_r - gt_r))
print("[球]   RANSAC 中心誤差=%.4f 半径誤差=%.4f / 素朴LS 中心誤差=%.4f 半径誤差=%.4f"
      % (c_err, r_err, c_err_ls, r_err_ls))
assert c_err < thresh and r_err < thresh                # 中心・半径を復元
assert c_err < 0.25 * c_err_ls                          # 素朴LSより明確に優位
assert (~mask[is_out]).mean() > 0.8 and mask[~is_out].mean() > 0.9

# --- 円柱 ---
P, Nrm, gt_axis, gt_r, is_out = make_cylinder(0)
params, mask, info = R.ransac_cylinder(P, Nrm, thresh=thresh)
ang_ransac = _angle_deg(params["axis"], gt_axis)
ang_ls = _angle_deg(ls_cylinder_axis(Nrm), gt_axis)
r_err = float(abs(params["radius"] - gt_r))
print("[円柱] RANSAC軸誤差=%.3f deg 半径誤差=%.4f / 素朴LS軸誤差=%.3f deg"
      % (ang_ransac, r_err, ang_ls))
print("       inlier_ratio=%.3f  外れ値排除率=%.3f  degenerate=%s"
      % (info["inlier_ratio"], float((~mask[is_out]).mean()), info["degenerate"]))
assert ang_ransac < 2.0                                 # 軸を復元(cos>0.98 相当)
assert r_err < thresh                                   # 半径を復元
assert ang_ransac < 0.5 * ang_ls                        # 素朴LS軸より優位
assert (~mask[is_out]).mean() > 0.7

print("\nOK: 3プリミティブとも30%(円柱25%)外れ値下で真値を復元し、素朴LSに優越")
