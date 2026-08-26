"""fringe — 構造化光による位相シフト・プロファイロメトリ(3D 形状計測)。

産業 3D スキャンの中核となる「縞投影(fringe projection)」の復号一式を提供する。プロジェクタが
正弦縞パターンを対象に投影し、カメラが撮る。物体の高さで縞が変形するので、その位相ずれから高さを
復元する(三角測量の一種)。Physical AI 用の 3D 計測サンプル(既知形状 → 縞画像 → 復元)生成にも使う。

パイプライン:
    位相シフト N 枚 → wrapped_phase(-π,π] → unwrap_phase_2d(連続位相) → phase_to_height(高さ)
    (絶対次数が要るときは Gray code を併用: graycode_decode で整数フリンジ次数を出す)

規約(重要):
    * 画像は numpy 2D 配列、値域 [0,1] を想定(範囲外でも計算は通るが変調度の意味が薄れる)。
    * 位相シフト量は等間隔 δ_n = 2πn/N(n = 0..N-1)。
    * wrapped_phase は φ = atan2(Σ_n I_n sin δ_n, Σ_n I_n cos δ_n)(標準 N-step 公式)。
      本モジュールの synthesize_fringes は I_n = a + b·cos(φ - δ_n) で縞を作るので、この公式が
      与位相 φ をそのまま(符号反転なしで)復元する — 生成と復号の符号規約を一致させてある。

limitations(正直な制約):
    * 位相アンラップ(spatial unwrap)は Itoh の仮定「隣接画素の真の位相差 < π」に依存する。
      急峻な段差・深い穴・オクルージョン境界では破綻し得る(縞次数の飛びを誤る)。絶対性が要る
      場面では graycode_decode(または多周波位相)で次数を確定させること。
    * unwrap は大域オフセット(+2πm の定数)の不定性を残す。参照平面位相 ref_phase の減算で
      相対高さは正しく出るが、絶対高さ 0 面の同定には較正(k と ref_phase)が要る。
    * 低変調画素(影・飽和・低反射)は位相が不定。modulation() でマスクして NaN 化するのが安全。
"""
from __future__ import annotations

import numpy as np

try:  # skimage は必須依存だが、無い環境では unwrap のみ graceful に失敗させる
    from skimage.restoration import unwrap_phase as _sk_unwrap_phase
    _HAVE_SKIMAGE = True
except Exception:  # pragma: no cover - 環境依存
    _sk_unwrap_phase = None
    _HAVE_SKIMAGE = False


# --------------------------------------------------------------------------- #
# 内部ヘルパ                                                                    #
# --------------------------------------------------------------------------- #
def _as_stack(images) -> np.ndarray:
    """位相シフト画像列 → (N, H, W) float 配列に正規化+検証。

    images: 長さ N のシーケンス(各 2D 画像)または (N, H, W) 配列。N >= 3 が必須。
    """
    if images is None:
        raise ValueError("images が None です(位相シフト画像列を渡してください)")
    stack = np.asarray(images, dtype=np.float64)
    if stack.ndim != 3:
        raise ValueError(
            f"位相シフト画像列は (N, H, W) の 3 次元である必要があります: 実際は shape={stack.shape}"
        )
    n = stack.shape[0]
    if n < 3:
        raise ValueError(f"N-step 位相シフトには N >= 3 が必要です: N={n}")
    if not np.all(np.isfinite(stack)):
        raise ValueError("位相シフト画像に非有限値(NaN/Inf)が含まれています")
    return stack


def _phase_sums(stack: np.ndarray):
    """Σ_n I_n sin δ_n(=s)と Σ_n I_n cos δ_n(=c)を返す(δ_n = 2πn/N)。"""
    n = stack.shape[0]
    delta = 2.0 * np.pi * np.arange(n) / n
    # (N,) と (N,H,W) の n 軸縮約
    s = np.tensordot(np.sin(delta), stack, axes=(0, 0))
    c = np.tensordot(np.cos(delta), stack, axes=(0, 0))
    return s, c


# --------------------------------------------------------------------------- #
# 1. wrapped phase                                                             #
# --------------------------------------------------------------------------- #
def wrapped_phase(images) -> np.ndarray:
    """N-step 位相シフト縞画像から wrapped phase (-π, π] を求める。

    標準 N-step 公式 φ = atan2(Σ_n I_n sin(2πn/N), Σ_n I_n cos(2πn/N))。N >= 3 の等間隔位相シフトを
    仮定。返り値は各画素の巻き込み位相(-π,π] の 2D 配列。

    images: 長さ N のシーケンス(各 2D [0,1] 画像)または (N, H, W) 配列。
    """
    stack = _as_stack(images)
    s, c = _phase_sums(stack)
    return np.arctan2(s, c)


# --------------------------------------------------------------------------- #
# 2. modulation(データ変調度 = 信頼度マップ)                                   #
# --------------------------------------------------------------------------- #
def modulation(images) -> np.ndarray:
    """縞のデータ変調度(fringe contrast = 振幅/平均)を返す。信頼度マップとして使う。

    振幅 b = (2/N)·sqrt(s² + c²)、平均 a = mean_n I_n(s,c は Σ I sin/cos)。変調度 γ = b/a。
    影・飽和・低反射で γ は小さくなる。低変調画素をマスクして位相を NaN 化するのに使う。
    平均が 0 の画素は γ=0(位相が定義できない)とする。
    """
    stack = _as_stack(images)
    n = stack.shape[0]
    s, c = _phase_sums(stack)
    amp = (2.0 / n) * np.hypot(s, c)
    mean = stack.mean(axis=0)
    gamma = np.zeros_like(amp)
    valid = np.abs(mean) > 1e-12
    gamma[valid] = amp[valid] / mean[valid]
    return gamma


# --------------------------------------------------------------------------- #
# 3. 2D 位相アンラップ(skimage ラッパ / NaN・マスク対応)                        #
# --------------------------------------------------------------------------- #
def unwrap_phase_2d(wrapped, mask=None) -> np.ndarray:
    """wrapped phase を skimage.restoration.unwrap_phase で連続位相に展開する。

    wrapped: wrapped_phase の出力(2D)。NaN を含んでよい(無効画素として扱う)。
    mask:    省略可。True = 有効画素(numpy masked array の慣習とは逆にした直感的な向き)。
             NaN 画素と mask=False 画素は無効としてアンラップから除外し、出力では NaN を返す。

    返り値: 連続位相(2D float)。無効画素は NaN。大域オフセット(+2πm)の不定性は残る。
    """
    if not _HAVE_SKIMAGE or _sk_unwrap_phase is None:
        raise RuntimeError(
            "skimage.restoration.unwrap_phase が利用できません(scikit-image を導入してください)"
        )
    arr = np.asarray(wrapped, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"unwrap_phase_2d は 2D 配列を想定: 実際は shape={arr.shape}")

    invalid = ~np.isfinite(arr)
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != arr.shape:
            raise ValueError(
                f"mask の形状 {mask.shape} が wrapped の形状 {arr.shape} と一致しません"
            )
        invalid = invalid | (~mask)

    if not invalid.any():
        return np.asarray(_sk_unwrap_phase(arr), dtype=np.float64)

    if invalid.all():
        raise ValueError("有効画素が 1 つもありません(全画素が NaN/マスク済み)")

    # 無効画素を masked array で除外してアンラップ(skimage が対応)。
    filled = np.where(invalid, 0.0, arr)
    ma = np.ma.array(filled, mask=invalid)
    unwrapped_ma = _sk_unwrap_phase(ma)
    out = np.array(np.ma.getdata(unwrapped_ma), dtype=np.float64)
    out[invalid] = np.nan
    return out


# --------------------------------------------------------------------------- #
# 4. Gray code デコード(絶対フリンジ次数)                                       #
# --------------------------------------------------------------------------- #
def graycode_decode(bit_images, thresh=0.5) -> np.ndarray:
    """Gray code ビット画像列 → 整数フリンジ次数マップ(絶対次数)。

    bit_images: 長さ K のシーケンス(各 2D 画像、明=1 / 暗=0)。**MSB first**(bit_images[0] が
                最上位ビット)。thresh で二値化する。
    thresh:     二値化しきい値(画素値 >= thresh を 1)。

    処理: 各ビット面を二値化 → MSB first で Gray 値を組み立て → Gray→binary 変換
          (binary = gray ^ (gray>>1) ^ ... ^ (gray>>(K-1)))で絶対次数(整数)を返す。
    返り値: dtype int64 の 2D 次数マップ(値域 0..2**K-1)。
    """
    if bit_images is None:
        raise ValueError("bit_images が None です")
    bits_stack = np.asarray(bit_images, dtype=np.float64)
    if bits_stack.ndim != 3:
        raise ValueError(
            f"bit_images は (K, H, W) の 3 次元が必要: 実際は shape={bits_stack.shape}"
        )
    k = bits_stack.shape[0]
    if k < 1:
        raise ValueError("Gray code のビット面が 1 枚もありません")
    if k > 62:
        raise ValueError(f"ビット数が多すぎます(int64 では K<=62): K={k}")
    if not np.all(np.isfinite(bits_stack)):
        raise ValueError("bit_images に非有限値(NaN/Inf)が含まれています")

    # 二値化 → Gray 整数(MSB first)
    binimg = (bits_stack >= thresh).astype(np.int64)
    gray = np.zeros(bits_stack.shape[1:], dtype=np.int64)
    for i in range(k):
        gray |= binimg[i] << (k - 1 - i)

    # Gray → binary: XOR of gray>>0, gray>>1, ..., gray>>(k-1)
    binary = gray.copy()
    for shift in range(1, k):
        binary ^= (gray >> shift)
    return binary


# --------------------------------------------------------------------------- #
# 5. 位相 → 高さ(参照平面線形モデル)                                            #
# --------------------------------------------------------------------------- #
def phase_to_height(phase, ref_phase, k) -> np.ndarray:
    """参照平面線形モデルで位相を高さに変換する: height = k·(phase - ref_phase)。

    phase:     計測対象の(アンラップ済み)連続位相。NaN を含んでよい(そのまま伝播)。
    ref_phase: 参照平面(高さ 0)の連続位相。スカラも 2D 配列も可。
    k:         較正定数(位相→高さのスケール、単位/rad)。符号反転もここで吸収できる。

    位相シフト法の高さは Δφ に線形で、Δφ = phase - ref_phase。較正 k は既知形状で決める。
    """
    ph = np.asarray(phase, dtype=np.float64)
    ref = np.asarray(ref_phase, dtype=np.float64)
    if ref.ndim != 0 and ref.shape != ph.shape:
        raise ValueError(
            f"ref_phase の形状 {ref.shape} が phase の形状 {ph.shape} と一致しません"
        )
    kf = float(k)
    return kf * (ph - ref)


# --------------------------------------------------------------------------- #
# 6. 便利関数: 位相シフト画像列 → 高さ                                           #
# --------------------------------------------------------------------------- #
def decode_fringe(phase_shift_images, ref_phase=None, k=1.0,
                  mask=None, min_modulation=None) -> np.ndarray:
    """位相シフト画像列を一括復号: wrapped → unwrap →(参照減算で)高さ。

    phase_shift_images: N-step 位相シフト縞画像列((N,H,W) または長さ N のシーケンス)。
    ref_phase:          参照平面(高さ 0)のアンラップ済み位相。None なら高さ = k·(unwrapped)。
    k:                  位相→高さ較正定数。
    mask:               省略可。True=有効画素。無効画素は NaN。
    min_modulation:     省略可。指定すると modulation < この値の画素を低信頼として無効化。

    返り値: 高さマップ(2D float)。ref_phase=None のときは k を掛けた連続位相を返す。
    無効画素は NaN。
    """
    stack = _as_stack(phase_shift_images)
    wrapped = wrapped_phase(stack)

    reliab = None
    if min_modulation is not None:
        reliab = modulation(stack) >= float(min_modulation)
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        reliab = m if reliab is None else (reliab & m)

    unwrapped = unwrap_phase_2d(wrapped, mask=reliab)
    if ref_phase is None:
        return float(k) * unwrapped
    return phase_to_height(unwrapped, ref_phase, k)


# --------------------------------------------------------------------------- #
# 7. 合成ヘルパ: 既知 height map → 位相シフト縞画像列                            #
# --------------------------------------------------------------------------- #
def synthesize_fringes(height, n_steps=4, freq=1.0, phase_gain=1.0,
                       bias=0.5, amplitude=0.5, axis=1, noise=0.0,
                       seed=None, return_phase=False):
    """既知の height map から N-step 位相シフト縞画像列を合成する(テスト/サンプル生成用)。

    モデル: 総位相 φ(x,y) = φ_carrier + phase_gain·height。搬送波 φ_carrier は視野を横切る線形
    ランプ(freq 周期)。各フレームは I_n = bias + amplitude·cos(φ - δ_n), δ_n = 2πn/N。
    この符号規約により wrapped_phase(...) は総位相 φ をそのまま復元する。

    height:      2D 配列(計測対象の高さ場、任意単位)。
    n_steps:     位相シフト枚数 N(>=3)。
    freq:        視野幅を横切る搬送波の周期数(縞本数)。0 なら搬送波なし(height のみ)。
    phase_gain:  高さ→位相の変換ゲイン(rad/単位)。復号側の較正 k = 1/phase_gain に対応。
    bias:        平均輝度 a(既定 0.5)。
    amplitude:   縞振幅 b(既定 0.5)。bias±amplitude が [0,1] に収まると自然。
    axis:        搬送波の方向(1 = 列方向 x に沿う既定、0 = 行方向 y)。
    noise:       付加ガウスノイズの標準偏差(0 で無ノイズ)。
    seed:        ノイズ用乱数シード。
    return_phase: True なら (images, total_phase) を返す(テスト・デバッグ用)。

    返り値: (N, H, W) float 配列(値域 [0,1] にクリップ)。return_phase=True なら位相も。
    """
    h = np.asarray(height, dtype=np.float64)
    if h.ndim != 2:
        raise ValueError(f"height は 2D 配列が必要: 実際は shape={h.shape}")
    n = int(n_steps)
    if n < 3:
        raise ValueError(f"n_steps は 3 以上が必要: n_steps={n}")
    if axis not in (0, 1):
        raise ValueError(f"axis は 0(行) か 1(列) のみ: axis={axis}")
    if amplitude < 0 or bias < 0:
        raise ValueError("bias / amplitude は非負である必要があります")

    rows, cols = h.shape
    # 搬送波: axis に沿った [0,1) 正規化座標 × 2π × freq
    if axis == 1:
        length = max(cols, 1)
        coord = (np.arange(cols, dtype=np.float64) / length)[None, :]
    else:
        length = max(rows, 1)
        coord = (np.arange(rows, dtype=np.float64) / length)[:, None]
    carrier = 2.0 * np.pi * float(freq) * coord  # broadcast → (rows, cols)
    carrier = np.broadcast_to(carrier, h.shape)

    total_phase = carrier + float(phase_gain) * h

    rng = np.random.default_rng(seed)
    images = np.empty((n, rows, cols), dtype=np.float64)
    for idx in range(n):
        delta = 2.0 * np.pi * idx / n
        frame = float(bias) + float(amplitude) * np.cos(total_phase - delta)
        if noise:
            frame = frame + rng.normal(0.0, float(noise), size=frame.shape)
        images[idx] = np.clip(frame, 0.0, 1.0)

    if return_phase:
        return images, total_phase
    return images
