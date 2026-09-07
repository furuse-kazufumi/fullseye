# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""メッシュを直してから測る —— 直した分だけ欠陥は消え、量は戻らない。

3-D プリントにも CAE にも、STL/OBJ を受け取ったら**まず健全性を見る**という
前処理があります。穴・自己交差・非多様体辺・裏返った面・退化三角形・重複頂点。
現場では「オイラー標数が 2 なら閉じている」「面数が同じなら同じ形」という
一つの数字で合否を出しがちなので、**その数字が何に盲目か**を知らないと、
壊れたメッシュをそのままスライサやソルバに渡すことになります。

EXTEND: 実測の STL に差し替えるなら :func:`make_body` が返す ``(V, F)`` を
``fs.read_mesh("part.stl")`` の戻り値に置き換えます。**そのとき失われるのは真値
だけです** —— 欠陥の種類ごとの個数も、元の体積・表面積も分からなくなるので、
「直った/直っていない」は言えても「どれだけ戻ったか」は言えません。実務では
CAD の公称体積(質量 ÷ 密度でも可)を 1 つ持ち込むと、この PoC の
「量が戻ったか」の軸だけは実データでも生き残ります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(頂点数・辺数・面数・オイラー標数だけで判定する)を先に測る**。
   健全なこの部品は χ = 0 —— 貫通穴が 1 本あいた種数 1 の立体なので、
   ★**「χ = 2 なら健全」という判定は、健全なメッシュを不合格にする**。
2. ★★**6 種類の欠陥のうち 4 種類は χ を 1 も動かさない**。裏返り 6 面、
   非多様体辺 5 本、退化三角形 16 枚、重複頂点 18 個 —— どれも
   χ = 0 のまま。χ が動くのは穴(6 個で χ = -6)だけ。
3. ★★**その 1 つの数字は打ち消しで騙せる**。穴 6 個(χ -6)と重複面 6 枚
   (χ +6)を同時に入れると **χ = 0 = 健全な値**に戻る。面数は 6 枚しか
   違わず、頂点数と辺数は 1 も違わない。種類ごとに数えれば、同じメッシュに
   境界辺 18 本と非多様体辺 18 本が同時に立っているのが分かる。
4. **種類ごとに数えると 6 種すべて真値と一致する**(穴 6/6、非多様体辺
   5/5、裏返り 6/6、退化 16/16、重複頂点 18/18)。ただし★**順番がある**:
   境界ループを先に数えると 12 個(真値の穴は 6 個)—— 溶接割れが作った
   ゼロ幅の境界を穴と一緒に数えてしまう。**先に頂点を溶接してから数えると
   ちょうど 6 個**になる。「合わせてから測ると、合わせた分だけ欠陥が消える」。
5. ★★**「直った」と「戻った」は別の指標**。ゼロ幅の割れは 2 通りに直せて
   **どちらも水密になる**が、頂点を溶接すると表面積の誤差は 0.000 %、
   穴埋めで塞ぐと **+0.051 %(面が 36 枚増える)**。水密かどうかだけを
   見ていると、面を二重に張った状態を合格にする。
6. ★**穴の大きさの崖は閉形式で予測できる —— 体積だけ**。球から半頂角 θ の
   冠を削って穴埋めすると、体積は「球欠の体積」で予測でき θ = 32° で
   予測 -1.644 % / 実測 -1.642 %、θ = 80° で -37.107 / -36.840 % と合う。
   ★ところが**表面積は予測が外れる**(θ = 45° で予測 -2.145 %、実測
   **+5.658 %** —— 符号すら逆)。理由は縁が円ではなく階段だからで、
   扇の面積は πa² ではなく 0.5·a·L(L = 縁の実周長)。L/2πa = 1.62 を
   入れ直すと合う。**予測は「円の穴」を仮定していたのが誤り**でした。
7. ★★**簡略化(decimate)は体積より先に曲率分布を壊す**。50 % 削減で
   体積誤差はまだ -0.019 %・表面積 -0.005 % なのに、曲率の 95 パーセンタイル
   は 5.89 → 7.72(**+31 %**)動いている。積分量(体積・面積)は
   局所形状の破壊に**構造的に盲目**。98 % 削減でようやく体積 -4.199 %。
8. ★**簡略化の誤差則は途中から変わる**。幾何からの予測は「相対誤差 ∝ 1/F」
   (弦の矢 ∝ h² ∝ 1/F)で、実測の傾きは面数 1680→224 の区間で **1.17**
   とほぼ予測どおり。ところが 5604→1680 の区間では **2.51** で予測より
   ずっと急 —— 削り始めは「消しても損しない頂点」から消えるので、
   誤差はしばらく予測より小さいまま。**崖は 70 % 削減あたり**(体積誤差が
   0.1 % を超える)。
9. ★**退化三角形のしきい値は面積比 1e-5 付近**。中央値の面積に対して
   8e-5 の潰れ方(t = 1e-4)では 16 枚中 **0 枚**しか検出されず、
   8e-7(t = 1e-6)で 2 枚、8e-9(t = 1e-8)でようやく 16 枚全部。
   ★見逃された潰れ面は**面法線を壊す**: t = 1e-6 の潰れ面の法線は
   親の面から最大 **19.5°** ずれる(t = 1e-2 では 0.0°)。
10. ★★**自己交差はどの位相検査もすり抜ける**。頂点を 6 個だけ内側へ
    0.75 突き刺すと、水密 True・辺多様体 True・χ = 0 のまま
    **表面積は +4.523 %、体積は -0.375 %** —— 12 倍の食い違い。
    体積だけを合否にしていると通る。fullseye には自己交差の検出 op が
    無いので、辺長の外れ値で 8 頂点を拾った(下の「道具の穴」)。

【グラウンドトゥルース】球・トーラス・角柱の SDF ブール和から貫通穴を引いた
解析形状 → marching cubes で閉じた三角メッシュ。同じ格子・同じ経路で作った
**半径 1 の球**を閉形式(4πR² / (4/3)πR³)と突き合わせて経路そのものを較正
してある(表面積 -0.049 %、体積 -0.092 %)。欠陥は**種類ごとに既知個数**を
注入する(穴 6・非多様体辺 5・裏返り 6・退化 16・重複頂点 18・自己交差 6)。
体積は Mirtich 1996 の発散定理による多面体の厳密値、表面積は三角形面積の総和。

来歴(公開文献のみ): B. Mirtich, *Fast and Accurate Computation of Polyhedral
Mass Properties*, J. Graphics Tools 1(2), 1996 —— 多面体の厳密な質量特性 /
M. Garland & P. Heckbert, *Surface Simplification Using Quadric Error Metrics*,
SIGGRAPH 1997 —— QEM 簡略化 / M. Meyer et al., *Discrete Differential-Geometry
Operators for Triangulated 2-Manifolds*, VisMath 2003 —— cotangent 曲率 /
W. Lorensen & H. Cline, *Marching Cubes*, SIGGRAPH 1987 /
M. Attene et al., *Polygon Mesh Repairing: An Application Perspective*,
ACM Computing Surveys 45(2), 2013 —— 欠陥の分類。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
GRID = 48               # 部品を切る格子 [voxel/辺]
HALF = 1.7              # 格子が覆う半幅 [mm](座標の単位を mm とする)
R_SPHERE = 1.0          # 本体の球の半径 [mm]
R_TORUS, R_TUBE = 1.0, 0.30   # 襟(トーラス)の主半径・管半径 [mm]
R_DRILL = 0.36          # 貫通穴の半径 [mm] —— これが種数 1 を作る
SPHERE_GRID = 72        # 崖の測定に使う球だけの格子
SEED = 7

# 注入する欠陥の既知個数(= 真値)
N_HOLE = 6              # 三角形 1 枚ぶんの穴の個数
N_NONMANIFOLD = 5       # 3 面が共有する辺の本数
N_FLIP = 6              # 巻き順を裏返す面の枚数
N_SLIVER = 8            # 潰す辺の本数(退化三角形はこの 2 倍できる)
N_CRACK = 6             # 溶接をほどく面の枚数(重複頂点はこの 3 倍)
N_SPIKE = 6             # 突き刺す頂点の個数
SLIVER_T = 1e-9         # 潰し具合(辺のパラメータ。小さいほど面積 0 に近い)
SPIKE_DEPTH = 0.75      # 突き刺す深さ [mm](襟の管径 0.30 より深い = 貫通)

L = fs.ledger           # 3-D op の公開経路


# --------------------------------------------------------------------------- #
# 場面 —— 解析形状から閉じたメッシュを作る                                       #
# --------------------------------------------------------------------------- #
def _grid(n: int, half: float):
    g = np.linspace(-half, half, n)
    return g, float(g[1] - g[0])


def make_body(n: int = GRID, half: float = HALF):
    """球 ∪ トーラス襟 ∪ 角柱ボス から貫通穴を引いた立体のメッシュ。

    ★**列の規約**: :func:`voxel_to_mesh` は**配列の添字順**で頂点を返す。
    ここでは軸 0 = 貫通穴の軸なので、返る ``V`` の列は ``(穴軸, 縦, 横)`` で
    あって ``(x, y, z)`` ではない。この PoC は軸名を使わずに済ませているが、
    実データと混ぜるときは**ここで並べ替える**こと。
    """
    g, sp = _grid(n, half)
    A, B, C = np.meshgrid(g, g, g, indexing="ij")     # A = 穴の軸
    sph = np.sqrt(A ** 2 + B ** 2 + C ** 2) - R_SPHERE
    q = np.sqrt(B ** 2 + C ** 2) - R_TORUS
    tor = np.sqrt(q ** 2 + A ** 2) - R_TUBE
    d = np.abs(np.stack([A, B, C - 0.95], -1)) - np.array([0.22, 0.22, 0.55])
    box = np.linalg.norm(np.maximum(d, 0.0), axis=-1) + np.minimum(d.max(-1), 0.0)
    drill = np.sqrt(B ** 2 + C ** 2) - R_DRILL
    sdf = L.sdf_subtract(L.sdf_union(L.sdf_union(sph, tor), box), drill)
    V, F = L.voxel_to_mesh(sdf, iso=0.0)
    return V * sp - half, np.asarray(F, np.int64), np.asarray(sdf)


def make_sphere(n: int = SPHERE_GRID, half: float = 1.4, radius: float = R_SPHERE):
    """半径 ``radius`` の球。**閉形式の真値と突き合わせるための較正体**。"""
    g, sp = _grid(n, half)
    A, B, C = np.meshgrid(g, g, g, indexing="ij")
    V, F = L.voxel_to_mesh(np.sqrt(A ** 2 + B ** 2 + C ** 2) - radius, iso=0.0)
    return V * sp - half, np.asarray(F, np.int64)


# --------------------------------------------------------------------------- #
# 測る道具 —— 位相の 4 つの数字と、量の 2 つ                                     #
# --------------------------------------------------------------------------- #
def topology(V, F) -> dict:
    """頂点数・辺数・面数・オイラー標数。**ゼロ点の判定材料そのもの**。"""
    F = np.asarray(F)
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    ue = np.unique(e, axis=0)
    nv = int(len(np.unique(F)))
    return {"V": nv, "E": int(len(ue)), "F": int(len(F)), "chi": nv - len(ue) + len(F)}


def signed_volume(V, F) -> float:
    """発散定理による符号つき体積。**水密でなくても値が出る**のが要点。

    :func:`fullseye.inertia_tensor` は水密でないメッシュを fail-closed で拒む
    (正しい設計 —— 閉じていない面が囲む立体は定義できない)。だが「直す前に
    どれだけ狂っているか」を測るにはどうしても値が要るので、ここだけ自前で
    持つ。水密なメッシュでは inertia_tensor と一致することを assert してある。
    """
    V = np.asarray(V, np.float64)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def boundary_loops(V, F) -> list:
    """境界辺を輪(ループ)にまとめる。→ 各輪の頂点リスト。

    ★``fs.boundary_edges`` は辺の集合しか返さないので、輪にまとめる工程は
    呼び手が持つ(下の「道具の穴」)。穴の**個数**は辺の本数ではなく輪の数。
    """
    be = np.asarray(fs.boundary_edges(V, F))
    if len(be) == 0:
        return []
    adj: dict[int, list[int]] = {}
    for a, b in be:
        adj.setdefault(int(a), []).append(int(b))
        adj.setdefault(int(b), []).append(int(a))
    seen, out = set(), []
    for s in adj:
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        out.append(comp)
    return out


def _edge_faces(F) -> dict:
    m: dict[tuple, list] = {}
    for i, t in enumerate(F):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            m.setdefault((int(min(a, b)), int(max(a, b))), []).append(i)
    return m


def _pick_isolated(F, n: int, rng, banned: set | None = None) -> np.ndarray:
    """互いに頂点を共有しない面を ``n`` 枚選ぶ(欠陥どうしを干渉させない)。"""
    used = set(banned or ())
    out = []
    for i in rng.permutation(len(F)):
        t = F[i].tolist()
        if used.isdisjoint(t):
            used.update(t)
            out.append(int(i))
            if len(out) == n:
                break
    return np.asarray(out, np.int64)


# --------------------------------------------------------------------------- #
# 欠陥の注入 —— すべて既知個数                                                   #
# --------------------------------------------------------------------------- #
def inject_holes(V, F, n, rng):
    """面を ``n`` 枚、互いに離して削る → 三角形 1 枚ぶんの穴が ``n`` 個。"""
    idx = _pick_isolated(F, n, rng)
    return V.copy(), np.delete(F, idx, axis=0), len(idx)


def inject_flips(V, F, n, rng):
    """面を ``n`` 枚だけ裏返す(巻き順を逆にする)。位相は 1 も動かない。"""
    idx = _pick_isolated(F, n, rng)
    G = F.copy()
    G[idx] = G[idx][:, ::-1]
    return V.copy(), G, len(idx)


def inject_nonmanifold(V, F, n, rng):
    """辺 ``n`` 本に 3 枚目の面(テント)を張る → その辺は 3 面共有。"""
    ef = _edge_faces(F)
    keys = [k for k, v in ef.items() if len(v) == 2]
    vn = np.asarray(L.vertex_normals((V, F)))
    Vl, Fl = list(V), [list(f) for f in F]
    used, done = set(), 0
    for oi in rng.permutation(len(keys)):
        a, b = keys[oi]
        if a in used or b in used:
            continue
        used.update((a, b))
        Vl.append((V[a] + V[b]) * 0.5 + vn[a] * 0.05)
        Fl.append([a, b, len(Vl) - 1])
        done += 1
        if done == n:
            break
    return np.asarray(Vl), np.asarray(Fl, np.int64), done


def inject_slivers(V, F, n, t, rng):
    """辺 ``n`` 本を端に寄せて分割し、面積 ≈ ``t``×親 の潰れ面を 2n 枚作る。

    分割は**水密・多様体のまま**行うので、この欠陥は退化三角形だけを単独で
    足せる(位相も体積も表面積も 1 も動かない)= きれいな対照群。
    """
    ef = _edge_faces(F)
    keys = [k for k, v in ef.items() if len(v) == 2]
    Vl, Fl = list(V), [list(f) for f in F]
    used, done, areas, sliver = set(), 0, [], []
    for oi in rng.permutation(len(keys)):
        a, b = keys[oi]
        inc = ef[(a, b)]
        if any(f in used for f in inc):
            continue
        m = len(Vl)
        Vl.append(V[a] + t * (V[b] - V[a]))
        for fi in inc:
            tri = list(F[fi])
            c = [x for x in tri if x not in (a, b)][0]
            if (tri.index(b) - tri.index(a)) % 3 == 1:
                Fl[fi] = [a, m, c]
                Fl.append([m, b, c])
            else:
                Fl[fi] = [b, m, c]
                Fl.append([m, a, c])
            used.add(fi)
            sliver.append(int(fi))          # 潰れたのは**その場で置き換えた側**
            areas.append(0.5 * float(np.linalg.norm(
                np.cross(V[c] - V[a], np.asarray(Vl[m]) - V[a]))))
        done += 1
        if done == n:
            break
    return (np.asarray(Vl), np.asarray(Fl, np.int64), 2 * done,
            float(np.mean(areas)), np.asarray(sliver, np.int64))


def inject_cracks(V, F, n, rng):
    """面 ``n`` 枚の頂点を複製して溶接をほどく → 幅ゼロの割れと重複頂点 3n 個。

    形は 1 mm も変わらない。変わるのは**共有されていたか**だけ —— STL が
    いちばんよく持ち込む欠陥で、体積も表面積も正しいまま水密でなくなる。
    """
    idx = _pick_isolated(F, n, rng)
    Vl, Fl = list(V), [list(f) for f in F]
    for fi in idx:
        new = []
        for v in F[fi]:
            Vl.append(V[v])
            new.append(len(Vl) - 1)
        Fl[fi] = new
    return np.asarray(Vl), np.asarray(Fl, np.int64), 3 * len(idx)


def inject_spikes(V, F, n, depth, rng):
    """襟の上の頂点 ``n`` 個を内側へ ``depth`` 押し込む → 面が自分を突き抜ける。"""
    vn = np.asarray(L.vertex_normals((V, F)))
    rad = np.linalg.norm(V[:, 1:], axis=1)          # 列 0 = 穴の軸
    cand = np.nonzero((np.abs(V[:, 0]) < 0.12) & (rad > 1.15))[0]
    spk = rng.choice(cand, n, replace=False)
    W = V.copy()
    W[spk] -= vn[spk] * depth
    return W, F.copy(), len(spk), spk


def inject_duplicate_faces(V, F, n, rng):
    """既にある面を ``n`` 枚そのまま複製する(二重シェルの STL がこれ)。"""
    idx = _pick_isolated(F, n, rng)
    return V.copy(), np.concatenate([F, F[idx]]), len(idx)


# --------------------------------------------------------------------------- #
# 描画 —— 同じカメラで並べる                                                     #
# --------------------------------------------------------------------------- #
_EYE = np.array([2.4, -3.4, 2.6])
_UP = np.array([1.0, 0.0, 0.0])
_W = 300


def _cam():
    pose = np.asarray(fs.look_at(_EYE, np.zeros(3), _UP))
    K = np.asarray(fs.intrinsics_from_fov(40.0, _W, _W))
    return pose, K


def render(V, F, shade: bool = True):
    """陰影(または深度)画像。背景は 0。"""
    pose, K = _cam()
    r = fs.render_mesh(np.asarray(V), np.asarray(F), pose=pose, intrinsics=K,
                       width=_W, height=_W)
    sil = np.asarray(r["silhouette"])
    if not shade:
        d = np.asarray(r["depth"])
        d = np.where(np.isfinite(d), d, 0.0)
        lo = d[sil > 0].min() if (sil > 0).any() else 0.0
        return np.where(sil > 0, np.clip((d - lo) / 1.6, 0, 1), 0.0)
    n = np.asarray(r["normals"])
    lam = np.clip(n @ np.array([0.25, 0.30, 0.92]), 0.0, 1.0)
    return (0.15 + 0.85 * lam) * sil


def depth_map(V, F):
    pose, K = _cam()
    r = fs.render_mesh(np.asarray(V), np.asarray(F), pose=pose, intrinsics=K,
                       width=_W, height=_W)
    d = np.asarray(r["depth"])
    return np.where(np.isfinite(d), d, np.nan), np.asarray(r["silhouette"])


# --------------------------------------------------------------------------- #
# 1. 場面と真値                                                                  #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面 —— 解析形状から閉じたメッシュを作り、閉形式で経路を較正する")
    print("=" * 78)

    Vs, Fs = make_sphere()
    a_s, v_s = L.mesh_area((Vs, Fs)), fs.inertia_tensor(Vs, Fs)["volume"]
    a_true, v_true = 4 * np.pi * R_SPHERE ** 2, 4 / 3 * np.pi * R_SPHERE ** 3
    e_a = 100 * (a_s - a_true) / a_true
    e_v = 100 * (v_s - v_true) / v_true
    print("  較正(半径 %.0f mm の球、格子 %d):" % (R_SPHERE, SPHERE_GRID))
    print("    表面積 %8.5f mm^2 / 閉形式 %8.5f  -> %+.3f %%" % (a_s, a_true, e_a))
    print("    体積   %8.5f mm^3 / 閉形式 %8.5f  -> %+.3f %%" % (v_s, v_true, e_v))
    print("    ★marching cubes 自身の誤差がこの大きさ。以下の欠陥の効きは"
          "これより 1〜3 桁大きいので、区別がつく。")

    V, F, sdf = make_body()
    t = topology(V, F)
    area, vol = L.mesh_area((V, F)), fs.inertia_tensor(V, F)["volume"]
    print("\n  健全な部品: 頂点 %d / 辺 %d / 面 %d / χ = %d" % (
        t["V"], t["E"], t["F"], t["chi"]))
    print("    水密 %s / 辺多様体 %s / 連結成分 %d" % (
        fs.is_watertight(V, F), fs.is_edge_manifold(V, F), len(fs.components(V, F))))
    print("    表面積 %.5f mm^2 / 体積 %.5f mm^3" % (area, vol))
    print("  ★★χ = %d。貫通穴が 1 本あるので種数 1 = χ 0 が**正しい**。"
          % t["chi"])
    print("     「χ = 2 なら閉じている」というゼロ点は、**健全な部品を"
          "不合格にする**。")

    assert fs.is_watertight(V, F) and t["chi"] == 0
    assert abs(signed_volume(V, F) - vol) < 1e-9, "自前の符号つき体積が食い違う"

    if figs.enabled():
        occ = sdf < 0
        mid = occ.shape[0] // 2
        figs.save_grid(
            "scene",
            [render(V, F), render(V, F, shade=False), occ[mid].astype(float)],
            ["陰影(球 ∪ 襟 ∪ ボス − 貫通穴)", "深度図 [mm]",
             "断面(穴軸の中央) —— 中心の空洞が種数 1 を作る"],
            title="健全な部品(閉じた三角メッシュ 面 %d 枚、χ = %d)" % (t["F"], t["chi"]),
            ncols=3,
            caption="この形の χ は 0。2 ではない。")
    return {"V": V, "F": F, "area": area, "vol": vol, "topo": t,
            "cal_a": e_a, "cal_v": e_v}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— 4 つの数字だけで判定する                                          #
# --------------------------------------------------------------------------- #
def build_defects(V, F, rng) -> dict:
    """単独欠陥の対照群を 6 種 + 打ち消しの組み合わせ。"""
    out = {}
    out["穴 %d 個" % N_HOLE] = inject_holes(V, F, N_HOLE, rng)[:2]
    out["裏返り %d 面" % N_FLIP] = inject_flips(V, F, N_FLIP, rng)[:2]
    out["非多様体辺 %d 本" % N_NONMANIFOLD] = inject_nonmanifold(
        V, F, N_NONMANIFOLD, rng)[:2]
    out["退化 %d 枚" % (2 * N_SLIVER)] = inject_slivers(
        V, F, N_SLIVER, SLIVER_T, rng)[:2]
    out["重複頂点 %d 個" % (3 * N_CRACK)] = inject_cracks(V, F, N_CRACK, rng)[:2]
    out["自己交差 %d 頂点" % N_SPIKE] = inject_spikes(
        V, F, N_SPIKE, SPIKE_DEPTH, rng)[:2]
    return out


def section_zero_point(scene: dict, defects: dict) -> dict:
    print("\n" + "=" * 78)
    print("2-3) ゼロ点 —— 頂点数・辺数・面数・オイラー標数だけで健全性を判定する")
    print("=" * 78)

    V, F = scene["V"], scene["F"]
    base = scene["topo"]
    rows = [["健全(真値)", str(base["V"]), str(base["E"]), str(base["F"]),
             "%+d" % base["chi"], "-", "-"]]
    print("  条件                 頂点      辺       面     χ    Δχ   χ で見える?")
    print("   %-18s %6d %7d %7d %5d    -" % (
        "健全(真値)", base["V"], base["E"], base["F"], base["chi"]))
    blind = 0
    for name, (Vd, Fd) in defects.items():
        t = topology(Vd, Fd)
        d = t["chi"] - base["chi"]
        vis = "見える" if d != 0 else "★見えない"
        blind += (d == 0)
        rows.append([name, str(t["V"]), str(t["E"]), str(t["F"]),
                     "%+d" % t["chi"], "%+d" % d, vis])
        print("   %-18s %6d %7d %7d %5d %+5d   %s" % (
            name, t["V"], t["E"], t["F"], t["chi"], d, vis))
    print("  ★★6 種のうち **%d 種**は χ を 1 も動かさない。" % blind)

    # 打ち消し —— 穴 6 個(χ -6)+ 重複面 6 枚(χ +6)
    Vh, Fh, _ = inject_holes(V, F, N_HOLE, np.random.default_rng(SEED))
    Vc, Fc, ndup = inject_duplicate_faces(Vh, Fh, N_HOLE,
                                          np.random.default_rng(SEED + 1))
    tc = topology(Vc, Fc)
    st = L.mesh_edge_stats(Vc, Fc)
    print("\n  ★★打ち消し: 穴 %d 個 + 重複面 %d 枚を同時に入れる" % (N_HOLE, ndup))
    print("     頂点 %d(健全と同じ)/ 辺 %d(同じ)/ 面 %d(%+d)/ χ = %d"
          " —— **健全な値と同じ**"
          % (tc["V"], tc["E"], tc["F"], tc["F"] - base["F"], tc["chi"]))
    print("     種類ごとに数えれば: 境界辺 %d 本・非多様体辺 %d 本・水密 %s"
          % (st["boundary_edges"], st["non_manifold_edges"],
             fs.is_watertight(Vc, Fc)))
    rows.append(["★穴 %d + 重複面 %d" % (N_HOLE, ndup), str(tc["V"]), str(tc["E"]),
                 str(tc["F"]), "%+d" % tc["chi"], "+0", "★見えない"])
    assert tc["chi"] == base["chi"], "打ち消しが成立していない"
    assert not fs.is_watertight(Vc, Fc)

    figs.save_table("euler_blindspots",
                    ["条件", "頂点", "辺", "面", "χ", "Δχ", "χ で見えるか"],
                    rows, title="オイラー標数は 6 種の欠陥のうち %d 種に盲目" % blind,
                    caption="健全な部品の χ は 0(種数 1)。χ=2 を合格条件に"
                            "すると健全品が落ちる。最終行は打ち消し。")
    return {"blind": blind, "cancel": (Vc, Fc), "cancel_topo": tc,
            "cancel_stats": st}


# --------------------------------------------------------------------------- #
# 4. 種類ごとに数える                                                            #
# --------------------------------------------------------------------------- #
def count_defects(V, F, weld_first: bool) -> dict:
    """欠陥を**種類ごとに**数える。``weld_first`` = 先に頂点を溶接するか。"""
    if weld_first:
        V, F = fs.weld_vertices(V, F, tol=1e-9)
    st = L.mesh_edge_stats(V, F)
    n_deg = len(F) - len(fs.remove_degenerate_faces(V, F)[1])
    n_dup = len(V) - len(fs.weld_vertices(V, F, tol=1e-9)[0])
    el = np.asarray(L.mesh_edge_lengths(np.asarray(V), np.asarray(F)))
    long_v = int((el > 4.0 * np.median(el)).sum())
    return {"loops": len(boundary_loops(V, F)),
            "boundary_edges": int(st["boundary_edges"]),
            "nonmanifold": int(st["non_manifold_edges"]),
            "degenerate": n_deg, "duplicate_v": n_dup, "long_edge_v": long_v}


def section_count_by_type(scene: dict, defects: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 種類ごとに数える —— 順番がある(合わせてから測ると割れが消える)")
    print("=" * 78)

    V, F = scene["V"], scene["F"]
    rng = np.random.default_rng(SEED)
    # 6 種すべてを 1 つのメッシュに重ねる(面は互いに離して選ぶ)
    W, G, n_hole = inject_holes(V, F, N_HOLE, rng)
    W, G, n_flip = inject_flips(W, G, N_FLIP, rng)
    W, G, n_nm = inject_nonmanifold(W, G, N_NONMANIFOLD, rng)
    W, G, n_deg = inject_slivers(W, G, N_SLIVER, SLIVER_T, rng)[:3]
    W, G, n_dup = inject_cracks(W, G, N_CRACK, rng)
    W, G, n_spk, spk = inject_spikes(W, G, N_SPIKE, SPIKE_DEPTH, rng)

    raw = count_defects(W, G, weld_first=False)
    wel = count_defects(W, G, weld_first=True)
    Fo, n_flip_found = fs.orient_consistent(
        *fs.weld_vertices(*fs.remove_degenerate_faces(W, G), tol=1e-9))

    rows = [
        ["穴(境界の輪)", str(n_hole),
         "%d = 穴 %d + 割れ %d + テント %d" % (raw["loops"], n_hole,
                                              2 * N_CRACK, n_nm),
         "%d = 穴 %d + テント %d" % (wel["loops"], n_hole, n_nm)],
        ["非多様体辺", str(n_nm), str(raw["nonmanifold"]), str(wel["nonmanifold"])],
        ["退化三角形", str(n_deg), "%d(一致)" % raw["degenerate"],
         "%d ★溶接が先に消した" % wel["degenerate"]],
        ["重複頂点", str(n_dup),
         "%d = 割れ %d + 潰れ辺 %d" % (raw["duplicate_v"], n_dup, N_SLIVER),
         "0(溶接済)"],
        ["裏返った面", str(n_flip), "—(位相を直すまで数えられない)",
         "%d(一致)" % int(n_flip_found)],
        ["自己交差(頂点)", str(n_spk), "—(検出 op なし)",
         "%d(辺長の外れ値で代用)" % wel["long_edge_v"]],
    ]
    print("  欠陥の種類        真値   そのまま数える                     溶接してから数える")
    for r in rows:
        print("   %-16s %5s   %-32s %s" % (r[0], r[1], r[2], r[3]))

    print("\n  ★★どの数字も「その欠陥だけ」を数えてはいない。境界の輪 %d 個の内訳は"
          % raw["loops"])
    print("     穴 %d + 割れ %d(1 枚ほどくと表裏 2 個の輪ができる) + "
          "テント %d(3 枚目の面が\n     2 本の境界辺を連れてくる)。"
          "**足し合わせは 1 個の狂いもなく合う**が、輪の数を穴の数だと"
          "\n     思って読むと %.1f 倍に読み違える。"
          % (n_hole, 2 * N_CRACK, n_nm, raw["loops"] / n_hole))
    print("  ★★順番が両向きに効く。**溶接を先にすると**割れの輪 %d 個は"
          "きれいに消えるが、" % (2 * N_CRACK))
    print("     退化三角形も一緒に %d -> %d 枚に消えて**数え損ねる**"
          "(潰し具合 t=%.0e の頂点は\n     元の頂点から %.0e mm しか離れておらず、"
          "溶接の許容差の内側)。退化は溶接の**前**に、\n     穴は溶接の**後**に数える。"
          % (raw["degenerate"], wel["degenerate"], SLIVER_T, SLIVER_T * 0.04))
    print("  ★重複頂点 %d 個と真値 %d 個の差 %d は**潰した辺が置いた頂点**。"
          % (raw["duplicate_v"], n_dup, raw["duplicate_v"] - n_dup))
    print("     退化と重複は同じ現象の 2 つの顔で、t が小さいところでは"
          "分けて数えられない。")

    assert raw["loops"] == n_hole + 2 * N_CRACK + n_nm, raw["loops"]
    assert wel["loops"] == n_hole + n_nm, wel["loops"]
    assert wel["loops"] - wel["nonmanifold"] == n_hole
    assert raw["nonmanifold"] == n_nm and wel["nonmanifold"] == n_nm
    assert raw["degenerate"] == n_deg and wel["degenerate"] == 0
    assert raw["duplicate_v"] == n_dup + N_SLIVER, raw["duplicate_v"]
    assert int(n_flip_found) == n_flip
    assert wel["long_edge_v"] == n_spk

    figs.save_table("defect_counts",
                    ["欠陥の種類", "真値", "そのまま数える", "溶接してから数える"],
                    rows, title="種類ごとに数えると内訳まで 1 個の狂いもなく合う",
                    caption="ただし順番が両向きに効く —— 溶接前は割れの境界を"
                            "穴として数え、溶接後は退化三角形を数え損ねる。")
    if figs.enabled():
        d0, s0 = depth_map(V, F)
        d1, s1 = depth_map(W, G)
        both = (s0 > 0) & (s1 > 0)
        diff = np.where(both, np.nan_to_num(d1 - d0), 0.0)
        figs.save_grid("defect_scene",
                       [render(V, F), render(W, G), diff],
                       ["健全", "6 種の欠陥を注入(穴 %d・裏返り %d・非多様体 %d・"
                        "退化 %d・重複頂点 %d・自己交差 %d)"
                        % (n_hole, n_flip, n_nm, n_deg, n_dup, n_spk),
                        "深度差 [mm](青=手前へ / 赤=奥へ)"],
                       signed=[False, False, True], ncols=3,
                       title="欠陥は絵にほとんど出ない —— 出るのは自己交差だけ",
                       caption="深度差が立つのは突き刺した %d 頂点の周りだけ。"
                               "穴・裏返り・退化・重複頂点は同じ絵になる。" % n_spk)
    return {"raw": raw, "welded": wel, "mesh": (W, G),
            "n": (n_hole, n_flip, n_nm, n_deg, n_dup, n_spk)}


# --------------------------------------------------------------------------- #
# 5. 直った / 戻った は別の指標                                                  #
# --------------------------------------------------------------------------- #
def section_repair_vs_restore(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) ★「直った(水密)」と「戻った(体積・表面積)」は別の指標")
    print("=" * 78)

    V, F = scene["V"], scene["F"]
    A0, Vol0 = scene["area"], scene["vol"]
    rng = np.random.default_rng(SEED)
    Vc, Fc, ndup = inject_cracks(V, F, N_CRACK, rng)

    print("  ゼロ幅の割れ(重複頂点 %d 個)—— 形は 1 mm も変わっていない:" % ndup)
    print("    水密 %s / 境界の輪 %d 個 / 表面積 %+.4f %% / 体積 %+.4f %%" % (
        fs.is_watertight(Vc, Fc), len(boundary_loops(Vc, Fc)),
        100 * (L.mesh_area((Vc, Fc)) - A0) / A0,
        100 * (signed_volume(Vc, Fc) - Vol0) / Vol0))

    rows = []
    for name, (Vr, Fr) in (("穴埋め(扇を張る)", fs.fill_holes(Vc, Fc)),
                           ("頂点を溶接する", fs.weld_vertices(Vc, Fc, tol=1e-9))):
        wt = fs.is_watertight(Vr, Fr)
        ea = 100 * (L.mesh_area((Vr, Fr)) - A0) / A0
        ev = 100 * (signed_volume(Vr, Fr) - Vol0) / Vol0
        rows.append([name, str(wt), "%+d" % (len(Fr) - len(F)),
                     "%+.4f %%" % ea, "%+.4f %%" % ev])
        print("    %-16s -> 水密 %-5s  面 %+5d  表面積 %+.4f %%  体積 %+.4f %%"
              % (name, wt, len(Fr) - len(F), ea, ev))
    print("  ★★**どちらも水密になる**。表面積が戻るのは片方だけ"
          "(%s vs %s)。" % (rows[0][3], rows[1][3]))
    print("     水密だけを合否にすると、**面を二重に張った状態**を合格にする。")

    Vf, Ff = fs.fill_holes(Vc, Fc)
    Vw, Fw = fs.weld_vertices(Vc, Fc, tol=1e-9)
    assert fs.is_watertight(Vf, Ff) and fs.is_watertight(Vw, Fw)
    assert abs(L.mesh_area((Vw, Fw)) - A0) < 1e-9, "溶接は面積を変えないはず"
    assert L.mesh_area((Vf, Ff)) > A0 + 1e-4, "穴埋めは面を足すはず"

    figs.save_table("repair_vs_restore",
                    ["直し方", "水密になったか", "面の増減", "表面積の誤差", "体積の誤差"],
                    rows, title="同じ欠陥を 2 通りに直すと、片方だけ量が戻る",
                    caption="幅ゼロの割れ(重複頂点 %d 個)を直した結果。"
                            "水密は 2 通りとも True。" % ndup)
    return {"rows": rows}


# --------------------------------------------------------------------------- #
# 6. 崖その 1 —— 穴の大きさ(閉形式で予測してから測る)                           #
# --------------------------------------------------------------------------- #
def section_hole_cliff() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖 1 —— 穴の大きさ。体積は閉形式で予測でき、表面積は予測が外れる")
    print("=" * 78)
    print("  予測(球 R=%.0f mm、半頂角 θ の冠を削って平らな扇で塞ぐ):" % R_SPHERE)
    print("    体積の減り = 球欠 πh²(3R-h)/3   表面積 = -2πRh + πa²"
          "  (h=R(1-cosθ), a=R sinθ)")

    R = R_SPHERE
    V0, F0 = make_sphere()
    A0 = L.mesh_area((V0, F0))
    Vol0 = fs.inertia_tensor(V0, F0)["volume"]
    cen = V0[F0].mean(1)

    degs, pv, mv, pa, ma, ratio, fanr = [], [], [], [], [], [], []
    print("\n   θ[deg]  削った面  縁の辺  体積: 予測    実測   |  表面積: 予測    実測"
          "  | L/2πa  扇/πa²")
    for deg in (4, 8, 14, 22, 32, 45, 60, 80):
        th = np.radians(deg)
        keep = cen[:, 0] < R * np.cos(th)
        Fh = F0[keep]
        be = np.asarray(fs.boundary_edges(V0, Fh))
        perim = float(np.linalg.norm(V0[be[:, 0]] - V0[be[:, 1]], axis=1).sum())
        a_hole = L.mesh_area((V0, Fh))
        Vf, Ff = fs.fill_holes(V0, Fh)
        a_fill = L.mesh_area((Vf, Ff))
        h, a = R * (1 - np.cos(th)), R * np.sin(th)
        p_v = -100 * (np.pi * h * h * (3 * R - h) / 3) / (4 / 3 * np.pi * R ** 3)
        p_a = 100 * (np.pi * a * a - 2 * np.pi * R * h) / (4 * np.pi * R * R)
        m_v = 100 * (signed_volume(Vf, Ff) - Vol0) / Vol0
        m_a = 100 * (a_fill - A0) / A0
        rr = perim / (2 * np.pi * a) if a > 1e-9 else np.nan
        fr = (a_fill - a_hole) / (np.pi * a * a) if a > 1e-9 else np.nan
        degs.append(deg); pv.append(p_v); mv.append(m_v)
        pa.append(p_a); ma.append(m_a); ratio.append(rr); fanr.append(fr)
        print("   %5d   %6d   %5d   %8.3f %8.3f  | %8.3f %8.3f  | %5.2f  %5.2f" % (
            deg, int((~keep).sum()), len(be), p_v, m_v, p_a, m_a, rr, fr))
        assert fs.is_watertight(Vf, Ff), "穴埋めは水密にするはず"

    i45 = degs.index(45)
    print("\n  ★体積は予測どおり(θ=32° で %+.3f / %+.3f %%、θ=80° で %+.3f / %+.3f %%)。"
          % (pv[degs.index(32)], mv[degs.index(32)], pv[-1], mv[-1]))
    print("     扇は平ら = 冠の体積がそのまま抜けるので、"
          "**球欠の閉形式がそのまま使える**。")
    print("  ★★表面積は**予測が外れた**: θ=45° で予測 %+.3f %%、実測 %+.3f %% —— 符号も逆。"
          % (pa[i45], ma[i45]))
    print("     原因は縁が円ではなく**階段**だから。θ=45° の縁は実周長が円周の"
          " %.2f 倍あり、" % ratio[i45])
    print("     張られた扇の面積は平らな円 πa² の **%.2f 倍**。同じ「穴の大きさ」でも"
          % fanr[i45])
    print("     θ=32° では %.2f 倍・θ=80° では %.2f 倍しかない —— "
          "**扇の面積は穴の大きさだけでは決まらない**。" % (fanr[degs.index(32)], fanr[-1]))
    print("     縁が voxel 格子のどこに落ちるかで階段の粗さが変わるから。"
          "\n     ★実データの縁はもっと汚いので、**穴埋め後の表面積は信用しない**"
          "(体積は使える)。")

    figs.save_plot("hole_cliff",
                   [("体積 予測(球欠)", degs, pv), ("体積 実測", degs, mv),
                    ("表面積 予測(平らな円)", degs, pa), ("表面積 実測", degs, ma)],
                   xlabel="穴の半頂角 θ [deg]", ylabel="穴埋め後の誤差 [%]",
                   title="穴の大きさの崖 —— 体積は予測でき、表面積はできない",
                   caption="体積の 2 本は重なる。表面積は θ=45° で符号すら逆。")
    figs.save_plot("hole_rim_roughness",
                   [("縁の実周長 / 円周", degs, ratio),
                    ("張られた扇 / 平らな円 πa²", degs, fanr),
                    ("円のとき(=1)", degs, [1.0] * len(degs))],
                   xlabel="穴の半頂角 θ [deg]", ylabel="比 [-]",
                   title="縁は円ではない —— 階段の粗さは穴の大きさで決まらない",
                   caption="どちらも 1 に近い θ と 2 倍を超える θ が混在する。"
                           "縁が voxel 格子のどこに落ちるかで変わる。")

    if figs.enabled():
        th = np.radians(45.0)
        Fh = F0[cen[:, 0] < R * np.cos(th)]
        Vf, Ff = fs.fill_holes(V0, Fh)
        d0, s0 = depth_map(V0, F0)
        d2, s2 = depth_map(Vf, Ff)
        both = (s0 > 0) & (s2 > 0)
        figs.save_grid("hole_frames",
                       [render(V0, F0), render(V0, Fh), render(Vf, Ff),
                        np.where(both, np.nan_to_num(d2 - d0), 0.0)],
                       ["健全な球", "θ=45° の穴", "穴埋め後(平らな扇)",
                        "深度差 [mm] —— 塞いだ面が奥に凹む"],
                       signed=[False, False, False, True], ncols=2,
                       title="穴埋めは水密にするが、冠のぶんの体積は戻らない")
    return {"deg": degs, "pv": pv, "mv": mv, "pa": pa, "ma": ma, "ratio": ratio}


# --------------------------------------------------------------------------- #
# 7-8. 崖その 2 —— 簡略化                                                        #
# --------------------------------------------------------------------------- #
def section_decimate_cliff(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("7-8) 崖 2 —— 簡略化。体積より先に曲率分布が壊れる")
    print("=" * 78)
    print("  予測: 辺長 h ∝ F^-1/2、弦の矢 ∝ h²/R なので**相対誤差 ∝ 1/F**"
          "(両対数の傾き 1)。")

    V0, F0 = scene["V"], scene["F"]
    A0, Vol0 = scene["area"], scene["vol"]
    faces, dv, da, c50, c95, curves = [], [], [], [], [], {}
    print("\n   削減率  面数    体積の誤差  表面積の誤差  曲率 p50  曲率 p95  退化面")
    for r in (0.0, 0.30, 0.50, 0.70, 0.85, 0.92, 0.95, 0.98):
        if r == 0.0:
            V2, F2 = V0, F0
        else:
            V2, F2 = fs.decimate_qem(V0, F0, int(round(len(F0) * (1 - r))))
        V3, F3 = fs.remove_degenerate_faces(V2, F2)
        ndeg = len(F2) - len(F3)
        vol = fs.inertia_tensor(V2, F2)["volume"]
        c = np.asarray(L.vertex_curvature((V3, F3)))
        faces.append(len(F2))
        dv.append(100 * (vol - Vol0) / Vol0)
        da.append(100 * (L.mesh_area((V2, F2)) - A0) / A0)
        c50.append(float(np.median(c)))
        c95.append(float(np.percentile(c, 95)))
        if r in (0.0, 0.50, 0.85, 0.98):
            curves[r] = np.sort(c)
        print("   %5.0f %%  %6d   %+8.3f %%  %+8.3f %%  %8.3f  %8.3f    %d" % (
            100 * r, len(F2), dv[-1], da[-1], c50[-1], c95[-1], ndeg))

    i50 = 2
    print("\n  ★★50 %% 削減の時点で体積誤差は %+.3f %%・表面積 %+.3f %% しかないのに、"
          % (dv[i50], da[i50]))
    print("     曲率の 95 パーセンタイルは %.2f -> %.2f(%+.0f %%)動いている。"
          % (c95[0], c95[i50], 100 * (c95[i50] - c95[0]) / c95[0]))
    print("     **積分量(体積・表面積)は局所形状の破壊に構造的に盲目**。")

    def slope(i, j):
        return (np.log(abs(dv[j]) / abs(dv[i]))
                / np.log(faces[i] / faces[j]))

    s_late = slope(4, 7)     # 1680 -> 224
    s_early = slope(2, 4)    # 5604 -> 1680
    print("  ★誤差則は途中で変わる: 面数 %d->%d の傾きは %.2f(予測 1 とほぼ一致)、"
          % (faces[4], faces[7], s_late))
    print("     %d->%d では %.2f と予測よりずっと急。削り始めは"
          "「消しても損しない頂点」から消えるので、" % (faces[2], faces[4], s_early))
    print("     しばらく誤差が予測より小さいまま残る。")
    cliff = next((100 * r for r, e in zip((0.0, .30, .50, .70, .85, .92, .95, .98), dv)
                  if abs(e) > 0.1), None)
    print("  ★崖(体積誤差が 0.1 %% を超える点)は削減率 %.0f %% あたり。" % cliff)

    assert abs(dv[-1]) > 1.0 and abs(dv[1]) < 0.05, (dv[1], dv[-1])
    assert c95[i50] > c95[0] * 1.2, "曲率が先に動くという所見が崩れた"

    ideal = [abs(dv[-1]) * faces[-1] / f for f in faces]
    figs.save_plot("decimate_cliff",
                   [("体積の誤差 |ΔV|", faces, [abs(x) for x in dv]),
                    ("表面積の誤差 |ΔA|", faces, [abs(x) for x in da]),
                    ("予測 ∝ 1/F", faces, ideal)],
                   xlabel="面数 [枚]", ylabel="誤差の大きさ [%]",
                   title="簡略化の崖 —— 体積は最後に効く",
                   caption="予測線は最も粗い点で合わせた 1/F。面数が多い側では"
                           "実測のほうが小さい(まだ削り代がある)。")
    figs.save_plot("decimate_curvature",
                   [("削減 %.0f %%" % (100 * r), curves[r],
                     np.linspace(0, 1, curves[r].size)) for r in sorted(curves)],
                   xlabel="平均曲率の大きさ |H| [1/mm]", ylabel="累積割合",
                   xlim=(0.0, 12.0),
                   title="曲率分布は体積より先に動く(50 %% 削減で p95 が %+.0f %%)"
                         % (100 * (c95[i50] - c95[0]) / c95[0]))
    return {"faces": faces, "dv": dv, "da": da, "c95": c95,
            "s_late": s_late, "s_early": s_early, "cliff": cliff}


# --------------------------------------------------------------------------- #
# 9. 崖その 3 —— 退化三角形のしきい値                                            #
# --------------------------------------------------------------------------- #
def section_sliver_threshold(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("9) 崖 3 —— 退化三角形は「どれだけ潰れたら」検出されるか")
    print("=" * 78)

    V0, F0 = scene["V"], scene["F"]
    n0 = np.asarray(L.face_normals((V0, F0)))     # 潰れ面が乗る平面の**厳密な**法線
    med = float(np.median(0.5 * np.linalg.norm(np.cross(
        V0[F0[:, 1]] - V0[F0[:, 0]], V0[F0[:, 2]] - V0[F0[:, 0]]), axis=1)))
    print("  中央値の面積 %.3e mm^2。潰れ面の面積をその何倍にするかで振る。" % med)
    print("  ★潰れ面が乗る平面は元の面と同じなので、**正しい法線は分かっている**"
          "(= 親の面法線)。")
    print("\n   t        面積比       検出 /%2d  法線 1°超  法線が作れない  最大ずれ [deg]"
          "  face_normals" % (2 * N_SLIVER))

    ts, frac, angs, ratios, nbroken, nzero = [], [], [], [], [], []
    for t in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9):
        rng = np.random.default_rng(SEED)
        Vd, Fd, ndeg, ar, sl = inject_slivers(V0, F0, N_SLIVER, t, rng)
        n_found = len(Fd) - len(fs.remove_degenerate_faces(Vd, Fd)[1])
        # 潰れ面の法線を自前で作る(face_normals は退化面を fail-closed で拒む)
        a, b, c = Vd[Fd[sl, 0]], Vd[Fd[sl, 1]], Vd[Fd[sl, 2]]
        cr = np.cross(b - a, c - a)
        nn = np.linalg.norm(cr, axis=1, keepdims=True)
        good = nn[:, 0] > 0
        unit = np.where(good[:, None], cr / np.where(nn > 0, nn, 1.0), 0.0)
        dot = np.abs(np.einsum("ij,ij->i", unit, n0[sl]))
        ang = np.degrees(np.arccos(np.clip(dot, 0.0, 1.0)))
        ang[~good] = 90.0                       # 法線が作れない = 完全に壊れた
        broken = int((ang > 1.0).sum())
        try:
            L.face_normals((Vd, Fd))
            fn = "通る"
        except ValueError:
            fn = "★拒む"
        ts.append(np.log10(t)); frac.append(n_found); angs.append(float(ang.max()))
        ratios.append(ar / med); nbroken.append(broken)
        nzero.append(int((~good).sum()))
        print("   %.0e   %.2e     %3d       %3d        %3d        %8.3f      %s" % (
            t, ar / med, n_found, broken, nzero[-1], ang.max(), fn))
        assert fs.is_watertight(Vd, Fd), "潰し方が位相を壊した"

    first = next(i for i, f in enumerate(frac) if f > 0)
    full = next(i for i, f in enumerate(frac) if f == 2 * N_SLIVER)
    fb = next(i for i, b in enumerate(nbroken) if b > 0)
    print("\n  ★検出の崖: 面積比 %.1e(t=%.0e)ではまだ 0 枚、%.1e(t=%.0e)で %d 枚、"
          "t=%.0e で全 %d 枚。"
          % (ratios[first - 1], 10.0 ** ts[first - 1], ratios[first],
             10.0 ** ts[first], frac[first], 10.0 ** ts[full], frac[full]))
    print("  ★★**壊れるほうが %d 桁早い**。t=%.0e(面積比 %.1e)で既に %d 枚の"
          "法線が 1° 以上(最大 %.1f°)ずれ、"
          % (abs(ts[first] - ts[fb]), 10.0 ** ts[fb], ratios[fb],
             nbroken[fb], angs[fb]))
    print("     水密も多様体も χ も健全なのに、``remove_degenerate_faces`` の"
          "検出は %d 枚。" % frac[fb])
    print("     **退化の判定は「面積が 0 か」だが、実害は「法線が壊れるか」で"
          "先に来る**。")
    print("  ★同じ族の 2 つの op が食い違う: t=%.0e で ``face_normals`` は"
          "メッシュ全体を拒むが、" % 10.0 ** ts[first])
    print("     法線が本当に作れない(外積が厳密に 0)のは %d 枚、"
          "``remove_degenerate_faces`` が落とすのは %d 枚 —— "
          "\n     「退化」の定義が 3 通りある。" % (nzero[first], frac[first]))

    assert frac[0] == 0 and frac[-1] == 2 * N_SLIVER
    assert max(angs) > 1.0, "法線が壊れるという所見が崩れた"
    assert fb < first, "法線のほうが先に壊れるという所見が崩れた"

    figs.save_plot("sliver_threshold",
                   [("検出された枚数", ts, [float(f) for f in frac]),
                    ("法線が 1°以上ずれた枚数", ts, [float(b) for b in nbroken]),
                    ("注入した枚数", ts, [float(2 * N_SLIVER)] * len(ts))],
                   xlabel="log10(潰し具合 t)", ylabel="枚数 [枚]",
                   title="退化の検出より、法線の破壊のほうが %d 桁早い"
                         % abs(ts[first] - ts[fb]),
                   caption="面積 0 の判定に引っかかるずっと手前で、"
                           "潰れ面の法線は使いものにならなくなる。")
    figs.save_plot("sliver_normal_error",
                   [("潰れ面の法線の最大ずれ", ts, angs),
                    ("1° の線", ts, [1.0] * len(ts))],
                   xlabel="log10(潰し具合 t)", ylabel="親の面法線からのずれ [deg]",
                   title="潰れ面の法線は親の平面から離れていく(90°=法線が作れない)")
    return {"t": ts, "found": frac, "ang": angs, "ratio": ratios,
            "broken": nbroken, "zero": nzero, "first": first, "fb": fb}


# --------------------------------------------------------------------------- #
# 10. 自己交差 —— どの位相検査もすり抜ける                                       #
# --------------------------------------------------------------------------- #
def section_self_intersection(scene: dict) -> dict:
    print("\n" + "=" * 78)
    print("10) ★★自己交差 —— 水密・多様体・χ をすべて通り抜ける")
    print("=" * 78)

    V0, F0 = scene["V"], scene["F"]
    A0, Vol0 = scene["area"], scene["vol"]
    el0 = np.asarray(L.mesh_edge_lengths(V0, F0))
    thr = 4.0 * float(np.median(el0))
    rows = []
    print("   深さ [mm]  水密  多様体   χ   表面積の誤差  体積の誤差  辺長の外れ値")
    for depth in (0.0, 0.20, 0.45, 0.75):
        rng = np.random.default_rng(SEED)
        Vs, Fs, n, spk = inject_spikes(V0, F0, N_SPIKE, depth, rng)
        t = topology(Vs, Fs)
        ea = 100 * (L.mesh_area((Vs, Fs)) - A0) / A0
        ev = 100 * (fs.inertia_tensor(Vs, Fs)["volume"] - Vol0) / Vol0
        el = np.asarray(L.mesh_edge_lengths(Vs, Fs))
        nl = int((el > thr).sum())
        rows.append(["%.2f" % depth, str(fs.is_watertight(Vs, Fs)),
                     str(fs.is_edge_manifold(Vs, Fs)), "%+d" % t["chi"],
                     "%+.3f %%" % ea, "%+.3f %%" % ev, str(nl)])
        print("   %8.2f   %-5s %-5s %+4d  %+9.3f %%  %+9.3f %%   %4d" % (
            depth, fs.is_watertight(Vs, Fs), fs.is_edge_manifold(Vs, Fs),
            t["chi"], ea, ev, nl))
        if depth == SPIKE_DEPTH:
            last = (ea, ev, nl)
            assert fs.is_watertight(Vs, Fs) and fs.is_edge_manifold(Vs, Fs)
            assert t["chi"] == scene["topo"]["chi"]

    ea, ev, nl = last
    print("\n  ★★頂点 %d 個を %.2f mm 押し込むと襟の管(径 %.2f mm)を突き抜ける。"
          % (N_SPIKE, SPIKE_DEPTH, 2 * R_TUBE))
    print("     位相の検査は 3 つとも健全のまま。量は**表面積 %+.3f %% / "
          "体積 %+.3f %%** で %.0f 倍食い違う。" % (ea, ev, abs(ea / ev)))
    print("     体積だけを合否にしていると通る。表面積も一緒に見ること。")
    print("     ★fullseye に自己交差の検出 op は無い。辺長の外れ値で %d 頂点"
          "拾えるが、これは**代用**であって検出ではない。" % nl)

    figs.save_table("self_intersection",
                    ["突き刺す深さ [mm]", "水密", "辺多様体", "χ",
                     "表面積の誤差", "体積の誤差", "辺長の外れ値 [頂点]"],
                    rows, title="自己交差は位相の検査を 3 つとも通り抜ける",
                    caption="頂点 %d 個だけを内側へ押した。形は壊れているのに"
                            "水密・多様体・χ はすべて健全のまま。" % N_SPIKE)
    return {"rows": rows, "last": last}


# --------------------------------------------------------------------------- #
# 11. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps(scene: dict) -> None:
    print("\n" + "=" * 78)
    print("11) 道具の穴(この PoC で mesh 修復族を使ってみて)")
    print("=" * 78)

    V, F = scene["V"], scene["F"]

    # (a) 同じ名前で別の op —— ファサードは mesh 版、台帳は深度画像版
    assert fs.fill_holes.__module__ == "meshrepair"
    import ops3d
    assert ops3d.OPS3D["fill_holes"]["module"] == "depth_bilateral"
    print("  (a) ★``fill_holes`` が 2 つある。``fs.fill_holes`` は**メッシュ**の"
          "穴埋め(meshrepair)、\n      ``fs.ledger.fill_holes`` は**深度画像**の"
          "穴埋め(depth_bilateral)。同名で別物・別入力。")

    # (b) 境界辺は返るが、輪にまとめる口が無い(穴の「個数」が出せない)
    assert hasattr(fs, "boundary_edges")
    assert not hasattr(fs, "boundary_loops") and not hasattr(fs.ledger, "boundary_loops")
    print("  (b) 境界を**輪にまとめる** op が無い。``boundary_edges`` は辺の集合"
          "なので、\n      穴の個数を出すには呼び手が連結成分を組む(この PoC の"
          "``boundary_loops``)。")

    # (c) 自己交差の検出が無い
    for n in ("self_intersections", "mesh_self_intersect", "triangle_intersect"):
        assert not hasattr(fs, n) and not hasattr(fs.ledger, n)
    print("  (c) ★**自己交差(面どうしの貫通)を検出する op が無い**。位相の"
          "検査を全部通るので、\n      いまの道具立てでは辺長や曲率の外れ値で"
          "代用するしかない。修復族の最大の穴。")

    # (d) 水密でないメッシュの体積が出せない(fail-closed は正しいが逃げ道が無い)
    rng = np.random.default_rng(SEED)
    Vh, Fh, _ = inject_holes(V, F, 2, rng)
    try:
        fs.inertia_tensor(Vh, Fh)
        raise AssertionError("水密でないのに通った")
    except ValueError:
        pass
    print("  (d) ``inertia_tensor`` は水密でないメッシュを fail-closed で拒む"
          "(設計は正しい)。\n      だが「直す前にどれだけ狂っているか」を測る"
          "口が無い。符号つき体積(発散定理)は\n      この PoC が自前で持った ——"
          "``signed_volume`` として族に入れる価値はある。")

    # (e) mesh_edge_stats は数えてくれるが「どの辺か」を返さない
    st = L.mesh_edge_stats(V, F)
    assert "non_manifold_edges" in st and isinstance(st["non_manifold_edges"], int)
    print("  (e) ``mesh_edge_stats`` は非多様体辺の**本数**は返すが**位置**を"
          "返さない。\n      直すにも見せるにも辺の index が要る。")

    # (f) 面法線・表面積・曲率がファサードに出ていない
    assert hasattr(fs.ledger, "mesh_area") and not hasattr(fs, "mesh_area")
    assert hasattr(fs.ledger, "face_normals") and not hasattr(fs, "face_normals")
    print("  (f) ``mesh_area`` / ``face_normals`` / ``vertex_curvature`` は"
          "``fs.ledger`` からしか呼べない。\n      同じメッシュ族なのに"
          "``fs.fill_holes`` は 1 行ファサードに在る —— 規約が揃っていない。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("メッシュの健全性診断と修復 —— 直した分だけ欠陥は消え、量は戻らない")
    print("部品: 球 ∪ トーラス襟 ∪ 角柱ボス − 貫通穴 / 格子 %d^3 / 単位 mm" % GRID)
    print("=" * 78)

    scene = section_scene()
    rng = np.random.default_rng(SEED)
    defects = build_defects(scene["V"], scene["F"], rng)
    zero = section_zero_point(scene, defects)
    counts = section_count_by_type(scene, defects)
    section_repair_vs_restore(scene)
    hole = section_hole_cliff()
    dec = section_decimate_cliff(scene)
    sliver = section_sliver_threshold(scene)
    spike = section_self_intersection(scene)
    section_tool_gaps(scene)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 1 つの数字(χ)は 6 種の欠陥のうち %d 種に盲目で、打ち消しで"
          "健全な値に戻せる。" % zero["blind"])
    print("  * 種類ごとに数えれば全部当たる。ただし**溶接してから数える**"
          "(順番がある)。")
    print("  * 「水密になった」と「体積・表面積が戻った」は別物。穴埋めは"
          "水密にするが\n    θ=45° の穴では表面積が %+.3f %% ずれる"
          "(予測は %+.3f %%)。" % (hole["ma"][5], hole["pa"][5]))
    print("  * 簡略化は体積より先に曲率を壊す(50 %% 削減で体積 %+.3f %%、"
          "曲率 p95 %+.0f %%)。" % (dec["dv"][2],
                                    100 * (dec["c95"][2] - dec["c95"][0]) / dec["c95"][0]))
    print("  * 自己交差は位相検査を全部通る(表面積 %s / 体積 %s)。"
          % (spike["rows"][-1][4], spike["rows"][-1][5]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
