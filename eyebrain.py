# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""eyebrain —— 「複眼が見る像」と「脳の応答」を繋ぐ薄い層(Studio の対話パネルと PoC が共用)。

役目は 4 つ:
1. **データ**: MaleCNS の soma つきニューロンのうち、右眼の六角柱(``assignedOlHex1/2``)ごとの視葉ニューロンと
   中枢のハブを合わせた部分グラフ(キャッシュ npz)。無ければ合成の代替(脳 2 葉 + VNC の点群に距離依存の配線と
   六角柱の割り当て)で同じ経路を走らせ、``provenance`` に ``synthetic surrogate`` と書く。
2. **対応**: 柱 (hex1, hex2) を軸座標として重心を寄せ、``fly_hex_lattice`` の個眼 (u, v) と正規化した座標の最近傍で結ぶ。
   個眼 → 柱 ``ommatidium_to_column``、柱 → 個眼 ``column_to_ommatidium``。近似であることは docstring と展示に書く。
3. **刺激**: 柱の近傍(六角距離 ≤ r)を刺激する列 ``stimulus_for_column`` と、像を ``fly_hex_resample`` で個眼に落とし
   個眼の明るさをその柱の刺激にする ``stimulus_from_image``。どちらも (n,) の W_in 列。
4. **波と絵**: ``run_wave`` は ``reservoir_states(W_in=...)``、``response_peak`` は**刺激ノードを除いた**最大値
   (表示の尺度。刺激ノードは飽和色で別に見せる)、``eye_view`` は個眼の信号を六角の絵にする。

数学は全部 ``conngraph`` / ``flyvision`` の op で、ここは配線だけ(numpy 以外に依存しない)。
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np

import conngraph as _cg
import flyvision as _fv

__all__ = ["EyeBrain", "load", "synthetic_eye_brain", "CACHE_FILE", "SIDE_COLORS"]

CACHE_FILE = "malecns_eye.npz"
SIDE_COLORS = {"L": (0.25, 0.75, 1.0), "R": (1.0, 0.6, 0.2)}
STIM_COLOR = (1.0, 1.0, 0.55)


def _cache_dir() -> str:
    base = os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye")
    return os.path.join(base, "poc_malecns_eye")


def synthetic_eye_brain(n_eye_cols: int = 300, k_per_col: int = 3, n_hub: int = 900, n_bg: int = 20000,
                        seed: int = 20260920) -> dict:
    """合成の代替: 右眼の柱を六角格子(半径 ~10)に置き、柱ごとに k 体、中枢に n_hub 体。配線は距離が近いほど密。"""
    rng = np.random.default_rng(seed)
    cols = [(0, 0)]
    r = 1
    while len(cols) < n_eye_cols:
        for u in range(-r, r + 1):
            for v in range(-r, r + 1):
                if max(abs(u), abs(v), abs(u + v)) == r and len(cols) < n_eye_cols:
                    cols.append((u, v))
        r += 1
    cols = np.array(cols, dtype=float)
    # 柱の soma 位置: 右葉の球面上に六角座標を貼る
    ang = cols * (np.pi / 40.0)
    eye_P = np.column_stack([42.0 + 22.0 * np.cos(ang[:, 0]) * np.cos(ang[:, 1]), 22.0 * np.sin(ang[:, 1]),
                             10.0 + 22.0 * np.sin(ang[:, 0]) * np.cos(ang[:, 1])])
    P_eye = np.repeat(eye_P, k_per_col, axis=0) + rng.normal(0, 1.5, (len(cols) * k_per_col, 3))
    hex_eye = np.repeat(cols, k_per_col, axis=0)

    def cloud(k, center, radii):
        u = rng.standard_normal((k, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        return center + u * (rng.random((k, 1)) ** (1 / 3)) * radii

    P_hub = np.vstack([cloud(n_hub // 2, (0.0, 0.0, 0.0), (26.0, 18.0, 22.0)), cloud(n_hub - n_hub // 2, (0.0, 0.0, -90.0), (16.0, 14.0, 55.0))])
    P = np.vstack([P_eye, P_hub])
    n = len(P)
    hexes = np.full((n, 2), np.nan)
    hexes[: len(P_eye)] = hex_eye
    supc = np.array(["ol_intrinsic"] * len(P_eye) + ["cb_intrinsic"] * (n_hub // 2) + ["vnc_intrinsic"] * (n_hub - n_hub // 2))
    side = np.where(P[:, 0] < 0, "L", "R").astype(str)
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    prob = 0.5 * np.exp(-D / 10.0) + 0.001
    W = (rng.random((n, n)) < prob) * rng.integers(1, 20, (n, n)).astype(np.float64)
    np.fill_diagonal(W, 0.0)
    P_all = np.vstack([cloud(n_bg // 3, (-30.0, 0.0, 0.0), (28.0, 18.0, 22.0)), cloud(n_bg // 3, (30.0, 0.0, 0.0), (28.0, 18.0, 22.0)),
                       cloud(n_bg - 2 * (n_bg // 3), (0.0, 0.0, -90.0), (16.0, 14.0, 55.0))])
    return {"W": W, "P": P, "side": side, "superclass": supc, "hex": hexes, "P_all": P_all}


class EyeBrain:
    """右眼の柱 ↔ 個眼格子 ↔ 脳の部分グラフ。``load()`` で作る。

    Attributes
    ----------
    W, P, side, superclass, hexes, P_all : データ(``hexes`` は (n, 2)、視葉外は NaN)
    columns : (m, 2) 柱の (hex1, hex2)(整列)、``node_col`` : (n,) 各ノードの柱番号(−1 = 視葉外)
    lattice : ``fly_hex_lattice`` の dict、``ommatidium_to_column`` / ``column_to_ommatidium``
    R, R_shuffle : reservoir(rho = 1.0)、``provenance`` : 来歴
    """

    def __init__(self, data: dict, provenance: str, lattice_radius: int = 9, rho: float = 1.0,
                 shuffle_seed: int = 1):
        self.W = np.asarray(data["W"], dtype=np.float64)
        self.P = np.asarray(data["P"], dtype=np.float64)
        self.side = np.asarray(data["side"]).astype(str)
        self.superclass = np.asarray(data["superclass"]).astype(str)
        self.hexes = np.asarray(data["hex"], dtype=np.float64)
        self.P_all = np.asarray(data["P_all"], dtype=np.float64)
        self.provenance = provenance
        n = self.W.shape[0]
        eye = np.isfinite(self.hexes[:, 0])
        cols = sorted({(int(a), int(b)) for a, b in self.hexes[eye]})
        self.columns = np.array(cols, dtype=np.float64)
        index = {c: k for k, c in enumerate(cols)}
        self.node_col = np.full(n, -1, dtype=np.int64)
        for i in np.nonzero(eye)[0]:
            self.node_col[i] = index[(int(self.hexes[i, 0]), int(self.hexes[i, 1]))]
        self.lattice = _fv.fly_hex_lattice(radius=int(lattice_radius))
        uv = np.asarray(self.lattice["uv"], dtype=np.float64)
        cu = self.columns - self.columns.mean(axis=0)
        a = uv / max(float(np.abs(uv).max()), 1e-9)
        b = cu / max(float(np.abs(cu).max()), 1e-9)
        d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
        self.ommatidium_to_column = d.argmin(axis=1)
        self.column_to_ommatidium = d.argmin(axis=0)
        self.R = _cg.reservoir_from_graph(self.W, rho=rho)
        self._rho = rho
        self._shuffle_seed = shuffle_seed
        self._R_shuffle = None
        self.colors = np.array([SIDE_COLORS.get(s, (0.85, 0.85, 0.85)) for s in self.side])

    # ------------------------------------------------------------------ data
    @property
    def n(self) -> int:
        return int(self.W.shape[0])

    @property
    def R_shuffle(self) -> np.ndarray:
        """次数保存 shuffle の reservoir(初回に作る: 2 × 辺数の swap)。"""
        if self._R_shuffle is None:
            m = int((self.W > 0).sum())
            Wsh = _cg.graph_degree_preserving_shuffle(self.W, n_swaps=2 * m, seed=self._shuffle_seed)
            self._R_shuffle = _cg.reservoir_from_graph(Wsh, rho=self._rho)
        return self._R_shuffle

    # ------------------------------------------------------------------ stimulus
    def column_neighbourhood(self, k: int, radius: int = 1) -> np.ndarray:
        """柱 k と六角距離 ≤ radius の柱の番号。"""
        c = self.columns
        d = c - c[int(k)]
        hexdist = np.maximum.reduce([np.abs(d[:, 0]), np.abs(d[:, 1]), np.abs(d[:, 0] + d[:, 1])])
        return np.nonzero(hexdist <= radius + 1e-9)[0]

    def stimulus_for_column(self, k: int, radius: int = 1, amp: float = 2.0) -> np.ndarray:
        """柱 k の近傍を刺激する (n,) の列(W_in の列)。"""
        near = self.column_neighbourhood(k, radius)
        return np.where(np.isin(self.node_col, near), float(amp), 0.0)

    def eye_signal(self, image2d: Any, fov_deg: float = 100.0, max_side: int = 160) -> np.ndarray:
        """像を個眼に落とした信号 (n_ommatidia,)、[0, 1]。

        ``fly_hex_resample`` は個眼数 × 画素数の重み行列を持つ(上限 2^24)ので、長辺が ``max_side`` を超える像は
        整数倍の升で面積平均して縮めてから渡す(個眼の受容野は数度で、それより細かい画素は要らない)。
        """
        img = np.asarray(image2d, dtype=np.float64)
        if img.ndim == 3:
            img = img[..., :3].mean(axis=2)
        f = int(np.ceil(max(img.shape) / float(max_side)))
        if f > 1:
            H, W = (img.shape[0] // f) * f, (img.shape[1] // f) * f
            img = img[:H, :W].reshape(H // f, f, W // f, f).mean(axis=(1, 3))
        sig = _fv.fly_hex_resample(img, self.lattice, fov_deg=float(fov_deg))
        sig = np.asarray(sig["signal"] if isinstance(sig, dict) else sig, dtype=np.float64)
        peak = float(sig.max())
        return sig / peak if peak > 0.0 else sig

    def stimulus_from_signal(self, signal: np.ndarray, amp: float = 2.0) -> np.ndarray:
        """個眼の信号 → 柱ごとの最大 → その柱のノードへ (n,) の刺激。"""
        sig = np.asarray(signal, dtype=np.float64)
        per_col = np.zeros(len(self.columns))
        np.maximum.at(per_col, self.ommatidium_to_column, sig)
        out = np.zeros(self.n)
        eye = self.node_col >= 0
        out[eye] = per_col[self.node_col[eye]] * float(amp)
        return out

    def stimulus_from_image(self, image2d: Any, amp: float = 2.0) -> np.ndarray:
        return self.stimulus_from_signal(self.eye_signal(image2d), amp)

    # ------------------------------------------------------------------ wave
    def run_wave(self, stimulus: np.ndarray, steps: int = 24, hold: int = 3, leak: float = 0.6,
                 shuffle: bool = False) -> np.ndarray:
        """パルス(t = 0..hold−1)を入れた状態列 (steps, n)。"""
        U = np.zeros((int(steps), 1))
        U[: int(hold), 0] = 1.0
        w_in = np.asarray(stimulus, dtype=np.float64).reshape(self.n, 1)
        return _cg.reservoir_states(self.R_shuffle if shuffle else self.R, U, leak=leak, W_in=w_in)

    @staticmethod
    def response_peak(X: np.ndarray, stimulus: np.ndarray) -> float:
        """刺激ノードを除いた |x| の最大(表示の尺度)。応答が無ければ 0。"""
        A = np.abs(np.asarray(X, dtype=np.float64))
        mask = np.asarray(stimulus) > 0
        if mask.all():
            return 0.0
        return float(A[:, ~mask].max()) if A.shape[0] else 0.0

    def brightness(self, x: np.ndarray, stimulus: np.ndarray, peak: float, gain: float = 30.0) -> np.ndarray:
        """1 コマの明るさ (n,) ∈ [0, 1]: 対数輝度(尺度 peak = 刺激を除いた応答の最大)、刺激ノードは 1。

        gain 30 で peak の 10 % が 0.36、2 % が 0.11。peak が 0(応答なし)なら刺激以外は 0。
        """
        b = np.log1p(gain * np.abs(x) / peak) / np.log1p(gain) if peak > 0.0 else np.zeros(self.n)
        b = np.clip(b, 0.0, 1.0)
        b[np.asarray(stimulus) > 0] = 1.0
        return b

    def node_colors(self, stimulus: np.ndarray) -> np.ndarray:
        """側の色(橙 = 右、青 = 左)、刺激ノードは黄。明るさは掛けていない((n, 3))。"""
        cols = self.colors.copy()
        cols[np.asarray(stimulus) > 0] = STIM_COLOR
        return cols

    def frame_colors(self, x: np.ndarray, stimulus: np.ndarray, peak: float, gain: float = 30.0,
                     floor: float = 0.12) -> np.ndarray:
        """1 コマのノード色 (n, 3) = node_colors × (floor + (1 − floor) × brightness)(Studio の Viewer3D 用。
        底が高いと静止ノードの密な視葉が「点いて」見える —— 2026-09-20 に実測 —— ので 0.12)。"""
        b = self.brightness(x, stimulus, peak, gain)
        return self.node_colors(stimulus) * (floor + (1.0 - floor) * b[:, None])

    # ------------------------------------------------------------------ eye view
    def eye_view(self, signal: np.ndarray | None = None, size: int = 300, highlight: np.ndarray | None = None) -> np.ndarray:
        """個眼格子の絵 (size, size, 3)。signal は個眼ごとの [0, 1](None なら一様)、highlight は柱番号の集合(黄で縁取り)。"""
        uv = np.asarray(self.lattice["uv"], dtype=np.float64)
        xy = self.lattice_xy(size)
        img = np.full((size, size, 3), 0.08)
        rad = max(2.0, 0.5 * size / (2.0 * float(np.abs(uv).max()) + 2.0) * 0.95)
        sig = np.full(len(uv), 0.25) if signal is None else np.clip(np.asarray(signal, dtype=np.float64), 0.0, 1.0)
        hl = set() if highlight is None else set(int(k) for k in np.asarray(highlight).ravel())
        yy, xx = np.mgrid[0:size, 0:size]
        for o in range(len(uv)):
            m = (xx - xy[o, 0]) ** 2 + (yy - xy[o, 1]) ** 2 <= rad * rad
            if int(self.ommatidium_to_column[o]) in hl:
                img[m] = STIM_COLOR                                  # 刺激した柱は黄で塗りつぶす
            else:
                v = 0.12 + 0.8 * sig[o]
                img[m] = (v, v, v * 0.85)
        return img

    def lattice_xy(self, size: int) -> np.ndarray:
        """個眼 (u, v) → 画素 (x, y)(軸座標を正六角格子に写す)。"""
        # ★fly_hex_resample と同じ向き: 画面の x = 方位角 az(右が正)、y = 仰角 el(上が正)。uv から組むと
        #   像と眼の絵の左右が食い違う(2026-09-20 に実測: 縞を右へ動かすと柱の u が減った)。
        az = np.asarray(self.lattice["az_rad"], dtype=np.float64)
        el = np.asarray(self.lattice["el_rad"], dtype=np.float64)
        s = 0.5 * size / (max(float(np.abs(az).max()), float(np.abs(el).max())) * 1.12 + 1e-9)
        return np.column_stack([size / 2.0 + az * s, size / 2.0 - el * s])

    def ommatidium_at(self, x: float, y: float, size: int) -> int:
        """画素 (x, y) に最も近い個眼の番号。"""
        xy = self.lattice_xy(size)
        return int(np.argmin((xy[:, 0] - x) ** 2 + (xy[:, 1] - y) ** 2))

    def column_at(self, x: float, y: float, size: int) -> int:
        return int(self.ommatidium_to_column[self.ommatidium_at(x, y, size)])


def load(cache_dir: str | None = None, lattice_radius: int = 9) -> EyeBrain:
    """キャッシュ npz があればそれを、無ければ合成の代替を ``EyeBrain`` にして返す。"""
    d = cache_dir or _cache_dir()
    npz = os.path.join(d, CACHE_FILE)
    if os.path.exists(npz):
        z = np.load(npz)
        data = {k: z[k] for k in ("W", "P", "side", "superclass", "hex", "P_all")}
        return EyeBrain(data, "MaleCNS v1.0 right-eye columns + hubs (cache: %s)" % npz, lattice_radius)
    return EyeBrain(synthetic_eye_brain(), "synthetic surrogate (no cache at %s)" % npz, lattice_radius)
