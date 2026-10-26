# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_gravity_tour — 小惑星イトカワの実際の形の上で、立つ場所の重さと坂を台帳の 2 op で測る(polygrav)。

    py -3.11 examples/itokawa_gravity_tour.py

【この例が示すこと】
1. **形** —— 公開データの形(NASA PDS Small Bodies Node の Gaskell Itokawa Shape Model V1.1、Q = 64 の 49,152 面、
   CC0 1.0。data/itokawa_shape/)。体積は ``mesh_volume``、質量 = 体積 × 1.9 g/cm³(Fujiwara 2006)。
2. **表面の重力** —— ``polyhedron_gravity``(一様密度の多面体の厳密な式、Werner & Scheeres 1997)を、長軸を通る断面
   (y = 0、``mesh_slice_contours``)に沿った頂点で計算する。自転(12.13 時間)の遠心力を足した実効重力は
   両端で軽く、首のあたりで重い。斜面の角 = 実効重力と −法線のなす角。
3. **限界** —— ``polyhedron_clip_halfspace`` で x ≥ 150 m を「頭」として切り、頭を 2,850 kg/m³・全体の質量を保つと
   重心が頭の方へずれる(Lowry et al. 2014 の説)。一様密度の仮定ではずれは 0。

【グラウンドトゥルース】ガウスの法則(重心で ∇·g = −4πGρ、面の立体角の和 = 4π)、遠方の点質量、切った 2 つの和 = 全体。
動く 3-D 版(5 タブ)は tools/build_itokawa_anim3d.py → docs/anim3d/itokawa_gravity.html。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402
import opsdrive                # noqa: E402  台帳(opsdrive の族 polygrav)から名前で呼ぶ

DATA = ROOT / "data" / "itokawa_shape" / "gaskell_q64.npz"
RHO = 1900.0                                        # Fujiwara 2006: 1.9 ± 0.13 g/cm³
OMEGA = math.radians(712.14376110) / 86400.0        # PDS の自転の値(度/日)→ rad/s


def load():
    z = np.load(DATA, allow_pickle=False)
    F = z["faces"].astype(np.int64)
    used = np.unique(F)
    remap = -np.ones(len(z["vertices_cm"]), dtype=np.int64)
    remap[used] = np.arange(used.size)
    return z["vertices_cm"][used] / 100.0, remap[F]


def main() -> int:
    V, F = load()
    vol = fs.ledger.mesh_volume((V, F))
    print("1. 形: %d 頂点・%d 面、体積 %.4g m³(公表 1.838e7)、質量 %.3g kg(公表 3.51e10)"
          % (len(V), len(F), vol, vol * RHO))
    # ---- 2. 長軸の断面に沿った重力 --------------------------------------------------- #
    Vr = np.stack([V[:, 0], V[:, 2], -V[:, 1]], axis=1)
    tab = fs.ledger.mesh_slice_contours((Vr, F), 0.0)
    ring = np.asarray(tab["ring"]).astype(int)
    rid = int(np.bincount(ring).argmax())
    pts = np.stack([np.asarray(tab["x"])[ring == rid], np.zeros(int((ring == rid).sum())),
                    np.asarray(tab["y"])[ring == rid]], axis=1)
    idx = np.unique(np.argmin(((pts[:, None, :] - V[None, :, :]) ** 2).sum(axis=2), axis=1))
    VN = fs.ledger.vertex_normals((V, F))
    g = opsdrive.call("polyhedron_gravity", (V, F), V[idx], density=RHO, omega=OMEGA, normals=VN[idx])
    ge = np.linalg.norm(g["effective_acceleration"], axis=1) * 1e6
    com = g["center_of_mass"]
    end = int(np.argmax(np.abs(V[idx, 0] - com[0])))
    print("2. 断面の %d 頂点: |g_eff| %.1f〜%.1f µm/s²(いちばん遠い端で %.1f)、斜面の角 最大 %.1f°"
          % (len(idx), ge.min(), ge.max(), ge[end], g["slope_deg"].max()))
    gin = opsdrive.call("polyhedron_gravity", (V, F), com[None, :], density=RHO)
    print("   ガウスの法則: 重心で ∇·g / (−4πGρ) − 1 = %.1e、立体角の和 / 4π − 1 = %.1e"
          % (gin["div_g"][0] / (-4 * math.pi * 6.67430e-11 * RHO) - 1, gin["solid_angle"][0] / (4 * math.pi) - 1))
    # ---- 3. 頭と胴で密度が違うと --------------------------------------------------- #
    head = opsdrive.call("polyhedron_clip_halfspace", (V, F), [150.0, 0.0, 0.0], [1.0, 0.0, 0.0])
    gh = opsdrive.call("polyhedron_gravity", head, com[None, :], density=1.0)
    vh, ch = gh["volume"], gh["center_of_mass"]
    rho_h = 2850.0
    rho_b = (1950.0 * vol - rho_h * vh) / (vol - vh)
    c2 = (rho_b * vol * com + (rho_h - rho_b) * vh * ch) / (1950.0 * vol)
    print("3. 頭(x ≥ 150 m)の体積 %.1f %%、頭 %.0f / 胴 %.0f kg/m³ で重心が x へ %+.1f m(Lowry 2014: 21 ± 12 m)"
          % (vh / vol * 100, rho_h, rho_b, c2[0] - com[0]))
    if figs.enabled():
        x = V[idx, 0]
        order = np.argsort(x)
        figs.save_plot("itokawa_section_gravity",
                       [("|g_eff| [µm/s²]", x[order], ge[order])],
                       xlabel="x [m](長軸)", ylabel="|g_eff| [µm/s²]",
                       title="イトカワの長軸の断面の実効重力(polyhedron_gravity)",
                       caption="y = 0 の断面の頂点での実効重力(一様密度 1.9 g/cm³ + 自転の遠心力)。両端で軽い。",
                       kinds=["scatter"], source="Gaskell Itokawa Shape Model V1.1(NASA PDS SBN、CC0 1.0)")
    assert abs(gin["div_g"][0] / (-4 * math.pi * 6.67430e-11 * RHO) - 1) < 1e-12
    assert ge.min() < ge.max() and 0 < c2[0] - com[0]
    return 0


if __name__ == "__main__":
    sys.exit(main())
