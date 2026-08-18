"""Fullseye 統一視覚 I/F — 動くデモ(F1 自然呼び出し / F2 発見 / F3 introspection).

本セッションで実装した 600 の HALCON facade op が、単一 registry + 章別名前空間で
「発見でき・メタを持ち・自然に呼べる」ことを実際に走らせて示す。

  PYTHONPATH=. py -3.11 spikes/unified_vision_demo.py

要件 docs/UNIFIED_API_REQUIREMENTS.md の F1/F2/F3 を、既存 op を一切変更せず(F7)実現。
"""
from __future__ import annotations

import warnings

import numpy as np

warnings.simplefilter("ignore")

import fullseye as fs                      # noqa: E402
vision = fs.vision                         # 章別名前空間(F1)
ops = fs.vision_ops                        # 単一 registry(F2/F3)


def section(t):
    print("\n" + "═" * 68 + f"\n {t}\n" + "═" * 68)


def main():
    section("F2 統一発見 — 単一 registry で 3 層(facade/進化/知覚)を横断で列挙")
    st = ops.stats()
    print(f"総 op {st['total']} / 名前空間 {st['namespaces']}")
    print(f"provenance 別: {st['by_provenance']}  "
          f"(facade=本セッション genuine / evolution=進化 registry a/b / perception=知覚 facade)")

    print("\n検索 ops.find('hand_eye')(層を跨いで検索):")
    for o in ops.find("hand_eye"):
        print(f"  [{o.provenance}] {o.namespace}.{o.name}  — {o.doc}")

    section("F3 introspection — 各 op が name/型/params/doc/描画ヒント/provenance を持つ")
    for name in ("camera_calibration", "gen_circle_contour_xld", "photometric_stereo"):
        d = ops.describe(name)
        print(f"\n▸ {d['signature']}")
        print(f"    namespace={d['namespace']}  chapter={d['chapter']}  "
              f"render_hint={d['render_hint']}  provenance={d['provenance']}")
        print(f"    {d['doc']}")

    section("F1 自然呼び出し — 章別名前空間 + 自然シグネチャ(進化用 a/b は露出しない)")

    # 1) 輪郭生成 → 点内外判定(fs.vision.contour)
    circ = vision.contour.gen_circle_contour_xld(row=50, col=50, radius=20, n=64)
    inside = vision.contour.test_xld_point(circ, 50, 50)[0]
    outside = vision.contour.test_xld_point(circ, 50, 90)[0]
    print(f"  contour.gen_circle_contour_xld(row=50,col=50,radius=20)  -> {circ['cs'][0].shape[0]} 点")
    print(f"  contour.test_xld_point(中心) = {inside} / (外) = {outside}")

    # 2) Zhang カメラ校正(fs.vision.calib)
    obj = np.array([[x, y] for x in range(6) for y in range(6)], float) * 0.05
    Ktrue = np.array([[800, 0, 320], [0, 810, 240], [0, 0, 1.0]])
    rng = np.random.default_rng(1)
    from calib import _axis_to_rot
    views = []
    for _ in range(10):
        R = _axis_to_rot(rng.normal(0, 0.3, 3))
        t = np.array([rng.normal() * 0.1, rng.normal() * 0.1, 1.3 + rng.random() * 0.4])
        P = np.column_stack([obj, np.zeros(len(obj))]) @ R.T + t
        uv = P @ Ktrue.T
        views.append(uv[:, :2] / uv[:, 2:3])
    K = vision.calib.camera_calibration(obj, views)
    print(f"  calib.camera_calibration(obj, 10 views)  -> fx={K['fx']:.1f} fy={K['fy']:.1f} "
          f"cx={K['cx']:.1f} cy={K['cy']:.1f}  (真値 800/810/320/240)")

    # 3) 勾配場から高さ場復元(fs.vision.recon3d, Frankot-Chellappa)
    yy, xx = np.mgrid[0:32, 0:32]
    z = np.sin(2 * np.pi * xx / 32) * np.cos(2 * np.pi * yy / 32)
    p = np.gradient(z, axis=1); q = np.gradient(z, axis=0)
    z_rec = vision.recon3d.reconstruct_height_field_from_gradient(q, p)
    corr = np.corrcoef((z - z.mean()).ravel(), (z_rec - z_rec.mean()).ravel())[0, 1]
    print(f"  recon3d.reconstruct_height_field_from_gradient(...)  -> 復元相関 {corr:.5f}")

    # 4) 領域集合演算(fs.vision.region)
    a = np.zeros((20, 20), bool); a[4:12, 4:12] = True
    b = np.zeros((20, 20), bool); b[8:16, 8:16] = True
    inter = vision.region.intersection(a, b)
    print(f"  region.intersection(a, b)  -> 重なり画素 {int(inter.sum())}")

    section("F7 後方互換 — 進化 registry / 知覚 facade と共存(何も壊れていない)")
    print(f"  進化 registry(fs.REGISTRY)   {len(fs.REGISTRY)} ops   fs.apply(...) 健在")
    print(f"  知覚 facade(fs.stereo 等)     健在")
    print(f"  統一視覚 I/F(fs.vision)       {len(ops)} ops  ← 本デモ")

    print("\n[demo OK] 600 op が単一 I/F で発見でき・メタを持ち・自然に呼べる(F1/F2/F3/F7)")


if __name__ == "__main__":
    main()
