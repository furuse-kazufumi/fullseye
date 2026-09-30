"""numpy だけの 3D Gaussian Splatting(表現 + EWA 描画)—— 合成世界を「3DGS にしてから」画像処理にかけるための層。

何をするか:
  * :func:`gs_from_world` —— 世界(driveworld / kendamaworld の三角形の束)の面にガウシアンを貼る。1 個ごとに「どの面の、どの重心座標か」と
    「面の局所座標での誤差」を固定で持つので、世界の頂点が動けば(けんを振る、玉が飛ぶ)ガウシアンも付いて動く(:func:`gs_update`)。
  * つまみ = 間隔 ``spacing``(密度 = 1 / spacing²、物体ごとの上限 ``max_per_object`` で背景は粗くなる)・位置の誤差 ``pos_noise``(m)・
    色の誤差 ``color_noise``。再構成の質を振る(ユーザー 2026-09-29「3DGS にして密度を振る」「位置や色にも少し誤差を載せる」)。
  * :func:`gs_render` —— EWA splatting(Zwicker ら 2001 / 3DGS の Kerbl ら 2023 と同じ投影): 2-D 共分散 Σ' = J W Σ Wᵀ Jᵀ + s·I
    (J = 透視投影のヤコビアン、s = 低域通過 0.3 px²、``antialias`` なら不透明度を √(det Σ / det(Σ + sI)) 倍 = Mip-Splatting)、深さの順に手前から α 合成 C = Σ_i c_i α_i Π_{j<i}(1 − α_j)。

正直な注記: 本物の 3DGS は写真からガウシアンを**最適化**して得る。ここでは真の形状(メッシュ)から**初期化**し、密度と誤差のつまみで
再構成の不完全さを模す。つまり「3DGS の表現と描画の上で画像処理が動くか」を測る道具であり、再構成の質そのものの主張ではない。
学習する版は fullseye_3dgs.py / gsplat_*(torch・任意)。
"""
from __future__ import annotations

import numpy as np

__all__ = ["gs_from_world", "gs_update", "gs_render", "gs_render_fn"]

_LOW_PASS = 0.3          # px²(3DGS の実装と同じ抗エイリアスの足し込み)
_ALPHA_MIN = 1.0 / 255.0
_ALPHA_MAX = 0.99


def _face_frames(V: np.ndarray, F: np.ndarray):
    """面ごとの (t1, t2, n, area)。t1 = 辺 0→1 の向き、n = 面法線、t2 = n × t1。退化面は面積 0(法線は +z の仮置き)。"""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    e1 = b - a
    cr = np.cross(e1, c - a)
    area2 = np.linalg.norm(cr, axis=1)
    ok = area2 > 1e-18
    n = np.zeros_like(cr)
    n[ok] = cr[ok] / area2[ok, None]
    n[~ok] = (0.0, 0.0, 1.0)
    le = np.linalg.norm(e1, axis=1)
    t1 = np.zeros_like(e1)
    good = ok & (le > 1e-15)
    t1[good] = e1[good] / le[good, None]
    # 退化面: n に直交する任意の向き
    bad = ~good
    if bad.any():
        ref = np.where(np.abs(n[bad, 0:1]) < 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
        tt = np.cross(n[bad], ref)
        t1[bad] = tt / np.linalg.norm(tt, axis=1, keepdims=True)
    t2 = np.cross(n, t1)
    return t1, t2, n, 0.5 * area2


def _face_curvature_radius(V: np.ndarray, F: np.ndarray, crease_deg: float = 75.0) -> np.ndarray:
    """面ごとの (曲率半径の見積り R_f, 角に接するか)。R_f = min_{隣の面} d⊥ / θ(θ = 隣り合う面の法線の角度、d⊥ = 重心の差の共有辺に垂直な成分)。θ ≥ ``crease_deg`` の辺は
    曲面でなく「角」(皿の縁・段)なので数えない。隣が無い・平らなら inf。"""
    _, _, n, _ = _face_frames(V, F)
    cen = V[F].mean(axis=1)
    M = len(F)
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E.sort(axis=1)
    fid = np.tile(np.arange(M), 3)
    key = E[:, 0].astype(np.int64) * (int(E.max()) + 1) + E[:, 1]
    o = np.argsort(key, kind="stable")
    k, f, Eo = key[o], fid[o], E[o]
    same = np.flatnonzero(k[1:] == k[:-1])                           # 辺を共有する面の組(多様体なら 2 枚)
    a, b = f[same], f[same + 1]
    cosang = np.clip(np.einsum("ij,ij->i", n[a], n[b]), -1.0, 1.0)
    th = np.arccos(cosang)
    ev = V[Eo[same, 1]] - V[Eo[same, 0]]
    ev /= np.maximum(np.linalg.norm(ev, axis=1, keepdims=True), 1e-300)
    dv = cen[b] - cen[a]
    dist = np.linalg.norm(dv - np.einsum("ij,ij->i", dv, ev)[:, None] * ev, axis=1)   # 共有辺に垂直な成分(細長い面で軸方向の差を数えない)
    ok = (th > 1e-6) & (th < np.radians(crease_deg))
    R = np.full(M, np.inf)
    rr = np.where(ok, dist / np.maximum(th, 1e-12), np.inf)
    np.minimum.at(R, a, rr)
    np.minimum.at(R, b, rr)
    crease = np.zeros(M, bool)
    cr = th >= np.radians(crease_deg)
    crease[a[cr]] = True
    crease[b[cr]] = True
    return R, crease


def gs_from_world(world: dict, *, spacing: float = 0.004, max_per_object: int = 20000, pos_noise: float = 0.0,
                  color_noise: float = 0.0, sigma_ratio: float = 1.0, normal_ratio: float = 0.1, opacity: float = 0.99,
                  curv_ratio: float = 0.5, edge_ratio: float = 0.25, seed: int = 0) -> dict:
    """世界の面にガウシアンを貼った 3DGS を返す(``world`` = driveworld の世界 dict: V, F, face_color, objects)。

    物体ごとに間隔 s_o = max(``spacing``, √(物体の面積 / ``max_per_object``))、個数 N_o = ⌈面積 / s_o²⌉。面は面積に比例した層化抽出
    (累積面積の (k + u)/N_o 点、u は物体ごとの一様乱数)で選び、面の中は R2 低食い違い列(一様乱数だと隙間 = 穴が空く)。共分散は面に沿う平たい円盤
    局所間隔 s_f = max(s_o / 8, min(s_o, ``curv_ratio`` · R_f / ``sigma_ratio``))(R_f = 面の曲率半径の見積り、角 ≥ 75° は数えない):
    平たい円盤が曲面からはみ出さない大きさに抑え、細い所(糸)はそのぶん密に置く(個数の重み = 面積 / s_f²)。角(隣の面と 75° 以上)に
    接する面は s_f ≤ ``edge_ratio`` · s_o(3DGS が縁で細かくするのと同じ: 大きな円盤が縁の外 —— 玉の穴の口 —— へはみ出して穴を塞いだ)。
    Σ = R diag(σt², σt², σn²) Rᵀ、σt = ``sigma_ratio`` · s_f(既定 1.0 = 3DGS の初期値「近い 3 点までの平均距離」と同じ。0.7 では
    板の 7 % の画素で α < 0.95 の隙間が残った)、σn = ``normal_ratio`` · σt、R = [t1 t2 n](面の局所座標)。
    誤差(1 個ごとに固定、コマをまたいで同じ): 面の局所座標での位置 N(0, ``pos_noise``²)(3 軸)・色 N(0, ``color_noise``²)(切り詰め)。

    返り値 dict: ``face`` (N,)・``bary`` (N,3)・``offset_local`` (N,3)・``color`` (N,3)・``opacity`` (N,)・``sigma_t`` (N,)・``sigma_n`` (N,)・
    ``obj`` (N,)(世界の objects の索引)・``label`` (N,)・``spacing_obj`` (物体数,)、加えて :func:`gs_update` が埋める ``mu`` (N,3)・
    ``R`` (N,3,3)(列 = t1, t2, n)・``normal`` (N,3)。
    fail-closed: spacing ≤ 0、max_per_object < 1、雑音 < 0、sigma_ratio ≤ 0、normal_ratio ≤ 0、opacity ∉ (0, 1]、面の無い世界は ValueError。"""
    if not (np.isfinite(spacing) and spacing > 0) or int(max_per_object) < 1:
        raise ValueError("gs_from_world: need spacing > 0 and max_per_object ≥ 1")
    if not (pos_noise >= 0 and color_noise >= 0) or not (sigma_ratio > 0 and normal_ratio > 0 and curv_ratio > 0 and 0 < edge_ratio <= 1) or not (0 < opacity <= 1):
        raise ValueError("gs_from_world: need pos_noise ≥ 0, color_noise ≥ 0, sigma_ratio > 0, normal_ratio > 0, 0 < opacity ≤ 1")
    V = np.asarray(world["V"], np.float64)
    F = np.asarray(world["F"], np.int64)
    if len(F) == 0:
        raise ValueError("gs_from_world: the world has no faces")
    C = np.asarray(world["face_color"], np.float64)
    Lb = np.asarray(world["face_label"], np.int64)
    _, _, _, area = _face_frames(V, F)
    Rc, crease = _face_curvature_radius(V, F)
    rng = np.random.default_rng(seed)
    objs = world.get("objects") or [{"faces": (0, len(F))}]
    faces, objid, sp_o, loc = [], [], [], []
    for oi, o in enumerate(objs):
        f0, f1 = (int(v) for v in o["faces"])
        A = area[f0:f1]
        tot = float(A.sum())
        if f1 <= f0 or tot <= 0:
            sp_o.append(np.nan)
            continue
        s = max(float(spacing), float(np.sqrt(tot / int(max_per_object))))
        # 面ごとの局所間隔: 平たい円盤が曲面からはみ出さない σ ≤ curv_ratio · R(糸のような細い所)なら、そのぶん密に置く
        sf = np.minimum(s, curv_ratio * Rc[f0:f1] / sigma_ratio)
        sf = np.where(crease[f0:f1], np.minimum(sf, edge_ratio * s), sf)   # 角(縁・段)に接する面は細かく: 円盤が縁の外へはみ出さない
        sf = np.maximum(sf, s / 8.0)                                  # 密にするのは 8 倍(64 倍の個数)まで
        wgt = A / (sf * sf)
        n = max(1, int(np.ceil(wgt.sum())))
        if n > int(max_per_object):                                    # 上限: 比を保ったまま全体を粗く
            n = int(max_per_object)
        cum = np.cumsum(wgt)
        u = (np.arange(n) + rng.uniform()) * (cum[-1] / n)
        fi = np.minimum(np.searchsorted(cum, u, side="right"), len(A) - 1) + f0
        faces.append(fi)
        objid.append(np.full(n, oi, np.int64))
        loc.append(np.sqrt(wgt.sum() / n) * sf[fi - f0])                # 実際の局所間隔(上限で粗くしたぶんを含む)
        sp_o.append(s)
    face = np.concatenate(faces)
    obj = np.concatenate(objid)
    N = len(face)
    # 面の中の置き方は低食い違い列(R2 列、Roberts 2018)を面ごとに通し番号で: 一様乱数だと隙間(穴)が空く。単位正方形 → 三角形は折り返し
    order = np.argsort(face, kind="stable")
    fs = face[order]
    first = np.r_[True, fs[1:] != fs[:-1]]
    rank = np.empty(N, np.int64)
    rank[order] = np.arange(N) - np.maximum.accumulate(np.where(first, np.arange(N), 0))
    ph = rng.uniform(size=(N, 2))[np.searchsorted(np.unique(fs), face)] if N else np.zeros((0, 2))   # 面ごとの位相
    s1 = (ph[:, 0] + (rank + 0.5) * 0.7548776662466927) % 1.0
    s2 = (ph[:, 1] + (rank + 0.5) * 0.5698402909980532) % 1.0
    fold = s1 + s2 > 1.0
    s1[fold], s2[fold] = 1.0 - s1[fold], 1.0 - s2[fold]
    bary = np.column_stack([1.0 - s1 - s2, s1, s2])
    offset = rng.normal(0.0, pos_noise, (N, 3)) if pos_noise > 0 else np.zeros((N, 3))
    col = C[face]
    if color_noise > 0:
        col = np.clip(col + rng.normal(0.0, color_noise, (N, 3)), 0.0, 1.0)
    sp = np.concatenate(loc)                                           # ガウシアンごとの局所間隔
    st = sigma_ratio * sp
    S_t = np.eye(2)[None] * (st * st)[:, None, None]
    gs = {"face": face, "bary": bary, "offset_local": offset, "color": col, "opacity": np.full(N, float(opacity)),
          "cov_t": S_t, "sigma_t": st, "sigma_n": normal_ratio * st, "obj": obj, "label": Lb[face],
          "spacing_obj": np.asarray(sp_o, np.float64),
          "params": {"spacing": float(spacing), "max_per_object": int(max_per_object), "pos_noise": float(pos_noise),
                     "color_noise": float(color_noise), "sigma_ratio": float(sigma_ratio), "normal_ratio": float(normal_ratio), "curv_ratio": float(curv_ratio), "edge_ratio": float(edge_ratio),
                     "seed": int(seed)}}
    return gs_update(gs, world)


def gs_update(gs: dict, world: dict) -> dict:
    """世界の**いまの**頂点からガウシアンの中心・向きを計算し直す(その場で書き換えて同じ dict を返す)。

    μ = Σ_k bary_k · V[F[face, k]] + R · offset_local、R = 面の局所座標 [t1 t2 n]。面の数が作ったときと違う世界は ValueError
    (物体を足した・消した世界には使えない: 作り直すこと)。剛体で動かした物体のガウシアンは同じ剛体変換で動く(門)。"""
    V = np.asarray(world["V"], np.float64)
    F = np.asarray(world["F"], np.int64)
    if len(F) <= int(gs["face"].max()):
        raise ValueError("gs_update: the world has fewer faces than when the splats were made (rebuild with gs_from_world)")
    t1, t2, n, _ = _face_frames(V, F)
    fi = gs["face"]
    R = np.stack([t1[fi], t2[fi], n[fi]], axis=2)                     # (N, 3, 3) 列 = t1, t2, n
    P = np.einsum("nk,nkd->nd", gs["bary"], V[F[fi]])
    gs["mu"] = P + np.einsum("nij,nj->ni", R, gs["offset_local"])
    gs["R"] = R
    gs["normal"] = n[fi]
    return gs


def gs_render(gs: dict, pose, K, width: int, height: int, *, light=(0.3, -0.5, 0.8), ambient: float = 0.35,
              sky=(0.62, 0.75, 0.92), max_radius: int = 64, max_pairs: int = 12_000_000, antialias: bool = True) -> dict:
    """3DGS をカメラ(``pose`` = world→camera 4×4、``K`` 3×3、driveworld.world_camera と同じ規約: −Z を見る、行は上が小さい)で描く。

    手順: (1) 中心をカメラ系へ、深さ d = −z ≤ 1e-6 は捨てる、(2) 2-D 共分散 Σ' = J W Σ Wᵀ Jᵀ + 0.3 I、
    J = [[fx/d, 0, fx·x/d²], [0, −fy/d, −fy·y/d²]]、(3) 半径 r = ⌈3 √λ_max(Σ')⌉(≤ ``max_radius``、超える物は捨てずに r を切る)の窓の
    画素ごとに α = min(0.99, o · exp(−½ Δᵀ Σ'⁻¹ Δ))(α < 1/255 は捨てる)、(4) 画素ごとに深さの順で手前から
    C = Σ c_i α_i T_i、T_i = Π_{j<i}(1 − α_j)、背景 = (1 − Σ α_i T_i) · sky。色は Lambert(world_camera と同じ ambient + (1 − ambient)|n·l|、
    光はカメラ系)。すべて配列演算(ガウシアン × 窓の画素の組を平らに並べ、画素 → 深さで並べて群ごとの累積和で T を出す)。

    返り値: ``color`` (H,W,3)・``alpha`` (H,W)(= Σ α_i T_i)・``depth`` (H,W)(α で重みづけた深さ / alpha、alpha < 0.5 は NaN)・
    ``label`` (H,W)(重み最大のガウシアンのラベル、alpha < 0.5 は −1)・``n_pairs``・``n_visible``。
    fail-closed: 画像の大きさ ≤ 0、max_radius < 1、組の数が ``max_pairs`` を超える(遅すぎる描画を黙って走らせない)は ValueError。"""
    W, H = int(width), int(height)
    if W <= 0 or H <= 0 or int(max_radius) < 1:
        raise ValueError("gs_render: need width, height > 0 and max_radius ≥ 1")
    pose = np.asarray(pose, np.float64)
    K = np.asarray(K, np.float64)
    Rw, tw = pose[:3, :3], pose[:3, 3]
    mu_c = gs["mu"] @ Rw.T + tw
    d = -mu_c[:, 2]
    vis = d > 1e-6
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    sky = np.asarray(sky, np.float64)
    out_color = np.empty((H, W, 3))
    out_color[:] = sky
    empty = {"color": out_color, "alpha": np.zeros((H, W)), "depth": np.full((H, W), np.nan), "label": np.full((H, W), -1, np.int64),
             "n_pairs": 0, "n_visible": 0}
    if not vis.any():
        return empty
    # 先に中心だけ写して、半径の上限(max_radius)より遠く窓の外にあるものを落とす(共分散の計算の前に: 窓だけ描く時に効く、結果は同じ)
    uu = np.where(vis, fx * mu_c[:, 0] / np.where(vis, d, 1.0) + cx, np.inf)
    vv = np.where(vis, cy - fy * mu_c[:, 1] / np.where(vis, d, 1.0), np.inf)
    mr = int(max_radius) + 1
    vis &= (uu >= -mr) & (uu <= W + mr) & (vv >= -mr) & (vv <= H + mr)
    if not vis.any():
        return empty
    idx = np.flatnonzero(vis)
    x, y, dd = mu_c[idx, 0], mu_c[idx, 1], d[idx]
    u, v = uu[idx], vv[idx]
    # 3-D 共分散(世界) → カメラ系 → 画像
    Rg = gs["R"][idx]
    Sl = np.zeros((len(idx), 3, 3))
    Sl[:, :2, :2] = gs["cov_t"][idx]
    Sl[:, 2, 2] = gs["sigma_n"][idx] ** 2
    Sw = np.einsum("nij,njk,nlk->nil", Rg, Sl, Rg)
    Sc = np.einsum("ij,njk,lk->nil", Rw, Sw, Rw)
    J = np.zeros((len(idx), 2, 3))
    J[:, 0, 0] = fx / dd
    J[:, 0, 2] = fx * x / dd ** 2
    J[:, 1, 1] = -fy / dd
    J[:, 1, 2] = -fy * y / dd ** 2
    S2 = np.einsum("nij,njk,nlk->nil", J, Sc, J)
    det0 = S2[:, 0, 0] * S2[:, 1, 1] - S2[:, 0, 1] ** 2               # 足し込み前
    S2[:, 0, 0] += _LOW_PASS
    S2[:, 1, 1] += _LOW_PASS
    a, b, c = S2[:, 0, 0], S2[:, 0, 1], S2[:, 1, 1]
    det = a * c - b * b
    # Mip-Splatting(Yu ら 2024)の 2-D 抗エイリアス: 足した 0.3 px² のぶん不透明度を √(det Σ / det(Σ + sI)) 倍にする。
    # 補正しないと画素より細いガウシアン(糸・皿の縁)が不透明のまま 0.55 px 以上に太る(糸が 3 画素の太さで写った)。
    comp = np.sqrt(np.clip(det0, 0.0, None) / np.maximum(det, 1e-300)) if antialias else np.ones(len(det))
    lam = 0.5 * (a + c) + np.sqrt(np.maximum(0.25 * (a - c) ** 2 + b * b, 0.0))
    r = np.minimum(np.ceil(3.0 * np.sqrt(lam)), int(max_radius)).astype(np.int64)
    on = (u + r >= -0.5) & (u - r <= W - 0.5) & (v + r >= -0.5) & (v - r <= H - 0.5) & (det > 0)
    if not on.any():
        return empty
    sel = np.flatnonzero(on)
    ia, ib, ic, idet = c[sel] / det[sel], -b[sel] / det[sel], a[sel] / det[sel], None   # Σ'⁻¹ = [[ia, ib], [ib, ic]]
    del idet
    # 色(Lambert、光はカメラ系)
    l = np.asarray(light, np.float64)
    l = l / np.linalg.norm(l)
    n_c = gs["normal"][idx[sel]] @ Rw.T
    shade = ambient + (1.0 - ambient) * np.clip(np.abs(n_c @ l), 0.0, 1.0)
    col = np.clip(gs["color"][idx[sel]] * shade[:, None], 0.0, 1.0)
    op = gs["opacity"][idx[sel]] * comp[sel]
    us, vs, ds, rs = u[sel], v[sel], dd[sel], r[sel]
    lab = gs["label"][idx[sel]]
    n_pairs = int(((2 * rs + 1) ** 2).sum())
    if n_pairs > int(max_pairs):
        raise ValueError("gs_render: %d splat-pixel pairs > max_pairs %d (raise spacing / max_per_object, or render a window)"
                         % (n_pairs, int(max_pairs)))
    G, PIX, AL = [], [], []
    for rv in np.unique(rs):                                          # 半径ごとに窓の格子を作る(半径の種類は少ない)
        g = np.flatnonzero(rs == rv)
        off = np.arange(-rv, rv + 1)
        ox, oy = np.meshgrid(off, off)
        ox, oy = ox.ravel(), oy.ravel()
        pc = np.rint(us[g])[:, None] + ox[None, :]
        pr = np.rint(vs[g])[:, None] + oy[None, :]
        dx, dy = pc - us[g][:, None], pr - vs[g][:, None]
        q = ia[g][:, None] * dx * dx + 2.0 * ib[g][:, None] * dx * dy + ic[g][:, None] * dy * dy
        al = np.minimum(_ALPHA_MAX, op[g][:, None] * np.exp(-0.5 * q))
        m = (al >= _ALPHA_MIN) & (pc >= 0) & (pc < W) & (pr >= 0) & (pr < H)
        G.append(np.broadcast_to(g[:, None], m.shape)[m])
        PIX.append((pr[m] * W + pc[m]).astype(np.int64))
        AL.append(al[m])
    G = np.concatenate(G)
    PIX = np.concatenate(PIX)
    AL = np.concatenate(AL)
    if len(G) == 0:
        return empty
    order = np.lexsort((ds[G], PIX))                                  # 画素 → 深さ(手前が先)
    G, PIX, AL = G[order], PIX[order], AL[order]
    lg = np.log1p(-AL)
    cs = np.cumsum(lg) - lg                                          # 自分より前(全体)の累積
    start = np.r_[True, PIX[1:] != PIX[:-1]]
    base = np.maximum.accumulate(np.where(start, np.arange(len(PIX)), 0))
    T = np.exp(cs - cs[base])                                         # 同じ画素の中で自分より手前の透過率
    w = AL * T
    npx = W * H
    acc = np.bincount(PIX, weights=w, minlength=npx)
    img = np.stack([np.bincount(PIX, weights=w * col[G, k], minlength=npx) for k in range(3)], axis=1)
    img += (1.0 - acc)[:, None] * sky[None, :]
    dep = np.bincount(PIX, weights=w * ds[G], minlength=npx)
    with np.errstate(invalid="ignore", divide="ignore"):
        depth = np.where(acc >= 0.5, dep / acc, np.nan)
    # 重み最大のガウシアンのラベル(画素ごと)
    ow = np.lexsort((-w, PIX))
    first = np.r_[True, PIX[ow][1:] != PIX[ow][:-1]]
    label = np.full(npx, -1, np.int64)
    label[PIX[ow][first]] = lab[G[ow][first]]
    label[acc < 0.5] = -1
    return {"color": np.clip(img, 0.0, 1.0).reshape(H, W, 3), "alpha": acc.reshape(H, W), "depth": depth.reshape(H, W),
            "label": label.reshape(H, W), "n_pairs": n_pairs, "n_visible": int(len(sel))}


def gs_render_fn(gs: dict, **render_kw):
    """``render_fn(world, cam) → (H, W, 3)``(:func:`kendamaworld.camera_perceiver` の描画の差し替え口)を返す: 呼ばれるたびに
    :func:`gs_update` で世界のいまの頂点へガウシアンを付け直し、``cam``(dict: pose, K, width, height)で :func:`gs_render` する。
    ``render_kw`` は gs_render へそのまま渡す。属性 ``n_calls``・``n_pairs``(累計)を持つ。"""
    if not isinstance(gs, dict) or "face" not in gs:
        raise ValueError("gs_render_fn: gs must come from gs_from_world")

    def render(world, cam):
        gs_update(gs, world)
        r = gs_render(gs, cam["pose"], cam["K"], int(cam["width"]), int(cam["height"]), **render_kw)
        render.n_calls += 1
        render.n_pairs += r["n_pairs"]
        return r["color"]

    render.n_calls = 0
    render.n_pairs = 0
    return render
