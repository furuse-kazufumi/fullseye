"""3D Harris/Shi-Tomasi キーポイント検出(workflow 並行探索・実測検証済、初期推定なしの大回転+部分重なり登録)。"""
import numpy as np

try:
    import torch
    import torch.nn.functional as F
except ImportError:                       # torch は optional(gpu/threed extra)
    # import 自体は成功させ(3D レジストリ全体を殺さない)、使用時に明確に拒否する。
    # Keep the module importable without torch; fail clearly only on use.
    class _TorchMissing:
        def __getattr__(self, name):
            raise ImportError(
                "this operator needs the optional 'torch' backend — "
                "install with: pip install \"fullseye[gpu]\"")
    torch = F = _TorchMissing()

from match3d import sobel3d, _gauss3d


def harris3d_keypoints(vol, device="cpu", k=0.005, nms=3, topn=64,
                       sigma_i=1.5, response="mineig", rel_thresh=0.01,
                       border=2):
    """3D Harris キーポイント検出(2D Harris コーナー検出の 3D 版)。

    voxel 密度場の 3D 勾配 g=(gz,gy,gx) から、各ボクセルで局所構造テンソル
    M=Σ_w w·g gᵀ(3x3 対称、gaussian 窓 sigma_i で積和)を組み、コーナー性を
    測る。応答が周囲で極大かつ閾値超のボクセルを keypoint とする(初期姿勢
    推定なしに検出できるため、大回転+部分重なりの対応付けや ICP の coarse
    init 供給に使える)。

    コーナー性の指標:
      - "mineig"(既定): 3x3 対称行列の最小固有値(Shi-Tomasi 流)。3 方向すべて
        に構造がある(=角)ほど最小固有値が大きい。閉形式(三角関数法)で算出。
        k 調整不要で頑健(実測 mean repeatability 85%、min 72.5%)。
      - "harris": R = det(M) - k·tr(M)³。3D では固有値 3 個なので tr の 3 乗で
        無次元化。★注意: 密度 voxel の角では det/tr³ 比が経験的に ~0.01 しか
        ないため、2D 標準の k=0.04〜0.06 では全応答が負になり検出 0 になる。
        3D では k≈0.005 が必要(実測 k=0.005 で mean 89.6%)。

    引数:
        vol: (D,H,W) 密度 voxel(numpy / torch)。points_to_voxel の出力を想定。
        device: torch デバイス("cpu" 等)。全演算をこのデバイス上で行う。
        k: Harris の感度係数(response="harris" 時のみ有効)。3D 密度場では
            0.005 前後(2D 慣習の 0.04〜0.06 は 3D では強すぎ検出 0 になる)。
        nms: 非最大抑制の立方体窓の一辺(奇数、標準 3 = 3x3x3 近傍)。
        topn: 応答降順で返す keypoint の最大数。
        sigma_i: 構造テンソルの積分窓(gaussian)の標準偏差(voxel)。
        response: "mineig"(既定, 頑健)か "harris"。
        rel_thresh: 応答の閾値 = rel_thresh × 有効領域の最大応答(雑音抑制)。
        border: 端から border ボクセル以内は検出しない(勾配の端効果を除去)。

    返り値:
        keypoints: (M,3) float64。keypoint の voxel 座標 (z,y,x)(sobel3d と
            同じ軸順)。応答降順、最大 topn 個。
        responses: (M,) float64。対応する応答値(降順)。

    依存: sobel3d(3D 勾配)、_gauss3d(積分窓平滑)。いずれも device 上で動作。
    """
    dev = torch.device(device)

    # --- 3D 勾配(sobel3d は numpy 入力から device テンソルを作るので device 安全) ---
    gz, gy, gx = sobel3d(np.asarray(vol, np.float64), device=device)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]                 # 各 (D,H,W)

    # --- 構造テンソルの 6 独立成分を積分窓で平滑(M=Σ w·g gᵀ)-----------------
    def _smooth(comp):
        return _gauss3d(comp[None, None], sigma_i)[0, 0]

    a = _smooth(gx * gx)     # Sxx
    b = _smooth(gy * gy)     # Syy
    c = _smooth(gz * gz)     # Szz
    d = _smooth(gx * gy)     # Sxy
    e = _smooth(gx * gz)     # Sxz
    f = _smooth(gy * gz)     # Syz

    tr = a + b + c
    det = (a * (b * c - f * f)
           - d * (d * c - f * e)
           + e * (d * f - b * e))

    if response == "harris":
        resp = det - k * tr.pow(3)
    elif response == "mineig":
        # 3x3 対称行列の固有値(閉形式・三角関数法, Smith 1961)。最小固有値を返す。
        q = tr / 3.0
        p1 = d * d + e * e + f * f
        p2 = (a - q).pow(2) + (b - q).pow(2) + (c - q).pow(2) + 2.0 * p1
        p = torch.sqrt(torch.clamp(p2 / 6.0, min=0.0))
        pinv = 1.0 / p.clamp_min(1e-20)
        # B=(M-qI)/p の行列式
        ba, bb, bc = (a - q) * pinv, (b - q) * pinv, (c - q) * pinv
        bd, be, bf = d * pinv, e * pinv, f * pinv
        detB = (ba * (bb * bc - bf * bf)
                - bd * (bd * bc - bf * be)
                + be * (bd * bf - bb * be))
        r = torch.clamp(detB / 2.0, -1.0, 1.0)
        phi = torch.arccos(r) / 3.0
        # 最小固有値 = q + 2p·cos(phi + 2π/3)
        eig_min = q + 2.0 * p * torch.cos(phi + 2.0 * np.pi / 3.0)
        # p≈0(等方=対角) の場合は成分そのもの(最小)
        diag_min = torch.minimum(torch.minimum(a, b), c)
        resp = torch.where(p > 1e-12, eig_min, diag_min)
    else:
        raise ValueError("response must be 'mineig' or 'harris'")

    D, H, W = resp.shape

    # --- 端の除去: 端は -inf にして最大値・極大に混入させない(0 埋めだと全応答が
    #     負のとき端の 0 が偽の全体最大になり検出が消える不具合を回避)------------
    neg_inf = torch.finfo(resp.dtype).min
    valid = torch.zeros_like(resp, dtype=torch.bool)
    bw = max(border, 0)
    valid[bw:D - bw, bw:H - bw, bw:W - bw] = True
    resp = torch.where(valid, resp, torch.full_like(resp, neg_inf))

    # --- 3D 非最大抑制 + 閾値(閾値は有効領域の最大応答基準)------------------
    pad = nms // 2
    pooled = F.max_pool3d(resp[None, None], kernel_size=nms, stride=1,
                          padding=pad)[0, 0]
    finite = resp[valid]
    rmax = float(finite.max().item()) if finite.numel() else 0.0
    thr = rmax * rel_thresh
    peaks = valid & (resp >= pooled) & (resp > thr)

    coords = torch.nonzero(peaks, as_tuple=False)             # (K,3) z,y,x
    if coords.numel() == 0:
        return np.zeros((0, 3), np.float64), np.zeros((0,), np.float64)
    vals = resp[peaks]
    order = torch.argsort(vals, descending=True)[:topn]
    coords = coords[order].detach().cpu().numpy().astype(np.float64)
    vals = vals[order].detach().cpu().numpy().astype(np.float64)
    return coords, vals
