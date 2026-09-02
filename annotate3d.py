# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate3d — 3-D のアンカーを画像に射影して矢印・引き出し線・寸法を描く図注 op。

学術図では「メッシュのこの点がこれ」「この距離が 10 mm」を、**描いた絵の上に**
矢印や線で示す。3-D の点を持っている側(点群・メッシュ・姿勢推定の結果)が
2-D の画素座標を手で計算するのは間違いの元(軸の向き・主点・-Z 慣習)なので、
**射影を 1 か所に閉じ込め**、描くのは :mod:`annotate` の 2-D 部品に任せる。

## カメラの慣習(:mod:`render3d` と同一)

* ``pose`` は **4x4 の object→camera 行列**(:func:`render3d.look_at` の返り)。
  ``(R, t)`` の 2-tuple も受け、同じ意味(``X_c = R X + t``)に組み直す。
* カメラは **local -Z を見る**(OpenGL / gluLookAt)。前方距離 ``z = -X_c[2]``。
* ``K`` は 3x3 ピンホール。画素中心が整数座標(``cx = (W-1)/2``、
  :func:`render3d.intrinsics_from_fov`)。
* 射影(閉形式): ``u = fx * X_c[0] / z + cx``、``v = cy - fy * X_c[1] / z``。
  :mod:`tests.test_annotate3d` は既知カメラ・既知点でこの式との一致を 1e-9 で
  確かめる。

:func:`camera.project_points` は **+Z を見る**別慣習(OpenCV 流)なので、その
姿勢をここへ渡すと点が「カメラの後ろ」と判定される。:func:`render3d.render_mesh`
に渡した ``pose``/``intrinsics`` をそのまま渡すのが正しい使い方。

## 遮蔽(occlusion)

``depth=`` に :func:`render3d.render_mesh` の ``depth``(前方距離、背景は inf)を
渡すと、アンカーの前方距離 ``z`` と、その画素の深度 ``d`` を比べて
``d < z * (1 - occlusion_tol)`` なら **隠れている**と判定する。隠れたアンカーは
**破線 + 白抜き印**で描く(消さない ―― 「そこにある」ことは示す)。

## 規律

* fail-closed: カメラの後ろの点・非有限・退化した姿勢は ValueError。
* 全 op は :mod:`annotate` と同じく入力を破壊せず新しい配列を返す(float [0,1])。
* 決定的(乱数なし)。
"""
from __future__ import annotations

import math

import numpy as np

import annotate as A

__all__ = [
    "project_anchors", "annotate3d_project",
    "annotate3d_arrow", "annotate3d_label", "annotate3d_scale_bar",
    "annotate3d_axes", "annotate3d_bbox", "annotate3d_measure",
]

#: 前方距離がこれ以下の点は「カメラ面上/後ろ」として拒否する。
_NEAR_EPS = 1e-9


# ------------------------------------------------------------------ #
# 射影(1 か所)
# ------------------------------------------------------------------ #

def _pose44(pose):
    """``pose`` を 4x4 の object→camera 行列にする(``(R, t)`` も受ける)。"""
    if isinstance(pose, (tuple, list)) and len(pose) == 2:
        R = np.asarray(pose[0], dtype=np.float64)
        t = np.asarray(pose[1], dtype=np.float64).ravel()
        if R.shape != (3, 3) or t.size != 3:
            raise ValueError(f"pose as (R, t) needs R (3,3) and t (3,) (got {R.shape}, {t.shape})")
        P = np.eye(4, dtype=np.float64)
        P[:3, :3] = R
        P[:3, 3] = t
    else:
        P = np.asarray(pose, dtype=np.float64)
        if P.shape != (4, 4):
            raise ValueError(f"pose must be a 4x4 matrix or (R, t) (got shape {P.shape})")
    if not np.all(np.isfinite(P)):
        raise ValueError("pose contains non-finite values")
    if abs(float(np.linalg.det(P[:3, :3]))) < 1e-9:
        raise ValueError("pose rotation is degenerate (near-zero determinant)")
    return P


def _K33(K):
    M = np.asarray(K, dtype=np.float64)
    if M.shape != (3, 3):
        raise ValueError(f"K must be a 3x3 intrinsics matrix (got shape {M.shape})")
    if not np.all(np.isfinite(M)):
        raise ValueError("K contains non-finite values")
    if abs(M[0, 0]) < 1e-12 or abs(M[1, 1]) < 1e-12:
        raise ValueError("K has a zero focal length (fx or fy)")
    return M


def _points3(p, name="points", min_n=1):
    a = np.asarray(p, dtype=np.float64)
    if a.ndim == 1 and a.size == 3:
        a = a[None, :]
    if a.ndim != 2 or a.shape[1] != 3:
        raise ValueError(f"{name} must be (N, 3) or (3,) (got shape {a.shape})")
    if a.shape[0] < min_n:
        raise ValueError(f"{name} needs at least {min_n} point(s) (got {a.shape[0]})")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} contains non-finite values")
    return a


def _project(points, P, K):
    """object 座標 (N,3) → ``(uv (N,2), z (N,))``。z は前方距離(後ろは負)。"""
    Xc = points @ P[:3, :3].T + P[:3, 3]
    z = -Xc[:, 2]
    safe = np.where(np.abs(z) < _NEAR_EPS, np.nan, z)
    u = K[0, 0] * (Xc[:, 0] / safe) + K[0, 1] * (Xc[:, 1] / safe) + K[0, 2]
    v = K[1, 2] - K[1, 1] * (Xc[:, 1] / safe)
    return np.stack([u, v], axis=1), z


def _depth_image(depth, shape=None):
    if depth is None:
        return None
    d = np.asarray(depth, dtype=np.float64)
    if d.ndim != 2:
        raise ValueError(f"depth must be a 2-D (H,W) distance image (got shape {d.shape})")
    if shape is not None and tuple(d.shape) != tuple(shape):
        raise ValueError(f"depth shape {d.shape} does not match the image {tuple(shape)}")
    if np.any(np.isnan(d)):
        raise ValueError("depth holds NaN — use +inf for background (render_mesh does)")
    return d


def project_anchors(points, pose, K, depth=None, shape=None, occlusion_tol=0.01):
    """3-D の点を画素へ射影し、前方 / 画像内 / 遮蔽の判定を付ける(表を返す)。

    Parameters
    ----------
    points : (N, 3) or (3,)
        object 座標。
    pose : (4,4) or (R, t)
        object→camera(:func:`render3d.look_at` の慣習、-Z を見る)。
    K : (3,3)
        内部行列。
    depth : (H, W) or None
        :func:`render3d.render_mesh` の ``depth``(前方距離、背景 inf)。
        渡すと ``hidden`` を判定する。
    shape : (H, W) or None
        画像の大きさ(``depth`` があればそれから取る)。``in_image`` に使う。
    occlusion_tol : float
        ``d < z * (1 - tol)`` で隠れ判定(z-buffer の離散化ぶんの許容)。

    Returns
    -------
    dict
        ``{"uv": (N,2), "depth": (N,), "in_front": bool (N,), "in_image": bool (N,),
        "hidden": bool (N,), "visible": bool (N,)}``。``uv`` は後ろの点で NaN。
        ``hidden`` は depth が無ければ全て False、``in_image`` は shape も depth も
        無ければ全て True(判定していない)。

    Raises
    ------
    ValueError
        形・非有限・退化姿勢・depth の形の不一致・tol が [0,1) の外。
    """
    P = _pose44(pose)
    Km = _K33(K)
    pts = _points3(points)
    tol = A._num(occlusion_tol, "occlusion_tol", lo=0.0)
    if tol >= 1.0:
        raise ValueError(f"occlusion_tol must be < 1 (got {tol})")
    d = _depth_image(depth)
    if d is not None:
        shape = d.shape
    uv, z = _project(pts, P, Km)
    in_front = z > _NEAR_EPS
    n = pts.shape[0]
    if shape is not None:
        H, W = A._shape2(shape)
        with np.errstate(invalid="ignore"):
            in_image = in_front & (uv[:, 0] >= 0) & (uv[:, 0] <= W - 1) & \
                (uv[:, 1] >= 0) & (uv[:, 1] <= H - 1)
    else:
        in_image = np.ones(n, dtype=bool)
    hidden = np.zeros(n, dtype=bool)
    if d is not None:
        for i in np.flatnonzero(in_front & in_image):
            c, r = int(round(uv[i, 0])), int(round(uv[i, 1]))
            dz = d[min(max(r, 0), d.shape[0] - 1), min(max(c, 0), d.shape[1] - 1)]
            hidden[i] = bool(np.isfinite(dz) and dz < z[i] * (1.0 - tol))
    return {"uv": uv, "depth": z, "in_front": in_front, "in_image": in_image,
            "hidden": hidden, "visible": in_front & in_image & ~hidden}


def annotate3d_project(points, pose, K, depth=None, shape=None, occlusion_tol=0.01):
    """table(dict)を返す: 3-D 点の画素座標・前方距離・画像内/遮蔽の判定(:func:`project_anchors`)。"""
    return project_anchors(points, pose, K, depth=depth, shape=shape,
                           occlusion_tol=occlusion_tol)


# ------------------------------------------------------------------ #
# 描く
# ------------------------------------------------------------------ #

def _need_front(tab, names):
    for i, name in enumerate(names):
        if not tab["in_front"][i]:
            raise ValueError(
                f"{name} lies on or behind the camera plane (front distance "
                f"{tab['depth'][i]:.3g}) — it has no pixel; check that pose is the "
                "render3d (look down -Z) convention, not camera.project_points (+Z)")


def _uv(tab, i):
    return float(tab["uv"][i, 0]), float(tab["uv"][i, 1])


_HIDDEN_DASH = (5.0, 4.0)


def annotate3d_arrow(img, p0, p1, pose, K, depth=None, color="emphasis", width=2,
                     head_len=12.0, head_width=9.0, occlusion_tol=0.01, scheme="okabe_ito"):
    """画像(image2d)を返す: 3-D の ``p0`` から ``p1`` へ、射影した矢印を描く。

    ``depth`` を渡し**両端とも隠れている**なら破線で描く(矢じりは半透明)。

    Raises
    ------
    ValueError
        端点がカメラの後ろ / 一致 / 両端とも画像の外、姿勢・K の不正。
    """
    a = A._prep(img)
    tab = project_anchors(np.vstack([_points3(p0, "p0"), _points3(p1, "p1")]), pose, K,
                          depth=depth, shape=a.shape[:2], occlusion_tol=occlusion_tol)
    _need_front(tab, ("p0", "p1"))
    q0, q1 = _uv(tab, 0), _uv(tab, 1)
    if math.hypot(q1[0] - q0[0], q1[1] - q0[1]) < 1e-9:
        raise ValueError("p0 and p1 project to the same pixel — the arrow has no direction "
                         "(the two points lie on one ray through the camera)")
    if depth is not None and tab["hidden"].all():
        w = A._num(width, "width", lo=1)
        span = math.hypot(q1[0] - q0[0], q1[1] - q0[1])
        hl, hw = float(head_len), float(head_width)
        if hl > 0.8 * span:
            k = 0.8 * span / hl
            hl, hw = hl * k, hw * k
        tri, base = A._head_polygon(q0, q1, hl, hw)
        a = A._aa_polyline(a, [q0, base], color, width=w, dash=_HIDDEN_DASH, scheme=scheme)
        return A.filled_polygon(a, tri, color=color, alpha=0.5, scheme=scheme)
    return A.arrow(a, q0, q1, color=color, width=width, head_len=head_len,
                   head_width=head_width, scheme=scheme)


def annotate3d_label(img, text, anchor, pose, K, depth=None, offset=(26.0, -22.0),
                     color="emphasis", width=1.5, cap_size=3.0, font_size=12, pad=4,
                     box_alpha=0.72, text_color=None, occlusion_tol=0.01,
                     scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: 3-D のアンカーに引き出し線つきの文字を付ける。

    文字はアンカーの画素から ``offset`` [px] ずらした位置(``offset[0]`` の符号で
    左右のアンカーを選ぶ)。``depth`` で隠れていると分かれば**破線 + 白抜きの印**。

    Raises
    ------
    ValueError
        アンカーがカメラの後ろ / 画像の外、文字が収まらない、姿勢・K の不正。
    """
    a = A._prep(img)
    tab = project_anchors(_points3(anchor, "anchor"), pose, K, depth=depth,
                          shape=a.shape[:2], occlusion_tol=occlusion_tol)
    _need_front(tab, ("anchor",))
    if not tab["in_image"][0]:
        raise ValueError(f"anchor projects to {tuple(round(v, 1) for v in _uv(tab, 0))}, outside "
                         f"the {a.shape[1]}x{a.shape[0]} image")
    ox, oy = A._pt(offset, "offset")
    x, y = _uv(tab, 0)
    txy = (x + ox, y + oy)
    hidden = bool(tab["hidden"][0])
    w = A._num(width, "width", lo=0.5)
    cap = A._num(cap_size, "cap_size", lo=0.0)
    a = A._aa_polyline(a, [(x, y), txy], color, width=w,
                       dash=_HIDDEN_DASH if hidden else None, scheme=scheme)
    if cap > 0:
        a = A._aa_disk(a, (x, y), cap, color, scheme=scheme, ring=(1.5 if hidden else 0.0))
    anch = "lm" if ox > 0 else ("rm" if ox < 0 else ("cb" if oy < 0 else "ct"))
    return A.text_box(a, str(text), txy, color=color, anchor=anch, pad=pad,
                      font_size=font_size, box_alpha=box_alpha, text_color=text_color,
                      font_path=font_path, scheme=scheme)


def _bar_with_ticks(a, q0, q1, color, width, tick, scheme, dash=None):
    a = A._aa_polyline(a, [q0, q1], color, width=width, dash=dash, scheme=scheme)
    dx, dy = q1[0] - q0[0], q1[1] - q0[1]
    n = math.hypot(dx, dy)
    if tick > 0 and n > 1e-9:
        px, py = -dy / n * tick / 2.0, dx / n * tick / 2.0
        for q in (q0, q1):
            a = A._aa_polyline(a, [(q[0] - px, q[1] - py), (q[0] + px, q[1] + py)], color,
                               width=width, scheme=scheme)
    return a


def annotate3d_scale_bar(img, origin, direction, length, pose, K, unit="", depth=None,
                         color="neutral", width=2.0, tick=8.0, font_size=12,
                         label_fmt="{:g}", box_alpha=0.55, text_color=None,
                         occlusion_tol=0.01, scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: メッシュ単位で ``length`` のバーを面上に置いて射影する。

    バーは ``origin`` から ``direction``(正規化)に ``length`` 進む 3-D 線分で、
    **射影後の画素長は視線に対する傾きで縮む**(遠近と短縮を正直に見せる)。
    像面に平行なら画素長は ``f * length / z`` ―― tests が確かめる。

    Raises
    ------
    ValueError
        direction がゼロ、length が非正、端点がカメラの後ろ / 画像の外。
    """
    a = A._prep(img)
    o = _points3(origin, "origin")[0]
    dvec = _points3(direction, "direction")[0]
    n = float(np.linalg.norm(dvec))
    if n < 1e-12:
        raise ValueError("direction is a zero vector")
    L = A._num(length, "length", lo=1e-300)
    p1 = o + dvec / n * L
    tab = project_anchors(np.vstack([o, p1]), pose, K, depth=depth, shape=a.shape[:2],
                          occlusion_tol=occlusion_tol)
    _need_front(tab, ("origin", "bar end"))
    if not tab["in_image"].all():
        raise ValueError("the scale bar leaves the image — shorten it or move the origin")
    q0, q1 = _uv(tab, 0), _uv(tab, 1)
    w = A._num(width, "width", lo=0.5)
    t = A._num(tick, "tick", lo=0.0)
    hidden = depth is not None and bool(tab["hidden"].all())
    a = _bar_with_ticks(a, q0, q1, color, w, t, scheme, dash=_HIDDEN_DASH if hidden else None)
    dx, dy = q1[0] - q0[0], q1[1] - q0[1]
    nn = math.hypot(dx, dy)
    nx, ny = (-dy / nn, dx / nn) if nn > 1e-9 else (0.0, -1.0)
    if ny > 0:                                    # 文字は画面上側(row 小)へ
        nx, ny = -nx, -ny
    mid = ((q0[0] + q1[0]) / 2.0 + nx * (t / 2.0 + 4), (q0[1] + q1[1]) / 2.0 + ny * (t / 2.0 + 4))
    text = f"{label_fmt.format(L)} {unit}".rstrip()
    return A.text_box(a, text, mid, color=color, anchor=A._text_anchor_for_direction(nx, ny),
                      pad=3, font_size=font_size, box_alpha=box_alpha, text_color=text_color,
                      font_path=font_path, scheme=scheme)


def annotate3d_axes(img, pose, K, origin=(0.0, 0.0, 0.0), length=1.0, depth=None,
                    labels=("X", "Y", "Z"), colors=("wrong", "right", "reference"), width=2,
                    font_size=11, occlusion_tol=0.01, scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: 世界座標の 3 軸(gnomon)を ``origin`` から射影して描く。

    Raises
    ------
    ValueError
        length が非正、原点や軸端がカメラの後ろ、labels/colors が 3 つでない、
        軸の文字が画像に収まらない。
    """
    a = A._prep(img)
    o = _points3(origin, "origin")[0]
    L = A._num(length, "length", lo=1e-300)
    if len(labels) != 3 or len(colors) != 3:
        raise ValueError("labels and colors must each hold exactly 3 entries")
    ends = np.vstack([o, o + np.array([L, 0, 0]), o + np.array([0, L, 0]), o + np.array([0, 0, L])])
    tab = project_anchors(ends, pose, K, depth=depth, shape=a.shape[:2],
                          occlusion_tol=occlusion_tol)
    _need_front(tab, ("origin", "x end", "y end", "z end"))
    q0 = _uv(tab, 0)
    for i in range(3):
        q1 = _uv(tab, i + 1)
        if math.hypot(q1[0] - q0[0], q1[1] - q0[1]) < 1e-9:
            continue                                   # 軸が視線に一致(点に潰れる)
        a = A.arrow(a, q0, q1, color=colors[i], width=width, head_len=8.0, head_width=6.0,
                    scheme=scheme)
        ux, uy = q1[0] - q0[0], q1[1] - q0[1]
        nn = math.hypot(ux, uy)
        txy = (q1[0] + ux / nn * (font_size * 0.7), q1[1] + uy / nn * (font_size * 0.7))
        a = A.text_box(a, str(labels[i]), txy, color=colors[i], anchor="cm", pad=2,
                       font_size=font_size, box_alpha=0.0, font_path=font_path, scheme=scheme)
    return a


_BOX_EDGES = ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
              (0, 4), (1, 5), (2, 6), (3, 7))


def annotate3d_bbox(img, bounds, pose, K, depth=None, color="emphasis", width=1.5,
                    occlusion_tol=0.01, scheme="okabe_ito"):
    """画像(image2d)を返す: 軸平行の 3-D 箱 ``((xmin,ymin,zmin),(xmax,ymax,zmax))`` の 12 辺を射影して描く。

    ``depth`` を渡すと、**両端が隠れている辺**を破線にする。

    Raises
    ------
    ValueError
        bounds の形 / min > max、角がカメラの後ろ。
    """
    a = A._prep(img)
    b = np.asarray(bounds, dtype=np.float64)
    if b.shape != (2, 3):
        raise ValueError(f"bounds must be ((xmin,ymin,zmin),(xmax,ymax,zmax)) (got shape {b.shape})")
    if not np.all(np.isfinite(b)):
        raise ValueError("bounds contain non-finite values")
    if np.any(b[1] < b[0]):
        raise ValueError(f"bounds max must be >= min on every axis (got {b.tolist()})")
    corners = np.array([[b[i, 0], b[j, 1], b[k, 2]] for i in (0, 1) for j in (0, 1) for k in (0, 1)])
    tab = project_anchors(corners, pose, K, depth=depth, shape=a.shape[:2],
                          occlusion_tol=occlusion_tol)
    _need_front(tab, tuple(f"corner {i}" for i in range(8)))
    w = A._num(width, "width", lo=0.5)
    for i, j in _BOX_EDGES:
        hid = depth is not None and bool(tab["hidden"][i] and tab["hidden"][j])
        a = A._aa_polyline(a, [_uv(tab, i), _uv(tab, j)], color, width=w,
                           dash=_HIDDEN_DASH if hid else None, scheme=scheme)
    return a


def annotate3d_measure(img, p0, p1, pose, K, unit="", depth=None, color="emphasis",
                       width=1.5, tick=8.0, font_size=12, label_fmt="{:.3g}", box_alpha=0.6,
                       text_color=None, occlusion_tol=0.01, scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: 3-D の 2 点間距離(メッシュ単位)を、射影した線と値で示す。

    値は ``|p1 - p0|``(3-D、閉形式)。画素上の長さは短縮しても値は変わらない。

    Raises
    ------
    ValueError
        2 点が一致、端点がカメラの後ろ / 画像の外。
    """
    a = A._prep(img)
    a0, a1 = _points3(p0, "p0")[0], _points3(p1, "p1")[0]
    dist = float(np.linalg.norm(a1 - a0))
    if dist < 1e-12:
        raise ValueError("p0 and p1 coincide — nothing to measure")
    tab = project_anchors(np.vstack([a0, a1]), pose, K, depth=depth, shape=a.shape[:2],
                          occlusion_tol=occlusion_tol)
    _need_front(tab, ("p0", "p1"))
    if not tab["in_image"].all():
        raise ValueError("a measured point projects outside the image")
    q0, q1 = _uv(tab, 0), _uv(tab, 1)
    w = A._num(width, "width", lo=0.5)
    t = A._num(tick, "tick", lo=0.0)
    hidden = depth is not None and bool(tab["hidden"].all())
    a = _bar_with_ticks(a, q0, q1, color, w, t, scheme, dash=_HIDDEN_DASH if hidden else None)
    for q, h in zip((q0, q1), tab["hidden"]):
        a = A._aa_disk(a, q, 3.0, color, scheme=scheme, ring=(1.5 if (depth is not None and h) else 0.0))
    dx, dy = q1[0] - q0[0], q1[1] - q0[1]
    nn = math.hypot(dx, dy)
    nx, ny = (-dy / nn, dx / nn) if nn > 1e-9 else (0.0, -1.0)
    if ny > 0:
        nx, ny = -nx, -ny
    mid = ((q0[0] + q1[0]) / 2.0 + nx * (t / 2.0 + 4), (q0[1] + q1[1]) / 2.0 + ny * (t / 2.0 + 4))
    text = f"{label_fmt.format(dist)} {unit}".rstrip()
    return A.text_box(a, text, mid, color=color, anchor=A._text_anchor_for_direction(nx, ny),
                      pad=3, font_size=font_size, box_alpha=box_alpha, text_color=text_color,
                      font_path=font_path, scheme=scheme)
