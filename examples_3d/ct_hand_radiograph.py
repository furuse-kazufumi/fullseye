"""骨格CTからX線ラジオグラフ(DRR)を合成する例。

実世界の問題:
    3D の X線CT ボリューム(密度場)を、放射線科医が見慣れた 1 枚の 2D X線写真へ
    「畳み込む」。これは DRR (Digitally Reconstructed Radiograph, デジタル再構成
    X線画像) と呼ばれ、CT ↔ 実写 X線のレジストレーション(IGRT/放射線治療位置合わせ)
    や、術前計画の下絵づくりの基礎になる。

原理:
    X線写真の各画素は、線源から検出器まで直進する 1 本のレイが通過した物質の
    「減衰の積算」。Beer–Lambert 則を線形近似すると、これは密度ボリュームを
    レイ方向へ単純に総和したものになる。ここでは手を厚み方向(掌→甲, z 軸)に
    沿って積算し、手の平面(縦 y × 横 x)に投影する。

    fullseye には match3d.render_volume_projection(vol, azimuth, elevation, mode="xray")
    があり、任意視点の DRR を生成できる(torch 使用)。azimuth=elevation=0 のとき、
    それはまさに z 軸方向の総和 = 本例の np.sum(axis=0) と一致する(Beer–Lambert 積算)。
    ここでは numpy/scipy だけで完結させたいので np.sum を使う。
"""
from __future__ import annotations

import os
import sys

import numpy as np

# --- fullseye モジュールを import 可能にする(リポジトリルートを sys.path へ) ---
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# 投影の本体は torch 非依存の np.sum で行う(この例は最小構成でも動く)。
# そのうえで、レジストリ側の match3d.render_volume_projection が**同じ絵を出すか**を
# 実際に呼んで確かめる。★2026-09-05 まで、この例は「azimuth=elevation=0 なら
# np.sum(axis=0) と一致」と書きながら**一度も確かめていなかった**。しかも
# op → example の索引が hasattr の文字列を呼び出しと誤認していたため、
# 「例が 1 つも無い op」が 100% カバレッジの中に隠れていた。
try:
    import match3d
    _HAS_RENDER = hasattr(match3d, "render_volume_projection")
except Exception:  # pragma: no cover - torch 不在などでも本例は動く
    match3d = None
    _HAS_RENDER = False


def load_volume() -> np.ndarray:
    """ボクセル化した実 MS-Human-700 手骨メッシュ由来の合成 X線CT 密度場を読む。"""
    path = os.path.join(_REPO_ROOT, "studio_assets", "sample_3d", "skeleton_ct.npy")
    vol = np.load(path).astype(np.float64)
    return vol


def synthesize_radiograph(vol: np.ndarray) -> np.ndarray:
    """厚み方向(軸 0 = z, 掌→甲)へ密度を積算して 2D の手 X線写真を作る。

    shape (z, y, x) の z を潰し、(y, x) = 手の縦×横 の DRR を返す。
    """
    # X線減衰の線形近似 = レイ方向(z)への密度総和(Beer–Lambert 積算の近似)。
    return vol.sum(axis=0)


def cross_check_registry_op(vol: np.ndarray, drr: np.ndarray) -> None:
    """レジストリの ``render_volume_projection`` を**実際に呼び**、np.sum と突き合わせる。

    正面(azimuth=elevation=0)の X線投影は厚み軸の総和そのものなので、
    両者は一致しなければならない。一致を**測る**ことで、この例は
    「op を持っている」ではなく「op が正しい」を主張できる。

    実測(2026-09-05、studio_assets/sample_3d/skeleton_ct.npy = (20,97,28)):
      絶対差 最大 1.9e-05 / 中央 1.8e-07(op 内部が float32 を経由するため)
    """
    if not _HAS_RENDER:
        print("[SKIP] match3d.render_volume_projection が無い(torch 不在)ため突き合わせを省略")
        return
    got = np.asarray(
        match3d.render_volume_projection(vol, azimuth=0.0, elevation=0.0, mode="xray"),
        dtype=np.float64)
    assert got.shape == drr.shape, f"形が違う: op {got.shape} vs np.sum {drr.shape}"
    err = float(np.abs(got - drr).max())
    tol = 1e-3 * float(drr.max())
    assert err <= tol, (
        f"op と np.sum(axis=0) が一致しない: 最大差 {err:.3e} > 許容 {tol:.3e}")
    print(f"[GT] render_volume_projection == np.sum(axis=0): 最大差 {err:.3e} "
          f"(許容 {tol:.3e}、op は内部で float32 を経由する)")


def main() -> int:
    vol = load_volume()
    print(f"[GT] volume shape (z,y,x) = {vol.shape}, "
          f"density range [{vol.min():.3f}, {vol.max():.3f}]")
    print(f"[GT] match3d.render_volume_projection available = {_HAS_RENDER}")

    z, y, x = vol.shape
    drr = synthesize_radiograph(vol)
    cross_check_registry_op(vol, drr)

    # --- 期待される Ground Truth ---
    # (1) 厚み軸 z を潰したので 2D 形状は (y, x)。
    expected_shape = (y, x)
    # (2) 骨を含む画素は背景より遥かに明るい(積算値が大きい)。
    bone_mask_2d = (vol > vol.mean() + vol.std()).any(axis=0)  # どこかに骨がある画素
    drr_max = float(drr.max())
    drr_median = float(np.median(drr))
    bone_px_mean = float(drr[bone_mask_2d].mean())
    bg_px_mean = float(drr[~bone_mask_2d].mean())
    ratio = drr_max / (drr_median + 1e-9)

    print(f"[GT] DRR shape = {drr.shape} (expect {expected_shape})")
    print(f"[GT] DRR max = {drr_max:.3f}, median = {drr_median:.3f}, "
          f"max/median = {ratio:.2f}x")
    print(f"[GT] bone-pixel mean = {bone_px_mean:.3f} vs "
          f"background-pixel mean = {bg_px_mean:.3f}")

    # --- 自己検証 ---
    assert drr.ndim == 2, f"DRR は 2D のはず, got {drr.ndim}D"
    assert drr.shape == expected_shape, \
        f"DRR shape {drr.shape} != expected {expected_shape}"
    # 骨画素は背景の 2 倍以上明るい(実測 ~6.7x); 保守的に max >> median を要求。
    assert drr_max > 3.0 * drr_median, \
        f"骨の投影ピークが背景中央値に対して不十分: {ratio:.2f}x"
    assert bone_px_mean > 2.0 * bg_px_mean, \
        f"骨画素が背景より十分明るくない: {bone_px_mean:.3f} vs {bg_px_mean:.3f}"
    assert drr_max > 0.0 and np.all(np.isfinite(drr)), "DRR に不正値"

    print("PASS: 骨格CTから手のX線ラジオグラフ(DRR)を合成し、"
          "骨画素が背景より明瞭に明るいことを確認")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
