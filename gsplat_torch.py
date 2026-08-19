"""純 PyTorch 3D Gaussian Splatting(CUDA コンパイル不要)。

gsplat ネイティブは Windows で CUDA Toolkit+MSVC を要するため、コンパイラ無しでも
RTX 5090 上で 3DGS を end-to-end 実証するための参照実装。tile 分割なし・大域深度ソート
の簡略版(小シーン/PoC 向け)。学習が進むこと(PSNR 上昇)を honest に測るのが目的。

規約: transforms.json の transform_matrix は OpenGL c2w(+X右/+Y上/-Z前方)。
内部で CV カメラ(z 前方正/y 下)へ F=diag(1,-1,-1) 変換して標準 3DGS 数式を使う。
"""
from __future__ import annotations
import numpy as np
import torch

_F = torch.tensor([[1., 0, 0], [0, -1., 0], [0, 0, -1.]])   # OpenGL->CV flip


def quat_to_rotmat(q: torch.Tensor) -> torch.Tensor:
    """(N,4) wxyz 四元数 -> (N,3,3) 回転行列。"""
    q = q / q.norm(dim=-1, keepdim=True).clamp_min(1e-9)
    w, x, y, z = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    N = q.shape[0]
    R = torch.empty(N, 3, 3, device=q.device, dtype=q.dtype)
    R[:, 0, 0] = 1 - 2 * (y * y + z * z); R[:, 0, 1] = 2 * (x * y - w * z); R[:, 0, 2] = 2 * (x * z + w * y)
    R[:, 1, 0] = 2 * (x * y + w * z); R[:, 1, 1] = 1 - 2 * (x * x + z * z); R[:, 1, 2] = 2 * (y * z - w * x)
    R[:, 2, 0] = 2 * (x * z - w * y); R[:, 2, 1] = 2 * (y * z + w * x); R[:, 2, 2] = 1 - 2 * (x * x + y * y)
    return R


class GaussianModel:
    """3D ガウシアン群(means/scales(log)/quats/colors(logit? いや0-1)/opacity(logit))。"""

    def __init__(self, means, colors, scales, device="cuda"):
        n = means.shape[0]
        self.means = torch.nn.Parameter(torch.as_tensor(means, dtype=torch.float32, device=device))
        self.log_scales = torch.nn.Parameter(torch.log(torch.as_tensor(scales, dtype=torch.float32, device=device).clamp_min(1e-4)))
        q = torch.zeros(n, 4, device=device); q[:, 0] = 1.0
        self.quats = torch.nn.Parameter(q)
        self.colors = torch.nn.Parameter(torch.logit(torch.as_tensor(colors, dtype=torch.float32, device=device).clamp(1e-4, 1 - 1e-4)))
        self.raw_opacity = torch.nn.Parameter(torch.full((n,), 2.0, device=device))   # sigmoid(2)=0.88
        self.device = device

    def params(self):
        return [self.means, self.log_scales, self.quats, self.colors, self.raw_opacity]

    @property
    def n(self):
        return self.means.shape[0]


def render(gm: GaussianModel, c2w: torch.Tensor, K: torch.Tensor, H: int, W: int,
           bg=(0.29, 0.30, 0.31)):
    """1 ビューをレンダリング(大域ソート alpha 合成)。戻り値 (H,W,3) in [0,1]。"""
    dev = gm.device
    Fm = _F.to(dev)
    w2c = torch.linalg.inv(c2w)
    Rcv = Fm @ w2c[:3, :3]                       # world->CV 回転
    tcv = Fm @ w2c[:3, 3]
    mu_cam = gm.means @ Rcv.T + tcv              # (N,3) CV カメラ座標
    z = mu_cam[:, 2]
    front = z > 1e-3
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    u = fx * mu_cam[:, 0] / z.clamp_min(1e-3) + cx
    v = fy * mu_cam[:, 1] / z.clamp_min(1e-3) + cy
    # 3D 共分散 -> 2D
    Rg = quat_to_rotmat(gm.quats)
    S = torch.exp(gm.log_scales)
    M = Rg * S[:, None, :]                        # R @ diag(S)
    Sigma = M @ M.transpose(1, 2)                # (N,3,3) world 共分散
    Wm = Rcv                                      # world->CV
    SigmaCam = Wm @ Sigma @ Wm.T
    zc = z.clamp_min(1e-3)
    J = torch.zeros(gm.n, 2, 3, device=dev)
    J[:, 0, 0] = fx / zc; J[:, 0, 2] = -fx * mu_cam[:, 0] / (zc * zc)
    J[:, 1, 1] = fy / zc; J[:, 1, 2] = -fy * mu_cam[:, 1] / (zc * zc)
    cov2d = J @ SigmaCam @ J.transpose(1, 2)     # (N,2,2)
    cov2d[:, 0, 0] += 0.2; cov2d[:, 1, 1] += 0.2  # anti-alias blur
    det = cov2d[:, 0, 0] * cov2d[:, 1, 1] - cov2d[:, 0, 1] * cov2d[:, 1, 0]
    det = det.clamp_min(1e-9)
    inv = torch.stack([cov2d[:, 1, 1], -cov2d[:, 0, 1], -cov2d[:, 1, 0], cov2d[:, 0, 0]], -1).reshape(-1, 2, 2) / det[:, None, None]
    opacity = torch.sigmoid(gm.raw_opacity)
    color = torch.sigmoid(gm.colors)
    # 有効ガウシアンのみ
    valid = front & (u > -50) & (u < W + 50) & (v > -50) & (v < H + 50)
    idx = torch.nonzero(valid, as_tuple=True)[0]
    if idx.numel() == 0:
        return torch.tensor(bg, device=dev).expand(H, W, 3).clone()
    order = torch.argsort(z[idx])                # near->far
    idx = idx[order]
    uu, vv, invv, oo, cc = u[idx], v[idx], inv[idx], opacity[idx], color[idx]
    ys, xs = torch.meshgrid(torch.arange(H, device=dev, dtype=torch.float32),
                            torch.arange(W, device=dev, dtype=torch.float32), indexing="ij")
    px = torch.stack([xs.reshape(-1), ys.reshape(-1)], -1)   # (P,2)
    dx = px[None, :, 0] - uu[:, None]            # (K,P)
    dy = px[None, :, 1] - vv[:, None]
    a = invv[:, 0, 0][:, None]; b = invv[:, 0, 1][:, None]; c = invv[:, 1, 1][:, None]
    power = -0.5 * (a * dx * dx + 2 * b * dx * dy + c * dy * dy)
    alpha = (oo[:, None] * torch.exp(power.clamp(max=0.0))).clamp(0, 0.999)   # (K,P)
    # front->back 合成: T_i = prod_{j<i}(1-alpha_j)
    log1m = torch.log((1 - alpha).clamp_min(1e-6))
    Tacc = torch.cumsum(log1m, dim=0) - log1m    # 排他 prefix
    weight = alpha * torch.exp(Tacc)             # (K,P)
    img = (weight[:, :, None] * cc[:, None, :]).sum(0)      # (P,3)
    Tfinal = torch.exp(torch.cumsum(log1m, dim=0)[-1])       # (P,)
    img = img + Tfinal[:, None] * torch.tensor(bg, device=dev)
    return img.reshape(H, W, 3).clamp(0, 1)


def psnr(a: torch.Tensor, b: torch.Tensor) -> float:
    mse = torch.mean((a - b) ** 2).item()
    return float("inf") if mse < 1e-12 else 10.0 * np.log10(1.0 / mse)


def knn_scale(points: np.ndarray, k: int = 3) -> np.ndarray:
    """最近傍平均距離を初期スケールに(等方)。O(N^2) の素朴実装(PoC 規模)。"""
    p = np.asarray(points, np.float32)
    n = len(p)
    if n <= 1:
        return np.full((n, 3), 0.02, np.float32)
    d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    kk = min(k, n - 1)
    nn = np.sort(d, axis=1)[:, :kk].mean(1)
    s = np.clip(nn, 1e-3, None).astype(np.float32)
    return np.repeat(s[:, None], 3, axis=1)
