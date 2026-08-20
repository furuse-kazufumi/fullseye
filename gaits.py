"""四足歩行の qpos 軌道を関節名から自動生成(トロット等)。動く 3DGS のモーション源。

関節名 FL/FR/RL/RR + thigh/calf(or knee)を検出して脚を対応づける。検出できない
モデルでは None を返し、呼び手はサイン波にフォールバックする。
"""
from __future__ import annotations
import math
import numpy as np


# 脚コード -> (前後, 左右)。FL/FR/RL/RR と LF/RF/LH/RH(anymal 系)の両方に対応。
_LEG_CANON = {
    "FL": ("F", "L"), "FR": ("F", "R"), "RL": ("R", "L"), "RR": ("R", "R"),
    "LF": ("F", "L"), "RF": ("F", "R"), "LH": ("R", "L"), "RH": ("R", "R"),
    "HL": ("R", "L"), "HR": ("R", "R"),   # hind-left/right(spot 系)
}


def _leg_joints(model):
    import mujoco
    legs = {}
    for j in range(model.njnt):
        nm = (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j) or "").upper()
        adr = int(model.jnt_qposadr[j])
        for code, canon in _LEG_CANON.items():
            if nm.startswith(code + "_") or nm.startswith(code):
                if "THIGH" in nm or "HFE" in nm or nm.endswith("_HY"):
                    legs.setdefault(canon, {})["thigh"] = adr
                elif "CALF" in nm or "KNEE" in nm or "KFE" in nm or nm.endswith("_KN"):
                    legs.setdefault(canon, {})["calf"] = adr
                break
    return legs


def quadruped_trot(model, home_qpos, *, n_frames=60, cycles=1.5,
                   thigh_amp=0.35, calf_amp=0.35, bob=0.025, travel=0.0):
    """トロット(対角脚が同位相)の qpos 軌道 (F, nq)。検出不可なら None。

    travel>0 で胴体 root x を -travel/2 → +travel/2 に前進させ、地形を横断させる
    (視覚デモ用。歩幅と厳密には同期しないが起伏の横断が見える)。"""
    legs = _leg_joints(model)
    need = [("F", "L"), ("F", "R"), ("R", "L"), ("R", "R")]
    if not all(k in legs and "thigh" in legs[k] and "calf" in legs[k] for k in need):
        return None
    # 対角同位相: 前左+後右=0, 前右+後左=π
    phase = {("F", "L"): 0.0, ("R", "R"): 0.0, ("F", "R"): math.pi, ("R", "L"): math.pi}
    home = np.asarray(home_qpos, dtype=np.float32)
    traj = []
    for i in range(n_frames):
        t = i / n_frames * cycles
        ph0 = 2 * math.pi * t
        q = home.copy()
        for leg, adrs in legs.items():
            ph = phase[leg]
            q[adrs["thigh"]] = home[adrs["thigh"]] + thigh_amp * math.sin(ph0 + ph)
            q[adrs["calf"]] = home[adrs["calf"]] + calf_amp * math.sin(ph0 + ph + 1.2)
        # root writes are only meaningful when the model actually HAS a floating base —
        # on a fixed-base model q[0]/q[2] are joint angles and bob/travel would corrupt them.
        has_free = model.njnt > 0 and int(model.jnt_type[0]) == 0    # mjJNT_FREE == 0
        if has_free and len(q) >= 3:
            q[2] = home[2] + bob * abs(math.sin(2 * ph0))     # 胴体の上下バウンド
        if has_free and travel and len(q) >= 1:
            frac = i / max(1, n_frames - 1)
            q[0] = home[0] + travel * (frac - 0.5)            # -travel/2 → +travel/2 前進
        traj.append(q)
    return np.array(traj, dtype=np.float32)


def build(model, home_qpos, name, *, n_frames=60, travel=0.0):
    """名前でgait軌道を返す。'trot' 対応。未対応/検出不可は None。"""
    if name == "trot":
        return quadruped_trot(model, home_qpos, n_frames=n_frames, travel=travel)
    return None
