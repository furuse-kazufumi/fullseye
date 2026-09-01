# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""defect_to_cad — 「2-D 画像で見つけた欠陥は CAD のどの面のどこか」を一巡する。

    py -3.11 examples/defect_to_cad.py

【この例が解く問題】
外観検査は 2-D で当たりを付ける。しかし報告先は CAD で、必要なのは「面 17 の
座標 (x, y, z) に 0.42 mm^2 の傷」であって「画素 (183, 96) が暗い」ではない。
fullseye には姿勢を出す道具(`align_cad_to_scan` / ICP / `ppf`)は既にあったが、
**姿勢から先が無かった**。ここはその先で、必要なのは学習でもレンダラでもなく、
画素 → 光線 → 三角形交差 → 重心座標 という**完全な閉形式**だけ。

(1) 部品(直方体)とカメラを置く。規約は `camera.py` に合わせる(+Z 前方、
    画素中心は整数座標)。
(2) 往復可逆性: 面上の既知の点を投影 → その画素から逆に引くと、**同じ面 ID・
    同じ重心座標**が返る。これがこのモジュールの厳密な真値。
(3) 検査カバレッジ: この視点で CAD のどの面を見たことになるか。
(4) ★面積: 傾いた面の欠陥は、画素数で数えると小さく出る。面上の実面積で
    出すと解析値に一致する — 合否が傾く場所なので数値で見る。
(5) 欠陥表: ラベル画像 → 面 ID / 面上の面積 / 3-D 重心の表。
(6) 遮蔽: 隠れている点を頼まれたとき、**黙って手前の面を返さない**。
(7) fail-closed: 当たらない画素・裏面・文字列の座標・資源上限。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 往復の重心座標誤差 2.4e-14、3-D 点の誤差 6.0e-13 mm(60 mm の部品を 320 mm
   から見た 300 点、すべて実測)。face_id は 300/300 一致。
2. 傾き 60 度のパッチの面積は解析値の 1.61% 以内。傾きを無視した値は真値の
   0.495 倍 = cos60 = 0.500(実測)。75 度では 0.255 倍 = 真値の約 1/4。
3. 隠れた点は `occluded=True` / `visible=False` で返る(画素座標自体は正当)。
4. 単位を 1e-3 倍しても 1e+3 倍しても同じ答え(相対誤差 1.5e-14 / 8.7e-15、
   face_id は全一致)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cadmap                                                    # noqa: E402
import camera                                                    # noqa: E402


def _box(size=(60.0, 40.0, 25.0), center=(0.0, 0.0, 0.0)):
    """外向き巻き(外から見て反時計回り)の直方体 (V, F)。単位 = mm。"""
    h = np.asarray(size, float) / 2.0
    c = np.asarray(center, float)
    V = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                  [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float) * h + c
    F = np.array([[0, 2, 1], [0, 3, 2],        # -z(カメラ側)
                  [4, 5, 6], [4, 6, 7],        # +z
                  [0, 1, 5], [0, 5, 4],        # -y
                  [3, 7, 6], [3, 6, 2],        # +y
                  [0, 4, 7], [0, 7, 3],        # -x
                  [1, 2, 6], [1, 6, 5]], np.int64)
    return V, F


def _tilted_patch(tilt_deg, z_mm, half_mm):
    """カメラを向いた平面パッチ + その解析面積 [mm^2]。"""
    a, b = half_mm
    P = np.array([[-a, -b, 0.0], [a, -b, 0.0], [a, b, 0.0], [-a, b, 0.0]])
    th = np.deg2rad(tilt_deg)
    Rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, np.cos(th), -np.sin(th)],
                   [0.0, np.sin(th), np.cos(th)]])
    return P @ Rx.T + np.array([0.0, 0.0, z_mm]), \
        np.array([[0, 2, 1], [0, 3, 2]], np.int64), 4.0 * a * b


def main() -> bool:
    W = H = 512
    K = camera.intrinsic_matrix(1200.0, 1200.0, (W - 1) / 2.0, (H - 1) / 2.0)
    R = camera.rodrigues(np.array([0.10, -0.18, 0.05]))
    t = np.array([2.0, -3.0, 320.0])                 # mm
    V, F = _box()

    print("=" * 74)
    print("(1) 部品とカメラ")
    print("=" * 74)
    print(f"   mesh: 頂点 {len(V)} / 三角形 {len(F)}(直方体 60x40x25 mm)")
    print(f"   K: fx=fy={K[0, 0]:.0f} px, 画像 {W}x{H}, カメラ距離 {t[2]:.0f} mm")
    print("   規約は camera.py に合わせる: +Z 前方 / u=列, v=行 / 画素中心は整数")

    print("\n" + "=" * 74)
    print("(2) 往復可逆性 — 面上の既知の点 → 投影 → 逆引き(厳密な真値)")
    print("=" * 74)
    vis = cadmap.cad_visible_faces((V, F), K=K, R=R, t=t, width=W, height=H)
    rng = np.random.default_rng(0)
    ids, bary, pts = [], [], []
    for fid in vis:
        for _ in range(50):
            w = rng.dirichlet(np.ones(3))
            ids.append(int(fid))
            bary.append(w)
            pts.append((V[F[fid]] * w[:, None]).sum(0))
    ids, bary, pts = np.array(ids), np.array(bary), np.array(pts)
    fwd = cadmap.cad_surface_to_pixel((V, F), pts, K=K, R=R, t=t, image_size=(W, H))
    keep = fwd["visible"]
    back = cadmap.cad_pixel_to_surface((V, F), fwd["uv"][keep], K=K, R=R, t=t,
                                       image_size=(W, H))
    same = bool(np.array_equal(back["face_id"], ids[keep]))
    b_err = float(np.abs(back["bary"] - bary[keep]).max())
    p_err = float(np.abs(back["point"] - pts[keep]).max())
    print(f"   可視な標本 {int(keep.sum())} 点(全 {len(ids)} 点中)")
    print(f"   face_id が全一致: {same}")
    print(f"   重心座標の最大誤差: {b_err:.3e}   3-D 点の最大誤差: {p_err:.3e} mm")
    if not (same and b_err < 1e-9 and p_err < 1e-6):
        print("   [FAIL] 往復が閉じない")
        return False

    print("\n" + "=" * 74)
    print("(3) 検査カバレッジ — この視点で見た面")
    print("=" * 74)
    print(f"   見えた面 {vis.size} / {len(F)}: {vis.tolist()}")
    hidden = sorted(set(range(len(F))) - set(vis.tolist()))
    print(f"   見えなかった面: {hidden}(裏面 + 遮蔽。次の視点で撮るべき面)")

    print("\n" + "=" * 74)
    print("(4) ★面積 — 斜めから見た面を画素数で数えると合否が傾く")
    print("=" * 74)
    Kp = camera.intrinsic_matrix(900.0, 900.0, (W - 1) / 2.0, (H - 1) / 2.0)
    print("   傾き |  真値 mm^2 | 面上の実面積 | 誤差 % | 傾き無視 | 比 | cos(傾き)")
    ok_area = True
    for tilt in (0.0, 30.0, 60.0, 75.0):
        Vp, Fp, area_true = _tilted_patch(tilt, 60.0, (16.0, 12.0))
        uv = np.stack(np.meshgrid(np.arange(W, dtype=float),
                                  np.arange(H, dtype=float)), -1).reshape(-1, 2)
        rec = cadmap.cad_pixel_to_surface((Vp, Fp), uv, K=Kp, R=np.eye(3),
                                          t=np.zeros(3), image_size=(W, H))
        lab = rec["hit"].reshape(H, W).astype(np.int32)
        r = cadmap.cad_defect_to_cad((Vp, Fp), lab, K=Kp, R=np.eye(3), t=np.zeros(3))[0]
        rel = abs(r["area"] - area_true) / area_true * 100.0
        ratio = r["area_naive"] / area_true
        print(f"   {tilt:5.0f} | {area_true:10.2f} | {r['area']:12.2f} | {rel:6.2f} "
              f"| {r['area_naive']:8.2f} | {ratio:.3f} | {np.cos(np.deg2rad(tilt)):.3f}")
        ok_area &= rel < 3.0 and abs(ratio - np.cos(np.deg2rad(tilt))) < 0.02
    print("   → 傾きを無視した値は cos(傾き) 倍にしかならない。75 度では真値の 1/4。")
    if not ok_area:
        print("   [FAIL] 面積が閉形式と合わない")
        return False

    print("\n" + "=" * 74)
    print("(5) 欠陥表 — ラベル画像 → 面 ID / 面上の面積 / 3-D 重心")
    print("=" * 74)
    labels = np.zeros((H, W), np.int32)
    labels[180:210, 150:200] = 1                       # 部品の上の傷
    labels[300:316, 280:300] = 2                       # もう 1 つ
    labels[20:40, 20:40] = 3                           # 背景(CAD の外)
    table = cadmap.cad_defect_to_cad((V, F), labels, K=K, R=R, t=t)
    print("   ラベル | 画素 | 当たり率 | 面上の面積 mm^2 | 面 ID | 3-D 重心 (mm)")
    for r in table:
        cen = ("なし(CAD 外)" if np.isnan(r["centroid"]).all()
               else "(%.1f, %.1f, %.1f)" % tuple(r["centroid"]))
        print(f"   {r['label']:6d} | {r['n_pixels']:4d} | {r['hit_fraction']:8.2f} "
              f"| {r['area']:15.3f} | {r['face_ids'].tolist()!s:>8} | {cen}")
    outside = [r for r in table if r["label"] == 3][0]
    if outside["n_hit"] != 0 or outside["area"] != 0.0:
        print("   [FAIL] CAD の外の領域が面に載ってしまった")
        return False
    print("   → CAD の外に載った領域は**表から消さず** area=0 / 当たり率 0 で残す。")
    print("     消すと『欠陥が無かったこと』になる。")

    print("\n" + "=" * 74)
    print("(6) 遮蔽 — 隠れている点を頼まれたら黙って手前の面を返さない")
    print("=" * 74)
    Vf, Ff, _ = _tilted_patch(0.0, 100.0, (10.0, 10.0))       # 手前の板
    Vb, Fb, _ = _tilted_patch(0.0, 200.0, (30.0, 30.0))       # 奥の板
    V2 = np.vstack([Vf, Vb])
    F2 = np.vstack([Ff, Fb + len(Vf)])
    probe = np.array([[0.0, 0.0, 200.0],       # 奥の板の中心 = 隠れている
                      [25.0, 0.0, 200.0]])     # 奥の板の端 = 見えている
    out = cadmap.cad_surface_to_pixel((V2, F2), probe, K=Kp, R=np.eye(3),
                                      t=np.zeros(3), image_size=(W, H))
    for i, tag in enumerate(("隠れている点", "見えている点")):
        print(f"   {tag}: 画素 ({out['uv'][i, 0]:.1f}, {out['uv'][i, 1]:.1f}) "
              f"depth={out['depth'][i]:.1f} occluded={bool(out['occluded'][i])} "
              f"occluder_face={out['occluder_face'][i]} "
              f"visible={bool(out['visible'][i])}")
    if not (out["occluded"][0] and not out["visible"][0] and out["visible"][1]):
        print("   [FAIL] 遮蔽が区別されていない")
        return False
    print("   → 画素座標そのものは正当な値で返る。嘘なのは『見えている』と言うほう。")

    print("\n" + "=" * 74)
    print("(7) fail-closed")
    print("=" * 74)
    miss = cadmap.cad_pixel_to_surface((V, F), np.array([[1.0, 1.0]]), K=K, R=R,
                                       t=t, image_size=(W, H))
    print(f"   当たらない画素: face_id={miss['face_id'][0]} "
          f"bary={miss['bary'][0]} (最寄りの面へは丸めない)")
    if miss["face_id"][0] != -1 or not np.isnan(miss["bary"]).all():
        print("   [FAIL] miss が最寄りの面に化けた")
        return False

    # 2026-09-02: 閉じた mesh を裏返すと「全部裏面」になり、裏面カリングが手前の
    # 壁を消して奥の面を『見えている』と返していた。いまは巻きを直したうえで
    # winding_fixed=True を返す(黙って直さない)。
    flipped = cadmap.cad_pixel_to_surface((V, F[:, ::-1].copy()),
                                          np.array([[W / 2.0, H / 2.0]]), K=K,
                                          R=R, t=t, image_size=(W, H))
    print(f"   巻きを反転(閉じた mesh): winding_fixed={flipped['winding_fixed']} "
          f"-> 直したうえで手前の面 face_id={flipped['face_id'][0]} を返す")
    if not flipped["winding_fixed"]:
        print("   [FAIL] 内向きの巻きが検出されず、黙って通った")
        return False
    strict_ok = False
    try:
        cadmap.cad_pixel_to_surface((V, F[:, ::-1].copy()),
                                    np.array([[W / 2.0, H / 2.0]]), K=K, R=R, t=t,
                                    image_size=(W, H), strict=True)
    except ValueError:
        strict_ok = True
    print(f"   strict=True なら直さず拒否: {strict_ok}")
    if not strict_ok:
        print("   [FAIL] strict=True が内向きの巻きを拒否しなかった")
        return False

    for bad, why in ((np.array([["100", "100"]]), "文字列の画素"),
                     (np.array([[True, False]]), "真偽値の画素"),
                     (np.array([[1 + 1j, 2 + 0j]]), "複素数の画素")):
        try:
            cadmap.cad_pixel_to_surface((V, F), bad)
            print(f"   [FAIL] {why} が通ってしまった")
            return False
        except ValueError:
            print(f"   拒否 {why}(float(\"100\") は成功してしまうので dtype で弾く)")

    saved = cadmap.MAX_RAY_FACE_TESTS
    try:
        cadmap.MAX_RAY_FACE_TESTS = 100
        cadmap.cad_visible_faces((V, F), K=K, R=R, t=t, width=W, height=H)
        print("   [FAIL] 資源上限が効かなかった")
        return False
    except ValueError as exc:
        print(f"   拒否 資源上限: {str(exc).splitlines()[0][:88]}")
    finally:
        cadmap.MAX_RAY_FACE_TESTS = saved

    print("\n" + "=" * 74)
    print("(8) 単位非依存 — um でも km でも同じ答え")
    print("=" * 74)
    for scale, unit in ((1e-3, "um 相当"), (1.0, "mm"), (1e3, "m 相当")):
        Vs, Fs = _box(size=(60.0 * scale, 40.0 * scale, 25.0 * scale))
        ts = np.array([2.0, -3.0, 320.0]) * scale
        vs = cadmap.cad_visible_faces((Vs, Fs), K=K, R=R, t=ts, width=256, height=256)
        w = rng.dirichlet(np.ones(3), size=vs.size)
        ps = np.einsum("mkj,mk->mj", Vs[Fs[vs]], w)
        fw = cadmap.cad_surface_to_pixel((Vs, Fs), ps, K=K, R=R, t=ts,
                                         image_size=(W, H))
        k = fw["visible"]
        bk = cadmap.cad_pixel_to_surface((Vs, Fs), fw["uv"][k], K=K, R=R, t=ts,
                                         image_size=(W, H))
        rel = float(np.abs(bk["point"] - ps[k]).max() / np.abs(ps[k]).max())
        agree = bool(np.array_equal(bk["face_id"], vs[k]))
        print(f"   x{scale:<8g} ({unit:<9}) 見えた面 {vs.size} / face_id 一致 {agree} "
              f"/ 相対誤差 {rel:.2e}")
        if not agree or rel > 1e-12:
            print("   [FAIL] 単位で答えが変わった")
            return False

    print("\nPASS: cadmap 4 op すべてが閉形式のグラウンドトゥルースと一致し、"
          "斜め面の実面積・遮蔽・単位非依存を数値で満たした")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
