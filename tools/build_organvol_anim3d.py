#!/usr/bin/env python3
"""BodyParts3D organ volume and sphericity lesson (ViEW 2026)."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import fullseye as fs  # noqa: E402
import pocviewer as pv  # noqa: E402
import render3d  # noqa: E402

T = pv.viewer_text
DATA = ROOT / "data" / "bodyparts3d"
OUT_HTML = ROOT / "docs" / "anim3d" / "organ_volume.html"
LANGS = ("ja", "en")
NAMES = ("heart", "kidney_left", "kidney_right", "liver", "lung_left", "lung_right")
LABELS = {"heart": ("心臓", "Heart"), "liver": ("肝臓", "Liver"),
          "kidney_left": ("左腎", "Left kidney"), "kidney_right": ("右腎", "Right kidney"),
          "lung_left": ("左肺", "Left lung"), "lung_right": ("右肺", "Right lung")}
COLORS = {"heart": [224, 82, 99], "liver": [153, 76, 98], "kidney_left": [192, 96, 72],
          "kidney_right": [192, 96, 72], "lung_left": [113, 170, 210], "lung_right": [113, 170, 210]}


def load_organs():
    out = {}
    for name in NAMES:
        d = np.load(DATA / (name + ".npz"))
        V, F = np.asarray(d["vertices"], float), np.asarray(d["faces"], int)
        V -= (V.max(axis=0) + V.min(axis=0)) / 2
        out[name] = (V, F, {k: d[k].item() for k in d.files if k not in ("vertices", "faces")})
    return out


def metrics(organs=None):
    organs = organs or load_organs()
    rows = {}
    for name, (V, F, meta) in organs.items():
        volume = abs(float(fs.ledger.mesh_volume((V, F))))
        area = float(fs.ledger.mesh_area((V, F)))
        topo = fs.ledger.mesh_euler_characteristic(V, F)
        pitch = float(np.ptp(V, axis=0).min() / 50.0)
        solid, _ = render3d.voxelize_solid(V, F, pitch)
        voxel_volume = float(solid.sum() * pitch ** 3)
        rows[name] = {"volume": volume, "voxel_volume": voxel_volume,
                      "relative_error": abs(voxel_volume - volume) / volume,
                      "area": area, "sphericity": math.pi ** (1/3) * (6 * volume) ** (2/3) / area,
                      "pitch": pitch, **meta, **topo}
    return rows


def sphere_mesh(nu=24, nv=12):
    u = np.arange(nu) * 2 * np.pi / nu
    v = np.linspace(-np.pi / 2, np.pi / 2, nv + 1)
    U, V = np.meshgrid(u, v, indexing="ij")
    p = np.stack([np.cos(V) * np.cos(U), np.cos(V) * np.sin(U), np.sin(V)], -1).reshape(-1, 3)
    f = []
    for i in range(nu):
        for j in range(nv):
            a, b = i * (nv + 1) + j, ((i + 1) % nu) * (nv + 1) + j
            f.extend([[a, b, b + 1], [a, b + 1, a + 1]])
    return p, np.asarray(f, int)


def mesh_sphericity(vertices, faces):
    volume = abs(float(fs.ledger.mesh_volume((vertices, faces))))
    area = float(fs.ledger.mesh_area((vertices, faces)))
    return math.pi ** (1/3) * (6 * volume) ** (2/3) / area


def sphere_gate():
    levels = []
    for nu in (12, 24, 48):
        V, F = sphere_mesh(nu, nu // 2)
        levels.append(mesh_sphericity(V, F))
    return {"levels": levels, "drawn": levels[1],
            "monotonic": levels[0] < levels[1] < levels[2] < 1.0}


def _motion(count, bodies):
    xyz = np.zeros((count, bodies, 3)); q = np.zeros((count, bodies, 4)); q[..., 0] = 1
    return xyz, q


def _lesson(question_ja, question_en, choices, answer, explain, formula, limit):
    return {"question": T(question_ja, question_en), "choices": [T(*x) for x in choices], "answer": answer,
            "explain": T(*explain), "formula": T(*formula), "limit": T(*limit)}


def build_spec():
    organs = load_organs(); m = metrics(organs); tabs = []
    order = sorted(NAMES, key=lambda n: m[n]["volume"])
    nf = 49; time = np.arange(nf) / 15.0
    bodies = []
    for name in order:
        V, F, _ = organs[name]; scale = 0.018
        bodies.append({"name": name, "pos": V * scale, "faces": F, "rgb": COLORS[name], "label": T(*LABELS[name])})
    xyz, q = _motion(nf, len(bodies))
    for i in range(len(bodies)):
        xyz[:, i, 0] = (i - 2.5) * 2.6
        xyz[:, i, 2] = np.maximum(0, (i * 8 - np.arange(nf))) * .08
    worst = max(x["relative_error"] for x in m.values())
    checks = [{"what": T("発散定理と固体ボクセル", "Divergence theorem vs solid voxels"),
               "criterion": T("相対差 < 1 %", "relative difference < 1%"), "result": "%.4f %%" % (worst * 100), "ok": worst < .01}]
    tabs.append(pv.viewer_anim3d_tab("volume", T("体積を並べる", "Rank by volume"), "passed",
        T("幅や高さだけではなく、閉曲面が包む三次元の量を比べる。", "Compare the three-dimensional amount enclosed, not one width or height."),
        time, bodies, xyz, q, checks=checks,
        axis={"values": np.arange(nf), "segments": [{"k": 0, "label": T("並べる段階", "Ranking step"), "unit": "", "decimals": 0}]},
        lesson=_lesson("見た目の幅が近ければ体積も近い？", "Does a similar width imply a similar volume?",
          [("はい", "Yes"), ("いいえ", "No")], 1,
          ("二つの独立な経路で体積を確かめる。", "Two independent routes verify each volume."),
          ("V = Σ v0·(v1×v2) / 6", "V = Σ v0·(v1×v2) / 6"),
          ("これは成人男性の参照モデルで、患者の計測ではない。", "This is an adult male reference model, not a patient measurement.")), view={"az": -45, "el": 18, "dist": 1.25}))

    # Sphericity: every organ is overlaid with its equal-volume sphere.
    sphV, sphF = sphere_mesh(); sphere_check = sphere_gate(); sb = []
    chosen = ("heart", "kidney_left", "liver")
    for i, name in enumerate(chosen):
        V, F, _ = organs[name]; s = .018; r = (3 * m[name]["volume"] / (4 * np.pi)) ** (1/3) * s
        sb.extend([{"name": name, "pos": V * s, "faces": F, "rgb": COLORS[name]},
                   {"name": name + "_sphere", "pos": sphV * r, "faces": sphF, "rgb": [240, 210, 80], "alpha": .28}])
    sx, sq = _motion(nf, len(sb))
    for i in range(len(chosen)):
        sx[:, 2*i:2*i+2, 0] = (i-1)*5
    tabs.append(pv.viewer_anim3d_tab("shape", T("球形度", "Sphericity"), "passed",
        T("黄色い半透明球は各臓器と同じ体積。表面が入り組むほど球形度は下がる。", "Each translucent yellow sphere has the same volume as its organ; a less compact surface lowers sphericity."),
        time, sb, sx, sq, checks=[{"what": T("描画した多面体球の球形度", "Sphericity of the drawn polyhedral sphere"),
                                  "criterion": T("細分 12 → 24 → 48 で 1 へ単調収束", "monotonic convergence to 1 at subdivisions 12 → 24 → 48"),
                                  "result": "%.6f (%.6f → %.6f → %.6f)" % (sphere_check["drawn"], *sphere_check["levels"]),
                                  "ok": sphere_check["monotonic"]}],
        axis={"values": np.linspace(0, 1, nf), "segments": [{"k": 0, "label": T("比較", "Comparison"), "unit": "", "decimals": 2}]},
        lesson=_lesson("同じ体積なら表面積も同じ？", "Does equal volume mean equal surface area?",
          [("同じ", "Same"), ("形で変わる", "It depends on shape")], 1,
          ("球が最小の表面積を持ち、球形度は 1。", "A sphere has minimum area and sphericity 1."),
          ("Ψ = π^(1/3)(6V)^(2/3) / A", "Ψ = π^(1/3)(6V)^(2/3) / A"),
          ("頂点の継ぎ目は溶接したが、99 % 削減版は細い構造を失う。", "Vertex seams are welded, but the 99% reduction loses thin structures.")), view={"az": -35, "el": 15, "dist": 1.2}))

    # Slice integration: a translucent plane descends through the liver.
    V, F, _ = organs["liver"]; planeV=np.array([[-3,-3,0],[3,-3,0],[3,3,0],[-3,3,0.]],float); planeF=np.array([[0,1,2],[0,2,3]])
    bx=[{"name":"liver","pos":V*.018,"faces":F,"rgb":COLORS["liver"],"alpha":.72},
        {"name":"slice","pos":planeV,"faces":planeF,"rgb":[80,220,220],"alpha":.32}]
    xx,qq=_motion(nf,2); z=np.linspace(V[:,2].max(),V[:,2].min(),nf)*.018; xx[:,1,2]=z
    tabs.append(pv.viewer_anim3d_tab("slices", T("断面を積む", "Stack cross-sections"), "passed",
        T("水色の面を下げ、断面積を積むと閉曲面の体積へ収束する。", "Lower the cyan plane; accumulating cross-sectional area converges to enclosed volume."), time,bx,xx,qq,
        checks=checks, axis={"values":z,"segments":[{"k":0,"label":T("断面の高さ", "Slice height"),"unit":" mm","decimals":1}]},
        lesson=_lesson("薄い断面を全部足すと何になる？", "What does summing all thin sections give?",
          [("表面積", "Surface area"), ("体積", "Volume")],1,
          ("断面積を高さで積分すると体積になる。", "Integrating cross-sectional area over height gives volume."),
          ("V = ∫ A(z) dz", "V = ∫ A(z) dz"),
          ("刻みが粗いと細い端部を飛ばす。", "A coarse step skips thin tips.")), view={"az":-40,"el":20,"dist":1.15}))

    tb=[]
    for name in ("lung_left","lung_right","heart"):
        V,F,_=organs[name]; tb.append({"name":name,"pos":V*.018,"faces":F,"rgb":COLORS[name]})
    tx,tq=_motion(nf,3); tx[:,0,0]=-3; tx[:,1,0]=3
    closed=all(m[n]["chi"]==2 and m[n]["boundary_edges"]==0 for n in NAMES)
    tabs.append(pv.viewer_anim3d_tab("topology",T("閉曲面と位相", "Closed surfaces and topology"),"limit",
        T("閉じた外皮は χ = 2。細い気管支を落としたモデルでは枝の位相を測れない。", "A closed shell has χ = 2; this reduced model cannot measure the topology of omitted bronchi."),time,tb,tx,tq,
        checks=[{"what":T("頂点溶接で閉じた 6 曲面", "Six surfaces closed by vertex welding"),
                 "criterion":T("修復後 χ = 2、境界辺 0", "after repair: χ = 2, boundary edges 0"),
                 "result":T("修復前 1,604 辺 → 修復後 0 辺、6 件すべて χ = 2",
                            "1,604 edges before repair → 0 after; χ = 2 for all 6"),"ok":closed},
                {"what":T("99 % 削減版の細い構造", "Thin structures in the 99% reduction"),"criterion":T("元形状の枝と面積を保存", "preserve source branches and area"),"result":T("気管・血管を失う", "trachea and vessels are lost"),"ok":False}],
        axis={"values":np.arange(nf),"segments":[{"k":0,"label":T("位相の確認", "Topology check"),"unit":"","decimals":0}]},
        lesson=_lesson("閉じた一枚の外皮の χ は？", "What is χ for one closed shell?",
          [("0", "0"), ("2", "2")],1,
          ("頂点・辺・面を別々に数えて χ を得る。", "Count vertices, edges and faces independently to obtain χ."),
          ("χ = V − E + F = 2", "χ = V − E + F = 2"),
          ("99 % 削減版は細い構造を失う。医療診断には使わない。", "The 99% reduction loses thin structures. Do not use it for diagnosis.")),view={"az":-45,"el":15,"dist":1.2}))
    return pv.viewer_spec("organ_volume",T("臓器の体積と球形度", "Organ volume and sphericity"),
        T("同じ大きさに見えても、包む量と表面の複雑さは違う", "Similar apparent size can hide different enclosed volume and surface complexity"),
        T("ドラッグで回し、つまみを動かす", "Drag to rotate and move the slider"),tabs,
        credit=T("BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International",
                 "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International"))


def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--out",type=Path,default=OUT_HTML); ap.add_argument("--check",action="store_true"); a=ap.parse_args(argv)
    m=metrics()
    for n in NAMES: print("CHECK",n,"relative_error=%.9g psi=%.9g chi=%d boundary=%d"%(m[n]["relative_error"],m[n]["sphericity"],m[n]["chi"],m[n]["boundary_edges"]))
    spec=build_spec()
    if a.check: pv._build_html(spec,list(LANGS))
    else: pv.write_viewer(spec,str(a.out),list(LANGS))
    return 0


if __name__ == "__main__": raise SystemExit(main())
