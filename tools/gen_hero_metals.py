# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事図: 加工された金属表面とガラスの光学(2026-09-04)。

ユーザーの要望 ――「光学的にガラスや鏡面を扱う op が沢山あると良い」「いろいろ加工された
いろんな素材の金属表面を再現できると良い」―― への答え。

**世界は無彩色**にしてある。環境も床の市松も灰色しか使っていない。それでも金は黄色く、
銅は赤く、ガラスの縁には虹が出る ―― 色はすべて **複素屈折率 n+ik の Fresnel** と
**硝材の分散**から出ている。「色を塗る」方式との差がこの 1 枚で分かるように作った。

奥行きは実際にレイを飛ばして作る(法線マップに陰影を付けたのでは、透過も映り込みも
出ないため)。手前の 2 球はガラスで、**床の市松と奥の金属球が上下反転して透けて見える**。
これが屈折。厚いところほど暗いのが Beer–Lambert 吸収、縁の色づきが分散である。

上段 = 3-D シーン(材質 x 仕上げ + ガラス)、下段 = その物理の検算 4 枚。

Run: py -3.11 tools/gen_hero_metals.py
出力: docs/articles/assets/hero_metals.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import glassmirror as G  # noqa: E402
import matappear as M  # noqa: E402
import metalfinish as MF  # noqa: E402
import raytrace as RT  # noqa: E402

OUT = ROOT / "docs" / "articles" / "assets" / "hero_metals.png"
FONT = "C:/Windows/Fonts/YuGothB.ttc"

FLOOR_Y = -0.90
RGB_NM = (0.610, 0.550, 0.465)          # R/G/B の代表波長 [µm](分散をこの 3 点で解く)
UP = np.array([0.0, 1.0, 0.0])


# --------------------------------------------------------------------------- #
# シーン定義
# --------------------------------------------------------------------------- #
def _metal(metal, finish, label):
    return {"kind": "metal", "metal": metal, "finish": finish, "label": label}


def _glass(glass, sigma):
    return {"kind": "glass", "glass": glass, "sigma": float(sigma)}


SPHERES = [
    # 奥列: 材質 x 仕上げ(左から)
    (np.array([-1.86, -0.48, -0.35]), 0.42, _metal("al", "linear", "アルミ ヘアライン")),
    (np.array([-0.62, -0.48, -0.35]), 0.42, _metal("cr", "circular", "クロム 旋盤目")),
    (np.array([0.62, -0.48, -0.35]), 0.42, _metal("au", "crosshatch", "金 ローレット")),
    (np.array([1.86, -0.48, -0.35]), 0.42, _metal("ag", "random", "銀 梨地")),
    # 手前: ガラス(左 = 無吸収の N-BK7 / 右 = 高分散の N-SF11 に吸収を入れたもの)。
    # 奥の球に重ねてあるのは、**金属球が上下反転して透ける**のを見せるため
    (np.array([-0.60, -0.53, 1.25]), 0.37, _glass("N-BK7", 0.0)),
    (np.array([0.60, -0.53, 1.25]), 0.37, _glass("N-SF11", 0.9)),
]

# 硝材ごとの RGB 屈折率(Sellmeier)。ここが虹の出どころで、手で色を置いてはいない
NRGB = {g: np.array([float(RT.refractive_index(g, w)) for w in RGB_NM])
        for g in ("N-BK7", "N-SF11")}


def _smoothbox(a, c, half, soft):
    """|a-c| が half 以内で 1、soft の幅で 0 に落ちる窓(境界がぼけると映り込みが伸びて見える)。"""
    t = np.clip((half + soft - np.abs(a - c)) / max(soft, 1e-9), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def environment(d):
    """手続き的なスタジオ環境(方向 → 放射輝度)。**無彩色**。

    金属の色は環境ではなく Fresnel(n,k) から来る、という主張を保つために環境に色を
    付けない。ソフトボックス 2 枚と天地の明暗だけで、映り込みの伸び方が読めるようにする。
    """
    up = np.clip(d[..., 1], -1.0, 1.0)
    az = np.arctan2(d[..., 0], d[..., 2])
    el = np.arcsin(up)
    env = 0.020 + 0.14 * np.clip(up, 0.0, 1.0) ** 1.5
    env = env + 12.0 * _smoothbox(az, -0.85, 0.34, 0.22) * _smoothbox(el, 0.66, 0.22, 0.20)
    env = env + 3.2 * _smoothbox(az, 1.30, 0.18, 0.18) * _smoothbox(el, 0.26, 0.40, 0.18)
    env = env + 0.45 * _smoothbox(el, 0.015, 0.012, 0.035)       # 細い水平の帯(仕上げの伸びが読める)
    return env


# 主光源の向き(環境の主ソフトボックスと同じ方位・仰角)。影と床の直接光はこれで作る
_KEY_AZ, _KEY_EL = -0.85, 0.66
KEY_DIR = np.array([np.sin(_KEY_AZ) * np.cos(_KEY_EL), np.sin(_KEY_EL),
                    np.cos(_KEY_AZ) * np.cos(_KEY_EL)])


def shadow(p, samples=5, softness=0.10):
    """主光源へ向かう可視率(0..1)。影が無いと球が床から浮いて見えるので、面光源を模して柔らかく。"""
    vis = np.zeros(p.shape[:1])
    rng = np.random.default_rng(3)
    offs = rng.normal(scale=softness, size=(samples, 3))
    offs[0] = 0.0
    for off in offs:
        ld = _normalize((KEY_DIR + off)[None])[0]
        ld = np.broadcast_to(ld, p.shape)
        blocked = np.zeros(p.shape[:1], bool)
        for c, r, _m in SPHERES:
            blocked |= np.isfinite(_sphere_t(p + 1e-3 * ld, ld, c, r))
        vis += ~blocked
    return vis / samples


def checker(p, t):
    """床の市松(無彩色)。遠方は環境色へ溶かしてモアレを抑える。"""
    c = ((np.floor(p[..., 0] / 0.55) + np.floor(p[..., 2] / 0.55)) % 2.0)
    base = 0.09 + 0.46 * c
    fade = np.exp(-np.maximum(t - 3.0, 0.0) / 7.0)
    return base * fade + 0.16 * (1.0 - fade)


# --------------------------------------------------------------------------- #
# 交差判定
# --------------------------------------------------------------------------- #
def _sphere_t(o, d, c, r, inside=False):
    oc = o - c
    b = (oc * d).sum(-1)
    cc = (oc * oc).sum(-1) - r * r
    disc = b * b - cc
    ok = disc > 0.0
    sq = np.sqrt(np.maximum(disc, 0.0))
    t = (-b + sq) if inside else np.where(-b - sq > 1e-4, -b - sq, -b + sq)
    return np.where(ok & (t > 1e-4), t, np.inf)


def _plane_t(o, d):
    dy = d[..., 1]
    safe = np.where(np.abs(dy) < 1e-9, 1e-9, dy)
    t = (FLOOR_Y - o[..., 1]) / safe
    return np.where((np.abs(dy) > 1e-9) & (t > 1e-4), t, np.inf)


def _normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _tangent(n, p, c, finish):
    """球面上の仕上げの接線場(= 加工の目の向き)と、目に直交する向き。"""
    if finish == "circular":                       # 旋盤の同心目: 縦軸まわりの周方向
        t = np.cross(np.broadcast_to(UP, n.shape), n)
    else:                                          # ヘアライン/交差目: 世界 x を面に射影
        ax = np.array([1.0, 0.0, 0.0])
        t = ax - (n * ax).sum(-1, keepdims=True) * n
    bad = np.linalg.norm(t, axis=-1) < 1e-6        # 極では退化するので別軸で埋める
    if bad.any():
        alt = np.array([0.0, 0.0, 1.0])
        t = np.where(bad[..., None], alt - (n * alt).sum(-1, keepdims=True) * n, t)
    t = _normalize(t)
    return t, _normalize(np.cross(n, t))


def _grooved(n, p, c, r, finish):
    """加工痕そのものを法線に刻む(目に**直交する**方向へ周期的に傾ける)。"""
    if finish == "random":
        return n
    t, b = _tangent(n, p, c, finish)
    q = (p - c) / r
    if finish == "circular":
        u = np.arccos(np.clip(q[..., 1], -1.0, 1.0)) * r          # 極角に沿って刻む
    else:
        u = np.arctan2(q[..., 2], q[..., 1]) * r                  # x 軸まわりの角度
    amp = 0.05 if finish != "crosshatch" else 0.04
    out = n + (amp * np.sin(2 * np.pi * u / 0.030))[..., None] * b
    if finish == "crosshatch":                                    # 二本目の目を直交方向に
        v = np.arctan2(q[..., 0], q[..., 1]) * r
        out = out + (amp * np.sin(2 * np.pi * v / 0.030))[..., None] * t
    return _normalize(out)


# --------------------------------------------------------------------------- #
# 追跡
# --------------------------------------------------------------------------- #
def _gauss_pairs(n, seed=7):
    """低食い違い列 → 標準正規。全画素で同じ位置を使うので粒状ノイズが出ない。"""
    i = np.arange(n) + 0.5
    rev = np.array([int(format(k, "022b")[::-1], 2) for k in range(n)]) / 2.0 ** 22
    u2 = (rev + np.random.default_rng(seed).random()) % 1.0
    r = np.sqrt(-2.0 * np.log(np.clip(i / n, 1e-12, 1.0)))
    return r * np.cos(2 * np.pi * u2), r * np.sin(2 * np.pi * u2)


_SAMPLES = {3: 16, 2: 4, 1: 1, 0: 1}


def trace(o, d, depth):
    """RGB 放射輝度を返す。o,d は (M,3)。depth=0 は環境のみ(打ち切り)。"""
    o = np.atleast_2d(o).astype(np.float64)
    d = _normalize(np.atleast_2d(d).astype(np.float64))
    col = np.zeros(o.shape[:1] + (3,))
    if o.shape[0] == 0:
        return col

    ts = np.stack([_sphere_t(o, d, c, r) for c, r, _m in SPHERES] + [_plane_t(o, d)], 0)
    idx = ts.argmin(0)
    tmin = np.take_along_axis(ts, idx[None], 0)[0]
    hit = np.isfinite(tmin)

    miss = ~hit
    if miss.any():
        col[miss] = environment(d[miss])[..., None]

    # --- 床 -----------------------------------------------------------------
    fl = hit & (idx == len(SPHERES))
    if fl.any():
        p = o[fl] + tmin[fl][..., None] * d[fl]
        albedo = checker(p, tmin[fl])
        direct = 1.35 * max(float(KEY_DIR[1]), 0.0) * shadow(p)   # 主光源 + 落ち影
        shade = albedo * (0.16 + direct)
        if depth > 0:                       # 床にも空が映る(弱い鏡面) = 奥行きの手がかり
            rr = d[fl] - 2.0 * (d[fl] * UP).sum(-1, keepdims=True) * UP
            shade = shade + 0.04 * environment(_normalize(rr))
        col[fl] = shade[..., None]

    # --- 球 -----------------------------------------------------------------
    for k, (c, r, mat) in enumerate(SPHERES):
        m = hit & (idx == k)
        if not m.any():
            continue
        t = tmin[m]
        p = o[m] + t[..., None] * d[m]
        n = _normalize(p - c)
        di = d[m]
        if mat["kind"] == "metal":
            col[m] = _shade_metal(p, n, di, c, r, mat, depth)
        else:
            col[m] = _shade_glass(p, n, di, c, r, mat, depth)
    return col


def _shade_metal(p, n, d, c, r, mat, depth):
    """異方性ローブでシーンを引く鏡面。色は metal_mirror_rgb(= Fresnel(n,k))のみ。"""
    finish = mat["finish"]
    ng = _grooved(n, p, c, r, finish)
    cat = MF.finish_catalog()[finish]
    ax, ay = float(cat["alpha_x"]), float(cat["alpha_y"])
    t, b = _tangent(ng, p, c, finish)
    refl = d - 2.0 * (d * ng).sum(-1, keepdims=True) * ng

    ns = _SAMPLES[depth]
    gx, gy = _gauss_pairs(ns)
    acc = np.zeros(p.shape[:1] + (3,))
    for a, bb in zip(gx, gy):
        rd = _normalize(refl + (ax * a) * t + (ay * bb) * b)
        acc += (environment(rd)[..., None] if depth <= 1 else trace(p + 1e-4 * ng, rd, depth - 1))
    acc /= ns
    cos_v = np.clip(-(d * ng).sum(-1), 0.0, 1.0)
    return acc * G.metal_mirror_rgb(mat["metal"], cos_v)


def _shade_glass(p, n, d, c, r, mat, depth):
    """入射 Fresnel + 屈折 2 回 + Beer–Lambert。屈折は **RGB それぞれの屈折率**で解く。"""
    nrgb = NRGB[mat["glass"]]
    cos_i = np.clip(-(d * n).sum(-1), 0.0, 1.0)
    out = np.zeros(p.shape[:1] + (3,))

    refl_d = _normalize(d - 2.0 * (d * n).sum(-1, keepdims=True) * n)
    refl = (np.repeat(environment(refl_d)[..., None], 3, -1) if depth <= 1
            else trace(p + 1e-4 * n, refl_d, depth - 1))

    for ch in range(3):
        nk = float(nrgb[ch])
        R = np.asarray(G.fresnel_dielectric(cos_i, 1.0, nk), float)   # 無偏光の反射率
        din, tir = G.refract_rays(d, n, 1.0, nk)                      # 内部へ
        din = _normalize(np.where(tir[..., None], refl_d, din))
        t_exit = _sphere_t(p + 1e-4 * din, din, c, r, inside=True)
        t_exit = np.where(np.isfinite(t_exit), t_exit, 0.0)
        q = p + (t_exit[..., None] + 1e-4) * din
        nq = -_normalize(q - c)                                       # 内側から見た法線
        absorb = np.asarray(G.beer_lambert_transmittance(t_exit, mat["sigma"]), float)
        dout, tir2 = G.refract_rays(din, nq, nk, 1.0)                 # 外へ
        # 全反射した光線は内部で 1 回跳ね返して出す(近似だが、縁が黒く抜けるのを防ぐ)
        bounce = _normalize(din - 2.0 * (din * nq).sum(-1, keepdims=True) * nq)
        dout = _normalize(np.where(tir2[..., None], bounce, dout))
        trans = (environment(dout) if depth <= 1
                 else trace(q + 1e-4 * dout, dout, depth - 1)[:, ch])
        out[:, ch] = R * refl[:, ch] + (1.0 - R) * absorb * trans
    return out


# --------------------------------------------------------------------------- #
def render_scene(width, height, ss=1.5):
    w, h = int(width * ss), int(height * ss)
    eye = np.array([0.0, 0.42, 4.25])
    tgt = np.array([0.0, -0.18, 0.0])
    fwd = _normalize((tgt - eye)[None])[0]
    right = _normalize(np.cross(fwd, UP)[None])[0]
    up = np.cross(right, fwd)
    half = np.tan(np.radians(17.0))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    sx = ((xx + 0.5) / w * 2.0 - 1.0) * half * (w / h)
    sy = (1.0 - (yy + 0.5) / h * 2.0) * half
    d = fwd[None, None] + sx[..., None] * right[None, None] + sy[..., None] * up[None, None]
    d = _normalize(d).reshape(-1, 3)
    o = np.broadcast_to(eye, d.shape)
    col = trace(o, d, 3).reshape(h, w, 3)
    return col


def tonemap(hdr, exposure=1.0):
    """ACES 風の簡易トーンマップ + ガンマ(線形 sRGB → 表示)。"""
    x = np.clip(np.asarray(hdr, np.float64) * float(exposure), 0.0, None)
    a, b, c, dd, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip((x * (a * x + b)) / (x * (c * x + dd) + e), 0.0, 1.0)
    return np.power(y, 1.0 / 2.2)


# --------------------------------------------------------------------------- #
# 極小プロット(依存を増やさない)
# --------------------------------------------------------------------------- #
def plot(w, h, series, ylim=(0.0, 1.0)):
    img = np.full((h, w, 3), 0.065)
    xs = np.concatenate([np.asarray(s[1], float) for s in series])
    x0, x1 = float(xs.min()), float(xs.max())
    y0, y1 = ylim
    for gy in np.linspace(0, 1, 5):
        img[int(np.clip((1.0 - gy) * (h - 1), 0, h - 1))] = 0.155
    for gx in np.linspace(0, 1, 5):
        cc = int(np.clip(gx * (w - 1), 0, w - 1))
        img[:, cc] = np.maximum(img[:, cc], 0.10)
    for _name, X, Y, rgb in series:
        X, Y = np.asarray(X, float), np.asarray(Y, float)
        if len(X) > 1 and X[-1] != X[0]:                     # 幅の分だけ内挿して線を繋ぐ
            gxs = np.linspace(X[0], X[-1], w)
            X, Y = gxs, np.interp(gxs, X, Y)
        cx = np.clip(((X - x0) / max(x1 - x0, 1e-12) * (w - 1)).astype(int), 0, w - 1)
        cy = np.clip(((1.0 - (Y - y0) / max(y1 - y0, 1e-12)) * (h - 1)).astype(int), 0, h - 1)
        for k in range(len(cx) - 1):
            a, b = sorted((cy[k], cy[k + 1]))
            img[a:b + 1, cx[k]] = rgb
        img[cy[-1], cx[-1]] = rgb
    return img, (x0, x1, y0, y1)


def annotate(im, rng, xfmt, yfmt, legend, tick):
    x0, x1, y0, y1 = rng
    dr = ImageDraw.Draw(im)
    w, h = im.size
    for f, txt in ((0.0, xfmt(x0)), (0.5, xfmt(0.5 * (x0 + x1))), (1.0, xfmt(x1))):
        tw = dr.textlength(txt, font=tick)
        dr.text((min(max(f * (w - 1) - tw / 2, 3), w - tw - 3), h - 19), txt, font=tick,
                fill=(152, 154, 160))
    for f, txt in ((1.0, yfmt(y1)), (0.5, yfmt(0.5 * (y0 + y1))), (0.0, yfmt(y0))):
        yy = (1.0 - f) * (h - 1)
        dr.text((4, min(max(yy - 7, 2), h - 32)), txt, font=tick, fill=(152, 154, 160))
    for j, (txt, rgb) in enumerate(legend):
        yy = 6 + j * 17
        dr.rectangle([w - 15, yy + 5, w - 7, yy + 8], fill=tuple(int(255 * v) for v in rgb))
        tw = dr.textlength(txt, font=tick)
        dr.text((w - 21 - tw, yy), txt, font=tick, fill=(208, 210, 216))
    return im


def build_plots(P):
    tick_specs = []
    ang = np.linspace(0.0, 89.5, 400)
    ci = np.cos(np.radians(ang))
    brew = G.brewster_angle_deg(1.0, 1.5168)
    c_s, c_p, c_u = (0.35, 0.65, 1.0), (1.0, 0.62, 0.30), (0.90, 0.90, 0.90)
    fres, r_fres = plot(P, P, [
        ("s", ang, G.fresnel_dielectric(ci, 1.0, 1.5168, "s"), c_s),
        ("p", ang, G.fresnel_dielectric(ci, 1.0, 1.5168, "p"), c_p),
        ("unpol", ang, G.fresnel_dielectric(ci, 1.0, 1.5168), c_u),
        ("brewster", np.full(2, brew), np.array([0.0, 1.0]), (0.42, 0.42, 0.48)),
    ])
    tick_specs.append((fres, r_fres,
                       ["検算: Fresnel 反射率 対 入射角",
                        f"縦線 = Brewster 角 {brew:.1f} 度(p が厳密に 0)"],
                       lambda v: f"{v:.0f}deg", lambda v: f"{v:.1f}",
                       [("s 偏光", c_s), ("p 偏光", c_p), ("無偏光", c_u)]))

    wl = np.linspace(380.0, 780.0, 300)
    mcol = {"ag": (0.92, 0.94, 0.98), "al": (0.45, 0.72, 1.0), "au": (1.0, 0.80, 0.25),
            "cu": (1.0, 0.48, 0.28), "cr": (0.62, 0.62, 0.66)}
    spec = [(m, wl, G.fresnel_conductor(1.0, *G.metal_optical_constants(m, wl)), mcol[m])
            for m in ("ag", "al", "au", "cu", "cr")]
    metals, r_metals = plot(P, P, spec)
    tick_specs.append((metals, r_metals,
                       ["検算: 金属の反射スペクトル", "上のシーンの色はここから出ている"],
                       lambda v: f"{v:.0f}nm", lambda v: f"{v:.1f}",
                       [(m.upper(), mcol[m]) for m in ("ag", "al", "au", "cu", "cr")]))

    pw = np.linspace(400.0, 700.0, 260)
    dev = G.prism_min_deviation_deg(pw, 60.0, "N-BK7")
    band = np.zeros((P, P, 3))
    lo, hi = float(np.nanmin(dev)), float(np.nanmax(dev))
    for k in range(len(pw)):
        colu = int((dev[k] - lo) / max(hi - lo, 1e-12) * (P - 1))
        rgb = np.clip(M.spectrum_to_srgb(pw, np.exp(-0.5 * ((pw - pw[k]) / 8.0) ** 2)), 0.0, None)
        # 単色光は線形 sRGB では色域外に出る。最大で割って色相を保ち、明るさはガンマに任せる
        band[:, colu] = np.maximum(band[:, colu], rgb / max(float(rgb.max()), 1e-12))
    for cc in range(1, P):
        if band[:, cc].max() == 0.0:
            band[:, cc] = band[:, cc - 1]
    d_line = float(G.prism_min_deviation_deg(587.6, 60.0, "N-BK7"))
    tick_specs.append((np.power(np.clip(band, 0.0, 1.0), 1.0 / 2.2), None,
                       ["検算: プリズムの分散(N-BK7 頂角 60 度)",
                        f"左 = 偏角小(赤) → 右 = 偏角大(青)"],
                       None, None, None))

    thick = np.linspace(0.0, 30.0, 300)
    c0, c2, c8 = (0.90, 0.90, 0.90), (0.45, 0.85, 0.55), (0.95, 0.55, 0.40)
    slab, r_slab = plot(P, P, [
        ("0", thick, float(G.slab_transmittance(1.0, 1.0, 1.5168, 1.0, 0.0)) * np.ones_like(thick), c0),
        ("0.02", thick, np.array([float(G.slab_transmittance(1.0, 1.0, 1.5168, dd, 0.02)) for dd in thick]), c2),
        ("0.08", thick, np.array([float(G.slab_transmittance(1.0, 1.0, 1.5168, dd, 0.08)) for dd in thick]), c8),
    ])
    tick_specs.append((slab, r_slab,
                       ["検算: 平板の透過 対 板厚", "右のガラス球が中心ほど暗いのと同じ理由"],
                       lambda v: f"{v:.0f}mm", lambda v: f"{v:.1f}",
                       [("sigma=0", c0), ("sigma=0.02", c2), ("sigma=0.08", c8)]))
    return tick_specs


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.time()
    SW, SH = 1260, 545
    scene = tonemap(render_scene(SW, SH), 1.0)
    print(f"[render] scene {time.time() - t0:.0f}s", flush=True)
    scene_im = Image.fromarray((np.clip(scene, 0, 1) * 255 + 0.5).astype(np.uint8)) \
        .resize((SW, SH), Image.LANCZOS)

    P = 420
    plots = build_plots(P)

    font = ImageFont.truetype(FONT, 21)
    small = ImageFont.truetype(FONT, 15)
    sub = ImageFont.truetype(FONT, 14)
    tick = ImageFont.truetype(FONT, 13)
    T, pad, cap, head = 300, 14, 46, 70
    labels = [s[2]["label"] for s in SPHERES if s[2]["kind"] == "metal"]
    cv = Image.new("RGB", (pad + 4 * (T + pad), head + SH + 48 + pad + T + cap + pad), (17, 19, 23))
    dr = ImageDraw.Draw(cv)
    dr.text((pad, 9), "加工された金属表面とガラスの光学 — 材質(n+ik) x 仕上げ(微小面の向きと粗さ)",
            font=font, fill=(242, 242, 242))
    dr.text((pad, 38), "世界は無彩色(環境も床の市松も灰色のみ)。それでも金は黄色く銅は赤く、ガラスの縁に虹が出る — "
                       "色は Fresnel(n,k) と硝材の分散だけから出ている",
            font=sub, fill=(196, 198, 205))
    cv.paste(scene_im, (pad, head))
    dr.text((pad, head + SH + 4), "奥列 = " + " / ".join(labels)
            + "。手前 = ガラス球(左 N-BK7 無吸収 / 右 N-SF11 + 吸収)",
            font=small, fill=(224, 226, 232))
    dr.text((pad, head + SH + 23),
            "床の市松と奥の金属球が上下反転して透けているのが屈折。中心ほど暗いのが Beer–Lambert 吸収で、"
            "縁の色づきは RGB で屈折率が違うこと(分散)から出ている",
            font=small, fill=(184, 186, 192))

    y0 = head + SH + 48 + pad
    for i, (img, rng, caption, xf, yf, leg) in enumerate(plots):
        im = Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).resize((T, T), Image.LANCZOS)
        if rng is not None:
            im = annotate(im, rng, xf, yf, leg, tick)
        x = pad + i * (T + pad)
        cv.paste(im, (x, y0))
        for j, line in enumerate(caption):
            dr.text((x, y0 + T + 6 + j * 19), line, font=small,
                    fill=(236, 236, 236) if j == 0 else (184, 186, 192))
    cv.save(OUT, optimize=True)
    print(f"[fig] {OUT} {cv.size} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
