"""Fullseye 統一 I/F — OSS アダプタ契約(F4).

要件 F4: OSS(OpenCV/scikit-image 等)を裏に持つ op も、統一 I/F(F1 設定オブジェクト+動詞
メソッド / F3 introspection)で同一に見える。**OSS 不在時は genuine numpy フォールバックへ
graceful に切替**(optional extras 方針 N3)。使う側は backend を意識せず同じ作法で呼べる。

  from oss_adapter import stereo, filter, features, contour
  disp = stereo.BlockMatching(max_disp=64).compute(left, right)   # cv2.StereoBM or numpy
  print(stereo.BlockMatching().backend)                           # "opencv" / "numpy(fallback)"
  out  = filter.Bilateral(d=5, sigma_color=0.1).apply(image)      # cv2 or scipy
  kps  = features.ORB(n=200).detect(image)                        # cv2.ORB or Harris(numpy)
  cs   = contour.FindContours(level=0.5).find(image)              # cv2.findContours or skimage/numpy

★契約: 各アダプタは (1) config オブジェクト(意味ある名前付き引数)(2) 動詞メソッド
(.compute/.apply/.detect/.find)(3) `.backend` プロパティ(実際に使うバックエンド)
(4) OSS 不在でも動く numpy フォールバック、を満たす。結果は同種(視差画像/画像/keypoints/contour)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _have(pkg: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(pkg) is not None


_HAS_CV2 = _have("cv2")
_HAS_SKIMAGE = _have("skimage")


def _to_u8(img):
    a = np.asarray(img, np.float64)
    return np.clip(a * 255, 0, 255).astype(np.uint8)


# ── stereo: 視差(OpenCV StereoBM/SGBM ↔ numpy fallback)────────────────────────── #
@dataclass
class BlockMatching:
    """ブロックマッチング視差(cv2.StereoBM、不在時 fullseye numpy)(stereo.BlockMatching)。"""
    max_disp: int = 64
    window: int = 15
    prefer: str = "auto"           # auto / opencv / numpy

    @property
    def backend(self) -> str:
        return "opencv" if (self.prefer != "numpy" and _HAS_CV2) else "numpy(fallback)"

    def compute(self, left, right):
        if self.backend == "opencv":
            import cv2
            nd = max(16, (self.max_disp // 16) * 16)
            bs = self.window if self.window % 2 == 1 else self.window + 1
            bm = cv2.StereoBM_create(numDisparities=nd, blockSize=max(5, bs))
            disp = bm.compute(_to_u8(left), _to_u8(right)).astype(np.float64) / 16.0
            return np.clip(disp, 0, None)
        import fullseye as fs
        return fs.disparity_map(np.asarray(left, float), np.asarray(right, float),
                                max_disp=self.max_disp, block=7)


@dataclass
class SGBM:
    """Semi-Global BM 視差(cv2.StereoSGBM、不在時 fullseye SGM numpy)(stereo.SGBM)。"""
    max_disp: int = 64
    window: int = 5
    prefer: str = "auto"

    @property
    def backend(self) -> str:
        return "opencv" if (self.prefer != "numpy" and _HAS_CV2) else "numpy(fallback)"

    def compute(self, left, right):
        if self.backend == "opencv":
            import cv2
            nd = max(16, (self.max_disp // 16) * 16)
            sg = cv2.StereoSGBM_create(minDisparity=0, numDisparities=nd, blockSize=self.window,
                                       P1=8 * self.window ** 2, P2=32 * self.window ** 2)
            disp = sg.compute(_to_u8(left), _to_u8(right)).astype(np.float64) / 16.0
            return np.clip(disp, 0, None)
        import fullseye as fs
        return fs.disparity_sgm(np.asarray(left, float), np.asarray(right, float),
                                max_disp=self.max_disp, window=self.window)


# ── filter: bilateral(cv2 ↔ scipy/numpy)──────────────────────────────────────── #
@dataclass
class Bilateral:
    """エッジ保存平滑化(cv2.bilateralFilter、不在時 numpy 実装)(filter.Bilateral)。"""
    d: int = 5
    sigma_color: float = 0.1
    sigma_space: float = 3.0
    prefer: str = "auto"

    @property
    def backend(self) -> str:
        return "opencv" if (self.prefer != "numpy" and _HAS_CV2) else "numpy(fallback)"

    def apply(self, image):
        im = np.asarray(image, np.float64)
        if self.backend == "opencv":
            import cv2
            out = cv2.bilateralFilter(im.astype(np.float32), self.d,
                                      self.sigma_color, self.sigma_space)
            return out.astype(np.float64)
        # numpy fallback: 素朴な bilateral(近傍ガウス×輝度差ガウス)
        from scipy.ndimage import gaussian_filter
        r = max(1, self.d // 2)
        out = np.zeros_like(im); wsum = np.zeros_like(im)
        for dr in range(-r, r + 1):
            for dc in range(-r, r + 1):
                shifted = np.roll(np.roll(im, dr, 0), dc, 1)
                gs = np.exp(-(dr ** 2 + dc ** 2) / (2 * self.sigma_space ** 2))
                gc = np.exp(-((im - shifted) ** 2) / (2 * self.sigma_color ** 2))
                w = gs * gc
                out += w * shifted; wsum += w
        return out / (wsum + 1e-12)


# ── features: ORB / corners(cv2 ↔ Harris numpy)───────────────────────────────── #
@dataclass
class ORB:
    """ORB キーポイント(cv2.ORB、不在時 Harris コーナー numpy)(features.ORB)。"""
    n: int = 200
    prefer: str = "auto"

    @property
    def backend(self) -> str:
        return "opencv" if (self.prefer != "numpy" and _HAS_CV2) else "numpy(fallback)"

    def detect(self, image):
        if self.backend == "opencv":
            import cv2
            orb = cv2.ORB_create(nfeatures=self.n)
            kps = orb.detect(_to_u8(image), None)
            return np.array([[k.pt[1], k.pt[0]] for k in kps]) if kps else np.zeros((0, 2))
        from matching3d import _harris_keypoints
        return _harris_keypoints(np.asarray(image, float), max_pts=self.n)


# ── contour: 輪郭抽出(cv2.findContours ↔ skimage/numpy)───────────────────────── #
@dataclass
class FindContours:
    """2 値/レベルからの輪郭抽出(cv2.findContours、不在時 skimage、なければ numpy)
    (contour.FindContours)。戻り値 = fullseye contour dict {shape, cs}。"""
    level: float = 0.5
    prefer: str = "auto"

    @property
    def backend(self) -> str:
        if self.prefer == "numpy":
            return "numpy(fallback)"
        if _HAS_CV2:
            return "opencv"
        if _HAS_SKIMAGE:
            return "skimage"
        return "numpy(fallback)"

    def find(self, image):
        im = np.asarray(image, np.float64)
        shape = im.shape
        be = self.backend
        if be == "opencv":
            import cv2
            mask = (im > self.level).astype(np.uint8)
            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cs = [c.reshape(-1, 2)[:, ::-1].astype(float) for c in cnts if len(c) >= 2]  # (x,y)->(row,col)
            return {"shape": shape, "cs": cs}
        if be == "skimage":
            from skimage import measure
            cs = [np.asarray(c, float) for c in measure.find_contours(im, self.level)]
            return {"shape": shape, "cs": cs}
        # numpy fallback: 境界画素を角度順に並べる(粗い単一輪郭)
        from scipy.ndimage import binary_erosion
        m = im > self.level
        border = m & ~binary_erosion(m)
        rs, cs_ = np.where(border)
        if rs.size == 0:
            return {"shape": shape, "cs": []}
        pts = np.column_stack([rs, cs_]).astype(float)
        c = pts.mean(0); ang = np.arctan2(pts[:, 0] - c[0], pts[:, 1] - c[1])
        return {"shape": shape, "cs": [pts[np.argsort(ang)]]}


# ── 名前空間(Qt 風)+ アダプタ列挙 ─────────────────────────────────────────────── #
class stereo:   # noqa: N801
    BlockMatching = BlockMatching
    SGBM = SGBM


class filter:   # noqa: N801  (組込み filter を隠すのは本モジュール内のみ)
    Bilateral = Bilateral


class features:  # noqa: N801
    ORB = ORB


class contour:  # noqa: N801
    FindContours = FindContours


ADAPTERS = [
    ("stereo", "BlockMatching", BlockMatching, "image"),
    ("stereo", "SGBM", SGBM, "image"),
    ("filter", "Bilateral", Bilateral, "image"),
    ("features", "ORB", ORB, "scalar"),
    ("contour", "FindContours", FindContours, "contour"),
]


def backends() -> dict:
    """各アダプタが実際に使うバックエンドの honest レポート(Studio/エージェント用)。"""
    return {f"{ns}.{cls.__name__}": cls().backend for ns, name, cls, _ in ADAPTERS}


if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore")
    print("== Fullseye OSS アダプタ契約(F4)==")
    print("OSS 検出: cv2", _HAS_CV2, "/ skimage", _HAS_SKIMAGE)
    for k, be in backends().items():
        print(f"  {k:24} backend={be}")
    rng = np.random.default_rng(0)
    from scipy.ndimage import gaussian_filter
    left = gaussian_filter(rng.random((64, 96)), 1.0)
    right = np.roll(left, 4, axis=1)
    d = stereo.SGBM(max_disp=32).compute(left, right)
    print(f"\nstereo.SGBM().compute(l,r) -> {d.shape} 中央値視差 {np.median(d[d>0]) if (d>0).any() else 0:.1f}")
    kp = features.ORB(n=100).detect(left)
    print(f"features.ORB(n=100).detect(img) -> {len(kp)} keypoints")
    cs = contour.FindContours(level=0.5).find((left > 0.5).astype(float))
    print(f"contour.FindContours().find(mask) -> {len(cs['cs'])} contours")
    b = filter.Bilateral(d=5).apply(left)
    print(f"filter.Bilateral().apply(img) -> {b.shape}")
