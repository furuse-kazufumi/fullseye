# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測の深度カメラの軌跡と平面の残差を、外の真値と公表された雑音の形で採点する(TUM RGB-D)。

ミュンヘン工科大学(TUM)が公開した RGB-D の実測データ(Kinect、``freiburg1_xyz``、CC BY 4.0)から
**32 枚の深度画像**(全 798 枚の 5 枚おき、約 5 秒)を、配布されたバイト列のまま ``data/tum_rgbd_fr1_xyz/``
に同梱した(SHA-256 を下の :data:`BUNDLED` に固定。出典・ライセンスは同ディレクトリの README.md)。
真値は 2 種類で、どちらも**外**にある:

1. **カメラ軌跡の真値**(モーションキャプチャ、``groundtruth.txt``)。深度を点群にし
   (``depth_to_organized_points``・``normals_from_depth``・``occlusion_edges``)、隣り合う 2 枚を
   ``icp_point2plane`` で合わせて相対姿勢を出し、真値の相対姿勢との差を **RPE**、鎖にした軌跡の位置の差を
   **ATE**(剛体整列後)で採点する。基準は「合わせない」(単位行列)。
2. **雑音の形**: Khoshelham & Elberink (2012, Sensors 12(2):1437) の式 (7) は、深度の標準偏差が距離の 2 乗に比例する
   (σ_Z = (m / f b) Z² σ_d′)と述べる。局所の平面(24 × 24 画素の窓)の当てはめ残差
   (``fit_plane_3d``)を距離ごとの中央値で見て、増え方がその形に乗るかを測る。

★ここで**測っていない**もの: 密な深度の真値は無いので深度の絶対誤差は測れない(姿勢と平面性だけ)。
標本は 1 系列・32 枚。公開された SLAM 手法との直接対決はしない(標本が違う)。
一次文献の**式の形**(距離の 2 乗)は確認したが、本文の係数 ``|m/(f b)| = 2.85e-5`` の**単位は本文から確認できなかった**ので、
係数の絶対値は門に使わず、傾きと増え方だけで採点する。

★門は結果を見てから置いた(1 系列を見ながら決めた)。ICP の ``trim``(下位の対応を捨てる割合)は前半 15 組で
選び、後半 16 組で採点する(1 回きりの分割)。分割の外(全 31 組)の数字も印字する。

実行例::

    py -3.11 examples/poc_real_tum_rgbd_slam.py

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): 深度と窓の残差、軌跡、組ごとの並進誤差、距離と雑音、判定の表。
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

L = fs.ledger
DATA = ROOT / "data" / "tum_rgbd_fr1_xyz"

#: 同梱ファイル: 名前 → (バイト数, SHA-256)。2026-11-11 に配布元の tgz(448,204,271 B)から取り出した値。
#: 深度 PNG は配布されたバイト列のまま、2 つのテキストは行の抜き出し(値は無改変)。
BUNDLED = {
    "depth_subset.txt":
        (1546, "ac0a0bea44fd8f4d4d512926288654f886a389a36267762c991d714bd84cb824"),
    "groundtruth_subset.txt":
        (36089, "430f412aa050798d57661728670ecdfc1b0d979d75f7e27ff4fa94708577707e"),
    "depth/1305031102.160407.png":
        (125530, "3d2b60049ced75b1c4f468ee1ff734650e4b31ca1a535698a02a1434f41eafae"),
    "depth/1305031102.329195.png":
        (122297, "d2f103ac3cf0e387a1276f57f4890880082668525a93d6d1d664406a1ae44093"),
    "depth/1305031102.494271.png":
        (120384, "53232cdd3fce4bafee048ee7d2ad0417b672b8c45ecc8673c920b36c86c14d6c"),
    "depth/1305031102.663273.png":
        (117639, "edb828d280ae6b64c98fe73ae3b031388188dd353116f38824c4f75d3af729bc"),
    "depth/1305031102.828537.png":
        (118833, "cc53c137bd6d292df3e93de9ce9a3f947595b7e7ce5fb7c2aab776b010333564"),
    "depth/1305031102.994164.png":
        (120003, "c7779af30bfc5634d45b59a45c9fb20d789497e81f489f2dd1a9142c368ae0de"),
    "depth/1305031103.162795.png":
        (122751, "7f931cabc8359bf8f407fd66b5f254dfa4feec8e4f94e830462f883a1fbd90ae"),
    "depth/1305031103.327550.png":
        (121434, "7ff74264151361d514299440a78def57725c433b12fc2f72118cdeb6d97c7025"),
    "depth/1305031103.494472.png":
        (123042, "2d210bf2617d2b40f9b2053a80fd961db9626ea6be273da0e4a0dd55de95715e"),
    "depth/1305031103.663594.png":
        (122983, "cfad6ba61b7d699bb86bc38cdb8190cc01b753e061a3c2ef6e99c34a23292c63"),
    "depth/1305031103.830367.png":
        (120867, "471eca30fa895109f592b8a8c84446e0ba00f76dbd41a8c948b00c88d6dc9efc"),
    "depth/1305031103.994365.png":
        (122650, "614ef8247fc9531737bd95d387b342597a32cd8baa8158c8a3e8d03dd31a302c"),
    "depth/1305031104.163440.png":
        (123321, "f80486c27a5b2911366b7667dbbf96571eeeb91e76ea96bd270692d1d92d60ac"),
    "depth/1305031104.331403.png":
        (124363, "17df0e45b8dfe49cab8915b1017b1e54ea408ea13b2edd5089aceb379807215f"),
    "depth/1305031104.495673.png":
        (124766, "31d5ba10451b6957561b23c49aa85785797ffe81c5456e2ac20f27f52640dc39"),
    "depth/1305031104.659863.png":
        (128142, "c6267d979f1bb453525dc8e1fb949b82b43859da57135cabffcf88a469501d6c"),
    "depth/1305031104.830961.png":
        (129688, "58a4e6143d49445f403e24945fcbf58c8e067e3446563496496cbb5f7e0b1b06"),
    "depth/1305031104.998342.png":
        (132193, "300dc291ad49fe121c0520510c06596a7c9077881bce805c6183a2da6a0a0927"),
    "depth/1305031105.159979.png":
        (130793, "b55505884a9b15c2484e7cf308625aa75cfd1a5253bc303b3d9e81b00728911c"),
    "depth/1305031105.328878.png":
        (125122, "f1a2dab70bba3f8244bb6e30cad4071b29d7f20366b46c295946ef560a65ca69"),
    "depth/1305031105.497931.png":
        (123671, "350fb47c2535f4a468b3b64e34bce3d889f361610971a4a36d0cf85105e82232"),
    "depth/1305031105.659104.png":
        (120517, "36ca0a381ecba80e1e8e838239ffcb07730857df50e3c60420b1496a2c9cf121"),
    "depth/1305031105.830008.png":
        (120061, "64fd564a531ac9ec927577fba7e19c052d86ba9e72d8a0e585893b0d3566d384"),
    "depth/1305031105.998271.png":
        (122339, "42d741bbf2a20fbc022eb947eeb39f7d98b860694865fa2a3736ed3b3a31dce4"),
    "depth/1305031106.166330.png":
        (122825, "079d484572f7c3c2affc7b3856a51185989536073a653d5f0ef80c04e46a2b72"),
    "depth/1305031106.330215.png":
        (121953, "9e177f323ab6e472377f178c82acceb44f3ceb589f059406ed14e68c769b7def"),
    "depth/1305031106.498096.png":
        (120684, "7ec1a134cb59196e09046112f1dea963ca85ad353e37675f407937f07cb56c89"),
    "depth/1305031106.667282.png":
        (122751, "90e6bae15f4f875d8edfc0aba3317b0653358abf5bc0397a8d8ddea6e3100ec3"),
    "depth/1305031106.830652.png":
        (119736, "7f94f1705b1d69172b986a49fafa12311a7fd719e497e22e5aedadefa558285b"),
    "depth/1305031106.998876.png":
        (118865, "ed0a66c343a3671a6936e602561afdb0ba0cc38a98f0d994e3981226f67c5468"),
    "depth/1305031107.165964.png":
        (119329, "e4e647ad0038e137cbf4b79578c8613394b0c09e8789b0f310bafd685c802fae"),
    "depth/1305031107.334800.png":
        (123185, "a9dea7cf1131c9f59f79a76a9e4049c9618e36d791afadb5299cfc62b121e047"),
}

SOURCE = ("TUM RGB-D benchmark, freiburg1_xyz (Sturm, Engelhard, Endres, Burgard, Cremers, IROS 2012), "
          "CC BY 4.0, https://cvg.cit.tum.de/data/datasets/rgbd-dataset; 5 枚おき 32 枚の深度のみ、画像は無改変")

#: 深度 PNG の倍率(TUM のファイル形式の記述 "scaled by a factor of 5000"、0 = 欠測)。
DEPTH_SCALE = 5000.0
#: 内部パラメータ。TUM の記述が推奨する ROS の既定値(深度の歪みは補正しない)。
K_ROS = (525.0, 525.0, 319.5, 239.5)
#: 比較用: TUM のページの Freiburg 1 の IR(深度)カメラの値。歪みの補正は掛けない。
K_FR1_IR = (591.1, 590.1, 331.0, 234.0)
IMG_SHAPE = (480, 640)
#: 有効画素の割合の下限。同梱 32 枚の実測は 0.70〜0.80(穴は光沢・斜面・遠方)。0.5 未満の画像は拒否する。
MIN_VALID_FRACTION = 0.5
#: 使う深度の範囲[m](装置の仕様 0.5〜5 m、近い側の余裕と遠方の疎な点を外す)。
Z_MIN, Z_MAX = 0.3, 3.5
#: 点を間引く間隔(画素)。1 枚あたり約 1 万点。
POINT_STRIDE = 5
#: 1 枚から取る点の下限(空・ほぼ空の通過を防ぐ)。
MIN_POINTS = 3000
#: 真値の 100 Hz の標本が深度の時刻をはさむ間隔の上限[s]。
MAX_GT_GAP_S = 0.05
#: ICP の設定。trim の候補は前半で選ぶ。
ICP_ITERS = 40
TRIM_CANDIDATES = (None, 0.1, 0.2, 0.3)
#: 窓の一辺(画素)・窓の有効画素の割合の下限・窓の法線の |n_z| の下限。
TILE = 24
TILE_MIN_VALID = 0.95
TILE_MIN_NZ = 0.5
#: 距離の区間[m]。1 区間は窓 30 個以上・5 枚以上から出たものだけ採る。
Z_EDGES = (0.5, 0.7, 0.9, 1.1, 1.3, 1.6, 2.0, 3.0)
BIN_MIN_TILES, BIN_MIN_FRAMES = 30, 5


class DepthRejected(ValueError):
    """深度画像を受け付けなかった(理由を名指しする。黙って通さない)。"""


class Gates:
    """門を 1 つずつ記録し、最後にまとめて判定する(どれが外れたかを全部出す)。"""

    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((name, ok, detail))
        print("  [%s] %s%s" % ("OK" if ok else "NG", name, (" — " + detail) if detail else ""))
        return ok

    def failed(self) -> list[tuple[str, bool, str]]:
        return [r for r in self.rows if not r[1]]


# --------------------------------------------------------------------------- #
# データ
# --------------------------------------------------------------------------- #
def load_bundled(name: str) -> bytes:
    """同梱ファイルを読み、バイト数と SHA-256 が台帳と一致したときだけ返す(fail-closed)。"""
    if name not in BUNDLED:
        raise KeyError("台帳に無い同梱ファイル: %s" % name)
    size, digest = BUNDLED[name]
    path = DATA / name
    if not path.is_file():
        raise realdata.RealDataError("同梱の実データが無い: data/tum_rgbd_fr1_xyz/%s" % name)
    raw = path.read_bytes()
    if len(raw) != size:
        raise realdata.RealDataError("%s のバイト数 %d が台帳 %d と違う" % (name, len(raw), size))
    got = hashlib.sha256(raw).hexdigest()
    if got != digest:
        raise realdata.RealDataError("%s の SHA-256 %s が台帳と違う" % (name, got))
    return raw


def decode_depth(raw: bytes) -> np.ndarray:
    """16 bit PNG のバイト列 → 深度[m](0 = 欠測のまま)。"""
    import io
    im = Image.open(io.BytesIO(raw))
    if im.mode != "I;16":
        raise DepthRejected("深度 PNG が 16 bit でない: mode=%s" % im.mode)
    return np.asarray(im, dtype=np.float64) / DEPTH_SCALE


def check_depth(depth: np.ndarray, label: str = "depth") -> float:
    """深度画像の入口の門。有効画素の割合を返す。基準を満たさなければ :class:`DepthRejected`。

    欠測 0 だらけの画像は、点群も法線も作れるが**意味が無い**(空の点群へ合わせて「成功」する)ので拒否する。
    """
    d = np.asarray(depth)
    if d.shape != IMG_SHAPE:
        raise DepthRejected("%s: 形 %s は %s でない" % (label, d.shape, IMG_SHAPE))
    if not np.all(np.isfinite(d)):
        raise DepthRejected("%s: NaN / inf を含む" % label)
    if np.any(d < 0):
        raise DepthRejected("%s: 負の深度を含む" % label)
    valid = float(np.mean((d > 0) & (d < Z_MAX)))
    if valid < MIN_VALID_FRACTION:
        raise DepthRejected("%s: 有効画素 %.1f %% が下限 %.0f %% 未満" % (label, 100 * valid, 100 * MIN_VALID_FRACTION))
    return valid


def load_sequence() -> dict:
    """同梱の 32 枚と真値を読む。実データを読んだ印をここで残す。"""
    rows = [ln.split() for ln in load_bundled("depth_subset.txt").decode().splitlines() if ln and ln[0] != "#"]
    ts = np.array([float(r[0]) for r in rows])
    depth = [decode_depth(load_bundled(r[1])) for r in rows]
    gt = np.array([[float(v) for v in ln.split()]
                   for ln in load_bundled("groundtruth_subset.txt").decode().splitlines() if ln and ln[0] != "#"])
    realdata.mark_read("tum-rgbd-fr1-xyz")       # 成熟度台帳の「実データを読んだ」記録(D6)
    return {"ts": ts, "depth": depth, "gt": gt}


# --------------------------------------------------------------------------- #
# 真値の姿勢
# --------------------------------------------------------------------------- #
def quat_to_matrix(q) -> np.ndarray:
    x, y, z, w = np.asarray(q, float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(q0, q1, u: float) -> np.ndarray:
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    if q0 @ q1 < 0:
        q1 = -q1
    theta = math.acos(min(1.0, float(q0 @ q1)))
    if theta < 1e-8:
        return q0
    return (math.sin((1 - u) * theta) * q0 + math.sin(u * theta) * q1) / math.sin(theta)


def gt_pose_at(gt: np.ndarray, t: float) -> tuple[np.ndarray, float]:
    """真値の時刻列から時刻 t の 4x4 姿勢(線形 + 球面線形補間)と、はさむ標本の間隔[s]。"""
    j = int(np.searchsorted(gt[:, 0], t))
    if j <= 0 or j >= len(gt):
        raise DepthRejected("時刻 %.3f が真値の範囲の外" % t)
    a, b = gt[j - 1], gt[j]
    gap = float(b[0] - a[0])
    u = (t - a[0]) / gap
    pose = np.eye(4)
    pose[:3, :3] = quat_to_matrix(slerp(a[4:8], b[4:8], u))
    pose[:3, 3] = a[1:4] * (1 - u) + b[1:4] * u
    return pose, gap


def rotation_angle_deg(R: np.ndarray) -> float:
    return math.degrees(math.acos(float(np.clip((np.trace(R) - 1) / 2, -1, 1))))


def rigid_align(src: np.ndarray, dst: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Umeyama(尺度なし)。dst ≈ R src + t の最小二乗の剛体。"""
    ms, md = src.mean(0), dst.mean(0)
    u, _, vt = np.linalg.svd((src - ms).T @ (dst - md))
    s = np.eye(3)
    s[2, 2] = np.sign(np.linalg.det(vt.T @ u.T))
    R = vt.T @ s @ u.T
    return R, md - R @ ms


# --------------------------------------------------------------------------- #
# 深度 → 点群 → 登録
# --------------------------------------------------------------------------- #
def make_cloud(depth: np.ndarray, K=K_ROS, stride: int = POINT_STRIDE) -> tuple[np.ndarray, np.ndarray]:
    """深度 → (点 (N,3)[m], 法線 (N,3))。遮蔽の縁と欠測の隣・範囲外を外し、``stride`` 画素おきに間引く。"""
    check_depth(depth)
    pts = L.depth_to_organized_points(depth, *K)
    nrm = L.normals_from_depth(depth, *K)
    edge = L.occlusion_edges(depth, 0.05)
    ok = binary_erosion((depth > Z_MIN) & (depth < Z_MAX) & ~edge, iterations=2)
    keep = np.zeros_like(ok)
    keep[::stride, ::stride] = True
    ok &= keep
    if int(ok.sum()) < MIN_POINTS:
        raise DepthRejected("使える点 %d が下限 %d 未満" % (int(ok.sum()), MIN_POINTS))
    return pts[ok], nrm[ok].astype(np.float64)


def register_pair(src_cloud, dst_cloud, trim) -> np.ndarray:
    """``src`` を ``dst`` に合わせる 4x4(dst ≈ R src + t)。"""
    R, t, _aligned, _rmse, _n = L.icp_point2plane.raw(src_cloud[0], dst_cloud[0], dst_cloud[1],
                                                      iters=ICP_ITERS, trim=trim)
    T = np.eye(4)
    T[:3, :3] = np.asarray(R)
    T[:3, 3] = np.asarray(t)
    return T


def pair_errors(est: np.ndarray, gt_rel: np.ndarray) -> tuple[float, float]:
    """相対姿勢の誤差 E = gt_rel⁻¹ · est の(並進[m], 回転[度])。TUM の RPE の定義。"""
    E = np.linalg.inv(gt_rel) @ est
    return float(np.linalg.norm(E[:3, 3])), rotation_angle_deg(E[:3, :3])


def rms(x) -> float:
    return float(np.sqrt(np.mean(np.square(np.asarray(x, float)))))


def trajectory(seq: dict) -> dict:
    """真値の姿勢と、そこから出る相対姿勢・基準(合わせない)の誤差。"""
    poses, gaps = zip(*[gt_pose_at(seq["gt"], float(t)) for t in seq["ts"]])
    rel = [np.linalg.inv(poses[i]) @ poses[i + 1] for i in range(len(poses) - 1)]
    ident = [pair_errors(np.eye(4), r) for r in rel]
    return {"poses": poses, "gaps": np.array(gaps), "rel": rel,
            "ident_t": np.array([a for a, _ in ident]), "ident_r": np.array([b for _, b in ident])}


def ate_rmse(chain: list[np.ndarray], poses) -> tuple[float, np.ndarray]:
    """鎖にした推定の位置と真値の位置(どちらも最初のフレーム基準)を剛体整列して RMSE[m]。"""
    est = np.array([c[:3, 3] for c in chain])
    inv0 = np.linalg.inv(poses[0])
    ref = np.array([(inv0 @ np.append(p[:3, 3], 1.0))[:3] for p in poses])
    R, t = rigid_align(est, ref)
    err = np.linalg.norm(est @ R.T + t - ref, axis=1)
    return rms(err), err


def chain_of(rels: list[np.ndarray]) -> list[np.ndarray]:
    out = [np.eye(4)]
    for T in rels:
        out.append(out[-1] @ T)
    return out


def evaluate_registration(seq: dict, traj: dict, K=K_ROS) -> dict:
    """全組を trim の候補ごとに合わせ、前半で選び、後半で採点する。"""
    clouds = [make_cloud(d, K) for d in seq["depth"]]
    n_pairs = len(clouds) - 1
    half = n_pairs // 2
    est: dict = {}
    err_t: dict = {}
    err_r: dict = {}
    for trim in TRIM_CANDIDATES:
        e = [register_pair(clouds[i + 1], clouds[i], trim) for i in range(n_pairs)]
        pe = [pair_errors(e[i], traj["rel"][i]) for i in range(n_pairs)]
        est[trim] = e
        err_t[trim] = np.array([a for a, _ in pe])
        err_r[trim] = np.array([b for _, b in pe])
    chosen = min(TRIM_CANDIDATES, key=lambda k: rms(err_t[k][:half]))
    return {"est": est, "err_t": err_t, "err_r": err_r, "half": half, "chosen": chosen,
            "n_points": [len(c[0]) for c in clouds], "n_pairs": n_pairs}


# --------------------------------------------------------------------------- #
# 窓の平面残差(距離と雑音)
# --------------------------------------------------------------------------- #
def tile_residuals(depth: np.ndarray, K=K_ROS, tile: int = TILE):
    """深度 → 窓ごとの (平均深度[m], 深度方向の残差の標準偏差[m], 窓の左上の行・列)。

    窓 = ``tile`` × ``tile`` 画素。有効画素 95 % 以上・遮蔽の縁なしの窓だけ、``fit_plane_3d`` の
    直交残差 RMS を ``|n_z|`` で割って深度方向の標準偏差にする。
    """
    pts = L.depth_to_organized_points(depth, *K)
    edge = L.occlusion_edges(depth, 0.05)
    good = (depth > Z_MIN) & (depth < Z_MAX) & ~edge
    out = []
    for v in range(0, depth.shape[0] - tile + 1, tile):
        for u in range(0, depth.shape[1] - tile + 1, tile):
            g = good[v:v + tile, u:u + tile]
            if g.mean() < TILE_MIN_VALID:
                continue
            q = pts[v:v + tile, u:u + tile][g]
            _c, n, res = L.fit_plane_3d(q)
            nz = abs(float(n[2]))
            if nz < TILE_MIN_NZ:
                continue
            out.append((float(q[:, 2].mean()), float(res) / nz, v, u))
    return out


def bin_medians(records: list) -> list[dict]:
    """距離の区間ごとの窓の残差の中央値。窓 30 個以上・5 枚以上の区間だけ返す。"""
    rows = []
    z = np.array([r[0] for r in records])
    s = np.array([r[1] for r in records])
    f = np.array([r[4] for r in records])
    for lo, hi in zip(Z_EDGES[:-1], Z_EDGES[1:]):
        m = (z >= lo) & (z < hi)
        n_frames = len(set(f[m].tolist()))
        if int(m.sum()) >= BIN_MIN_TILES and n_frames >= BIN_MIN_FRAMES:
            rows.append({"lo": lo, "hi": hi, "n": int(m.sum()), "frames": n_frames,
                         "z": float(np.median(z[m])), "sigma": float(np.median(s[m])),
                         "p25": float(np.percentile(s[m], 25))})
    return rows


def loglog_slope(rows: list[dict]) -> float:
    return float(np.polyfit(np.log([r["z"] for r in rows]), np.log([r["sigma"] for r in rows]), 1)[0])


def synthetic_plane_depth(sigma_m: float, seed: int = 0, tilt_deg: float = 30.0, z0: float = 1.0) -> np.ndarray:
    """1 m の傾いた平面の深度(16 bit の量子化 1/5000 m まで再現、雑音 ``sigma_m``)。窓の推定器の検算用。"""
    v, u = np.mgrid[0:IMG_SHAPE[0], 0:IMG_SHAPE[1]]
    ray = np.stack([(u - K_ROS[2]) / K_ROS[0], (v - K_ROS[3]) / K_ROS[1], np.ones_like(u, dtype=float)], -1)
    th = math.radians(tilt_deg)
    n = np.array([math.sin(th), 0.0, math.cos(th)])
    z = z0 / (ray @ n)
    if sigma_m > 0:
        z = z + np.random.default_rng(seed).normal(0.0, sigma_m, z.shape)
    return np.round(z * DEPTH_SCALE) / DEPTH_SCALE


def whole_plane_sigma(depth: np.ndarray, lo: float, hi: float, K=K_ROS) -> list[float]:
    """比較用: 画像全体から ``plane_segmentation`` + ``euclidean_cluster`` で大きな面を取り、距離 [lo, hi) の部分の残差。"""
    pts = L.depth_to_organized_points(depth, *K)
    edge = L.occlusion_edges(depth, 0.05)
    ok = binary_erosion((depth > Z_MIN) & (depth < Z_MAX) & ~edge, iterations=2)
    keep = np.zeros_like(ok)
    keep[::3, ::3] = True
    p = pts[ok & keep]
    lab = L.plane_segmentation(p, 0.02, 1500, 3, 300, 0)
    out = []
    for k in range(int(lab.max()) + 1):
        q = p[lab == k]
        cl = L.euclidean_cluster(q, 0.06, 50)
        if cl.size == 0 or cl.max() < 0:
            continue
        q = q[cl == 0]
        c = q.mean(0)
        n = np.linalg.svd(q - c, full_matrices=False)[2][2]
        if abs(n[2]) < 0.6:
            continue
        r = (q - c) @ n / abs(n[2])
        m = (q[:, 2] >= lo) & (q[:, 2] < hi)
        if int(m.sum()) >= 300:
            out.append(float(r[m].std()))
    return out


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def tile_map(depth: np.ndarray, rec: list, tile: int = TILE) -> np.ndarray:
    img = np.zeros(depth.shape)
    for _z, s, v, u in rec:
        img[v:v + tile, u:u + tile] = s * 1000.0
    return img


def write_figures(seq, traj, reg, noise, g: Gates) -> None:
    if not figs.enabled():
        return
    k = 4
    d = seq["depth"][k]
    rec = [r for r in tile_residuals(d)]
    figs.save_grid("depth_and_tiles", [d, tile_map(d, rec)],
                   captions=["深度[m](黒 = 欠測 0)", "窓(24×24 画素)の平面残差[mm](黒 = 窓なし)"],
                   title="同梱 32 枚のうち 5 枚目の深度と、窓ごとの平面当てはめ残差",
                   caption="TUM RGB-D fr1/xyz の深度(Kinect、机の上)。右は窓ごとの当てはめ残差(深度方向)。"
                           "窓は欠測・縁・急な傾きを外した平らに近い所だけ。距離ごとの中央値は別の図。",
                   vrange=[(0.0, 2.0), (0.0, 8.0)], colorbar=True, unit="")
    # 軌跡: 真値の主軸 2 本へ投影
    inv0 = np.linalg.inv(traj["poses"][0])
    ref = np.array([(inv0 @ np.append(p[:3, 3], 1.0))[:3] for p in traj["poses"]])
    chosen = reg["chosen"]
    ch = chain_of(reg["est"][chosen])
    pe = np.array([c[:3, 3] for c in ch])
    R, t = rigid_align(pe, ref)
    pe = pe @ R.T + t
    c0 = ref.mean(0)
    axes = np.linalg.svd(ref - c0, full_matrices=False)[2][:2]
    a, b = (ref - c0) @ axes.T, (pe - c0) @ axes.T
    figs.save_plot("trajectory",
                   [("真値(モーションキャプチャ)", list(a[:, 0]), list(a[:, 1])),
                    ("ICP の鎖(剛体整列後)", list(b[:, 0]), list(b[:, 1])),
                    ("合わせない(原点のまま)", [0.0], [0.0])],
                   kinds=["line", "line", "scatter"], styles=["dashed", None, None],
                   colors=["reference", "emphasis", "wrong"], xlabel="主軸 1 [m]", ylabel="主軸 2 [m]",
                   title="カメラ軌跡: ATE %.0f mm(合わせない %.0f mm)" % (1e3 * noise["ate"], 1e3 * noise["ate_ident"]),
                   caption="カメラ位置の軌跡を真値の主軸 2 本へ投影した。ICP の鎖は誤差が溜まる(ドリフト)。",
                   source=SOURCE, aspect="equal")
    steps = list(range(1, reg["n_pairs"] + 1))
    figs.save_plot("rpe_steps",
                   [("合わせない(真値の動きの大きさ)", steps, list(traj["ident_t"] * 1e3)),
                    ("ICP(trim なし、既定)", steps, list(reg["err_t"][None] * 1e3)),
                    ("ICP(trim %s)" % chosen, steps, list(reg["err_t"][chosen] * 1e3))],
                   kinds=["line", "line", "line"], styles=["dashed", None, None],
                   colors=["reference", "wrong", "emphasis"], xlabel="隣り合う 2 枚の組(約 0.17 秒おき)",
                   ylabel="相対姿勢の並進誤差 [mm]",
                   title="RPE の組ごとの並進誤差(後半 %d 組が採点、前半は trim を選んだ組)" % (reg["n_pairs"] - reg["half"]),
                   caption="破線は「合わせない」の誤差 = 真値の 1 組あたりの動き(約 60 mm)。ICP は大半の組で小さいが、"
                           "動きが大きい組で外れることがある。", source=SOURCE)
    rows = noise["bins"]
    z = [r["z"] for r in rows]
    s = [r["sigma"] * 1e3 for r in rows]
    zz = np.linspace(min(z) * 0.9, max(z) * 1.1, 30)
    anchor = rows[int(np.argmin([abs(r["z"] - 1.0) for r in rows]))]
    c2 = anchor["sigma"] * 1e3 / anchor["z"] ** 2
    figs.save_plot("sigma_vs_z",
                   [("窓の残差の中央値(距離の区間ごと)", z, s),
                    ("σ ∝ Z²(形だけ。1 m 付近に合わせた)", list(zz), list(c2 * zz ** 2)),
                    ("σ ∝ Z(比較)", list(zz), list(anchor["sigma"] * 1e3 / anchor["z"] * zz))],
                   kinds=["scatter", "line", "line"], styles=[None, "dashed", "dotted"],
                   colors=["emphasis", "reference", "neutral"], xlabel="平面の距離 Z [m]",
                   ylabel="深度方向の残差の標準偏差 [mm]",
                   title="窓の残差は距離で増えるが、2 m 以下は Z に比例(傾き %.2f、Z² なら 2)" % noise["slope_le2"],
                   caption="点は 24×24 画素の窓の残差の中央値。破線は Khoshelham & Elberink 2012 の式(7)の形(距離の 2 乗)を"
                           "1 m 付近の点に合わせたもの(係数は実測に合わせたので、論文の係数との比較ではない)。",
                   source=SOURCE)
    header = ["門", "判定", "中身"]
    rows_t = [[n, "OK" if ok else "NG", dt] for n, ok, dt in g.rows]
    figs.save_table("verdicts", header, rows_t, title="門 %d 本(外れ %d 本)" % (len(g.rows), len(g.failed())),
                    caption="結果を見てから置いた門を含む(docstring の限界を参照)。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    seq = load_sequence()
    n = len(seq["depth"])
    print("読んだ: %d 枚(深度 480x640)、真値 %d 行  [%s]" % (n, len(seq["gt"]), SOURCE))

    # --- 入口の門 ---------------------------------------------------------- #
    valid = [check_depth(d, "frame %d" % i) for i, d in enumerate(seq["depth"])]
    g.check("有効画素が全 %d 枚で下限以上" % n,
            min(valid) >= MIN_VALID_FRACTION, "実測 %.1f〜%.1f %%(下限 %.0f %%)" % (100 * min(valid), 100 * max(valid), 100 * MIN_VALID_FRACTION))
    rejected = {}
    zeros = np.zeros(IMG_SHAPE)
    mostly = seq["depth"][0].copy()
    mostly[:, :] = 0.0
    mostly[:60, :] = seq["depth"][0][:60, :]
    nan_frame = seq["depth"][0].copy()
    nan_frame[0, 0] = np.nan
    for label, bad in (("全部 0", zeros), ("9 割 0", mostly), ("NaN", nan_frame), ("形違い", zeros[:100])):
        try:
            check_depth(bad, label)
            rejected[label] = False
        except DepthRejected:
            rejected[label] = True
    g.check("0 だらけ・NaN・形違いを拒否する", all(rejected.values()), ", ".join("%s=%s" % kv for kv in rejected.items()))
    try:
        make_cloud(zeros)
        refused_cloud = False
    except DepthRejected:
        refused_cloud = True
    g.check("全部 0 の深度から点群を作らない", refused_cloud, "空の点群を ICP に通さない")
    traj = trajectory(seq)
    g.check("真値の標本間隔が 0.05 s 以下",
            float(traj["gaps"].max()) <= MAX_GT_GAP_S, "最大 %.1f ms" % (1e3 * float(traj["gaps"].max())))

    # --- 軌跡 ------------------------------------------------------------- #
    print("\n[軌跡] 隣り合う 2 枚を icp_point2plane で合わせ、真値の相対姿勢と比べる(trim 候補 %s)" % (TRIM_CANDIDATES,))
    reg = evaluate_registration(seq, traj)
    half, chosen, npair = reg["half"], reg["chosen"], reg["n_pairs"]
    g.check("1 枚から取った点が下限 %d 以上" % MIN_POINTS, min(reg["n_points"]) >= MIN_POINTS,
            "実測 %d〜%d 点" % (min(reg["n_points"]), max(reg["n_points"])))
    print("  trim 候補ごとの並進 RPE の RMS [mm](前半 %d 組 / 後半 %d 組 / 全 %d 組):" % (half, npair - half, npair))
    for trim in TRIM_CANDIDATES:
        et = reg["err_t"][trim]
        print("    trim=%-5s %7.1f / %7.1f / %7.1f   回転 %.2f°" % (trim, 1e3 * rms(et[:half]), 1e3 * rms(et[half:]),
                                                                 1e3 * rms(et), rms(reg["err_r"][trim])))
    it, ir = traj["ident_t"], traj["ident_r"]
    print("    合わせない %7.1f / %7.1f / %7.1f   回転 %.2f°" % (1e3 * rms(it[:half]), 1e3 * rms(it[half:]), 1e3 * rms(it), rms(ir)))
    print("  前半で選んだ trim = %s" % (chosen,))
    best_b = min(TRIM_CANDIDATES, key=lambda k: rms(reg["err_t"][k][half:]))
    print("  ★選択は後半に移っていない: 後半だけで見ると最良は trim=%s(%.1f mm)で、前半で選んだ trim=%s は %.1f mm"
          % (best_b, 1e3 * rms(reg["err_t"][best_b][half:]), chosen, 1e3 * rms(reg["err_t"][chosen][half:])))
    et, er = reg["err_t"][chosen], reg["err_r"][chosen]
    rpe_t_b, rpe_t_id_b = rms(et[half:]), rms(it[half:])
    rpe_r_b, rpe_r_id_b = rms(er[half:]), rms(ir[half:])
    print("  ★後半(採点): 並進 %.1f mm(合わせない %.1f mm、比 %.2f)、回転 %.2f°(合わせない %.2f°)、最大 %.1f mm、"
          "中央 %.1f mm" % (1e3 * rpe_t_b, 1e3 * rpe_t_id_b, rpe_t_b / rpe_t_id_b, rpe_r_b, rpe_r_id_b,
                           1e3 * float(et[half:].max()), 1e3 * float(np.median(et[half:]))))
    g.check("後半の並進 RPE が合わせないの半分未満", rpe_t_b < 0.5 * rpe_t_id_b,
            "%.1f mm 対 %.1f mm(比 %.2f)" % (1e3 * rpe_t_b, 1e3 * rpe_t_id_b, rpe_t_b / rpe_t_id_b))
    g.check("後半の回転 RPE が合わせないより小", rpe_r_b < rpe_r_id_b, "%.2f° 対 %.2f°" % (rpe_r_b, rpe_r_id_b))
    default_t = rms(reg["err_t"][None])
    g.check("既定(trim なし)でも並進 RPE が合わせないより小", default_t < rms(it),
            "全 31 組で %.1f mm 対 %.1f mm(比 %.2f)" % (1e3 * default_t, 1e3 * rms(it), default_t / rms(it)))
    ch = chain_of(reg["est"][chosen])
    ate, ate_err = ate_rmse(ch, traj["poses"])
    ate_ident, _ = ate_rmse([np.eye(4)] * n, traj["poses"])
    ate_default, _ = ate_rmse(chain_of(reg["est"][None]), traj["poses"])
    path = float(np.sum(np.linalg.norm(np.diff([p[:3, 3] for p in traj["poses"]], axis=0), axis=1)))
    print("  ATE(鎖、剛体整列後)RMSE: 選んだ trim %.1f mm / 既定 %.1f mm / 合わせない %.1f mm(経路長 %.2f m、"
          "最終ドリフト %.1f mm)" % (1e3 * ate, 1e3 * ate_default, 1e3 * ate_ident, path, 1e3 * float(ate_err[-1])))
    g.check("ATE が合わせないの半分未満", ate < 0.5 * ate_ident,
            "%.1f mm 対 %.1f mm(全 %d 組の鎖)" % (1e3 * ate, 1e3 * ate_ident, npair))
    # 内部パラメータの感度
    reg_ir = evaluate_registration(seq, traj, K_FR1_IR)
    ir_t = rms(reg_ir["err_t"][chosen])
    print("  内部パラメータを IR の公称値(%s、歪み補正なし)にすると、同じ trim の全組の並進 RPE %.1f mm(ROS の既定 %.1f mm)"
          % (K_FR1_IR, 1e3 * ir_t, 1e3 * rms(et)))
    g.check("内部パラメータを替えても合わせないより良い", ir_t < rms(it), "%.1f mm 対 %.1f mm" % (1e3 * ir_t, 1e3 * rms(it)))

    # --- 雑音 ------------------------------------------------------------- #
    print("\n[雑音] 窓(%d×%d 画素)の平面当てはめ残差(深度方向)を、距離の区間ごとの中央値で見る" % (TILE, TILE))
    flat = synthetic_plane_depth(0.0)
    floor = float(np.median([r[1] for r in tile_residuals(flat)]))
    noisy = synthetic_plane_depth(0.003)
    got = float(np.median([r[1] for r in tile_residuals(noisy)]))
    print("  推定器の検算: 雑音なし(量子化のみ)の傾いた平面で中央値 %.3f mm、σ=3 mm を足すと %.2f mm" % (1e3 * floor, 1e3 * got))
    g.check("検算: 量子化だけの平面で窓残差 0.3 mm 未満", floor < 3e-4, "%.3f mm" % (1e3 * floor))
    g.check("検算: 足した雑音 3 mm を ±10 % で返す", abs(got - 3e-3) < 3e-4, "%.2f mm" % (1e3 * got))
    records = []
    for i, d in enumerate(seq["depth"]):
        records += [(*r[:4], i) for r in tile_residuals(d)]
    # records の列は (z, sigma, v, u, frame)
    bins = bin_medians(records)
    print("  窓 %d 個(%d 枚から)。区間ごとの中央値:" % (len(records), n))
    for r in bins:
        print("    Z %.1f〜%.1f m: 窓 %4d 個(%2d 枚)、Z の中央 %.2f m、σ_z 中央 %.2f mm(下位 25 %% %.2f mm)、σ/Z² = %.2f mm/m²"
              % (r["lo"], r["hi"], r["n"], r["frames"], r["z"], 1e3 * r["sigma"], 1e3 * r["p25"], 1e3 * r["sigma"] / r["z"] ** 2))
    g.check("距離の区間が 4 つ以上", len(bins) >= 4, "%d 区間(窓 %d 個以上・%d 枚以上のもの)" % (len(bins), BIN_MIN_TILES, BIN_MIN_FRAMES))
    slope = loglog_slope(bins)
    slope_le2 = loglog_slope([r for r in bins if r["hi"] <= 2.0])
    near = [r for r in bins if r["z"] < 0.8][0]
    far = [r for r in bins if 1.1 <= r["z"] < 1.6][0]
    ratio = far["sigma"] / near["sigma"]
    print("  対数の傾き(σ と Z): 全区間 %.2f、2 m 以下の区間だけ %.2f(式 (7) の形は 2、Z に比例なら 1)。遠い側(Z≈%.2f)/ 近い側(Z≈%.2f)= %.2f 倍"
          % (slope, slope_le2, far["z"], near["z"], ratio))
    print("  ★2 m 以下では Z² でなくほぼ Z に比例(傾き %.2f)。全区間で 1.4 に見えるのは 2〜3 m の 1 区間(%.1f mm)が引き上げた分で、"
          "その区間が遠方の斜めの壁など別の事情かは未確認。Z² の形は、この標本では確認できなかった。" % (slope_le2, 1e3 * bins[-1]["sigma"]))
    mono = all(b["sigma"] >= a["sigma"] for a, b in zip(bins[:-1], bins[1:]))
    g.check("区間の中央値が距離で単調に増える", mono,
            " → ".join("%.2f" % (1e3 * r["sigma"]) for r in bins) + " mm")
    g.check("遠い側が近い側の 1.5 倍以上", ratio >= 1.5, "1.1〜1.6 m 対 0.8 m 未満で %.2f 倍" % ratio)
    # 参考(門にしない): 画像全体の面の残差との違い
    lo, hi = 0.9, 1.1
    whole = [x for d in seq["depth"] for x in whole_plane_sigma(d, lo, hi)]
    tile_b = [r for r in bins if r["lo"] == lo][0]
    if whole:
        print("  参考: 画像全体の大きな面(plane_segmentation + euclidean_cluster、しきい 20 mm)の Z %.1f〜%.1f m の残差 中央 %.2f mm"
              "(%d 面)は、同じ距離の窓の %.2f mm の %.1f 倍 ―― 大きな面の残差は雑音でなく机の上の凹凸と面の取り方を含む"
              % (lo, hi, 1e3 * float(np.median(whole)), len(whole), 1e3 * tile_b["sigma"], float(np.median(whole)) / tile_b["sigma"]))
    kh_coef = 2.85e-5
    print("  一次文献: 式 (7) σ_Z = (m / f b) Z² σ_d′、本文の |m/(f b)| = %.2e と σ_d′ = 1/2 画素。本文は単位を書かず、"
          "単位を決められないので係数の絶対値は未確認(門にしていない)。" % kh_coef)

    noise = {"bins": bins, "slope": slope, "slope_le2": slope_le2, "ratio": ratio, "ate": ate, "ate_ident": ate_ident}
    record = {
        "n_frames": n, "n_pairs": npair, "chosen_trim": chosen,
        "rpe_t_mm": {"b_icp": round(1e3 * rpe_t_b, 2), "b_ident": round(1e3 * rpe_t_id_b, 2),
                     "all_icp": round(1e3 * rms(et), 2), "all_ident": round(1e3 * rms(it), 2),
                     "all_default": round(1e3 * default_t, 2)},
        "rpe_r_deg": {"b_icp": round(rpe_r_b, 3), "b_ident": round(rpe_r_id_b, 3)},
        "ate_mm": {"icp": round(1e3 * ate, 2), "default": round(1e3 * ate_default, 2), "ident": round(1e3 * ate_ident, 2)},
        "sigma_z_mm": [[r["z"], round(1e3 * r["sigma"], 3)] for r in bins], "slope": round(slope, 3),
        "slope_le2m": round(slope_le2, 3),
        "gates": len(g.rows), "failed": len(g.failed()),
    }
    print("\nRECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))
    write_figures(seq, traj, reg, noise, g)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise SystemExit("門が %d 本外れた: %s" % (len(bad), "; ".join(r[0] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
