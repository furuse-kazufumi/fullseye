# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mesh_decimate — 三角メッシュ簡略化(mesh decimation)の **境界保存・多様体厳格** な
quadric error metric(QEM, Garland & Heckbert, SIGGRAPH 1997)edge-collapse 実装
``decimate_qem_manifold``。

関係する既存 op(重複ではなく変種であることの明示 / honest disclosure):
    fullseye には既に **``meshrepair.decimate_qem(V, F, target_faces)``**(``fullseye.decimate_qem``
    として公開・テスト済み)があり、同じ Garland & Heckbert 1997 の QEM edge-collapse を
    「実用(practical)」水準で実装している(正しい per-vertex quadric・最小コスト collapse・
    法線反転ガード)。本モジュールはそれを置き換える「新規で唯一の簡略化 op」ではない。
    ``decimate_qem`` が **明示的に持たない** 3 点を足した **姉妹 op(sibling variant)** である:
      (1) **境界エッジ拘束二次形式**(Garland の boundary term)。``decimate_qem`` は
          "no boundary-preservation term" と自認しており、開いたメッシュの境界(穴の縁・
          切り口の rim)を保てない。本 op は境界頂点が rim から離れる動きを強く罰する。
      (2) **link condition による多様体保存**(Dey+ 1999)。``decimate_qem`` の法線反転
          ヒューリスティックより厳密にトポロジー(2-manifold)を保つ。
      (3) **4×4 拘束系での最適縮約位置**と、病的な外れ位置を棄却する
          ``_FALLBACK_DIST_RATIO`` 外れ値除去。
    使い分け:安価な衝突プロキシ=``decimate_qem`` / 開境界の保存と厳密 2-manifold が要る=本 op。
    (differentiation は examples_3d/mesh_decimate.py が両者を実測比較して裏付ける — 開半球の
    rim で本 op は境界を rim 上に保つが ``decimate_qem`` は rim を内側へ引き込む。)

原理:高ポリ(high-poly)メッシュを形をできるだけ保ったまま目標面数へ落とす。素朴に
「面をランダムに間引く」と穴(hole)や非多様体(non-manifold)を作って形が壊れるが、QEM は
「各頂点を、これまで消してきた面群の平面からの二乗距離の和(=誤差二次形式 Q)」で評価し、
**誤差が最小になる辺から順に縮約(collapse)**する。縮約後の頂点は Q を最小化する最適位置へ
寄せるので、平坦部は大胆に・曲率の高い所は保守的に間引かれ、元表面への Hausdorff 距離が小さく保たれる。

このモジュールが行うこと(honest な範囲):
  * 誤差二次形式 Q を面の基本二次形式(fundamental quadric K = p·pᵀ, p=平面 [a,b,c,d])の
    和として頂点ごとに積む。
  * 開いた面の**境界エッジ(boundary edge)**には Garland 流の垂直拘束二次形式を重み付きで
    足し、境界が内側へ崩れるのを防ぐ(閉曲面では境界が無く無影響=そこでは ``decimate_qem`` と
    差が出ないのが正しい挙動)。
  * 縮約の可否は **link condition**(Dey+ 1999)で判定し、非多様体を生む縮約は拒否する。
  * 縮約先頂点は Q を最小化する 4×4 線形系で解く(特異なら端点/中点から最小コストを採る)。
  * lazy-deletion な最小ヒープでコスト最小の辺から縮約し、面数が目標に達したら停止する。

mesh 表現は recon3d / match3d / meshrepair と同一:頂点 ``vertices`` (N,3) float、面
``faces`` (M,3) int(三角形の頂点インデックス)。入力は fail-closed に検証(形状・
インデックス範囲・非有限)。numpy + scipy(spatial のみ)で完結し、重い依存は使わない。

Reference (public): M. Garland and P. S. Heckbert, "Surface Simplification Using
Quadric Error Metrics", SIGGRAPH 1997.  Link condition: T. K. Dey, H. Edelsbrunner,
S. Guha, D. V. Nekhayev, "Topology preserving edge contraction", 1999.
"""
from __future__ import annotations

import heapq

import numpy as np

__all__ = ["decimate_qem_manifold"]

# 境界エッジ拘束二次形式の重み。境界頂点が境界線から離れるのを強く罰する
# (面の基本二次形式は単位法線由来で O(1) なので、境界を「効かせる」には十分大きく取る)。
_BOUNDARY_WEIGHT = 1.0e3

# 最適縮約位置が端点中点からこの倍数(×エッジ長)より遠ければ、線形解を棄却して
# 端点/中点の最小コスト候補へフォールバックする(病的な外れ位置を防ぐ)。
# 2026-08-30: 10.0 → 1.0 に強化。境界二次形式(重み 1e3)混入で Qsum が中程度に
# 悪条件化(実測 cond≈2400)すると、解は finite だが端点から数エッジ長飛んだ位置に
# なり(実測 3.95×)、リム頂点が球面半径 1.0→0.48 まで崩れて「境界保存」の主張が
# 高圧縮比で自壊していた。健全な QEM 最適位置は実用上ほぼ中点から 1 エッジ長以内で、
# 超える場合は端点/中点フォールバック(コスト最小選択)が形状を守る。
_FALLBACK_DIST_RATIO = 1.0


def _as_mesh(vertices, faces) -> tuple[np.ndarray, np.ndarray]:
    """(vertices, faces) を検証して (float64 (N,3), int64 (M,3)) に正規化。fail-closed。

    形状不正・非有限・インデックス範囲外・空メッシュは ValueError。
    """
    V = np.asarray(vertices, dtype=np.float64)
    F = np.asarray(faces, dtype=np.int64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"vertices must be (N,3) (received shape={V.shape})")
    if F.ndim != 2 or F.shape[1] != 3:
        raise ValueError(f"faces must be (M,3) (received shape={F.shape})")
    if len(V) == 0 or len(F) == 0:
        raise ValueError("empty mesh (0 vertices or 0 faces)")
    if not np.isfinite(V).all():
        raise ValueError("vertices contains NaN/Inf")
    if F.min() < 0 or F.max() >= len(V):
        raise ValueError(
            f"faces indices are out of range (expected [0,{len(V)}), "
            f"got [{int(F.min())},{int(F.max())}])")
    return V, F


def _face_quadric(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray):
    """三角形の基本二次形式 K=p·pᵀ(4×4)を返す。退化(面積≈0)なら None。

    平面 p=[a,b,c,d]、(a,b,c)=単位法線、d=-n·p0。頂点 v(同次 [x,y,z,1])の
    その平面からの符号付き距離は p·v で、二乗距離 = vᵀ(p·pᵀ)v。
    """
    n = np.cross(p1 - p0, p2 - p0)
    ln = float(np.linalg.norm(n))
    if ln < 1e-14:
        return None
    n = n / ln
    d = -float(n @ p0)
    p = np.array([n[0], n[1], n[2], d], dtype=np.float64)
    return np.outer(p, p)


def _boundary_quadric(pa: np.ndarray, pb: np.ndarray, face_normal: np.ndarray):
    """境界エッジ (a,b) に対する垂直拘束二次形式(重み付き)。退化なら None。

    面に垂直でエッジを通る平面(法線 m = normalize(edge × face_normal))を作り、
    その基本二次形式を ``_BOUNDARY_WEIGHT`` 倍する。境界頂点がこの平面から離れる
    (=境界線から逸れる)動きを強く罰する。
    """
    e = pb - pa
    m = np.cross(e, face_normal)
    lm = float(np.linalg.norm(m))
    if lm < 1e-14:
        return None
    m = m / lm
    d = -float(m @ pa)
    p = np.array([m[0], m[1], m[2], d], dtype=np.float64)
    return _BOUNDARY_WEIGHT * np.outer(p, p)


def _optimal_placement(Qsum: np.ndarray, pi: np.ndarray, pj: np.ndarray):
    """縮約先の (cost, position)。Qsum を最小化する同次点を 4×4 線形系で解く。

    ∂(vᵀQv)/∂v=0 は、Q の上 3 行 + 最下行を [0,0,0,1] に置換した系 A v=[0,0,0,1]。
    特異・非有限・外れ位置なら {pi, pj, mid} の中でコスト最小の候補にフォールバック。
    cost = vᵀ Qsum v(数値誤差の負値は 0 にクランプ)。
    """
    A = Qsum.copy()
    A[3, :] = (0.0, 0.0, 0.0, 1.0)
    b = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)
    pos = None
    try:
        v = np.linalg.solve(A, b)
        if np.all(np.isfinite(v)):
            mid = 0.5 * (pi + pj)
            edge_len = float(np.linalg.norm(pj - pi))
            far = _FALLBACK_DIST_RATIO * max(edge_len, 1e-12)
            if float(np.linalg.norm(v[:3] - mid)) <= far:
                pos = v[:3]
    except np.linalg.LinAlgError:
        pos = None

    if pos is None:
        cands = [np.append(pi, 1.0), np.append(pj, 1.0),
                 np.append(0.5 * (pi + pj), 1.0)]
        costs = [float(c @ Qsum @ c) for c in cands]
        k = int(np.argmin(costs))
        vh = cands[k]
        return max(costs[k], 0.0), vh[:3].copy()

    vh = np.append(pos, 1.0)
    cost = float(vh @ Qsum @ vh)
    return max(cost, 0.0), pos.copy()


def decimate_qem_manifold(vertices, faces, target_faces: int):
    """三角メッシュを目標面数へ簡略化する(境界保存・多様体厳格な QEM edge-collapse)。mesh→mesh。

    ``meshrepair.decimate_qem`` の姉妹 op。同じ QEM edge-collapse だが、境界エッジ拘束
    (Garland boundary term)・link condition(Dey 1999)・4×4 拘束解・外れ位置棄却を足して、
    **開いたメッシュの境界を保存**し **厳密な 2-manifold** を保つ(``decimate_qem`` はこれらを
    持たない — module docstring 参照)。閉曲面では境界が無いので ``decimate_qem`` と挙動が
    近づくのが正しい(差が出るのは開境界を持つメッシュ)。

    形をできるだけ保ったまま面数を減らす。誤差二次形式(quadric error metric)で評価した
    縮約コスト最小の辺から順に collapse し、有効面数が ``target_faces`` 以下になったら停止する。
    非多様体を生む縮約は link condition で拒否するため、素朴なランダム間引きと違って穴・
    非多様体を作らず、元表面への幾何誤差(Hausdorff)を小さく保つ。

    Parameters
    ----------
    vertices : array_like (N,3)
        頂点座標。
    faces : array_like (M,3)
        三角形の頂点インデックス(vertices を参照)。
    target_faces : int
        目標面数(>=4)。現在の面数以上なら簡略化不要としてメッシュをそのまま返す
        (未使用頂点を詰め直した copy)。

    Returns
    -------
    out_vertices : numpy.ndarray (V,3) float64
        簡略化後の頂点(使用頂点のみに詰め直し済み)。
    out_faces : numpy.ndarray (F,3) int64
        簡略化後の三角形(out_vertices を参照)。``F`` は ``target_faces`` 近傍
        (link condition で早期停止すると僅かに上回ることがある — honest に実面数を返す)。

    Raises
    ------
    ValueError
        形状不正・非有限・インデックス範囲外・空メッシュ、または ``target_faces < 4``。
    """
    V0, F0 = _as_mesh(vertices, faces)
    if int(target_faces) < 4:
        raise ValueError(f"target_faces must be >=4 (received {target_faces})")
    target = int(target_faces)

    # 退化(面積 0 / 同一インデックス)面を最初に除く。
    tri = V0[F0]
    areas = 0.5 * np.linalg.norm(
        np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    nondegen = (areas > 1e-14) & (F0[:, 0] != F0[:, 1]) & \
               (F0[:, 1] != F0[:, 2]) & (F0[:, 0] != F0[:, 2])
    F0 = F0[nondegen]
    if len(F0) == 0:
        raise ValueError("no valid faces (all are degenerate)")

    n_faces = len(F0)
    if target >= n_faces:
        return _compact(V0, F0)

    N = len(V0)
    V = V0.copy()
    faces_arr = [list(f) for f in F0.tolist()]     # 可変な面リスト
    valid_f = np.ones(len(faces_arr), dtype=bool)
    valid_v = np.ones(N, dtype=bool)
    vver = np.zeros(N, dtype=np.int64)             # 頂点バージョン(ヒープ stale 判定)
    vf: list[set] = [set() for _ in range(N)]      # 頂点 → 接する面 index 集合
    for fi, (a, b, c) in enumerate(faces_arr):
        vf[a].add(fi); vf[b].add(fi); vf[c].add(fi)

    # --- 1) 頂点ごとの誤差二次形式 Q を積む ---
    Q = np.zeros((N, 4, 4), dtype=np.float64)
    face_normals = {}
    for fi, (a, b, c) in enumerate(faces_arr):
        K = _face_quadric(V[a], V[b], V[c])
        if K is None:
            continue
        Q[a] += K; Q[b] += K; Q[c] += K
        nrm = np.cross(V[b] - V[a], V[c] - V[a])
        face_normals[fi] = nrm / (np.linalg.norm(nrm) + 1e-14)

    # --- 2) 境界エッジ拘束を Q に追加(開いた面のみ効く) ---
    edge_face_count: dict[tuple[int, int], int] = {}
    edge_one_face: dict[tuple[int, int], int] = {}
    for fi, (a, b, c) in enumerate(faces_arr):
        for u, w in ((a, b), (b, c), (a, c)):
            key = (u, w) if u < w else (w, u)
            edge_face_count[key] = edge_face_count.get(key, 0) + 1
            edge_one_face[key] = fi
    for (u, w), cnt in edge_face_count.items():
        if cnt == 1:                               # 境界エッジ
            fi = edge_one_face[(u, w)]
            fn = face_normals.get(fi)
            if fn is None:
                continue
            Kb = _boundary_quadric(V[u], V[w], fn)
            if Kb is not None:
                Q[u] += Kb; Q[w] += Kb

    # --- 3) 初期エッジのコストをヒープへ ---
    counter = [0]
    heap: list = []

    def push_edge(i: int, j: int):
        Qsum = Q[i] + Q[j]
        cost, pos = _optimal_placement(Qsum, V[i], V[j])
        heapq.heappush(heap, (cost, counter[0], i, j, int(vver[i]), int(vver[j]),
                              pos[0], pos[1], pos[2]))
        counter[0] += 1

    seen_edges = set()
    for (u, w) in edge_face_count.keys():
        if (u, w) not in seen_edges:
            seen_edges.add((u, w))
            push_edge(u, w)

    def ring(v: int) -> set:
        """v に隣接する頂点集合(接する面の頂点から v を除く)。"""
        s = set()
        for fi in vf[v]:
            a, b, c = faces_arr[fi]
            s.add(a); s.add(b); s.add(c)
        s.discard(v)
        return s

    # --- 4) 縮約ループ:コスト最小の辺から collapse ---
    while n_faces > target and heap:
        cost, _cnt, i, j, vi, vj, px, py, pz = heapq.heappop(heap)
        # stale 判定(頂点が消えた/位置・Q が更新された)
        if not (valid_v[i] and valid_v[j]):
            continue
        if vver[i] != vi or vver[j] != vj:
            continue
        shared = vf[i] & vf[j]
        if len(shared) == 0:            # もう実エッジでない(stale)
            continue
        if len(shared) > 2:             # 入力が既に非多様体な辺
            continue
        # link condition: ring(i)∩ring(j) が共有面の対頂点集合に一致してこそ多様体保存
        opposite = set()
        for fi in shared:
            for vtx in faces_arr[fi]:
                if vtx != i and vtx != j:
                    opposite.add(vtx)
        if (ring(i) & ring(j)) != opposite:
            continue                    # 非多様体になるので拒否(skip)

        # --- collapse: j を i へ寄せ、i を最適位置 (px,py,pz) に置く ---
        V[i] = (px, py, pz)
        Q[i] = Q[i] + Q[j]
        for fi in list(vf[j]):
            va, vb, vc = faces_arr[fi]
            if i in (va, vb, vc):       # i と j を両方含む面 → 退化 → 削除
                valid_f[fi] = False
                n_faces -= 1
                for vv in (va, vb, vc):
                    vf[vv].discard(fi)
            else:                        # j を i へ張り替え
                faces_arr[fi] = [i if x == j else x for x in faces_arr[fi]]
                vf[i].add(fi)
        valid_v[j] = False
        vf[j] = set()
        vver[i] += 1

        # i 周りのエッジコストを更新(新バージョンで再push、旧entryは stale化)
        for k in ring(i):
            push_edge(i, k)

    # --- 5) 生き残りを詰め直して返す ---
    out_faces = np.array([faces_arr[fi] for fi in range(len(faces_arr))
                          if valid_f[fi]], dtype=np.int64)
    if len(out_faces) == 0:
        raise ValueError("decimation left no faces remaining (target too small)")
    return _compact(V, out_faces)


def _compact(V: np.ndarray, F: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """使用頂点のみに詰め直す(未参照頂点を除去し index を振り直す)。"""
    used = np.unique(F)
    remap = -np.ones(len(V), dtype=np.int64)
    remap[used] = np.arange(len(used))
    return V[used].astype(np.float64), remap[F].astype(np.int64)
