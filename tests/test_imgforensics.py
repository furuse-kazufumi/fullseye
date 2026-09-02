# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""imgforensics — 画像フォレンジック op 族の検証。

この族の主張は「加工を見つけられる」ではなく「**証拠量を出し、その量が何を
意味しないかを一緒に返す**」である。したがってこのファイルは 2 種類のテストを
半々に持つ:

  (A) **正解を自分で作って当てさせる** —— コピー&ムーブは複製元と複製先の座標を
      こちらが決めたので真のシフトが分かる。PRNU は合成センサパターンを自分で
      作ったので「同じセンサ / 別のセンサ」が分かる。JPEG は Pillow で品質を
      指定して符号化したので真の品質が分かる。透かしは埋めたビット列が分かる。
      **当たったことを数で固定する**。

  (B) **破綻点を破綻点として固定する** —— ELA は無圧縮画像では何も言えない、
      PRNU は再圧縮で消える、知覚ハッシュは反転・回転に無力、ブロック法は
      ``step`` の倍数のシフトしか見つけられない、コピー&ムーブは回転に効かない。
      これらは**欠陥だから隠すのではなく、そういう結果になることをテストで残す**。
      直ったつもりの改変で (B) が壊れたら、それは「主張が強くなった」のではなく
      「測り方が変わった」可能性のほうが高い。

数値はすべてこの環境(numpy 2.4.6 / scipy 1.15.2 / Pillow 12.3.0 /
PyWavelets 1.8.0)での実測で、docstring に書いた表と同じ値である。
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import features                                          # noqa: E402
import imgforensics as F                                 # noqa: E402
import opsimgforensics                                   # noqa: E402
from scipy import ndimage                                # noqa: E402

# optional 依存は「無ければ skip」ではなく「無ければ **その op のテストだけ** skip」。
# import 自体が通ることは test_registry_declares_optional_dependencies が別に見る。
try:
    from PIL import Image                                # noqa: E402
    HAVE_PIL = True
except ImportError:                                      # pragma: no cover
    HAVE_PIL = False
try:
    import pywt                                          # noqa: F401,E402
    HAVE_PYWT = True
except ImportError:                                      # pragma: no cover
    HAVE_PYWT = False

needs_pil = pytest.mark.skipif(not HAVE_PIL, reason="Pillow が無い")
needs_pywt = pytest.mark.skipif(not HAVE_PYWT, reason="PyWavelets が無い")


# --------------------------------------------------------------------------- #
# 参照画像(決定的)                                                             #
# --------------------------------------------------------------------------- #
def natural(n=256, seed=0, beta=1.6):
    """1/f^beta のスペクトルを持つ自然画像風のランダム場。

    ``seed`` を変えると **構造そのもの**が変わる(雑音だけが変わるのではない)。
    知覚ハッシュの「別画像」対照にはこれが要る —— 同じ構造に雑音だけ足した 2 枚は
    ハッシュ距離が 2 程度にしかならず、「別画像なら距離が大きい」の対照にならない
    (最初にそれで測って気付いた)。
    """
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fy ** 2 + fx ** 2)
    f[0, 0] = 1.0
    spec = np.fft.fft2(r.standard_normal((n, n))) / (f ** beta)
    spec[0, 0] = 0
    img = np.real(np.fft.ifft2(spec))
    return 0.15 + 0.7 * (img - img.min()) / (np.ptp(img) + 1e-12)


def textured(n=256, seed=4):
    """低周波の地 + はっきりしたテクスチャ。コーナーが立ちパッチが弁別できる画像。"""
    r = np.random.default_rng(seed)
    tex = ndimage.gaussian_filter(r.standard_normal((n, n)), 1.0)
    tex = (tex - tex.min()) / np.ptp(tex)
    return np.clip(0.55 * natural(n, seed) + 0.45 * tex, 0, 1)


def jpeg(img, q):
    """本物の JPEG を通して戻す(近似ではない)。"""
    buf = io.BytesIO()
    Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8), "L").save(
        buf, "JPEG", quality=q, subsampling=0)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("L"), np.float64) / 255.0


def sensor_pattern(n, seed):
    """合成センサ PRNU パターン K(ゼロ平均・単位分散の白色)。"""
    r = np.random.default_rng(seed)
    k = r.standard_normal((n, n))
    return (k - k.mean()) / k.std()


def shoot(scene, K, gain=0.03, read=0.01, seed=0):
    """撮像モデル I = I0·(1 + gain·K) + 読み出し雑音(Chen et al. 2008 の形)。"""
    r = np.random.default_rng(seed)
    return np.clip(scene * (1.0 + gain * K) + read * r.standard_normal(scene.shape), 0, 1)


N_PRNU = 128


def prnu_bank(K, n, size=N_PRNU):
    return [shoot(natural(size, 300 + i), K, seed=1000 + i) for i in range(n)]


def forge(img, src=(40, 32), dst=(150, 160), size=64, rot=0):
    """既知の座標でコピー&ムーブを作る。真のシフトは ``dst - src``。"""
    out = img.copy()
    p = img[src[0]:src[0] + size, src[1]:src[1] + size]
    if rot:
        p = ndimage.rotate(p, rot, reshape=False, order=1, mode="reflect")
    out[dst[0]:dst[0] + size, dst[1]:dst[1] + size] = p
    return out


TRUE_SHIFT = (110.0, 128.0)          # forge() の既定 (150,160) - (40,32)


# =========================================================================== #
# (0) 台帳と既存資産の整合                                                      #
# =========================================================================== #
def test_registry_is_complete_and_matches_the_module():
    """台帳の op がすべて実体を持ち、モジュールの公開一覧と一致する。

    2026-09-02 の TRIZ 点検で ``null_distribution`` / ``evidence_quantile``
    を足して 14 → 16。両方とも ``measurement`` の**消費側**で、それまで
    ``hash_distance`` が産むだけの袋小路だった。
    """
    assert opsimgforensics.missing() == []
    assert sorted(opsimgforensics.list_ops()) == sorted(F.IMGFORENSICS)
    assert len(F.IMGFORENSICS) == 16


def test_new_sorts_are_not_dead_ends():
    """新語彙 phash / fingerprint / measurement に **産む op も食う op も**あること。

    片方しか無い語彙は袋小路(または到達不能)で、検査面を増やしたつもりで
    増えていない状態になる。この repo の台帳の規律をここで機械的に固定する。

    ``measurement`` は 2026-09-02 の点検まで**産む 1・食う 0** だった ――
    「証拠は返すが判定は返さない」設計が正しい一方で、**その証拠を解釈する
    手段が無い**という穴になっていた。しきい値を同梱すると嘘になるので、
    利用者自身の清浄データから帰無分布を測る 2 op を消費側に置いて塞いだ。
    """
    d = opsimgforensics.new_sorts()
    assert d["phash"]["producers"] and d["phash"]["consumers"]
    assert d["fingerprint"]["producers"] and d["fingerprint"]["consumers"]
    # fingerprint は image2d への出口を必ず持つ(でないと行き止まり)
    assert ("fingerprint", "image2d") in opsimgforensics.conversion_edges()

    reg = opsimgforensics.OPSIMGFORENSICS
    produced = {op for op, m in reg.items() if m["out"] == "measurement"}
    consumed = {op for op, m in reg.items() if "measurement" in m["in"]}
    assert produced == {"hash_distance"}
    assert consumed == {"evidence_quantile"}


def test_luma_table_is_the_shared_one():
    """JPEG 標準輝度表は ``backends_aug`` のものを **参照**している(複製でない)。

    2 つの表が別々に育つと、``aug_jpeg_blocks`` が作った劣化画像の品質を
    :func:`jpeg_quality_estimate` が外す = 同じ repo の中で答え合わせが狂う。
    """
    import backends_aug
    assert F.JPEG_LUMA_Q is backends_aug._JPEG_LUMA_Q
    assert F.JPEG_LUMA_Q.shape == (8, 8)
    assert F.JPEG_LUMA_Q[0, 0] == 16 and F.JPEG_LUMA_Q[7, 7] == 99


def test_ijg_quality_scaling_matches_the_standard_rule():
    """品質 50 は標準表そのもの、品質 100 は全 1(IJG の公開規則)。"""
    assert np.array_equal(F._ijg_table(50), F.JPEG_LUMA_Q)
    assert np.all(F._ijg_table(100) == 1)
    # 品質が上がるほど表は単調に小さくなる(等しさは許す)
    for q in range(2, 101):
        assert np.all(F._ijg_table(q) <= F._ijg_table(q - 1))


def test_match_descriptors_cannot_self_match():
    """既存 :func:`features.match_descriptors` は自己マッチに **使えない**。

    これが :func:`imgforensics._self_match` を新しく書いた理由なので、
    「使えないこと」自体をテストで固定する。既存 API が将来変わって自己を
    除けるようになったら、このテストが落ちて乗り換えを促す。
    """
    img = forge(textured(256, 4))
    kp = features.harris_corners(img)
    desc, kp = features.describe_patches(img, kp, 11)
    m = features.match_descriptors(desc, desc)
    assert m.shape[0] > 0
    assert int(np.sum(m[:, 0] == m[:, 1])) == m.shape[0]    # 100% が自分自身


# =========================================================================== #
# (1) 知覚ハッシュ                                                             #
# =========================================================================== #
@pytest.mark.parametrize("mode", ["dct", "average", "difference"])
def test_hash_is_bool_bits_of_the_declared_length(mode):
    h = F.perceptual_hash(natural(128, 1), mode, hash_size=8)
    assert h.dtype == np.bool_ and h.shape == (64,)
    assert F.perceptual_hash(natural(128, 1), mode, hash_size=4).shape == (16,)


@pytest.mark.parametrize("mode", ["dct", "average", "difference"])
def test_hash_is_deterministic(mode):
    a = F.perceptual_hash(natural(128, 1), mode)
    b = F.perceptual_hash(natural(128, 1), mode)
    assert np.array_equal(a, b) and F.hash_distance(a, b) == 0


@needs_pil
def test_hash_survives_recompression_and_resize():
    """(A) 同じ画像の再圧縮・縮小・明るさ変更では距離が **小さい**。実測値で固定。"""
    img = natural(256, 1)
    expect = {                       # mode -> (q60, q30, 1/2 縮小, 1/4 縮小, 明るさ+0.1)
        "dct": (0, 2, 0, 0, 0),
        "average": (0, 0, 0, 0, 0),
        "difference": (0, 0, 0, 0, 0),
    }
    for mode, (e60, e30, e2, e4, eb) in expect.items():
        h = F.perceptual_hash(img, mode)
        assert F.hash_distance(h, F.perceptual_hash(jpeg(img, 60), mode)) == e60
        assert F.hash_distance(h, F.perceptual_hash(jpeg(img, 30), mode)) == e30
        assert F.hash_distance(h, F.perceptual_hash(F._area_resize(img, (128, 128)), mode)) == e2
        assert F.hash_distance(h, F.perceptual_hash(F._area_resize(img, (64, 64)), mode)) == e4
        assert F.hash_distance(h, F.perceptual_hash(np.clip(img + 0.1, 0, 1), mode)) == eb


def test_hash_separates_different_images():
    """(A) 無関係な 2 枚は距離 32(= ビット長の半分)前後。20 対の平均で固定。"""
    expect = {"dct": 31.3, "average": 34.2, "difference": 32.6}
    for mode, mean in expect.items():
        ds = [F.hash_distance(F.perceptual_hash(natural(256, s), mode),
                              F.perceptual_hash(natural(256, s + 50), mode))
              for s in range(20)]
        assert np.mean(ds) == pytest.approx(mean, abs=0.05)
        assert min(ds) >= 18                    # 一度も「同じ画像」に見えない


def test_hash_is_blind_to_flip_and_rotation():
    """(B) **破綻点**: 反転・回転は「別の画像」と区別が付かない。

    これは欠陥であり、隠さずに数で残す。距離が無関係な 2 枚の域(平均 32 前後)に
    入っていることを固定するので、「実は回転に強い」という改変があればここが落ちる。
    """
    img = natural(256, 1)
    expect = {"dct": (28, 32), "average": (42, 30), "difference": (34, 32)}
    for mode, (flip, rot) in expect.items():
        h = F.perceptual_hash(img, mode)
        assert F.hash_distance(h, F.perceptual_hash(img[:, ::-1], mode)) == flip
        assert F.hash_distance(h, F.perceptual_hash(np.rot90(img), mode)) == rot
        assert flip >= 18 and rot >= 18         # 無関係な 2 枚と同じ域


def test_hash_is_blind_to_small_local_tampering():
    """(B) **破綻点**: 512x512 に 24x24 のコピー&ムーブを入れても距離はほぼ 0。

    8x8 に潰したハッシュに細部が残らないのは当然だが、「ハッシュが同じ = 同じ画像」
    という読み方を潰すために測っておく。
    """
    big = natural(512, 11)
    tam = big.copy()
    tam[300:324, 300:324] = big[100:124, 100:124]
    assert not np.array_equal(big, tam)         # 実際に改竄されている
    got = {m: F.hash_distance(F.perceptual_hash(big, m), F.perceptual_hash(tam, m))
           for m in ("dct", "average", "difference")}
    assert got == {"dct": 0, "average": 0, "difference": 1}


def test_hash_distance_is_fail_closed():
    """float の 1-D は **黙って通さない**(『距離 64 = 別画像』という嘘を作らない)。"""
    h = F.perceptual_hash(natural(64, 1))
    with pytest.raises(ValueError, match="bool"):
        F.hash_distance(np.zeros(64), np.ones(64))
    with pytest.raises(ValueError, match="bool"):
        F.hash_distance(h, h.astype(np.uint8))
    with pytest.raises(ValueError, match="ハッシュ長"):
        F.hash_distance(h, F.perceptual_hash(natural(64, 1), hash_size=4))
    with pytest.raises(ValueError):
        F.perceptual_hash(natural(64, 1), "median")


def test_hash_bits_satisfy_existing_1d_predicates():
    """(B) 新語彙 ``phash`` を作った **根拠そのもの**を固定する。

    bool の 1-D は既存の ``signal`` / ``indices`` / ``descriptor`` の述語を 3 つとも
    満たし、``signal1d`` の 5 op が例外も NaN も出さずに有限値を返す。
    この事実が変わったら、語彙を分けた理由の一方が消えるので気付けるようにする。
    """
    import signal1d
    h = F.perceptual_hash(natural(64, 1))
    assert isinstance(h, np.ndarray) and h.ndim == 1            # signal / indices
    assert h.ndim in (1, 2)                                     # descriptor
    passed = []
    for name in ("lowpass", "highpass", "bandpass", "smooth"):
        r = np.asarray(getattr(signal1d, name)(h))
        assert np.all(np.isfinite(r))
        passed.append(name)
    assert len(passed) == 4          # 「意味の無い有限値」が 4 経路で作れてしまう


# =========================================================================== #
# (2) PRNU センサ指紋                                                          #
# =========================================================================== #
def test_prnu_separates_two_sensors():
    """(A) 同一センサと別センサで PCE が **2〜3 桁**離れる。枚数ごとに固定。

    ``corr`` も一緒に測るのが要点で、PCE だけ見ていると『指紋が真のパターンを
    まったく捉えていないのに分離しているように見える』状態を見逃す
    (実際に一度その状態にあった。:func:`imgforensics._wiener_denoise` の docstring)。
    """
    K, K2 = sensor_pattern(N_PRNU, 101), sensor_pattern(N_PRNU, 202)
    test_a = shoot(natural(N_PRNU, 900), K, seed=5000)
    test_b = shoot(natural(N_PRNU, 900), K2, seed=5000)
    expect = {2: (0.727, 5295), 4: (0.809, 6472), 8: (0.859, 7246), 16: (0.892, 7755)}
    for n, (corr, pce) in expect.items():
        fp = F.sensor_fingerprint(prnu_bank(K, n))
        assert np.corrcoef(fp.ravel(), K.ravel())[0, 1] == pytest.approx(corr, abs=0.01)
        same = F.fingerprint_correlate(test_a, fp)
        diff = F.fingerprint_correlate(test_b, fp)
        assert same["pce"] == pytest.approx(pce, rel=0.02)
        assert same["peak_shift"] == (0, 0)      # 同一センサはピークが原点
        assert abs(diff["pce"]) < 30             # 別センサは 2 桁以上下
        assert diff["peak_shift"] != (0, 0)      # ピークが原点に来ない


def test_fingerprint_is_zero_mean_unit_variance():
    fp = F.sensor_fingerprint(prnu_bank(sensor_pattern(N_PRNU, 101), 4))
    assert abs(float(fp.mean())) < 1e-12
    assert float(fp.std()) == pytest.approx(1.0, abs=1e-9)
    # 行平均・列平均も抜けている(ZM 前処理)
    assert np.max(np.abs(fp.mean(axis=0))) < 1e-12
    assert np.max(np.abs(fp.mean(axis=1))) < 1e-12


@needs_pywt
def test_wavelet_denoiser_is_at_least_as_good():
    """``denoiser="wavelet"`` は既定より強い。**既定が精度で選ばれていない**ことの明示。"""
    K = sensor_pattern(N_PRNU, 101)
    bank = prnu_bank(K, 8)
    c_w = np.corrcoef(F.sensor_fingerprint(bank, denoiser="wiener").ravel(), K.ravel())[0, 1]
    c_v = np.corrcoef(F.sensor_fingerprint(bank, denoiser="wavelet").ravel(), K.ravel())[0, 1]
    assert c_w == pytest.approx(0.859, abs=0.01)
    assert c_v == pytest.approx(0.873, abs=0.01)
    assert c_v > c_w


@needs_pil
def test_prnu_dies_under_recompression():
    """(B) **破綻点**: 再圧縮で PRNU は消える。低い PCE は『別カメラ』を意味しない。"""
    K = sensor_pattern(N_PRNU, 101)
    fp = F.sensor_fingerprint(prnu_bank(K, 8))
    test = shoot(natural(N_PRNU, 900), K, seed=5000)
    base = F.fingerprint_correlate(test, fp)["pce"]
    assert base == pytest.approx(7246, rel=0.02)
    got = {q: F.fingerprint_correlate(jpeg(test, q), fp)["pce"] for q in (95, 90, 75, 50, 30)}
    for q, expected in ((95, 6174), (90, 4214), (75, 1412), (50, 530), (30, 207)):
        assert got[q] == pytest.approx(expected, rel=0.03)
    # 単調に落ちる。品質 30 では無圧縮の 3% しか残らない
    assert got[95] > got[90] > got[75] > got[50] > got[30]
    assert got[30] / base < 0.05


def test_fingerprint_gate_rejects_plain_images():
    """(A) 普通の画像を指紋として渡すと fail-closed。**比はスケール不変**。"""
    K = sensor_pattern(N_PRNU, 101)
    fp = F.sensor_fingerprint(prnu_bank(K, 8))
    test = shoot(natural(N_PRNU, 900), K, seed=5000)
    assert abs(fp.mean()) / fp.std() < 1e-15
    plain = natural(N_PRNU, 1)
    for candidate, ratio in ((plain, 4.626), (plain * 0.03, 4.626),
                             (np.clip(plain * 3 - 1, 0, 1), 1.801)):
        c = np.asarray(candidate, np.float64)
        assert abs(c.mean()) / c.std() == pytest.approx(ratio, abs=0.01)
        with pytest.raises(ValueError, match="ゼロ平均"):
            F.fingerprint_correlate(test, c)


def test_fingerprint_gate_is_only_half_safe():
    """(B) **破綻点**: 自分でゼロ平均化した画像はゲートを通り、有限の PCE が返る。

    これが「実行時チェックでは守れないので型で分ける」判断の根拠なので、
    ゲートが完全であるかのような改変が入ったら落ちるようにしておく。
    """
    K = sensor_pattern(N_PRNU, 101)
    test = shoot(natural(N_PRNU, 900), K, seed=5000)
    fake = natural(N_PRNU, 42)
    fake = (fake - fake.mean()) / fake.std()
    r = F.fingerprint_correlate(test, fake)              # 例外は出ない
    assert np.isfinite(r["pce"])
    assert abs(r["pce"]) < 30                            # 中身は無相関相当
    assert r["caveats"]                                  # 注意書きは必ず付く


def test_fingerprint_correlate_is_fail_closed_on_shape_and_constants():
    K = sensor_pattern(N_PRNU, 101)
    fp = F.sensor_fingerprint(prnu_bank(K, 4))
    test = shoot(natural(N_PRNU, 900), K, seed=5000)
    with pytest.raises(ValueError, match="shape"):
        F.fingerprint_correlate(test[:64, :64], fp)
    with pytest.raises(ValueError, match="定数"):
        F.fingerprint_correlate(test, np.zeros_like(fp))
    with pytest.raises(ValueError, match="ノルム"):
        F.fingerprint_correlate(np.full_like(test, 0.5), fp)


def test_sensor_fingerprint_refuses_mismatched_or_single_images():
    """PRNU は画素の位置そのもの。**リサイズして揃えられない**ので shape 不一致は例外。"""
    K = sensor_pattern(N_PRNU, 101)
    bank = prnu_bank(K, 4)
    with pytest.raises(ValueError, match="少なくとも 2"):
        F.sensor_fingerprint(bank[:1])
    with pytest.raises(ValueError, match="shape"):
        F.sensor_fingerprint([bank[0], bank[1][:64, :64]])
    with pytest.raises(ValueError):
        F.sensor_fingerprint(bank[0])                    # list ですらない


def test_strength_map_marks_the_saturated_half():
    """(A) 飽和した領域では指紋の強度が **18.8 倍**低い = そこでは何も言えない。"""
    K = sensor_pattern(N_PRNU, 101)
    imgs = []
    for i in range(8):
        sc = natural(N_PRNU, 300 + i).copy()
        sc[:, :N_PRNU // 2] = 1.6                        # clip されて飽和する
        imgs.append(shoot(sc, K, seed=1000 + i))
    sm = F.fingerprint_strength_map(F.sensor_fingerprint(imgs), 16)
    sat, ok = sm[:, :N_PRNU // 2].mean(), sm[:, N_PRNU // 2:].mean()
    assert sat == pytest.approx(0.075, abs=0.005)
    assert ok == pytest.approx(1.409, abs=0.02)
    assert ok / sat == pytest.approx(18.8, rel=0.05)
    assert sm.shape == (N_PRNU, N_PRNU)                  # 元の格子に戻っている


# =========================================================================== #
# (3) ELA                                                                      #
# =========================================================================== #
@needs_pil
def test_ela_separates_a_paste_only_when_the_base_was_jpeg():
    """(A)+(B) **ELA が意味を持つのは元が JPEG のときだけ**。両方を同時に固定する。"""
    clean = natural(256, 5)
    patch = natural(256, 6)[20:84, 20:84]
    mask = np.zeros((256, 256), bool)
    mask[96:160, 96:160] = True

    png_paste = clean.copy()
    png_paste[96:160, 96:160] = patch
    e1 = F.error_level_map(png_paste, 90)
    ratio_png = e1[mask].mean() / e1[~mask].mean()

    jpg_paste = jpeg(clean, 75)
    jpg_paste[96:160, 96:160] = patch
    e2 = F.error_level_map(jpg_paste, 90)
    ratio_jpg = e2[mask].mean() / e2[~mask].mean()

    assert ratio_png == pytest.approx(1.096, abs=0.01)   # 分離しない
    assert ratio_jpg == pytest.approx(4.898, abs=0.05)   # 分離する
    assert ratio_jpg > 4.0 > ratio_png


@needs_pil
def test_ela_is_not_merely_an_edge_map():
    """(B) ELA は勾配の言い換えではない —— それでも無圧縮では役に立たない。

    「ELA は高周波を見ているだけ」という説明は、少なくともこの画像では成り立たない
    (相関 0.003)。役に立たない理由は勾配との重複ではなく、**比べる基準になる
    量子化履歴が無い**ことである。この区別を残しておく。
    """
    clean = natural(256, 5)
    paste = clean.copy()
    paste[96:160, 96:160] = natural(256, 6)[20:84, 20:84]
    ela = F.error_level_map(paste, 90)
    grad = np.hypot(ndimage.sobel(paste, 0), ndimage.sobel(paste, 1))
    assert abs(np.corrcoef(ela.ravel(), grad.ravel())[0, 1]) < 0.05


@needs_pil
def test_ela_range_and_normalisation():
    img = natural(128, 5)
    norm = F.error_level_map(img, 90, normalize=True)
    raw = F.error_level_map(img, 90, normalize=False)
    assert norm.shape == img.shape and 0.0 <= norm.min() and norm.max() == pytest.approx(1.0)
    assert raw.max() > 1.0                                # 8 bit 階調そのまま
    with pytest.raises(ValueError):
        F.error_level_map(img, 0)
    with pytest.raises(ValueError, match=r"\[0, 1\] の外"):
        F.error_level_map(img * 3.0, 90)                  # clip で隠さない


# =========================================================================== #
# (4) JPEG 品質・ゴースト                                                       #
# =========================================================================== #
@needs_pil
def test_jpeg_quality_estimate_recovers_quality():
    """(A) 真の品質をブラインドで当てる。**低品質で崩れることも同時に固定**。"""
    src = natural(256, 9)
    expect = {95: 95, 90: 90, 80: 80, 70: 71, 60: 60, 50: 52, 40: 40, 30: None}
    for q, want in expect.items():
        r = F.jpeg_quality_estimate(jpeg(src, q))
        assert r["quality"] == want, (q, r["quality"])
        if want is not None:
            assert r["jpeg_compressed"] is True
            assert r["table"].shape == (8, 8)
    # 品質が下がるほど「櫛が読める係数」が減る = 材料が画像から消えていく
    hits = [F.jpeg_quality_estimate(jpeg(src, q))["n_quantized"] for q in (95, 90, 80, 60, 40, 30)]
    assert hits == [11, 19, 13, 9, 6, 4]


def test_jpeg_quality_estimate_says_nothing_on_uncompressed():
    """(A) 無圧縮では **``quality=None``**。『品質 100』とは答えない。

    そう答えると「無圧縮」と「ほぼ無劣化の JPEG」が同じ答えになり、区別が消える。
    """
    for seed in (1, 2, 3, 9):
        r = F.jpeg_quality_estimate(natural(256, seed))
        assert r["jpeg_compressed"] is False
        assert r["quality"] is None
        assert r["n_quantized"] == 0
        assert r["caveats"]


def _comb(rng, step, spread, n=4096, jitter=0.2):
    """真のステップ ``step``・広がり ``spread`` ステップぶんの合成 comb。"""
    return np.round(rng.standard_normal(n) * spread) * step + jitter * rng.standard_normal(n)


def test_estimate_step_rejects_the_two_measured_traps():
    """量子化ステップ推定が過去に踏んだ **2 つの罠**を回帰テストとして固定する。

    罠 1: 候補 q が値域より大きいと「集中」が無条件に立つ(→ 無圧縮に品質 17)。
    罠 2: 0 に量子化された係数の塊がどの q でも位相 0 に集まる(→ 低品質で上振れ)。
    """
    rng = np.random.default_rng(0)
    # 罠 1: 連続値(量子化されていない)。何も答えてはいけない
    assert F._estimate_step(rng.standard_normal(4096) * 30.0) == 0.0
    assert F._estimate_step(rng.standard_normal(4096) * 80.0) == 0.0
    # 罠 2: 大半が 0 に潰れた櫛でも真のステップを当てる
    for step in (5.0, 12.0, 16.0):
        assert F._estimate_step(_comb(rng, step, 2.5)) == step
        assert F._estimate_step(_comb(rng, step, 4.0)) == step
    # 標本が少なすぎるときも答えない
    assert F._estimate_step(np.round(rng.standard_normal(20) * 3) * 8.0) == 0.0


def test_estimate_step_still_overshoots_on_narrow_combs():
    """(B) **残っている限界を残っているものとして固定する**(直したふりをしない)。

    係数の広がりが真のステップの約 2.5 倍未満だと上振れが残る。実画像では
    高周波係数か低品質 JPEG がこの域に入り、:func:`jpeg_quality_estimate` は
    それを ``n_quantized`` の減少として表に出す(材料が消えたので答えない)。
    """
    rng = np.random.default_rng(0)
    got = {step: F._estimate_step(_comb(rng, step, 1.5)) for step in (5.0, 12.0, 16.0)}
    assert got == {5.0: 6.0, 12.0: 25.0, 16.0: 34.0}
    assert all(v > k for k, v in got.items())            # 必ず「上」に外れる


@needs_pil
def test_jpeg_ghost_finds_the_pasted_quality():
    """(A) 別品質で圧縮した貼り付けを、**その品質**として言い当てる。"""
    n = 192
    bg = jpeg(natural(n, 12), 92)
    comp = bg.copy()
    comp[64:128, 64:128] = jpeg(natural(n, 13), 60)[40:104, 40:104]
    qs = list(range(40, 100, 5))
    ghosts = F.jpeg_ghost_map(comp, qs, block=16)
    assert len(ghosts) == len(qs) and all(g.shape == (n, n) for g in ghosts)
    qmap = F.jpeg_ghost_quality(ghosts, qs)
    inside = np.zeros((n, n), bool); inside[72:120, 72:120] = True
    outside = np.zeros((n, n), bool); outside[8:56, 8:56] = True
    assert np.bincount(qmap[inside].astype(int)).argmax() == 60      # 真値 60
    assert np.bincount(qmap[outside].astype(int)).argmax() == 95     # 掃引の刻みの限界


@needs_pil
def test_jpeg_ghost_quality_is_fail_closed_on_length_mismatch():
    """(A) 品質の本数と地図の本数がずれたら例外。**添字のずれた地図を返さない**。"""
    ghosts = F.jpeg_ghost_map(natural(64, 3), [50, 70, 90], block=8)
    assert len(ghosts) == 3
    with pytest.raises(ValueError, match="qualities の数"):
        F.jpeg_ghost_quality(ghosts)                      # 既定は 12 本を仮定
    assert F.jpeg_ghost_quality(ghosts, [50, 70, 90]).shape == (64, 64)
    with pytest.raises(ValueError, match="2 本以上"):
        F.jpeg_ghost_quality(ghosts[:1], [50])


# =========================================================================== #
# (5) ノイズ整合性                                                             #
# =========================================================================== #
def test_noise_map_recovers_the_true_sigma():
    """(A) 上下で σ が 4 倍違う合成画像。**絶対値も比も 1% 以内**で当てる。"""
    n = 256
    r = np.random.default_rng(3)
    img = np.full((n, n), 0.5) + 0.01 * r.standard_normal((n, n))
    img[128:] = 0.5 + 0.04 * r.standard_normal((128, n))
    nm = F.noise_inconsistency_map(np.clip(img, 0, 1), 16)
    lo = nm[16:96, 16:240].mean()                         # 真値 0.01 * 255 = 2.55
    hi = nm[160:240, 16:240].mean()                       # 真値 0.04 * 255 = 10.20
    assert lo == pytest.approx(2.533, abs=0.02)
    assert hi == pytest.approx(10.214, abs=0.05)
    assert hi / lo == pytest.approx(4.0, rel=0.02)
    assert nm.shape == (n, n)


def test_noise_map_counts_texture_as_noise():
    """(B) **破綻点**: 雑音が同じでも模様のある領域は σ が 6 倍高く出る。

    段差 = 改竄ではない。この地図の段差を単独で証拠に使えないことを数で残す。
    """
    n = 256
    r = np.random.default_rng(3)
    img = np.full((n, n), 0.5) + 0.01 * r.standard_normal((n, n))
    yy, xx = np.mgrid[0:n, 0:n]
    img[128:] += 0.15 * ((((xx[128:] // 2) + (yy[128:] // 2)) % 2) - 0.5)
    nm = F.noise_inconsistency_map(np.clip(img, 0, 1), 16)
    plain = nm[16:96, 16:240].mean()
    tex = nm[160:240, 16:240].mean()
    assert tex / plain == pytest.approx(6.2, rel=0.05)
    assert tex > 4 * plain          # 本物の σ 差(4 倍)と見分けが付かない大きさ


# =========================================================================== #
# (6) コピー&ムーブ —— 正解が手元にある                                          #
# =========================================================================== #
@pytest.mark.parametrize("method,n_matches", [("keypoint", 15), ("block", 3249)])
def test_copy_move_finds_the_known_offset(method, n_matches):
    """(A) **こちらが決めた**シフト (110, 128) を誤差 0 px で当てる。"""
    img = forge(textured(256, 4))
    got = F.copy_move_regions(img, method=method)
    assert len(got) == 1
    top = got[0]
    assert top["offset"] == pytest.approx(TRUE_SHIFT, abs=1e-9)
    assert top["n_matches"] == n_matches
    assert top["method"] == method
    # bbox が実際の複製元 / 複製先を囲んでいる
    sr0, sc0, sr1, sc1 = top["src_bbox"]
    dr0, dc0, dr1, dc1 = top["dst_bbox"]
    assert 40 <= sr0 and sr1 <= 40 + 64 and 32 <= sc0 and sc1 <= 32 + 64
    assert 150 <= dr0 and dr1 <= 150 + 64 and 160 <= dc0 and dc1 <= 160 + 64
    assert top["caveats"]


@pytest.mark.parametrize("method", ["keypoint", "block"])
@pytest.mark.parametrize("seed", [4, 5, 6])
def test_copy_move_has_no_false_positive_on_clean_images(method, seed):
    """(A) 改竄していない画像では **1 件も出ない**(検出器としての最低条件)。"""
    assert F.copy_move_regions(textured(256, seed), method=method) == []


def test_copy_move_block_only_finds_multiples_of_step():
    """(B) **破綻点**: ブロック法は ``step`` の倍数のシフトしか見つけられない。

    真のシフト (110, 128) は 4 の倍数でないので、``step=4`` では原理的に一度も
    格子が重ならない。速度のために step を上げるとき何を失うかを数で残す。
    """
    img = forge(textured(256, 4))
    assert len(F.copy_move_regions(img, method="block", step=1)) == 1
    assert len(F.copy_move_regions(img, method="block", step=2)) == 1
    assert F.copy_move_regions(img, method="block", step=4) == []


@pytest.mark.parametrize("method", ["keypoint", "block"])
@pytest.mark.parametrize("rot", [5, 15, 30])
def test_copy_move_is_blind_to_rotated_copies(method, rot):
    """(B) **破綻点**: 回転を伴う複製は **5 度でも**取れない。"""
    img = forge(textured(256, 4), rot=rot)
    assert F.copy_move_regions(img, method=method) == []


def test_copy_move_offset_orientation_is_position_based():
    """シフトの向きは **位置**で決める(添字で決めると符号が画像ごとに入れ替わった)。"""
    for size in (40, 48, 64):
        img = forge(textured(256, 4), size=size)
        got = F.copy_move_regions(img, method="keypoint")
        if got:
            dy, dx = got[0]["offset"]
            assert (dy, dx) == pytest.approx(TRUE_SHIFT, abs=1e-9)


def test_copy_move_flat_regions_need_the_variance_gate():
    """(B) **破綻点**: ``min_variance=0`` は一様な領域から偽の群を作る。

    上半分を一様な「空」にした **改竄していない** 画像で測る。
    """
    img = textured(256, 4)
    img[:96, :] = 0.85
    assert F.copy_move_regions(img, method="block", min_variance=1e-4) == []
    assert F.copy_move_regions(img, method="block", min_variance=1e-6) == []
    spurious = F.copy_move_regions(img, method="block", min_variance=0.0)
    assert len(spurious) == 1 and spurious[0]["n_matches"] == 264


@needs_pil
def test_copy_move_degrades_under_recompression_but_stays_correct():
    """(B) 再圧縮で **見つかりにくくなる**。ただし見つかったときの答えは正しい。"""
    img = forge(textured(256, 4))
    expect = {95: (10, 138), 85: (7, 10), 75: (7, 0)}
    for q, (n_kp, n_blk) in expect.items():
        j = jpeg(img, q)
        kp = F.copy_move_regions(j, method="keypoint")
        blk = F.copy_move_regions(j, method="block")
        assert len(kp) == 1 and kp[0]["n_matches"] == n_kp
        assert kp[0]["offset"] == pytest.approx(TRUE_SHIFT, abs=1e-9)
        if n_blk == 0:
            assert blk == []
        else:
            assert blk[0]["n_matches"] == n_blk
            assert blk[0]["offset"] == pytest.approx(TRUE_SHIFT, abs=1e-9)


def test_copy_move_block_count_cap_is_fail_closed():
    """ブロック数の上限は **例外**で知らせる(黙って間引かない / 黙って遅くならない)。

    ``step=1`` は既定なので、大きい画像では簡単に数十万ブロックになる。ここで
    黙って間引くと「実行はされたが実質何も見ていない」= 発見ゼロの偽装になる。
    """
    small = np.zeros((256, 256))                          # 249*249 = 62001 ブロック
    assert F.copy_move_regions(small, method="block") == []
    big = np.zeros((560, 560))                            # 553*553 = 305809 ブロック
    with pytest.raises(ValueError, match="上限"):
        F.copy_move_regions(big, method="block", block=8, step=1)
    # step を上げれば通る(何を失うかは test_copy_move_block_only_finds_multiples_of_step)
    assert F.copy_move_regions(big, method="block", block=8, step=2) == []
    assert F.MAX_BLOCKS == 300_000


def test_copy_move_rejects_unknown_method():
    with pytest.raises(ValueError, match="method"):
        F.copy_move_regions(textured(64, 4), method="sift")


# =========================================================================== #
# (7) 電子透かし                                                               #
# =========================================================================== #
@needs_pywt
def test_watermark_roundtrip_is_exact():
    """(A) 埋めたビット列がそのまま戻る。距離は :func:`hash_distance` で数える。"""
    base = textured(256, 7)
    bits = np.random.default_rng(0).integers(0, 2, 128).astype(bool)
    wm = F.watermark_embed(base, bits, strength=0.1)
    got = F.watermark_extract(wm, 128)
    assert got.dtype == np.bool_ and got.shape == (128,)
    assert F.hash_distance(bits, got) == 0
    assert wm.shape == base.shape
    # 透かしの無い画像から読むと、ただの乱数と変わらない(半分前後が違う)
    assert F.hash_distance(bits, F.watermark_extract(base, 128)) == 83


@needs_pywt
def test_watermark_strength_psnr_tradeoff():
    """(A) 強度 → PSNR / BER の表。**トレードオフを数で返す**ことがこの op の仕事。"""
    base = textured(256, 7)
    bits = np.random.default_rng(0).integers(0, 2, 128).astype(bool)
    cap = F.watermark_capacity(base, bits)
    assert cap["capacity_bits"] == 256 and cap["ll_shape"] == (128, 128)
    expect = {0.02: 45.48, 0.05: 44.48, 0.1: 42.95, 0.2: 40.32, 0.4: 36.37}
    for row in cap["rows"]:
        assert row["psnr_db"] == pytest.approx(expect[row["strength"]], abs=0.05)
        assert row["ber"] == 0.0
        assert row["clipped"] == 0.0
    # 強度を上げると PSNR は単調に下がる
    psnr = [r["psnr_db"] for r in cap["rows"]]
    assert psnr == sorted(psnr, reverse=True)
    assert cap["caveats"]


@needs_pywt
@needs_pil
def test_watermark_jpeg_robustness_needs_strength():
    """(A)+(B) 弱い透かしは JPEG で **19.5% が化ける**。これがトレードオフの実体。"""
    base = textured(256, 7)
    bits = np.random.default_rng(0).integers(0, 2, 128).astype(bool)
    rows = {r["strength"]: r for r in
            F.watermark_capacity(base, bits, jpeg_quality=75)["rows"]}
    assert rows[0.02]["ber_jpeg"] == pytest.approx(0.1953, abs=0.005)
    assert rows[0.05]["ber_jpeg"] == pytest.approx(0.0078, abs=0.005)
    assert rows[0.1]["ber_jpeg"] == 0.0
    assert rows[0.4]["ber_jpeg"] == 0.0
    # 品質を渡さなければ列そのものが入らない(環境で返る列が変わらない)
    assert "ber_jpeg" not in F.watermark_capacity(base, bits)["rows"][0]


@needs_pywt
def test_watermark_dies_under_geometric_change():
    """(B) **破綻点**: 1 px ずらすだけでブロックの位置がずれ、透かしが壊れる。"""
    base = textured(256, 7)
    bits = np.random.default_rng(0).integers(0, 2, 128).astype(bool)
    wm = F.watermark_embed(base, bits, strength=0.1)
    shifted = np.roll(wm, 1, axis=1)
    assert F.hash_distance(bits, F.watermark_extract(shifted, 128)) == 29


@needs_pywt
def test_watermark_is_fail_closed():
    base = textured(128, 7)
    bits = np.random.default_rng(0).integers(0, 2, 16).astype(bool)
    with pytest.raises(ValueError, match="float"):
        F.watermark_embed(base, bits.astype(np.float64))
    with pytest.raises(ValueError, match="0 と 1"):
        F.watermark_embed(base, np.array([0, 2, 1], int))
    with pytest.raises(ValueError, match="容量"):
        F.watermark_embed(base, np.ones(9999, bool))
    with pytest.raises(ValueError, match="容量"):
        F.watermark_extract(base, 9999)
    with pytest.raises(ValueError, match="strength"):
        F.watermark_embed(base, bits, strength=0.0)


# =========================================================================== #
# (8) 共通の契約(fail-closed / 決定性 / optional 依存)                          #
# =========================================================================== #
@pytest.mark.parametrize("op", ["perceptual_hash", "noise_inconsistency_map",
                                "jpeg_quality_estimate", "copy_move_regions"])
def test_ops_reject_broken_input(op):
    """非有限 / 空 / 次元違いは **文書化された ValueError**。黙って 0 で埋めない。"""
    fn = getattr(F, op)
    bad = natural(64, 1).copy()
    bad[3, 3] = np.nan
    with pytest.raises(ValueError, match="非有限"):
        fn(bad)
    with pytest.raises(ValueError, match="空"):
        fn(np.empty((0, 0)))
    with pytest.raises(ValueError):
        fn(np.zeros((4, 4, 5)))                           # 最終軸が 3 でも 4 でもない


def test_colour_input_is_reduced_to_luma_explicitly():
    """カラーは輝度に落とす。**落とすこと自体は docstring に書いてある**契約。"""
    g = natural(64, 1)
    rgb = np.stack([g, g, g], -1)
    assert np.array_equal(F.perceptual_hash(rgb), F.perceptual_hash(g))
    assert F._as_image(rgb).shape == (64, 64)
    with pytest.raises(ValueError, match="2-D のみ"):
        F._as_image(rgb, allow_color=False)


@pytest.mark.parametrize("op,args", [
    ("perceptual_hash", ()),
    ("noise_inconsistency_map", ()),
    ("copy_move_regions", ()),
])
def test_ops_are_deterministic(op, args):
    """同じ入力で 2 回呼んだら同じ答え(再現できない証拠は証拠ではない)。"""
    img = forge(textured(128, 4), src=(8, 8), dst=(60, 64), size=32)
    a, b = getattr(F, op)(img, *args), getattr(F, op)(img, *args)
    if isinstance(a, np.ndarray):
        assert np.array_equal(a, b)
    else:
        assert repr(a) == repr(b)


def test_area_resize_is_exact_area_average():
    """面積平均リサンプルが **平均を保つ**こと(ハッシュの安定性の土台)。"""
    rng = np.random.default_rng(0)
    x = rng.random((64, 96))
    for shape in ((8, 8), (32, 48), (16, 24)):
        y = F._area_resize(x, shape)
        assert y.shape == shape
        assert y.mean() == pytest.approx(x.mean(), abs=1e-12)
    # 整数倍の縮小はブロック平均と厳密に一致する
    blk = x.reshape(8, 8, 12, 8).mean(axis=(1, 3))
    assert np.allclose(F._area_resize(x, (8, 12)), blk, atol=1e-12)


def test_registry_declares_optional_dependencies():
    """optional 依存の表があり、**import は依存が無くても通る**設計であること。"""
    needs = opsimgforensics.requires()
    assert needs["error_level_map"] == ("PIL",)
    assert needs["jpeg_ghost_map"] == ("PIL",)
    assert needs["watermark_embed"] == ("pywt",)
    # 依存の要らない op は表に出ない
    assert "perceptual_hash" not in needs
    assert "copy_move_regions" not in needs
    # PIL 専用の一覧が取れる
    assert set(opsimgforensics.requires("PIL")) == {"error_level_map", "jpeg_ghost_map"}


def test_missing_optional_dependency_raises_a_useful_error(monkeypatch):
    """依存が無いときは **その op だけ**が、何を入れればよいか言う例外を出す。"""
    real_import = F.__builtins__["__import__"] if isinstance(F.__builtins__, dict) \
        else __import__

    def fake_import(name, *a, **kw):
        if name == "PIL":
            raise ImportError("no PIL for this test")
        return real_import(name, *a, **kw)

    monkeypatch.setattr("builtins.__import__", fake_import)
    # PyPI の配布名で案内する(`pip install PIL` は存在しない)
    with pytest.raises(ImportError, match="pip install Pillow"):
        F.error_level_map(natural(64, 1), 90)
    # 依存の要らない op は同じ状況でも普通に動く
    assert F.perceptual_hash(natural(64, 1)).size == 64


def test_no_op_returns_a_verdict():
    """**どの op も『改竄されている』と言わない**。この族の設計方針を機械で守る。

    table を返す 4 op の返りに、真偽の判定を名乗るキーが無いことを確認し、
    代わりに ``caveats``(その量が何を意味しないか)が必ず入っていることを固定する。
    """
    img = forge(textured(128, 4), src=(8, 8), dst=(60, 64), size=32)
    banned = {"tampered", "is_forged", "forged", "manipulated", "verdict",
              "authentic", "fake", "suspicious"}
    tables = [F.copy_move_regions(img)[0] if F.copy_move_regions(img) else {},
              F.jpeg_quality_estimate(img)]
    K = sensor_pattern(64, 5)
    fp = F.sensor_fingerprint([shoot(natural(64, 300 + i), K, seed=i) for i in range(3)])
    tables.append(F.fingerprint_correlate(shoot(natural(64, 900), K, seed=9), fp))
    for t in tables:
        if not t:
            continue
        assert not (banned & set(t)), sorted(banned & set(t))
        assert t.get("caveats")
        assert all(isinstance(c, str) for c in t["caveats"])


# =========================================================================
# TRIZ による点検で見つかった穴(2026-09-02)—— 証拠を解釈できる形にする
# =========================================================================

def test_null_distribution_is_measured_not_shipped():
    """しきい値は同梱しない。**利用者の清浄データから測る**。

    分離点は枚数・解像度・圧縮率・被写体で動くので、出荷時に決められる値では
    ない(各 op の caveats がそう言っている)。同梱するのは「しきい値の測り方」。
    """
    import numpy as np
    import imgforensics as F

    rng = np.random.default_rng(0)
    base = [(rng.random((64, 64)) * 255).astype(np.uint8) for _ in range(40)]
    clean = [F.hash_distance(F.perceptual_hash(x), F.perceptual_hash(y))
             for x in base[:20] for y in base[20:]]
    nd = F.null_distribution(clean)

    assert nd["n"] == 400
    assert 5 in nd["quantiles"] and 99 in nd["quantiles"]
    assert nd["quantiles"][5] <= nd["quantiles"][50] <= nd["quantiles"][99]
    assert any("普遍的なしきい値ではない" in c for c in nd["caveats"])


def test_a_small_sample_says_so_instead_of_extrapolating():
    import imgforensics as F
    nd = F.null_distribution([1.0, 2.0, 3.0, 4.0, 5.0])
    assert nd["n"] == 5
    assert any("裾に届かない" in c for c in nd["caveats"])


def test_evidence_quantile_places_the_value_without_judging_it():
    """関連する組は分布の外に、無関係な組は真ん中に座る。判定は返さない。

    実測: ずらした同一画像は距離 2 で **z = -7.05**(清浄分布の完全に外)、
    無関係な組の平均は **z = 0.00**。
    """
    import numpy as np
    import imgforensics as F

    rng = np.random.default_rng(0)
    base = [(rng.random((64, 64)) * 255).astype(np.uint8) for _ in range(40)]
    clean = [F.hash_distance(F.perceptual_hash(x), F.perceptual_hash(y))
             for x in base[:20] for y in base[20:]]
    nd = F.null_distribution(clean)

    a = base[0]
    d = F.hash_distance(F.perceptual_hash(a), F.perceptual_hash(np.roll(a, 1, axis=0)))
    q = F.evidence_quantile(d, nd, higher_is_stronger=False)
    assert q["beyond_fraction"] == 1.0
    assert q["z"] < -5.0
    assert "改竄" not in str(q.get("verdict", ""))            # 判定は返らない
    assert "verdict" not in q and "tampered" not in q

    typical = F.evidence_quantile(nd["mean"], nd, higher_is_stronger=False)
    assert abs(typical["z"]) < 1e-9


def test_the_direction_argument_matters_and_is_not_guessable():
    """向きを間違えると、いちばん強い証拠が「珍しくない」と出る(例外は出ない)。"""
    import numpy as np
    import imgforensics as F

    nd = F.null_distribution(np.arange(100.0))
    strong_low = F.evidence_quantile(1.0, nd, higher_is_stronger=False)
    wrong_way = F.evidence_quantile(1.0, nd, higher_is_stronger=True)
    # 1.0 sits beyond ~99% of the clean values 0..99 (exactly 1/99 lie below it)
    assert abs(strong_low["beyond_fraction"] - (1.0 - 1.0 / 99.0)) < 1e-9
    assert abs(wrong_way["beyond_fraction"] - 1.0 / 99.0) < 1e-9
    assert strong_low["direction"] != wrong_way["direction"]
    # strictly outside the clean range the two directions saturate at 1 and 0
    assert F.evidence_quantile(-1.0, nd, higher_is_stronger=False)["beyond_fraction"] == 1.0
    assert F.evidence_quantile(-1.0, nd, higher_is_stronger=True)["beyond_fraction"] == 0.0


def test_evidence_quantile_is_a_continuous_quantile_not_a_ladder():
    """Regression (2026-09-02 audit): ``beyond_fraction`` used to count how many of
    the 6 stored quantile markers the value passed (a {0, 1/6, ..., 1} ladder), so
    on the uniform sample 0..99 a measurement of 60 (true quantile 0.60) came out
    as 0.500 and 96 (true 0.96) as 0.833. The documented quantity is the fraction
    of clean values the measurement lies beyond — a continuous number that is
    exact at the stored knots and linear between them.
    """
    import numpy as np
    import imgforensics as F

    nd = F.null_distribution(np.arange(100.0))
    # exact at every stored knot: min / 5 / 25 / 50 / 75 / 95 / 99 percentiles / max
    for q, val in nd["quantiles"].items():
        got = F.evidence_quantile(val, nd, higher_is_stronger=True)["beyond_fraction"]
        assert abs(got - q / 100.0) < 1e-12, (q, val, got)
    assert F.evidence_quantile(nd["min"], nd)["beyond_fraction"] == 0.0
    assert F.evidence_quantile(nd["max"], nd)["beyond_fraction"] == 1.0
    # the two audit reproducers, now within linear-interpolation error of the truth
    for m, truth in ((60.0, 0.60), (96.0, 0.96), (3.0, 0.03), (80.0, 0.80)):
        got = F.evidence_quantile(m, nd, higher_is_stronger=True)["beyond_fraction"]
        assert abs(got - truth) < 0.012, (m, truth, got)
        assert got not in {0.0, 1 / 6, 2 / 6, 0.5, 4 / 6, 5 / 6, 1.0}
    # monotone in the measurement, and the two directions are complementary
    ms = np.linspace(-5.0, 105.0, 111)
    hi = [F.evidence_quantile(m, nd, higher_is_stronger=True)["beyond_fraction"] for m in ms]
    lo = [F.evidence_quantile(m, nd, higher_is_stronger=False)["beyond_fraction"] for m in ms]
    assert all(b >= a for a, b in zip(hi, hi[1:]))
    assert np.allclose(np.asarray(hi) + np.asarray(lo), 1.0)
    # a degenerate null (every clean value identical) still answers, at mid-rank
    flat = F.null_distribution([7.0] * 30)
    assert F.evidence_quantile(7.0, flat)["beyond_fraction"] == 0.5
    assert F.evidence_quantile(8.0, flat)["beyond_fraction"] == 1.0
    assert F.evidence_quantile(6.0, flat)["beyond_fraction"] == 0.0
    assert F.evidence_quantile(7.0, flat)["z"] is None


def test_calibration_ops_fail_closed():
    import numpy as np
    import pytest as _pytest
    import imgforensics as F

    with _pytest.raises(ValueError, match="at least one"):
        F.null_distribution([])
    with _pytest.raises(ValueError, match="finite"):
        F.null_distribution([1.0, np.nan])
    with _pytest.raises(ValueError, match="null_distribution"):
        F.evidence_quantile(1.0, {"mean": 0.0})
    with _pytest.raises(ValueError, match="measurement must be finite"):
        F.evidence_quantile(np.inf, F.null_distribution([1.0, 2.0]))
