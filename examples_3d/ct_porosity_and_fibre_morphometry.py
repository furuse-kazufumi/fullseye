"""産業 CT の気孔・繊維を「形態計測」で数える例(真値つき)。

実世界の問題:
    鋳造品やダイカストは内部に **気孔(す)** を持つ。発泡材や焼結体は
    「どれくらいつながっているか」で透過性が決まる。CFRP は **繊維の向きが
    揃っているか** で強度が変わる。どれも「欠陥を見つける」ではなく
    **「分布として数える」** 仕事で、必要な量は昔から決まっている ——
    気孔径分布、局所肉厚、開気孔と閉気孔の別、配向の揃い具合。

    HALCON はボクセル型を持たないので、この一族はそもそも比較対象が無い。
    構造テンソルだけは HALCON も内部で使っているが(``coherence_enhancing_diff``)、
    **拡散に使うだけで向きも異方度も返さない**。測った量を返すのがここの差。

原理と、この例で見せること:
    真値の分かる合成ボリュームを作り、5 つの op が**その真値を復元する**ことを
    数字で確かめる。合成なので「当たっている」と言い切れる。

    1. ``vol_local_std``   —— 既知 sigma の白色雑音を入れて、その sigma が返るか。
                              誤差は閉形式 ``1/sqrt(2(n-1))``(n = 窓の体素数)。
    2. ``vol_local_thickness`` — 直径が既知の球を置いて、その直径が返るか。
    3. ``vol_granulometry``    — 気孔径**分布**が既知の体積分率どおりに立つか。
    4. ``vol_euler_number``    — 貫通孔(開気孔)と密閉気泡(閉気孔)を別々に数えるか。
                                 chi ひとつでは両者を区別できない、というのが要点。
    5. ``vol_orientation_coherence`` —— 一方向に並べた層で 1 に近づき、等方雑音で
                                 落ち、一様ブロックでちょうど 0 になるか
                                 (一様面で丸め屑が「向き」に化けないこと)。

    ★体素の大きさ(spacing)を渡すと結果はミリになる。異方ボクセルの CT では
    これは飾りではなく、渡さないと肉厚が軸ごとに違う値になる。
"""
from __future__ import annotations

import os
import sys

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import volops  # fullseye: vol_* は (v, a, b) 規約ではなく名前つき引数を取る


SPHERES = ((16, 16, 16, 4), (16, 48, 48, 7), (48, 16, 48, 10))   # (z, y, x, 半径)


def make_pores(shape=(64, 64, 64), spec=SPHERES) -> np.ndarray:
    """直径が既知の球を互いに離して置いたボリューム(気孔を前景として扱う)。"""
    zz, yy, xx = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]]
    vol = np.zeros(shape)
    for cz, cy, cx, r in spec:
        vol[(zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 1.0
    return vol


def make_torus(n=48, major=14.0, minor=5.0) -> np.ndarray:
    """貫通孔をちょうど 1 つ持つ形(b1 = 1)。"""
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n]
    q = np.sqrt((yy - n / 2.0) ** 2 + (xx - n / 2.0) ** 2) - major
    return ((q ** 2 + (zz - n / 2.0) ** 2) <= minor * minor).astype(float)


def make_sealed_bubble(n=40) -> np.ndarray:
    """密閉気泡をちょうど 1 つ持つ形(b2 = 1)。トーラスと chi では区別できない。"""
    vol = np.zeros((n, n, n))
    vol[10:30, 10:30, 10:30] = 1.0
    vol[15:25, 15:25, 15:25] = 0.0
    return vol


def main() -> int:
    checks = 0
    print("=" * 74)
    print("産業 CT の形態計測 —— 気孔径分布・局所肉厚・開/閉気孔・繊維配向")
    print("=" * 74)

    # 1. 局所標準偏差: 既知の sigma を絶対値で返す ---------------------------- #
    print("\n1) vol_local_std —— 既知のノイズ量を絶対値で返す")
    rng = np.random.default_rng(20260917)
    for sigma_true in (0.01, 0.05):
        noisy = 0.5 + rng.normal(0, sigma_true, (48, 48, 48))
        for k in (3, 5, 9):
            s = volops.vol_local_std(noisy, size=k)
            bound = 1.0 / np.sqrt(2.0 * (k ** 3 - 1))
            assert abs(float(s.mean()) - sigma_true) < 0.02 * sigma_true
            print(f"   sigma={sigma_true:.2f} 窓 {k}^3: 推定 {s.mean():.5f} "
                  f"(比 {s.mean() / sigma_true:.4f})  1 体素の相対誤差 {bound * 100:.1f} %")
        checks += 1
    flat = volops.vol_local_std(np.full((24, 24, 24), 1000.0), size=5)
    assert float(flat.max()) == 0.0
    print(f"   一様ブロック(輝度 1000): 最大 {flat.max():.1e} —— 偽のテクスチャが出ない")
    checks += 1

    # 2. 局所肉厚: 球の直径をそのまま返す ------------------------------------ #
    print("\n2) vol_local_thickness —— 気孔の直径を 1 枚の地図として")
    pores = make_pores()
    th = volops.vol_local_thickness(pores)
    for cz, cy, cx, r in SPHERES:
        assert abs(th[cz, cy, cx] - 2 * r) < 1e-9
        print(f"   球 直径 {2 * r:2d} 体素 -> 推定 {th[cz, cy, cx]:.1f}")
    leaked = int(((th > 0.0) & (pores == 0.0)).sum())
    assert leaked == 0
    print(f"   前景の外への漏れ: {leaked} 体素")
    mm = volops.vol_local_thickness(pores, spacing=(0.05, 0.05, 0.05))
    assert abs(float(mm[16, 16, 16]) - 0.05 * float(th[16, 16, 16])) < 1e-9
    print(f"   体素 50 µm を渡すと: {mm[16, 16, 16] * 1000:.0f} µm(ミリで返る)")
    checks += 1

    # 3. 気孔径分布: 体積分率まで合う ---------------------------------------- #
    print("\n3) vol_granulometry —— 径の分布(体積分率つき)")
    g = volops.vol_granulometry(pores)
    assert g["surviving_fraction"][0] == 1.0 and g["surviving_fraction"][-1] == 0.0
    sizes = np.asarray(g["sizes"][:-1])
    dens = np.asarray(g["density"])
    fg = th[pores > 0]
    for size, d in zip(sizes, dens):
        if d <= 1e-9:
            continue
        want = float((fg == size).sum()) / fg.size
        assert abs(d - want) < 1e-9
        print(f"   直径 {size:4.0f} 体素: 体積分率 {d * 100:5.2f} %(真値 {want * 100:5.2f} %)")
    print(f"   平均径 {g['mean_size']:.2f} / D50 {g['d50']:.1f} 体素")
    checks += 1

    # 4. 開気孔と閉気孔: chi ひとつでは分けられない -------------------------- #
    print("\n4) vol_euler_number —— 貫通孔と密閉気泡を別々に数える")
    solid = np.zeros((40, 40, 40))
    solid[10:30, 10:30, 10:30] = 1.0
    for name, vol, want in (("中実の立方体", solid, (1, 0, 0)),
                            ("密閉気泡 1 つ", make_sealed_bubble(), (1, 0, 1)),
                            ("貫通孔 1 つ", make_torus(), (1, 1, 0))):
        r = volops.vol_euler_number(vol)
        got = (r["objects"], r["tunnels"], r["cavities"])
        assert got == want, (name, got, want)
        print(f"   {name}: chi={r['euler']:+d}  物体 {r['objects']} / "
              f"貫通孔 {r['tunnels']} / 閉気孔 {r['cavities']}")
    a = volops.vol_euler_number(make_sealed_bubble())
    b = volops.vol_euler_number(make_torus())
    assert a["euler"] != b["euler"]
    print(f"   ★この 2 つは chi が {a['euler']:+d} と {b['euler']:+d} で違うが、"
          "形が複雑になると chi は一致しうる。")
    print("     透過性を語れるのは b1(貫通孔)であって chi ではない。")
    checks += 1

    # 5. 配向の揃い具合 ------------------------------------------------------ #
    print("\n5) vol_orientation_coherence —— 繊維がどれだけ揃っているか")
    zz, yy, xx = np.mgrid[0:40, 0:40, 0:40]
    layered = 0.5 + 0.4 * np.sin(2.0 * np.pi * xx / 8.0)
    iso = rng.normal(0.5, 0.05, (40, 40, 40))
    c_lay = float(np.median(volops.vol_orientation_coherence(layered)))
    c_iso = float(np.median(volops.vol_orientation_coherence(iso)))
    assert c_lay > 0.9 and c_iso < 0.5
    print(f"   一方向の層: {c_lay:.3f}   等方な雑音: {c_iso:.3f}")
    for level in (0.0, 0.5, 1000.0):
        o = volops.vol_orientation_coherence(np.full((24, 24, 24), level))
        assert float(o.max()) == 0.0
    print("   一様ブロック(輝度 0 / 0.5 / 1000): すべて 0.000 —— "
          "丸め屑が「向き」に化けない")
    checks += 1

    print("\n" + "=" * 74)
    print(f"PASS: 5 ops3d op を真値つきで確認、{checks} 件の検査")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
