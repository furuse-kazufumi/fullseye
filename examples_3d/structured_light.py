# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 構造化光(縞投影)で物体の高さを 3D 復元する (structured-light profilometry).

やりたいこと(素朴な言葉で): プロジェクタが「縞模様」を物体に投影し、カメラで撮る。
物体の凸凹で縞がずれる。そのずれ(位相)から、各画素の高さを測りたい。1 枚では
明るさと高さの区別がつかないので、縞を少しずつ横にずらした N 枚(位相シフト法)を撮る。

方法(このモジュールの op を鎖にする):
    既知の高さマップ(傾斜ランプ + こぶ)
      -> synthesize_fringes : 位相シフト縞画像 N 枚を合成(既知高さから作る=GT付き)
      -> wrapped_phase       : N 枚から巻き込み位相 (-π,π] を出す(縞のせいで 2π 跳びだらけ)
      -> unwrap_phase_2d     : 2π 跳びをつないで連続位相にする
      -> decode_fringe       : 参照平面(高さ0)の位相を引いて較正 k を掛け、高さを復元

検証(GT): 高さマップは自分で作った既知の真値。同じ搬送波で作った「高さ0の参照平面」の
位相を引くと搬送波が相殺し、残りが高さに比例する。復元高さと真の高さの RMSE を測る。
位相シフト法は大域オフセット(+2πm の定数)の不定性を残す(モジュール docstring 参照)ので、
GT は定数分を除いた「形」で比較する(差の平均を引いた残差 RMSE)。

beat-the-null(零点を上回る): アンラップを省いて巻き込み位相をそのまま高さとみなすと、
2π 跳びが残って大きく誤る。この null を明示し、アンラップ有りの実手法がそれを大幅に
下回る(小さい RMSE になる)ことを assert する。単なる「小さい誤差」ではなく
「零点に対して判別的に勝つ」ことを示す。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from fringe import synthesize_fringes, wrapped_phase, unwrap_phase_2d, decode_fringe


def make_height_map(rows, cols):
    """既知の高さマップ = 行方向の傾斜ランプ + ガウスのこぶ(真値 = GT)。

    搬送波は列方向(axis=1)に走らせるので、高さは行方向のランプにして向きを分離し、
    さらに局所的なこぶを乗せて「平面ではない」ことを分かりやすくする。
    """
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float64)
    yy /= max(rows, cols)
    xx /= max(rows, cols)
    tilt = 0.8 * yy                                   # 行方向に増える傾斜
    cx, cy, sigma = 0.5, 0.35, 0.12                   # こぶの中心と広がり
    bump = 0.5 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * sigma ** 2)))
    return tilt + bump


def demean(a):
    """有限値の平均を引く(+2πm の大域定数オフセットを吸収するため)。"""
    return a - np.nanmean(a)


def rmse(a, b):
    """2 配列の RMSE(定数オフセット除去後の形の一致を測る)。"""
    d = np.asarray(a) - np.asarray(b)
    return float(np.sqrt(np.nanmean(d * d)))


def main():
    rows, cols = 96, 96
    freq = 3.0            # 視野を横切る縞本数(搬送波の周期数)。>1 で 2π 跳びが必ず出る
    phase_gain = 4.0      # 高さ -> 位相ゲイン(rad/単位)
    k = 1.0 / phase_gain  # 復号側の較正定数(位相 -> 高さ)

    # --- 1) 既知の高さマップ(GT)と、それを高さ0にした参照平面 ---
    true_height = make_height_map(rows, cols)
    flat = np.zeros((rows, cols), dtype=np.float64)
    height_range = float(true_height.max() - true_height.min())

    # --- 2) synthesize_fringes: 既知高さ -> 位相シフト縞画像 N 枚(対象と参照) ---
    #     わずかなセンサノイズを載せる(無ノイズだと実質厳密で「サンプル」として不自然)。
    #     対象と参照でシードを変え、独立ノイズにする。
    noise = 0.01
    obj_images = synthesize_fringes(true_height, n_steps=4, freq=freq,
                                    phase_gain=phase_gain, noise=noise, seed=0)
    ref_images = synthesize_fringes(flat, n_steps=4, freq=freq,
                                    phase_gain=phase_gain, noise=noise, seed=1)

    # --- 3) wrapped_phase: N 枚 -> 巻き込み位相 (-π,π](搬送波のせいで 2π 跳びだらけ) ---
    wrapped_obj = wrapped_phase(obj_images)
    wrapped_ref = wrapped_phase(ref_images)
    n_wraps = int(np.sum(np.abs(np.diff(wrapped_obj, axis=1)) > np.pi))
    print(f"高さレンジ(真値)          : {height_range:.4f}")
    print(f"巻き込み位相の 2π 跳び本数 : {n_wraps}  (搬送波 {freq:.0f} 周期ぶん = 復元に unwrap 必須)")

    # --- 4) unwrap_phase_2d: 2π 跳びをつないで連続位相に(参照平面ぶんも) ---
    unwrapped_ref = unwrap_phase_2d(wrapped_ref)

    # --- 5) decode_fringe: 参照位相を引いて較正 k を掛け高さ復元(内部で wrapped->unwrap) ---
    recovered = decode_fringe(obj_images, ref_phase=unwrapped_ref, k=k)

    # --- 6) beat-the-null: アンラップ省略(巻き込み位相をそのまま高さとみなす)---
    #     参照の巻き込み位相を引いて k を掛けるだけ。2π 跳びが残るので大きく誤るはず。
    height_null = k * (wrapped_obj - wrapped_ref)

    # --- 7) GT 検証: 大域定数オフセットを除いた形で RMSE を比較 ---
    real_rmse = rmse(demean(recovered), demean(true_height))
    null_rmse = rmse(demean(height_null), demean(true_height))
    real_pct = 100.0 * real_rmse / height_range
    null_pct = 100.0 * null_rmse / height_range

    print(f"復元 RMSE (unwrap 有・実手法): {real_rmse:.6f}  ({real_pct:.3f}% of range)")
    print(f"null  RMSE (unwrap 無・零点) : {null_rmse:.6f}  ({null_pct:.3f}% of range)")

    # 実手法は高さレンジの数%未満で真値に一致する(無ノイズ・符号規約一致のため実質厳密)。
    assert real_rmse < 0.02 * height_range, \
        f"復元高さが真値と一致しない: RMSE {real_rmse:.6f} >= {0.02 * height_range:.6f}"
    # 零点を判別的に上回る: null は 2π 跳びで大きく誤り、実手法はそれを桁で下回る。
    assert real_rmse < 0.1 * null_rmse, \
        f"零点(unwrap 無)を十分に上回れていない: real {real_rmse:.6f} vs null {null_rmse:.6f}"

    print(f"PASS: 復元 RMSE {real_pct:.3f}% < 2% of range、かつ null({null_pct:.2f}%)を "
          f"{null_rmse / real_rmse:.0f}x 下回る(unwrap が 2π 跳びを解いて高さを復元)")


if __name__ == "__main__":
    main()
