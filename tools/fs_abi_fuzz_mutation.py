"""**ファザーそのものを検査する**(変異解析)。

`tools/fs_abi_fuzz.py` は 60,000 ケースで「食い違い 0」と言い続けている。
探針を 2 度強化してもゼロなので、**そろそろ「一致している」ではなく「検出できて
いない」を疑う番**([[feedback_zero_findings_may_mean_never_executed]])。

やり方: **既知の欠陥を Python 側へ故意に注入し、ファザーが何ケース目で捕まえるか**を
測る。捕まらない変異があれば、それは**ファザーが構造的に見えない座標**。

注入する変異は、実際に起きた壊れ方(と、その近傍):
  m1 連結性を 4 連結へ戻す        —— 2026-09-14 に実在した欠陥
  m2 しきい値の上端を開区間にする  —— 契約は閉区間
  m3 しきい値の下端を開区間にする
  m4 gauss の端を BORDER_REFLECT_101 へ —— 2026-09-14 に実在した欠陥
  m5 重心を 0.5 画素ずらす        —— 画素中心の規約違反
  m6 select_shape を半開区間にする
  m7 物体の並びを逆順にする        —— 契約は最初の run の (row,col) 昇順
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi

ROOT = Path(r"C:\dev\projects\imgevolve")
sys.path.insert(0, str(ROOT))
import fslib  # noqa: E402

spec = importlib.util.spec_from_file_location("fz", str(ROOT / "tools" / "fs_abi_fuzz.py"))
fz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fz)
lib = fz.load_rust()

ORIG = {k: dict(v) for k, v in fslib._REGISTRY.items()}
_orig_threshold = fslib.threshold
_orig_select = fslib.select_shape


def restore():
    for k, v in ORIG.items():
        fslib._REGISTRY[k] = dict(v)
    fslib.threshold = _orig_threshold
    fslib.select_shape = _orig_select


# --- 変異 ------------------------------------------------------------------
def m1_four_connected():
    """★この変異は 2 度書き直している。失敗の記録ごと残す。

    1 度目: `ndi.label(reg._mask)` で 4 連結を作り `ObjectSet` を素朴に組んだ ——
      **`ObjectSet` の作り方が不正で `measure_all` が `IndexError`**。ファザーは
      「15 ケース目で検出」と報告したが、見ていたのは欠陥ではなく**私のバグ**。
    2 度目: `cv2.connectedComponentsWithStats(mask, 4, CV_32S)` と**位置引数**で
      書いた —— cv2 5.0.0 では位置引数が connectivity として解釈されず、
      **4 連結になっていなかった**(5,000 ケースで検出ゼロの正体)。ここから
      `fslib` 本体も同じ書き方で「既定の 8 に頼っていた」ことが分かった。
    → 変異が殺されないときは、**まず注入が効いているかを確かめる**。
    """
    import cv2

    def bad(reg):
        k, lbl, stats, cents = cv2.connectedComponentsWithStats(
            reg._mask.astype(np.uint8), connectivity=4, ltype=cv2.CV_32S)
        return fslib.ObjectSet(lbl, np.arange(1, k, dtype=np.int32),
                               {"_cc_stats": stats, "_cc_centroids": cents})
    for be in fslib._REGISTRY["connection"]:
        fslib._REGISTRY["connection"][be] = bad


def m2_open_upper():
    def bad(img, lo, hi):
        a = img.pixels
        return fslib.Region((a >= img.absolute(lo)) & (a < img.absolute(hi)))
    for be in fslib._REGISTRY["threshold"]:
        fslib._REGISTRY["threshold"][be] = bad


def m3_open_lower():
    def bad(img, lo, hi):
        a = img.pixels
        return fslib.Region((a > img.absolute(lo)) & (a <= img.absolute(hi)))
    for be in fslib._REGISTRY["threshold"]:
        fslib._REGISTRY["threshold"][be] = bad


def m4_reflect101():
    def bad(img, sigma):
        return img.with_pixels(
            ndi.gaussian_filter(img.pixels.astype(np.float32), float(sigma), mode="mirror"))
    fslib._REGISTRY["gauss"]["numpy"] = bad


def m5_centroid_shift():
    base = ORIG["measure_all"]["numpy"]

    def bad(objs):
        a, r, c = base(objs)
        return a, np.asarray(r) + 0.5, c
    for be in fslib._REGISTRY["measure_all"]:
        fslib._REGISTRY["measure_all"][be] = bad


def m6_half_open_select():
    def bad(objs, feature, vmin, vmax):
        ar, ro, co = fslib.measure_all(objs)
        vals = {"area": ar, "row": ro, "column": co}.get(feature)
        if vals is None:
            raise fslib.FsTypeError("unknown feature %r" % feature)
        if not (float(vmin) <= float(vmax)):
            raise fslib.FsTypeError("inverted")
        return objs.select((np.asarray(vals) >= float(vmin)) & (np.asarray(vals) < float(vmax)))
    fslib.select_shape = bad


def m7_reverse_order():
    """★これも 1 度書き直している(m1 と同型の失敗)。

    最初は `o.ids = o.ids[::-1]` と代入していたが、`ObjectSet` は **frozen
    dataclass** なので `FrozenInstanceError`。ファザーが「1 ケース目で検出」と
    言っていたのは**並びの違いではなく注入のバグ**だった。
    正しくは**新しい ObjectSet を作る**。
    """
    base = ORIG["connection"]["numpy"]

    def bad(reg):
        o = base(reg)
        return fslib.ObjectSet(o.labels, o.ids[::-1].copy(), dict(o.feats))
    for be in fslib._REGISTRY["connection"]:
        fslib._REGISTRY["connection"][be] = bad


MUTANTS = [
    ("m1 連結性を 4 連結に(実在した欠陥)", m1_four_connected),
    ("m2 しきい値の上端を開区間に", m2_open_upper),
    ("m3 しきい値の下端を開区間に", m3_open_lower),
    ("m4 gauss の端を REFLECT_101 に(実在した欠陥)", m4_reflect101),
    ("m5 重心を 0.5 画素ずらす", m5_centroid_shift),
    ("m6 select_shape を半開区間に", m6_half_open_select),
    ("m7 物体の並びを逆順に", m7_reverse_order),
]

BUDGET = 3000

print("既知の欠陥を注入して、ファザーが何ケース目で捕まえるかを測る")
print("(捕まえられない変異 = ファザーが構造的に見えない座標)")
print("=" * 72)
killed = 0
for label, apply in MUTANTS:
    restore()
    try:
        apply()
    except Exception as e:
        print("%-44s 注入に失敗 %s" % (label, e))
        continue
    rng = np.random.default_rng(0)
    at = None
    for i in range(BUDGET):
        c = fz.gen_case(rng)
        try:
            why = fz.compare(fz.observe_rust(lib, c, {"gauss"}), fz.observe_python(c, {"gauss"}))
        except Exception as e:
            why = "例外 %s" % type(e).__name__
        if why:
            at = (i + 1, why)
            break
    if at:
        killed += 1
        print("%-44s ★%4d ケース目で検出  (%s)" % (label, at[0], at[1][:46]))
    else:
        print("%-44s ✗ %d ケースで**検出できず**" % (label, BUDGET))
restore()
print("=" * 72)
print("殺せた変異 %d / %d" % (killed, len(MUTANTS)))
if killed < len(MUTANTS):
    print("★ 検出できない変異がある = そこはファザーの盲点。文法か観測を足すこと。")
else:
    print("全部殺せた。**だから「食い違い 0」は意味を持つ** —— 少なくとも")
    print("これらの壊れ方はもう素通りしない。")
