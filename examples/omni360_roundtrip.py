"""全方位画像を既存の画像処理へ渡し、通常画像を全方位表示へ戻す最小例。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import omni360 as omni  # noqa: E402
from scipy.ndimage import sobel  # noqa: E402


h, w = 128, 256
dirs = omni.equirect_to_dir(h, w)
panorama = .5 + .25 * dirs[..., 0] + .2 * (dirs[..., 1] > .2)

# Device output -> an existing inspection primitive.
viewport = omni.viewport_from_equirect(panorama, yaw=35, pitch=-10, fov_deg=80, size=(96, 128))
edges = np.hypot(sobel(viewport, 0), sobel(viewport, 1))

# Existing image generator -> device input (six cubemap faces).
checker = ((np.indices((64, 128)).sum(0) // 8) % 2).astype(float)
faces = omni.cubemap_from_equirect(checker, 48)
restored = omni.equirect_from_cubemap(faces, checker.shape)

print("viewport", viewport.shape, "edge maximum", float(edges.max()))
print("cubemap", faces.shape, "WS-PSNR", omni.ws_psnr(checker, restored))
