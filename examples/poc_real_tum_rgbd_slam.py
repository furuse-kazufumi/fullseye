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

★基準は 3 つある。「合わせない」(単位行列)は**最弱**で、RPE は真値の動きの大きさそのもの、ATE は真値の経路の広がりにすぎない
(ICP の出発点も単位行列なので、比べているのは ICP 自身の出発点との比)。そこで**等速**(直前の組の真値の相対姿勢をそのまま使う。真値を
使う oracle)を足した。ICP は等速とほぼ同じ水準で、設定(trim)によっては勝つが、ここでは「等速よりはっきり良い」とは言わない。

★ここで**測っていない**もの: 密な深度の真値は無いので深度の絶対誤差は測れない(姿勢と平面性だけ)。
標本は 1 系列・32 枚。公開された SLAM 手法との直接対決はしない(標本が違う)。
一次文献の**式の形**(距離の 2 乗)は確認したが、本文の係数 ``|m/(f b)| = 2.85e-5`` の**単位は本文から確認できなかった**ので、
係数の絶対値は門に使わず、傾きと増え方だけで採点する。

★門は結果を見てから置いた(1 系列を見ながら決めた)。ICP の ``trim``(下位の対応を捨てる割合)は前半 15 組で
選び、後半 16 組で採点する。**この 1 回の分割だけの話で、一般化しない**: 他の 7 通りの分割(後半→前半・偶数→奇数・奇数→偶数・
4 分割)も印字する。後半 16 組の RMS は 3 組(組 16〜18、分割の直後の 1 つの失敗)が二乗和の大半を占めるので、
それを除いた値・中央値・組の復元抽出による比の区間も印字する。

★雑音の門(「単調に増える」「遠い側が近い側の 1.5 倍以上」)は、距離に比例しても 2 乗でも通る。**Z² を排除できる門ではない**
(増えることの確認だけ)。窓の残差は (a) センサの雑音、(b) 構造化光の深度カメラの視差の量子化(段差は Z² で増える)、(c) 窓の中の面の凹凸と
窓の物理的な広さ(窓は遠いほど広い)の混ざりで、窓の大きさを替えると値が変わる(センサ雑音だけなら一定のはず)。
この PoC は「雑音の距離依存を測った」とは言わず、「窓の残差が距離でどう増えるか」と、その中の量子化の寄与の見積りまでを言う。

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


def rms_of(x) -> float:
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
    return rms_of(err), err


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
    chosen = min(TRIM_CANDIDATES, key=lambda k: rms_of(err_t[k][:half]))
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


def bin_medians(records: list, edges=Z_EDGES) -> list[dict]:
    """距離の区間ごとの窓の残差の中央値。窓 30 個以上・5 枚以上の区間だけ返す。"""
    rows = []
    z = np.array([r[0] for r in records])
    s = np.array([r[1] for r in records])
    f = np.array([r[4] for r in records])
    for lo, hi in zip(edges[:-1], edges[1:]):
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
# 基準・分割・量子化(独立レビューの指摘への応答、2026-11-11)
# --------------------------------------------------------------------------- #
def constant_velocity_errors(rel: list[np.ndarray]) -> np.ndarray:
    """等速の基準(oracle): 直前の組の**真値**の相対姿勢をそのまま推定として使った並進誤差[m]。組 1 以降の ``len(rel) - 1`` 個。"""
    return np.array([pair_errors(rel[i - 1], rel[i])[0] for i in range(1, len(rel))])


def split_scores(err_t: dict, ident: np.ndarray, n: int) -> list[dict]:
    """trim を選択側の RMS 最小で選び、採点側の RMS を「合わせない」と比べる。8 通りの分割。"""
    idx = np.arange(n)
    h = n // 2
    defs = [("前半→後半(本文の分割)", idx < h, idx >= h), ("後半→前半", idx >= h, idx < h),
            ("偶数→奇数", idx % 2 == 0, idx % 2 == 1), ("奇数→偶数", idx % 2 == 1, idx % 2 == 0)]
    for f in range(4):
        te = (idx * 4 // n) == f
        defs.append(("4 分割の %d 番目を採点" % (f + 1), ~te, te))
    rows = []
    for name, sel, sc in defs:
        ch = min(TRIM_CANDIDATES, key=lambda k: rms_of(err_t[k][sel]))
        icp, idn = rms_of(err_t[ch][sc]), rms_of(ident[sc])
        rows.append({"name": name, "trim": ch, "icp": icp, "ident": idn, "ratio": icp / idn,
                     "default": rms_of(err_t[None][sc])})
    return rows


def bootstrap_ratio(err: np.ndarray, ident: np.ndarray, idx, n_boot: int = 5000, seed: int = 0) -> tuple[float, float]:
    """組を復元抽出して RMS の比(ICP / 合わせない)の 95 % 区間を出す(標本が 16 組と小さいので、点の比を精密に読まない)。"""
    rng = np.random.default_rng(seed)
    idx = np.asarray(idx)
    ratios = [rms_of(err[s]) / rms_of(ident[s]) for s in (rng.choice(idx, len(idx)) for _ in range(n_boot))]
    lo, hi = np.percentile(ratios, [2.5, 97.5])
    return float(lo), float(hi)


def fit_disparity_grid(depths: list[np.ndarray]) -> dict:
    """同梱の深度の**実測の値**から、逆深度(≒視差)の量子化の格子(刻み・位相)を推定する。論文や校正の定数は使わない。

    32 枚で現れた深度の値(0.5〜3 m)の逆数が等間隔の格子に乗るなら、位相を刻みで巻いたベクトルの平均の長さ(整列度)が 1 に近い。
    刻みは 0.0025〜0.0035 /m を走査して整列度が最大のものを取る。
    """
    levels = np.unique(np.concatenate([np.unique(d[(d > 0.5) & (d < 3.0)]) for d in depths]))
    inv = 1.0 / levels
    deltas = np.linspace(0.0025, 0.0035, 2001)
    coh = np.array([abs(np.mean(np.exp(2j * np.pi * inv / dl))) for dl in deltas])
    k = int(np.argmax(coh))
    delta = float(deltas[k])
    offset = float(np.angle(np.mean(np.exp(2j * np.pi * inv / delta))) / (2 * np.pi) * delta)
    return {"delta": delta, "offset": offset, "alignment": float(coh[k]), "n_levels": int(len(levels))}


def quantize_disparity(depth: np.ndarray, grid: dict) -> np.ndarray:
    """深度を逆深度の格子に丸め、16 bit の 1/5000 m に量子化する(雑音ゼロの視差量子化の模擬)。"""
    inv = 1.0 / depth
    q = grid["offset"] + grid["delta"] * np.round((inv - grid["offset"]) / grid["delta"])
    return np.round(DEPTH_SCALE / q) / DEPTH_SCALE


def quantization_only_sigma(grid: dict, z0: float, tilt_deg: float = 30.0) -> float:
    """雑音ゼロの傾いた平面(中心の距離 z0)を視差量子化して、窓推定器にかけた残差の中央値[m]。"""
    plane = synthetic_plane_depth(0.0, z0=z0, tilt_deg=tilt_deg)
    res = [r[1] for r in tile_residuals(quantize_disparity(plane, grid))]
    return float(np.median(res)) if res else float("nan")

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
                   caption="TUM RGB-D fr1/xyz の深度(構造化光の深度カメラ、机の上)。右は窓ごとの当てはめ残差(深度方向)。"
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
    ymax = float(max(traj["ident_t"].max(), reg["err_t"][None].max()) * 1e3)
    cut = noise["half"] + 0.5
    figs.save_plot("rpe_steps",
                   [("合わせない(真値の動きの大きさ)", steps, list(traj["ident_t"] * 1e3)),
                    ("等速(直前の真値、oracle)", steps[1:], list(noise["cv"] * 1e3)),
                    ("ICP(trim なし、既定)", steps, list(reg["err_t"][None] * 1e3)),
                    ("ICP(trim %s、前半で選んだ)" % chosen, steps, list(reg["err_t"][chosen] * 1e3)),
                    ("ICP(trim 0.1、後半だけなら最良)", steps, list(reg["err_t"][0.1] * 1e3)),
                    ("分割位置(前半 %d | 後半 %d)" % (noise["half"], reg["n_pairs"] - noise["half"]), [cut, cut], [0.0, ymax])],
                   kinds=["line"] * 6, styles=["dashed", "dashed", None, None, None, "dotted"],
                   colors=["reference", "neutral", "wrong", "emphasis", "right", "neutral"],
                   xlabel="隣り合う 2 枚の組(約 0.17 秒おき)", ylabel="相対姿勢の並進誤差 [mm]",
                   title="RPE の組ごとの並進誤差(分割の直後の組 16〜18 で ICP が外れる)",
                   caption="破線は「合わせない」の誤差(= 真値の 1 組あたりの動き、約 60 mm)と、直前の真値を使う等速の誤差。"
                           "点線は trim を選んだ前半 15 組と採点した後半 16 組の境。ICP は大半の組で小さいが、境の直後の 3 組"
                           "(組 16〜18)で外れ、後半の二乗和の大半を占める。", source=SOURCE)
    rows = noise["bins"]
    z = [r["z"] for r in rows]
    s = [r["sigma"] * 1e3 for r in rows]
    zz = np.linspace(min(z) * 0.9, max(z) * 1.1, 30)
    anchor = rows[int(np.argmin([abs(r["z"] - 1.0) for r in rows]))]
    c2 = anchor["sigma"] * 1e3 / anchor["z"] ** 2
    q_rows = noise["q_rows"]
    figs.save_plot("sigma_vs_z",
                   [("窓の残差の中央値(距離の区間ごと)", z, s),
                    ("量子化だけの合成平面(雑音ゼロ)", [r["z"] for r in q_rows], [r["q"] * 1e3 for r in q_rows]),
                    ("σ ∝ Z²(形だけ。1 m 付近に合わせた)", list(zz), list(c2 * zz ** 2)),
                    ("σ ∝ Z(比較)", list(zz), list(anchor["sigma"] * 1e3 / anchor["z"] * zz))],
                   kinds=["scatter", "scatter", "line", "line"], styles=[None, None, "dashed", "dotted"],
                   colors=["emphasis", "right", "reference", "neutral"], xlabel="平面の距離 Z [m]",
                   ylabel="深度方向の残差の標準偏差 [mm]",
                   title="窓の残差(雑音+量子化+凹凸)は距離で増える: 2 m 以下の傾き %.2f〜%.2f" % (noise["slope_lo"], noise["slope_hi"]),
                   caption="点は 24×24 画素の窓の残差の中央値(センサの雑音だけではなく、視差の量子化・窓の中の凹凸・窓の広さを含む)。"
                           "水色の点は雑音ゼロの傾いた平面を、同梱の深度から推定した視差の格子で量子化したもの(1.4 m 以遠は実測の大半を説明する)。"
                           "破線は式(7)の形(距離の 2 乗)を 1 m 付近の点に合わせたもの(係数は実測に合わせたので、論文の係数との比較ではない)。"
                           "傾きは窓の大きさ(12・24・48 画素)と区間の取り方で変わる。",
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
        print("    trim=%-5s %7.1f / %7.1f / %7.1f   回転 %.2f°" % (trim, 1e3 * rms_of(et[:half]), 1e3 * rms_of(et[half:]),
                                                                 1e3 * rms_of(et), rms_of(reg["err_r"][trim])))
    it, ir = traj["ident_t"], traj["ident_r"]
    print("    合わせない %7.1f / %7.1f / %7.1f   回転 %.2f°" % (1e3 * rms_of(it[:half]), 1e3 * rms_of(it[half:]), 1e3 * rms_of(it), rms_of(ir)))
    print("  前半で選んだ trim = %s" % (chosen,))
    best_b = min(TRIM_CANDIDATES, key=lambda k: rms_of(reg["err_t"][k][half:]))
    print("  ★選択は後半に移っていない: 後半だけで見ると最良は trim=%s(%.1f mm)で、前半で選んだ trim=%s は %.1f mm"
          % (best_b, 1e3 * rms_of(reg["err_t"][best_b][half:]), chosen, 1e3 * rms_of(reg["err_t"][chosen][half:])))
    et, er = reg["err_t"][chosen], reg["err_r"][chosen]
    rpe_t_b, rpe_t_id_b = rms_of(et[half:]), rms_of(it[half:])
    rpe_r_b, rpe_r_id_b = rms_of(er[half:]), rms_of(ir[half:])
    print("  ★後半(採点): 並進 %.1f mm(合わせない %.1f mm、比 %.2f)、回転 %.2f°(合わせない %.2f°)、最大 %.1f mm、"
          "中央 %.1f mm" % (1e3 * rpe_t_b, 1e3 * rpe_t_id_b, rpe_t_b / rpe_t_id_b, rpe_r_b, rpe_r_id_b,
                           1e3 * float(et[half:].max()), 1e3 * float(np.median(et[half:]))))
    g.check("後半の並進 RPE が合わせないの半分未満", rpe_t_b < 0.5 * rpe_t_id_b,
            "%.1f mm 対 %.1f mm(比 %.2f)" % (1e3 * rpe_t_b, 1e3 * rpe_t_id_b, rpe_t_b / rpe_t_id_b))
    g.check("後半の回転 RPE が合わせないより小", rpe_r_b < rpe_r_id_b, "%.2f° 対 %.2f°" % (rpe_r_b, rpe_r_id_b))
    default_t = rms_of(reg["err_t"][None])
    g.check("既定(trim なし)でも並進 RPE が合わせないより小", default_t < rms_of(it),
            "全 31 組で %.1f mm 対 %.1f mm(比 %.2f)" % (1e3 * default_t, 1e3 * rms_of(it), default_t / rms_of(it)))
    ch = chain_of(reg["est"][chosen])
    ate, ate_err = ate_rmse(ch, traj["poses"])
    ate_ident, _ = ate_rmse([np.eye(4)] * n, traj["poses"])
    ate_default, _ = ate_rmse(chain_of(reg["est"][None]), traj["poses"])
    path = float(np.sum(np.linalg.norm(np.diff([p[:3, 3] for p in traj["poses"]], axis=0), axis=1)))
    print("  ATE(鎖、剛体整列後)RMSE: 選んだ trim %.1f mm / 既定 %.1f mm / 合わせない %.1f mm(経路長 %.2f m、"
          "最終ドリフト %.1f mm)" % (1e3 * ate, 1e3 * ate_default, 1e3 * ate_ident, path, 1e3 * float(ate_err[-1])))
    g.check("ATE が合わせないの半分未満", ate < 0.5 * ate_ident,
            "%.1f mm 対 %.1f mm(全 %d 組の鎖)" % (1e3 * ate, 1e3 * ate_ident, npair))
    # --- 基準を強くする(等速)・分割を替える・3 組の影響 ------------------------------ #
    rel = traj["rel"]
    cv = constant_velocity_errors(rel)                  # 組 1 以降(組 0 は直前が無い)
    sl = slice(1, npair)
    cv_rms, id1_rms = rms_of(cv), rms_of(it[sl])
    print("\n[基準] 等速(直前の組の真値の相対姿勢をそのまま使う oracle、組 1〜%d の %d 組):" % (npair - 1, npair - 1))
    print("    等速 %.1f mm / 合わせない %.1f mm / ICP(trim %s)%.1f mm / ICP(trim 0.1)%.1f mm / ICP(既定)%.1f mm"
          % (1e3 * cv_rms, 1e3 * id1_rms, chosen, 1e3 * rms_of(et[sl]), 1e3 * rms_of(reg["err_t"][0.1][sl]),
             1e3 * rms_of(reg["err_t"][None][sl])))
    icp_over_cv = rms_of(et[sl]) / cv_rms
    print("  ★選んだ trim の ICP は等速の %.2f 倍(%s)。「合わせない」比 %.2f だけを見ると良く見えるが、等速との比はこう。"
          % (icp_over_cv, "ほぼ同じ" if 0.8 <= icp_over_cv <= 1.25 else ("ICP が良い" if icp_over_cv < 0.8 else "等速が良い"),
             rms_of(et[sl]) / id1_rms))
    t_mean = np.eye(4)
    t_mean[:3, 3] = np.mean([r[:3, 3] for r in rel], axis=0)
    ate_cv, _ = ate_rmse(chain_of([np.eye(4)] + [rel[i - 1] for i in range(1, npair)]), traj["poses"])
    ate_mean, _ = ate_rmse(chain_of([t_mean] * npair), traj["poses"])
    print("  ATE: 等速(oracle)の鎖 %.1f mm / 真値の平均の動きを足すだけの鎖 %.1f mm / 合わせない %.1f mm / ICP %.1f mm"
          "(合わせないの ATE は真値の経路の広がりにすぎない)" % (1e3 * ate_cv, 1e3 * ate_mean, 1e3 * ate_ident, 1e3 * ate))
    g.check("選んだ trim の ICP が等速の 1.5 倍以内", icp_over_cv <= 1.5,
            "%.1f mm 対 %.1f mm(%.2f 倍。等速より良いとは言わない)" % (1e3 * rms_of(et[sl]), 1e3 * cv_rms, icp_over_cv))
    e2 = et[half:]
    sq = np.sort(e2 ** 2)
    share3 = float(sq[-3:].sum() / sq.sum())
    rms_wo3 = rms_of(np.sort(e2)[:-3])
    worst = sorted(int(i) + 1 for i in np.argsort(e2)[-3:] + half)
    worse = [i + 1 for i in range(npair) if et[i] > it[i]]
    print("  後半 %d 組の RMS %.1f mm は、最悪の 3 組(組 %s)が二乗和の %.0f %%。3 組を除くと %.1f mm、中央値 %.1f mm。"
          "この 3 組は分割の直後に連続する 1 つの失敗。trim %s が合わせないより悪い組: %s"
          % (npair - half, 1e3 * rms_of(e2), worst, 100 * share3, 1e3 * rms_wo3, 1e3 * float(np.median(e2)), chosen, worse))
    ci_lo, ci_hi = bootstrap_ratio(et, it, np.arange(half, npair))
    print("  後半の比 %.2f の 95 %% 区間(組の復元抽出 5000 回): %.2f〜%.2f" % (rpe_t_b / rpe_t_id_b, ci_lo, ci_hi))
    g.check("後半の比の 95 % 区間の上端が 1 未満", ci_hi < 1.0, "%.2f〜%.2f(点の 0.42 は精度過剰)" % (ci_lo, ci_hi))
    splits = split_scores(reg["err_t"], it, npair)
    print("  分割を替えると(trim は選択側の RMS 最小で選ぶ。ICP / 合わせない、mm):")
    for r in splits:
        print("    %-22s trim=%-5s %6.1f / %6.1f = %.2f(既定 %.1f)" % (r["name"], r["trim"], 1e3 * r["icp"], 1e3 * r["ident"],
                                                                  r["ratio"], 1e3 * r["default"]))
    ratios = [r["ratio"] for r in splits]
    n01 = sum(r["trim"] == 0.1 for r in splits)
    print("  ★比は %.2f〜%.2f(本文の分割は最悪の %.2f)。trim 0.1 が選ばれたのは 8 通り中 %d 通り、本文の分割だけ 0.2。"
          "全 31 組では trim 0.1 が %.1f mm、0.2 が %.1f mm。「選択が後半に移らない」は**この 1 回の分割の話**で一般化しない。"
          % (min(ratios), max(ratios), ratios[0], n01, 1e3 * rms_of(reg["err_t"][0.1]), 1e3 * rms_of(et)))
    g.check("分割 8 通りのどれでも合わせないの半分未満", max(ratios) < 0.5, "比 %.2f〜%.2f" % (min(ratios), max(ratios)))
    # 内部パラメータの感度
    reg_ir = evaluate_registration(seq, traj, K_FR1_IR)
    ir_t = rms_of(reg_ir["err_t"][chosen])
    print("  内部パラメータを IR の公称値(%s、歪み補正なし)にすると、同じ trim の全組の並進 RPE %.1f mm(ROS の既定 %.1f mm)"
          % (K_FR1_IR, 1e3 * ir_t, 1e3 * rms_of(et)))
    g.check("内部パラメータを替えても合わせないより良い", ir_t < rms_of(it), "%.1f mm 対 %.1f mm" % (1e3 * ir_t, 1e3 * rms_of(it)))

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
    print("  ★2 m 以下の傾きは %.2f。全区間で 1.4 に見えるのは 2〜3 m の 1 区間(%.1f mm)が引き上げた分(下の量子化だけの見積りは 7.8 mm で 6 割。残りは斜面の |n_z| での割り算などの可能性があるが未確認)。"
          "Z² の形は、この標本では支持されなかった(反証ではない、下を参照)。" % (slope_le2, 1e3 * bins[-1]["sigma"]))
    mono = all(b["sigma"] >= a["sigma"] for a, b in zip(bins[:-1], bins[1:]))
    g.check("区間の中央値が距離で単調に増える(Z でも Z² でも通る)", mono,
            " → ".join("%.2f" % (1e3 * r["sigma"]) for r in bins) + " mm")
    g.check("遠い側が近い側の 1.5 倍以上(Z でも Z² でも通る)", ratio >= 1.5, "1.1〜1.6 m 対 0.8 m 未満で %.2f 倍" % ratio)
    # --- 量子化・窓の大きさの寄与(独立レビュー S4) ----------------------------------- #
    grid = fit_disparity_grid(seq["depth"])
    print("  視差の量子化の格子(同梱の深度の値の逆数から推定): 刻み %.5f /m、整列度 %.2f(1 = 完全に等間隔、%d 水準)。"
          "Z での段差 = 刻み × Z² = Z 1 m で %.2f mm、2 m で %.2f mm" % (grid["delta"], grid["alignment"], grid["n_levels"],
                                                                     1e3 * grid["delta"], 4e3 * grid["delta"]))
    q_rows = []
    for z0 in (0.66, 1.0, 1.4, 1.7, 2.86):
        meas = min(bins, key=lambda r: abs(r["z"] - z0))
        qs = quantization_only_sigma(grid, z0)
        q_rows.append({"z": z0, "q": qs, "meas": meas["sigma"], "meas_z": meas["z"]})
    print("  量子化だけ(雑音ゼロの傾いた平面)の窓残差 / 実測の中央値 [mm]:")
    for r in q_rows:
        print("    Z %.2f m: 量子化だけ %.2f / 実測(Z≈%.2f)%.2f = %.0f %%" % (r["z"], 1e3 * r["q"], r["meas_z"],
                                                                      1e3 * r["meas"], 100 * r["q"] / r["meas"]))
    q_slope = float(np.polyfit(np.log([r["z"] for r in q_rows]), np.log([r["q"] for r in q_rows]), 1)[0])
    far_share = min(r["q"] / r["meas"] for r in q_rows if r["z"] >= 1.4)
    print("  量子化だけの窓残差の対数の傾き %.2f(Z² なら 2)。1.4 m 以遠は実測の %.0f %% 以上を量子化だけで説明する"
          "(1.4 m より近い側は実測が量子化の 2 倍前後 = センサの雑音・面の凹凸・窓の広さが残る)。" % (q_slope, 100 * far_share))
    g.check("視差の量子化だけで窓残差が Z² に近く増える(傾き 1.5 以上)", q_slope >= 1.5, "傾き %.2f" % q_slope)
    g.check("1.4 m 以遠は量子化だけで実測の半分以上", far_share >= 0.5, "最小 %.0f %%" % (100 * far_share))
    win = {}
    for tile in (12, 24, 48):
        recs = []
        for i, d in enumerate(seq["depth"]):
            recs += [(*r[:4], i) for r in tile_residuals(d, tile=tile)]
        wb = bin_medians(recs)
        w1 = [r for r in wb if r["lo"] == 0.9][0]
        win[tile] = {"sigma_1m": w1["sigma"], "slope_le2": loglog_slope([r for r in wb if r["hi"] <= 2.0]), "n": len(recs)}
    print("  窓の大きさを替える(センサの雑音だけなら窓によらず一定のはず): Z 0.9〜1.1 m の中央値 %s mm、2 m 以下の傾き %s"
          % (" / ".join("%d 画素 %.2f" % (t, 1e3 * v["sigma_1m"]) for t, v in win.items()),
             " / ".join("%.2f" % v["slope_le2"] for v in win.values())))
    all_recs = [(*r[:4], i) for i, d in enumerate(seq["depth"]) for r in tile_residuals(d)]
    edge_sets = ((0.5, 0.8, 1.1, 1.4, 1.7, 2.0), (0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0), (0.5, 1.0, 1.5, 2.0))
    slopes = [v["slope_le2"] for v in win.values()] + [loglog_slope(bin_medians(all_recs, e)) for e in edge_sets]
    print("  2 m 以下の傾きは窓・区間の取り方で %.2f〜%.2f(本文の 1.07 は点推定として過精度)。"
          "Z² を支持しないが、反証でもない(量子化は Z² で、窓の広さ・面の凹凸と混ざる)。" % (min(slopes), max(slopes)))
    win_ratio = win[48]["sigma_1m"] / win[12]["sigma_1m"]
    g.check("窓の大きさで窓残差が変わる(48 画素 / 12 画素 が 1.5 倍以上)", win_ratio >= 1.5,
            "%.2f 倍(センサの雑音だけの量ではない)" % win_ratio)
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

    noise = {"bins": bins, "slope": slope, "slope_le2": slope_le2, "ratio": ratio, "ate": ate, "ate_ident": ate_ident,
             "q_rows": q_rows, "slope_lo": min(slopes), "slope_hi": max(slopes), "cv": cv, "half": half}
    record = {
        "n_frames": n, "n_pairs": npair, "chosen_trim": chosen,
        "rpe_t_mm": {"b_icp": round(1e3 * rpe_t_b, 2), "b_ident": round(1e3 * rpe_t_id_b, 2),
                     "all_icp": round(1e3 * rms_of(et), 2), "all_ident": round(1e3 * rms_of(it), 2),
                     "all_default": round(1e3 * default_t, 2)},
        "rpe_r_deg": {"b_icp": round(rpe_r_b, 3), "b_ident": round(rpe_r_id_b, 3)},
        "ate_mm": {"icp": round(1e3 * ate, 2), "default": round(1e3 * ate_default, 2), "ident": round(1e3 * ate_ident, 2)},
        "sigma_z_mm": [[r["z"], round(1e3 * r["sigma"], 3)] for r in bins], "slope": round(slope, 3),
        "slope_le2m": round(slope_le2, 3), "slope_range": [round(min(slopes), 2), round(max(slopes), 2)],
        "baseline": {"cv_mm": round(1e3 * cv_rms, 2), "icp_over_cv": round(icp_over_cv, 2), "ate_cv_mm": round(1e3 * ate_cv, 1),
                     "ate_mean_motion_mm": round(1e3 * ate_mean, 1)},
        "worst3": {"pairs": worst, "share": round(share3, 3), "rms_without_mm": round(1e3 * rms_wo3, 2),
                   "ci95": [round(ci_lo, 2), round(ci_hi, 2)]},
        "splits": [{"name": r["name"], "trim": r["trim"], "ratio": round(r["ratio"], 2)} for r in splits],
        "quantization": {"delta": round(grid["delta"], 5), "alignment": round(grid["alignment"], 2),
                         "slope": round(q_slope, 2), "far_share_min": round(far_share, 2)},
        "window": {str(t): round(1e3 * v["sigma_1m"], 2) for t, v in win.items()},
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
