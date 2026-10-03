# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""motionio — 動きのデータを読む: BVH(モーションキャプチャ)とイベントカメラの (x, y, t, p)。

Studio のドラッグ・アンド・ドロップ(2026-10-03、ユーザー「Physical AI で使われるデータ形式も読んで表示」)の読み手。
stdlib + numpy だけ。

* **BVH**(Biovision Hierarchy)—— 骨格の階層(ROOT / JOINT / End Site、OFFSET、CHANNELS)と各コマの値。
  ``read_bvh`` は順運動学までやって、各コマの関節の世界座標 ``(T, J, 3)`` を返す。回転の CHANNELS は書かれた順に
  **内因的**に掛ける(``Zrotation Xrotation Yrotation`` なら R = Rz·Rx·Ry、度)。
  門: 手で計算できる骨格(根を Z まわりに 90° 回すと (0, 1, 0) の子は (−1, 0, 0))。
* **イベントカメラ** —— 1 行 1 イベントの (x, y, t, p)。列の順は形式でばらばら(N-MNIST の txt は x y t p、
  Prophesee の csv は x, y, p, t …)なので、見出しがあれば名前で、無ければ**中身で**決める: 時刻 = 単調非減少で
  幅が最大の列、極性 = 2 値({0, 1} か {−1, 1})の列、残り 2 つが x, y(整数)。
  ``events_to_frames`` が極性つきのコマ (T, H, W)(ON = +1、OFF = −1 の和)に積む = 動画として見られる。
"""
from __future__ import annotations

import math
import os

import numpy as np

__all__ = ["read_bvh", "read_events", "events_to_frames"]


# ── BVH ──────────────────────────────────────────────────────────────────────────── #
def _rot(axis: str, deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "X":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "Y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def read_bvh(path) -> dict:
    """BVH を読み、骨格と全コマの関節の世界座標を返す。

    Returns:
        ``names`` 関節名(End Site は ``<親>_end``)、``parents``(根は −1)、``offsets`` (J, 3)、
        ``positions`` (T, J, 3) 世界座標、``frame_time`` [s]、``channels``(関節ごとの CHANNELS の名前)、
        ``motion`` (T, C) の生の値。

    Raises:
        ValueError: HIERARCHY / MOTION が無い、括弧の対応が崩れている、コマの値の数が CHANNELS の合計と違う。
    """
    with open(os.fspath(path), "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    head, sep, motion = text.partition("MOTION")
    if "HIERARCHY" not in head or not sep:
        raise ValueError("read_bvh: HIERARCHY と MOTION の両方が要る")
    tok = head.split()
    names, parents, offsets, channels = [], [], [], []
    stack: list[int] = []
    i = tok.index("HIERARCHY") + 1
    while i < len(tok):
        t = tok[i]
        if t in ("ROOT", "JOINT"):
            names.append(tok[i + 1]); parents.append(stack[-1] if stack else -1)
            offsets.append(np.zeros(3)); channels.append([])
            i += 2
        elif t == "End":                                             # End Site
            names.append(names[stack[-1]] + "_end"); parents.append(stack[-1])
            offsets.append(np.zeros(3)); channels.append([])
            i += 2
        elif t == "{":
            stack.append(len(names) - 1); i += 1
        elif t == "}":
            if not stack:
                raise ValueError("read_bvh: '}' が多い(括弧の対応が崩れている)")
            stack.pop(); i += 1
        elif t == "OFFSET":
            offsets[stack[-1]] = np.array([float(v) for v in tok[i + 1:i + 4]])   # 開いている節(End Site も)
            i += 4
        elif t == "CHANNELS":
            n = int(tok[i + 1]); channels[stack[-1]] = tok[i + 2:i + 2 + n]; i += 2 + n
        else:
            i += 1
    if stack:
        raise ValueError("read_bvh: '{' が閉じていない")
    mt = motion.split()
    try:
        n_frames = int(mt[mt.index("Frames:") + 1])
        k = mt.index("Time:")
        frame_time = float(mt[k + 1])
    except (ValueError, IndexError):
        raise ValueError("read_bvh: MOTION に 'Frames:' と 'Frame Time:' が要る") from None
    vals = np.array([float(v) for v in mt[k + 2:]], dtype=np.float64)
    n_ch = sum(len(c) for c in channels)
    if n_ch == 0 or vals.size != n_frames * n_ch:
        raise ValueError("read_bvh: 値が %d 個(コマ %d × CHANNELS %d = %d のはず)"
                         % (vals.size, n_frames, n_ch, n_frames * n_ch))
    M = vals.reshape(n_frames, n_ch)
    J = len(names)
    off = np.array(offsets)
    pos = np.zeros((n_frames, J, 3))
    for fr in range(n_frames):
        c = 0
        R_w = [None] * J
        for j in range(J):
            R = np.eye(3)
            tr = off[j].copy()
            for ch in channels[j]:
                v = M[fr, c]; c += 1
                if ch.endswith("position"):                         # 平行移動 = OFFSET + 値(根の位置もこれ)
                    tr["XYZ".index(ch[0])] += v
                elif ch.endswith("rotation"):
                    R = R @ _rot(ch[0], v)
            p = parents[j]
            if p < 0:
                R_w[j] = R
                pos[fr, j] = tr
            else:
                R_w[j] = R_w[p] @ R
                pos[fr, j] = pos[fr, p] + R_w[p] @ tr
    return {"names": names, "parents": np.array(parents), "offsets": off, "positions": pos,
            "frame_time": frame_time, "channels": channels, "motion": M}


# ── イベントカメラ ─────────────────────────────────────────────────────────────────── #
_ALIASES = {"x": ("x", "col", "u"), "y": ("y", "row", "v"), "t": ("t", "ts", "time", "timestamp"),
            "p": ("p", "pol", "polarity", "on")}


def _guess_columns(A: np.ndarray) -> dict:
    """見出しの無い (N, 4) の列を中身で x, y, t, p に割り当てる。"""
    cols = list(range(A.shape[1]))
    binary = [c for c in cols if set(np.unique(A[:, c][:4096]).tolist()) <= {0.0, 1.0, -1.0}]
    if not binary:
        raise ValueError("read_events: 極性の列(値が 0/1 か −1/1)が無い")
    pcol = binary[-1]
    rest = [c for c in cols if c != pcol]
    mono = [c for c in rest if np.all(np.diff(A[:, c]) >= 0)]
    if not mono:
        raise ValueError("read_events: 時刻の列(単調非減少)が無い —— 時刻順に並んでいない?")
    tcol = max(mono, key=lambda c: float(np.ptp(A[:, c])))
    xy = [c for c in rest if c != tcol]
    return {"x": xy[0], "y": xy[1], "t": tcol, "p": pcol}


def read_events(path) -> dict:
    """イベントカメラのイベント列を読む(.txt / .csv / .npy / .npz)。

    Returns:
        ``x``・``y``(int64)、``t``(float64、ファイルの単位のまま)、``p``(int8、+1 / −1)、``columns``
        (どの列をどれと読んだか —— 推定したなら ``guessed=True``)、``shape``(x・y の最大 + 1)。
    """
    p_ = os.fspath(path)
    ext = os.path.splitext(p_)[1].lower()
    named = None
    if ext in (".npy", ".npz"):
        obj = np.load(p_, allow_pickle=False)
        if isinstance(obj, np.lib.npyio.NpzFile):
            keys = list(obj.keys())
            if all(any(a in keys for a in al) for al in _ALIASES.values()):
                named = {k: np.asarray(obj[next(a for a in al if a in keys)]) for k, al in _ALIASES.items()}
                A = None
            else:
                A = np.asarray(obj[keys[0]])
        else:
            A = obj
        if named is None and A.dtype.names:
            nm = A.dtype.names
            named = {k: np.asarray(A[next(a for a in al if a in nm)]) for k, al in _ALIASES.items()}
    else:
        with open(p_, "r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
        delim = "," if "," in first else None
        has_head = any(ch.isalpha() for ch in first.replace("e-", "").replace("e+", ""))
        A = np.loadtxt(p_, delimiter=delim, skiprows=1 if has_head else 0, ndmin=2)
        if has_head:
            hdr = [h.strip().lower() for h in (first.split(",") if delim else first.split())]
            try:
                named = {k: A[:, next(hdr.index(a) for a in al if a in hdr)] for k, al in _ALIASES.items()}
            except StopIteration:
                raise ValueError("read_events: 見出し %s に x, y, t, p が揃っていない" % hdr) from None
    guessed = False
    if named is None:
        A = np.asarray(A, np.float64)
        if A.ndim != 2 or A.shape[1] != 4 or A.shape[0] < 1:
            raise ValueError("read_events: (N, 4) の x, y, t, p が要る(形 %s)" % (A.shape,))
        cols = _guess_columns(A)
        named = {k: A[:, c] for k, c in cols.items()}
        guessed = True
        colmap = cols
    else:
        colmap = "by name"
    x = np.asarray(named["x"]).astype(np.int64)
    y = np.asarray(named["y"]).astype(np.int64)
    t = np.asarray(named["t"], np.float64)
    pol = np.where(np.asarray(named["p"], np.float64) > 0, 1, -1).astype(np.int8)
    if x.size and (x.min() < 0 or y.min() < 0):
        raise ValueError("read_events: 座標が負(列の取り違え?)")
    return {"x": x, "y": y, "t": t, "p": pol, "columns": colmap, "guessed": guessed,
            "shape": (int(y.max()) + 1 if y.size else 0, int(x.max()) + 1 if x.size else 0)}


def events_to_frames(events: dict, n_frames: int = 32, shape=None) -> np.ndarray:
    """イベントを時間で n_frames に等分し、画素ごとに極性を足したコマ (T, H, W) にする(ON = +1、OFF = −1)。

    全イベントの極性の和はコマの総和と一致する(落とすイベントは無い)。
    """
    x, y, t, p = events["x"], events["y"], events["t"], events["p"]
    H, W = shape if shape is not None else events["shape"]
    T = int(n_frames)
    if T < 1 or H < 1 or W < 1:
        raise ValueError("events_to_frames: n_frames と shape は正")
    out = np.zeros((T, H, W), np.float64)
    if t.size == 0:
        return out
    span = float(t.max() - t.min())
    k = np.zeros(t.size, np.int64) if span <= 0 else np.minimum(((t - t.min()) / span * T).astype(np.int64), T - 1)
    ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    np.add.at(out, (k[ok], y[ok], x[ok]), p[ok].astype(np.float64))
    return out
