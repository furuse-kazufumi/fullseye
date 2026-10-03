# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""横断歩道を渡るヒューマノイド —— 実在ロボットを、車の物理は正確なまま、歩く側は安く描く(2026-10-03)。

著者の発案: 「自動運転の世界で人の代わりにヒューマノイドも何種類か擬似的に歩かせておく」「計算コストを下げられるなら
手段は特に指定しない」「当たり判定はそこまで精密でなくてもいい」「あらかじめ物体ごとの描画をマスク付きで作っておく」
「車に対してはある程度正確な物理演算が要るけど、他のオブジェクトはそこまで正確さは要らない」。

何をするか:
  1. MuJoCo Menagerie の人型(G1・H1・T1・Berkeley Humanoid・Fourier N1・TALOS・Apollo)から、手続き的な歩行 1 周期を作る
     (drivehumanoid.humanoid_walk_clip)。関節の役割は**名前でなく体の形**から決める(名前は機種ごとにばらばら)。
  2. 見た目の費用を 3 通りで測る: 見た目のメッシュそのまま / 格子で間引いたメッシュ / 向き × 位相のマスク付き事前描画。
  3. 横断歩道を渡る群れを車載カメラで撮る(事前描画)。当たり判定は外形の箱。

門(Menagerie が無くても回る部分): 事前描画のマスクが直接の描画と一致し(段の上で IoU ≥ 0.85)、手前の壁に隠れる。
Menagerie がある時の門: 7 機種が歩く(接地・前進・支持脚が滑らない)、間引きのずれ ≤ √3·格子幅、事前描画 10 体の 1 コマが
地面だけの 1.5 倍以内。

正直に: 歩き方は周期の式で、物理(重心・バランス)は解いていない —— 「擬似的に歩く」。事前描画は方位を 16 段・位相を 12 段に
丸め、遠くから水平に見た像を縮めて貼るので、カメラが高い・近いと透視の違いが出る(門の IoU はその大きさ)。OP3 は向きの
判定が合わず、ToddlerBot は足元に箱が残るので外した。

Menagerie の場所は環境変数 FULLSEYE_MENAGERIE_DIR(git clone https://github.com/google-deepmind/mujoco_menagerie)。
Run: py -3.11 examples/poc_driving_humanoids.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く)
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import drivehumanoid as H  # noqa: E402
import driveterrain as DT  # noqa: E402
import driveworld as DW  # noqa: E402

MODELS = [("unitree_g1", "g1.xml"), ("unitree_h1", "h1.xml"), ("booster_t1", "t1.xml"),
          ("berkeley_humanoid", "berkeley_humanoid.xml"), ("fourier_n1", "n1.xml"), ("pal_talos", "talos.xml"),
          ("apptronik_apollo", "apptronik_apollo.xml")]
W, Hh = 640, 400


def _ground_world():
    w = DW._empty_world()
    V, F = DW._grid_plane(-10, 40, -20, 20, step=1.0)   # 升が粗いと手前の升がカメラの後ろとして丸ごと落ちる
    DW.world_add(w, V, F, 0, np.tile([.33, .33, .35], (len(F), 1)), name="road")
    cw = DT.crosswalk_mesh((14.0, -3.5), (14.0, 3.5), length=4.0)
    DW.world_add(w, cw["V"], cw["F"], cw["label"], cw["color"], name="crosswalk")
    return w


def _box_clip(T=8):
    ms = [DT.pedestrian_mesh(1.7, stride=0.4 * np.sin(2 * np.pi * k / T)) for k in range(T)]
    return {"V": np.stack([m["V"] for m in ms]), "F": ms[0]["F"], "color": ms[0]["color"], "label": 7,
            "dims": ms[0]["dims"], "advance": np.linspace(0, 1.2, T, endpoint=False), "cycle_length": 1.2}


def gate_impostor_fidelity():
    """Menagerie が無くても回る門: 段の上で直接の描画と一致、手前の壁に隠れる。"""
    c = _box_clip()
    imp = H.humanoid_impostors(c, n_yaw=16, n_phase=8, res=160)
    K = DW.camera_intrinsics(60, 640, 400)
    ious = []
    for b, dist in ((0, 6.0), (3, 9.0), (10, 7.0), (6, 12.0)):
        pose = DW.camera_pose((-dist, 0.0, imp["eye_h"]), (0.0, 0.0, imp["eye_h"]))
        yaw = math.pi - 2 * math.pi * b / 16
        s = imp["phase_s"][3]
        w = _ground_world()
        DT.add_mesh_object(w, H.humanoid_clip_mesh(c, s), 0.0, 0.0, yaw)
        a = DW.world_camera(w, pose, K, 640, 400)["label"] == 7
        q = H.world_camera_impostors(_ground_world(), pose, K, 640, 400,
                                     [{"imp": imp, "x": 0.0, "y": 0.0, "yaw": yaw, "distance": s}])["label"] == 7
        ious.append(float((a & q).sum() / max((a | q).sum(), 1)))
    print("事前描画と直接の描画のマスクの一致度(段の上、6〜12 m): " + "  ".join("%.3f" % v for v in ious))
    assert min(ious) >= 0.85, ious
    w = _ground_world()
    V = np.array([[-4, -3, 0], [-4, 3, 0], [-4, 3, 3], [-4, -3, 3]], np.float64)
    DW.world_add(w, V, np.array([[0, 1, 2], [0, 2, 3]]), 3, (0.7, 0.7, 0.7), name="wall")
    pose = DW.camera_pose((-10.0, 0.0, 1.0), (0.0, 0.0, 1.0))
    act = [{"imp": imp, "x": 0.0, "y": 0.0, "yaw": 0.0, "distance": 0.0}]
    hid = H.world_camera_impostors(w, pose, K, 640, 400, act)["impostor_pixels"]
    seen = H.world_camera_impostors(_ground_world(), pose, K, 640, 400, act)["impostor_pixels"]
    print("手前の壁: 壁なし %d 画素 → 壁あり %d 画素" % (seen, hid))
    assert seen > 200 and hid == 0


def menagerie_part(root):
    import mujoco  # noqa: F401  (無ければ呼び出し側で [skip])
    lo, hi, rows = {}, {}, []
    for d, f in MODELS:
        p = os.path.join(root, d, f)
        if not os.path.exists(p):
            print("[skip] %s が無い" % p)
            continue
        c = H.humanoid_walk_clip(p)
        lo[d], hi[d] = c, H.humanoid_walk_clip(p, tri_budget=30000)
        dec = c["decimation"]
        assert np.allclose(c["V"][:, :, 2].min(axis=1), 0.0)
        assert c["cycle_length"] > 0.2, (d, c["cycle_length"])
        assert dec["max_vertex_shift"] <= math.sqrt(3) * dec["cell"] + 1e-12
        rows.append((d, dec["tris_before"], dec["tris_after"], "%.1f" % (dec["cell"] * 100),
                     "%.1f" % (dec["max_vertex_shift"] * 100), "%.2f" % c["cycle_length"], "%.2f" % c["dims"][2]))
    assert len(lo) >= 3, "Menagerie の人型が 3 機種未満"
    print("%-18s %10s %8s %8s %10s %8s %6s" % ("機種", "元の三角形", "間引後", "格子 cm", "最大ずれ cm", "1 周期 m", "身長 m"))
    for r in rows:
        print("%-18s %10d %8d %8s %10s %8s %6s" % r)
    figs.save_table("humanoid_decimation", ["機種", "元の三角形", "間引後", "格子 [cm]", "最大のずれ [cm]",
                                            "1 周期 [m]", "身長 [m]"], rows,
                    title="見た目のメッシュを格子で間引く(ずれ ≤ √3·格子幅)")
    # 費用: 10 体、3 通り
    K = DW.camera_intrinsics(60, W, Hh)
    pose = DW.camera_pose((5.0, -2.2, 1.4), (14.0, 0.0, 0.8))
    names = list(lo)
    pos = [(12.0 + 0.8 * ((k % 3) - 1), -3.0 + 0.7 * k, math.pi / 2 if k % 2 == 0 else -math.pi / 2, 0.13 * k)
           for k in range(10)]
    imps = {d: H.humanoid_impostors(hi[d]) for d in names}

    def timed(fn, n=2):
        fn()
        t = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - t) / n
    base = _ground_world()
    t_ground = timed(lambda: DW.world_camera(base, pose, K, W, Hh))
    results = {}
    for tag, clips in (("間引いたメッシュ(1,500)", lo), ("精細なメッシュ(30,000)", hi)):
        w = _ground_world()
        for k, (x, y, yaw, s) in enumerate(pos):
            DT.add_mesh_object(w, H.humanoid_clip_mesh(clips[names[k % len(names)]], s), x, y, yaw)
        results[tag] = timed(lambda: DW.world_camera(w, pose, K, W, Hh))
    acts = [{"imp": imps[names[k % len(names)]], "x": x, "y": y, "yaw": yaw, "distance": s}
            for k, (x, y, yaw, s) in enumerate(pos)]
    results["マスク付きの事前描画"] = timed(lambda: H.world_camera_impostors(base, pose, K, W, Hh, acts))
    print("1 コマ(%d×%d、10 体): 地面だけ %.3f s" % (W, Hh, t_ground))
    for k, v in results.items():
        print("  %-24s %.3f s(地面だけの %.2f 倍)" % (k, v, v / t_ground))
    assert results["マスク付きの事前描画"] <= 1.5 * t_ground + 0.01
    # 渡る群れの動画(事前描画)
    frames = []
    for f in range(32):
        a2 = []
        for k, (x, y, yaw, s) in enumerate(pos):
            v = 0.9 + 0.05 * k
            dist = s + v * f / 8.0
            a2.append({"imp": acts[k]["imp"], "x": x, "y": y + math.sin(yaw) * (dist - s), "yaw": yaw,
                       "distance": dist})
        frames.append(H.world_camera_impostors(base, pose, K, W, Hh, a2)["color"])
    figs.save_gif("humanoids_crossing", frames, caption="横断歩道を渡る 7 機種(マスク付きの事前描画、1 体 数 ms)", fps=8)
    figs.save("humanoids_crossing_still", frames[16], caption="同じ場面の 1 コマ")


def main():
    gate_impostor_fidelity()
    root = os.environ.get("FULLSEYE_MENAGERIE_DIR", "")
    try:
        import mujoco  # noqa: F401
        have_mj = True
    except ImportError:
        have_mj = False
    if root and os.path.isdir(root) and have_mj:
        menagerie_part(root)
    else:
        print("[skip] Menagerie の部分: FULLSEYE_MENAGERIE_DIR と mujoco が要る(%s)"
              % ("mujoco なし" if not have_mj else "場所の指定なし"))
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
