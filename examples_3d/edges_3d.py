"""事例: 3Dスキャンの中実ボールから「表面(境界エッジ)」だけを取り出す (3D edge detection).

問題(やさしい言葉で):
  医療CTや3Dスキャンのように、空間を細かい立方体(ボクセル)で区切った濃淡データがある。
  その中に、中身の詰まったボール(球)が1つ写っている。欲しいのはボールの「表面」――
  中身と外側の境目――だけ。これは2D画像で輪郭線を描くのと同じ「エッジ検出」を、
  3Dの塊に対してやること。

  現実に寄せて、ボールの中身は場所によってなだらかに濃さが変わるようにした(本物のCTでも
  臓器や部品の内部は一様ではない)。ただしボールの外周だけは中身と外側で濃さが急に変わる=
  くっきりした境界。取り出したいのはこの外周の境界だけで、内部のなだらかな濃さ変化は
  エッジではない(=拾ってはいけない)。

方法(この事例で連結して使うop):
  1) gradient3d  … ガウス平滑後の勾配強度(濃さの変化の大きさ)を出す。しきい値の基準と、
                   後述の null(素朴なベースライン)にも使う。
  2) canny3d     … 勾配方向の非最大抑制(NMS)+二閾値ヒステリシスで、境界を1ボクセルに
                   細線化して検出する。これが主役。
  3) log_zero_crossings … LoG(ガウシアンのラプラシアン)のゼロ交差でも同じ境界が出ることを
                   確認する副検証。
  検出maskは edge_points で座標点群に変換して幾何的に検証する。

正解(ground truth)と null(ベースライン):
  合成データなので球の中心と半径Rが既知。よって「検出エッジが本当に球面(半径R±1.5ボクセル)
  に乗っているか」を "オンシェル率" で厳密に測れる。理想は、境界上の検出率が高く、内部・外部の
  誤検出が少ないこと。

  beat-the-null(素朴案を実際に上回ることを assert する):
    null = 生の勾配強度を固定しきい値で二値化するだけ(NMSもヒステリシスも無し)。
    これは (a) なだらかな内部の濃さ変化まで拾ってしまい内部誤検出が大量に出る、
    (b) 境界も細線化されず「ぼやけた厚い帯」になり半径R±1.5から外れる、の二重で外す。
    canny3d は同じしきい値を土台にしつつ NMS+ヒステリシスで内部誤検出をほぼ0にし、
    オンシェル率で null を明確に上回る。これを数値で示して assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import edges3d as E


def make_solid_ball_volume(grid: int = 48, radius: float = 12.0,
                           base: float = 1.0, interior_ramp: float = 0.6):
    """既知の中心・半径をもつ「中実ボール」ボクセル体積を作る。

    ボールの外側 = 0。内側 = base に、なだらかな内部濃さ変化 interior_ramp を足す
    (x方向の線形ランプ)。interior_ramp < base なので内部値は常に正のまま = 外周は
    どこでも中身(>0)と外側(0)でくっきり段差になる=鋭い境界。

    Returns
    -------
    vol : (grid,grid,grid) float64
        濃淡ボクセル体積。
    center : (3,) float64
        球中心の座標 (axis0, axis1, axis2)。
    radius : float
        球半径(=既知の真の境界)。
    """
    if grid < 8:
        raise ValueError(f"grid が小さすぎます: {grid}")
    if not (0 < radius < grid / 2 - 1):
        raise ValueError(f"radius はグリッドに収まる正の値である必要があります: radius={radius}, grid={grid}")
    if not (0.0 <= interior_ramp < base):
        # ランプが base 以上だと内部値が負になり外周の段差が消える(境界が壊れる)。
        raise ValueError(f"interior_ramp は 0<=ramp<base である必要があります: ramp={interior_ramp}, base={base}")

    center = np.array([(grid - 1) / 2.0] * 3, dtype=np.float64)
    zz, yy, xx = np.indices((grid, grid, grid)).astype(np.float64)
    dist = np.sqrt((zz - center[0]) ** 2 + (yy - center[1]) ** 2 + (xx - center[2]) ** 2)
    inside = dist <= radius

    vol = np.zeros((grid, grid, grid), dtype=np.float64)
    vol[inside] = base + interior_ramp * (xx[inside] - center[2]) / radius
    return vol, center, radius


def on_shell_stats(points: np.ndarray, center: np.ndarray, radius: float,
                   tol: float, inner_margin: float = 2.0):
    """検出点群が既知の球面(半径 radius±tol)に乗っているかの統計。

    Parameters
    ----------
    points : (M,3) array
        検出エッジの座標 (axis0,axis1,axis2)。
    center, radius, tol : 球中心 / 半径 / 許容半径ずれ(ボクセル)。
    inner_margin : float
        「明らかに内部」とみなす境界からの内側マージン(誤検出=内部を拾った量の指標)。

    Returns
    -------
    on_shell_rate : float
        検出点のうち |dist-radius| <= tol の割合(=境界に乗っている率)。点が無ければ 0.0。
    n : int
        検出点数。
    interior_fp : int
        dist < radius-inner_margin の点数(=明らかに内部での誤検出)。
    """
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3:
        raise ValueError(f"points は (M,3) である必要があります: shape={pts.shape}")
    if pts.shape[0] == 0:
        return 0.0, 0, 0
    d = np.sqrt(((pts - center) ** 2).sum(axis=1))
    on_shell_rate = float((np.abs(d - radius) <= tol).mean())
    interior_fp = int((d < radius - inner_margin).sum())
    return on_shell_rate, int(pts.shape[0]), interior_fp


def main() -> None:
    grid = 48
    sigma = 1.0
    shell_tol = 1.5  # 「半径R±1.5ボクセルなら境界上」とみなす許容ずれ

    # --- 1) 合成データ: 既知の中心・半径をもつ中実ボール(内部はなだらかに濃さが変化) ---
    vol, center, radius = make_solid_ball_volume(grid=grid, radius=12.0,
                                                 base=1.0, interior_ramp=0.6)

    # 入力の健全性チェック(退化入力で偽の成功を出さないため)。
    if vol.ndim != 3:
        raise ValueError(f"vol は3次元である必要があります: shape={vol.shape}")
    n_inside = int((vol > 0).sum())
    if not (0 < n_inside < vol.size):
        raise RuntimeError(f"ボールが退化しています(内側 {n_inside} / 全体 {vol.size}) — 境界が存在しません")

    # --- 2) gradient3d: ガウス平滑後の勾配強度。しきい値の基準+null に使う ---
    gmag, gvec = E.gradient3d(vol, sigma=sigma)
    if gmag.shape != vol.shape or gvec.shape != vol.shape + (3,):
        raise RuntimeError(f"gradient3d の返り形状が不正: gmag={gmag.shape}, gvec={gvec.shape}")
    gmax = float(gmag.max())
    if not np.isfinite(gmax) or gmax <= 0.0:
        # 完全平坦=境界なし。ここで PASS を出すのは嘘になるので停止する。
        raise RuntimeError(f"勾配が全てゼロ(gmax={gmax}) — 境界が検出できない退化ケース")

    low = 0.08 * gmax
    high = 0.35 * gmax

    # --- 3) canny3d(主役): NMS+ヒステリシスで境界を1ボクセルに細線化 ---
    canny_mask = E.canny3d(vol, low, high, sigma=sigma)
    if canny_mask.shape != vol.shape or canny_mask.dtype != np.bool_:
        raise RuntimeError(f"canny3d の返り値が不正: shape={canny_mask.shape}, dtype={canny_mask.dtype}")
    canny_pts = E.edge_points(canny_mask)
    if canny_pts.shape[0] == 0:
        # 何も検出できていない状態で成功扱いにしない。
        raise RuntimeError("canny3d が1つもエッジを検出しませんでした — しきい値/入力を見直す必要があります")

    # --- 4) null(ベースライン): 生の勾配を同じ low で固定しきい値化しただけ ---
    null_mask = gmag >= low
    null_pts = np.argwhere(null_mask).astype(np.float64)  # (M,3) = (z,y,x)

    # --- 5) log_zero_crossings(副検証): LoGゼロ交差でも同じ境界が出るか ---
    log_mask = E.log_zero_crossings(vol, sigma=1.5)
    if log_mask.shape != vol.shape:
        raise RuntimeError(f"log_zero_crossings の返り形状が不正: {log_mask.shape}")
    log_pts = E.edge_points(log_mask)

    # --- 6) GT検証: 既知の球面(半径R±tol)にどれだけ乗っているか ---
    canny_on, canny_n, canny_ifp = on_shell_stats(canny_pts, center, radius, shell_tol)
    null_on, null_n, null_ifp = on_shell_stats(null_pts, center, radius, shell_tol)
    log_on, log_n, log_ifp = on_shell_stats(log_pts, center, radius, shell_tol)

    print(f"合成ボール           : grid={grid}^3, 中心={center.tolist()}, 半径R={radius}")
    print(f"勾配強度 gmag.max()  : {gmax:.4f}  (low={low:.4f}, high={high:.4f})")
    print(f"許容半径ずれ tol     : {shell_tol} ボクセル (|dist-R|<=tol なら境界上)")
    print("-" * 68)
    print(f"canny3d (主役)       : オンシェル率={canny_on:.3f}  検出={canny_n:5d}  内部誤検出={canny_ifp}")
    print(f"log_zero_crossings   : オンシェル率={log_on:.3f}  検出={log_n:5d}  内部誤検出={log_ifp}")
    print(f"null 生勾配しきい値   : オンシェル率={null_on:.3f}  検出={null_n:5d}  内部誤検出={null_ifp}")
    print("-" * 68)
    print(f"beat-the-null 差     : canny {canny_on:.3f} - null {null_on:.3f} = {canny_on - null_on:+.3f}")

    # --- 7) アサーション ---
    # (a) canny は既知の球面に高い精度で乗る。
    assert canny_n > 500, f"canny の検出数が少なすぎる: {canny_n}"
    assert canny_on >= 0.90, f"canny のオンシェル率が低い: {canny_on:.3f}"
    # (b) canny は内部誤検出がほぼ0(なだらかな内部を拾わない)。
    assert canny_ifp <= max(5, int(0.01 * canny_n)), \
        f"canny の内部誤検出が多い: {canny_ifp} (検出 {canny_n})"
    # (c) beat-the-null: canny のオンシェル率が null を明確に上回る。
    assert (canny_on - null_on) >= 0.20, \
        f"canny が null を十分上回っていない: canny {canny_on:.3f} vs null {null_on:.3f}"
    # (d) null は実際に「なだらかな内部」を大量に拾って外している(素朴案の失敗を実証)。
    assert null_ifp >= 100, f"null が内部を拾う失敗を再現できていない: 内部誤検出={null_ifp}"
    assert null_ifp > 10 * (canny_ifp + 1), \
        f"null の内部誤検出が canny と差がない: null {null_ifp} vs canny {canny_ifp}"
    # (e) 副検証: log_zero_crossings も同じ境界に乗る。
    assert log_n > 300, f"log_zero_crossings の検出数が少なすぎる: {log_n}"
    assert log_on >= 0.90, f"log_zero_crossings のオンシェル率が低い: {log_on:.3f}"
    assert log_ifp <= max(5, int(0.01 * log_n)), \
        f"log_zero_crossings の内部誤検出が多い: {log_ifp}"

    print(
        "PASS: canny3d は既知の球面(R±{tol})に乗り(オンシェル率 {c:.3f}・内部誤検出 {cifp})、"
        "生勾配しきい値の null(オンシェル率 {n:.3f}・内部誤検出 {nifp})を +{d:.3f} 上回った。"
        "log_zero_crossings も同境界を再現(オンシェル率 {l:.3f})。".format(
            tol=shell_tol, c=canny_on, cifp=canny_ifp,
            n=null_on, nifp=null_ifp, d=canny_on - null_on, l=log_on)
    )


if __name__ == "__main__":
    main()
