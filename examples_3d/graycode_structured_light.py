# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: Gray code 構造化光で各画素の「投影機コラム番号」を絶対復号する (structured-light).

やりたいこと(素朴な言葉で): プロジェクタが白黒の縞(ビット面)を K 枚投影し、カメラで撮る。
各画素がどの縞パターンで「明」だったかを並べると、その画素を照らしている投影機コラムの
絶対番号(0..W-1 の整数)が分かる。位相シフト法(structured_light.py)は連続位相で
相対高さを出すが 2π 跳びの絶対次数が不定になる。Gray code はその絶対次数を「整数」で
一発確定させる相棒で、隣接コードが必ず 1 ビットしか違わない(1 画素の誤読が ±1 番以内に
収まる)ため境界に強い。

方法(このモジュールの op を使う):
    既知のコラム番号マップ(物体深度で湾曲した 0..W-1 の整数 GT)
      -> binary->Gray + ビット面展開 : 標準 Gray 符号のビット面 K 枚を自前合成(MSB first・明=1/暗=0)
      -> fringe.graycode_decode      : ビット面を二値化 -> Gray 組み立て -> Gray->binary で整数次数へ

検証(GT): コラム番号マップは自分で作った既知の整数真値。復号した整数マップが真値と
**全画素で厳密一致**(整数の完全一致)することを要求する。連続量の RMSE ではなく整数の
完全一致なので、1 ビットでも組み立て順・極性を間違えれば判別的に落ちる。撮影ノイズは
コントラストの半分近く(±0.25)まで載せるが、しきい値二値化がそれを吸収し復号は厳密に保たれる
(= しきい値クロスオラクル的な頑健性を同時に示す)。

beat-the-null(零点を上回る): 明暗の極性を反転した束(配線ミス相当)や、ビット面順を
MSB<->LSB 取り違えた束(順序ミス相当)、さらに「常に最頻値を返す」自明復号を null として
同じ計測をする。Gray->binary は GF(2) 上で線形なので、極性反転 null は復号値が真値と
定数 XOR ずれ(!=0)になり **全画素で不一致(一致率 0%)**。実手法(一致率 100%)との差が桁で開く。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from fringe import graycode_decode


def binary_to_gray(n):
    """標準の binary -> Gray 変換: gray = n XOR (n >> 1)(隣接値が 1 ビットだけ違う符号)。"""
    n = np.asarray(n, dtype=np.int64)
    return n ^ (n >> 1)


def make_column_code_map(rows, cols, warp_amp=6.0):
    """既知の「投影機コラム番号」GT マップを作る(物体深度で湾曲した 0..cols-1 の整数場)。

    素の値は列インデックス x のランプ。物体の凸凹があると、同じ画素でも見えている投影機
    コラムが行ごとにずれる。これを行方向の正弦ワープ(振幅 warp_amp)で模し、単なる列一定
    ではない「本物の 2 次元整数マップ」にする。値は clip で 0..cols-1 に収め、Gray 符号化
    可能なビット数に収まるようにする(復号側の値域 0..2**K-1 と厳密一致させるため)。
    """
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float64)
    warp = np.round(warp_amp * np.sin(2.0 * np.pi * yy / rows))   # 行方向の湾曲(整数ずれ)
    code = np.clip(xx + warp, 0, cols - 1).astype(np.int64)       # 0..cols-1 の整数 GT
    return code


def encode_graycode_bitplanes(code, k, bright=0.8, dark=0.2,
                              noise_std=0.12, noise_clip=0.25, seed=1):
    """整数コードマップ -> Gray code ビット面束 (K, H, W)(MSB first・明=1/暗=0)。

    fringe.graycode_decode は bit_images[0] を最上位ビットとして扱う(MSB first)ので、
    重み (k-1-i) のビットを i 番目の面に置く。撮影ノイズを ±noise_clip で頭打ちにして
    載せる: bright-noise_clip > thresh かつ dark+noise_clip < thresh を保てば二値化は
    絶対に反転しない(= 復号は厳密なまま)。この頑健さも同時に示す。

    返り値: (planes, max_abs_noise)。max_abs_noise は実際に載ったノイズの最大振幅。
    """
    gray = binary_to_gray(code)                     # 各画素の Gray 整数
    rng = np.random.default_rng(seed)
    H, W = code.shape
    planes = np.empty((k, H, W), dtype=np.float64)
    max_abs_noise = 0.0
    for i in range(k):
        weight = k - 1 - i                          # MSB first: 面 0 が最上位
        bit = (gray >> weight) & 1                  # そのビット面(0/1)
        base = np.where(bit == 1, bright, dark)     # 明=bright / 暗=dark
        noise = np.clip(rng.normal(0.0, noise_std, size=base.shape),
                        -noise_clip, noise_clip)    # ノイズを頭打ち(反転させない)
        max_abs_noise = max(max_abs_noise, float(np.max(np.abs(noise))))
        planes[i] = np.clip(base + noise, 0.0, 1.0)
    return planes, max_abs_noise


def match_fraction(a, b):
    """2 つの整数マップの画素ごと完全一致率(1.0 = 全画素一致)。"""
    a = np.asarray(a); b = np.asarray(b)
    return float(np.mean(a == b))


def main():
    rows, cols = 96, 128            # W=128 = 2**7 -> K=7 ビット面で 0..127 を一意符号化
    thresh = 0.5

    # --- 1) 既知の GT: 物体深度で湾曲した投影機コラム番号マップ(整数真値) ---
    code_gt = make_column_code_map(rows, cols, warp_amp=6.0)
    k = int(code_gt.max()).bit_length()             # 必要ビット数(127 -> 7)
    n_distinct = int(np.unique(code_gt).size)
    print(f"画像サイズ (H,W)            : {rows}x{cols}")
    print(f"GT コード値域               : {int(code_gt.min())}..{int(code_gt.max())}  "
          f"(異なるコード {n_distinct} 種)")
    print(f"Gray code ビット面枚数 K    : {k}  (復号値域 0..{2**k - 1})")

    # --- 2) 自前合成: binary->Gray -> ビット面 K 枚(MSB first・明暗+頭打ちノイズ) ---
    bit_images, max_noise = encode_graycode_bitplanes(
        code_gt, k, bright=0.8, dark=0.2, noise_std=0.12, noise_clip=0.25, seed=1)
    contrast = 0.8 - 0.2
    print(f"ビット面 明/暗 コントラスト : {contrast:.2f}  (載せた撮影ノイズ最大 {max_noise:.3f} "
          f"= コントラストの {100 * max_noise / contrast:.0f}%)")

    # --- 3) 実手法: fringe.graycode_decode で整数コードへ絶対復号 ---
    decoded = graycode_decode(bit_images, thresh=thresh)

    # --- 4) beat-the-null: 3 つの零点で同じ計測 ---
    #   (a) 極性反転(明暗の配線ミス相当): 1-画像 で二値が全反転
    null_inv = graycode_decode(1.0 - bit_images, thresh=thresh)
    #   (b) ビット面順の取り違え(MSB<->LSB): 面を逆順に渡す
    null_lsb = graycode_decode(bit_images[::-1], thresh=thresh)
    #   (c) 自明復号: 全画素を GT の最頻値と決め打ち(情報ゼロのベースライン)
    mode_val = int(np.bincount(code_gt.ravel()).argmax())
    null_const = np.full_like(code_gt, mode_val)

    # --- 5) GT 検証: 完全一致率 ---
    real = match_fraction(decoded, code_gt)
    m_inv = match_fraction(null_inv, code_gt)
    m_lsb = match_fraction(null_lsb, code_gt)
    m_const = match_fraction(null_const, code_gt)
    print(f"実手法 一致率               : {100 * real:.3f}%  (全 {rows * cols} 画素)")
    print(f"null(極性反転) 一致率      : {100 * m_inv:.3f}%")
    print(f"null(面順取り違え) 一致率  : {100 * m_lsb:.3f}%")
    print(f"null(最頻値決め打ち) 一致率: {100 * m_const:.3f}%")

    # GT: 復号した整数マップが真値と全画素で厳密一致(整数の完全一致)すること。
    assert decoded.dtype == np.int64, f"復号 dtype が int ではない: {decoded.dtype}"
    assert np.array_equal(decoded, code_gt), \
        f"復号コードが真値と厳密一致しない(一致率 {100 * real:.3f}%)"
    # 零点を判別的に上回る: 極性反転 null は GF(2) 線形性から全画素不一致(0%)になる。
    assert real == 1.0, f"実手法が完全一致でない: {100 * real:.3f}%"
    assert m_inv < 0.5, f"極性反転 null が一致しすぎ: {100 * m_inv:.3f}%"
    assert m_lsb < 0.5, f"面順取り違え null が一致しすぎ: {100 * m_lsb:.3f}%"
    assert m_const < 0.5, f"最頻値決め打ち null が一致しすぎ: {100 * m_const:.3f}%"
    assert real > max(m_inv, m_lsb, m_const), "実手法が null を上回っていない"

    print(f"PASS: Gray code 復号が全 {rows * cols} 画素で整数厳密一致(100.000%)、"
          f"零点(極性反転 {100 * m_inv:.1f}% / 面順 {100 * m_lsb:.1f}% / "
          f"最頻値 {100 * m_const:.1f}%)を判別的に上回る")


if __name__ == "__main__":
    main()
