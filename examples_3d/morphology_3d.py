"""事例: 3Dボクセル形状のノイズ除去 (3D モルフォロジー: closing / opening / gradient / top-hat).

CTスキャンや点群を voxel 化すると、形が「だいたい正しい」だけで細かい欠陥が残る:
  (1) 本体の内側に小さな空洞(穴)が空く   — 例: スキャンの取りこぼし
  (2) 本体から細いトゲ(突起)がはみ出す   — 例: ノイズ点の塊
これを直したいが、素朴に「膨らませる/削る」だけだと本体まで太ったり痩せたりする。

手法(この4つの op を鎖状につなぐ):
  - closing  = dilate → erode : 小さな空洞を埋める(本体サイズは戻る)
  - opening  = erode  → dilate : 細い突起を消す(本体サイズは戻る)
  - morph_gradient3d           : dilate − erode = 表面の殻(境界)だけを取り出す
  - morph_tophat3d             : vol − opening = SE より細い明構造(=そのトゲ)を抽出

なぜ closing/opening なのか(beat-the-null): 空洞を埋めるだけなら「素の dilate」でも埋まる。
だが素の dilate は本体まで 1 voxel 膨らんだまま(太る)。closing は続く erode で元のサイズに
戻すので、空洞は埋まったまま本体形状は保存される。ここが素の dilate との判別点。
同様に opening は「素の erode(突起は消えるが本体が痩せる)」を上回る。

検証(GT): 合成データなので真値が既知:
  - 本体 = 12×12×12 の中実キューブ(既知の bounding box)
  - 既知の 2×2×2 内部空洞と、既知の 3 voxel の細いトゲを人工的に入れる
これに対し closing 後の空洞 voxel 数 = 0、本体との対称差 = 0(=完全一致)を要求する。
素の dilate はこの対称差が大きく(本体が膨張)、closing がそれを判別的に上回ることを確認する。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import match3d as m


def _validate_volume(vol, name):
    """3D の非退化ボクセル配列であることを検証(退化入力で偽の成功を出さない)。"""
    a = np.asarray(vol)
    if a.ndim != 3:
        raise ValueError(f"{name}: 3D 配列が必要 (ndim={a.ndim}, shape={a.shape})")
    if a.size == 0 or 0 in a.shape:
        raise ValueError(f"{name}: 空の配列 (shape={a.shape})")
    if a.sum() == 0:
        raise ValueError(f"{name}: 前景 voxel が 0(退化入力)")
    return a


def build_cavity_shape(n=24):
    """中実キューブ + 既知の内部空洞(2×2×2)を持つ2値ボクセル。真値マスクも返す。"""
    vol = np.zeros((n, n, n), np.float32)
    vol[6:18, 6:18, 6:18] = 1.0                 # 本体 = 12^3 の中実キューブ
    cavity = np.zeros((n, n, n), bool)
    cavity[11:13, 11:13, 11:13] = True          # 内部の 2×2×2 空洞(既知)
    vol[cavity] = 0.0
    solid = np.zeros((n, n, n), bool)
    solid[6:18, 6:18, 6:18] = True              # 空洞を埋めた「真の中実本体」= GT
    return vol, cavity, solid


def build_spike_shape(n=24):
    """中実キューブ + 既知の細いトゲ(3 voxel)を持つ2値ボクセル。真値マスクも返す。"""
    vol = np.zeros((n, n, n), np.float32)
    vol[6:18, 6:18, 6:18] = 1.0
    spike = [(18, 12, 12), (19, 12, 12), (20, 12, 12)]   # +x 面から出る 1 voxel 太のトゲ
    for c in spike:
        vol[c] = 1.0
    solid = np.zeros((n, n, n), bool)
    solid[6:18, 6:18, 6:18] = True              # トゲを除いた「真の本体」= GT
    return vol, spike, solid


def _binarize(vol, thr=0.5):
    return np.asarray(vol) >= thr


def main():
    r = 1                                        # cube SE 半径(3×3×3)
    n = 24

    # ── 1) closing で内部空洞を埋める(dilate → erode を鎖状に) ──────────────
    v_cav, cavity, solid = build_cavity_shape(n)
    _validate_volume(v_cav, "cavity_shape")

    dilated = m.morph_dilate3d(v_cav, r)         # 素の dilate = beat-the-null の baseline
    closed = m.morph_erode3d(dilated, r)         # closing = dilate → erode
    if dilated.shape != v_cav.shape or closed.shape != v_cav.shape:
        raise ValueError(f"op が形状を変えた: in={v_cav.shape} dil={dilated.shape} clo={closed.shape}")

    b_closed = _binarize(closed)
    b_dilated = _binarize(dilated)

    holes_closing = int((~b_closed[cavity]).sum())     # closing 後に残る空洞 voxel 数
    holes_dilate = int((~b_dilated[cavity]).sum())     # 素の dilate 後に残る空洞 voxel 数
    err_closing = int((b_closed ^ solid).sum())        # closing と真の中実本体の対称差
    err_dilate = int((b_dilated ^ solid).sum())        # 素の dilate と真の中実本体の対称差

    print("[closing] 内部空洞を埋める / 本体を保存する")
    print(f"  本体 voxel(真値)          : {int(solid.sum())}")
    print(f"  内部空洞 voxel(真値)      : {int(cavity.sum())}")
    print(f"  closing 後の残存空洞        : {holes_closing}   (0 なら完全に埋まった)")
    print(f"  closing の形状誤差(対称差) : {err_closing}   (0 なら本体を完全保存)")
    print(f"  [null] 素の dilate の残存空洞: {holes_dilate}   (dilate でも空洞は埋まる)")
    print(f"  [null] 素の dilate の形状誤差: {err_dilate}   (本体が膨張=太る)")

    # ── 2) opening で細いトゲを除く(erode → dilate を鎖状に) ────────────────
    v_spk, spike, solid2 = build_spike_shape(n)
    _validate_volume(v_spk, "spike_shape")

    eroded = m.morph_erode3d(v_spk, r)           # 素の erode = beat-the-null の baseline
    opened = m.morph_dilate3d(eroded, r)         # opening = erode → dilate
    b_opened = _binarize(opened)
    b_eroded = _binarize(eroded)

    spike_after_opening = int(sum(bool(b_opened[c]) for c in spike))
    spike_after_erode = int(sum(bool(b_eroded[c]) for c in spike))
    err_opening = int((b_opened ^ solid2).sum())       # opening と真の本体の対称差
    err_erode = int((b_eroded ^ solid2).sum())         # 素の erode と真の本体の対称差

    print("[opening] 細い突起を除く / 本体を保存する")
    print(f"  トゲ voxel(真値)          : {len(spike)}")
    print(f"  opening 後の残存トゲ        : {spike_after_opening}   (0 なら完全に除去)")
    print(f"  opening の形状誤差(対称差) : {err_opening}   (0 なら本体を完全保存)")
    print(f"  [null] 素の erode の残存トゲ : {spike_after_erode}   (erode でもトゲは消える)")
    print(f"  [null] 素の erode の形状誤差 : {err_erode}   (本体が収縮=痩せる)")

    # ── 3) morph_gradient3d で表面の殻を取り出す ─────────────────────────────
    grad = m.morph_gradient3d(closed, r)         # dilate(closed) − erode(closed) = 境界殻
    shell_count = int((grad > 0.5).sum())
    interior_max = float(grad[8:16, 8:16, 8:16].max())   # 深部内側は空洞(勾配0)のはず
    surface_val = float(grad[6, 12, 12])                 # 本体表面の voxel(勾配>0)のはず

    print("[gradient] 表面の殻だけを取り出す")
    print(f"  殻 voxel 数                 : {shell_count}   (>0)")
    print(f"  深部内側の最大勾配          : {interior_max:.2f}   (~0 なら中身は空洞)")
    print(f"  表面 voxel の勾配           : {surface_val:.2f}   (>0 なら境界に乗る)")

    # ── 4) morph_tophat3d で細い明構造(トゲ)を抽出 ─────────────────────────
    tophat = m.morph_tophat3d(v_spk, r)          # vol − opening = SE より細い明構造
    b_tophat = tophat > 0.5
    tophat_count = int(b_tophat.sum())
    tophat_on_spike = int(sum(bool(b_tophat[c]) for c in spike))
    tophat_body = float(tophat[12, 12, 12])      # 本体中心はトゲでない → ~0

    print("[top-hat] SE より細い明構造(=トゲ)を抽出")
    print(f"  抽出された voxel 数         : {tophat_count}   (トゲ voxel 数 {len(spike)} と一致すべき)")
    print(f"  うちトゲ位置に乗った数      : {tophat_on_spike}")
    print(f"  本体中心の top-hat 応答     : {tophat_body:.2f}   (~0 なら本体を拾っていない)")

    # ── GT アサーション(真値との照合 + beat-the-null) ──────────────────────
    # closing: 空洞は完全に埋まり、本体形状は完全保存
    assert holes_closing == 0, f"closing が空洞を埋めていない: 残存 {holes_closing}"
    assert err_closing == 0, f"closing が本体形状を保存していない: 対称差 {err_closing}"
    # beat-the-null: 素の dilate も空洞は埋めるが本体が膨張し、closing と判別的に区別できる
    assert holes_dilate == 0, "前提が崩れた: 素の dilate でも空洞は埋まるはず"
    assert err_dilate > err_closing, \
        f"beat-null 失敗: dilate の形状誤差 {err_dilate} が closing {err_closing} を上回らない"
    assert err_dilate >= 500, f"素の dilate の膨張が想定より小さい: {err_dilate}"

    # opening: トゲは完全に除去され、本体形状は完全保存
    assert spike_after_opening == 0, f"opening がトゲを除去していない: 残存 {spike_after_opening}"
    assert err_opening == 0, f"opening が本体形状を保存していない: 対称差 {err_opening}"
    # beat-the-null: 素の erode もトゲは消すが本体が収縮し、opening と判別的に区別できる
    assert spike_after_erode == 0, "前提が崩れた: 素の erode でもトゲは消えるはず"
    assert err_erode > err_opening, \
        f"beat-null 失敗: erode の形状誤差 {err_erode} が opening {err_opening} を上回らない"

    # gradient: 境界に乗り、深部内側は空洞(勾配0)
    assert shell_count > 0, "gradient が殻を出していない"
    assert interior_max < 0.5, f"gradient の深部内側が空洞でない: max {interior_max:.2f}"
    assert surface_val > 0.5, f"gradient が表面に乗っていない: {surface_val:.2f}"

    # top-hat: 既知のトゲ(3 voxel)だけを抽出し、本体は拾わない
    assert tophat_count == len(spike), \
        f"top-hat の抽出数がトゲ voxel 数と不一致: {tophat_count} vs {len(spike)}"
    assert tophat_on_spike == len(spike), \
        f"top-hat がトゲ位置に乗っていない: {tophat_on_spike}/{len(spike)}"
    assert tophat_body < 0.5, f"top-hat が本体を拾っている: {tophat_body:.2f}"

    print(
        "PASS: closing で空洞 "
        f"{int(cavity.sum())}→0 かつ本体対称差 0(素の dilate は {err_dilate}=膨張で判別可), "
        f"opening でトゲ {len(spike)}→0 かつ本体対称差 0(素の erode は {err_erode}=収縮), "
        f"gradient の殻 {shell_count} voxel は境界に乗り内部は空洞, "
        f"top-hat は既知のトゲ {len(spike)} voxel だけを抽出"
    )


if __name__ == "__main__":
    main()
