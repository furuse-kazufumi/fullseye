# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""interactive_anim3d_viewer — 動く 3-D を 1 枚の HTML で再生する(fs.viewer_anim3d_tab)。

    py -3.11 examples/interactive_anim3d_viewer.py                    # 一時フォルダに書いて検査だけ
    py -3.11 examples/interactive_anim3d_viewer.py --out out/arm.html # 開いて触れる HTML を残す

【この例が示すこと】
3 関節のアーム(旋回 + 肩 + 肘、手先は常に真下)が、床の箱をつかんで別の台へ運ぶ。物理エンジンは
使わず、手先の通り道を決めて逆運動学で関節角を出す(外部依存なし、numpy だけ)。それを

* 物体ごとのメッシュは **1 回だけ**(床・台・旋回台・2 本のリンク・手のひら・2 本の指・箱)、
* コマごとには **剛体の姿勢だけ**(位置 uint16 + 四元数 int16)、

で 1 本の自己完結 HTML にする。同じタブで、手先の残像の軌跡・箱の全軌跡・上から見た距離センサーの
点群(つかむ前と置いた後の 2 回)・段の区切り(近づく/つかむ/運ぶ/置く/離す/戻る)・時系列グラフ
(手先の高さ・指の開き)・**上から見たカメラの高さ画像と、その二値化(op の結果に相当)** を
同じ時間軸で再生する。2-D の画像は無損失の PNG で埋める(画素は 1 つも変えない、間引かない)。

検査(PASS の条件):
* 埋めた姿勢を Python 側で戻すと、位置は量子化の刻みの半分以内、四元数の角度の誤差は 1e-4 rad 未満。
* 戻した姿勢で手先の点を動かしても、真の手先とのずれが刻みから見積もった上限以内。
* PNG で埋めた 2 枚の画像列が、描いた画像と画素ごとに一致する。外部 URL は無い。

EXTEND: 実機やシミュレータの記録なら、物体ごとのメッシュ(ローカル座標)と、コマごとの世界姿勢
(位置 + 四元数 w,x,y,z)を渡すだけ。2-D の列はセンサー画像や op の出力をそのまま ``panes`` へ。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402

pv = fs.pocviewer

# 寸法 [m]
H0, L1, L2, LG = 0.30, 0.40, 0.35, 0.12          # 肩の高さ / 上腕 / 前腕 / 手首から指先
BOX = 0.08                                       # 箱の一辺
FPS, T = 30, 150                                 # 5 秒
A = np.array([0.45, -0.25])                      # 箱の最初の場所(xy)
B = np.array([0.15, 0.48])                       # 置く台(xy)
HOME = np.array([0.30, 0.05, 0.42])              # 手先の待機位置


def _t(ja: str, en: str) -> dict:
    return fs.viewer_text(ja, en)


# --------------------------------------------------------------------------- 形
def box_mesh(lo, hi):
    """軸に沿った直方体(面ごとに頂点を分け、陰影が角でにじまないようにする)。"""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    pos, tri = [], []
    for q in quads:
        k = len(pos)
        pos += [c[i] for i in q]
        tri += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    return np.array(pos), np.array(tri)


def cylinder_mesh(r, h, n=24):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.column_stack([r * np.cos(a), r * np.sin(a)])
    side = np.vstack([np.column_stack([ring, np.zeros(n)]), np.column_stack([ring, np.full(n, h)])])
    tri = [[i, (i + 1) % n, n + (i + 1) % n] for i in range(n)] + [[i, n + (i + 1) % n, n + i] for i in range(n)]
    top0 = len(side)
    top = np.vstack([[0, 0, h], np.column_stack([ring, np.full(n, h)])])
    tri += [[top0, top0 + 1 + i, top0 + 1 + (i + 1) % n] for i in range(n)]
    return np.vstack([side, top]), np.array(tri)


# --------------------------------------------------------------------------- 四元数 (w,x,y,z)
def qz(a):
    return np.array([np.cos(a / 2), 0.0, 0.0, np.sin(a / 2)])


def qy(a):
    return np.array([np.cos(a / 2), 0.0, np.sin(a / 2), 0.0])


def qmul(p, q):
    w1, x1, y1, z1 = p
    w2, x2, y2, z2 = q
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def qmat(q):
    return pv._quat_matrix(np.asarray(q, float))


def quat_angle(p, q):
    """2 つの単位四元数の回転の差 [rad](acos を使わない: 1 付近で丸めの床が出るため)。"""
    p = p / np.linalg.norm(p, axis=-1, keepdims=True)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    q = q * np.where((p * q).sum(-1) < 0, -1.0, 1.0)[..., None]       # q と -q は同じ回転
    return 4 * np.arctan2(np.linalg.norm(p - q, axis=-1), np.linalg.norm(p + q, axis=-1))


# --------------------------------------------------------------------------- 運動
def ease(u):
    return 0.5 - 0.5 * np.cos(np.pi * np.clip(u, 0, 1))


def tip_path():
    """手先の通り道(円柱座標 yaw, r, z で補間して自然な弧に)と指の開き・段。"""
    def cyl(p):
        return np.array([np.arctan2(p[1], p[0]), np.hypot(p[0], p[1]), p[2]])
    zg = BOX / 2 + 0.005                                         # つかむ高さ(箱の中ほど)
    pA_up, pA = np.r_[A, 0.22], np.r_[A, zg]
    pB_up, pB = np.r_[B, 0.22], np.r_[B, zg + 0.012]                  # 台の厚みぶん上で離す
    # (区間の長さ [s], 始点, 終点, 指の開き 始→終, 段の名前)
    segs = [(0.9, HOME, pA_up, 1, 1, ("近づく", "Approach")),
            (0.5, pA_up, pA, 1, 1, None),
            (0.4, pA, pA, 1, 0, ("つかむ", "Grasp")),
            (0.5, pA, pA_up, 0, 0, ("運ぶ", "Transport")),
            (1.1, pA_up, pB_up, 0, 0, None),
            (0.5, pB_up, pB, 0, 0, ("置く", "Place")),
            (0.3, pB, pB, 0, 1, ("離す", "Release")),
            (0.8, pB, HOME, 1, 1, ("戻る", "Return"))]
    t = np.arange(T) / FPS
    tip, grip, events, t0 = np.zeros((T, 3)), np.zeros(T), [], 0.0
    bounds = []
    for dur, p0, p1, g0, g1, name in segs:
        if name:
            events.append({"t": t0, "label": _t(*name)})
        bounds.append((t0, t0 + dur, cyl(p0), cyl(p1), g0, g1))
        t0 += dur
    for i, ti in enumerate(t):
        for s0, s1, c0, c1, g0, g1 in bounds:
            if ti < s1 + 1e-9 or (s0, s1) == bounds[-1][:2]:
                u = ease((ti - s0) / (s1 - s0))
                c = c0 + (c1 - c0) * u
                tip[i] = [c[1] * np.cos(c[0]), c[1] * np.sin(c[0]), c[2]]
                grip[i] = g0 + (g1 - g0) * u
                break
    grasped = (t >= bounds[2][0] + 0.3) & (t < bounds[6][0] + 0.15)     # 指が閉じきってから、開き始めまで
    return t, tip, grip, events, grasped


def ik(wrist):
    """手首の位置 → (旋回, 肩, 肘)。肘を上にする解。届かなければ止める(黙って近い所へ置かない)。"""
    x, y, z = wrist
    yaw = np.arctan2(y, x)
    r, dz = np.hypot(x, y), z - H0
    c2 = (r * r + dz * dz - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if not -1 <= c2 <= 1:
        raise ValueError("手首 %s に届かない" % (wrist,))
    q2 = -np.arccos(c2)
    q1 = np.arctan2(dz, r) - np.arctan2(L2 * np.sin(q2), L1 + L2 * np.cos(q2))
    return yaw, q1, q2


def build():
    t, tip, grip, events, grasped = tip_path()
    floor = box_mesh([-0.35, -0.45, -0.01], [0.85, 0.75, 0.0])
    pad_a = box_mesh([-0.07, -0.07, 0.0], [0.07, 0.07, 0.004])
    pad_b = box_mesh([-0.08, -0.08, 0.0], [0.08, 0.08, 0.012])
    base = cylinder_mesh(0.07, H0)
    link1 = box_mesh([0, -0.03, -0.03], [L1, 0.03, 0.03])
    link2 = box_mesh([0, -0.025, -0.025], [L2, 0.025, 0.025])
    palm = box_mesh([-0.03, -0.09, -0.04], [0.03, 0.09, 0.0])
    finger = box_mesh([-0.012, -0.006, -(LG - 0.04)], [0.012, 0.006, 0.0])
    payload = box_mesh([-BOX / 2] * 3, [BOX / 2] * 3)
    shapes = [("floor", floor, [58, 66, 76]), ("pad_a", pad_a, [176, 112, 60]), ("pad_b", pad_b, [70, 150, 96]),
              ("turret", base, [120, 132, 146]), ("upper_arm", link1, [79, 150, 220]),
              ("forearm", link2, [104, 180, 240]), ("palm", palm, [200, 205, 212]),
              ("finger_l", finger, [230, 230, 236]), ("finger_r", finger, [230, 230, 236]),
              ("box", payload, [240, 176, 64])]
    Bn = len(shapes)
    xyz, quat = np.zeros((T, Bn, 3)), np.zeros((T, Bn, 4))
    quat[..., 0] = 1.0
    xyz[:, 1, :2], xyz[:, 2, :2] = A, B
    box_q = qz(np.arctan2(A[1], A[0]))                              # 箱は放射方向に向いて置いてある
    box_p = np.r_[A, BOX / 2]
    rel = None
    for i in range(T):
        wrist = tip[i] + [0, 0, LG]
        yaw, q1, q2 = ik(wrist)
        qyaw = qz(yaw)
        elbow = np.r_[0, 0, H0] + L1 * np.array([np.cos(q1) * np.cos(yaw), np.cos(q1) * np.sin(yaw), np.sin(q1)])
        quat[i, 3] = qyaw
        xyz[i, 4], quat[i, 4] = [0, 0, H0], qmul(qyaw, qy(-q1))
        xyz[i, 5], quat[i, 5] = elbow, qmul(qyaw, qy(-(q1 + q2)))
        xyz[i, 6], quat[i, 6] = wrist, qyaw
        Ry = qmat(qyaw)
        half = 0.046 + 0.03 * grip[i]                               # 指の中心の、手の中心からの距離
        for k, sgn in ((7, 1), (8, -1)):
            xyz[i, k], quat[i, k] = wrist + Ry @ [0, sgn * half, -0.04], qyaw
        if grasped[i]:
            if rel is None:                                          # つかんだ瞬間の相対姿勢を固定
                rel = (qmat(qyaw).T @ (box_p - wrist), qmul(np.r_[qyaw[0], -qyaw[1:]], box_q))
            box_p, box_q = wrist + Ry @ rel[0], qmul(qyaw, rel[1])
        else:
            if rel is not None:                                      # 離したら台の上に落ち着く
                box_p = np.r_[box_p[:2], 0.012 + BOX / 2]
                rel = None
        xyz[i, 9], quat[i, 9] = box_p, box_q
    bodies = [{"name": n, "pos": m[0], "faces": m[1], "rgb": c} for n, m, c in shapes]
    return t, tip, grip, events, grasped, bodies, xyz, quat


# --------------------------------------------------------------------------- 上から見たカメラ
RES, X0, Y0, IH, IW = 0.0075, -0.15, -0.45, 120, 148


def surface_samples(pos, faces, step):
    """三角形の面を step 間隔ほどで埋める点(ローカル座標)。"""
    out = []
    for a, b, c in faces:
        P0, P1, P2 = pos[a], pos[b], pos[c]
        n = max(2, int(np.ceil(max(np.linalg.norm(P1 - P0), np.linalg.norm(P2 - P0)) / step)) + 1)
        u, v = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n))
        m = (u + v) <= 1
        out.append(P0 + u[m, None] * (P1 - P0) + v[m, None] * (P2 - P0))
    return np.vstack(out)


def height_images(bodies, xyz, quat):
    """真上からの正射影の高さ画像(各画素の最も高い面)。0..0.6 m を 0..255 に。"""
    samples = [surface_samples(b["pos"], b["faces"], RES / 2) for b in bodies]
    R = qmat(quat)                                                     # (T,B,3,3)
    imgs = np.zeros((T, IH, IW), np.uint8)
    for i in range(T):
        hz = np.full(IH * IW, -1.0)
        for k, S in enumerate(samples):
            w = S @ R[i, k].T + xyz[i, k]
            r = np.floor((w[:, 0] - X0) / RES).astype(int)
            c = np.floor((w[:, 1] - Y0) / RES).astype(int)
            ok = (r >= 0) & (r < IH) & (c >= 0) & (c < IW)
            np.maximum.at(hz, r[ok] * IW + c[ok], w[ok, 2])
        imgs[i] = np.rint(np.clip(hz.reshape(IH, IW), 0, 0.6) / 0.6 * 255)
    return imgs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", help="HTML を残す先(省略すると一時フォルダに書いて検査だけ)")
    a = ap.parse_args(argv)

    t, tip, grip, events, grasped, bodies, xyz, quat = build()
    depth = height_images(bodies, xyz, quat)
    lo8, hi8 = int(np.rint(0.02 / 0.6 * 255)), int(np.rint(0.10 / 0.6 * 255))
    mask = (((depth >= lo8) & (depth <= hi8)) * 255).astype(np.uint8)   # 床より高く腕より低い = 置かれた物
    box_px = np.column_stack([(xyz[:, 9, 1] - Y0) / RES - 0.5, (xyz[:, 9, 0] - X0) / RES - 0.5])
    rel_k = int(np.argmax(t >= events[5]["t"] + 0.35))                # 離した後
    rng = np.random.default_rng(0)

    def cloud(k):                                                        # 上から見た距離センサー(雑音 2 mm)
        rr, cc = np.mgrid[0:IH:3, 0:IW:3]                                # センサーの画素ピッチ(3 画素おき)
        z = depth[k][rr, cc] / 255 * 0.6
        p = np.column_stack([X0 + (rr.ravel() + 0.5) * RES, Y0 + (cc.ravel() + 0.5) * RES,
                             z.ravel() + rng.normal(0, 0.002, z.size)])
        return {"k": k, "pos": p, "color": "#80deea", "point_size": 0.006}

    tab = fs.viewer_anim3d_tab(
        "arm", _t("アームが箱を運ぶ", "An arm carries a box"), "passed",
        _t("3 関節のアーム(旋回・肩・肘)が箱をつかみ、台へ運ぶ。逆運動学だけの合成(物理なし)。"
           "右下は真上からの高さ画像と、その二値化(置かれた物だけが残る)。",
           "A three-joint arm (yaw, shoulder, elbow) grasps a box and carries it to a stand. Pure inverse "
           "kinematics (no physics). Below: a top-down height image and its binarisation (only resting objects remain)."),
        t, bodies, xyz, quat,
        trails=[{"body": "palm", "offset": [0, 0, -LG], "color": "#ffd54f", "tail": 1.2,
                 "label": _t("手先(残像 1.2 s)", "Fingertip (1.2 s trail)")},
                {"body": "box", "color": "#4dd0e1", "label": _t("箱の中心", "Box centre")}],
        clouds=[cloud(0), cloud(rel_k)],
        events=events,
        series=[{"label": _t("手先の高さ", "Fingertip height"), "values": tip[:, 2], "lo": 0.0, "hi": 0.5,
                 "unit": "m", "decimals": 3, "color": "#ffd54f"},
                {"label": _t("指の開き", "Finger opening"), "values": grip * 100, "lo": 0.0, "hi": 100.0,
                 "unit": "%", "decimals": 0, "color": "#81c784"}],
        panes=[{"label": _t("真上からの高さ画像(0〜0.6 m)", "Top-down height image (0-0.6 m)"), "frames": depth,
                "boxes": [{"label": _t("箱(真値)", "Box (truth)"), "color": "#4fc3f7", "xy": box_px,
                           "size": [BOX / RES * 1.4, BOX / RES * 1.4], "flag": grasped, "flag_color": "#ffb74d",
                           "flag_text": _t("把持中", "held")}]},
               {"label": _t("二値化: 高さ 2〜10 cm", "Binarised: height 2-10 cm"), "frames": mask}],
        follow="box", view={"az": -2.2, "el": 0.55, "dist": 1.0},
        numbers=[fs.viewer_number(_t("コマ", "Frames"), "%d @ %d fps" % (T, FPS)),
                 fs.viewer_number(_t("物体", "Bodies"), str(len(bodies)))])
    spec = fs.viewer_spec("interactive_anim3d_viewer", _t("動く 3-D の見本", "Moving 3-D sample"),
                          _t("姿勢の時系列と、同じ時間軸の 2-D を 1 枚に。", "Pose time series and synchronised 2-D in one page."),
                          _t("ドラッグで回転、ホイールで拡大。空白で再生/停止、← → でコマ送り。段のボタンで跳ぶ。",
                             "Drag to rotate, wheel to zoom. Space plays/pauses, arrow keys step. Stage buttons jump."),
                          [tab])

    with tempfile.TemporaryDirectory() as d:
        path = fs.write_viewer(spec, a.out or os.path.join(d, "anim3d.html"), ["ja", "en"])
        html = open(path, encoding="utf-8").read()
        data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
        tb = data["tabs"][0]
        A_ = data["arrays"]
        rx, rq = A_[tb["xyz"]], A_[tb["quat"]]
        bx, bq = pv._decode_array(rx), pv._decode_array(rq)
        stepx = pv._quant_step(rx)
        wx = float(np.max(np.abs(bx - xyz) / (stepx / 2)))
        ang = float(np.max(quat_angle(bq, quat)))
        # 手先の点(手のひら + (0,0,-LG))を、戻した姿勢で動かしたときのずれ
        tip_back = bx[:, 6] + np.einsum("tij,j->ti", qmat(bq[:, 6] / np.linalg.norm(bq[:, 6], axis=-1, keepdims=True)), [0, 0, -LG])
        tip_err = float(np.max(np.linalg.norm(tip_back - tip, axis=1)))
        bound = float(np.linalg.norm(stepx / 2) + ang * LG)
        raw = sum(np.asarray(x).nbytes for x in (depth, mask))
        png = sum(len(s) * 3 // 4 for k in (tb["panes"][0]["frames"], tb["panes"][1]["frames"]) for s in A_[k]["png"])
        same = all(np.array_equal(pv._decode_array(A_[p["frames"]]), src) for p, src in zip(tb["panes"], (depth, mask)))
        pose_b = (len(bx.ravel()) * 2 + len(bq.ravel()) * 2)
        print("書いた: %s(%.0f KB、ja+en、物体 %d・コマ %d)" % (path if a.out else "一時フォルダ", os.path.getsize(path) / 1e3,
                                                         len(bodies), T))
        print("姿勢: %d B(位置 uint16 + 四元数 int16)。位置の復元は最悪で刻みの半分の %.2f 倍、"
              "四元数の角度の誤差は最大 %.1e rad" % (pose_b, wx, ang))
        print("手先の点のずれ: 最大 %.1f µm(刻みから見積もった上限 %.1f µm)" % (tip_err * 1e6, bound * 1e6))
        print("2-D: 生の u8 なら %.0f KB → 無損失 PNG で %.0f KB(%.1f 分の 1)、画素ごとに一致: %s"
              % (raw / 1e3, png / 1e3, raw / max(png, 1), same))
        assert wx <= 1.0 + 1e-9, wx
        assert ang < 1e-4, ang
        assert tip_err <= bound + 1e-12, (tip_err, bound)
        assert same, "PNG で戻した画像が元と違う"
        assert "http://" not in html and "https://" not in html, "外部 URL がある"
        assert len(tb["events"]) == 6 and tb["events"][0]["k"] == 0
        assert mask[0].any() and mask[rel_k].any(), "二値化に箱が写っていない"
        try:                                                             # 四元数のノルム 0 は止まる
            bad = quat.copy()
            bad[3, 9] = 0.0
            pv._build_html(fs.viewer_spec("x", _t("a", "a"), _t("b", "b"), _t("c", "c"),
                                          [dict(tab, quat=bad)]), "ja")
        except ValueError as exc:
            print("ノルム 0 の四元数は拒否: %s" % str(exc)[:70])
        else:
            raise AssertionError("ノルム 0 の四元数が通ってしまった")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
