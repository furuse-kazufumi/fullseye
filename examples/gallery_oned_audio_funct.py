# -*- coding: utf-8 -*-
"""事例: 音のファイルを読み、特徴量と零交差率を出し、1-D 関数を組み替える(1-D の台帳 op ギャラリー: dsp / funct1d)

平たく言うと:
  一時ディレクトリに小さな WAV を標準ライブラリ(wave)で書き、``read_audio`` で読み戻して値が 1 LSB 以内で一致するかを見る
  (repo には書かない・ネットに出ない)。整数周期の余弦波で特徴量を閉形式と、零交差の数を解析的な交差時刻と比べ、
  HALCON 流の 1-D 関数の op を手計算と照合する。各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * read_audio          —— 16 bit の整数値 / 32768 と完全一致・サンプリング周波数、ステレオは左右の平均
  * zero_crossing_rate  —— docstring の例 [1, 0, 1, 0, 1] → 0・[1, 0, −1] → 0.5、正弦波は交差時刻 (kπ − φ)/(2πf) の個数 / (N − 1)
  * signal_features     —— 振幅 A の 50 Hz 余弦(1000 点で 50 周期ちょうど): rms = A/√2・peak = A・波高率 √2・ピーク周波数 50 Hz
  * compose_funct_1d    —— y1(y2): 位置を四捨五入して端で止める(負は先頭、範囲外は末尾)
  * negate_funct_1d     —— −y、2 回で元に戻る
  * transform_funct_1d  —— (2i + 1, 3y − 1) の組を手計算と

    py -3.11 examples/gallery_oned_audio_funct.py
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import dsp  # noqa: E402
import funct1d as F  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def _write_pcm16(path: str, frames: np.ndarray, rate: int) -> None:
    """int16 の (n,) か (n, ch) を標準ライブラリだけで WAV に書く(読む側の op とは独立の経路)。"""
    a = np.asarray(frames, np.int16)
    ch = 1 if a.ndim == 1 else a.shape[1]
    with wave.open(path, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(a.astype("<i2").tobytes())


def demo_read_audio() -> None:
    rng = np.random.default_rng(7)
    rate = 8000
    n = np.arange(800)
    mono = np.round(20000 * np.sin(2 * math.pi * 440 * n / rate)).astype(np.int16)
    left = rng.integers(-30000, 30000, 400).astype(np.int16)
    right = rng.integers(-30000, 30000, 400).astype(np.int16)
    with tempfile.TemporaryDirectory(prefix="fullseye_audio_") as tmp:
        p1 = os.path.join(tmp, "mono.wav")
        _write_pcm16(p1, mono, rate)
        x, r = dsp.read_audio(p1)
        err = float(np.abs(x - mono / 32768.0).max())
        check("read_audio", "16 bit モノラル 800 点(440 Hz)を一時ディレクトリに書いて読む", f"整数 / 32768 と一致、rate {rate}",
              f"差 {err:.1e}、rate {r}、{len(x)} 点", err == 0.0 and r == rate and len(x) == 800)
        p2 = os.path.join(tmp, "stereo.wav")
        _write_pcm16(p2, np.column_stack([left, right]), 22050)
        y, r2 = dsp.read_audio(p2)
        want = (left / 32768.0 + right / 32768.0) / 2
        err2 = float(np.abs(y - want).max())
        check("read_audio", "16 bit ステレオ 400 点(乱数、seed 7)", "左右の平均のモノラル、rate 22050",
              f"差 {err2:.1e}、rate {r2}、形 {y.shape}", err2 < 1e-15 and r2 == 22050 and y.shape == (400,))


def demo_zcr_features() -> None:
    a = dsp.zero_crossing_rate([1, 0, 1, 0, 1])
    b = dsp.zero_crossing_rate([1, 0, -1])
    check("zero_crossing_rate", "docstring の例 [1,0,1,0,1] と [1,0,−1]", "0.0 と 0.5(ちょうど 0 は交差でない)", f"{a} と {b}",
          a == 0.0 and b == 0.5)
    fs, f, ph, N = 1000.0, 37.0, 0.3, 1000
    t = np.arange(N) / fs
    x = np.sin(2 * math.pi * f * t + ph)
    t_end = (N - 1) / fs
    k = np.arange(1, 200)
    tk = (k * math.pi - ph) / (2 * math.pi * f)                # sin の零点の時刻
    n_cross = int(np.count_nonzero((tk > 0) & (tk < t_end)))
    z = dsp.zero_crossing_rate(x)
    check("zero_crossing_rate", "37 Hz の正弦(位相 0.3)、fs 1 kHz、1000 点", f"交差 {n_cross} 回 / 999 = {n_cross / 999:.6f}",
          f"{z:.6f}", abs(z - n_cross / 999) < 1e-15)

    A = 0.8
    c = A * np.cos(2 * math.pi * 50 * t)
    ft = dsp.signal_features(c, rate=fs)
    ok = (abs(ft["rms"] - A / math.sqrt(2)) < 1e-6 and ft["peak"] == A and abs(ft["crest_factor"] - math.sqrt(2)) < 1e-4
          and ft["peak_freq"] == 50.0 and abs(ft["spectral_centroid"] - 50.0) < 1e-3 and ft["bandwidth"] < 1e-3
          and ft["zcr"] == round(dsp.zero_crossing_rate(c), 6))
    check("signal_features", "0.8·cos(2π·50 t)、fs 1 kHz、1000 点(50 周期ちょうど)",
          f"rms {A / math.sqrt(2):.6f}、peak 0.8、波高率 √2、ピーク・重心 50 Hz、帯域 ≈ 0",
          f"rms {ft['rms']}、peak {ft['peak']}、{ft['crest_factor']}、{ft['peak_freq']} / {ft['spectral_centroid']} Hz、帯域 {ft['bandwidth']}", ok)
    two = A * np.cos(2 * math.pi * 50 * t) + 0.4 * np.cos(2 * math.pi * 200 * t)
    f2 = dsp.signal_features(two, rate=fs)
    cen = (0.8 * 50 + 0.4 * 200) / 1.2
    bw = math.sqrt((0.8 * (50 - cen) ** 2 + 0.4 * (200 - cen) ** 2) / 1.2)
    check("signal_features", "50 Hz(0.8)+ 200 Hz(0.4)", f"重心 (0.8·50 + 0.4·200)/1.2 = {cen:.3f}、帯域 {bw:.3f}、rms √(0.8² + 0.4²)/√2",
          f"{f2['spectral_centroid']}、{f2['bandwidth']}、{f2['rms']}",
          abs(f2["spectral_centroid"] - cen) < 2e-3 and abs(f2["bandwidth"] - bw) < 2e-3
          and abs(f2["rms"] - math.sqrt(0.8 ** 2 + 0.4 ** 2) / math.sqrt(2)) < 1e-6)


def demo_funct1d() -> None:
    y1 = np.arange(6) * 10.0                                    # 0, 10, …, 50
    out = F.compose_funct_1d(y1, [0, 1.4, 2.6, -3, 99, 4.5])
    want = [0.0, 10.0, 30.0, 0.0, 50.0, 40.0]                   # 4.5 は np.round で偶数へ → 4
    check("compose_funct_1d", "y1 = 10·i(6 点)、位置 (0, 1.4, 2.6, −3, 99, 4.5)", f"{want}(端で止める、4.5 → 4)",
          str(out.tolist()), out.tolist() == want)
    y = np.array([0.5, -2.0, 3.25, 0.0])
    ng = F.negate_funct_1d(y)
    check("negate_funct_1d", "y = (0.5, −2, 3.25, 0)", "(−0.5, 2, −3.25, −0)、2 回で元", str(ng.tolist()),
          np.array_equal(ng, -y) and np.array_equal(F.negate_funct_1d(ng), y) and len(F.negate_funct_1d([])) == 0)
    tr = F.transform_funct_1d(y, mult_x=2.0, add_x=1.0, mult_y=3.0, add_y=-1.0)
    want_t = [[1.0, 0.5], [3.0, -7.0], [5.0, 8.75], [7.0, -1.0]]
    check("transform_funct_1d", "同じ y を x → 2i + 1、y → 3y − 1", str(want_t), str(tr.tolist()), tr.tolist() == want_t)


def main() -> int:
    t0 = time.time()
    demo_read_audio()
    demo_zcr_features()
    demo_funct1d()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
