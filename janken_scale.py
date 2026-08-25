from dataclasses import replace
import sys, time, numpy as np, janken as J, mujoco
res = int(sys.argv[1])
base = J.JCfg(res=res, reveal_ms=200)
j = J.Janken(base); j.make_templates()
img = j._pose_image(J.PAPER)
J._TRACK.clear(); J.detect_arc_win(img, j.cfg)
cost = {}
for det, fn in J.DETECTORS.items():
    t0 = time.perf_counter()
    for _ in range(15):
        fn(img, j.cfg)
    cost[det] = (time.perf_counter() - t0) / 15 * 1000
print(f"--- 解像度 {res} (円弧半径 {j.cfg.arc_px:.0f}px / 肌画素 {int(J._skin(img).sum())}) ---")
print(f"  {'検出器':<10}{'費用ms':>9}{'判別ms':>9}{'判別+費用':>11}{'予算ms':>9}")
for det, fn in J.DETECTORS.items():
    cfg = replace(j.cfg, detector=det)
    out = {}
    for pose in J.POSES:
        J._TRACK.clear(); ok = None
        for k in range(cfg.reveal_ms + 1):
            f = min(1.0, k / cfg.reveal_ms)
            for i in range(5):
                a = J.POSES[J.ROCK][i] + f * (J.POSES[pose][i] - J.POSES[J.ROCK][i])
                j.data.ctrl[j.hj[i]] = a
                j.data.qpos[j.model.joint(f"human_j{i}").qposadr[0]] = a
            mujoco.mj_forward(j.model, j.data)
            ok = (k if ok is None else ok) if fn(j._render(), cfg) == pose else None
        out[pose] = ok
    w = max(v for v in out.values() if v is not None)
    tot = w + cost[det]
    print(f"  {det:<10}{cost[det]:9.2f}{w:9d}{tot:11.1f}{320 - 43 - tot:9.1f}")
