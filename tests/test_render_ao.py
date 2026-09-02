# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""環境光遮蔽(AO)の焼き込みと、それを支えるラスタライザの属性出力の検証。

この族はこれまで**単体テストが 1 本も無かった**(検証は examples_3d/render_ao.py の
自己チェックだけ)。2026-09-02 に記事の hero 画像でまだら模様が見つかり、原因が
「頂点 AO を最近傍 3 頂点の逆距離重みで混ぜていたこと」だと切り分けられたので、
同じ壊れ方を二度と通さないための回帰テストをここに置く。

まだら模様は **粗い面ほど強く出る**(頂点間の距離が大きいほど逆距離重みが
三角形の内側から外れる)ので、テストは意図的に**粗い平面**を使う。
細かいメッシュで試すと差が消えて通ってしまう ―― 乱数入力で対称性の破れが
隠れるのと同じ形の見落としになる。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render3d  # noqa: E402
import render_ao  # noqa: E402


def _quad_grid(n: int, half: float = 1.0, z: float = 0.0):
    """z 平面上の n×n セル格子(頂点 (n+1)^2)。粗さを n で直接指定できる。"""
    xs = np.linspace(-half, half, n + 1)
    X, Y = np.meshgrid(xs, xs, indexing="ij")
    V = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], axis=1)
    F = []
    for i in range(n):
        for j in range(n):
            a = i * (n + 1) + j
            F.append([a, a + 1, a + n + 2])
            F.append([a, a + n + 2, a + n + 1])
    return V, np.asarray(F, np.int64)


# --------------------------------------------------------------------------- #
# ラスタライザの属性出力(三角形 id + 透視補正重心座標)                        #
# --------------------------------------------------------------------------- #
def test_attributes_are_opt_in():
    """既定では face/bary を返さない。影パスは 512x512 を 6 回叩いて depth しか
    読まないので、常時確保すると誰も使わないメモリを毎回払うことになる。"""
    V, F = _quad_grid(2)
    plain = render3d.render_mesh(V, F, pose=np.eye(4), width=16, height=16)
    assert set(plain) == {"depth", "silhouette", "normals"}
    rich = render3d.render_mesh(V, F, pose=np.eye(4), width=16, height=16,
                                attributes=True)
    assert set(rich) == {"depth", "silhouette", "normals", "face", "bary"}


def test_barycentric_weights_reconstruct_depth_exactly():
    """重心座標が**透視補正済み**であることの検算。

    スクリーン空間の重心座標をそのまま使うとアフィン補間にしかならず、
    傾いた面ほど誤差が大きくなる ―― 地面は視線に対して寝ているので、
    まさにそこが一番効く。頂点の深度を重みで混ぜて実際の深度に一致すれば、
    同じ重みで混ぜた**任意の**頂点量も同じ精度で正しい。
    """
    V = np.array([[-1.0, -1.0, -3.0], [1.0, -1.0, -3.0], [0.0, 1.0, -6.0]])
    F = np.array([[0, 1, 2]])
    r = render3d.render_mesh(V, F, pose=np.eye(4), width=64, height=64,
                             attributes=True)
    m = r["silhouette"] > 0
    assert m.any()
    bw = r["bary"][m]
    assert abs(float(bw.sum(axis=1).max()) - 1.0) < 1e-12
    assert abs(float(bw.sum(axis=1).min()) - 1.0) < 1e-12
    depth_v = -V[:, 2]
    got = np.einsum("ij,ij->i", bw, depth_v[F[r["face"][m]]])
    assert float(np.abs(got - r["depth"][m]).max()) < 1e-12


def test_background_face_is_minus_one():
    """背景は「どの三角形でもない」を -1 で言う。0 で埋めると 0 番の三角形と
    区別がつかず、下流が背景に本物の頂点量を焼き込んでも例外にならない。"""
    V, F = _quad_grid(1, half=0.2)
    r = render3d.render_mesh(V, F, pose=np.eye(4), width=32, height=32,
                             attributes=True)
    bg = r["silhouette"] == 0
    assert bg.any()
    assert int(r["face"][bg].max()) == -1


# --------------------------------------------------------------------------- #
# AO の焼き込み                                                                #
# --------------------------------------------------------------------------- #
def _ao_of_coarse_plane_under_a_box():
    """粗い地面 + その上の箱。地面の AO は箱の直下が暗く、外側ほど明るい。"""
    Vg, Fg = _quad_grid(6, half=3.0, z=0.0)          # 7x7 頂点 = わざと粗い
    # 地面の上に浮かせた小さな板(遮蔽物)
    Vb, Fb = _quad_grid(1, half=0.7, z=0.9)
    V = np.vstack([Vg, Vb])
    F = np.vstack([Fg, Fb + len(Vg)])
    pose, K = render3d.auto_view(V, margin=1.1, width=96, height=96)
    ao = render_ao.ambient_occlusion(V, F, pose=pose, intrinsics=K,
                                     width=96, height=96, n_dirs=32)
    return ao


def test_ao_on_a_coarse_surface_has_no_polygonal_cells():
    """粗い面でも AO 場が滑らかであること(まだら模様の回帰テスト)。

    最近傍 k 頂点の逆距離重みだと、頂点の疎な格子が**多角形のセル**になって
    現れる。セルの境界では値が折れるので、隣り合う画素の差に**飛び**が立つ。

    ここで測るのは **同じ地面の上で隣り合う 2 画素**の差だけ。最初は画像の
    内側を一律に見て失敗したが、原因は補間ではなく**測り方**だった ――
    地面の上に浮かぶ板の縁は本物の不連続(別の面)なので、そこを一緒に数えると
    どんな補間でも 100% の飛びが出る。面が変わる境目は除いて数える。
    """
    ao, face, n_ground_faces = _ao_of_coarse_plane_under_a_box()
    span = float(ao.max() - ao.min())
    assert span > 0.05, f"AO に濃淡が無い(遮蔽が効いていない): span={span}"
    ground = (face >= 0) & (face < n_ground_faces)
    pair = ground[:, :-1] & ground[:, 1:]            # 左右とも地面の画素対
    assert pair.sum() > 200, "地面の画素対が少なすぎて判定にならない"
    d = np.abs(np.diff(ao, axis=1))[pair]
    jump = float(d.max()) / span
    assert jump < 0.15, (
        f"地面の上で隣り合う画素の AO 差が値域の {jump:.0%} に達している "
        "= 補間が折れている(最近傍逆距離のセル境界の症状)")


def test_ao_is_interpolated_within_the_covering_triangle():
    """画素の AO が、**その画素を覆っている三角形の 3 頂点**の値の内側に入る。

    これは最近傍補間との決定的な違い。逆距離重みは近くにある**別の三角形**の
    頂点(極端には隣接する別物体の頂点)を拾いうるので、覆っている三角形の
    値の範囲を平気で外れる。重心補間なら凸結合なので構造的に外れない。
    """
    Vg, Fg = _quad_grid(4, half=2.0, z=0.0)
    Vb, Fb = _quad_grid(1, half=0.6, z=0.8)
    V = np.vstack([Vg, Vb])
    F = np.vstack([Fg, Fb + len(Vg)])
    pose, K = render3d.auto_view(V, margin=1.1, width=80, height=80)
    ao = render_ao.ambient_occlusion(V, F, pose=pose, intrinsics=K,
                                     width=80, height=80, n_dirs=24)
    view = render3d.render_mesh(V, F, pose, K, 80, 80, attributes=True)
    ao_v = render_ao.vertex_occlusion(V, F, n_dirs=24)
    m = view["silhouette"] > 0
    tri = ao_v[F[view["face"][m]]]                   # (n, 3) 覆う三角形の頂点値
    got = ao[m]
    assert np.all(got >= tri.min(axis=1) - 1e-12)
    assert np.all(got <= tri.max(axis=1) + 1e-12)


def test_ao_does_not_leak_across_disconnected_parts():
    """離れた 2 つの物体の間で AO が混ざらない。

    最近傍 k 頂点は「3 次元で近い」だけを見るので、接している / すれ違って
    いる別部品の頂点を平気で拾う。ここでは **一様に露出した板** と
    **深く遮蔽された板** を並べ、露出側の画素が遮蔽側の値へ引きずられて
    いないことを見る。
    """
    # 露出側: 単独の板(遮るものが無い)
    Va, Fa = _quad_grid(2, half=0.5, z=0.0)
    Va = Va + np.array([-2.0, 0.0, 0.0])
    # 遮蔽側: 板を 2 枚重ねて下面を暗くする
    Vb, Fb = _quad_grid(2, half=0.5, z=0.0)
    Vb = Vb + np.array([2.0, 0.0, 0.0])
    Vc, Fc = _quad_grid(2, half=0.5, z=0.25)
    Vc = Vc + np.array([2.0, 0.0, 0.0])
    V = np.vstack([Va, Vb, Vc])
    F = np.vstack([Fa, Fb + len(Va), Fc + len(Va) + len(Vb)])
    pose, K = render3d.auto_view(V, margin=1.05, width=96, height=96)
    ao = render_ao.ambient_occlusion(V, F, pose=pose, intrinsics=K,
                                     width=96, height=96, n_dirs=24)
    view = render3d.render_mesh(V, F, pose, K, 96, 96, attributes=True)
    face = view["face"]
    n_fa = len(Fa)
    lone = (face >= 0) & (face < n_fa)               # 単独の板の画素
    assert lone.any()
    # 単独の板は遮るものが無いので、どの画素もほぼ完全露出
    assert float(ao[lone].min()) > 0.9, (
        f"遮るものが無い板の AO が {ao[lone].min():.3f} まで落ちている "
        "= 別部品の遮蔽が漏れている")


def test_ao_rejects_a_degenerate_view():
    """fail-closed: 不正なカメラは黙って通さない。"""
    V, F = _quad_grid(2)
    with pytest.raises(ValueError):
        render_ao.ambient_occlusion(V, F, pose=np.eye(3), intrinsics=np.eye(3),
                                    width=16, height=16)
    with pytest.raises(ValueError):
        render_ao.ambient_occlusion(V, F, width=0, height=16)
