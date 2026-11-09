# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""混載デパレタイズ: 継ぎ目が詰まると深度の段差では分けられない。V 字の溝とカラーの溝の勝ち負けは合わせ目の作りで入れ替わる。
(仮定: 段ボールの縁の丸み 4 mm。天面の外フラップの合わせ目の深さ・切り口のすき間・テープは作者の仮定で、地図にして振る)
同じ柄では、合わせ目の溝が深い(2 mm)ならカラーの溝、すき間 1.5 mm・テープ無し・溝 1 mm 以下なら深度の V 字が多く分ける。

大きさ・印字・テープ・ラベル・つぶれ・シュリンク包装の違う段ボールをパレット(JIS T11、1100 × 1100)に
2 段に混載し、天井の RGB-D カメラ(真下向き、床から 2.70 m、960 × 720)で撮る。Fullseye の op で
箱の天面(平面の分割・矩形の当てはめ・高さ)と吸着の位置を出し、6 軸アームが 1 個ずつ下ろす。

**比べるもの** —— 分割の手がかり 5 通り(測り方 = 平面と矩形の当てはめは共通)。どれも同じ作者が書いた
古典的なやり方で、学習型の分割や市販の製品とは比べていない:

* 深度の段差: 上を向いた面を深度の段差(5 × 5 の高低差 9 mm)で切る。
* 深度の V 字: 段差で切った面を、端から端まで通る深度の浅い V 字の溝(段ボールの角の丸みが作る)で割る。
* カラーだけ: カラーの境界(輝度の勾配 + 暗い細い溝)を watershed で切る(高さ・矩形は深度から読む)。
  自作の弱い基準線で、印字・テープ・ラベルで天面が割れる。
* カラーの溝: 段差で切った面を、カラーの暗い溝が線の 72 % 以上で続く線で割る。
* 両方(AND): カラーの溝**かつ**深度の V 字の溝がある線でだけ割る。

★切除の結果(基本の場面 = 合わせ目の溝 0.8〜2.0 mm・すき間なし・テープはクラフト 7 割と透明 3 割、種 10 本の中央値):
継ぎ目が詰まる・同じ柄では、深度の段差がいちばん少なく分ける。同じ柄では深度の V 字はカラーの溝より少なく分ける
(合わせ目でも割る)。継ぎ目が詰まるでは V 字とカラーの溝はほぼ同じだけ見つけ、カラーの溝のほうが割りすぎない。
両方(AND)はカラーの溝と同じか下。隙間ありでは段差だけで足り、V 字は割りすぎる。
★合わせ目の地図(継ぎ目が詰まる・同じ柄、種 3〜5): 溝の深さ 0.2〜2 mm × 切り口のすき間 0 / 0.5 / 1.5 mm ×
テープ(クラフト / 透明 / 無し)。同じ柄では、クラフトかテープ無しで溝が 1 mm 以下なら V 字はカラーの溝と同じか上、
溝が 2 mm になると V 字が崩れてカラーの溝が勝つ。すき間 1.5 mm・テープ無し・溝 1 mm 以下では、カラーの溝も
合わせ目の暗い線で割って崩れ、V 字が上(すき間 0.5 mm では同点)。透明テープは升目ごとにまちまち、継ぎ目が詰まるでは差が小さい(0.57〜0.82 で入れ替わる)。基本の場面が深い側に寄っていたことが、前の版の「カラーの溝が勝つ」の正体。
V 字の溝の深さは場面の作り(縁の丸み 4 mm)が決めるので、丸みの感度と閾値(VALLEY_MIN)の掃引も表で出す。
閾値 VALLEY_MIN・SEAM_BH・STEP_M は種 0〜2 の場面を見てから置き、種 3〜9 は見ていない。主張の門は結果を
見てから置いた(全部の種と見ていない種の両方で確かめる)。隙間ありの最低線(≥ 0.85)は段差と両方に元からあり、
カラーの溝は結果を見てから足した(CI の代用カラーでは 0.86 で、余裕は 0.01)。

**難しい順の 5 条件**(各 10 枚のパレット、最初のコマも 1 個ずつ下ろす繰り返しも 10 枚全部): 隙間あり(15〜30 mm)→
継ぎ目が詰まる(0〜2 mm)→ 同じ柄が隣り合う → シュリンク包装の反射 → つぶれ・傾き。

**真値は描いた場面そのもの**(箱の寸法・姿勢・つぶれ)= 自作の場面で、外の実データではない。採点は 2 段:
最初のコマで「空いている箱の天面」との照合(矩形の IoU ≥ 0.5、寸法つきは辺の誤差 ≤ 20 mm も)、
1 個ずつ下ろす繰り返しで結果を数える。**成否は物理の模擬ではなく規則で判定する**: 成功 / 姿勢がずれる
(中心 20 mm・向き 5° を超える)/ 二重取り(吸着パッド 160 × 80 mm の足跡が 2 箱に 15 % ずつ以上)/
取り落とし(足跡の 88 % 未満が箱の上・天面の平面当てはめの残差 6 mm 超・引きはがしのモーメント比 > 1)/
引っかけ(上に別の箱が載った箱を吸う)/ 可搬超過(箱 + 手先の道具 1.8 kg がアームの可搬 12.5 kg を超える
—— 11 kg の品種 D は 12.8 kg で超える)/ 見つからない(候補が無い・足跡の半分以上が箱の上に無い)。
失敗のたびに人が直したことにして先へ進む。

**描画**:

* 深度はいつも、この中の正確な幾何(点の z-buffer)から作り、縞・パターン投影の深度センサの物理を
  足す: 投光器の影(基線 0.30 m)、光沢(シュリンクフィルム・透明テープ)の飽和と抜け、多重反射の
  奥にずれた偽の点、暗い印刷の抜け、斜面の抜け、段差の混合画素と飛び点、縞の位相の残りのうねり、
  距離の 2 乗で増える相関つきの雑音。抜けは相関した塊で作る(1 画素ずつの塩粒にしない)。
* カラーは 2 通り。**代表の数字と図は Blender(Cycles、物理ベース)で描いたカラー**に撮像素子の雑音を
  足したもの。描画は repo の外(``FULLSEYE_DEPAL_RENDERS``)に置き、``tools/depal_blender_run.py`` で
  作り直せる。無い環境(CI)では、同じ反射率の画像を数値で陰影づけした代用のカラーで回す。
  ★代用のカラーでは境界がくっきりして、カラーを使うやり方の順位が Blender と入れ替わる。そこで CI の
  門は、カラーを読まない主張(深度の V 字 > 深度の段差、種 0 の 1 枚)と、隙間ありの最低線(深度の段差・
  カラーの溝・両方 ≥ 0.85。カラーの溝と両方は代用カラーで測る)だけにしてある。カラーを使うやり方の比べ合い
  と合わせ目の地図は CI では確かめていない(全部を回す実行でだけ門にする)。
* Blender の深度と幾何の深度の照合は、同じ幾何を書き出して描いたもの —— カメラの合わせの検算でしかない。

**実データの章**(BOP の HOPE があるとき): 能動ステレオ式の深度カメラの実深度で、同じ op の組
(depth_to_organized_points・bilateral_filter_depth・normals_from_depth・watersheds_marker・ransac_plane・
fit_rectangle2。切り分けの手順と閾値は別実装)が箱型の物体の面の寸法をどこまで出すかを、BOP の真の姿勢と
寸法で採点する。対象は卓上の玩具の食品箱を斜め 0.5〜1 m から撮ったもので、天井 2.7 m の段ボールではない。
継ぎ目で割るやり方は HOPE では一度も割らなかったので外した —— この章は「実深度で平面 → 矩形の寸法が
この程度」だけを支え、見出しの主張は支えない。同梱の dataset_info.md は CC BY-NC-SA 4.0、BOP の配布
ページは CC BY-SA 4.0 と食い違うので、厳しい方に倒して**数値だけ**を載せ、画像は図に出さない
(文言は ``HOPE_LICENSE_BUNDLED`` / ``HOPE_LICENSE_BOP`` に逐語で、出典は ``HOPE_CREDIT``)。

実行例::

    py -3.11 examples/poc_mixed_case_depalletizing.py                   # CI と同じ縮小版(種 0 の 1 枚、2 手まで)
    set FULLSEYE_DEPAL_FULL=1 & py -3.11 examples/poc_mixed_case_depalletizing.py   # 全部(10 枚 × 5 条件、掃引、実データ)

図(``FULLSEYE_FIGURE_DIR`` があり、全部を回したときだけ): 代表図(同じ柄のパレットを 5 通りで)、
難しさの梯子、最初のコマの再現率の表、結果の数の表、成功率のグラフ、閾値と縁の丸みの掃引の表、
動画(条件ごとに「カラーの溝」の成功の手と失敗の手)、失敗の見本、実データの数表。
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import depth_bilateral  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import geometry2d  # noqa: E402
import image_gen  # noqa: E402
import measure  # noqa: E402
import range_image  # noqa: E402
import ransac_fit  # noqa: E402
import realdata  # noqa: E402
import segmentation  # noqa: E402


# ================================================================================================
# 混載デパレタイズの場面: 段ボールの寸法・印字・置き方と、天井カメラの幾何(真値の側)。
#
# Mixed-case depalletizing scene: carton catalogue, print textures, pallet layouts for five
# conditions of increasing difficulty, and the overhead camera geometry. Everything here is the
# **ground truth** side —— the perception code in ``poc_mixed_case_depalletizing`` never reads it.
#
# 座標は世界 = 床が z = 0、パレットの中心が原点、x 右・y 奥・z 上 [m]。
# 天井のカメラは真下を向き、画像の右 = +x、画像の下 = −y。
#
# ================================================================================================

#: パレット(JIS T11 の平パレット 1100 × 1100、高さ 144 mm)。
PALLET_SIZE = 1.10
PALLET_TOP = 0.144

#: 天井のカメラ: 床から 2.70 m、真下向き。960 × 720、焦点距離 1250 px(上段の箱の天面で約 1.7 mm/px、
#: パレットの上段の外周まで視野に入る)。
IMG_W, IMG_H = 960, 720
FX = FY = 1250.0
CX, CY = (IMG_W - 1) / 2.0, (IMG_H - 1) / 2.0
CAM_Z = 2.70
#: 投光器(縞・パターン投影)はカメラから +x に 0.30 m(基線)。影=投光の届かない所が欠測になる。
PROJ_BASELINE = 0.30

#: 段ボールの角の丸み [m](段ボールの折り目は角が丸く、詰めて並べても継ぎ目に V 字の溝ができる)。
EDGE_RADIUS = 0.004

#: 箱の品種(長さ・幅・高さ [m]、1 箱の質量 [kg])。実在の規格箱の代表的な寸法帯から選んだ架空の品種。
CATALOGUE = {
    "A": (0.44, 0.30, 0.25, 9.0),
    "B": (0.36, 0.26, 0.20, 5.5),
    "C": (0.30, 0.22, 0.18, 3.5),
    "D": (0.50, 0.32, 0.25, 11.0),
    "E": (0.40, 0.36, 0.30, 7.5),
    "F": (0.34, 0.24, 0.25, 6.0),
    "G": (0.26, 0.20, 0.15, 2.5),
    "H": (0.46, 0.34, 0.20, 8.0),
}
BOTTOM_SKUS = ("A", "D", "F")           # 下段は高さ 0.25 m で揃う(上段の台になる)
TOP_SKUS = ("B", "C", "E", "G", "H", "A")

#: 難しい順の 5 条件。
CONDITIONS = ("gap", "tight", "same", "shrink", "crush")
CONDITION_JA = {
    "gap": "隙間あり",
    "tight": "継ぎ目が詰まる",
    "same": "同じ柄が隣り合う",
    "shrink": "シュリンク包装の反射",
    "crush": "つぶれ・傾き",
}


@dataclass
class Box:
    """1 個の段ボール(真値)。姿勢は「底面の中心 + ヨー + 傾き」。"""

    id: int
    sku: str
    L: float
    W: float
    H: float
    mass: float
    x: float
    y: float
    z0: float                   # 底面の高さ [m]
    yaw: float                  # z 軸まわり [rad]
    tilt_axis: float = 0.0      # 傾けたときの回転軸の向き(箱の局所 x から)[rad]
    tilt: float = 0.0           # 傾き [rad](底面の 1 辺を支点に持ち上げた形)
    sag: float = 0.0            # 天面のつぶれ(中央の沈み)[m]
    shrink: bool = False        # シュリンクフィルムで包んである
    tape: str = "kraft"         # "kraft" / "clear"
    label: bool = False         # 送り状ラベル
    print_seed: int = 0         # 印字の柄(同じ品種・同じ seed = 同じ柄)
    layer: int = 0
    edge_r: float = EDGE_RADIUS  # 天面の縁の丸み [m](継ぎ目の V 字の溝の深さを決める)
    flap_dip: float = 0.0       # 天面の中央、外フラップの合わせ目の溝の深さ [m](テープの下で浅く残る)
    flap_gap: float = 0.0       # 外フラップの切り口のすき間 [m](クラフトテープは覆う。透明テープ・テープ無しは開く)

    def rotation(self) -> np.ndarray:
        """局所 → 世界の回転(ヨーの後に傾き)。"""
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        if self.tilt == 0.0:
            return Rz
        a = np.array([math.cos(self.tilt_axis), math.sin(self.tilt_axis), 0.0])
        K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        Rt = np.eye(3) + math.sin(self.tilt) * K + (1 - math.cos(self.tilt)) * (K @ K)
        return Rz @ Rt

    def pivot_local(self) -> np.ndarray:
        """傾けるときの支点(局所座標、底面上の辺の中点)。傾いていなければ原点。"""
        if self.tilt == 0.0:
            return np.zeros(3)
        # 支点の辺は回転軸に平行で、持ち上がる側の反対側にある
        n = np.array([-math.sin(self.tilt_axis), math.cos(self.tilt_axis), 0.0])
        # 箱の半幅を n 方向へ射影した長さ(軸が局所 x/y に平行な場合だけ使う)
        half = abs(n[0]) * self.L / 2 + abs(n[1]) * self.W / 2
        return -n * half

    def to_world(self, p_local: np.ndarray) -> np.ndarray:
        """局所(底面中心が原点、z 上)→ 世界。"""
        R = self.rotation()
        piv = self.pivot_local()
        c, s = math.cos(self.yaw), math.sin(self.yaw)
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        base = np.array([self.x, self.y, self.z0])
        # 支点を固定して回す: p_w = base + Rz piv + R (p - piv)
        return base + (Rz @ piv) + (np.asarray(p_local) - piv) @ R.T

    def top_center_world(self) -> np.ndarray:
        """天面の中心(つぶれの前の平らな天面)の世界座標。"""
        return self.to_world(np.array([0.0, 0.0, self.H]))

    def top_normal_world(self) -> np.ndarray:
        return self.rotation() @ np.array([0.0, 0.0, 1.0])

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scene:
    condition: str
    seed: int
    boxes: list = field(default_factory=list)
    variant: str = ""            # 合わせ目の地図の場面の名前(描画の置き場を分ける)。通常の場面は空

    def to_dict(self) -> dict:
        return {"condition": self.condition, "seed": self.seed, "variant": self.variant,
                "boxes": [b.to_dict() for b in self.boxes]}


def _pack_layer(rng, skus, region, gap_fn, z0, start_id, layer, same_rows, fill=1.0):
    """長方形の領域に箱を行ごとに詰める(行の奥行きは行の最初の箱の幅)。"""
    x_lo, x_hi, y_lo, y_hi = region
    boxes = []
    y = y_lo
    bid = start_id
    while True:
        sku_row = rng.choice(skus)
        L, W, H, m = CATALOGUE[sku_row]
        if y + W > y_hi + 1e-9:
            break
        x = x_lo
        row = []
        row_print = int(rng.integers(0, 10_000))
        while True:
            sku = sku_row if same_rows else rng.choice([s for s in skus if CATALOGUE[s][1] <= W + 1e-9])
            L2, W2, H2, m2 = CATALOGUE[sku]
            if x + L2 > x_hi + 1e-9:
                break
            pseed = row_print if same_rows else int(rng.integers(0, 10_000))
            row.append(Box(id=bid, sku=sku, L=L2, W=W2, H=H2, mass=m2,
                           x=x + L2 / 2, y=y + W2 / 2, z0=z0, yaw=0.0, print_seed=pseed, layer=layer,
                           tape="clear" if rng.random() < 0.3 else "kraft",
                           label=bool(rng.random() < 0.45)))
            bid += 1
            x += L2 + gap_fn()
        boxes.extend(row)
        y += W + gap_fn()
        if fill < 1.0 and y > y_lo + fill * (y_hi - y_lo):
            break
    # 行の右端の余りを詰め直す: 各行を領域の中で中央に寄せる
    return boxes, bid


def _center_rows(boxes, x_lo, x_hi):
    rows = {}
    for b in boxes:
        rows.setdefault(round(b.y - b.W / 2, 4), []).append(b)
    for row in rows.values():
        lo = min(b.x - b.L / 2 for b in row)
        hi = max(b.x + b.L / 2 for b in row)
        shift = (x_lo + x_hi) / 2 - (lo + hi) / 2
        for b in row:
            b.x += shift


def make_scene(condition: str, seed: int, edge_r: float = EDGE_RADIUS, flap: bool = True,
               bulge: bool = True, flap_map: tuple | None = None) -> Scene:
    """``flap_map`` = (合わせ目の溝の深さ [m], すき間 [m], テープ "kraft"/"clear"/"none") で全部の箱をそろえる(地図の場面)。"""
    """条件と seed から 1 枚のパレットを作る(決定的)。"""
    if condition not in CONDITIONS:
        raise ValueError("unknown condition: %r" % (condition,))
    rng = np.random.default_rng(1000 * (CONDITIONS.index(condition) + 1) + seed)
    if condition == "gap":
        gap_fn = lambda: float(rng.uniform(0.015, 0.030))      # noqa: E731
    else:
        gap_fn = lambda: float(rng.uniform(0.0, 0.002))        # noqa: E731
    same = condition == "same"
    half = PALLET_SIZE / 2
    bottom, nid = _pack_layer(rng, BOTTOM_SKUS, (-half, half, -half, half), gap_fn,
                              PALLET_TOP, 0, 0, same)
    _center_rows(bottom, -half, half)
    # 下段の外形を中央に寄せる(y)
    ylo = min(b.y - b.W / 2 for b in bottom)
    yhi = max(b.y + b.W / 2 for b in bottom)
    for b in bottom:
        b.y += -(ylo + yhi) / 2
    top_z = PALLET_TOP + 0.25
    inner = half - 0.02
    top, nid = _pack_layer(rng, TOP_SKUS, (-inner, inner, -inner, inner), gap_fn,
                           top_z, nid, 1, same)
    _center_rows(top, -inner, inner)
    ylo = min(b.y - b.W / 2 for b in top)
    yhi = max(b.y + b.W / 2 for b in top)
    for b in top:
        b.y += -(ylo + yhi) / 2
    # 上段の積み方が下段の外へはみ出さないように(はみ出す行は落とす)
    top = [b for b in top if abs(b.y) + b.W / 2 <= half and abs(b.x) + b.L / 2 <= half]
    boxes = bottom + top
    # 小さな置きずれ(ヨー ±1.5°、位置 ±3 mm)を足す。隙間が無い条件では重ならない範囲だけ
    for b in boxes:
        if condition == "gap":
            b.yaw = float(rng.normal(0.0, math.radians(1.5)))
            b.x += float(rng.normal(0, 0.003))
            b.y += float(rng.normal(0, 0.003))
        else:
            b.yaw = float(rng.normal(0.0, math.radians(0.15)))
    if condition == "shrink":
        for b in boxes:
            b.shrink = bool(rng.random() < 0.45)
    if condition == "crush":
        for b in boxes:
            if rng.random() < 0.35:
                b.sag = float(rng.uniform(0.010, 0.028))
        tops = [b for b in boxes if b.layer == 1]
        for b in rng.choice(tops, size=max(1, len(tops) // 4), replace=False):
            b.tilt = math.radians(float(rng.uniform(4.0, 8.0)))
            b.tilt_axis = float(rng.choice([0.0, math.pi / 2, math.pi, -math.pi / 2]))
    for i, b in enumerate(boxes):
        b.id = i
        b.edge_r = float(edge_r)
    # 実物の A 式段ボールの天面: 外フラップの合わせ目の溝(テープの下で 0.8〜2.0 mm 残る)と、
    # 中身の多い箱の天面のふくらみ(4 割の箱で 3〜8 mm)。並べ方とは別の乱数で足す(並べ方を変えない)。
    rng2 = np.random.default_rng(777000 + 1000 * (CONDITIONS.index(condition) + 1) + seed)
    for b in boxes:
        b.flap_dip = float(rng2.uniform(0.0008, 0.0020)) if flap else 0.0
        if bulge and b.sag == 0.0 and rng2.random() < 0.4:
            b.sag = -float(rng2.uniform(0.003, 0.008))
    variant = ""
    if flap_map is not None:
        dip, gap, tape = flap_map
        for b in boxes:
            b.flap_dip, b.flap_gap, b.tape = float(dip), float(gap), str(tape)
        variant = "_map_d%03d_g%02d_%s" % (round(dip * 1e4), round(gap * 1e4), tape)
    return Scene(condition=condition, seed=seed, boxes=boxes, variant=variant)


# ---------------------------------------------------------------- 面の標本化(深度・色の共通の幾何)

def _rounded_drop(d: np.ndarray, r: float = EDGE_RADIUS) -> tuple[np.ndarray, np.ndarray]:
    """縁からの距離 d [m] → 天面の沈み [m] と、縁の方向への傾き(sinθ)。四分円の丸み。"""
    dd = np.clip(r - d, 0.0, r)
    drop = r - np.sqrt(np.maximum(r * r - dd * dd, 0.0))
    slope = dd / r
    return drop, slope


def wrinkle_field(s, t, seed, amp=0.0018):
    """シュリンクフィルムのしわ: 縁ほど強い、数 cm の周期の凹凸 [m]。"""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(s)
    for _ in range(6):
        k = rng.uniform(25, 90)
        th = rng.uniform(0, math.pi)
        ph = rng.uniform(0, 2 * math.pi)
        out += np.sin(k * (math.cos(th) * s + math.sin(th) * t) + ph)
    return amp * out / 6.0


def sample_top(box: Box, spacing: float):
    """天面を格子で標本化 → (世界の点 (N,3)、世界の法線 (N,3)、天面の局所 (s,t))。"""
    ns = max(2, int(math.ceil(box.L / spacing)) + 1)
    nt = max(2, int(math.ceil(box.W / spacing)) + 1)
    s = np.linspace(-box.L / 2, box.L / 2, ns)
    t = np.linspace(-box.W / 2, box.W / 2, nt)
    if box.flap_gap > 0:
        # すき間のある箱だけ、合わせ目のまわり(±8 mm)を 0.25 mm 刻みで標本化する(0.5 mm のすき間を取りこぼさない。
        # すき間の無い通常の場面の標本化は変えない = 描画済みのコマと同じ幾何)
        fine = np.arange(-0.008, 0.008 + 1e-9, 0.00025)
        g = box.flap_gap / 2
        t = np.unique(np.concatenate([t, fine, [-g - 1e-5, -g + 1e-5, g - 1e-5, g + 1e-5]]))
    S, T = np.meshgrid(s, t)
    S = S.ravel()
    T = T.ravel()
    z = np.full_like(S, box.H)
    nx = np.zeros_like(S)
    ny = np.zeros_like(S)
    # つぶれ(sag > 0): 中央が沈む cos 型のくぼみ。ふくらみ(sag < 0): 中身が多く天面が持ち上がる
    if box.sag != 0:
        u = S / (box.L / 2)
        v = T / (box.W / 2)
        prof = np.cos(np.clip(u, -1, 1) * math.pi / 2) ** 2 * np.cos(np.clip(v, -1, 1) * math.pi / 2) ** 2
        z = z - box.sag * prof
        du = -box.sag * 2 * np.cos(u * math.pi / 2) * (-np.sin(u * math.pi / 2)) * (math.pi / 2) / (box.L / 2) \
            * np.cos(v * math.pi / 2) ** 2
        dv = -box.sag * 2 * np.cos(v * math.pi / 2) * (-np.sin(v * math.pi / 2)) * (math.pi / 2) / (box.W / 2) \
            * np.cos(u * math.pi / 2) ** 2
        nx -= du
        ny -= dv
    # 外フラップの合わせ目: 天面の中央を長辺方向に走る浅い溝(幅 ~6 mm、テープが上を渡る)
    if box.flap_dip > 0:
        wf = 0.003
        g = np.exp(-(T / wf) ** 2)
        z = z - box.flap_dip * g
        ny -= box.flap_dip * g * 2 * T / wf ** 2
    # 切り口のすき間: クラフトテープは上を覆う(深度もカラーも見えない)。透明テープ・テープ無しは、すき間の底
    # (内フラップの上、板厚 4 mm 下)が見える(透明テープは深度にもカラーにも素通しと仮定)
    if box.flap_gap > 0 and box.tape != "kraft":
        z = np.where(np.abs(T) < box.flap_gap / 2, z - 0.004, z)
    # 縁の丸み
    dx = box.L / 2 - np.abs(S)
    dy = box.W / 2 - np.abs(T)
    drop_x, sl_x = _rounded_drop(dx, box.edge_r)
    drop_y, sl_y = _rounded_drop(dy, box.edge_r)
    z = z - np.maximum(drop_x, drop_y)
    nx += np.sign(S) * sl_x * 1.2
    ny += np.sign(T) * sl_y * 1.2
    if box.shrink:
        w = wrinkle_field(S, T, box.id * 7 + 3)
        edge_w = 0.35 + 0.65 * np.exp(-np.minimum(dx, dy) / 0.04)
        z = z + 0.0015 + w * edge_w
        eps = 1e-3
        gx = (wrinkle_field(S + eps, T, box.id * 7 + 3) - wrinkle_field(S - eps, T, box.id * 7 + 3)) / (2 * eps)
        gy = (wrinkle_field(S, T + eps, box.id * 7 + 3) - wrinkle_field(S, T - eps, box.id * 7 + 3)) / (2 * eps)
        nx -= gx * edge_w
        ny -= gy * edge_w
    nloc = np.stack([nx, ny, np.ones_like(S)], 1)
    nloc /= np.linalg.norm(nloc, axis=1, keepdims=True)
    pl = np.stack([S, T, z], 1)
    pw = box.to_world(pl)
    nw = nloc @ box.rotation().T
    return pw, nw, np.stack([S, T], 1)


def sample_sides(box: Box, spacing: float):
    """4 つの側面 → (点、法線、面番号 1..4、局所 (u: 横, h: 高さ))。"""
    pts, nrm, fid, uv = [], [], [], []
    nh = max(2, int(math.ceil(box.H / spacing)) + 1)
    h = np.linspace(0.0, box.H - box.edge_r, nh)
    for k, (axis, sign) in enumerate([(0, 1), (0, -1), (1, 1), (1, -1)]):
        length = box.W if axis == 0 else box.L
        nu = max(2, int(math.ceil(length / spacing)) + 1)
        u = np.linspace(-length / 2, length / 2, nu)
        U, Hh = np.meshgrid(u, h)
        U = U.ravel()
        Hh = Hh.ravel()
        if axis == 0:
            p = np.stack([np.full_like(U, sign * box.L / 2), U, Hh], 1)
            n = np.tile([sign, 0.0, 0.0], (len(U), 1))
        else:
            p = np.stack([U, np.full_like(U, sign * box.W / 2), Hh], 1)
            n = np.tile([0.0, sign, 0.0], (len(U), 1))
        if box.shrink:
            p = p + n * 0.0015
        pts.append(box.to_world(p))
        nrm.append(n @ box.rotation().T)
        fid.append(np.full(len(U), k + 1))
        uv.append(np.stack([U, Hh], 1))
    return np.concatenate(pts), np.concatenate(nrm), np.concatenate(fid), np.concatenate(uv)


def world_to_cam(p: np.ndarray, cam_x: float = 0.0, cam_y: float = 0.0, cam_z: float = CAM_Z):
    """世界の点 → カメラ座標 (x 右, y 下, z 奥)。真下向きのカメラ。"""
    xc = p[:, 0] - cam_x
    yc = -(p[:, 1] - cam_y)
    zc = cam_z - p[:, 2]
    return np.stack([xc, yc, zc], 1)


def project(p: np.ndarray, cam_x: float = 0.0):
    c = world_to_cam(p, cam_x=cam_x)
    u = FX * c[:, 0] / c[:, 2] + CX
    v = FY * c[:, 1] / c[:, 2] + CY
    return u, v, c[:, 2]


def top_surface_height(box: Box, xy: np.ndarray):
    """世界の xy 点で、この箱の天面がどの高さにあるか(天面の外なら NaN)。傾き・つぶれ込み。"""
    R = box.rotation()
    piv = box.pivot_local()
    c, s = math.cos(box.yaw), math.sin(box.yaw)
    Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    base = np.array([box.x, box.y, box.z0]) + Rz @ piv
    # 天面の平面: 世界の点 p = base + R (q - piv), q = (S, T, H)。(S, T) を xy から逆算(1 回の線形近似で十分)
    A = R[:2, :2]
    rhs = xy - base[:2] - (R @ (np.array([0.0, 0.0, box.H]) - piv))[:2] + (A @ np.zeros(2))
    st = np.linalg.solve(A, rhs.T).T
    S, T = st[:, 0], st[:, 1]
    inside = (np.abs(S) <= box.L / 2) & (np.abs(T) <= box.W / 2)
    z = np.full(len(S), box.H)
    if box.sag != 0:
        u = S / (box.L / 2)
        v = T / (box.W / 2)
        z = z - box.sag * np.cos(np.clip(u, -1, 1) * math.pi / 2) ** 2 * np.cos(np.clip(v, -1, 1) * math.pi / 2) ** 2
    q = np.stack([S, T, z], 1)
    pw = base + (q - piv) @ R.T
    out = np.where(inside, pw[:, 2], np.nan)
    return out, S, T


def footprint_corners(box: Box) -> np.ndarray:
    """天面の 4 隅(世界、xy)。"""
    c = np.array([[box.L / 2, box.W / 2, box.H], [-box.L / 2, box.W / 2, box.H],
                  [-box.L / 2, -box.W / 2, box.H], [box.L / 2, -box.W / 2, box.H]])
    return box.to_world(c)


# ================================================================================================
# 段ボールの天面・側面の地色と印字(反射率の画像)。数値の描画と Blender の描画が同じ画像を使う。
#
# Carton albedo textures (kraft fibre noise, printed handling marks, item codes, tape, shipping
# label with a barcode). Both the numpy renderer and the Blender renderer read the same arrays,
# so the two renderings differ only in light transport.
# 社名・商品名は出さない(取扱表示と架空の品番だけ)。
#
# ================================================================================================

#: テクスチャの解像度 [px/m](2 px/mm)。
TEX_PPM = 2000

_KRAFT = [(0.60, 0.45, 0.31), (0.66, 0.50, 0.35), (0.55, 0.41, 0.29), (0.82, 0.80, 0.74)]
_INK = [(0.10, 0.18, 0.42), (0.08, 0.32, 0.20), (0.55, 0.10, 0.10), (0.08, 0.08, 0.08)]
_WORDS = ["天地無用", "取扱注意", "ワレモノ注意", "水濡れ注意", "上積み厳禁", "精密機器"]


def _font(size: int):
    for p in (r"C:\Windows\Fonts\YuGothB.ttc", r"C:\Windows\Fonts\meiryob.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
              "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fibre_noise(h, w, rng):
    """段ボールの繊維の濃淡(低周波のむら + 細かい粒)。"""
    lo = rng.normal(0, 1, (max(2, h // 40), max(2, w // 40)))
    lo = np.asarray(Image.fromarray(lo.astype(np.float32)).resize((w, h), Image.BICUBIC))
    hi = rng.normal(0, 1, (h, w))
    return 0.035 * lo + 0.02 * hi


def _arrow_marks(draw, x, y, s, ink):
    """取扱表示の「上向き矢印 2 本」(JIS Z 0150 の図記号に似せた形)。"""
    for dx in (0, int(0.55 * s)):
        cx = x + dx
        draw.polygon([(cx + s * 0.25, y), (cx + s * 0.5, y + s * 0.35), (cx + s * 0.32, y + s * 0.35),
                      (cx + s * 0.32, y + s), (cx + s * 0.18, y + s), (cx + s * 0.18, y + s * 0.35),
                      (cx, y + s * 0.35)], fill=ink)
    draw.line([(x - s * 0.05, y + s * 1.08), (x + s * 1.1, y + s * 1.08)], fill=ink, width=max(2, int(s * 0.06)))


def _umbrella(draw, x, y, s, ink):
    draw.pieslice([x, y, x + s, y + s * 0.8], 180, 360, fill=ink)
    draw.line([(x + s / 2, y + s * 0.4), (x + s / 2, y + s * 0.95)], fill=ink, width=max(2, int(s * 0.07)))
    draw.arc([x + s * 0.3, y + s * 0.8, x + s / 2, y + s * 1.05], 0, 180, fill=ink, width=max(2, int(s * 0.07)))


def print_layer(L, W, sku, seed):
    """印字だけの画像(RGBA、透明が地)。同じ (sku, seed) なら同じ柄。"""
    rng = np.random.default_rng(seed * 31 + ord(sku))
    w, h = int(round(L * TEX_PPM)), int(round(W * TEX_PPM))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    ink = tuple(int(255 * c) for c in _INK[int(rng.integers(len(_INK)))]) + (235,)
    # 品番(大きな文字)
    code = "%s-%04d" % (sku, int(rng.integers(1000, 9999)))
    f_big = _font(int(h * 0.16))
    tx = int(w * rng.uniform(0.06, 0.18))
    ty = int(h * rng.uniform(0.08, 0.20))
    dr.text((tx, ty), code, font=f_big, fill=ink)
    # 取扱表示の語
    word = _WORDS[int(rng.integers(len(_WORDS)))]
    f_mid = _font(int(h * 0.09))
    dr.text((int(w * 0.55), int(h * 0.70)), word, font=f_mid, fill=ink)
    # 入数
    dr.text((tx, int(h * 0.72)), "入数 %d" % int(rng.choice([6, 12, 20, 24])), font=f_mid, fill=ink)
    # 図記号
    s = int(h * 0.20)
    _arrow_marks(dr, int(w * 0.70), int(h * 0.10), s, ink)
    if rng.random() < 0.6:
        _umbrella(dr, int(w * 0.70) - int(s * 1.3), int(h * 0.12), int(s * 0.9), ink)
    # 枠線(印刷の囲み罫)を半分の箱に
    if rng.random() < 0.5:
        m = int(0.03 * TEX_PPM)
        dr.rectangle([m, m, w - m, h - m], outline=ink, width=max(3, int(0.004 * TEX_PPM)))
    return im


def tape_mask(L, W, width=0.050):
    """天面の中央を長辺方向に走るテープ(フラップの合わせ目を覆う)の範囲(bool 画像)。"""
    w, h = int(round(L * TEX_PPM)), int(round(W * TEX_PPM))
    yy = np.arange(h)[:, None] / TEX_PPM - W / 2
    return np.broadcast_to(np.abs(yy) <= width / 2, (h, w)).copy()


def _barcode(dr, x, y, w, h, rng):
    xx = x
    while xx < x + w:
        bw = int(rng.choice([2, 2, 4, 6]))
        if rng.random() < 0.55:
            dr.rectangle([xx, y, xx + bw - 1, y + h], fill=(15, 15, 15, 255))
        xx += bw


def label_layer(L, W, seed):
    """送り状ラベル(白い紙 + バーコード + 数字)。置き場所は seed で決まる。"""
    rng = np.random.default_rng(seed + 77)
    w, h = int(round(L * TEX_PPM)), int(round(W * TEX_PPM))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    lw, lh = int(0.10 * TEX_PPM), int(0.07 * TEX_PPM)
    side = rng.integers(2)
    x0 = int(w * (0.08 if side == 0 else 0.62))
    y0 = int(h * rng.uniform(0.62, 0.70)) if rng.random() < 0.5 else int(h * rng.uniform(0.06, 0.12))
    dr.rectangle([x0, y0, x0 + lw, y0 + lh], fill=(242, 242, 236, 255))
    _barcode(dr, x0 + 12, y0 + 14, lw - 24, int(lh * 0.45), rng)
    f = _font(int(lh * 0.18))
    dr.text((x0 + 12, y0 + int(lh * 0.66)), "%012d" % int(rng.integers(10**11, 10**12 - 1)), font=f,
            fill=(20, 20, 20, 255))
    return im


def top_texture(box) -> tuple[np.ndarray, np.ndarray]:
    """天面の反射率 (h, w, 3) と「光沢の強さ」(h, w)。行 0 が局所 t = −W/2、列 0 が s = −L/2。"""
    rng = np.random.default_rng(box.print_seed * 13 + ord(box.sku))
    base = np.array(_KRAFT[int(rng.integers(len(_KRAFT)))])
    w, h = int(round(box.L * TEX_PPM)), int(round(box.W * TEX_PPM))
    noise_rng = np.random.default_rng(box.id * 101 + 5)
    alb = base[None, None, :] * (1.0 + _fibre_noise(h, w, noise_rng))[..., None]
    gloss = np.zeros((h, w))
    pr = np.asarray(print_layer(box.L, box.W, box.sku, box.print_seed), np.float64) / 255.0
    a = pr[..., 3:4]
    alb = alb * (1 - a) + pr[..., :3] * a
    tm = tape_mask(box.L, box.W)
    if box.tape == "none":
        pass                                            # テープ無し(合わせ目がそのまま見える)
    elif box.tape == "kraft":
        tape_col = np.array([0.50, 0.36, 0.22])
        alb[tm] = tape_col * (1.0 + 0.02 * noise_rng.normal(0, 1, (int(tm.sum()), 1)))
        gloss[tm] = 0.25
    else:
        alb[tm] = alb[tm] * 0.93 + 0.03
        gloss[tm] = 0.9
    if box.label:
        lb = np.asarray(label_layer(box.L, box.W, box.id), np.float64) / 255.0
        a = lb[..., 3:4]
        alb = alb * (1 - a) + lb[..., :3] * a
        gloss = np.maximum(gloss, 0.15 * a[..., 0])
    if box.shrink:
        gloss = np.maximum(gloss, 1.0)
        alb = alb * 0.92 + 0.02
    # 行 0 を局所 t = −W/2 に合わせる(印字は +t 側が上なので上下を反転して持つ)
    return np.clip(alb, 0, 1)[::-1].copy(), gloss[::-1].copy()


def side_texture(box, face: int) -> np.ndarray:
    """側面の反射率 (h, w, 3)。行 0 が高さ 0(底)、列 0 が u = −長さ/2。"""
    rng = np.random.default_rng(box.print_seed * 13 + ord(box.sku))
    base = np.array(_KRAFT[int(rng.integers(len(_KRAFT)))])
    length = box.W if face in (1, 2) else box.L
    w, h = int(round(length * TEX_PPM / 2)), int(round(box.H * TEX_PPM / 2))
    noise_rng = np.random.default_rng(box.id * 101 + face)
    alb = base[None, None, :] * (1.0 + _fibre_noise(h, w, noise_rng))[..., None]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    ink = tuple(int(255 * c) for c in _INK[int(rng.integers(len(_INK)))]) + (230,)
    f = _font(max(8, int(h * 0.22)))
    dr.text((int(w * 0.1), int(h * 0.35)), "%s 品番" % box.sku, font=f, fill=ink)
    pr = np.asarray(im, np.float64)[::-1] / 255.0          # 行 0 = 底
    a = pr[..., 3:4]
    alb = alb * (1 - a) + pr[..., :3] * a
    if box.shrink:
        alb = alb * 0.92 + 0.02
    return np.clip(alb, 0, 1)


def lookup(tex: np.ndarray, s: np.ndarray, t: np.ndarray, L: float, W: float, ppm: float = TEX_PPM):
    """局所 (s, t) [m] → テクスチャの値(最近傍)。"""
    h, w = tex.shape[:2]
    col = np.clip(((s + L / 2) * ppm).astype(np.int64), 0, w - 1)
    row = np.clip(((t + W / 2) * ppm).astype(np.int64), 0, h - 1)
    return tex[row, col]


# ================================================================================================
# 数値の描画(CI 用)と、深度センサの物理(投光の影・光沢の穴・多重反射・混合画素・雑音)。
#
# Point-splat z-buffer renderer for the overhead RGB-D camera, plus the depth-sensor model of a
# structured-light (pattern-projection) camera. The Blender (Cycles) path replaces only the
# colour image; the depth always comes from the exact geometry here so both paths share one
# geometry truth.
#
# ================================================================================================

H, W = IMG_H, IMG_W


class Buffers:
    """z-buffer と画素ごとの属性(真値の側)。"""

    def __init__(self):
        self.z = np.full(H * W, np.inf)
        self.id = np.full(H * W, -3, np.int32)          # -1 パレット, -2 床
        self.face = np.zeros(H * W, np.int8)            # 0 天面, 1..4 側面
        self.n = np.zeros((H * W, 3))
        self.p = np.zeros((H * W, 3))
        self.alb = np.zeros((H * W, 3))
        self.gloss = np.zeros(H * W)

    def merge(self, part):
        """部品の z-buffer(画素ごとに 1 点へ縮めたもの)を重ねる。"""
        pix, z = part["pix"], part["z"]
        closer = z < self.z[pix]
        pix = pix[closer]
        self.z[pix] = z[closer]
        self.id[pix] = part["id"][closer]
        self.face[pix] = part["face"][closer]
        self.n[pix] = part["n"][closer]
        self.p[pix] = part["p"][closer]
        if part.get("alb") is not None:
            self.alb[pix] = part["alb"][closer]
            self.gloss[pix] = part["gloss"][closer]

    def image(self, a):
        return a.reshape((H, W) + a.shape[1:])


def _reduce(pw, nw, alb, gloss, bid, face, cam_x):
    """点の集まり → 画素ごとに最も手前の 1 点(部品の z-buffer)。"""
    u, v, z = project(pw, cam_x=cam_x)
    ui = np.round(u).astype(np.int64)
    vi = np.round(v).astype(np.int64)
    ok = np.flatnonzero((ui >= 0) & (ui < W) & (vi >= 0) & (vi < H) & (z > 0.05))
    idx = vi[ok] * W + ui[ok]
    order = np.lexsort((z[ok], idx))
    idx_s = idx[order]
    first = np.ones(len(idx_s), bool)
    first[1:] = idx_s[1:] != idx_s[:-1]
    sel = ok[order[first]]
    n = len(sel)
    part = {"pix": idx_s[first], "z": z[sel], "n": nw[sel], "p": pw[sel],
            "id": np.full(n, bid, np.int32),
            "face": (np.full(n, face, np.int8) if np.isscalar(face) else face[sel].astype(np.int8))}
    if alb is not None:
        part["alb"] = alb[sel]
        part["gloss"] = np.full(n, gloss) if np.isscalar(gloss) else gloss[sel]
    return part


def _concat(parts):
    keys = parts[0].keys()
    return {k: np.concatenate([p[k] for p in parts]) for k in keys}


def _pallet_and_floor(cam_x=0.0, with_color=True):
    """床(コンクリート)とパレットの上板(木、板の隙間あり)の部品。"""
    rng = np.random.default_rng(9)
    parts = []
    xs = np.arange(-1.2, 1.2, 0.0016)
    ys = np.arange(-0.95, 0.95, 0.0016)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], 1)
    N = np.tile([0, 0, 1.0], (len(P), 1))
    alb = None
    if with_color:
        g = 0.42 + 0.05 * rng.normal(0, 1, len(P))
        alb = np.stack([g, g * 0.98, g * 0.95], 1)
    parts.append(_reduce(P, N, alb, 0.05, -2, 0, cam_x))
    half = PALLET_SIZE / 2
    xs = np.arange(-half, half, 0.0012)
    ys = np.arange(-half, half, 0.0012)
    X, Y = np.meshgrid(xs, ys)
    pitch = PALLET_SIZE / 9
    board = ((Y + half) % pitch) < (pitch - 0.024)
    P = np.stack([X[board], Y[board], np.full(board.sum(), PALLET_TOP)], 1)
    N = np.tile([0, 0, 1.0], (len(P), 1))
    if with_color:
        grain = 0.06 * np.sin(X[board] * 90 + 3 * np.sin(Y[board] * 40)) + 0.03 * rng.normal(0, 1, len(P))
        alb = np.stack([0.62 + grain, 0.48 + grain, 0.32 + grain * 0.8], 1)
    parts.append(_reduce(P, N, alb, 0.05, -1, 0, cam_x))
    return parts


def _box_part(b, cam_x, with_color, spacing):
    pw, nw, st = sample_top(b, spacing)
    alb = gl = None
    if with_color:
        tex, gtex = top_texture(b)
        alb = lookup(tex, st[:, 0], st[:, 1], b.L, b.W)
        gl = lookup(gtex, st[:, 0], st[:, 1], b.L, b.W)
    top = _reduce(pw, nw, alb, gl if with_color else 0.0, b.id, 0, cam_x)
    pw, nw, fid, uv = sample_sides(b, spacing * 1.3)
    alb = None
    gl = 0.0
    if with_color:
        alb = np.zeros((len(pw), 3))
        for f in range(1, 5):
            m = fid == f
            tex = side_texture(b, f)
            length = b.W if f in (1, 2) else b.L
            alb[m] = lookup(tex, uv[m, 0], uv[m, 1] - b.H / 2, length, b.H, ppm=TEX_PPM / 2)
        gl = np.full(len(pw), 1.0 if b.shrink else 0.0)
    side = _reduce(pw, nw, alb, gl, b.id, fid, cam_x)
    return [top, side]          # 同じ画素が天面と側面の両方に出るので、別々に重ねる


class Renderer:
    """場面ごとに部品(箱 1 個ずつ)の z-buffer を 1 度だけ作り、残っている箱だけ重ねて描く。"""

    def __init__(self, scene, spacing=0.0009):
        self.scene = scene
        self.spacing = spacing
        self._cache = {}

    def _parts(self, key, maker):
        if key not in self._cache:
            self._cache[key] = maker()
        return self._cache[key]

    def render(self, boxes, with_color=True, cam_x=0.0):
        buf = Buffers()
        for part in self._parts(("bg", cam_x, with_color), lambda: _pallet_and_floor(cam_x, with_color)):
            buf.merge(part)
        sp = self.spacing if cam_x == 0.0 else self.spacing * 1.33
        for b in boxes:
            for part in self._parts(("box", b.id, cam_x, with_color),
                                    lambda b=b: _box_part(b, cam_x, with_color, sp)):
                buf.merge(part)
        return buf


def render(scene, with_color=True, cam_x=0.0, spacing=0.0009, boxes=None):
    """1 回だけ描く(部品の使い回しなし)。"""
    return Renderer(scene, spacing).render(scene.boxes if boxes is None else boxes, with_color, cam_x)


# ---------------------------------------------------------------- 色の描画(CI の代用。代表図は Blender)

LIGHT_DIR = np.array([0.25, 0.35, 1.0]) / np.linalg.norm([0.25, 0.35, 1.0])


def shade(buf: Buffers, rng, exposure=1.0):
    """反射率・法線 → 8 bit の sRGB。拡散 + 光沢(天井の照明)+ 隙間の暗がり + 撮像素子の雑音。"""
    n = buf.image(buf.n)
    alb = buf.image(buf.alb)
    gloss = buf.image(buf.gloss)
    p = buf.image(buf.p)
    lam = np.clip(np.einsum("hwc,c->hw", n, LIGHT_DIR), 0, 1)
    # 隙間・段差の暗がり(画面空間の遮蔽): 近傍の最も高い面より低いほど暗い
    zt = p[..., 2]
    hi = ndimage.maximum_filter(zt, size=21)
    ao = np.exp(-np.clip(hi - zt, 0, None) / 0.06)
    hi2 = ndimage.maximum_filter(zt, size=5)
    ao *= np.exp(-np.clip(hi2 - zt, 0, None) / 0.004 * 0.25)
    diffuse = alb * (0.30 * ao + 0.70 * lam * (0.4 + 0.6 * ao))[..., None]
    # 光沢: カメラの位置から見た反射(天井照明はカメラの近くにも並ぶ)
    view = np.stack([-p[..., 0], -p[..., 1], CAM_Z - p[..., 2]], -1)
    view /= np.linalg.norm(view, axis=-1, keepdims=True)
    half = view + LIGHT_DIR
    half /= np.linalg.norm(half, axis=-1, keepdims=True)
    spec = np.clip(np.einsum("hwc,hwc->hw", n, half), 0, 1) ** 220
    spec2 = np.clip(np.einsum("hwc,hwc->hw", n, view), 0, 1) ** 400      # カメラ脇の照明
    specular = (gloss * (1.6 * spec + 1.2 * spec2))[..., None]
    lin = exposure * (diffuse + specular)
    # 周辺減光
    yy, xx = np.mgrid[0:H, 0:W]
    r2 = ((xx - CX) ** 2 + (yy - CY) ** 2) / (CX ** 2 + CY ** 2)
    lin = lin * (1 - 0.25 * r2)[..., None]
    # レンズのぼけ
    lin = ndimage.gaussian_filter(lin, sigma=(0.7, 0.7, 0))
    return camera_sensor(lin, rng)


def srgb_to_linear(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def camera_sensor(lin, rng):
    """線形の放射輝度(1 = 飽和)→ 8 bit の sRGB。光子の雑音・読み出しの雑音・10 bit の量子化。

    数値の描画と Blender の描画の両方がここを通る(Blender は雑音の無い 16 bit を渡す)。
    """
    # 撮像素子: 光子(満水 9000 e-)+ 読み出し 6 e- + 10 bit
    fw = 9000.0
    e = np.clip(lin, 0, 1.2) * fw
    e = rng.poisson(np.maximum(e, 0)).astype(np.float64) + rng.normal(0, 6.0, e.shape)
    lin = np.clip(e / fw, 0, 1)
    lin = np.round(lin * 1023) / 1023
    srgb = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return (np.clip(srgb, 0, 1) * 255 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------- 深度センサ(縞・パターン投影)

#: 雑音: 2 m で 0.6 mm(距離の 2 乗で増える)、暗い面ほど増える。
SIGMA_2M = 0.0006


def _blobs(rng, frac, sigma):
    """相関した抜けの模様: 平滑化した乱数の上位 ``frac`` の割合(1 画素ずつの塩粒にしない)。"""
    f = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), sigma)
    return f > np.quantile(f, 1.0 - frac)


def depth_sensor(renderer, buf: Buffers, rng, boxes):
    """真の深度 → 測った深度 [m](欠測は 0)と、欠測の理由の画像。

    理由の番号: 1 投光の影 / 2 光沢の飽和 / 3 暗い面 / 4 段差の混合画素 / 5 多重反射(偽の点、値は残る)/
    6 斜面(見込み角が浅く対応が取れない)。抜けはどれも相関した塊(実機の能動ステレオ・縞投影の深度に
    近い見た目。1 画素ずつの塩粒にはしない)。
    """
    z = buf.image(buf.z).copy()
    p = buf.image(buf.p)
    n = buf.image(buf.n)
    gloss = buf.image(buf.gloss)
    alb = buf.image(buf.alb)
    reason = np.zeros((H, W), np.int8)
    # 1. 投光の影: 投光器から見えない点
    pbuf = renderer.render(boxes, with_color=False, cam_x=PROJ_BASELINE)
    pz = pbuf.image(pbuf.z)
    up, vp, zp = project(p.reshape(-1, 3), cam_x=PROJ_BASELINE)
    ui = np.clip(np.round(up).astype(int), 0, W - 1)
    vi = np.clip(np.round(vp).astype(int), 0, H - 1)
    inside = (up >= 0) & (up < W) & (vp >= 0) & (vp < H)
    seen = pz[vi, ui]
    # 隣の画素の最小で比べる(標本化の粗さで自分を影と誤らない)
    pz_min = ndimage.minimum_filter(pz, size=3)
    shadow = inside & (zp > pz_min[vi, ui] + 0.006) & (zp > seen + 0.006)
    shadow = shadow.reshape(H, W)
    reason[shadow] = 1
    # 2. 光沢の飽和: 投光の鏡面反射がカメラに入る
    proj = np.array([PROJ_BASELINE, 0.0, CAM_Z])
    to_p = proj[None, None, :] - p
    to_p /= np.linalg.norm(to_p, axis=-1, keepdims=True)
    to_c = np.array([0.0, 0.0, CAM_Z])[None, None, :] - p
    to_c /= np.linalg.norm(to_c, axis=-1, keepdims=True)
    hv = to_p + to_c
    hv /= np.linalg.norm(hv, axis=-1, keepdims=True)
    cosh = np.clip(np.einsum("hwc,hwc->hw", n, hv), -1, 1)
    ang = np.degrees(np.arccos(cosh))
    glossy = gloss > 0.5
    film = gloss > 0.95                 # シュリンクフィルム(しわで鏡面の向きが散る)。透明テープは 0.9
    sat = glossy & (ang < 7.0)
    # 鏡面のまわりで信号が乱れ、ところどころ抜ける(フィルムはしわで広く、テープは狭く)
    flaky = glossy & (ang < np.where(film, 16.0, 11.0)) & np.where(film, _blobs(rng, 0.35, 2.0), _blobs(rng, 0.2, 2.0))
    reason[(sat | flaky) & (reason == 0)] = 2
    # 5. 多重反射: 光沢の面のまわりで、奥にずれた偽の点
    multipath = glossy & (ang < np.where(film, 22.0, 14.0)) & (reason == 0)         & np.where(film, _blobs(rng, 0.18, 1.5), _blobs(rng, 0.08, 1.5))
    # 3. 暗い面(バーコードの黒い棒など)
    lum = alb @ np.array([0.3, 0.55, 0.15])
    dark = ndimage.binary_dilation(lum < 0.09, iterations=1) & _blobs(rng, 0.6, 1.2)
    reason[dark & (reason == 0)] = 3
    # 6. 斜面: 見込み角が浅い面(箱の側面)は対応が取れず抜ける
    cosv = np.einsum("hwc,hwc->hw", n, to_c)
    slant = (cosv < math.cos(math.radians(62.0))) & _blobs(rng, 0.7, 1.5)
    reason[slant & (reason == 0)] = 6
    # 雑音(相関あり: 相関窓 ≈ 5 px)
    sig = SIGMA_2M * (z / 2.0) ** 2 * np.sqrt(0.5 / np.clip(lum, 0.08, 1.0))
    sig = np.where(np.isfinite(sig), sig, 0.0)
    corr = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), 1.5) * 2.6
    # 縞の位相の残りが作る面内のうねり(± 0.25 mm、周期 約 40 px)
    yy, xx = np.mgrid[0:H, 0:W]
    ripple = 0.00025 * np.sin(2 * math.pi * (xx / 41.0 + 0.3 * yy / 97.0))
    zm = z + ripple + sig * (0.8 * corr + 0.6 * rng.normal(0, 1, (H, W)))
    # 段差の混合画素: 相関窓の中に段差があると前後の深度が混ざる(飛び点)
    zf = np.where(np.isfinite(zm), zm, 0.0)
    zs = ndimage.gaussian_filter(zf, 1.2)
    rng_loc = ndimage.maximum_filter(zf, size=3) - ndimage.minimum_filter(zf, size=3)
    step = rng_loc > 0.03
    zm = np.where(step, zs, zm)
    flying_drop = step & _blobs(rng, 0.45, 1.0)
    reason[flying_drop & (reason == 0)] = 4
    zm = np.where(multipath, zm + rng.uniform(0.005, 0.025, (H, W)), zm)
    reason[multipath & (reason == 0)] = 5
    zm = np.round(zm / 0.000125) * 0.000125
    out = np.where(((reason >= 1) & (reason <= 4)) | (reason == 6), 0.0, zm)
    out = np.where(np.isfinite(out), out, 0.0)
    return out, reason


# ================================================================================================
# 箱の天面を見つける 3 つのやり方(深度だけ / カラーだけ / 両方)。真値は読まない。
#
# Top-face detection from an overhead RGB-D frame, three ways:
#
# * ``depth``  —— 上を向いた面を深度の段差で切り分ける(継ぎ目が詰まって高さが揃うと分けられない)。
# * ``color``  —— カラーの境界(輝度の勾配 + 暗い継ぎ目)で切り分ける(印字・テープ・ラベルで割れる)。
# * ``fused``  —— 深度で切った面を、面の端から端まで通る暗い継ぎ目があるときだけカラーで割る。
#
# どれも分割の後の**測り方は同じ**(深度の点に平面を当て、天面の矩形を当てる)。カラーだけの
# やり方も高さと矩形は深度から読む —— 比べているのは「何で切り分けるか」だけ。
#
# Fullseye の op: ``depth_to_organized_points``(range_image)、``bilateral_filter_depth``、
# ``normals_from_depth``、``watersheds_marker``(segmentation)、``ransac_plane``(ransac_fit)、
# ``fit_rectangle2``(measure)、``crop_rectangle2``(image_gen)。
#
# ================================================================================================

#: 天面とみなす法線の傾きの上限 [deg]。
UP_DEG = 18.0
#: 深度の段差とみなす局所の高低差 [m](5 × 5 の窓)。センサの雑音(2 m で 0.6 mm)の 10 倍余り。
STEP_M = 0.009
#: 埋める穴の大きさ [px](最寄りの有効画素までの距離)。光沢の点々の抜けは埋め、大きな抜けは残す。
HOLE_PX = 6.0
#: 平面の当てはめの閾値 [m]。
PLANE_TOL = 0.005
#: 箱の天面として受け入れる辺の長さ [m] と、矩形らしさ(面積 / 外接矩形)の下限。
SIDE_MIN, SIDE_MAX = 0.11, 0.75
RECT_MIN = 0.78
#: 割る線(継ぎ目)の判定: 暗い溝の強さ [8 bit の階調] と、線に沿って溝が続く割合。
SEAM_BH = 10.0
SEAM_SPAN = 0.72
#: 深度の継ぎ目の溝: 線に沿った平均の沈み [m](線の外の中央値からの差)。手元の場面で継ぎ目は 0.6〜1.9 mm、印刷の罫線は 0.4 mm 以下だった。
VALLEY_MIN = 0.0005
DEBUG_SEAM = False


def set_valley_min(v: float) -> float:
    """VALLEY_MIN を差し替え、元の値を返す(閾値の掃引用)。"""
    global VALLEY_MIN
    old, VALLEY_MIN = VALLEY_MIN, float(v)
    return old
#: カラーの境界: 勾配 [階調/px] と暗い溝。
COLOR_GRAD = 9.0


@dataclass
class Detection:
    cx: float           # 天面の中心(世界)[m]
    cy: float
    cz: float
    yaw: float          # 長辺の向き [rad]
    l1: float           # 半辺 [m](l1 ≥ l2)
    l2: float
    normal: tuple       # 平面の法線(世界、上向き)
    rect: float         # 矩形らしさ
    mask: np.ndarray    # 画素の範囲(bool)
    split: int = 0      # カラーの継ぎ目で割った回数


def world_points(depth, K, cam_z):
    """深度 → 世界の点 (H, W, 3)(欠測は NaN)。カメラは真下向き(画像の下 = −y)。"""
    fx, fy, cx, cy = K
    pc = range_image.depth_to_organized_points(depth, fx, fy, cx, cy)
    pw = np.stack([pc[..., 0], -pc[..., 1], cam_z - pc[..., 2]], -1)
    pw[depth <= 0] = np.nan
    return pw


def _gray(rgb):
    return rgb[..., :3].astype(np.float64) @ np.array([0.299, 0.587, 0.114])


def color_maps(rgb):
    return _memo("color", rgb, lambda: _color_maps(rgb))


def _color_maps(rgb):
    """カラーの手がかり 2 つ: 勾配の強さと、暗い細い溝(黒のトップハット)。単位は 8 bit の階調。"""
    g = _gray(rgb)
    gs = ndimage.gaussian_filter(g, 1.2)
    grad = np.hypot(ndimage.sobel(gs, 0), ndimage.sobel(gs, 1)) / 8.0
    bh = ndimage.grey_closing(gs, size=(11, 11)) - gs
    return grad, bh


def _measure(region, pw, pix_area, split=0):
    """1 つの領域 → 平面 + 矩形。条件を満たさなければ None。"""
    pts = pw[region]
    pts = pts[np.isfinite(pts).all(1)]
    if len(pts) < 300:
        return None
    if len(pts) > 6000:
        sub = pts[np.random.default_rng(0).choice(len(pts), 6000, replace=False)]
    else:
        sub = pts
    params, inl, _ = ransac_fit.ransac_plane(sub, PLANE_TOL, iters=150, seed=0)
    nrm = np.asarray(params["normal"], float)
    if nrm[2] < 0:
        nrm = -nrm
    if nrm[2] < math.cos(math.radians(25)):
        return None
    d = (pts - np.asarray(params["point"])) @ nrm
    keep = np.abs(d) < 2 * PLANE_TOL
    pts = pts[keep]
    if len(pts) < 300:
        return None
    # 天面の矩形: 平面の上の 2 次元座標で当てる(傾いた箱の寸法を斜めに縮めないため)
    e1 = np.cross([0.0, 1.0, 0.0], nrm)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    c0 = pts.mean(0)
    a = (pts - c0) @ e1
    b = (pts - c0) @ e2
    try:
        r = measure.fit_rectangle2(np.stack([b, a], 1))
    except ValueError:
        return None
    l1, l2 = r["l1"], r["l2"]
    centre = c0 + r["cx"] * e1 + r["cy"] * e2
    th = math.radians(r["angle_deg"])
    axis = math.cos(th) * e1 + math.sin(th) * e2
    yaw = math.atan2(axis[1], axis[0])
    area = float(pix_area[region].sum()) * nrm[2]
    filled = ndimage.binary_fill_holes(region)
    area = max(area, float(pix_area[filled].sum()) * nrm[2])
    rect = area / max(4 * l1 * l2, 1e-9)
    return Detection(float(centre[0]), float(centre[1]), float(centre[2]), yaw, l1, l2,
                     tuple(nrm), float(min(rect, 1.5)), region, split)


def plausible(d: Detection) -> bool:
    return (SIDE_MIN <= 2 * d.l2 and 2 * d.l1 <= SIDE_MAX and d.rect >= RECT_MIN)


def _pix_area(depth, K):
    fx, fy = K[0], K[1]
    return (depth / fx) * (depth / fy)


_MEMO: dict = {}


def _memo(name, arr, fn):
    """同じコマ(同じ配列)に 2 度かけない(深度だけ・両方が同じ分割を使う)。直近の 4 件だけ持つ。"""
    key = (name, id(arr), arr.shape, float(arr[::37, ::41].sum()))
    if key not in _MEMO:
        if len(_MEMO) > 8:
            _MEMO.clear()
        _MEMO[key] = fn()
    return _MEMO[key]


def depth_regions(depth, K, cam_z):
    return _memo("regions", depth, lambda: _depth_regions(depth, K, cam_z))


def _depth_regions(depth, K, cam_z):
    """深度だけで上向きの面を切り分ける → (ラベル画像, 世界の点)。"""
    dz = depth_bilateral.bilateral_filter_depth(depth, 1.5, 0.004, invalid=0.0)
    pw = world_points(dz, K, cam_z)
    # 段差と法線は「小さな穴を埋め、飛び点を中央値で抑えた」深度で見る(測るのは元の点)
    filled = depth_bilateral.fill_holes(dz, HOLE_PX, invalid=0.0)
    filled = ndimage.median_filter(np.where(np.isfinite(filled), filled, 0.0), size=5)
    Km = np.array([[K[0], 0, K[2]], [0, K[1], K[3]], [0, 0, 1.0]])
    n = fs.normals_from_depth(np.where(filled > 0, filled, np.nan), Km, smooth=1)
    up = np.isfinite(n).all(-1) & (-n[..., 2] > math.cos(math.radians(UP_DEG)))
    zw = np.where(filled > 0, cam_z - filled, -1.0)
    rng_loc = ndimage.maximum_filter(zw, size=5) - ndimage.minimum_filter(zw, size=5)
    core = up & (rng_loc < STEP_M) & (filled > 0)
    core = ndimage.binary_opening(core, iterations=2)
    lab, nl = ndimage.label(core)
    # 段差の帯(切るために外した画素)を、深度の勾配の上で最寄りの面へ戻す(watershed)
    grad = np.where(np.isfinite(rng_loc), rng_loc, 1.0)
    grown = segmentation.watersheds_marker(grad, lab)
    grown = np.where(up | (filled <= 0), grown, 0)
    return np.asarray(grown, np.int32), pw, dz


def _area_ok(region, pa):
    return pa[region].sum() >= 0.10 * 0.10


def detect_depth(depth, rgb, K, cam_z):
    lab, pw, dz = depth_regions(depth, K, cam_z)
    pa = _pix_area(np.where(dz > 0, dz, np.median(dz[dz > 0])), K)
    out = []
    for i in range(1, int(lab.max()) + 1):
        reg = lab == i
        if not _area_ok(reg, pa):
            continue
        d = _measure(reg, pw, pa)
        if d is not None:
            out.append(d)
    return out


def detect_color(depth, rgb, K, cam_z):
    """カラーの境界で切り分け、測るのは深度(高さ・矩形)。"""
    grad, bh = color_maps(rgb)
    boundary = (grad > COLOR_GRAD) | (bh > SEAM_BH)
    inner = ~boundary
    dist = ndimage.distance_transform_edt(inner)
    markers, nm = ndimage.label(dist > 7.0)
    lab = np.asarray(segmentation.watersheds_marker(grad, markers), np.int32)
    _, pw, dz = depth_regions(depth, K, cam_z)
    pa = _pix_area(np.where(dz > 0, dz, np.median(dz[dz > 0])), K)
    out = []
    for i in range(1, int(lab.max()) + 1):
        reg = lab == i
        if not _area_ok(reg, pa):
            continue
        d = _measure(reg, pw, pa)
        if d is not None:
            out.append(d)
    return out


def _seam_split(reg, bh, valley, depth_px_per_m, level=0, use_color=True, use_valley=True):
    """領域の中を端から端まで通る継ぎ目があれば、そこで 2 つに割る(再帰)。

    ``use_color`` / ``use_valley`` で手がかりを片方ずつ外せる(切除の比較: 深度の V 字だけ / カラーの溝だけ)。

    候補の線 = カラーの暗い溝が線の 72 % 以上で続く所。そのうえで、**深度にも継ぎ目の溝**
    (段ボールの角の丸みが作る浅い V 字、線に沿った平均で ``VALLEY_MIN`` 以上)がある線だけを採る。
    印刷の罫線・テープの縁はカラーでは継ぎ目に似るが、深度には溝が無い。
    """
    rr, cc = np.nonzero(reg)
    if len(rr) < 500 or level > 3:
        return [reg]
    try:
        r = measure.fit_rectangle2(np.stack([rr, cc], 1).astype(float))
    except ValueError:
        return [reg]
    phi = math.radians(r["angle_deg"])
    l1, l2 = int(r["l1"]) - 6, int(r["l2"]) - 6          # 縁の溝(箱の外周)は除く
    if l1 < 20 or l2 < 20:
        return [reg]
    crop = image_gen.crop_rectangle2(np.where(reg, bh, 0.0), r["cy"], r["cx"], phi, l1, l2)
    vcrop = image_gen.crop_rectangle2(np.where(reg, valley, 0.0), r["cy"], r["cx"], phi, l1, l2)
    best = None
    min_px = 0.11 * depth_px_per_m
    for axis in (0, 1):
        # axis 0: 長辺に直交する線(列ごと)、axis 1: 長辺に平行な線(行ごと)
        prof_frac = (crop > SEAM_BH).mean(axis=axis) if use_color else np.ones(crop.shape[1 - axis])
        prof_val = vcrop.mean(axis=axis)
        prof_val = prof_val - np.median(prof_val)          # 雑音で底上げされた分(最大値フィルタの偏り)を引く
        prof_mean = crop.mean(axis=axis) if use_color else np.clip(prof_val, 0, None)
        n = len(prof_frac)
        half = (n - 1) / 2.0
        full = (l1 if axis == 0 else l2) + 6
        offs = np.arange(n) - half
        ok = (prof_frac >= SEAM_SPAN) & ((full + offs) >= min_px) & ((full - offs) >= min_px)
        for k in np.flatnonzero(ok):
            lo, hi = max(0, k - 2), min(n, k + 3)
            val = float(prof_val[lo:hi].max())
            if DEBUG_SEAM:
                print("seam cand axis", axis, "k", k, "frac %.2f" % prof_frac[k], "valley %.2f mm" % (val * 1e3))
            if use_valley and val < VALLEY_MIN:
                continue
            # 溝の中心へ寄せる: カラーの溝の深さの重心(±4 px)
            lo4, hi4 = max(0, k - 4), min(n, k + 5)
            w = np.clip(prof_mean[lo4:hi4], 0, None)
            kc = float((np.arange(lo4, hi4) * w).sum() / w.sum()) if w.sum() > 0 else float(k)
            score = val if use_valley else float(prof_frac[k])
            if best is None or score > best[0]:
                best = (score, axis, kc - half)
    if best is None:
        return [reg]
    _, axis, off = best
    # 割る線: 矩形の座標で、長辺方向(axis 0)なら u = off、短辺方向なら v = off
    ca, sa = math.cos(phi), math.sin(phi)
    du = (cc - r["cx"]) * ca + (rr - r["cy"]) * sa
    dv = -(cc - r["cx"]) * sa + (rr - r["cy"]) * ca
    coord = du if axis == 0 else dv
    a = np.zeros_like(reg)
    b = np.zeros_like(reg)
    a[rr[coord < off - 1], cc[coord < off - 1]] = True
    b[rr[coord > off + 1], cc[coord > off + 1]] = True
    out = []
    for part in (a, b):
        out.extend(_seam_split(part, bh, valley, depth_px_per_m, level + 1, use_color, use_valley))
    return out


def depth_valley(depth, K, cam_z):
    """深度の細い溝 [m]: 近傍(9 px)の最も高い面からの沈み。継ぎ目の V 字の手がかり。"""
    def make():
        _, pw, dz = depth_regions(depth, K, cam_z)
        f = depth_bilateral.fill_holes(dz, HOLE_PX, invalid=0.0)
        f = np.where(np.isfinite(f) & (f > 0), f, np.nan)
        h = np.where(np.isfinite(f), cam_z - f, -1.0)
        v = ndimage.maximum_filter(h, size=9) - h
        v = np.where(np.isfinite(f), np.clip(v, 0, 0.02), 0.0)
        return ndimage.uniform_filter(v, 3)
    return _memo("valley", depth, make)


def _split_detect(depth, rgb, K, cam_z, use_color, use_valley):
    """深度で切った面を継ぎ目の線で割る(手がかりは use_color / use_valley で選ぶ)。"""
    lab, pw, dz = depth_regions(depth, K, cam_z)
    bh = color_maps(rgb)[1] if use_color else np.zeros(depth.shape)
    valley = depth_valley(depth, K, cam_z)
    pa = _pix_area(np.where(dz > 0, dz, np.median(dz[dz > 0])), K)
    out = []
    for i in range(1, int(lab.max()) + 1):
        reg = lab == i
        if not _area_ok(reg, pa):
            continue
        zc = np.nanmedian(pw[reg][:, 2]) if np.isfinite(pw[reg][:, 2]).any() else 1.0
        px_per_m = K[0] / max(cam_z - zc, 0.3)
        # 割る線は「深度のある画素」の範囲で探す(投光の影などの欠測を領域の外形に入れない)
        parts = _seam_split(reg & (dz > 0), bh, valley, px_per_m, 0, use_color, use_valley)
        for k, part in enumerate(parts):
            d = _measure(part, pw, pa, split=len(parts) - 1)
            if d is not None:
                out.append(d)
    return out


def detect_fused(depth, rgb, K, cam_z):
    """両方: カラーの暗い溝が線の 72 % 以上で続き、かつ深度の V 字の溝がある線でだけ割る。"""
    return _split_detect(depth, rgb, K, cam_z, True, True)


def detect_vgroove(depth, rgb, K, cam_z):
    """深度の V 字だけ(カラーを使わない): 深度の段差で切った面を、深度の浅い溝の線で割る。"""
    return _split_detect(depth, None, K, cam_z, False, True)


def detect_cseam(depth, rgb, K, cam_z):
    """カラーの溝だけ: 深度の段差で切った面を、カラーの暗い溝が通る線で割る(深度の溝は見ない)。"""
    return _split_detect(depth, rgb, K, cam_z, True, False)


DETECTORS = {"depth": detect_depth, "vgroove": detect_vgroove, "color": detect_color,
             "cseam": detect_cseam, "fused": detect_fused}
MODE_JA = {"depth": "深度の段差", "vgroove": "深度の V 字", "color": "カラーだけ", "cseam": "カラーの溝",
           "fused": "両方(AND)"}
#: カラーを読まないやり方(CI の代用カラーでも結論が変わらない)。
DEPTH_ONLY_MODES = ("depth", "vgroove")


# ================================================================================================
# 採点(真値の側): 検出の照合、吸着ハンドの成否と失敗の分類、1 個ずつ下ろす繰り返し。
#
# Scoring against the rendered ground truth: detection ↔ free top faces, the suction-pad outcome
# with a failure taxonomy (not found / double pick / drop / snag / pose off), and the
# pick-one-re-sense loop.
#
# ================================================================================================

#: 吸着パッド(段ボール用の角形フォームパッド)160 × 80 mm、真空 −60 kPa。
PAD_L, PAD_W = 0.16, 0.08
VACUUM_PA = 60e3
#: パッドの下の面の凹凸がこれを超えると漏れる [m](フォームの沈み込みの範囲)。
SEAL_DEV = 0.006
#: 引きはがしのモーメントの許容 = 吸着力 × パッド半長 × 係数(フォームの縁で受ける分)。
PEEL_K = 0.30
#: 持ち上げと搬送の加速(重力の 1.6 倍で見積もる)。
DYN = 1.6
#: コンベアへ置くときの許容: 中心 20 mm、向き 5°。
PLACE_POS, PLACE_YAW = 0.020, math.radians(5.0)
#: 二重取り: パッドの下に 2 つの箱がそれぞれ 15 % 以上。
DOUBLE_FRAC = 0.15
SINGLE_FRAC = 0.88

#: 6 軸アームの可搬質量 [kg](公表値)と、手先の道具(真空の配管・軸・パッド)の質量 [kg](見積もり)。
PAYLOAD_KG = 12.5
TOOL_KG = 1.8
#: 寸法つきの一致: IoU ≥ 0.5 に加えて、長辺・短辺の誤差がどちらもこれ以下 [m]。
SIZE_TOL = 0.020

OUTCOMES = ("success", "pose", "double", "drop", "snag", "overload", "notfound")
OUTCOME_JA = {"success": "成功", "pose": "姿勢がずれる", "double": "二重取り", "drop": "取り落とし",
              "snag": "引っかけ", "overload": "可搬超過", "notfound": "見つからない"}


def free_boxes(boxes):
    """上に何も載っていない箱(天面の 98 % 以上が空いている)。"""
    out = []
    for b in boxes:
        g = np.linspace(-0.45, 0.45, 12)
        ss, tt = np.meshgrid(g * b.L, g * b.W)
        pts = b.to_world(np.stack([ss.ravel(), tt.ravel(), np.full(ss.size, b.H)], 1))
        covered = np.zeros(len(pts), bool)
        for o in boxes:
            if o is b or o.z0 < b.z0 + b.H - 0.02:
                continue
            z, _, _ = top_surface_height(o, pts[:, :2])
            covered |= np.isfinite(z)
        if covered.mean() < 0.02:
            out.append(b)
    return out


def _yaw_err(a, b):
    d = (a - b) % math.pi
    return min(d, math.pi - d)


def match(dets, boxes):
    """検出 ↔ 空いている箱の天面(矩形の重なりの IoU ≥ 0.5)。"""
    free = free_boxes(boxes)
    pairs = []
    used = set()
    for di, d in enumerate(dets):
        best = None
        for b in free:
            if b.id in used:
                continue
            tc = b.top_center_world()
            inter = geometry2d.area_intersection_rectangle2(
                d.cy, d.cx, d.yaw, d.l1, d.l2, tc[1], tc[0], b.yaw, b.L / 2, b.W / 2)
            union = 4 * d.l1 * d.l2 + b.L * b.W - inter
            iou = inter / union if union > 0 else 0.0
            if iou >= 0.5 and (best is None or iou > best[0]):
                best = (iou, b)
        if best is not None:
            b = best[1]
            used.add(b.id)
            tc = b.top_center_world()
            pairs.append({"det": di, "box": b.id, "iou": best[0],
                          "pos_err": float(math.hypot(d.cx - tc[0], d.cy - tc[1])),
                          "yaw_err": float(_yaw_err(d.yaw, b.yaw)),
                          "size_err": float(max(abs(2 * d.l1 - b.L), abs(2 * d.l2 - b.W)))})
    n_size = sum(1 for q in pairs if q["size_err"] <= SIZE_TOL)
    return {"n_free": len(free), "n_det": len(dets), "n_match": len(pairs), "n_match_size": n_size, "pairs": pairs}


def surface_under(boxes, xy):
    """世界の xy 点の真上から見て一番上の箱の天面(高さ、箱の番号)。"""
    zbest = np.full(len(xy), -np.inf)
    who = np.full(len(xy), -1)
    for b in boxes:
        z, _, _ = top_surface_height(b, xy)
        better = np.isfinite(z) & (z > zbest)
        zbest[better] = z[better]
        who[better] = b.id
    return zbest, who


def grasp_outcome(det, boxes):
    """吸着パッドを検出の中心に当てたときの結果と、それを決めた量。"""
    ca, sa = math.cos(det.yaw), math.sin(det.yaw)
    g1 = np.linspace(-PAD_L / 2, PAD_L / 2, 17)
    g2 = np.linspace(-PAD_W / 2, PAD_W / 2, 9)
    U, V = np.meshgrid(g1, g2)
    xy = np.stack([det.cx + U.ravel() * ca - V.ravel() * sa, det.cy + U.ravel() * sa + V.ravel() * ca], 1)
    z, who = surface_under(boxes, xy)
    info = {"target": None}
    if (who < 0).all():
        return "notfound", info
    ids, counts = np.unique(who[who >= 0], return_counts=True)
    frac = dict(zip(ids.tolist(), (counts / len(who)).tolist()))
    if sum(frac.values()) < 0.5:
        # パッドの半分以上が箱の上に無い = 箱ではない面(パレットの板・床)を天面と取り違えた
        info["not_a_box"] = True
        return "notfound", info
    big = [i for i, f in frac.items() if f >= DOUBLE_FRAC]
    if len(big) >= 2:
        info["target"] = big
        return "double", info
    top_id = max(frac, key=frac.get)
    b = next(o for o in boxes if o.id == top_id)
    info["target"] = [top_id]
    if frac[top_id] < SINGLE_FRAC:
        return "drop", info                          # パッドが縁からはみ出して漏れる
    zz = z[who == top_id]
    P = np.column_stack([xy[who == top_id], np.ones(len(zz))])
    coef, *_ = np.linalg.lstsq(P, zz, rcond=None)
    dev = float(np.max(np.abs(P @ coef - zz)))
    info["seal_dev"] = dev
    if dev > SEAL_DEV:
        return "drop", info
    if b not in free_boxes(boxes):
        return "snag", info
    if b.mass + TOOL_KG > PAYLOAD_KG:
        # 吸着はできても、箱と道具の質量がアームの可搬を超える(持ち上げない)
        info["payload_kg"] = b.mass + TOOL_KG
        return "overload", info
    tc = b.top_center_world()
    off = math.hypot(det.cx - tc[0], det.cy - tc[1])
    force = VACUUM_PA * PAD_L * PAD_W
    moment = b.mass * 9.81 * DYN * off
    info["moment_ratio"] = moment / (force * PAD_L / 2 * PEEL_K)
    if b.mass * 9.81 * DYN > force or info["moment_ratio"] > 1.0:
        return "drop", info
    yaw_e = _yaw_err(det.yaw, b.yaw)
    info["pos_err"] = off
    info["yaw_err"] = yaw_e
    if off > PLACE_POS or yaw_e > PLACE_YAW:
        return "pose", info
    return "success", info


def choose(dets):
    """次に取る検出: 一番高い天面(15 mm 以内は同じ高さとみなし、コンベア側 = +x を先に)。"""
    cand = [d for d in dets if plausible(d)]
    if not cand:
        return None
    zmax = max(d.cz for d in cand)
    top = [d for d in cand if d.cz >= zmax - 0.015]
    return max(top, key=lambda d: d.cx)


# ================================================================================================
# 1 個ずつ下ろして撮り直す繰り返し(3 つのやり方で同じ場面を回す)。
# ================================================================================================

K = (FX, FY, CX, CY)


class FrameSource:
    """残っている箱の組 → (カラー, 深度, 欠測の理由)。同じ組なら同じコマ(やり方の間で共有)。"""

    def __init__(self, scene, color_provider=None):
        self.scene = scene
        self.r = Renderer(scene)
        self.cache = {}
        self.color_provider = color_provider      # Blender の描画を差し込む口(無ければ数値の描画)
        self.renders = 0

    def get(self, boxes, need_rgb=True):
        """(カラー or None, 深度, 欠測の理由, 箱の番号の画像)。カラーは要るときだけ作る(深度だけのやり方は読まない)。"""
        key = tuple(sorted(b.id for b in boxes))
        if key not in self.cache:
            h = hashlib.sha256(("%s/%d/%s" % (self.scene.condition, self.scene.seed, key)).encode()).digest()
            rng = np.random.default_rng(int.from_bytes(h[:8], "little"))
            buf = self.r.render(boxes)
            depth, reason = depth_sensor(self.r, buf, rng, boxes)
            self.cache[key] = [None, depth, reason, buf]
            self.renders += 1
        ent = self.cache[key]
        if need_rgb and ent[0] is None:
            rgb = None
            if self.color_provider is not None:
                rgb = self.color_provider(self.scene, key)
            if rgb is None:
                h = hashlib.sha256(("rgb/%s/%d/%s" % (self.scene.condition, self.scene.seed, key)).encode()).digest()
                rgb = shade(ent[3], np.random.default_rng(int.from_bytes(h[:8], "little")))
            ent[0] = rgb
        return ent[0], ent[1], ent[2], ent[3]


def run_loop(src: FrameSource, mode: str, max_steps: int = 60):
    """やり方 ``mode`` で、パレットが空になるまで 1 個ずつ下ろす。各手の記録の列を返す。"""
    boxes = list(src.scene.boxes)
    log = []
    det_fn = DETECTORS[mode]
    while boxes and len(log) < max_steps:
        rgb, depth, _, _ = src.get(boxes, need_rgb=(mode not in DEPTH_ONLY_MODES))
        dets = det_fn(depth, rgb, K, CAM_Z)
        d = choose(dets)
        free = free_boxes(boxes)
        if d is None:
            outcome, info = "notfound", {"target": None}
        else:
            outcome, info = grasp_outcome(d, boxes)
        rec = {"step": len(log), "outcome": outcome, "n_left": len(boxes),
               "key": tuple(sorted(b.id for b in boxes)),
               "det": None if d is None else {"cx": d.cx, "cy": d.cy, "cz": d.cz, "yaw": d.yaw,
                                               "l1": d.l1, "l2": d.l2, "split": d.split}}
        for k in ("pos_err", "yaw_err", "seal_dev", "moment_ratio"):
            if k in info:
                rec[k] = float(info[k])
        # 場面の更新: 取れた箱・落とした箱・人が直した箱を外す
        if outcome in ("success", "pose", "drop", "snag", "double", "overload") and info.get("target"):
            gone = set(info["target"])
        else:
            # 見つからない: 人が一番高い空いた箱を 1 個どける(数えたうえで先へ進む)
            hb = max(free, key=lambda b: b.top_center_world()[2])
            gone = {hb.id}
        rec["removed"] = sorted(gone)
        log.append(rec)
        boxes = [b for b in boxes if b.id not in gone]
    return log


def summarize(logs):
    """手の記録の列(複数パレット分)→ 結果ごとの数と、位置・向きの誤差。"""
    cnt = {k: 0 for k in OUTCOMES}
    pos, yaw = [], []
    n_boxes = 0
    for log in logs:
        for rec in log:
            cnt[rec["outcome"]] += 1
            n_boxes += len(rec["removed"])
            if "pos_err" in rec:
                pos.append(rec["pos_err"])
                yaw.append(rec["yaw_err"])
    n = sum(cnt.values())
    return {"counts": cnt, "attempts": n, "boxes": n_boxes,
            "success_rate": cnt["success"] / n if n else float("nan"),
            "pos_med_mm": 1000 * float(np.median(pos)) if pos else float("nan"),
            "pos_p95_mm": 1000 * float(np.percentile(pos, 95)) if pos else float("nan"),
            "yaw_med_deg": math.degrees(float(np.median(yaw))) if yaw else float("nan")}


# ================================================================================================
# 場面を Blender に渡す形(箱ごとの OBJ と反射率の PNG、JSON)で書き出す。
#
# Export a depalletizing scene for the Blender (Cycles) renderer: one OBJ per box part in the
# box's local frame (top with crush and rounded edges, four sides, the shrink film), the albedo /
# gloss PNGs the numpy renderer also uses, and a JSON with world transforms and camera intrinsics.
#
# ================================================================================================

MESH_SPACING = 0.004


def _local_box(b):
    c = copy.copy(b)
    c.x = c.y = c.z0 = 0.0
    c.yaw = 0.0
    c.tilt = 0.0
    return c


def box_matrix(b) -> np.ndarray:
    """箱の局所(底面中心が原点)→ 世界の 4 × 4。``Box.to_world`` と同じ変換。"""
    R = b.rotation()
    piv = b.pivot_local()
    c, s = math.cos(b.yaw), math.sin(b.yaw)
    Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    t = np.array([b.x, b.y, b.z0]) + Rz @ piv - R @ piv
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = t
    return M


def _grid_obj(path: Path, P: np.ndarray, UV: np.ndarray, nr: int, nc: int, flip=False):
    """格子に並んだ点 (nr × nc) を四角形の面の OBJ に書く。"""
    lines = ["# depal export"]
    lines += ["v %.6f %.6f %.6f" % tuple(p) for p in P]
    lines += ["vt %.6f %.6f" % tuple(u) for u in UV]
    for i in range(nr - 1):
        for j in range(nc - 1):
            a = i * nc + j + 1
            q = (a, a + 1, a + nc + 1, a + nc)
            if flip:
                q = q[::-1]
            lines.append("f " + " ".join("%d/%d" % (k, k) for k in q))
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def _top_grid(b, shrink):
    lb = _local_box(b)
    lb.shrink = shrink
    ns = max(2, int(math.ceil(b.L / MESH_SPACING)) + 1)
    pw, _, st = sample_top(lb, b.L / (ns - 1) * 0.999999)
    # sample_top は (t の行) × (s の列) の順で並べる
    nt2 = len(np.unique(np.round(st[:, 1], 9)))
    ns2 = len(st) // nt2
    uv = np.stack([(st[:, 0] + b.L / 2) / b.L, (b.W / 2 - st[:, 1]) / b.W], 1)
    return pw, uv, nt2, ns2


def _side_grids(b, shrink):
    """側面 4 枚(局所)。面ごとに (点, uv, 行数, 列数, 面番号)。"""
    out = []
    off = 0.0015 if shrink else 0.0
    nh = max(2, int(math.ceil(b.H / MESH_SPACING)) + 1)
    h = np.linspace(0.0, b.H - b.edge_r, nh)
    for k, (axis, sign) in enumerate([(0, 1), (0, -1), (1, 1), (1, -1)]):
        length = b.W if axis == 0 else b.L
        nu = max(2, int(math.ceil(length / MESH_SPACING)) + 1)
        u = np.linspace(-length / 2, length / 2, nu)
        U, Hh = np.meshgrid(u, h)
        if axis == 0:
            P = np.stack([np.full(U.size, sign * (b.L / 2 + off)), U.ravel(), Hh.ravel()], 1)
        else:
            P = np.stack([U.ravel(), np.full(U.size, sign * (b.W / 2 + off)), Hh.ravel()], 1)
        uv = np.stack([(U.ravel() + length / 2) / length, 1.0 - Hh.ravel() / b.H], 1)
        flip = (axis == 0 and sign < 0) or (axis == 1 and sign > 0)
        out.append((P, uv, nh, nu, k + 1, flip))
    return out


def _png(path: Path, arr: np.ndarray):
    a = np.clip(arr, 0, 1)
    if a.ndim == 2:
        Image.fromarray((a * 255 + 0.5).astype(np.uint8), "L").save(path)
    else:
        # 反射率は線形 → sRGB で保存(Blender は sRGB の色空間として読む)
        srgb = np.where(a <= 0.0031308, 12.92 * a, 1.055 * np.power(a, 1 / 2.4) - 0.055)
        Image.fromarray((srgb * 255 + 0.5).astype(np.uint8), "RGB").save(path)


def export_scene(scene, out: Path, frames: list[tuple[int, ...]] | None = None) -> Path:
    """``out`` に書く。``frames`` は描くコマ(残っている箱の番号の組)の並び。"""
    out.mkdir(parents=True, exist_ok=True)
    boxes = []
    for b in scene.boxes:
        bd = b.to_dict()
        bd["matrix"] = box_matrix(b).tolist()
        tex, gloss = top_texture(b)
        _png(out / ("top_%02d.png" % b.id), tex)
        _png(out / ("gloss_%02d.png" % b.id), gloss)
        P, uv, nr, nc = _top_grid(b, False)
        _grid_obj(out / ("top_%02d.obj" % b.id), P, uv, nr, nc)
        sides = []
        for (P, uv, nr, nc, f, flip) in _side_grids(b, False):
            _png(out / ("side_%02d_%d.png" % (b.id, f)), side_texture(b, f))
            name = "side_%02d_%d.obj" % (b.id, f)
            _grid_obj(out / name, P, uv, nr, nc, flip)
            sides.append(name)
        bd["sides"] = sides
        if b.shrink:
            P, uv, nr, nc = _top_grid(b, True)
            _grid_obj(out / ("film_top_%02d.obj" % b.id), P, uv, nr, nc)
            fs_ = []
            for (P, uv, nr, nc, f, flip) in _side_grids(b, True):
                name = "film_side_%02d_%d.obj" % (b.id, f)
                _grid_obj(out / name, P, uv, nr, nc, flip)
                fs_.append(name)
            bd["film_sides"] = fs_
        boxes.append(bd)
    meta = {
        "condition": scene.condition, "seed": scene.seed, "boxes": boxes,
        "camera": {"z": CAM_Z, "fx": FX, "fy": FY, "cx": CX, "cy": CY,
                   "width": IMG_W, "height": IMG_H},
        "pallet": {"size": PALLET_SIZE, "top": PALLET_TOP},
        "frames": [list(f) for f in (frames or [tuple(b.id for b in scene.boxes)])],
    }
    p = out / "scene.json"
    p.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return p


# ================================================================================================
# 混載デパレタイズの「平らな面 → 平面 → 矩形」を、実機の深度(HOPE / 能動ステレオ式の深度カメラ)で検算する。
#
# HOPE (Household Objects for Pose Estimation, BOP 形式) の val 50 枚を使う。
# ライセンスは同梱 dataset_info.md が CC BY-NC-SA 4.0、BOP 配布ページが CC BY-SA 4.0 と
# 食い違うので、厳しい NC 側に倒して**数値だけ**を出す。画像を外へ出す図は作らない。
#
# 構成(検出と採点を分ける):
#
# * 検出側 ``hope_detect_planes`` —— 引数は深度 [m]、RGB、K だけ。
#   GT のファイルも dict も一切受け取らない(``hope_load_observation`` が読むのは rgb/depth/
#   scene_camera.json の 3 つだけ)。
# * 真値側 ``hope_load_truth`` / ``gt_faces`` —— scene_gt.json・scene_gt_info.json・mask_visib・
#   models_info.json・ply だけを読む。
# * 採点 ``hope_score_image`` —— 検出の結果(矩形と画素の範囲)と真の面を照合する。
#
# 単位: 検出も真値も内部は m。報告は mm。
# 深度の補正係数 0.98042517 は dataset_info.md に「RGB へ登録する前に深度を何倍かした」と
# あり、配布済みの深度に掛け済み。ここでは**もう一度掛けない**(``depth_sanity`` で、面の
# 投影上の実測深度と真の深度の比を見て確かめる)。
#
# ================================================================================================

# ---------------------------------------------------------------------------
# 閾値(全画像で 1 組。画像ごとに変えない)
# ---------------------------------------------------------------------------
#: 間引き。配布の深度は 深度カメラの 1280×720 を 1920×1080 の RGB へ登録して拡大したもの
#: なので、半分(960×540)に落としても深度の情報はほぼ失わない。0.7 m で 1 画素 ≈ 1 mm、
#: 一番小さい面(Butter の 24 × 53 mm)でも 24 × 53 画素ある。
hope_DS = 2
#: bilateral の空間 σ [px] と値 σ [m]。天井の場面の depth_regions と同じ(2 px, 4 mm)。
BIL_SS, BIL_SR = 2.0, 0.004
#: 法線を出す前の箱平均 [px]。
hope_NRM_SMOOTH = 5
#: 隣を見る距離 [px](≈ 2 mm)。
hope_NB = 2
#: 段差 [m]: 画素の接平面から 2 px 先の点までの距離。天井の場面の depth_regions の 9 mm は「雑音の 10 倍余り」
#: (2 m で 0.6 mm)から決めていた。ここでは 000001/000000(GT は見ない)の 9×9 画素の局所平面
#: 残差を測ると中央値 0.42 mm・90 % 点 1.2 mm だったので、同じ考え方で約 10 倍の 4 mm。
#: 一番薄い箱(Butter・CreamCheese の 24 mm)の 1/6 で、箱と机の段差は必ず越える。
#: 斜めのカメラでは局所の深度の幅は面の傾きで大きくなる(60° の面では 5 mm 横で 8.7 mm)ので、
#: depal の「5×5 の max−min」ではなく「接平面からの距離」で測る(傾いた面を段差と取り違えない)。
hope_STEP_M = 0.004
#: 法線の不連続 [deg]: 隣の画素の法線との角度。箱の隣り合う面は 90°、雑音の揺れは数度。
hope_NRM_DEG = 20.0
#: 切り目を太らせる画素数(途切れた切り目から隣の面へ漏れないように)。
hope_EDGE_GROW = 2
#: 平面の当てはめの閾値 [m]。最初は局所の雑音(9×9 で 0.4〜1.2 mm)と模型の平らさ(ply で 10–90 %
#: 幅 ≤ 1.3 mm)から 3 mm にしたが、深度カメラの深度には面の幅で効くうねりがあり、bilateral 後の点を
#: 面ごとに平面へ当てた残差は σ 1.2〜3.2 mm・95 % 点 1.8〜6.3 mm(scene 1・2 の 10 枚、真の面の投影で
#: 測った)。3 mm では 1 m 先の面が 2〜4 片に割れた。95 % 点の典型 3〜4 mm に余裕を足し、天井の場面の知覚
#: と同じ 5 mm にした。★この値は scene 1・2 の真値を見て決めたので、scene 1・2 は「調整に使った」、
#: scene 3〜10 は「見ていない」として結果を分けて出す(``split_by_tuning``)。
hope_PLANE_TOL = 0.005
#: 閾値を決めるのに真値を見たシーン(結果を分けて出す)。
hope_TUNING_SCENES = (1, 2)
#: 領域の最小の画素数(半分の解像度で)。0.7 m で ≈ 150 mm²(12 × 12 mm)。
hope_MIN_PX = 150
#: 測るときに縁を戻す幅 [px]。切り目の線(1〜2 px)を hope_EDGE_GROW = 2 太らせると面の縁が約 2〜3 px 落ち、
#: watershed の帯で戻った分も hope_split_planes の法線の条件(平滑の半径 ≈ 2.5 px の丸み)で落ちる。見積もり
#: ≈ 3 px。★感度: scene 1・2 の 10 枚で 0 px → 長辺 −13 / 短辺 −4.5 mm、6 px → −0.3 / +4.1 mm
#: (6 px では遮る縁の 深度カメラの「縁の太り」まで拾って外へ伸びる)。真値で合わせ込まず見積もりの 3 にした。
#: 全 50 枚の 0 / 3 / 6 の比較(下書きの段で出した): 再現率 0.705 / 0.705 / 0.674、誤検出 14.8 / 43.1 / 52.2 枚あたり。
#: 全 50 枚の実測(2026-11-08): 0 px → 再現率 0.705・長 −7.8・短 −2.6 mm・誤検出 14.8 枚/画像 /
#: 3 px → 0.705・−2.0・+2.9・43.1 / 6 px → 0.674・+0.4・+5.8・52.2。再現率は変わらず、寸法の偏りと
#: 誤検出の数の綱引き(太らせると雑音の小片まで矩形らしくなる)。
hope_GROW_PX = 3
#: 逐次 RANSAC: 画素の法線と平面の法線の角度の上限 [deg] と、1 領域から抜く平面の最大数。
hope_SPLIT_DEG = 25.0
hope_SPLIT_MAX = 80            # 000001/000001 では粗い領域が 18 万画素(机・箱・容器が繋がる)になり、12 では面まで届かなかった
#: 採点で「矩形らしい」とみなす範囲(誤検出の定義もこれ): 辺 15〜200 mm、面積 / 矩形 ≥ 0.75。
SIDE_LO, SIDE_HI = 0.015, 0.200
hope_RECT_MIN = 0.75
#: 照合: 中心 < 15 mm かつ 法線 < 15°。
MATCH_D, MATCH_DEG = 0.015, 15.0
#: 真値の面: カメラを向く(cos > 0.5)、物体の visib_fract ≥ 0.7、面の投影の 8 割以上が見える。
FACE_COS, VISIB_MIN, FACE_VIS_MIN = 0.5, 0.7, 0.8
#: 箱型の候補(ply の頂点・面で確かめてから使う)。
hope_BOX_CANDIDATES = (3, 5, 6, 8, 9, 12, 22, 23, 25)
#: ply の面のうち、平らさ(10–90 % 幅)がこれを超える面は真値から外す(反った底など)。
hope_FACE_WARP_MAX = 2.0e-3
#: 箱とみなす条件: 表面の 97 % 以上が外接箱から 4 mm 以内。
hope_BOX_WITHIN4_MIN = 0.97


# ===========================================================================
# 検出側(GT を読まない)
# ===========================================================================
@dataclass
class hope_Plane:
    centre: np.ndarray          # カメラ座標 [m]
    normal: np.ndarray          # カメラを向く単位法線
    sides: tuple                # (長辺, 短辺) [m]
    rect: float                 # 面積 / 矩形の面積
    mask: np.ndarray            # 間引いた画像の上の画素の範囲 (bool)
    n_pts: int
    split: int = 0


@dataclass
class hope_Observation:
    depth: np.ndarray           # [m]、間引き後、欠測 0
    rgb: np.ndarray             # 間引き後 uint8
    K: np.ndarray               # 間引き後 3×3


def hope_load_observation(scene_dir: Path, im_id: int) -> hope_Observation:
    """検出に渡すものだけを読む(rgb, depth, scene_camera.json)。"""
    cams = json.loads((scene_dir / "scene_camera.json").read_text())
    cam = cams[str(im_id)]
    K = np.array(cam["cam_K"], float).reshape(3, 3)
    dep = np.asarray(Image.open(scene_dir / "depth" / f"{im_id:06d}.png"), np.float64)
    dep = dep * float(cam["depth_scale"]) / 1000.0           # → mm → m
    rgb = np.asarray(Image.open(scene_dir / "rgb" / f"{im_id:06d}.png").convert("RGB"))
    Kd = K.copy()
    Kd[0, 0] /= hope_DS; Kd[1, 1] /= hope_DS
    # 画素中心の合わせ: 間引き後の画素 u' は元の u = hope_DS·u'(左上の画素を取る)
    Kd[0, 2] /= hope_DS; Kd[1, 2] /= hope_DS
    return hope_Observation(dep[::hope_DS, ::hope_DS].copy(), rgb[::hope_DS, ::hope_DS].copy(), Kd)


def _hope_shift(a, dy, dx):
    """a を (dy, dx) ずらした配列(はみ出しは NaN)。out[y, x] = a[y+dy, x+dx]。"""
    out = np.full_like(a, np.nan)
    H, W = a.shape[:2]
    ys = slice(max(0, -dy), min(H, H - dy)); xs = slice(max(0, -dx), min(W, W - dx))
    ys2 = slice(max(0, dy), min(H, H + dy)); xs2 = slice(max(0, dx), min(W, W + dx))
    out[ys, xs] = a[ys2, xs2]
    return out


def hope_plane_regions(obs: hope_Observation):
    """カメラ座標で平らな面を切り分ける → (ラベル, 点 (H,W,3), 平滑後の深度)。

    法線の不連続(隣の法線と hope_NRM_DEG 以上)と段差(接平面から hope_STEP_M 以上)を切り目にし、
    残った芯をラベル付け、切り目の帯を watershed で最寄りの芯へ戻す。
    """
    d = obs.depth
    dz = depth_bilateral.bilateral_filter_depth(d, BIL_SS, BIL_SR, invalid=0.0)
    K = obs.K
    P = range_image.depth_to_organized_points(dz, K[0, 0], K[1, 1], K[0, 2], K[1, 2])
    P[dz <= 0] = np.nan
    n = fs.normals_from_depth(np.where(dz > 0, dz, np.nan), K, smooth=hope_NRM_SMOOTH)
    valid = np.isfinite(n).all(-1) & np.isfinite(P).all(-1)
    cmin = math.cos(math.radians(hope_NRM_DEG))
    step = np.zeros(d.shape)
    ndev = np.zeros(d.shape)
    for dy, dx in ((hope_NB, 0), (-hope_NB, 0), (0, hope_NB), (0, -hope_NB)):
        Pq = _hope_shift(P, dy, dx)
        nq = _hope_shift(n, dy, dx)
        s = np.abs(np.sum(n * (Pq - P), -1))
        c = np.sum(n * nq, -1)
        step = np.fmax(step, np.where(np.isfinite(s), s, 1.0))
        ndev = np.fmax(ndev, np.where(np.isfinite(c), 1.0 - c, 1.0))
    edge = (step > hope_STEP_M) | (ndev > 1.0 - cmin) | ~valid
    # 切り目は 1〜2 画素の細い線で、ところどころ途切れる(角の丸み・雑音)。途切れから隣の面へ
    # 漏れないよう hope_EDGE_GROW 画素太らせてから芯を作る(太らせた分は後で watershed が戻す)。
    edge = ndimage.binary_dilation(edge, iterations=hope_EDGE_GROW)
    core = ndimage.binary_opening(~edge, iterations=1)
    lab, nl = ndimage.label(core)
    if nl:
        sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nl + 1))
        keep = np.zeros(nl + 1, bool); keep[1:] = sizes >= hope_MIN_PX
        lab = np.where(keep[lab], lab, 0)
        lab, nl = ndimage.label(lab > 0)
    # 切り目の帯(芯から 4 px 以内)だけを、段差の強さの上で最寄りの芯へ戻す
    grad = np.clip(step / hope_STEP_M, 0, 10) + np.clip(ndev / (1 - cmin), 0, 10)
    grown = np.asarray(segmentation.watersheds_marker(grad, lab), np.int32)
    band = ndimage.binary_dilation(lab > 0, iterations=4) & valid
    grown = np.where(band, grown, 0)
    return grown, P, n


def hope_split_planes(region: np.ndarray, P: np.ndarray, n: np.ndarray, seed: int = 0) -> list[np.ndarray]:
    """1 つの領域を、平面を 1 枚ずつ抜き出して割る(逐次 RANSAC + 画像上の連結成分)。

    法線と段差の切り目は角の丸み・雑音で途切れ、隣の面と 1 つの領域に繋がることがある(000001/000000
    の検分で、同じ箱の直交する 2 面・隣り合う箱が 1 領域になった)。そこで領域の中で ransac_plane の
    最大平面を取り、「平面から hope_PLANE_TOL 以内 かつ 画素の法線が平面の法線から hope_SPLIT_DEG 以内」の画素の
    画像上の連結成分を 1 面とし、残りで繰り返す。
    """
    out = []
    rest = region & np.isfinite(P).all(-1) & np.isfinite(n).all(-1)
    rng = np.random.default_rng(seed)
    cmin = math.cos(math.radians(hope_SPLIT_DEG))
    fails = 0
    for it in range(hope_SPLIT_MAX):
        if rest.sum() < hope_MIN_PX or fails >= 3:
            break
        pts = P[rest]
        sub = pts[rng.choice(len(pts), 3000, replace=False)] if len(pts) > 3000 else pts
        try:
            params, _, _ = ransac_fit.ransac_plane(sub, hope_PLANE_TOL, iters=200, seed=seed + it)
        except ValueError:
            break
        nrm = np.asarray(params["normal"], float)
        p0 = np.asarray(params["point"], float)
        dist = np.abs((P - p0) @ nrm)
        cosn = np.abs(np.sum(n * nrm, -1))
        inl = rest & (dist < hope_PLANE_TOL) & (cosn > cmin)
        if inl.sum() < hope_MIN_PX // 2:
            fails += 1
            continue
        fails = 0
        cl, nc = ndimage.label(inl)
        if nc:
            sz = ndimage.sum(inl, cl, index=np.arange(1, nc + 1))
            for k in np.nonzero(sz >= hope_MIN_PX)[0]:
                out.append(cl == k + 1)
        rest = rest & ~inl
    return out


def _hope_measure(region: np.ndarray, P: np.ndarray, fx: float, split: int = 0, seed: int = 0) -> hope_Plane | None:
    """1 つの領域 → 平面 + 平面の上の矩形。

    平面から hope_PLANE_TOL 以内の画素のうち、**画像の上で**最大の連結成分だけを使う(飛び画素を除く)。
    最初の版は平面の上の 1 mm 格子で連結成分を取っていたが、斜めの面では画素の足跡が 1 mm を越えて
    格子が飛び飛びになり、面の一部しか測れなかった(000001〜000002 で長辺が半分になる例)ので改めた。
    矩形は平面の上の 2 次元座標に fit_rectangle2 を当て、点は画素の中心なので辺に足跡 1 つ分を足す。
    """
    H, W = region.shape
    fin = region & np.isfinite(P).all(-1)
    pts = P[fin]
    if len(pts) < hope_MIN_PX:
        return None
    rng = np.random.default_rng(seed)
    sub = pts[rng.choice(len(pts), 4000, replace=False)] if len(pts) > 4000 else pts
    try:
        params, _, _ = ransac_fit.ransac_plane(sub, hope_PLANE_TOL, iters=150, seed=seed)
    except ValueError:
        return None
    nrm = np.asarray(params["normal"], float)
    p0 = np.asarray(params["point"], float)
    if nrm @ p0 > 0:                                          # カメラ(原点)を向かせる
        nrm = -nrm
    # 縁を戻す: 切り目(法線・段差の判定 + 太らせ)と hope_split_planes の法線の条件で、面の縁の数画素が
    # 落ちている。領域を hope_GROW_PX 太らせた範囲で、平面からの距離だけで画素を拾い直す。直交する隣の面
    # (同じ箱の側面・机)の点は平面へ投影すると稜線の上に落ちるので、辺を外へ伸ばさない。
    # ★scipy の binary_dilation は iterations=0 で「変わらなくなるまで」太らせる(= 切り出し全体)。0 は太らせない。
    grown = ndimage.binary_dilation(region, iterations=hope_GROW_PX) if hope_GROW_PX > 0 else region
    cand = grown & np.isfinite(P).all(-1)
    inl = np.zeros((H, W), bool)
    cp = P[cand]
    inl[cand] = np.abs((cp - p0) @ nrm) < hope_PLANE_TOL
    cl, nc = ndimage.label(inl)
    if nc == 0:
        return None
    big = np.argmax(ndimage.sum(inl, cl, index=np.arange(1, nc + 1))) + 1
    keep = cl == big
    pts = P[keep]
    if len(pts) < hope_MIN_PX:
        return None
    # 最小二乗で当て直す(inlier の共分散の最小主軸)
    c0 = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c0, full_matrices=False)
    nrm = vt[2] / np.linalg.norm(vt[2])
    if nrm @ c0 > 0:
        nrm = -nrm
    # 平面の上の 2 次元座標(斜めの面を斜めに縮めないため、画像でなく平面上で測る)
    ref = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(ref, nrm); e1 /= np.linalg.norm(e1)
    e2 = np.cross(nrm, e1)
    uv = np.stack([(pts - c0) @ e1, (pts - c0) @ e2], 1)
    if np.ptp(uv[:, 0]) > 2.0 or np.ptp(uv[:, 1]) > 2.0:       # 2 m を越える平面(壁・床)は測らない
        return None
    # 画素の足跡(平面の上)[m]: z / fx を視線と法線の角度で割る
    ray = pts / np.linalg.norm(pts, axis=1, keepdims=True)
    cos_v = np.clip(np.abs(ray @ nrm), 0.2, 1.0)
    foot_area = (pts[:, 2] / fx) ** 2 / cos_v
    foot = float(np.median(np.sqrt(foot_area)))
    try:
        r = measure.fit_rectangle2(uv)                       # (row, col) = (u, v)
    except ValueError:
        return None
    l1 = 2 * r["l1"] + foot
    l2 = 2 * r["l2"] + foot
    centre = c0 + r["cy"] * e1 + r["cx"] * e2
    # 矩形らしさ: 画像の上で穴を埋めた画素数 × 足跡の面積(中央値)/ 矩形の面積
    n_fill = int(ndimage.binary_fill_holes(keep).sum())
    rect = n_fill * float(np.median(foot_area)) / max(l1 * l2, 1e-12)
    return hope_Plane(centre, nrm, (max(l1, l2), min(l1, l2)), min(rect, 1.5), keep, int(len(pts)), split)


def _hope_regions(lab: np.ndarray, P: np.ndarray, n: np.ndarray):
    """粗い領域ごとに hope_split_planes を外接矩形の切り出しの上で回す(速さのため)。→ [(slice, 切り出しの bool)]"""
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        for part in hope_split_planes(lab[sl] == i, P[sl], n[sl]):
            out.append((sl, part))
    return out


def _hope_measure_full(sl, part, P, fx, shape, split=0):
    """切り出し(縁を戻す分 hope_GROW_PX + 1 だけ広げる)の上で測り、mask を画像全体へ戻す。"""
    m = hope_GROW_PX + 1
    sl2 = (slice(max(sl[0].start - m, 0), min(sl[0].stop + m, shape[0])),
           slice(max(sl[1].start - m, 0), min(sl[1].stop + m, shape[1])))
    part2 = np.zeros((sl2[0].stop - sl2[0].start, sl2[1].stop - sl2[1].start), bool)
    part2[sl[0].start - sl2[0].start: sl[0].stop - sl2[0].start,
          sl[1].start - sl2[1].start: sl[1].stop - sl2[1].start] = part
    p = _hope_measure(part2, P[sl2], fx, split=split)
    if p is None:
        return None
    full = np.zeros(shape, bool)
    full[sl2] = p.mask
    p.mask = full
    return p


def _hope_detect_depth(obs, P, regs):
    out = []
    for sl, part in regs:
        p = _hope_measure_full(sl, part, P, obs.K[0, 0], obs.depth.shape)
        if p is not None:
            out.append(p)
    return out


def hope_detect_planes(obs: hope_Observation) -> list[hope_Plane]:
    """深度だけ: 平らな面を切り分け、領域ごとに平面と矩形。"""
    lab, P, n = hope_plane_regions(obs)
    return _hope_detect_depth(obs, P, _hope_regions(lab, P, n))


def hope_detect_all(obs: hope_Observation) -> tuple[dict, dict]:
    """深度だけの検出(切り分け → 平面 → 矩形)。→ ({方式: [hope_Plane]}, {段: 秒})。

    ★下書きでは「深度で切った面をカラーの継ぎ目で割る」版も回したが、HOPE の小さく印刷の多い箱では
    一度も割らなかった(割った回数 0)ので、PoC には深度だけを残した。
    """
    t0 = time.perf_counter()
    lab, P, n = hope_plane_regions(obs)
    regs = _hope_regions(lab, P, n)
    t1 = time.perf_counter()
    a = _hope_detect_depth(obs, P, regs)
    t2 = time.perf_counter()
    return {"depth": a}, {"segment": t1 - t0, "depth": t2 - t1}


hope_DETECTORS = {"depth": hope_detect_planes}


def hope_plausible(p: hope_Plane) -> bool:
    """箱の面らしい矩形(辺 15〜200 mm・矩形らしさ ≥ 0.75)。誤検出の数え方にも使う。"""
    return SIDE_LO <= p.sides[1] and p.sides[0] <= SIDE_HI and p.rect >= hope_RECT_MIN


# ===========================================================================
# 真値側(検出には渡さない)
# ===========================================================================
def _hope_read_ply(path: Path):
    lines = path.read_text().split("\n")
    nv = int(next(l for l in lines if l.startswith("element vertex")).split()[-1])
    nf = int(next(l for l in lines if l.startswith("element face")).split()[-1])
    s = lines.index("end_header") + 1
    V = np.array([[float(x) for x in l.split()[:3]] for l in lines[s:s + nv]])
    F = np.array([[int(x) for x in l.split()[1:4]] for l in lines[s + nv:s + nv + nf]])
    return V, F


def hope_box_models(root: Path, seed: int = 0) -> dict:
    """ply の表面を面積に比例して標本化し、本当に直方体かを確かめる。

    返り値: obj_id → {"size": (3,) [m], "is_box", "within4", "faces": {(ax, sg): {...}}}。
    面ごとに、模型の実際の面の位置(外接箱からの沈み)、平らさ(10–90 % 幅)、平らな部分の
    広がり(外接箱の辺との差)を測る。
    """
    info = json.loads((root / "models" / "models_info.json").read_text())
    rng = np.random.default_rng(seed)
    out = {}
    for oid in hope_BOX_CANDIDATES:
        V, F = _hope_read_ply(root / "models" / f"obj_{oid:06d}.ply")
        A = V[F]
        area = 0.5 * np.linalg.norm(np.cross(A[:, 1] - A[:, 0], A[:, 2] - A[:, 0]), axis=1)
        k = rng.choice(len(F), 150000, p=area / area.sum())
        u = rng.random((150000, 2)); m = u.sum(1) > 1; u[m] = 1 - u[m]
        S = A[k, 0] + u[:, :1] * (A[k, 1] - A[k, 0]) + u[:, 1:] * (A[k, 2] - A[k, 0])
        mn, mx = S.min(0), S.max(0)
        c, h = (mn + mx) / 2, (mx - mn) / 2
        size_info = np.array([info[str(oid)]["size_x"], info[str(oid)]["size_y"], info[str(oid)]["size_z"]])
        Sc = S - c
        within4 = float(np.mean(np.min(h - np.abs(Sc), 1) < 4.0))
        faces = {}
        for ax in range(3):
            o = [a for a in range(3) if a != ax]
            for sg in (-1, 1):
                dd = h[ax] - sg * Sc[:, ax]
                inner = (dd < 6) & (np.abs(Sc[:, o[0]]) < 0.6 * h[o[0]]) & (np.abs(Sc[:, o[1]]) < 0.6 * h[o[1]])
                off = float(np.median(dd[inner])) if inner.any() else float("nan")
                spread = float(np.percentile(dd[inner], 90) - np.percentile(dd[inner], 10)) if inner.any() else float("inf")
                flat = np.abs(dd - off) < 1.5
                ext = [float(np.percentile(Sc[flat, a], 99.5) - np.percentile(Sc[flat, a], 0.5)) for a in o]
                faces[(ax, sg)] = {"offset_m": off / 1000, "warp_m": spread / 1000,
                                   "flat_ext_m": [e / 1000 for e in ext]}
        out[oid] = {"size": size_info / 1000, "centre_off": c / 1000, "within4": within4,
                    "is_box": within4 >= hope_BOX_WITHIN4_MIN, "faces": faces}
    return out


@dataclass
class hope_TrueFace:
    scene: int
    im: int
    obj_id: int
    gt_idx: int
    axis: int
    sign: int
    centre: np.ndarray          # カメラ座標 [m](外接箱の面の中心)
    normal: np.ndarray
    sides: tuple                # 外接箱の (長, 短) [m]
    flat_sides: tuple           # ply の平らな部分の (長, 短) [m]
    vis_frac: float             # 面の投影のうち mask_visib に乗る割合
    depth_valid: float          # 面の投影のうち深度がある割合(失敗の分類用)
    depth_ratio: float          # 実測深度 / 真の深度(中央値)
    proj_px: np.ndarray = field(repr=False, default=None)   # 間引き画像の上の面の画素 (N,2) row,col
    eligible: bool = False
    reason: str = ""            # 採点から外した理由: "occluded"(8 割未満しか見えない)/ "warped"(模型の面が反っている)


def hope_load_truth(scene_dir: Path, im_id: int, models: dict, depth_m_full: np.ndarray | None = None):
    """1 枚の真の面を作る(採点専用)。depth_m_full は深度の検算と失敗の分類にだけ使う。

    → (faces, objlab)。objlab は間引き画像の上の見えている物体: 0 = 背景、obj_id = 採点対象の箱、
    1000+id = 箱だが visib_fract < 0.7、2000+id = 箱でない物体(缶・瓶など)。
    """
    gts = json.loads((scene_dir / "scene_gt.json").read_text())[str(im_id)]
    infos = json.loads((scene_dir / "scene_gt_info.json").read_text())[str(im_id)]
    cam = json.loads((scene_dir / "scene_camera.json").read_text())[str(im_id)]
    K = np.array(cam["cam_K"], float).reshape(3, 3)
    faces = []
    objlab = None                       # 間引き画像の上の「どの物体が見えているか」(誤検出の分類用)
    for gi, (g, inf) in enumerate(zip(gts, infos)):
        oid = int(g["obj_id"])
        mv = np.asarray(Image.open(scene_dir / "mask_visib" / f"{im_id:06d}_{gi:06d}.png"))[::hope_DS, ::hope_DS] > 0
        if objlab is None:
            objlab = np.zeros(mv.shape, np.int32)
        scored_box = oid in models and models[oid]["is_box"] and inf["visib_fract"] >= VISIB_MIN
        objlab[mv] = oid if scored_box else (1000 + oid if (oid in models and models[oid]["is_box"]) else 2000 + oid)
        if oid not in models or not models[oid]["is_box"]:
            continue
        if inf["visib_fract"] < VISIB_MIN:
            continue
        R = np.array(g["cam_R_m2c"], float).reshape(3, 3)
        t = np.array(g["cam_t_m2c"], float) / 1000.0
        mdl = models[oid]
        h = mdl["size"] / 2
        cmod = mdl["centre_off"]          # 外接箱の中心(BOP の模型は ≈ 0)
        mask = np.asarray(Image.open(scene_dir / "mask_visib" / f"{im_id:06d}_{gi:06d}.png")) > 0
        H, W = mask.shape
        for ax in range(3):
            o = [a for a in range(3) if a != ax]
            for sg in (-1, 1):
                fn = np.zeros(3); fn[ax] = sg
                fc = cmod + fn * h[ax]
                cc = R @ fc + t
                nn = R @ fn
                if float(nn @ (-cc / np.linalg.norm(cc))) <= FACE_COS:
                    continue
                fi = mdl["faces"][(ax, sg)]
                warped = fi["warp_m"] > hope_FACE_WARP_MAX
                # 面の内側 90 % を 0.7 mm 間隔で標本化して投影(間引き画像の画素 ≈ 1 mm より細かく)
                a = np.arange(-0.9 * h[o[0]], 0.9 * h[o[0]] + 1e-9, 0.0007)
                b = np.arange(-0.9 * h[o[1]], 0.9 * h[o[1]] + 1e-9, 0.0007)
                A_, B_ = np.meshgrid(a, b, indexing="ij")
                Q = np.zeros((A_.size, 3)); Q[:, ax] = fc[ax]; Q[:, o[0]] = cmod[o[0]] + A_.ravel(); Q[:, o[1]] = cmod[o[1]] + B_.ravel()
                Qc = Q @ R.T + t
                uvw = Qc @ K.T
                u = uvw[:, 0] / uvw[:, 2]; v = uvw[:, 1] / uvw[:, 2]
                ui = np.round(u).astype(int); vi = np.round(v).astype(int)
                inside = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
                if not inside.any():
                    continue
                vis = np.zeros(len(u), bool); vis[inside] = mask[vi[inside], ui[inside]]
                vis_frac = float(vis.mean())
                dv, dr = float("nan"), float("nan")
                if depth_m_full is not None:
                    dm = np.zeros(len(u)); dm[inside] = depth_m_full[vi[inside], ui[inside]]
                    sel = vis & (dm > 0)
                    dv = float(sel.sum() / max(vis.sum(), 1))
                    if sel.sum() > 20:
                        dr = float(np.median(dm[sel] / Qc[sel, 2]))
                sides = sorted([2 * h[o[0]], 2 * h[o[1]]], reverse=True)
                flat = sorted(fi["flat_ext_m"], reverse=True)
                pr = np.unique(np.stack([vi[inside] // hope_DS, ui[inside] // hope_DS], 1), axis=0)
                tf = hope_TrueFace(int(scene_dir.name), im_id, oid, gi, ax, sg, cc, nn, tuple(sides), tuple(flat),
                              vis_frac, dv, dr, pr)
                tf.reason = "warped" if warped else ("occluded" if vis_frac < FACE_VIS_MIN else "")
                tf.eligible = tf.reason == ""
                faces.append(tf)
    return faces, objlab


# ===========================================================================
# 採点
# ===========================================================================
def _hope_angle_deg(a, b):
    return float(np.degrees(np.arccos(np.clip(abs(float(a @ b)), -1.0, 1.0))))


def hope_match(dets: list[hope_Plane], faces: list[hope_TrueFace]):
    """1 対 1 の照合(中心 < 15 mm かつ 法線 < 15°、費用 = 中心の距離)。→ [(det_i, face_j)]"""
    if not dets or not faces:
        return []
    C = np.full((len(dets), len(faces)), 1e6)
    for i, d in enumerate(dets):
        for j, f in enumerate(faces):
            dist = float(np.linalg.norm(d.centre - f.centre))
            if dist < MATCH_D and _hope_angle_deg(d.normal, f.normal) < MATCH_DEG:
                C[i, j] = dist
    ri, ci = linear_sum_assignment(C)
    return [(int(i), int(j)) for i, j in zip(ri, ci) if C[i, j] < 1e5]


def _hope_classify_miss(f: hope_TrueFace, dets: list[hope_Plane], shape) -> tuple[str, dict]:
    """見つからなかった面の型を当てる(検出の画素範囲と面の投影の重なりから)。"""
    H, W = shape
    fm = np.zeros(shape, bool)
    pr = f.proj_px
    ok = (pr[:, 0] < H) & (pr[:, 1] < W)
    fm[pr[ok, 0], pr[ok, 1]] = True
    nf = int(fm.sum())
    best, best_ov = None, 0.0
    for d in dets:
        inter = int((d.mask & fm).sum())
        if inter == 0:
            continue
        cover = inter / max(nf, 1)
        if cover > best_ov:
            best, best_ov = d, cover
    detail = {"face_px": nf, "min_side_mm": round(f.sides[1] * 1000, 1), "depth_valid": round(f.depth_valid, 2)}
    if f.depth_valid < 0.7:
        return "depth_missing", detail
    if best is None or best_ov < 0.2:
        return ("too_small" if nf < 2 * hope_MIN_PX else "not_segmented"), detail
    dist = float(np.linalg.norm(best.centre - f.centre)) * 1000
    ang = _hope_angle_deg(best.normal, f.normal)
    outside = int((best.mask & ~ndimage.binary_dilation(fm, iterations=3)).sum()) / max(int(best.mask.sum()), 1)
    detail.update({"cover": round(best_ov, 2), "outside_frac": round(outside, 2),
                   "centre_err_mm": round(dist, 1), "normal_err_deg": round(ang, 1),
                   "det_sides_mm": [round(s * 1000, 1) for s in best.sides]})
    if outside > 0.3:
        return "merged_with_neighbour", detail
    if best_ov < 0.6:
        return "fragmented", detail
    return "measured_off", detail


def hope_score_image(dets: list[hope_Plane], faces: list[hope_TrueFace], shape, objlab: np.ndarray | None = None) -> dict:
    """1 枚の採点。照合は採点対象(eligible)の面とだけ行い、それ以外の面に当たった検出は誤検出に数えない。"""
    elig = [f for f in faces if f.eligible]
    pairs = hope_match(dets, elig)
    matched_d = {i for i, _ in pairs}
    matched_f = {j for _, j in pairs}
    rows = []
    for i, j in pairs:
        d, f = dets[i], elig[j]
        rows.append({
            "scene": f.scene, "im": f.im, "obj_id": f.obj_id, "gt_idx": f.gt_idx,
            "err_long_mm": (d.sides[0] - f.sides[0]) * 1000, "err_short_mm": (d.sides[1] - f.sides[1]) * 1000,
            "err_long_flat_mm": (d.sides[0] - f.flat_sides[0]) * 1000,
            "err_short_flat_mm": (d.sides[1] - f.flat_sides[1]) * 1000,
            "centre_mm": float(np.linalg.norm(d.centre - f.centre)) * 1000,
            "normal_deg": _hope_angle_deg(d.normal, f.normal), "rect": d.rect, "hope_plausible": hope_plausible(d),
            "true_sides_mm": [s * 1000 for s in f.sides],
        })
    # 誤検出: どの真の面(採点対象外の面も含む)にも当たらない、箱の面らしい矩形
    all_pairs_any = hope_match([d for k, d in enumerate(dets) if k not in matched_d], faces)
    hit_other = {k for k, _ in all_pairs_any}
    rest = [d for k, d in enumerate(dets) if k not in matched_d]
    fps = [d for k, d in enumerate(rest) if k not in hit_other and hope_plausible(d)]
    fp_where = []
    for d in fps:
        where = "unknown"
        if objlab is not None:
            v = objlab[d.mask]
            vals, cnt = np.unique(v, return_counts=True)
            top = int(vals[np.argmax(cnt)])
            where = ("background" if top == 0 else "scored_box" if top < 1000 else
                     "box_low_visib" if top < 2000 else "non_box_object")
            where_id = top % 1000
        fp_where.append((where, where_id if objlab is not None else None))
    misses = []
    for j, f in enumerate(elig):
        if j in matched_f:
            continue
        kind, detail = _hope_classify_miss(f, dets, shape)
        misses.append({"scene": f.scene, "im": f.im, "obj_id": f.obj_id, "gt_idx": f.gt_idx, "kind": kind, **detail})
    return {"n_faces": len(elig), "n_found": len(pairs), "rows": rows, "misses": misses,
            "fp": [{"sides_mm": [round(s * 1000, 1) for s in d.sides], "rect": round(d.rect, 2),
                    "centre_m": [round(float(x), 3) for x in d.centre], "on": w, "on_obj": wid}
                   for d, (w, wid) in zip(fps, fp_where)],
            "n_dets": len(dets), "n_dets_plausible": int(sum(hope_plausible(d) for d in dets)),
            "n_dets_split": int(sum(d.split > 0 for d in dets))}


def _hope_stats(v):
    v = np.asarray(v, float)
    if v.size == 0:
        return {"n": 0}
    return {"n": int(v.size), "median": round(float(np.median(v)), 2),
            "abs_median": round(float(np.median(np.abs(v))), 2),
            "abs_p95": round(float(np.percentile(np.abs(v), 95)), 2)}


def _hope_summarise(per_image: list[dict]) -> dict:
    rows = [r for s in per_image for r in s["rows"]]
    misses = [m for s in per_image for m in s["misses"]]
    nf = sum(s["n_faces"] for s in per_image)
    nfound = sum(s["n_found"] for s in per_image)
    kinds = {}
    for m in misses:
        kinds.setdefault(m["kind"], []).append(m)
    return {
        "n_faces": nf, "n_found": nfound, "recall": round(nfound / nf, 3) if nf else None,
        "err_long_mm": _hope_stats([r["err_long_mm"] for r in rows]),
        "err_short_mm": _hope_stats([r["err_short_mm"] for r in rows]),
        "err_long_vs_flat_mm": _hope_stats([r["err_long_flat_mm"] for r in rows]),
        "err_short_vs_flat_mm": _hope_stats([r["err_short_flat_mm"] for r in rows]),
        "centre_err_mm": _hope_stats([r["centre_mm"] for r in rows]),
        "normal_err_deg": _hope_stats([r["normal_deg"] for r in rows]),
        "matched_plausible_frac": round(float(np.mean([r["hope_plausible"] for r in rows])), 3) if rows else None,
        "n_false_pos": int(sum(len(s["fp"]) for s in per_image)),
        "false_pos_by_where": _hope_count([f["on"] for s in per_image for f in s["fp"]]),
        "false_pos_examples": [dict(f, scene=s["scene"], im=s["im"]) for s in per_image for f in s["fp"]][:8],
        "false_pos_per_image": round(sum(len(s["fp"]) for s in per_image) / max(len(per_image), 1), 2),
        "n_dets": int(sum(s["n_dets"] for s in per_image)),
        "miss_kinds": {k: {"n": len(v), "examples": v[:5]} for k, v in sorted(kinds.items(), key=lambda kv: -len(kv[1]))},
        "misses_all": misses,
        "recall_by_min_side": _hope_recall_by_side(rows, misses),
        "n_dets_split_by_seam": int(sum(s.get("n_dets_split", 0) for s in per_image)),
        "false_pos_all": [dict(f, scene=s["scene"], im=s["im"]) for s in per_image for f in s["fp"]],
        "per_object": _hope_per_object(per_image),
    }


def _hope_recall_by_side(rows, misses):
    """真の面の短辺で区切った再現率(小さい面ほど落ちるか)。"""
    bins = [(0, 30), (30, 45), (45, 60), (60, 300)]
    out = {}
    for lo, hi in bins:
        f = sum(lo <= r["true_sides_mm"][1] < hi for r in rows)
        m = sum(lo <= x["min_side_mm"] < hi for x in misses)
        out[f"{lo}-{hi}mm"] = {"found": f, "missed": m, "recall": round(f / (f + m), 3) if f + m else None}
    return out


def _hope_brief(s: dict) -> dict:
    return {"n_faces": s["n_faces"], "n_found": s["n_found"], "recall": s["recall"],
            "err_long_med": s["err_long_mm"].get("median"), "err_short_med": s["err_short_mm"].get("median"),
            "centre_med": s["centre_err_mm"].get("abs_median"), "normal_med": s["normal_err_deg"].get("abs_median"),
            "fp_per_image": s["false_pos_per_image"]}


def _hope_count(xs):
    out = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _hope_per_object(per_image):
    out = {}
    for s in per_image:
        for r in s["rows"]:
            o = out.setdefault(r["obj_id"], {"found": 0, "missed": 0, "err_long": [], "err_short": []})
            o["found"] += 1; o["err_long"].append(r["err_long_mm"]); o["err_short"].append(r["err_short_mm"])
        for m in s["misses"]:
            out.setdefault(m["obj_id"], {"found": 0, "missed": 0, "err_long": [], "err_short": []})["missed"] += 1
    return {str(k): {"found": v["found"], "missed": v["missed"],
                     "err_long_med_mm": round(float(np.median(v["err_long"])), 1) if v["err_long"] else None,
                     "err_short_med_mm": round(float(np.median(v["err_short"])), 1) if v["err_short"] else None}
            for k, v in sorted(out.items())}


# ===========================================================================
# 全体
# ===========================================================================
def hope_evaluate_hope(root: Path, max_images: int | None = None, seed: int = 0) -> dict:
    """HOPE val の全画像で、平らな面の検出と寸法を真値と照合する。

    Returns: dict(鍵は報告の末尾と ``__main__`` の表を参照)。
    """
    root = Path(root)
    t0 = time.perf_counter()
    models = hope_box_models(root, seed=seed)
    images = []
    for sd in sorted((root / "val").iterdir()):
        if not sd.is_dir():
            continue
        cams = json.loads((sd / "scene_camera.json").read_text())
        for k in sorted(cams, key=int):
            images.append((sd, int(k)))
    if max_images is not None:
        images = images[:max_images]
    per_mode = {m: [] for m in hope_DETECTORS}
    depth_ratio, depth_valid = [], []
    face_counts = {"facing": 0, "warped": 0, "eligible": 0, "occluded": 0}
    cross = []                          # 取り違え検査: 別シーンの真値で採点
    timing = {"segment": 0.0, **{m: 0.0 for m in hope_DETECTORS}}
    prev = None
    for sd, im in images:
        obs = hope_load_observation(sd, im)
        full_depth = np.asarray(Image.open(sd / "depth" / f"{im:06d}.png"), np.float64) / 1000.0 * \
            float(json.loads((sd / "scene_camera.json").read_text())[str(im)]["depth_scale"])
        faces, objlab = hope_load_truth(sd, im, models, full_depth)
        face_counts["facing"] += len(faces)
        face_counts["eligible"] += sum(f.eligible for f in faces)
        face_counts["occluded"] += sum(f.reason == "occluded" for f in faces)
        face_counts["warped"] += sum(f.reason == "warped" for f in faces)
        for f in faces:
            if f.eligible and np.isfinite(f.depth_ratio):
                depth_ratio.append(f.depth_ratio)
            if f.eligible:
                depth_valid.append(f.depth_valid)
        all_dets, tt = hope_detect_all(obs)              # ← 検出に渡すのは観測(深度・RGB・K)だけ
        for k, v in tt.items():
            timing[k] += v
        for m in hope_DETECTORS:
            dets = all_dets[m]
            sc = hope_score_image(dets, faces, obs.depth.shape, objlab)
            sc.update({"scene": int(sd.name), "im": im})
            per_mode[m].append(sc)
            if m == "depth":
                if prev is not None and prev[0] != int(sd.name):
                    cs = hope_score_image(dets, prev[1], obs.depth.shape)
                    cross.append((cs["n_found"], cs["n_faces"]))
                prev = (int(sd.name), faces)
        print(f"  {sd.name}/{im:06d}: faces {sum(f.eligible for f in faces)}  " +
              "  ".join(f"{m} {per_mode[m][-1]['n_found']}" for m in hope_DETECTORS), flush=True)
    # 反った面で外したもの(参考)
    for oid, mdl in models.items():
        face_counts.setdefault("warped_faces_by_obj", {})[str(oid)] = [
            f"{'xyz'[a]}{'+' if s > 0 else '-'}" for (a, s), fi in mdl["faces"].items() if fi["warp_m"] > hope_FACE_WARP_MAX]
    elapsed = time.perf_counter() - t0
    res = {
        "dataset": "HOPE val (BOP), 能動ステレオ式の深度カメラ; numbers only (CC BY-NC-SA 4.0 per dataset_info.md)",
        "n_images": len(images),
        "params": {"hope_DS": hope_DS, "BIL_SS": BIL_SS, "BIL_SR_m": BIL_SR, "hope_NRM_SMOOTH": hope_NRM_SMOOTH, "NB_px": hope_NB,
                   "STEP_m": hope_STEP_M, "hope_NRM_DEG": hope_NRM_DEG, "hope_EDGE_GROW": hope_EDGE_GROW, "PLANE_TOL_m": hope_PLANE_TOL, "hope_TUNING_SCENES": hope_TUNING_SCENES, "hope_MIN_PX": hope_MIN_PX, "hope_GROW_PX": hope_GROW_PX, "hope_SPLIT_DEG": hope_SPLIT_DEG, "hope_SPLIT_MAX": hope_SPLIT_MAX,
                   "SIDE_LO_HI_m": [SIDE_LO, SIDE_HI], "hope_RECT_MIN": hope_RECT_MIN, "MATCH_D_m": MATCH_D,
                   "MATCH_DEG": MATCH_DEG, "FACE_COS": FACE_COS, "VISIB_MIN": VISIB_MIN,
                   "FACE_VIS_MIN": FACE_VIS_MIN, "FACE_WARP_MAX_m": hope_FACE_WARP_MAX},
        "box_check": {str(k): {"within4mm": round(v["within4"], 3), "is_box": v["is_box"],
                               "size_mm": [round(float(x) * 1000, 1) for x in v["size"]]} for k, v in models.items()},
        "face_counts": face_counts,
        "depth_sanity": {"ratio_measured_over_true": _hope_stats(depth_ratio) | (
            {"p05": round(float(np.percentile(depth_ratio, 5)), 4), "p95": round(float(np.percentile(depth_ratio, 95)), 4),
             "median_exact": round(float(np.median(depth_ratio)), 4)} if depth_ratio else {}),
            "valid_depth_frac_on_faces": _hope_stats(depth_valid)},
        "cross_scene_check": {"found": int(sum(a for a, _ in cross)), "faces": int(sum(b for _, b in cross)),
                              "note": "検出(ある画像)を別シーンの真の面で採点した数。0 に近いはず"},
        "modes": {m: _hope_summarise(v) for m, v in per_mode.items()},
        "split_by_tuning": {m: {
            "tuning_scenes_1_2": _hope_brief(_hope_summarise([s for s in v if s["scene"] in hope_TUNING_SCENES])),
            "held_out_scenes_3_10": _hope_brief(_hope_summarise([s for s in v if s["scene"] not in hope_TUNING_SCENES]))}
            for m, v in per_mode.items()},
        "by_lighting": {m: {str(k): _hope_brief(_hope_summarise([s for s in v if s["im"] == k])) for k in range(5)}
                        for m, v in per_mode.items()},
        "by_scene": {m: {str(k): _hope_brief(_hope_summarise([s for s in v if s["scene"] == k])) for k in
                         sorted({s["scene"] for s in v})} for m, v in per_mode.items()},
        "per_image": {m: [{"scene": s["scene"], "im": s["im"], "n_faces": s["n_faces"], "n_found": s["n_found"],
                           "n_fp": len(s["fp"])} for s in v] for m, v in per_mode.items()},
        "matched_rows": {m: [r for s in v for r in s["rows"]] for m, v in per_mode.items()},
        "timing_s": {"total": round(elapsed, 1), **{f"detect_{m}": round(t, 1) for m, t in timing.items()},
                     "per_image_depth_only": round((timing["segment"] + timing["depth"]) / max(len(images), 1), 2),
                     },
    }
    return res


def _hope_print_table(res: dict) -> None:
    print()
    print(f"画像 {res['n_images']} 枚 / 対象面 {res['face_counts']['eligible']}"
          f"(カメラを向く面 {res['face_counts']['facing']}、遮られて外した {res['face_counts']['occluded']}、"
          f"模型の面が反っていて外した {res['face_counts']['warped']})")
    ds = res["depth_sanity"]["ratio_measured_over_true"]
    print(f"深度の検算: 実測/真 の中央値 {ds.get('median_exact')}(5–95 %: {ds.get('p05')}–{ds.get('p95')})")
    print(f"取り違え検査(別シーンの真値で採点): {res['cross_scene_check']['found']} / {res['cross_scene_check']['faces']}")
    hdr = ["方式", "再現率", "見つ/対象", "長辺誤差 中央(±)", "|長| 中央/95%", "短辺誤差 中央(±)", "|短| 中央/95%",
           "中心 中央/95%", "法線° 中央/95%", "誤検出(枚あたり)"]
    print(" | ".join(hdr))
    for m, s in res["modes"].items():
        L, S, C, N = s["err_long_mm"], s["err_short_mm"], s["centre_err_mm"], s["normal_err_deg"]
        print(" | ".join([m, f"{s['recall']}", f"{s['n_found']}/{s['n_faces']}",
                          f"{L.get('median')}", f"{L.get('abs_median')}/{L.get('abs_p95')}",
                          f"{S.get('median')}", f"{S.get('abs_median')}/{S.get('abs_p95')}",
                          f"{C.get('abs_median')}/{C.get('abs_p95')}", f"{N.get('abs_median')}/{N.get('abs_p95')}",
                          f"{s['n_false_pos']} ({s['false_pos_per_image']})"]))
    for m, s in res["modes"].items():
        print(f"[{m}] 平らな部分(ply)との差: 長 {s['err_long_vs_flat_mm'].get('median')} 短 {s['err_short_vs_flat_mm'].get('median')} mm")
        print(f"[{m}] 誤検出の場所: {s['false_pos_by_where']}")
        print(f"[{m}] 見逃しの内訳: " + ", ".join(f"{k} {v['n']}" for k, v in s["miss_kinds"].items()))
    for m, d in res["split_by_tuning"].items():
        print(f"[{m}] 調整に使った scene 1-2: {d['tuning_scenes_1_2']}")
        print(f"[{m}] 見ていない scene 3-10: {d['held_out_scenes_3_10']}")
    for m, d in res["by_lighting"].items():
        print(f"[{m}] 照明別の再現率: " + ", ".join(f"{k}:{v['recall']}" for k, v in d.items()))
    print("時間:", res["timing_s"])


hope_print_table = _hope_print_table


# ================================================================================================
# 図: 代表図(1 枚のパレットを 3 つのやり方で)・難しさの梯子・結果の表とグラフ・失敗の見本。
# ================================================================================================

RIGHT = tuple(fs.role_rgb8("right"))
WRONG = tuple(fs.role_rgb8("wrong"))
REF = tuple(fs.role_rgb8("neutral"))
EMPH = tuple(fs.role_rgb8("emphasis"))


def font(size, bold=False):
    p = figs._japanese_font_path(bold=bold)
    return ImageFont.truetype(str(p), size)


def project_rect(cx, cy, cz, yaw, l1, l2):
    """天面の矩形(世界)→ 画像の 4 隅。"""
    ca, sa = math.cos(yaw), math.sin(yaw)
    pts = []
    for a, b in ((l1, l2), (-l1, l2), (-l1, -l2), (l1, -l2)):
        x = cx + a * ca - b * sa
        y = cy + a * sa + b * ca
        zc = CAM_Z - cz
        pts.append((FX * x / zc + CX, FY * (-y) / zc + CY))
    return pts


def true_rect(b):
    c = footprint_corners(b)
    zc = CAM_Z - c[:, 2]
    return [(FX * x / z + CX, FY * (-y) / z + CY) for (x, y, _), z in zip(c, zc)]


def depth_rgb(depth, zlo=None, zhi=None):
    """深度 → 疑似カラー × 陰影(光を左上から当てた起伏)。欠測は黒。

    色の尺度は固定(パレットの上面〜上段の天面)。陰影は高さの勾配を 1 mm/px で飽和させて掛けるので、
    面の中の雑音・うねり(± 0.5 mm 程度)と継ぎ目の浅い溝が見える(色だけだと面ごとに一様な帯に見える)。
    """
    h = np.where(depth > 0, CAM_Z - depth, np.nan)
    zlo = PALLET_TOP if zlo is None else zlo
    zhi = 0.75 if zhi is None else zhi
    rgb = np.asarray(fs.colorize_depth(np.nan_to_num(h, nan=zlo), vmin=zlo, vmax=zhi), np.float64)[..., :3]
    hf = np.where(np.isfinite(h), h, np.nanmedian(h))
    gy, gx = np.gradient(hf)
    shade = 0.62 + 0.38 * np.clip((gx + gy) / 0.0014, -1, 1)
    rgb = rgb * shade[..., None]
    rgb[~np.isfinite(h)] = 0.0
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def overlay(rgb, scene_boxes, dets, match, show_truth=True):
    """検出(一致 = 役割 right、外れ = wrong)と空いている箱の真の天面(reference の細線)を重ねる。"""
    im = Image.fromarray(rgb).convert("RGB")
    dr = ImageDraw.Draw(im)
    if show_truth:
        for b in free_boxes(scene_boxes):
            dr.polygon(true_rect(b), outline=REF, width=2)
    ok = {p["det"] for p in match["pairs"]}
    for i, d in enumerate(dets):
        col = RIGHT if i in ok else WRONG
        dr.polygon(project_rect(d.cx, d.cy, d.cz, d.yaw, d.l1, d.l2), outline=col, width=5)
        u, v = project_rect(d.cx, d.cy, d.cz, 0, 0, 0)[0]
        dr.ellipse([u - 6, v - 6, u + 6, v + 6], fill=col)
    return np.asarray(im)


def band(img, text, sub="", h=64, size=30):
    """画像の上に見出しの帯(データの上に文字を置かない)。"""
    w = img.shape[1]
    bar = Image.new("RGB", (w, h), (24, 28, 34))
    dr = ImageDraw.Draw(bar)
    dr.text((14, 8), text, font=font(size, True), fill=(240, 242, 246))
    if sub:
        dr.text((14 + dr.textlength(text, font=font(size, True)) + 18, 16), sub, font=font(size - 8),
                fill=(190, 200, 210))
    return np.concatenate([np.asarray(bar), img], 0)


def resize(img, w):
    h = int(round(img.shape[0] * w / img.shape[1]))
    return np.asarray(Image.fromarray(img).resize((w, h), Image.LANCZOS))


def grid(panels, ncols, gap=8, bg=(255, 255, 255)):
    rows = [panels[i:i + ncols] for i in range(0, len(panels), ncols)]
    ph = max(p.shape[0] for p in panels)
    pw = max(p.shape[1] for p in panels)
    out = np.full((len(rows) * ph + (len(rows) - 1) * gap, ncols * pw + (ncols - 1) * gap, 3), bg, np.uint8)
    for r, row in enumerate(rows):
        for c, p in enumerate(row):
            y, x = r * (ph + gap), c * (pw + gap)
            out[y:y + p.shape[0], x:x + p.shape[1]] = p
    return out


def fig_overview(name, scene, rgb, depth, dets, matches, colour_source, caption, note=""):
    """代表図: 上段 = カラー・深度・真の天面・深度の段差、下段 = 深度の V 字・カラーだけ・カラーの溝・両方。"""
    w = 480
    free = free_boxes(scene.boxes)
    truth = Image.fromarray(rgb).convert("RGB")
    dr = ImageDraw.Draw(truth)
    for b in free:
        dr.polygon(true_rect(b), outline=EMPH, width=5)
    panels = [band(resize(rgb, w), "カラー", colour_source, size=26, h=52),
              band(resize(depth_rgb(depth), w), "深度", "陰影つき・黒 = 欠測", size=26, h=52),
              band(resize(np.asarray(truth), w), "真の天面", "空いている箱 %d 個" % len(free), size=26, h=52)]
    for m in ("depth", "vgroove", "color", "cseam", "fused"):
        pl = [d for d in dets[m] if plausible(d)]
        mt = matches[m]
        panels.append(band(resize(overlay(rgb, scene.boxes, pl, mt), w), MODE_JA[m],
                           "一致 %d / %d・外れ %d" % (mt["n_match"], mt["n_free"], mt["n_det"] - mt["n_match"]),
                           size=26, h=52))
    img = grid(panels, 4)
    head = Image.new("RGB", (img.shape[1], 70), (255, 255, 255))
    d = ImageDraw.Draw(head)
    d.text((16, 12), "混載パレットの天面: %s(%s)" % (CONDITION_JA[scene.condition], "天井の RGB-D、真下向き、種 0"),
           font=font(34, True), fill=(20, 20, 20))
    foot = Image.new("RGB", (img.shape[1], 46 + (40 if note else 0)), (255, 255, 255))
    d = ImageDraw.Draw(foot)
    d.text((16, 8), "太線: 検出(%s 一致 / %s 外れ)  細線: 空いている箱の真の天面  照合 = 矩形の IoU ≥ 0.5"
           % (fs.ROLE_MARKERS["right"], fs.ROLE_MARKERS["wrong"]), font=font(24), fill=(60, 60, 60))
    if note:
        d.text((16, 46), note, font=font(24, True), fill=tuple(int(c) for c in WRONG))
    out = np.concatenate([np.asarray(head), img, np.asarray(foot)], 0)
    figs.save(name, out, caption)


def fig_ladder(name, frames, stats, caption):
    """難しさの梯子: 5 条件のカラーと深度の切り出し(同じ範囲)と、深度だけ / 両方の再現率。"""
    cols = []
    v0, v1, u0, u1 = 120, 420, 240, 640              # 上段の中央付近(継ぎ目が写る範囲)
    for cond in CONDITIONS:
        rgb, depth = frames[cond]
        c = rgb[v0:v1, u0:u1]
        dd = depth_rgb(depth)[v0:v1, u0:u1]
        st = stats[cond]
        sub = "段差 %.0f / V 字 %.0f / 両方 %.0f %%" % (100 * st["depth"], 100 * st["vgroove"], 100 * st["fused"])
        col = np.concatenate([band(c, CONDITION_JA[cond], size=26, h=52),
                              np.full((6, c.shape[1], 3), 255, np.uint8), dd,
                              band(np.full((1, c.shape[1], 3), 255, np.uint8), sub, size=22, h=44)[:44]], 0)
        cols.append(col)
    img = grid(cols, 5, gap=10)
    head = Image.new("RGB", (img.shape[1], 64), (255, 255, 255))
    ImageDraw.Draw(head).text((14, 12), "難しさの順(左 → 右): 上 = カラー、下 = 深度(陰影つき、黒 = 欠測)、下の数 = 天面の再現率(種 10 本の中央値)",
                              font=font(30, True), fill=(20, 20, 20))
    figs.save(name, np.concatenate([np.asarray(head), img], 0), caption)


def fig_gallery(name, examples, caption):
    """失敗の見本: 結果の種類ごとに 1 コマ、取ろうとした矩形(太線)と真の天面(細線)。"""
    panels = []
    for ex in examples:
        rgb = ex["rgb"]
        im = Image.fromarray(rgb).convert("RGB")
        dr = ImageDraw.Draw(im)
        for b in ex["truth"]:
            dr.polygon(true_rect(b), outline=REF, width=2)
        d = ex["det"]
        col = RIGHT if ex["outcome"] == "success" else WRONG
        if d is not None:
            pts = project_rect(d["cx"], d["cy"], d["cz"], d["yaw"], d["l1"], d["l2"])
            dr.polygon(pts, outline=col, width=6)
            pad = project_rect(d["cx"], d["cy"], d["cz"], d["yaw"], PAD_L / 2, PAD_W / 2)
            dr.polygon(pad, outline=EMPH, width=4)
            uc = np.mean([p[0] for p in pts])
            vc = np.mean([p[1] for p in pts])
        else:
            uc, vc = CX, CY
        x0 = int(np.clip(uc - 210, 0, rgb.shape[1] - 420))
        y0 = int(np.clip(vc - 160, 0, rgb.shape[0] - 320))
        crop = np.asarray(im)[y0:y0 + 320, x0:x0 + 420]
        panels.append(band(crop, OUTCOME_JA[ex["outcome"]],
                           "%s・%s" % (CONDITION_JA[ex["cond"]], MODE_JA[ex["mode"]]), size=26, h=52))
    img = grid(panels, 3, gap=10)
    foot = Image.new("RGB", (img.shape[1], 44), (255, 255, 255))
    ImageDraw.Draw(foot).text((12, 8), "太線: 選んだ天面  四角: 吸着パッド 160 × 80 mm の位置  細線: 真の天面",
                              font=font(22), fill=(60, 60, 60))
    figs.save(name, np.concatenate([img, np.asarray(foot)], 0), caption)


# ---------------------------------------------------------------- 動画(Blender の斜めのコマ + 天井カメラの差し込み + 章カード・字幕)

#: 見出し(動画の題のカード・docstring と同じ主張。数字は全部回した実行の表から)。
HEADLINE_LINES = (
    "継ぎ目が詰まると、深度の段差では箱を分けられない",
    "深度の V 字の溝とカラーの暗い溝のどちらが勝つかは、天面の合わせ目の作りで入れ替わる",
    "同じ柄では、溝が深い(2 mm)とカラーの溝、すき間 1.5 mm・テープ無し・溝 1 mm 以下で V 字",
    "仮定: 縁の丸み 4 mm。合わせ目の作り(深さ・すき間・テープ)は外の根拠の無い作者の仮定",
)
#: 動画の題のカード(1 行を短く折る。中身は HEADLINE_LINES と同じ)
VIDEO_TITLE_LINES = (
    "継ぎ目が詰まると、深度の段差では箱を分けられない",
    "深度の V 字の溝とカラーの暗い溝の勝ち負けは、",
    "天面の合わせ目の作りで入れ替わる",
    "同じ柄では、合わせ目の溝が深い(2 mm)とカラーの溝、",
    "すき間 1.5 mm・テープ無し・溝 1 mm 以下で V 字が上",
    "仮定: 縁の丸み 4 mm。合わせ目の作りは外の根拠の無い作者の仮定",
)

COND_HARD = {
    "gap": "箱の間に 15〜30 mm の隙間。深度の段差で分かれる",
    "tight": "隙間 0〜2 mm。高さが揃うと深度の段差が消える",
    "same": "同じ箱・同じ印刷が詰めて並ぶ。カラーの柄も切れ目にならない",
    "shrink": "シュリンクフィルムの照り返しで深度が抜け、偽の点が出る",
    "crush": "天面のつぶれ(10〜28 mm)と傾き(4〜8°)。吸着が漏れる",
}


def _card(w, h, lines, sizes, colors=None):
    im = Image.new("RGB", (w, h), (20, 24, 30))
    dr = ImageDraw.Draw(im)
    y = int(h * 0.22)
    for i, (t, s) in enumerate(zip(lines, sizes)):
        f = font(s, i == 0)
        tw = dr.textlength(t, font=f)
        while tw > w - 48 and s > 14:                   # 画面の左右で切れないよう、収まるまで字を小さくする
            s -= 1
            f = font(s, i == 0)
            tw = dr.textlength(t, font=f)
        dr.text(((w - tw) / 2, y), t, font=f, fill=(colors[i] if colors else (236, 240, 244)))
        y += int(s * 1.6)
    return np.asarray(im)


def _subtitle(w, text, h=64):
    im = Image.new("RGB", (w, h), (12, 14, 18))
    ImageDraw.Draw(im).text((18, 14), text, font=font(26), fill=(240, 242, 246))
    return np.asarray(im)


def _inset(rgb, det, outcome, w=320):
    im = Image.fromarray(rgb).convert("RGB")
    dr = ImageDraw.Draw(im)
    if det is not None:
        col = RIGHT if outcome == "success" else WRONG
        dr.polygon(project_rect(det["cx"], det["cy"], det["cz"], det["yaw"], det["l1"], det["l2"]),
                   outline=col, width=8)
        dr.polygon(project_rect(det["cx"], det["cy"], det["cz"], det["yaw"], PAD_L / 2, PAD_W / 2),
                   outline=EMPH, width=6)
    a = resize(np.asarray(im), w)
    bar = Image.new("RGB", (w, 30), (12, 14, 18))
    ImageDraw.Draw(bar).text((8, 3), "天井カメラ・カラーの溝で選んだ天面", font=font(18), fill=(230, 230, 230))
    return np.concatenate([np.asarray(bar), a], 0)


def outcome_text(c):
    o = c["outcome"]
    ja = OUTCOME_JA[o]
    if o in ("success", "pose") and c.get("pos_err") is not None:
        return "%s(中心のずれ %.1f mm・向き %.1f°)" % (ja, 1000 * c["pos_err"], math.degrees(c["yaw_err"]))
    if o == "double":
        return "%s: パッドが 2 箱にまたがる → 人が直す" % ja
    if o == "drop":
        return "%s: 吸着が漏れる → 人が直す" % ja
    if o == "notfound":
        return "%s: 取れる箱の天面が無い(または箱でない面を選んだ)→ 人が直す" % ja
    return ja


def compose_video(name, root, stats, caption, colour_frame):
    """``root/video/<条件>/`` の Blender のコマと plan.json から動画を組む。足りなければ何もしない(None)。

    ロボットの型式とクレジットの文は plan.json(``tools/depal_video_run.py`` が書く)から読む。
    """
    import json as _json

    W, Hh = 960, 540
    frames = []
    plans = {}
    for cond in CONDITIONS:
        pj = Path(root) / "video" / cond / "plan.json"
        if not pj.is_file():
            return None
        plans[cond] = _json.loads(pj.read_text(encoding="utf-8"))
    fps = int(plans[CONDITIONS[0]]["fps"])
    robot = plans[CONDITIONS[0]].get("robot_model", "6 軸アーム")

    def hold(img, sec):
        frames.extend([img] * int(round(sec * fps)))

    def pct(c, m, key=""):
        return "%.0f%%" % (100 * stats[c][key + m])

    title = _card(W, Hh + 64, ["混載デパレタイズ"] + list(VIDEO_TITLE_LINES)
                  + ["天井の RGB-D → Fullseye の op で天面と吸着の位置 → %s が 1 個ずつ下ろす" % robot],
                  [50] + [24] * len(VIDEO_TITLE_LINES) + [20])
    hold(title, 3.0)
    for k, cond in enumerate(CONDITIONS):
        d = Path(root) / "video" / cond
        plan = plans[cond]
        card = _card(W, Hh + 64, ["条件 %d / 5: %s" % (k + 1, CONDITION_JA[cond]), COND_HARD[cond],
                                  "再現率(種 10 本)  段差 %s  V 字 %s  カラーだけ %s  カラーの溝 %s  両方 %s"
                                  % (pct(cond, "depth"), pct(cond, "vgroove"), pct(cond, "color"), pct(cond, "cseam"),
                                     pct(cond, "fused")),
                                  "成功率(種 10 本)  段差 %s  V 字 %s  カラーだけ %s  カラーの溝 %s  両方 %s"
                                  % (pct(cond, "depth", "s_"), pct(cond, "vgroove", "s_"), pct(cond, "color", "s_"),
                                     pct(cond, "cseam", "s_"), pct(cond, "fused", "s_"))],
                     [38, 24, 22, 22], [(255, 255, 255), (230, 200, 120), (200, 220, 240), (200, 220, 240)])
        hold(card, 2.0)
        for ci, c in enumerate(plan["cycles"]):
            if ci > 0 and c["outcome"] == "success":
                continue                                    # 失敗の無い条件は成功の手 1 つだけ(動画を 5 MB 以下に)
            ins = _inset(colour_frame(cond, tuple(c["key"])), c["det"], c["outcome"])
            for j in range(c["n_frames"]):
                if j / fps > c["t"]["t_release"] + 0.6:
                    break                                   # 戻りの動きは省く(動画を 5 MB 以下に)
                if j / fps < c["t"]["t_contact"] - 1.0:
                    continue                                # 待機から近づく前半も省く(同上)
                fi = c["frame_start"] + j
                f = d / ("vid_%05d.png" % fi)
                if not f.is_file():
                    return None
                img = np.asarray(Image.open(f).convert("RGB")).copy()
                img[10:10 + ins.shape[0], W - 10 - ins.shape[1]:W - 10] = ins
                t = j / fps
                if t >= c["t"]["t_contact"]:
                    sub = "%d 手目(%s): %s" % (c["step"] + 1, robot, outcome_text(c))
                else:
                    sub = "%d 手目: 撮る → 深度で面を切り、カラーの暗い溝の線で割る → 一番高い天面" % (c["step"] + 1)
                frames.append(np.concatenate([img, _subtitle(W, sub)], 0))
    credit = [x + "。" for x in plans[CONDITIONS[0]].get("robot_credit", "").split("。") if x.strip()]
    end = _card(W, Hh + 64, ["下ろした成功率(種 10 本、規則で判定)", "段差 / V 字 / カラーだけ / カラーの溝 / 両方"]
                + ["%s: %s / %s / %s / %s / %s" % (CONDITION_JA[c], pct(c, "depth", "s_"), pct(c, "vgroove", "s_"),
                                                  pct(c, "color", "s_"), pct(c, "cseam", "s_"), pct(c, "fused", "s_"))
                   for c in CONDITIONS]
                + ["描画: Blender Cycles"] + credit, [30, 22, 26, 26, 26, 26, 26, 18] + [16] * len(credit))
    hold(end, 6.0)
    figs.save_video(name, frames, caption=caption, fps=fps, gif_every=8, gif_width=360)
    return len(frames)


def fig_flap_map(name, fm, conds, cells, dips, gaps, tapes, tape_ja, caption):
    """合わせ目の地図: 条件ごとに、行 = (テープ, すき間)、列 = 合わせ目の溝の深さ。色 = カラーの溝 − V 字 の再現率。"""
    rows = [(t, g) for t in tapes for g in (gaps if t != "kraft" else (0.0,))]
    cw, ch, lw, top = 150, 64, 300, 60
    lut = np.asarray(fs.diverging_lut(256))
    panels = []
    for c in conds:
        w = lw + cw * len(dips)
        h = top + ch * len(rows) + 10
        im = Image.new("RGB", (w, h), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        dr.text((10, 8), CONDITION_JA[c], font=font(28, True), fill=(20, 20, 20))
        for j, d in enumerate(dips):
            dr.text((lw + j * cw + 18, 34), "溝 %.1f mm" % d, font=font(20), fill=(60, 60, 60))
        for i, (t, g) in enumerate(rows):
            y = top + i * ch
            dr.text((10, y + 18), "%s・すき間 %.1f mm" % (tape_ja[t], g), font=font(20), fill=(40, 40, 40))
            for j, d in enumerate(dips):
                v = fm[(c, (d, g, t), "vgroove")][0]
                cs = fm[(c, (d, g, t), "cseam")][0]
                diff = cs - v
                k = int(np.clip((diff * 0.5 + 0.5) * 255, 0, 255))
                col = tuple(int(255 * x) for x in np.clip(lut[k][:3], 0, 1))
                x0 = lw + j * cw
                dr.rectangle([x0 + 2, y + 2, x0 + cw - 2, y + ch - 2], fill=col)
                lum = 0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2]
                dr.text((x0 + 10, y + 18), "V %.2f / 色 %.2f" % (v, cs), font=font(19),
                        fill=(250, 250, 250) if lum < 110 else (15, 15, 15))
        panels.append(np.asarray(im))
    img = grid(panels, len(panels), gap=24)
    head = Image.new("RGB", (img.shape[1], 64), (255, 255, 255))
    ImageDraw.Draw(head).text((14, 12), "合わせ目の作りで勝つやり方が入れ替わる(V = 深度の V 字、色 = カラーの溝、種 3 本の中央)",
                              font=font(28, True), fill=(20, 20, 20))
    foot = Image.new("RGB", (img.shape[1], 44), (255, 255, 255))
    ImageDraw.Draw(foot).text((14, 8), "升目の色 = カラーの溝 − V 字 の再現率: 青 = カラーの溝が上、橙 = V 字が上、暗い = ほぼ同じ。",
                              font=font(22), fill=(60, 60, 60))
    figs.save(name, np.concatenate([np.asarray(head), img, np.asarray(foot)], 0), caption)


# ================================================================================================
# 章の組み立て・門・図(下書き。最後に 1 本の PoC へまとめる)。
# ================================================================================================

# ---------------------------------------------------------------- Blender の描画を差し込む

def renders_root() -> Path | None:
    """Blender の描画の置き場。``FULLSEYE_DEPAL_RENDERS`` か、作業場の ``data/fullseye_poc_real/depal_blender``。

    どちらにも無ければ None(数値の描画で代用。CI はこちら)。描画は ``tools/depal_blender_run.py`` で作る。
    """
    v = os.environ.get("FULLSEYE_DEPAL_RENDERS", "").strip()
    if v:
        return Path(v)
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        d = here.parent.parent / "data" / "fullseye_poc_real" / "depal_blender"
        if d.is_dir():
            return d
    return None


def blender_depth_check(root: Path, scene, depth_exact) -> dict | None:
    """Blender の深度(Z)と、この中の幾何の深度を比べる(同じ場面を 2 つの描画器で描いた照合)。"""
    f = root / (scene_dir_name(scene)) / ("depth_%s.npy" % frame_key(sorted(b.id for b in scene.boxes)))
    if not f.is_file():
        return None
    zb = np.load(str(f))
    ok = np.isfinite(depth_exact) & (zb < 100)
    d = (zb - depth_exact)[ok]
    return {"n": int(ok.sum()), "median_mm": 1000 * float(np.median(d)), "within_2mm": float(np.mean(np.abs(d) < 0.002))}


def scene_dir_name(scene) -> str:
    """描画の置き場の名前: 条件_種(合わせ目の地図の場面は名前を足す)。"""
    return "%s_%d%s" % (scene.condition, scene.seed, getattr(scene, "variant", ""))


def frame_key(key) -> str:
    return "_".join("%02d" % i for i in key)


class BlenderColor:
    """Blender が描いた 16 bit の sRGB を読み、撮像素子の雑音を足して 8 bit にする。無いコマは控える。

    ``on_missing``(既定 None)に関数を入れると、無いコマをその場で描かせる口になる
    (``tools/depal_blender_run.py`` が Blender の待ち受けにつなぐ。PoC 自身は Blender を呼ばない)。
    """

    on_missing = None

    def __init__(self, root: Path):
        self.root = root
        self.missing = {}
        self.used = 0

    def __call__(self, scene, key):
        import cv2

        d = self.root / (scene_dir_name(scene))
        f = d / ("rgb_%s.png" % frame_key(key))
        if not f.is_file() and BlenderColor.on_missing is not None:
            BlenderColor.on_missing(scene, tuple(key), f)
        a = cv2.imread(str(f), cv2.IMREAD_UNCHANGED) if f.is_file() else None
        if a is None:
            self.missing.setdefault(scene_dir_name(scene), set()).add(tuple(key))
            return None
        self.used += 1
        lin = srgb_to_linear(a[..., ::-1].astype(np.float64) / 65535.0)
        import hashlib

        h = hashlib.sha256(("blender/%s/%d/%s" % (scene.condition, scene.seed, tuple(key))).encode()).digest()
        return camera_sensor(lin, np.random.default_rng(int.from_bytes(h[:8], "little")))


# ---------------------------------------------------------------- 章

MODES = tuple(DETECTORS)
#: 閾値(VALLEY_MIN・SEAM_BH・STEP_M)を決めるのに見た場面の種 / 見ていない種。
TUNE_SEEDS = (0, 1, 2)
HELD_SEEDS = (3, 4, 5, 6, 7, 8, 9)
#: 深度の V 字の溝の閾値の掃引 [mm](決めた値 0.5 mm は種 0〜2 の場面を見てから置いた)。
VALLEY_SWEEP_MM = (0.2, 0.3, 0.5, 0.8, 1.0, 1.3, 1.6)
SWEEP_CONDS = ("tight", "same")
#: 天面の縁の丸み [mm] の掃引(溝の深さを作者が決めていることの開示)。数値の描画、深度だけの 2 通り。
EDGE_SWEEP_MM = (1.0, 2.0, 3.0, 4.0, 6.0)
EDGE_SEEDS = (0, 1, 2, 3, 4)


def run_scene(cond, seed, loop_steps, do_loop, root, want_fig, sweep=False):
    """1 枚のパレット: 最初のコマの検出(5 通り)と、1 個ずつ下ろす繰り返し。プロセスを分けて回せる形。"""
    provider = BlenderColor(root) if root else None
    src = FrameSource(make_scene(cond, seed), provider)
    rgb, depth, reason, buf = src.get(src.scene.boxes)
    out = {"cond": cond, "seed": seed, "n_boxes": len(src.scene.boxes), "static": {}, "logs": {},
           "dets": {}, "examples": {}, "sweep": {},
           "blender_depth": blender_depth_check(root, src.scene, buf.image(buf.z)) if root else None}
    for m in MODES:
        dets = DETECTORS[m](depth, rgb, K, CAM_Z)
        pl = [d for d in dets if plausible(d)]
        mt = match(pl, src.scene.boxes)
        out["static"][m] = {k: v for k, v in mt.items() if k != "pairs"}
        out["static"][m]["size_err"] = [q["size_err"] for q in mt["pairs"]]
        out["static"][m]["pos_err"] = [q["pos_err"] for q in mt["pairs"]]
        if want_fig:
            for d in pl:
                d.mask = None
            out["dets"][m] = (pl, mt)
        if do_loop and loop_steps:
            log = run_loop(src, m, max_steps=loop_steps)
            out["logs"][m] = log
            if want_fig:
                _collect_examples(out["examples"], src, cond, m, log)
    if sweep:
        base = VALLEY_MIN
        try:
            for v in VALLEY_SWEEP_MM:
                set_valley_min(v / 1000.0)
                for m in ("vgroove", "fused"):
                    pl = [d for d in DETECTORS[m](depth, rgb, K, CAM_Z) if plausible(d)]
                    mt = match(pl, src.scene.boxes)
                    out["sweep"][(m, v)] = (mt["n_match"], mt["n_free"])
        finally:
            set_valley_min(base)
    if want_fig:
        out["frame"] = (rgb, depth, src.scene)
    out["renders"] = src.renders
    out["blender_used"] = provider.used if provider else 0
    out["missing"] = {k: sorted(v) for k, v in provider.missing.items()} if provider else {}
    return out


#: 合わせ目の地図: 溝の深さ [mm] × 切り口のすき間 [mm] × テープ。クラフトテープはすき間を覆うので 0 mm だけ。
MAP_DIPS_MM = (0.2, 0.5, 1.0, 2.0)
MAP_GAPS_MM = (0.0, 0.5, 1.5)
MAP_TAPES = ("kraft", "clear", "none")
MAP_TAPE_JA = {"kraft": "クラフトテープ", "clear": "透明テープ", "none": "テープ無し"}
MAP_CONDS = ("tight", "same")
MAP_SEEDS = (3, 4, 5)
MAP_MODES = ("vgroove", "cseam", "fused")


def map_cells():
    """地図の升目(深さ, すき間, テープ)の並び。"""
    return [(d, g, t) for t in MAP_TAPES for g in (MAP_GAPS_MM if t != "kraft" else (0.0,)) for d in MAP_DIPS_MM]


def run_map(cond, seed, dip_mm, gap_mm, tape, root):
    """合わせ目の作りをそろえた場面の最初のコマ: やり方ごとの (一致, 空き, 外れ)。"""
    scene = make_scene(cond, seed, flap_map=(dip_mm / 1000.0, gap_mm / 1000.0, tape))
    src = FrameSource(scene, BlenderColor(root) if root else None)
    rgb, depth, _, _ = src.get(scene.boxes)
    out = {}
    for m in MAP_MODES:
        pl = [d for d in DETECTORS[m](depth, rgb, K, CAM_Z) if plausible(d)]
        mt = match(pl, scene.boxes)
        out[m] = (mt["n_match"], mt["n_free"], mt["n_det"] - mt["n_match"])
    missing = sum(len(v) for v in src.color_provider.missing.values()) if root else 0
    return cond, seed, (dip_mm, gap_mm, tape), out, missing


def chapter_map(root, workers):
    jobs = [(c, s, d, g, t, root) for c in MAP_CONDS for s in MAP_SEEDS for (d, g, t) in map_cells()]
    agg, miss = {}, 0
    for c, s, cell, out, mi in _pool(run_map, jobs, workers):
        miss += mi
        for m, (k, n, f) in out.items():
            agg.setdefault((c, cell, m), []).append((k / n if n else float("nan"), f))
    res = {k: (med([a for a, _ in v]), med([b for _, b in v])) for k, v in agg.items()}
    return res, miss


def run_edge(cond, seed, r_mm, flap=True):
    """縁の丸みを変えた場面(数値の描画、カラーを使わない 2 通り)の最初のコマの再現率。"""
    src = FrameSource(make_scene(cond, seed, edge_r=r_mm / 1000.0, flap=flap, bulge=flap), None)
    _, depth, _, _ = src.get(src.scene.boxes, need_rgb=False)
    out = {}
    for m in DEPTH_ONLY_MODES:
        pl = [d for d in DETECTORS[m](depth, None, K, CAM_Z) if plausible(d)]
        mt = match(pl, src.scene.boxes)
        out[m] = (mt["n_match"], mt["n_free"])
    return cond, seed, (r_mm if flap else -r_mm), out


def _pool(fn, jobs, workers):
    if workers > 1:
        import concurrent.futures as cf

        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(fn, *zip(*jobs)))
    return [fn(*j) for j in jobs]


def chapter_conditions(seeds, loop_seeds, loop_steps, root=None, loop_conds=None, workers=1, sweep=False):
    """5 条件 × seeds の場面を回して、条件ごとに束ねる。繰り返しは loop_seeds だけ。"""
    jobs = [(c, s, loop_steps, s in loop_seeds and (loop_conds is None or c in loop_conds), root, s == seeds[0],
             sweep and c in SWEEP_CONDS)
            for c in CONDITIONS for s in seeds]
    outs = _pool(run_scene, jobs, workers)
    res = {c: {m: {"static": [], "logs": [], "log_seeds": []} for m in MODES} for c in CONDITIONS}
    res["_examples"] = {}
    res["_missing"] = {}
    res["_blender_used"] = 0
    res["_sweep"] = {}
    for o in outs:
        c = o["cond"]
        for m in MODES:
            res[c][m]["static"].append(dict(o["static"][m], seed=o["seed"]))
            if m in o["logs"]:
                res[c][m]["logs"].append(o["logs"][m])
                res[c][m]["log_seeds"].append(o["seed"])
        res[c].setdefault("_n_boxes", []).append(o["n_boxes"])
        if "frame" in o:
            res[c]["_frame"] = o["frame"]
            res[c]["_dets"] = o["dets"]
        for k, v in o["examples"].items():
            res["_examples"].setdefault(k, v)
        for k, v in o["sweep"].items():
            res["_sweep"].setdefault((c,) + k, []).append(v)
        res["_missing"].update(o["missing"])
        res["_blender_used"] += o["blender_used"]
        if o["blender_depth"] is not None:
            res.setdefault("_blender_depth", []).append(o["blender_depth"])
    return res


def chapter_edge(workers):
    jobs = [(c, s, r, True) for c in SWEEP_CONDS for s in EDGE_SEEDS for r in EDGE_SWEEP_MM]
    jobs += [(c, s, EDGE_RADIUS * 1000, False) for c in SWEEP_CONDS for s in EDGE_SEEDS]   # 合わせ目・ふくらみ無し
    agg = {}
    for c, s, r, out in _pool(run_edge, jobs, workers):
        for m, v in out.items():
            agg.setdefault((c, m, r), []).append(v[0] / v[1])
    return {k: float(np.median(v)) for k, v in agg.items()}


def _collect_examples(ex, src, cond, mode, log):
    """失敗の見本: (やり方, 結果) ごとに最初の 1 コマ(カラーと、そのときの箱の真値)を控える。"""
    for rec in log:
        o = rec["outcome"]
        if (mode, o) in ex or (rec["det"] is None and o != "notfound"):
            continue
        boxes = [b for b in src.scene.boxes if b.id in set(rec["key"])]
        rgb = src.get(boxes, need_rgb=True)[0]
        ex[(mode, o)] = {"rgb": rgb.copy(), "det": rec["det"], "truth": free_boxes(boxes), "outcome": o,
                         "cond": cond, "mode": mode}


def success(res, cond, mode, seeds=None):
    """1 個ずつ下ろした成功率(seeds で種を絞る)。"""
    e = res[cond][mode]
    logs = [lg for lg, sd in zip(e["logs"], e["log_seeds"]) if seeds is None or sd in seeds]
    return summarize(logs)["success_rate"] if logs else float("nan")


def per_seed(entries, seeds=None, size=False):
    """種ごとの再現率(寸法つきなら寸法の誤差 ≤ SIZE_TOL の一致だけ)。"""
    out = []
    for e in entries:
        if seeds is not None and e["seed"] not in seeds:
            continue
        k = e["n_match_size"] if size else e["n_match"]
        out.append(k / e["n_free"] if e["n_free"] else float("nan"))
    return out


def med(v):
    return float(np.median(v)) if len(v) else float("nan")


def static_summary(entries, seeds=None):
    es = [e for e in entries if seeds is None or e["seed"] in seeds]
    r = per_seed(es)
    size = [x for e in es for x in e["size_err"]]
    pos = [x for e in es for x in e["pos_err"]]
    n_det = sum(e["n_det"] for e in es)
    n_match = sum(e["n_match"] for e in es)
    return {"n_free": sum(e["n_free"] for e in es), "n_det": n_det, "n_match": n_match,
            "recall": med(r), "recall_min": min(r) if r else float("nan"), "recall_max": max(r) if r else float("nan"),
            "recall_size": med(per_seed(es, size=True)),
            "false_med": med([e["n_det"] - e["n_match"] for e in es]),
            "precision": n_match / n_det if n_det else float("nan"),
            "pos_med_mm": 1000 * med(pos), "size_med_mm": 1000 * med(size)}


def gates(res, full: bool, held):
    """門(どれか外れたら止める)。値は同じ実行の値。主張は種の中央値で書き、門も中央値で。"""
    fails = []
    for cond in CONDITIONS:
        for m in MODES:
            if sum(e["n_free"] for e in res[cond][m]["static"]) < 5 * len(res[cond][m]["static"]):
                fails.append("%s/%s: 空いている箱が 1 枚あたり 5 個に満たない(採点にならない)" % (cond, m))
            if any(e["n_free"] < 3 for e in res[cond][m]["static"]):
                fails.append("%s/%s: 空いている箱が 3 個未満の場面がある" % (cond, m))
            for log, nb in zip(res[cond][m]["logs"], res[cond]["_n_boxes"]):
                removed = sum(len(r["removed"]) for r in log)
                if full and log and log[-1]["n_left"] - len(log[-1]["removed"]) == 0 and removed != nb:
                    fails.append("%s/%s: 下ろした箱 %d ≠ 積んだ箱 %d" % (cond, m, removed, nb))
    st = {(c, m): static_summary(res[c][m]["static"]) for c in CONDITIONS for m in MODES}
    # 隙間あり ≥ 0.85 は段差と両方に元からあった門(V 字は割りすぎるので入れない。カラーの溝は結果を見てから足した)
    for m in ("depth", "cseam", "fused"):
        if not st[("gap", m)]["recall"] >= 0.85:
            fails.append("隙間あり・%s の再現率 %.2f < 0.85(易しい条件で効かない)" % (m, st[("gap", m)]["recall"]))
    # 深度だけの主張(カラーを読まないので CI の代用カラーでも成り立つ): 深度の V 字 > 深度の段差
    for cond in ("tight", "same"):
        d, v = st[(cond, "depth")]["recall"], st[(cond, "vgroove")]["recall"]
        if not v > d:
            fails.append("%s: 深度の V 字 %.2f が深度の段差 %.2f を上回らない" % (cond, v, d))
        if held:
            dh = static_summary(res[cond]["depth"]["static"], held)["recall"]
            vh = static_summary(res[cond]["vgroove"]["static"], held)["recall"]
            if not vh > dh:
                fails.append("%s(見ていない種): 深度の V 字 %.2f が深度の段差 %.2f を上回らない" % (cond, vh, dh))
    if not full:
        return fails
    # カラーを使う主張(Blender のカラーでだけ確かめる。CI の代用カラーでは確かめていない)。
    # ★これらの門は、天面の合わせ目を入れた場面の結果を見てから置いた。全部の種と見ていない種 3〜9 の両方で確かめる。
    for seeds, tag in ((None, "全部の種"), (held, "見ていない種")):
        if seeds is not None and not seeds:
            continue
        rec = {(c, m): static_summary(res[c][m]["static"], seeds)["recall"] for c in ("tight", "same") for m in MODES}
        for cond in ("tight", "same"):
            c_, d_, cs = rec[(cond, "color")], rec[(cond, "depth")], rec[(cond, "cseam")]
            if not cs > d_:
                fails.append("%s(%s): カラーの溝 %.2f が深度の段差 %.2f を上回らない" % (cond, tag, cs, d_))
            if not c_ < cs:
                fails.append("%s(%s): カラーだけ %.2f がカラーの溝 %.2f を下回らない" % (cond, tag, c_, cs))
            sd, sc = success(res, cond, "depth", seeds), success(res, cond, "cseam", seeds)
            if not sc > sd:
                fails.append("%s(%s): 下ろす成功率 カラーの溝 %.2f が段差 %.2f を上回らない" % (cond, tag, sc, sd))
        # 継ぎ目が詰まる: カラーの溝は V 字より割りすぎない(外れの中央が少ない)
        fv = static_summary(res["tight"]["vgroove"]["static"], seeds)["false_med"]
        fc = static_summary(res["tight"]["cseam"]["static"], seeds)["false_med"]
        if not fc < fv:
            fails.append("tight(%s): カラーの溝の外れ %.1f が V 字の外れ %.1f より少なくない" % (tag, fc, fv))
        # 合わせ目で割りすぎる: 同じ柄では深度の V 字だけがカラーの溝を下回る
        if not rec[("same", "vgroove")] < rec[("same", "cseam")]:
            fails.append("same(%s): 深度の V 字 %.2f がカラーの溝 %.2f を下回らない(合わせ目で割りすぎる、の主張)"
                         % (tag, rec[("same", "vgroove")], rec[("same", "cseam")]))
    return fails


def print_map(fm):
    print("== 合わせ目の地図(%s、種 %s の中央): 再現率 / 外れ 件/枚  V 字 | カラーの溝 | 両方 ==" % (
        "・".join(CONDITION_JA[c] for c in MAP_CONDS), ",".join(map(str, MAP_SEEDS))))
    for c in MAP_CONDS:
        for cell in map_cells():
            d, g, t = cell
            print("  %-8s %-8s 溝 %.1f mm すき間 %.1f mm: " % (CONDITION_JA[c][:6], MAP_TAPE_JA[t], d, g)
                  + "  ".join("%.2f/%.1f" % fm[(c, cell, m)] for m in MAP_MODES))


def map_gates(fm):
    """合わせ目の地図の門(結果を見てから置いた。種 3 本の中央。入れ替わりが本当に地図の中にあるかを確かめる)。"""
    fails = []
    deep = fm[("same", (2.0, 0.0, "kraft"), "cseam")][0], fm[("same", (2.0, 0.0, "kraft"), "vgroove")][0]
    if not deep[0] > deep[1]:
        fails.append("地図: 合わせ目 2 mm・クラフトテープでカラーの溝 %.2f が V 字 %.2f を上回らない" % deep)
    open_ = fm[("same", (1.0, 1.5, "none"), "vgroove")][0], fm[("same", (1.0, 1.5, "none"), "cseam")]
    if not (open_[0] > open_[1][0] and open_[1][1] > 0):
        fails.append("地図: すき間 1.5 mm・テープ無しで V 字 %.2f がカラーの溝 %.2f を上回らない(か外れが 0)"
                     % (open_[0], open_[1][0]))
    shallow = fm[("same", (0.5, 0.0, "kraft"), "vgroove")][0], fm[("same", (0.5, 0.0, "kraft"), "cseam")][0]
    if not shallow[0] >= shallow[1]:
        fails.append("地図: 合わせ目 0.5 mm・すき間なしで V 字 %.2f がカラーの溝 %.2f を下回る" % shallow)
    return fails


def write_map_figures(fm):

    if not fm or not figs.enabled():
        return
    header = ["条件", "テープ", "すき間 mm", "合わせ目の溝 mm"] + ["%s 再現率 / 外れ" % MODE_JA[m] for m in MAP_MODES]
    rows = []
    for c in MAP_CONDS:
        for cell in map_cells():
            d, g, t = cell
            rows.append([CONDITION_JA[c], MAP_TAPE_JA[t], "%.1f" % g, "%.1f" % d]
                        + ["%.2f / %.1f" % fm[(c, cell, m)] for m in MAP_MODES])
    figs.save_table("flap_seam_map_table", header, rows,
                    title="合わせ目の作り × やり方(Blender のカラー、種 %s の中央)" % ",".join(map(str, MAP_SEEDS)),
                    caption="天面の合わせ目の溝の深さ・切り口のすき間・テープを全部の箱でそろえた場面の再現率と外れ。")
    fig_flap_map("flap_seam_map", fm, MAP_CONDS, map_cells(), MAP_DIPS_MM, MAP_GAPS_MM, MAP_TAPES, MAP_TAPE_JA,
                   "どの作りならどのやり方が勝つか: 升目の色 = カラーの溝 − 深度の V 字 の再現率(数字は両者)。")


def print_tables(res, held, sweep, edge):
    print("== 最初のコマ(空いている箱の天面、IoU ≥ 0.5)。再現率は種ごとの値の中央値 [最小〜最大] ==")
    print("%-10s %-8s %22s %8s %8s %8s %6s %8s" % ("条件", "やり方", "全部の種", "決めた種", "見ない種", "寸法つき", "外れ", "寸法mm"))
    for cond in CONDITIONS:
        for m in MODES:
            s = static_summary(res[cond][m]["static"])
            t = static_summary(res[cond][m]["static"], TUNE_SEEDS)
            h = static_summary(res[cond][m]["static"], held) if held else {"recall": float("nan")}
            print("%-10s %-8s %8.2f [%.2f〜%.2f] %8.2f %8.2f %8.2f %6.1f %8.1f" % (
                CONDITION_JA[cond], MODE_JA[m], s["recall"], s["recall_min"], s["recall_max"], t["recall"],
                h["recall"], s["recall_size"], s["false_med"], s["size_med_mm"]))
    if sweep:
        print("== 深度の V 字の閾値(VALLEY_MIN)の掃引: 再現率の中央値(種 %d 本) ==" % len(next(iter(sweep.values()))))
        for v in VALLEY_SWEEP_MM:
            print("  %.1f mm: " % v + "  ".join("%s/%s %.2f" % (CONDITION_JA[c][:4], MODE_JA[m], med([a / b for a, b in sweep[(c, m, v)]]))
                                            for c in SWEEP_CONDS for m in ("vgroove", "fused")))
    if edge:
        print("== 縁の丸み(数値の描画、種 %d 本): 再現率の中央値 ==" % len(EDGE_SEEDS))
        for r in list(EDGE_SWEEP_MM) + [-EDGE_RADIUS * 1000]:
            print("  %s: " % ("%.0f mm" % r if r > 0 else "%.0f mm 合わせ目なし" % -r)
                  + "  ".join("%s/%s %.2f" % (CONDITION_JA[c][:4], MODE_JA[m], edge[(c, m, r)])
                              for c in SWEEP_CONDS for m in DEPTH_ONLY_MODES))
    loop_seeds = sorted({e["seed"] for c in CONDITIONS for m in MODES for e in res[c][m]["static"]})
    print("== 1 個ずつ下ろす(結果の数、回した種 %s。縮小版は「同じ柄」だけ 2 手) ==" % ",".join(map(str, loop_seeds)))
    print("%-10s %-8s " % ("条件", "やり方") + " ".join("%6s" % OUTCOME_JA[k][:4] for k in OUTCOMES) + "   成功率")
    for cond in CONDITIONS:
        for m in MODES:
            if not res[cond][m]["logs"]:
                continue                                  # 縮小版では回していない条件
            s = summarize(res[cond][m]["logs"])
            print("%-10s %-8s " % (CONDITION_JA[cond], MODE_JA[m])
                  + " ".join("%6d" % s["counts"][k] for k in OUTCOMES) + "   %.2f" % s["success_rate"])


def write_figures(res, colour_source, held, sweep, edge):

    if not figs.enabled():
        return
    rgb, depth, scene = res["same"]["_frame"]
    dets = {m: res["same"]["_dets"][m][0] for m in MODES}
    mts = {m: res["same"]["_dets"][m][1] for m in MODES}
    v_all = per_seed(res["same"]["vgroove"]["static"])
    v0 = [e for e in res["same"]["vgroove"]["static"] if e["seed"] == 0][0]
    note = ("★この種 0 は深度の V 字に有利な種: V 字 %d / %d(10 種の中央 %.2f)。種 0 は閾値を決めた種でもある。"
            % (v0["n_match"], v0["n_free"], med(v_all)))
    fig_overview("overview_same_pattern", scene, rgb, depth, dets, mts, colour_source,
                   "同じ柄の箱が詰めて並んだパレット(種 0)を、5 通りの手がかりで切り分けた天面。種 0 は V 字に有利な種"
                   "(図の下の注)。", note)
    frames = {c: res[c]["_frame"][:2] for c in CONDITIONS}
    stats = {c: {m: static_summary(res[c][m]["static"])["recall"] for m in MODES} for c in CONDITIONS}
    fig_ladder("difficulty_ladder", frames, stats, "5 つの条件(難しい順)のカラーと深度(陰影つき)、天面の再現率(種 10 本の中央値)。")
    header = ["条件", "やり方", "全部の種 中央 [最小〜最大]", "決めた種 0〜2", "見ていない種 3〜9", "寸法つき(±20 mm)",
              "外れ 件/枚", "寸法の誤差 mm"]
    rows = []
    for c in CONDITIONS:
        for m in MODES:
            s = static_summary(res[c][m]["static"])
            t = static_summary(res[c][m]["static"], TUNE_SEEDS)
            h = static_summary(res[c][m]["static"], held)
            rows.append([CONDITION_JA[c], MODE_JA[m], "%.2f [%.2f〜%.2f]" % (s["recall"], s["recall_min"], s["recall_max"]),
                         "%.2f" % t["recall"], "%.2f" % h["recall"], "%.2f" % s["recall_size"], "%.1f" % s["false_med"],
                         "%.1f" % s["size_med_mm"]])
    figs.save_table("first_frame_recall", header, rows, title="最初のコマの天面の再現率(Blender のカラー、条件ごとに種 10 本)",
                    caption="種ごとの再現率の中央値と幅。閾値は種 0〜2 を見て決め、種 3〜9 は見ていない。")
    header = ["条件", "やり方"] + [OUTCOME_JA[k] for k in OUTCOMES] + ["成功率", "決めた種 0〜2", "見ていない種 3〜9"]
    rows = []
    for c in CONDITIONS:
        for mo in MODES:
            s = summarize(res[c][mo]["logs"])
            rows.append([CONDITION_JA[c], MODE_JA[mo]] + [str(s["counts"][k]) for k in OUTCOMES]
                        + ["%.2f" % s["success_rate"], "%.2f" % success(res, c, mo, TUNE_SEEDS),
                           "%.2f" % success(res, c, mo, held)])
    figs.save_table("outcomes", header, rows, title="1 個ずつ下ろした結果(種 10 本、規則で判定)",
                    caption="結果の数。成否は規則(パッドの足跡・天面の凹凸・モーメント比・可搬)で判定した。")
    xs = list(range(1, len(CONDITIONS) + 1))
    series = [(MODE_JA[mo], xs, [summarize(res[c][mo]["logs"])["success_rate"] for c in CONDITIONS])
              for mo in MODES]
    figs.save_plot("success_rate", series, xlabel="条件(1 隙間あり → 5 つぶれ・傾き)", ylabel="成功率",
                   title="1 個ずつ下ろした成功率(種 10 本)", ylim=(0, 1.05),
                   caption="1 個ずつ下ろしたときの成功率(条件ごと、5 通り)。")
    header = ["深度の V 字の閾値"] + ["%s・%s" % (CONDITION_JA[c], MODE_JA[m]) for c in SWEEP_CONDS for m in ("vgroove", "fused")]
    rows = [["%.1f mm%s" % (v, "(採用)" if abs(v / 1000 - VALLEY_MIN) < 1e-9 else "")]
            + ["%.2f" % med([a / b for a, b in sweep[(c, m, v)]]) for c in SWEEP_CONDS for m in ("vgroove", "fused")]
            for v in VALLEY_SWEEP_MM]
    figs.save_table("valley_threshold_sweep", header, rows, title="閾値の掃引(再現率の中央値、種 10 本、Blender のカラー)",
                    caption="採用した 0.5 mm は種 0〜2 の場面を見てから置いた。1.3 mm から上では V 字が効かない。")
    header = ["縁の丸み"] + ["%s・%s" % (CONDITION_JA[c], MODE_JA[m]) for c in SWEEP_CONDS for m in DEPTH_ONLY_MODES]
    rows = [["%.0f mm%s" % (r, "(既定)" if abs(r / 1000 - EDGE_RADIUS) < 1e-9 else "")]
            + ["%.2f" % edge[(c, m, r)] for c in SWEEP_CONDS for m in DEPTH_ONLY_MODES] for r in EDGE_SWEEP_MM]
    r0 = EDGE_RADIUS * 1000
    rows.append(["%.0f mm・合わせ目とふくらみ無し" % r0]
                + ["%.2f" % edge[(c, m, -r0)] for c in SWEEP_CONDS for m in DEPTH_ONLY_MODES])
    figs.save_table("edge_radius_sweep", header, rows, title="天面の縁の丸みと合わせ目(数値の描画、種 5 本、深度だけ)",
                    caption="継ぎ目の V 字の溝は縁の丸みが作る。丸みが小さいと深度の V 字は効かない。最後の行は天面の合わせ目とふくらみを外した場面。")
    root = renders_root()
    if root is not None:
        vstats = {c: dict(stats[c], **{"s_" + mo: summarize(res[c][mo]["logs"])["success_rate"] for mo in MODES})
                  for c in CONDITIONS}
        bc = BlenderColor(root)

        def colour_frame(cond, key):
            img = bc(make_scene(cond, 0), key)
            if img is None:
                raise RuntimeError("動画の差し込みのコマが無い: %s %s" % (cond, key))
            return img

        n = compose_video("depal_robot_video", root, vstats,
                            "条件ごとに、ロボットが「カラーの溝」のやり方で選んだ天面を吸って下ろす手(成功と失敗)と、天井カメラの差し込み。",
                            colour_frame)
        print("動画のコマ数: %s" % n)
    ex = res.get("_examples", {})
    want = [("fused", "success"), ("fused", "double"), ("fused", "drop"), ("fused", "overload"),
            ("depth", "double"), ("color", "notfound")]
    picks = [ex[k] for k in want if k in ex]
    if picks:
        fig_gallery("failure_gallery", picks, "結果の種類ごとの見本(両方の成功・失敗と、他のやり方の典型の失敗)。")


#: HOPE の誤検出の場所の呼び名(合計は誤検出の件数に一致する)。
FP_WHERE_JA = {"background": "背景", "non_box_object": "箱でない物", "scored_box": "採点した箱の別の面",
               "box_low_visib": "隠れの多い箱"}


#: HOPE(BOP)の取得物の SHA-256(2026-11-08 に Hugging Face の bop-benchmark/hope から取得、tools/fetch_hope_bop.py)。
HOPE_ZIPS = {
    "hope_base.zip": "fb3bf622e1cc873af2fecb676420a639967bf1f97f8e37d96503a64ac02b0be7",
    "hope_models.zip": "b92d47db20fc98c8f54ea42754ca1b5db123f7ed99aa9b9aca3ed0409160385d",
    "hope_val_realsense.zip": "25c75bb2daad4ad7e143b3f8d5bdff793fadb65463492792e822dbb36245a49f",  # 出典表示(配布元のファイル名)
}
#: 出典表示(配布元の文言を逐語で引用)。同梱の dataset_info.md と BOP の配布ページで食い違うので、厳しい NC に倒す。
HOPE_CREDIT = ("HOPE: S. Tyree, J. Tremblay, T. To, J. Cheng, T. Mosier, J. Smith, S. Birchfield, "
               "'6-DoF Pose Estimation of Household Objects for Robotic Manipulation: An Accessible Dataset "
               "and Benchmark', IROS 2022 (BOP format, https://bop.felk.cvut.cz/datasets/)")
HOPE_LICENSE_BUNDLED = ("Copyright (C) 2020 NVIDIA Corporation. All rights reserved. Licensed under the "  # 出典表示
                        "CC BY-NC-SA 4.0 license (https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode).")
HOPE_LICENSE_BOP = "license: CC BY-SA 4.0 (https://bop.felk.cvut.cz/datasets/)"
#: HOPE の門(全 50 枚の結果 0.705 / 5.6 mm / 2.6° / 43 件を見てから置いた。結果に対して余裕は小さく取った)。
HOPE_GATE = {"recall_min": 0.68, "long_abs_med_max_mm": 6.5, "normal_med_max_deg": 3.5, "fp_per_image_max": 50.0}


def hope_root() -> Path | None:
    """HOPE の置き場(``FULLSEYE_HOPE_DATA`` か、作業場の ``data/fullseye_poc_real/hope_bop``)。zip の SHA-256 を照合する。"""
    v = os.environ.get("FULLSEYE_HOPE_DATA", "").strip()
    if v:
        root = Path(v)
    else:
        here = Path(__file__).resolve().parents[1]
        if here.parent.name.lower() != "projects":
            return None
        root = here.parent.parent / "data" / "fullseye_poc_real" / "hope_bop"
    if not (root / "val").is_dir():
        return None
    for name, sha in HOPE_ZIPS.items():
        f = root / "zips" / name
        if not f.is_file():
            raise realdata.RealDataError("HOPE の取得物が無い: %s(tools/fetch_hope_bop.py)" % f)
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        if h.hexdigest() != sha:
            raise realdata.RealDataError("HOPE の %s の SHA-256 が台帳と違う" % name)
    return root


def chapter_hope(fails):
    """実データの章: 能動ステレオ式の深度カメラの実深度で、平面 → 矩形の寸法を BOP の真値で採点する(数値だけ)。"""
    root = hope_root()
    if root is None:
        print("実データの章(HOPE): データが無いので回さない(tools/fetch_hope_bop.py で取得)")
        return None
    realdata.mark_read("hope_bop:val")
    print("出典:", HOPE_CREDIT)
    print("ライセンス(同梱 dataset_info.md):", HOPE_LICENSE_BUNDLED)
    print("ライセンス(BOP の配布ページ):", HOPE_LICENSE_BOP, "→ 厳しい方(非商用)に倒し、数値だけを出す")
    res = hope_evaluate_hope(root)
    hope_print_table(res)
    s = res["modes"]["depth"]
    if res["n_images"] != 50:
        fails.append("HOPE の画像が %d 枚(50 枚のはず)" % res["n_images"])
    if res["cross_scene_check"]["found"] != 0:
        fails.append("HOPE: 別シーンの真値で %d 面が当たった(照合が甘い)" % res["cross_scene_check"]["found"])
    if sum(s["false_pos_by_where"].values()) != s["n_false_pos"]:
        fails.append("HOPE: 誤検出の内訳の合計 %d が件数 %d と合わない" % (sum(s["false_pos_by_where"].values()), s["n_false_pos"]))
    g = HOPE_GATE
    if not (s["recall"] >= g["recall_min"] and s["err_long_mm"]["abs_median"] <= g["long_abs_med_max_mm"]
            and s["normal_err_deg"]["abs_median"] <= g["normal_med_max_deg"]
            and s["false_pos_per_image"] <= g["fp_per_image_max"]):
        fails.append("HOPE: 再現率 %.3f・長辺の誤差 %.1f mm・法線 %.1f°・誤検出 %.1f 件/枚 のどれかが門を外れた"
                     % (s["recall"], s["err_long_mm"]["abs_median"], s["normal_err_deg"]["abs_median"],
                        s["false_pos_per_image"]))
    return res


def write_hope_table(res):
    if res is None or not figs.enabled():
        return
    s = res["modes"]["depth"]
    held = res["split_by_tuning"]["depth"]["held_out_scenes_3_10"]
    rows = [["画像 / 対象の面", "%d 枚 / %d 面" % (res["n_images"], s["n_faces"])],
            ["再現率(見つかった面)", "%.3f(%d 面)" % (s["recall"], s["n_found"])],
            ["再現率(閾値を決めるのに見なかった scene 3〜10)", "%s" % held["recall"]],
            ["長辺の誤差 中央(符号つき)/ |誤差| 中央 / 95 %", "%s / %s / %s mm" % (
                s["err_long_mm"]["median"], s["err_long_mm"]["abs_median"], s["err_long_mm"]["abs_p95"])],
            ["短辺の誤差 中央(符号つき)/ |誤差| 中央 / 95 %", "%s / %s / %s mm" % (
                s["err_short_mm"]["median"], s["err_short_mm"]["abs_median"], s["err_short_mm"]["abs_p95"])],
            ["中心の誤差 中央 / 95 %", "%s / %s mm" % (s["centre_err_mm"]["abs_median"], s["centre_err_mm"]["abs_p95"])],
            ["法線の誤差 中央 / 95 %", "%s / %s °" % (s["normal_err_deg"]["abs_median"], s["normal_err_deg"]["abs_p95"])],
            ["誤検出(件 / 枚)", "%s" % s["false_pos_per_image"]],
            ] + [["  誤検出の内訳: %s" % FP_WHERE_JA.get(k, k), "%d 件" % v]
                 for k, v in sorted(s["false_pos_by_where"].items(), key=lambda kv: -kv[1])] + [
            ["深度の検算(実測 / 真、中央)", "%s" % res["depth_sanity"]["ratio_measured_over_true"].get("median_exact")]]
    rows.append(["支える範囲", "実深度で平面 → 矩形の寸法がこの程度、まで"])
    rows.append(["支えない範囲", "継ぎ目で割る主張(HOPE は卓上の玩具の箱)"])
    figs.save_table("hope_real_depth", ["量(HOPE、能動ステレオ式の深度カメラの実深度、数値だけ)", "値"], rows,
                    title="実データの章: 平面 → 矩形の寸法を BOP の真値で採点",
                    caption="HOPE の箱型の物体の面を、同じ op の組(切り分けと閾値は別実装)で測った結果。画像は NC のため出さない。",
                    )


def main():
    full = os.environ.get("FULLSEYE_DEPAL_FULL", "") == "1"
    iterating = os.environ.get("FULLSEYE_DEPAL_ALLOW_MISSING") == "1"
    seeds = TUNE_SEEDS + HELD_SEEDS if full else (0,)
    held = HELD_SEEDS if full else ()
    loop_steps = 60 if full else 2
    root = renders_root()
    workers = min(15, max(1, (os.cpu_count() or 2) - 2)) if full else 1
    t0 = time.time()
    res = chapter_conditions(seeds, seeds, loop_steps, root, None if full else ("same",),
                             workers, sweep=full)
    edge = chapter_edge(workers) if full and not iterating else {}
    flapmap, map_missing = chapter_map(root, workers) if full and not iterating else ({}, 0)
    print_tables(res, held, res["_sweep"], edge)
    if flapmap:
        print_map(flapmap)
    fails = gates(res, full, held)
    if flapmap:
        fails += map_gates(flapmap)
        if map_missing:
            fails.append("合わせ目の地図の Blender のコマが %d 枚足りない" % map_missing)
    if not full:
        print("★縮小版(CI): 主張の門は深度だけの主張(深度の V 字 > 深度の段差、種 0 の 1 枚)と、隙間ありの最低線"
              "(段差・カラーの溝・両方 ≥ 0.85)だけ。カラーを使うやり方の比べ合い(カラーの溝 > 段差、カラーだけ < カラーの溝、"
              "V 字 < カラーの溝)は、代用のカラーでは逆転しうるので確かめていない。")
    # 実データの章は全部を回すときだけ(Blender のコマを揃える繰り返しの途中では回さない)
    hope = chapter_hope(fails) if full and not iterating else None
    missing = res["_missing"]
    n_missing = sum(len(v) for v in missing.values())
    if root is not None:
        print("Blender のコマ %d 枚、足りないコマ %d 枚" % (res["_blender_used"], n_missing))
        if os.environ.get("FULLSEYE_DEPAL_MISSING"):        # 描画の道具だけが置き場を渡す(PoC は既定で何も書かない)
            Path(os.environ["FULLSEYE_DEPAL_MISSING"]).write_text(json.dumps(missing), encoding="utf-8")
        if full and n_missing and not iterating:
            fails.append("Blender の描画が %d コマ足りない(数値の描画で代用した)" % n_missing)
        for bd in res.get("_blender_depth", []):
            if not (abs(bd["median_mm"]) < 0.5 and bd["within_2mm"] >= 0.9):
                fails.append("Blender の深度が幾何と合わない(中央 %.2f mm、2 mm 以内 %.3f)"
                             % (bd["median_mm"], bd["within_2mm"]))
        bds = res.get("_blender_depth", [])
        if bds:
            print("Blender の深度と幾何の深度(カメラの合わせの検算): %d 枚、2 mm 以内 %.3f〜%.3f"
                  % (len(bds), min(b["within_2mm"] for b in bds), max(b["within_2mm"] for b in bds)))
    if full and not n_missing and not iterating:
        write_figures(res, "Blender Cycles で描画" if root is not None else "数値の描画(代用)", held,
                      res["_sweep"], edge)
        write_hope_table(hope)
        write_map_figures(flapmap)
    print("経過 %.0f 秒" % (time.time() - t0))

    errors = figs.errors()
    if errors:
        fails.append("図の書き出しで失敗: " + "; ".join(errors))
    if fails:
        raise SystemExit("門を通らなかった: " + "; ".join(fails))
    print("PASS")


if __name__ == "__main__":
    main()
