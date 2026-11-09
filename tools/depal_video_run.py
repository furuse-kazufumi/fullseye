# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""混載デパレタイズの動画のコマ: 条件ごとに「カラーの溝」のやり方で最初の 2 手を回し、6 軸アーム(MuJoCo Menagerie
の UR10e、BSD-3)の動きを ``tools/depal_robot_motion.py`` で計画して Blender(Cycles)で描く(手元専用)。

    py -3.11 tools/depal_video_run.py          # 先に tools/depal_blender_run.py で天井カメラのコマを揃えておく

Menagerie の置き場は ``MUJOCO_MENAGERIE``(既定は作業場の projects/mujoco_menagerie)。

出力(描画の置き場の video/ の下):
  <cond>/vid_00000.png ...     Blender の斜めのコマ(960 × 540)
  <cond>/plan.json             手ごとの結果・検出・時刻(PoC が字幕と差し込みに使う)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[1]
#: Blender の実行ファイル(環境変数 BLENDER だけから取る。手元の場所を追跡するファイルに書かない)。
BLENDER = os.environ.get("BLENDER", "").strip()


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


POC = _load("poc_depal", ROOT / "examples" / "poc_mixed_case_depalletizing.py")
RB = _load("depal_robot_motion", ROOT / "tools" / "depal_robot_motion.py")
S = X = L = M = POC                      # 場面・書き出し・繰り返し・描画の口はどれも PoC の中にある
FPS = 20
STEPS = 2
CONVEYOR_V = 0.35          # コンベアの速さ [m/s]
VIEW = {"pos": [-1.80, -2.05, 2.05], "target": [0.25, 0.32, 0.60], "lens": 27.0}


def quat_mat(p):
    w, x, y, z = p[3:7]
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p[:3]
    return T


#: 動画に映す 6 軸アームの型式と、クレジット(動画の章カードに出す。PoC の本文には書かない)。
ROBOT_MODEL = "UR10e"
ROBOT_CREDIT = ("ロボット: UR10e の形状(MuJoCo Menagerie、BSD-3-Clause、Copyright 2018 ROS Industrial Consortium)。"
                "配色は無地に変更。各社とは無関係で、推薦・保証を意味しない。")
#: 動画で見せるやり方(見出しの主張の中心 = 深度で切った面をカラーの暗い溝で割る)。
VIDEO_MODE = "cseam"
FAIL_OUTCOMES = ("double", "drop", "overload", "pose", "snag")


def _clip(scene, rec, pick, boxes_all, M_init):
    """1 手ぶんの動き: 計画と、コマごとの箱の行列(このコマで残っている箱だけ)。"""
    plan = RB.plan_motion([pick], fps=FPS)
    e = plan["boxes"][0]
    keep = set(rec["key"])
    carry = rec["outcome"] in ("success", "pose")
    tgt = rec["removed"][0]
    attach = None
    frames = []
    for fr in plan["frames"]:
        t = fr["t"]
        bx = {}
        for bid in keep:
            Mi = M_init[bid]
            if bid in rec["removed"] and not (carry and bid == tgt) and t >= e["t_cycle_end"] - 1e-9:
                continue                                    # 運ばなかった箱は人が直す(手の終わりに消す)
            Mt = Mi
            if carry and bid == tgt:
                if fr["attached"] == bid and fr["box_pose"] is not None:
                    if attach is None:
                        attach = quat_mat(fr["box_pose"])
                    Mt = quat_mat(fr["box_pose"]) @ np.linalg.inv(attach) @ Mi
                elif t >= e["t_release"]:
                    A = attach if attach is not None else quat_mat(e["initial_pose"])
                    Mt = quat_mat(e["placed_pose"]) @ np.linalg.inv(A) @ Mi
                    Mt[1, 3] += CONVEYOR_V * (t - e["t_release"])
                    if Mt[1, 3] > plan["conveyor"]["center"][1] + plan["conveyor"]["length"] / 2:
                        continue
            bx[str(bid)] = [float(v) for v in Mt.ravel()]
        frames.append({"t": t, "parts": fr["parts"], "flange_pose": fr["flange_pose"],
                       "rail_y": fr.get("rail_y", 0.0), "boxes": bx, "phase": fr["phase"]})
    return plan, frames


def _require_env() -> None:
    """要る環境変数が無ければ、何をすればよいかを書いて止まる(既定の場所は持たない)。"""
    if not BLENDER or not Path(BLENDER).is_file():
        raise SystemExit("set BLENDER to the Blender executable (got %r)" % BLENDER)
    if os.environ.get("DEPAL_DEVICE", "CPU") == "GPU" and not os.environ.get("FULLSEYE_GPU_LOCK", "").strip():
        raise SystemExit("GPU rendering needs FULLSEYE_GPU_LOCK (the caller holds the shared GPU lock); or DEPAL_DEVICE=CPU")


def main():
    _require_env()
    root = M.renders_root()
    if root is None:
        raise SystemExit("no Blender overhead frames: run tools/depal_blender_run.py first")
    conds = os.environ.get("DEPAL_CONDS", ",".join(S.CONDITIONS)).split(",")
    samples = os.environ.get("DEPAL_VIDEO_SAMPLES", "16")
    for cond in conds:
        scene = S.make_scene(cond, 0)
        prov = M.BlenderColor(root)
        src = L.FrameSource(scene, prov)
        log = L.run_loop(src, VIDEO_MODE, max_steps=60)
        if prov.missing and os.environ.get("DEPAL_ALLOW_MISSING") != "1":
            raise SystemExit("Blender のコマが足りない: %s" % prov.missing)
        # 映す手: 最初の手と、「両方」が最初に失敗した手(無ければ 2 手目)
        chosen = [log[0]]
        fail = [r for r in log[1:] if r["outcome"] in FAIL_OUTCOMES and r["det"] is not None]
        chosen.append(fail[0] if fail else log[1])
        boxes = {b.id: b for b in scene.boxes}
        M_init = {b.id: np.asarray(X.box_matrix(b)) for b in scene.boxes}
        out = root / "video" / cond
        out.mkdir(parents=True, exist_ok=True)
        for f in out.glob("vid_*.png"):
            f.unlink()
        exp = Path(tempfile.gettempdir()) / "depal_video_exports" / cond
        if not (exp / "scene.json").is_file():
            X.export_scene(scene, exp)
        frames, cycles, meta = [], [], None
        for rec in chosen:
            d = rec["det"]
            b = boxes[rec["removed"][0]]
            pick = {"box_id": int(b.id), "grasp": [d["cx"], d["cy"], d["cz"], d["yaw"]],
                    "box_size": [b.L, b.W, b.H], "box_top_center": b.top_center_world().tolist(), "box_yaw": b.yaw}
            plan, fr = _clip(scene, rec, pick, boxes, M_init)
            meta = plan
            e = plan["boxes"][0]
            cycles.append({"step": rec["step"], "outcome": rec["outcome"], "key": list(rec["key"]), "det": d,
                           "removed": rec["removed"], "pos_err": rec.get("pos_err"), "yaw_err": rec.get("yaw_err"),
                           "frame_start": len(frames), "n_frames": len(fr),
                           "t": {k: e[k] for k in ("t_cycle_start", "t_capture", "t_contact", "t_release", "t_cycle_end")}})
            frames.extend(fr)
        video = {"fps": FPS, "width": 960, "height": 540, "camera": VIEW, "meshes": meta["meshes"],
                 "tool": meta["tool"], "base": meta["base"], "conveyor": meta["conveyor"], "frames": frames}
        vjson = out / "video_frames.json"
        vjson.write_text(json.dumps(video), encoding="utf-8")
        info = {"cond": cond, "fps": FPS, "n_frames": len(frames), "cycles": cycles,
                "robot_model": ROBOT_MODEL, "robot_credit": ROBOT_CREDIT}
        (out / "plan.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
        env = dict(os.environ, DEPAL_DEVICE=os.environ.get("DEPAL_DEVICE", "CPU"))
        r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python",
                            str(ROOT / "tools" / "depal_blender_video.py"), "--", str(exp), str(out), str(vjson), samples,
                            os.environ.get("DEPAL_VIDEO_RANGE", "0:100000:1")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        n = r.stdout.count("DEPAL_VIDEO_FRAME")
        print(cond, [c["outcome"] for c in cycles], "frames", n, "/", len(frames), flush=True)
        if n == 0:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("Blender の動画のコマが描けなかった: " + cond)


if __name__ == "__main__":
    main()
