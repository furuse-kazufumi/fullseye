# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 見た目が同じ異物をハイパースペクトル(NIR/SWIR)で選別する —— 実画像 2 つ + 材料表から作る合成で壊れ方を数える。

【問い】食品のライン(豚バラ・ナッツ)に混じる樹脂片・紙・木・金属や、リサイクルの樹脂の破片は、色が似ていると
RGB のカメラでは見分けられない。選別機は近赤外(0.9〜2.5 µm)の分光で分ける —— C-H の倍音(1.2 / 1.7 µm)と
結合音(2.3 µm)、O-H(1.45 / 1.94 µm)の吸収帯が材料ごとに違うから。**主役は公開の実画像**で、Fullseye の op
(`read_envi`・`spec_continuum_removal`・`spec_angle_mapper`・`spec_band_selection_fisher`)で分類し、データに付いた
正解ラベルを真値に混同行列と ROC を出す。合成は「どの帯域が効くか・黒い樹脂・水・ランプ・光子」の壊れ方を
既知の量で振る補助。

章(実データの数字は 2026-10-15 の手元の実行。CI はデータを持たないので記録値を印字して実データの章を飛ばす):
  0a. **実画像 1: 樹脂の破片 6 種**(RODARE 3390、400〜2500 nm の分光カメラ、46 x 92 px、1100〜2400 nm): 左半分で学び右半分で採点。
      連続体除去 + SAM でクラス平均の再現率 0.816(生の反射率の SAM は 0.439 —— 暗い破片は足し算のベースラインに
      負ける)。★外の真値: 別の撮影の基準試料をライブラリにすると PP / PET / PE を 0.878、**この PoC の材料表の
      物理モデルだけ**をライブラリにすると 0.628(当て推量 0.333)—— 谷の位置は合うが深さと幅は推定。黒い樹脂は
      反射率 0.03、C-H の谷の深さが他の 1/6。★ヘッダの不整合を fail-closed の読み手が見つけた(fwhm が切り出す前の
      450 個のまま)—— 波長の札が正しいことは PE / PP の谷の位置で確かめ、fwhm だけを直した写しを読む。
  0b. **実画像 2: 豚バラの上の異物 10 種**(Zenodo 17242553、900〜1700 nm の InGaAs ラインスキャン分光カメラ、0.47 mm/px): 撮影ごとに分け、2 枚で学び
      2 枚(65 万画素、うち異物 1.2 万)で採点。SAM は AUC 0.92 だが誤警報 10 %、全 184 帯の LDA で検出 0.92・誤警報
      1.1 %。★Fisher で選んだ 6 帯の LDA は誤警報 2.1 %、3 帯では 23 % —— **合成では 3 帯で足りたのに、実データ
      では足りない**(10 種の異物と肉・脂の個体差は合成の模型より広い)。波長の札は記録の説明から再構成し、PEHD・脂・
      肉の谷で検算した(15〜35 nm 短い側にずれている可能性がある)。
  1. **物理の門**: Kubelka–Munk の極限、InGaAs の端、水の吸収(Kou 1993 と 10 %)、樹脂の谷の位置(USGS の実測と
     5 nm)、撮像の線形性と分散 = 平均 + 読出し²。
  2〜6. **合成**(仁と同じ色の殻・木片・樹脂片のトレイ、真値つき): RGB の AUC 0.48 対 ハイパースペクトル 1.0000、
     Fisher の 3 帯で全帯と同じ、濡れ・白板の後のランプのずれ・光子・影、黒い樹脂(カーボンブラック 1 wt % で PP と PE
     の角が 1 画素の雑音を下回る)、白い樹脂の破片 4 種。★**逆犯罪**: 場面とライブラリが同じ模型なので合成の精度は
     上限 —— 実データの 0a / 0b がその差を示す(合成 1.000 に対して実データ 0.82〜0.92)。

【パラメータの出典の表】(2026-10-15 に一次情報で照合。U = USGS の実測、L = 論文の実測、D = データシート、
 E = 推定 = 模型):
  樹脂の谷の位置   PE 1215/1395/1731/1765/2310/2350/2387 nm(U: splib05a GDS351/391/393/402)、PET 1130/1662/1715/
                   1907/2131/2258/2334(U: GDS379/380/383)、PP 1195/1395(L: Rani 2019)・1709/1727(L: Vázquez-Guardado
                   2015、未再確認)、PS 1145/1682(L: Rani 2019)、PS 2170/2310(E)
  帯の強さと幅     PE は USGS の薄膜の谷の深さからの逆算の桁(1730 nm 0.4〜1、2310 nm 1.5〜1.7 /mm)、ほかは E
  水               Segelstein 1981(材料表、k だけ)—— Kou 1993 と 10 % 以内
  アーモンドの組成 脂質 49.9 / タンパク質 21.2 / 炭水化物 21.6 / 水 4.4 %(USDA FDC 170567)
  殻の組成         リグニン 29.5 %(L: Li 2018)、セルロース + ヘミセルロース 67 %(PoC は 60 %)、水 8 %(E)
  カーボンブラック MAC 7.5 m²/g @550 nm、λ⁻¹(L: Bond & Bergstrom 2006、大気の粒子の値を樹脂に流用)、樹脂の
                   添加量 0.5〜3 wt %(L: Becker 2017)
  Kubelka–Munk     拡散照明・等方散乱で成立(L: Myrick 2011)、K ≈ 2α(教科書値、E)、Saunderson の r_i = 0.6
                   (n 1.5 の Fresnel の半球積分 0.596 に合う)
  InGaAs           標準 0.9〜1.7 µm で QE 80 % 超、拡張品は 2.6 µm までピーク約 70 %(D: 市販の InGaAs 素子のデータシート)
  ライン           市販の InGaAs ラインスキャン分光カメラ: 224 帯・527〜670 fps・SNR 1000:1・フルウェル 1.44 Me⁻(D)、
                   ベルト 2.8〜4.5 m/s(業界誌)
  照明の照度・読出し雑音  E(一次情報なし)

EXTEND: 自社の分光カメラの画像は `SP.read_envi` で読み、正解のマスク(画素ごとのクラス番号)を用意すれば
`chapter_real_polymers` と同じ経路(連続体除去 → クラス平均の SAM / Fisher の帯域選択 → LDA)がそのまま回る。
学びと採点は**撮影を分けて**(同じ破片の隣の画素で当てない)。帯の表は ``materials.material_nir_absorption(..., bands=...)``
で実測に合わせた帯に差し替えられる。カメラの QE と光源はデータシートの曲線を ``hyperspectral_band_weights`` に渡す。

【実データ】(repo に入れない。``FULLSEYE_HSI_DOWNLOAD=1`` で ``FULLSEYE_DATA_DIR``(既定 ``~/.cache/fullseye``)へ取得)
  * E. Arbash, A. de Lima Ribeiro, A. Rizaldy, M. Fuchs, P. Ghamisi, P. Scheunders, R. Gloaguen, "Polymers Hyperspectral
    Imaging", RODARE (HZDR), doi:10.14278/rodare.3390 —— **CC BY 4.0**(記録のページで確認)。改変: 試験ヘッダの fwhm を
    360 帯に切り詰めた写し、1100〜2400 nm の切り出し、連続体除去。542 MB、SHA-256 で検証。
  * V. G. Ghimpeteanu, H. Rajani, J. Quintana, R. Garcia, "A Hyperspectral Image Dataset for Identifying Foreign Objects
    on Pork Belly", Zenodo, doi:10.5281/zenodo.17242553 —— **CC BY 4.0**(記録のページで確認)。関連論文 arXiv:2503.16086
    (論文本文は CC BY-NC-SA なので図は使わない)。改変: 18.9 GB の zip から val の範囲(1.08 GB)だけを HTTP の Range で
    取り、各メンバーを CRC32 で検証し、20x16 のパッチを元の位置へ並べ直した。

【出典】A. Vázquez-Guardado ら, Appl. Opt. 54, 7396 (2015) / M. Rani ら, Materials 12, 2740 (2019) / R. N. Clark ら,
USGS OFR 03-395 (2003) と R. F. Kokaly ら, USGS DS 1035 (2017)(public domain)/ P. Kubelka, J. Opt. Soc. Am. 38, 448
(1948)/ M. L. Myrick ら, Appl. Spectrosc. Rev. 46, 140 (2011)/ D. J. Segelstein (1981) と L. Kou ら, Appl. Opt. 32,
3531 (1993)/ T. C. Bond, R. W. Bergstrom, Aerosol Sci. Technol. 40, 27 (2006)/ M. Becker ら, Polymers 9, 435 (2017)。
【学習した数】実データ: クラス平均と LDA(学びの撮影だけから)。合成: 排出の閾値 1 つ。【較正】0。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import materials as MT  # noqa: E402
import specops as SP  # noqa: E402
import spectralrad as SR  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

WL = np.linspace(900.0, 2500.0, 321)               # 反射率の波長格子(5 nm)
MM_PX = 0.5                                        # 1 画素 = 0.5 mm(ベルト面)
H, W = (120, 180) if REDUCED else (240, 360)
SS = 3                                             # 被覆率(境界の混合画素)を作る細分格子
BELT_SPEED_M_S = 2.0
EXPOSURE_S = MM_PX * 1e-3 / BELT_SPEED_M_S         # ラインスキャンの露光 = 画素の長さ / 速度
READ_E = 80.0                                      # 高速 InGaAs の読出し雑音(典型の桁)
CHAIN = dict(band_fwhm_nm=10.0, source_temperature_k=3000.0, irradiance_w_m2=3000.0, f_number=2.0,
             pixel_um=15.0, optics_material="SILICA", optics_thickness_mm=None)
CAMS = {"std": dict(qe_cutoff_nm=1700.0, band_centers_nm=tuple(np.arange(950.0, 1651.0, 10.0))),
        "ext": dict(qe_cutoff_nm=2500.0, band_centers_nm=tuple(np.arange(1000.0, 2451.0, 10.0)))}
CAM_LABEL = {"std": "標準 InGaAs(0.95〜1.65 µm、71 帯)", "ext": "拡張 InGaAs(1.0〜2.45 µm、146 帯)"}

#: 食品のトレイのクラス。0 = ベルト。
FOOD = ["ベルト", "仁", "殻", "木片", "PE 片", "PP 片", "黒い樹脂"]
FOREIGN = [2, 3, 4, 5, 6]
SAME_COLOUR = [2, 3, 4, 5]
#: 見た目の色(線形 RGB の反射率)。★**同じ色にしたのは設計**(この PoC の問いそのもの: 色を合わせた異物)。
#: 皮つきアーモンドの茶色に、殻・木片・茶色に着色した樹脂片を ±3 % で合わせた。黒い樹脂だけは黒い。
RGB_ALBEDO = {1: (0.30, 0.12, 0.050), 2: (0.31, 0.125, 0.050), 3: (0.29, 0.12, 0.052), 4: (0.30, 0.118, 0.048),
              5: (0.305, 0.12, 0.051), 6: (0.035, 0.035, 0.038)}
BELT_RGB = (0.23, 0.25, 0.28)
BELT_R = 0.22                                       # ベルトの NIR 反射率(灰色、平坦と仮定)

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _at(c, x):
    return float(np.interp(x, c[:, 0], c[:, 1]))


# --------------------------------------------------------------------------- #
# 0. 実データ(主役): 公開のハイパースペクトル画像 2 つ(CC BY 4.0)                   #
# --------------------------------------------------------------------------- #
#: 実データの置き場(repo には入れない)。MaleCNS の PoC と同じ ``FULLSEYE_DATA_DIR``(既定 ``~/.cache/fullseye``)。
#: 取得は ``FULLSEYE_HSI_DOWNLOAD=1`` のときだけ(RODARE 542 MB、Zenodo は 18.9 GB の zip から検証用の範囲 約 1.1 GB を
#: HTTP の Range で取る)。キャッシュも許可も無いとき(CI)は、下の記録値を印字して実データの章を飛ばす(合格にも失格にも数えない)。
POLYMERS_URL = "https://rodare.hzdr.de/api/files/f751b71e-ce94-417e-8088-62806fbdb7c7/Polymers%201.0.zip"
POLYMERS_SHA256 = "c56221cf2e2aad9d84c7e2aa99e6473b0eb5d42dfd691897ed0f29597d385db0"
PORK_URL = "https://zenodo.org/api/records/17242553/files/training_dataset_20x16.zip/content"
PORK_ZIP_SIZE = 18877188241
#: 豚バラのクラス(Zenodo の記録の表、ID 0〜12)。0〜9 が異物、10〜12 が陰性(肉・脂・ベルト)。
PORK_CLASSES = ["PA-PP", "PU", "金属", "PEHD", "テフロン", "ニトリル", "木", "紙", "段ボール", "白ベルト片", "肉", "脂", "ベルト"]
PORK_NEG = (10, 11, 12)
#: 樹脂のクラス(RODARE の記録の Data Classes in Masks、1〜6)。0 = ラベル無し。
POLY_CLASSES = ["(無し)", "PP", "黒い樹脂", "PVC", "PET", "ABS", "PE"]
#: 記録値(2026-10-15 の手元の実行)。CI では実データを持たないので、これを印字して章を飛ばす。
RECORDED: dict[str, float] = {
    "poly_sam_bacc": 0.816, "poly_sam_raw_bacc": 0.439, "poly_acc3_ref": 0.878, "poly_acc3_phys": 0.628,
    "poly_black_depth": 0.062, "pork_auc": 0.921, "pork_detect": 0.821, "pork_false_alarm": 0.101,
    "pork_lda_det": 0.921, "pork_lda_fa": 0.0111,
}


def _data_dir() -> str:
    d = os.path.join(os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye"),
                     "poc_hyperspectral_foreign_matter")
    os.makedirs(d, exist_ok=True)
    return d


def _may_download() -> bool:
    return os.environ.get("FULLSEYE_HSI_DOWNLOAD", "").strip() in ("1", "yes", "true")


def _download(url, path, byte_range=None):
    import urllib.request
    req = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % byte_range} if byte_range else {})
    tmp = path + ".part"
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 22)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, path)


def _download_parallel(url, path, byte_range, parts=16):
    """Range を *parts* 本に分けて並列に取る(Zenodo は 1 本あたり 0.1 MB/s 前後に絞られる、2026-10-15 に実測)。"""
    import concurrent.futures
    import urllib.request
    lo, hi = byte_range
    total = hi - lo + 1
    step = total // parts + 1
    tmp = path + ".part"
    with open(tmp, "wb") as f:
        f.truncate(total)

    def one(i):
        a = lo + i * step
        b = min(hi, a + step - 1)
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (a, b)})
                with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "r+b") as f:
                    f.seek(a - lo)
                    got = 0
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                if got != b - a + 1:
                    raise IOError("short read %d of %d" % (got, b - a + 1))
                return got
            except Exception:                                          # noqa: BLE001
                if attempt == 4:
                    raise
    with concurrent.futures.ThreadPoolExecutor(parts) as ex:
        list(ex.map(one, range(parts)))
    os.replace(tmp, path)


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_polymers():
    """RODARE 3390 の Polymers を取って展開し、試験の場面のヘッダを直す。無ければ None。

    ★改変は 1 つだけ: 試験の場面のヘッダは 360 帯なのに ``fwhm`` が切り出す前の 450 個のまま
    残っていて、Fullseye の ``read_envi`` は(正しく)fail-closed で拒否する。波長の並びを 450 帯の元の表と
    突き合わせ、同じ位置の 360 個の fwhm だけを残したヘッダをキャッシュに書く(データは触らない)。
    波長の札そのものが正しいことは、樹脂の吸収の谷の位置(PE 1731・PP 1709 nm)で確かめた —— 帯の名前に残る
    「ROI Resize (378.19 nm …)」の側を波長と読むと、PE の谷が 1694 nm にずれる。
    """
    import zipfile
    d = _data_dir()
    root = os.path.join(d, "Polymers 1.0")
    zpath = os.path.join(d, "polymers_1.0.zip")
    if not os.path.isdir(root):
        if not os.path.exists(zpath):
            if not _may_download():
                return None
            print("   取得: RODARE 3390 Polymers(542 MB、CC BY 4.0)→ %s" % zpath)
            _download(POLYMERS_URL, zpath)
        if _sha256(zpath) != POLYMERS_SHA256:
            raise ValueError("Polymers zip の SHA-256 が記録と違う(壊れたか差し替えられた): %s" % zpath)
        with zipfile.ZipFile(zpath) as z:
            for i in z.infolist():
                n = i.filename
                if n.startswith("Polymers 1.0/") and ".ipynb" not in n and not n.endswith(".DS_Store") and ".." not in n:
                    z.extract(i, d)
    import glob
    hdrs = [h for h in glob.glob(os.path.join(root, "Test", "*_crop.hdr"))]
    fulls = glob.glob(os.path.join(root, "Training", "HSI_im2", "*_refl.*.hdr"))
    if len(hdrs) != 1 or len(fulls) != 1:
        raise ValueError("Polymers の試験ヘッダか 450 帯の表が 1 つに決まらない: %s / %s" % (hdrs, fulls))
    test_hdr, full_hdr = hdrs[0], fulls[0]
    fixed = os.path.join(root, "Test", "test_scene_fixed.hdr")
    if not os.path.exists(fixed):
        import re as _re
        t = io_read(test_hdr)
        full = io_read(full_hdr)
        wl_t = [float(x) for x in _re.search(r"\nwavelength\s*=\s*\{([^}]*)\}", t).group(1).split(",")]
        wl_f = [float(x) for x in _re.search(r"\nwavelength\s*=\s*\{([^}]*)\}", full).group(1).split(",")]
        fw = [x.strip() for x in _re.search(r"\nfwhm\s*=\s*\{([^}]*)\}", t).group(1).split(",") if x.strip()]
        i0 = int(np.argmin(np.abs(np.asarray(wl_f) - wl_t[0])))
        if len(fw) != len(wl_f) or not np.allclose(wl_f[i0:i0 + len(wl_t)], wl_t, atol=0.02):
            raise ValueError("Polymers の試験ヘッダの波長が 450 帯の表の連続した区間になっていない(直せない)")
        t = _re.sub(r"\nfwhm\s*=\s*\{[^}]*\}", "\nfwhm = {" + ", ".join(fw[i0:i0 + len(wl_t)]) + "}", t)
        t = t.replace("\ndescription = {", "\ndescription = {fullseye: fwhm subset to the 360 bands; ", 1)
        with open(fixed, "w", encoding="utf-8") as f:
            f.write(t)
        import shutil
        shutil.copyfile(test_hdr[:-4] + ".dat", os.path.join(root, "Test", "test_scene_fixed.dat"))
    return root


def io_read(p):
    with open(p, encoding="utf-8", errors="replace") as f:
        return f.read()


def _zip_central_directory(url, size):
    """zip64 の中央ディレクトリを Range で取り、{名前: (圧縮後, 元, 局所ヘッダの位置, CRC, 方式)} を返す。"""
    import struct
    import urllib.request
    tail = urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (size - 200000, size - 1)}),
                                  timeout=120).read()
    i = tail.rfind(b"PK\x06\x06")
    if i < 0:
        raise ValueError("zip64 の終端レコードが無い")
    n_ent, cd_size, cd_off = struct.unpack("<QQQ", tail[i + 32:i + 56])
    cd = urllib.request.urlopen(urllib.request.Request(url, headers={"Range": "bytes=%d-%d" % (cd_off, cd_off + cd_size - 1)}),
                                timeout=600).read()
    out, p = {}, 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        meth, = struct.unpack("<H", cd[p + 10:p + 12])
        crc, csz, usz = struct.unpack("<III", cd[p + 16:p + 28])
        n, m, k = struct.unpack("<HHH", cd[p + 28:p + 34])
        lho, = struct.unpack("<I", cd[p + 42:p + 46])
        name = cd[p + 46:p + 46 + n].decode("utf-8")
        ex = cd[p + 46 + n:p + 46 + n + m]
        q = 0
        while q + 4 <= len(ex):
            hid, hs = struct.unpack("<HH", ex[q:q + 4])
            if hid == 1:
                vals = [struct.unpack("<Q", ex[q + 4 + j:q + 12 + j])[0] for j in range(0, hs, 8)]
                it = iter(vals)
                if usz == 0xFFFFFFFF:
                    usz = next(it)
                if csz == 0xFFFFFFFF:
                    csz = next(it)
                if lho == 0xFFFFFFFF:
                    lho = next(it)
            q += 4 + hs
        out[name] = (csz, usz, lho, crc, meth)
        p += 46 + n + m + k
    if len(out) != n_ent:
        raise ValueError("中央ディレクトリの数が合わない: %d vs %d" % (len(out), n_ent))
    return out


def fetch_pork():
    """Zenodo 17242553 の検証用(val)のパッチ 4,617 枚を Range で取り、捕捉ごとに元の位置へ並べ直した npz にする。

    記録の説明は「20x16 のパッチ・50 % 重なり」だが、val のパッチの位置(ファイル名の行・列)は大半が 20 行・16 列
    おき(重ならない)で、端だけ 22 行・8 列にずれた物がある —— パッチ全体を元の位置に置き、重なりは後勝ち。
    各メンバーは中央ディレクトリの CRC32 で検証する(fail-closed)。
    """
    import struct
    import zlib
    d = _data_dir()
    npz = os.path.join(d, "pork_val_mosaics.npz")
    if os.path.exists(npz):
        return npz
    rng_bin = os.path.join(d, "pork_val_range.bin")
    meta = os.path.join(d, "pork_cd.json")
    if not os.path.exists(rng_bin):
        if not _may_download():
            return None
    import json as _json
    if os.path.exists(meta):
        cd = {k: tuple(v) for k, v in _json.load(open(meta, encoding="utf-8")).items()}
    else:
        if not _may_download():
            return None
        cd = _zip_central_directory(PORK_URL, PORK_ZIP_SIZE)
        cd = {k: v for k, v in cd.items() if "/val/" in k and not k.endswith("/")}
        with open(meta, "w", encoding="utf-8") as f:
            _json.dump(cd, f)
    lo = min(v[2] for v in cd.values())
    hi = min(PORK_ZIP_SIZE, max(v[2] + v[0] + 30 + 512 for v in cd.values()))
    if not os.path.exists(rng_bin):
        print("   取得: Zenodo 17242553 の val の範囲 %.2f GB(CC BY 4.0)→ %s" % ((hi - lo) / 1e9, rng_bin))
        _download_parallel(PORK_URL, rng_bin, (lo, hi - 1))
    from PIL import Image
    import io as _io
    raw = open(rng_bin, "rb")
    mos = {}
    for name, (csz, usz, lho, crc, meth) in sorted(cd.items()):
        if not name.endswith(".npy") or "/images/" not in name:
            continue
        stem = name.rsplit("/", 1)[1][:-4]
        cap, r0, c0 = stem.rsplit("_", 2)
        pair = {}
        for kind, nm in (("img", name), ("mask", name.replace("/images/", "/masks/")[:-4] + ".png")):
            cz, uz, off, cc, mt = cd[nm]
            raw.seek(off - lo)
            hdr = raw.read(30)
            if hdr[:4] != b"PK\x03\x04":
                raise ValueError("局所ヘッダが無い: %s" % nm)
            n, m = struct.unpack("<HH", hdr[26:30])
            raw.seek(off - lo + 30 + n + m)
            blob = raw.read(cz)
            data = zlib.decompress(blob, -15) if mt == 8 else blob
            if (zlib.crc32(data) & 0xFFFFFFFF) != cc or len(data) != uz:
                raise ValueError("CRC32 か長さが中央ディレクトリと合わない: %s" % nm)
            pair[kind] = data
        x = np.load(_io.BytesIO(pair["img"]), allow_pickle=False)
        msk = np.array(Image.open(_io.BytesIO(pair["mask"])))
        if x.shape[:2] != (20, 16) or msk.shape[:2] != (20, 16):
            raise ValueError("パッチの形が 20x16 でない: %s %s %s" % (name, x.shape, msk.shape))
        if msk.ndim == 3:
            cmap = np.array([[211, 244, 255], [250, 128, 114], [255, 212, 221], [76, 76, 76], [0, 255, 0], [0, 76, 116],
                             [119, 95, 236], [201, 0, 55], [168, 199, 157], [10, 117, 173], [223, 116, 255], [255, 255, 0],
                             [53, 136, 119]])
            dist = ((msk[..., None, :3].astype(int) - cmap[None, None]) ** 2).sum(-1)
            lab = np.where(dist.min(-1) == 0, dist.argmin(-1), -1)
        else:
            lab = msk.astype(int)
        mos.setdefault(cap, []).append((int(r0), int(c0), x.astype(np.float32), lab.astype(np.int16)))
    out = {}
    for cap, items in mos.items():
        H_ = max(r for r, _, _, _ in items) + 20
        W_ = max(c for _, c, _, _ in items) + 16
        cube = np.zeros((H_, W_, items[0][2].shape[-1]), np.float32)
        lab = np.full((H_, W_), -2, np.int16)                          # -2 = パッチの無い所
        for r, c, xx, ll in items:
            cube[r:r + 20, c:c + 16] = xx
            lab[r:r + 20, c:c + 16] = ll
        key = cap.split("_")[-2] if "_" in cap else cap
        out["cube_" + key] = cube
        out["lab_" + key] = lab
    np.savez(npz, **out)
    return npz


def chapter_real_polymers():
    print("\n0a. 実データ: 樹脂の破片(RODARE 3390 Polymers、400〜2500 nm の分光カメラ、CC BY 4.0)")
    root = fetch_polymers()
    if root is None:
        print("   データが無い(FULLSEYE_HSI_DOWNLOAD=1 で取得)。記録値: " + ", ".join("%s %.3f" % kv for kv in RECORDED.items() if kv[0].startswith("poly")))
        return None
    cube, meta = SP.read_envi(os.path.join(root, "Test", "test_scene_fixed.hdr"))
    wl = np.asarray(SP._meta_wavelengths(meta), float)
    cube = cube / 65535.0                                        # reflectance scale factor = 65535(ヘッダ)
    from PIL import Image
    gt = np.array(Image.open(os.path.join(root, "Test", "Test_GT.png"))).astype(int)
    if gt.shape != cube.shape[:2]:
        raise ValueError("正解マスクの形が場面と違う")
    keep = (wl >= 1100.0) & (wl <= 2400.0)                       # 樹脂の C-H の帯の所(端の雑音の多い帯を除く)
    R, wlk = cube[..., keep], wl[keep]
    # ★実データの破片は暗い(反射率の中央値 0.07)ので、生の反射率の SAM は足し算のベースラインに負ける(下で数える)。
    #   連続体除去(`spec_continuum_removal`、上側の凸包で割る)の帯の深さ 1 − R/包絡 を特徴にする。
    C = 1.0 - SP.spec_continuum_removal(R, wlk) + 1e-6

    def depth_of(spec):
        return 1.0 - SP.spec_continuum_removal(np.asarray(spec, float)[None, None, :], wlk)[0, 0] + 1e-6
    # 空間で分ける: 左半分の画素でライブラリ(クラス平均)と帯域選択、右半分で採点(同じ破片の隣の画素で当てない)
    H_, W_ = gt.shape
    left = np.zeros_like(gt, bool)
    left[:, : W_ // 2] = True
    tr, te = (gt > 0) & left, (gt > 0) & ~left
    cls = list(range(1, 7))
    lib = np.stack([unit(unit(C[tr & (gt == c)]).mean(0)) for c in cls])
    ang = np.stack([SP.spec_angle_mapper(C, lib[k]) for k in range(6)], -1)
    pred = np.array(cls)[np.argmin(ang, -1)]
    conf = np.zeros((6, 6), int)
    np.add.at(conf, (gt[te] - 1, pred[te] - 1), 1)
    rec = conf.diagonal() / np.maximum(conf.sum(1), 1)
    NUMBERS.update({"poly_sam_bacc": float(rec.mean()), **{"poly_rec_%s" % POLY_CLASSES[c]: float(rec[c - 1]) for c in cls}})
    lib_raw = np.stack([unit(unit(R[tr & (gt == c)]).mean(0)) for c in cls])
    p_raw = np.array(cls)[np.argmin(np.stack([SP.spec_angle_mapper(R, lib_raw[k]) for k in range(6)], -1), -1)]
    raw_bacc = float(np.mean([(p_raw[te & (gt == c)] == c).mean() for c in cls]))
    NUMBERS["poly_sam_raw_bacc"] = raw_bacc
    print("   場面 %d x %d px、%d 帯(1100〜2400 nm を使う)、ラベル %d px(左半分で学び右半分で採点 %d px)"
          % (H_, W_, C.shape[-1], int((gt > 0).sum()), int(te.sum())))
    print("   SAM(左半分のクラス平均)の再現率: " + "、".join("%s %.3f" % (POLY_CLASSES[c], rec[c - 1]) for c in cls))
    # ROC: 1 クラス対その他、度合 = 他クラスの最小角 − 自クラスの角
    aucs = {}
    for k, c in enumerate(cls):
        s = np.delete(ang, k, -1).min(-1) - ang[..., k]
        _, _, aucs[c] = roc(s[te & (gt == c)], s[te & (gt != c) & (gt > 0)])
    NUMBERS.update({"poly_auc_%s" % POLY_CLASSES[c]: v for c, v in aucs.items()})
    print("   1 対その他の ROC の AUC: " + "、".join("%s %.3f" % (POLY_CLASSES[c], aucs[c]) for c in cls))
    gate("★実データ(樹脂の破片 6 種): 連続体除去 + SAM のクラス平均の再現率 %.3f(右半分 %d px、ライブラリは左半分)。生の反射率の SAM は %.3f"
         % (rec.mean(), int(te.sum()), raw_bacc), rec.mean() > 0.7 and rec.mean() > raw_bacc + 0.2,
         " / ".join("%s %.2f" % (POLY_CLASSES[c], rec[c - 1]) for c in cls))
    # Fisher の帯域選択 + LDA(左半分で選んで学び、右半分で採点)
    F = C
    sel = SP.spec_band_selection_fisher(F, np.where(tr, gt, -1), n_select=6)
    baccs = []
    for k in range(1, 7):
        b = sel["selected"][:k]
        model = lda_fit(F[tr][:, b], gt[tr])
        p = lda_predict(model, F[te][:, b][:, None, :])[:, 0]
        baccs.append(float(np.mean([(p[gt[te] == c] == c).mean() for c in cls])))
    NUMBERS.update({"poly_lda_k%d" % (k + 1): v for k, v in enumerate(baccs)})
    print("   Fisher で選んだ帯域 %s nm、1〜6 帯域の LDA の再現率 %s" % (", ".join("%.0f" % wlk[i] for i in sel["selected"]),
                                                                " / ".join("%.3f" % v for v in baccs)))
    # ★外の真値の検査 1: 別の撮影の基準試料(Training/PP・PE・PET の 11x11)をライブラリにして、試験の場面の PP / PET / PE を分ける
    ref = {}
    for c, f in ((1, "PP/PP_std1_VNIR_SWIR.hdr"), (4, "PET/PET_std1_VNIR_SWIR.hdr"), (6, "PE/PE_HD_std1_VNIR_SWIR.hdr")):
        rc, rm = SP.read_envi(os.path.join(root, "Training", f))
        rw = np.asarray(SP._meta_wavelengths(rm), float)
        s = rc.reshape(-1, rc.shape[-1]).mean(0)
        ref[c] = depth_of(np.interp(wlk, rw, s))
    m3 = te & np.isin(gt, (1, 4, 6))
    three = (1, 4, 6)

    def acc3(L):
        Lu = unit(np.stack([L[c] for c in three]))
        a = np.arccos(np.clip(unit(C[m3]) @ Lu.T, -1, 1))
        p = np.array(three)[a.argmin(-1)]
        return float(np.mean([(p[gt[m3] == c] == c).mean() for c in three])), p
    acc_ref, _ = acc3(ref)
    # ★外の真値の検査 2: この PoC の材料表の物理(吸収帯 + Kubelka–Munk)をライブラリにする
    phys = {c: depth_of(np.interp(wlk, WL, SR.spectral_reflectance_from_material(m, thickness_mm=None)[:, 1]))
            for c, m in ((1, "PP"), (4, "PET"), (6, "PE"))}
    acc_phys, pphys = acc3(phys)
    acc_scene, _ = acc3({c: lib[c - 1] for c in three})
    NUMBERS.update({"poly_acc3_ref": acc_ref, "poly_acc3_phys": acc_phys, "poly_acc3_scene": acc_scene})
    print("   PP / PET / PE の 3 種(右半分): 場面のクラス平均 %.3f、別撮影の基準試料 %.3f、材料表の物理モデル %.3f"
          % (acc_scene, acc_ref, acc_phys))
    gate("★別の撮影の基準試料をライブラリにしても、実データの PP / PET / PE を 3 種の平均再現率 %.3f で分ける" % acc_ref, acc_ref > 0.5)
    gate("材料表の物理モデル(吸収帯 + Kubelka–Munk、実データを一度も見ていない)をライブラリにすると %.3f(当て推量 0.333)" % acc_phys,
         acc_phys > 0.34)
    # 黒い樹脂: 帯の形が消える
    blk = R[(gt == 2)].mean(0)
    others = {POLY_CLASSES[c]: R[gt == c].mean(0) for c in (1, 3, 4, 5, 6)}

    def depth(s):
        base = np.interp(wlk, [1600, 1800], [np.interp(1600, wlk, s), np.interp(1800, wlk, s)])
        m = (wlk > 1650) & (wlk < 1770)
        return float(np.max(1 - s[m] / base[m]))
    NUMBERS.update({"poly_black_mean_R": float(blk.mean()), "poly_black_depth": depth(blk),
                    "poly_white_depth_mean": float(np.mean([depth(s) for s in others.values()]))})
    gate("実データの黒い樹脂: 平均反射率 %.3f、1.65〜1.77 µm の C-H の谷の深さ %.3f(他の 5 種の平均 %.3f)"
         % (blk.mean(), depth(blk), NUMBERS["poly_white_depth_mean"]), depth(blk) < 0.5 * NUMBERS["poly_white_depth_mean"])
    return {"cube": R, "depth": C, "wl": wlk, "gt": gt, "pred": pred, "pred_raw": p_raw, "full": cube, "wl_full": wl, "te": te, "conf": conf, "lib": lib, "phys": phys, "ref": ref,
            "aucs": aucs, "sel": sel, "baccs": baccs, "black": blk, "others": others}


def chapter_real_pork():
    print("\n0b. 実データ: 豚バラの上の異物(Zenodo 17242553、InGaAs ラインスキャン分光カメラ、CC BY 4.0)")
    npz = fetch_pork()
    if npz is None:
        print("   データが無い(FULLSEYE_HSI_DOWNLOAD=1 で取得)。記録値: " + ", ".join("%s %.3f" % kv for kv in RECORDED.items() if kv[0].startswith("pork")))
        return None
    z = np.load(npz)
    caps = sorted(k[5:] for k in z.files if k.startswith("cube_"))
    # 捕捉(撮影)で分ける: 2 枚で学び、残り 2 枚で採点(同じ肉片の隣の画素で当てない)
    train_caps, test_caps = caps[:2], caps[2:]
    # 波長: 記録の説明「942〜1723 nm を 224 帯(約 3.5 nm)、最初と最後の 20 帯を除いて 184 帯」→ 1012〜1653 nm と読む
    wl = 942.0 + (1723.0 - 942.0) / 223.0 * np.arange(20, 204)

    def pix(names):
        X, y = [], []
        for k in names:
            c, l = z["cube_" + k], z["lab_" + k]
            m = l >= 0
            X.append(c[m])
            y.append(l[m])
        return np.concatenate(X).astype(np.float64), np.concatenate(y).astype(int)
    Xtr, ytr = pix(train_caps)
    Xte, yte = pix(test_caps)
    present = [c for c in range(13) if (ytr == c).sum() >= 20 and (yte == c).sum() >= 1]
    lib = np.stack([unit(unit(Xtr[ytr == c]).mean(0)) for c in present])
    ang = np.arccos(np.clip(unit(Xte) @ lib.T, -1, 1))
    pred = np.array(present)[ang.argmin(-1)]
    conf = np.zeros((13, 13), int)
    np.add.at(conf, (yte, pred), 1)
    neg = np.array([c in PORK_NEG for c in present])
    score = ang[:, neg].min(-1) - ang[:, ~neg].min(-1)          # 陰性(肉・脂・ベルト)より異物に近いほど大
    isf = ~np.isin(yte, PORK_NEG)
    fpr, tpr, auc = roc(score[isf], score[~isf])
    det = float((pred[isf] < 10).mean())
    far = float((pred[~isf] < 10).mean())
    NUMBERS.update({"pork_auc": auc, "pork_detect": det, "pork_false_alarm": far,
                    "pork_n_test": int(len(yte)), "pork_n_foreign_test": int(isf.sum())})
    rec = {PORK_CLASSES[c]: float((pred[yte == c] == c).mean()) for c in range(13) if (yte == c).any()}
    print("   捕捉 %d 枚(学び %s / 採点 %s)、採点 %d px のうち異物 %d px" % (len(caps), train_caps, test_caps, len(yte), int(isf.sum())))
    print("   SAM の再現率: " + "、".join("%s %.2f" % kv for kv in rec.items()))
    gate("★実データ(豚バラ): 異物か陰性かの ROC の AUC %.3f、画素の検出率 %.3f・誤警報 %.4f(SAM、別の撮影で学んだライブラリ)"
         % (auc, det, far), auc > 0.8)
    # Fisher の帯域選択(学びの捕捉だけ)
    F = np.log(np.clip(Xtr, 1e-4, None))[:, None, :]
    sub = np.zeros(len(ytr), bool)
    rs = np.random.default_rng(3)
    for c in present:
        idx = np.flatnonzero(ytr == c)
        sub[rs.choice(idx, min(len(idx), 400), replace=False)] = True
    sel = SP.spec_band_selection_fisher(F[sub], ytr[sub][:, None], n_select=6)
    NUMBERS.update({"pork_band_%d" % i: float(wl[b]) for i, b in enumerate(sel["selected"])})
    print("   Fisher で選んだ帯域(学びの捕捉): %s nm" % ", ".join("%.0f" % wl[b] for b in sel["selected"]))
    # 線形判別(LDA、log 反射率、クラスごとに最大 3,000 画素で学ぶ): 全帯と、Fisher の k 帯
    sub2 = np.zeros(len(ytr), bool)
    for c in present:
        idx = np.flatnonzero(ytr == c)
        sub2[rs.choice(idx, min(len(idx), 3000), replace=False)] = True
    Ltr, Lte = np.log(np.clip(Xtr[sub2], 1e-4, None)), np.log(np.clip(Xte, 1e-4, None))
    lda_rows = []
    for k in (1, 2, 3, 4, 6, None):
        b = list(range(Xtr.shape[1])) if k is None else sel["selected"][:k]
        mdl = lda_fit(Ltr[:, b], ytr[sub2])
        pl = lda_predict(mdl, Lte[:, b][:, None, :])[:, 0]
        lda_rows.append((k or Xtr.shape[1], float((pl[isf] < 10).mean()), float((pl[~isf] < 10).mean())))
    pred_lda = pl
    NUMBERS.update({"pork_lda_det": lda_rows[-1][1], "pork_lda_fa": lda_rows[-1][2]})
    NUMBERS.update({"pork_lda_k%d_det" % r[0]: r[1] for r in lda_rows})
    NUMBERS.update({"pork_lda_k%d_fa" % r[0]: r[2] for r in lda_rows})
    print("   LDA(log 反射率): " + " / ".join("%d 帯 → 検出 %.3f・誤警報 %.4f" % r for r in lda_rows))
    gate("★実データ(豚バラ): 全 %d 帯の LDA で異物の画素の検出率 %.3f・誤警報 %.4f —— SAM(誤警報 %.3f)より 1 桁少ない"
         % (Xtr.shape[1], lda_rows[-1][1], lda_rows[-1][2], far), lda_rows[-1][2] < far / 3 and lda_rows[-1][1] > 0.8)
    # 波長の読みの検算: 脂の平均スペクトルの谷は脂質の C-H 2 次倍音(1210 nm)の近くに、肉は水(1450 nm)の近くに出るはず
    fat, meat = Xtr[ytr == 11].mean(0), Xtr[ytr == 10].mean(0)

    def trough(s, lo_, hi_):
        m = (wl > lo_) & (wl < hi_)
        x, y = wl[m], s[m]
        base = np.interp(x, [x[0], x[-1]], [y[0], y[-1]])
        return float(x[np.argmin(y / base)])
    tf, tm = trough(fat, 1150, 1260), trough(meat, 1380, 1520)
    tp = trough(Xtr[ytr == 3].mean(0), 1150, 1260)
    NUMBERS.update({"pork_fat_trough": tf, "pork_meat_trough": tm, "pork_pehd_trough": tp})
    gate("波長の読み(942 + 3.50 nm × 帯番号 20〜203、記録の説明から再構成)の検算: PEHD の谷 %.0f nm(USGS の HDPE 1215 nm)、"
         "脂 %.0f nm(脂質 1210 nm)、肉 %.0f nm(水 1450 nm)—— 札は 15〜35 nm 短い側にずれている可能性があり、選んだ帯域の波長はその幅で読む"
         % (tp, tf, tm), abs(tp - 1215) < 30 and abs(tf - 1210) < 30 and abs(tm - 1450) < 40)
    conf_lda = np.zeros((13, 13), int)
    np.add.at(conf_lda, (yte, pred_lda), 1)
    return {"z": z, "caps": caps, "test_caps": test_caps, "wl": wl, "lib": lib, "present": present, "conf": conf_lda, "conf_sam": conf,
            "lda": lda_fit(Ltr, ytr[sub2]), "lda_rows": lda_rows,
            "roc": (fpr, tpr, auc), "sel": sel, "fat": fat, "meat": meat}


# --------------------------------------------------------------------------- #
# 1. 物理の門                                                                   #
# --------------------------------------------------------------------------- #
def chapter_physics():
    print("\n1. 物理の門(Kubelka–Munk・InGaAs・水・樹脂の谷・撮像の線形性)")
    flat = np.stack([WL[:11], np.full(11, 0.4)], axis=1)
    r_inf = SR.kubelka_munk_reflectance(flat, 3.0, None)[0, 1]
    ks = 0.8 / 3.0
    e1 = abs(r_inf - (1 + ks - math.sqrt(ks * ks + 2 * ks)))
    e2 = abs((1 - r_inf) ** 2 / (2 * r_inf) - ks) / ks
    e3 = max(abs(SR.kubelka_munk_reflectance(flat, 3.0, X, r_inf)[0, 1] - r_inf) for X in (0.01, 0.3, 3.0))
    sx, rg = 0.6, 0.3
    e4 = abs(SR.kubelka_munk_reflectance(flat * [1, 0], 3.0, 0.2, rg)[0, 1] - (sx * (1 - rg) + rg) / (1 + sx * (1 - rg)))
    gate("Kubelka–Munk: R∞ の閉形式・逆 K/S = (1−R)²/2R・背景 = R∞ で厚さに不変・吸収 0 の式 6(1e-12)",
         max(e1, e2, e3, e4) < 1e-12, "最大 %.1e" % max(e1, e2, e3, e4))
    qs = SR.ingaas_photodiode_qe(1700.0, wl_min_nm=800.0, wl_max_nm=2600.0, n_points=1801)
    qe_ = SR.ingaas_photodiode_qe(2500.0, wl_min_nm=800.0, wl_max_nm=2600.0, n_points=1801)
    NUMBERS.update({"qe_std_1300": _at(qs, 1300.0), "qe_std_1750": _at(qs, 1750.0), "qe_ext_2300": _at(qe_, 2300.0)})
    gate("InGaAs: 標準は 1.0〜1.6 µm で 0.8 以上・1.75 µm で 5 % 未満、拡張は 2.3 µm で 0.7 以上",
         min(_at(qs, w) for w in (1000.0, 1300.0, 1600.0)) > 0.8 and _at(qs, 1750.0) < 0.05 and _at(qe_, 2300.0) > 0.7,
         "標準 1300 nm %.2f / 1750 nm %.3f、拡張 2300 nm %.2f" % (_at(qs, 1300.0), _at(qs, 1750.0), _at(qe_, 2300.0)))
    w = MT.material_nir_absorption("WATER", 1400.0, 2000.0, 601)
    a1450, a1930 = _at(w, 1453.0) * 10.0, _at(w, 1930.0) * 10.0
    NUMBERS.update({"water_1450_per_cm": a1450, "water_1930_per_cm": a1930})
    gate("水の吸収(材料表の Segelstein 1981)は Kou ら 1993 の実測 32.8 / 136.7 /cm と 10 % 以内",
         abs(a1450 / 32.8 - 1) < 0.1 and abs(a1930 / 136.7 - 1) < 0.1, "%.1f / %.1f /cm" % (a1450, a1930))
    troughs = {"PE": (1731.0, 1765.0, 2310.0, 2387.0), "PP": (1709.0, 1727.0), "PET": (1662.0, 2258.0, 2334.0), "PS": (1682.0,)}
    worst = 0.0
    for m, cs in troughs.items():
        r = SR.spectral_reflectance_from_material(m, thickness_mm=None, wl_min_nm=1600.0, wl_max_nm=2450.0, n_points=8501)
        for c in cs:
            loc = r[(r[:, 0] > c - 12) & (r[:, 0] < c + 12)]
            worst = max(worst, abs(loc[np.argmin(loc[:, 1]), 0] - c))
    gate("樹脂の反射の谷は実測位置(USGS splib の PE 1731/1765/2310/2387・PET 1662/2258/2334、論文の PP 1709/1727・PS 1682 nm)と 5 nm 以内",
         worst <= 5.0, "最大 %.1f nm" % worst)
    r1 = SR.spectral_reflectance_from_material("NUT_KERNEL", thickness_mm=None, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    r2 = SR.spectral_reflectance_from_material("PE", thickness_mm=None, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    kw = dict(CHAIN, exposure_s=EXPOSURE_S, **CAMS["std"])
    c1, c2 = SR.hyperspectral_capture(r1, read_noise_e=READ_E, **kw), SR.hyperspectral_capture(r2, read_noise_e=READ_E, **kw)
    mix = SR.hyperspectral_capture(np.stack([WL, 0.25 * r1[:, 1] + 0.75 * r2[:, 1]], axis=1), read_noise_e=READ_E, **kw)
    lin = float(np.max(np.abs(mix["electrons"] - 0.25 * c1["electrons"] - 0.75 * c2["electrons"]) / mix["electrons"]))
    cube = np.broadcast_to(r1[:, 1], (160, 160, WL.size)).copy()
    out = SR.hyperspectral_capture_cube(cube, WL, seed=11, read_noise_e=READ_E, **kw)
    var = out["cube"].reshape(-1, out["cube"].shape[-1]).var(axis=0)
    vr = float(np.max(np.abs(var / c1["noise_e"] ** 2 - 1)))
    NUMBERS.update({"white_e_mid": float(np.median(c1["white_electrons"])), "kernel_snr_mid": float(np.median(c1["snr"]))})
    gate("撮像は反射率に線形(混合の電子数 = 電子数の混合、1e-12)、画像の分散 = 平均 + 読出し²(5 % 以内)",
         lin < 1e-12 and vr < 0.05, "線形 %.1e、分散比のずれ最大 %.3f" % (lin, vr))
    print("   2 m/s・0.5 mm の画素(露光 %.0f µs)で白板 %.2e 電子/帯、仁の SNR %.0f(帯の中央値)"
          % (EXPOSURE_S * 1e6, NUMBERS["white_e_mid"], NUMBERS["kernel_snr_mid"]))
    return qs, qe_


# --------------------------------------------------------------------------- #
# トレイ(真値つきの合成の場面)                                                 #
# --------------------------------------------------------------------------- #
def _object_spectrum(cls, rng, wet=None, black_material="PP"):
    """クラス *cls* の物体 1 個の反射スペクトル(粒径・含水率・厚さを個体ごとに振る)。"""
    if cls == 1:
        water = rng.uniform(0.035, 0.06) if wet is None else wet
        return SR.spectral_reflectance_from_material("NUT_KERNEL", particle_um=rng.uniform(700, 1400), thickness_mm=None,
                                                     water_fraction=water, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    if cls == 2:
        return SR.spectral_reflectance_from_material("NUT_SHELL", particle_um=rng.uniform(300, 800), thickness_mm=None,
                                                     water_fraction=rng.uniform(0.06, 0.10), wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    if cls == 3:
        return SR.spectral_reflectance_from_material("WOOD", particle_um=rng.uniform(300, 800), thickness_mm=None,
                                                     water_fraction=rng.uniform(0.08, 0.15), wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    if cls in (4, 5):
        m = "PE" if cls == 4 else "PP"
        return SR.spectral_reflectance_from_material(m, particle_um=rng.uniform(350, 700), thickness_mm=rng.uniform(1.0, 3.0),
                                                     background_reflectance=BELT_R, wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    if cls == 6:
        return SR.spectral_reflectance_from_material(black_material, carbon_black_fraction=rng.uniform(0.01, 0.03),
                                                     thickness_mm=rng.uniform(1.0, 3.0), background_reflectance=BELT_R,
                                                     wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    raise ValueError(cls)


def _shape(cls, u, v, a, b, rng):
    """物体の局所座標 (u, v)(長軸 a・短軸 b)で、内側の度合 q(≤ 1 が内側)と高さ h を返す。"""
    if cls == 1:                                   # アーモンド: 涙形(先が細い)
        bb = b * (1.0 - 0.32 * np.clip(u / a, -1, 1))
        q = (u / a) ** 2 + (v / bb) ** 2
        return q, np.sqrt(np.clip(1 - q, 0, 1))
    th = np.arctan2(v / b, u / a)
    if cls in (2, 6, 4, 5):                        # 破片: でこぼこの多角形
        harm = rng.normal(0, 1, (2, 5))
        rr = 1.0 + sum(0.10 / (k + 1) * (harm[0, k] * np.cos((k + 2) * th) + harm[1, k] * np.sin((k + 2) * th)) for k in range(5))
        q = ((u / a) ** 2 + (v / b) ** 2) / rr ** 2
        h = 0.35 * np.sqrt(np.clip(1 - q, 0, 1)) if cls == 2 else 0.12 * np.clip(1 - q, 0, 1)
        return q, h
    q = np.maximum(np.abs(u / a), np.abs(v / b)) ** 4 + 0.0 * th   # 木片: 角の丸い長方形
    return q, 0.18 * np.clip(1 - q, 0, 1) ** 0.3


#: 物体ごとの色の個体差: 彩度を 1 + N(0, σ) 倍、色相(赤と青の比)を 1 + N(0, σ/3)。天然物の色むらは、
#: 異物を同色に合わせた差(±3 %)より大きい —— 仁どうしの方が仁と異物よりばらつく。
CHROMA_JITTER = 0.12
#: 物体ごとの「モデルに無い」スペクトルのばらつき: 反射率に 1 + a·(滑らかな 3 次までの多項式)を掛ける
#: (表面の汚れ・油の染み・個体差の代役)。既定 a = 1 %、4 章で掃く。
SPECTRAL_JITTER = 0.01
_XN = (WL - WL.mean()) / (0.5 * (WL[-1] - WL[0]))


def _jitter(rng, amp):
    c = rng.normal(0.0, 1.0, 3) / math.sqrt(3.0)
    return 1.0 + amp * (c[0] * _XN + c[1] * (1.5 * _XN ** 2 - 0.5) + c[2] * (2.5 * _XN ** 3 - 1.5 * _XN))


def _tint(rgb, sat, hue):
    """線形 RGB の色を、平均の明るさを保って彩度 (1 + sat) 倍・赤/青の比を (1 + hue) 倍にする。"""
    c = np.asarray(rgb, dtype=float)
    m = c.mean()
    c = m + (c - m) * (1.0 + sat)
    c = c * np.array([1.0 + hue, 1.0, 1.0 - hue])
    return np.clip(c, 1e-3, 1.0)


def make_tray(seed, counts=None, h=H, w=W, wet=None, classes=FOOD, black_material="PP", sizes=None,
              spectrum_fn=None, albedo=None, spectral_jitter=SPECTRAL_JITTER, shape_kind=None):
    """真値つきのトレイ: 被覆率 cov、物体の番号 oid、クラス cls、陰影 g、RGB、物体ごとの反射スペクトル。"""
    rng = np.random.default_rng(seed)
    jrng = np.random.default_rng(seed + 7919)          # ばらつきは別の乱数列(形と置き方を変えないため)
    if counts is None:
        scale = (h * w) / (240 * 360)
        counts = {1: max(6, int(round(22 * scale))), 2: max(1, int(round(3 * scale))), 3: max(1, int(round(3 * scale))),
                  4: max(1, int(round(2 * scale))), 5: max(1, int(round(2 * scale))), 6: 1, -1: max(2, int(round(6 * scale)))}
    sizes = sizes or {1: (20, 12), -1: (10, 7), 2: (9, 7), 3: (14, 5), 4: (9, 7), 5: (9, 7), 6: (10, 8)}   # 半軸 [px]
    # -1 = 割れた仁(クラスは仁、形は破片)。形だけで「破片 = 異物」と決められないようにするため
    hs, ws = h * SS, w * SS
    yy, xx = (np.mgrid[0:hs, 0:ws] + 0.5) / SS
    oid = np.full((hs, ws), -1)
    height = np.zeros((hs, ws))
    objs = []
    order = [c for c, n in counts.items() for _ in range(n)]
    rng.shuffle(order)
    occ = np.zeros((h, w), dtype=bool)
    for kind in order:
        cls = 1 if kind == -1 else kind
        a0, b0 = sizes[kind]
        a, b = a0 * rng.uniform(0.8, 1.15), b0 * rng.uniform(0.8, 1.15)
        for _try in range(60):
            cy, cx = rng.uniform(a + 2, h - a - 2), rng.uniform(a + 2, w - a - 2)
            y0, y1, x0, x1 = int(cy - a), int(cy + a) + 1, int(cx - a), int(cx + a) + 1
            if not occ[max(0, y0 - 2):y1 + 2, max(0, x0 - 2):x1 + 2].any():
                break
        else:
            continue
        th = rng.uniform(0, np.pi)
        sl = (slice(max(0, y0 * SS), min(hs, y1 * SS)), slice(max(0, x0 * SS), min(ws, x1 * SS)))
        dy, dx = yy[sl] - cy, xx[sl] - cx
        u = dx * np.cos(th) + dy * np.sin(th)
        v = -dx * np.sin(th) + dy * np.cos(th)
        q, hh = _shape(shape_kind if shape_kind is not None else (2 if kind == -1 else cls), u, v, a, b, rng)
        inside = q <= 1.0
        if cls == 1:
            hh = hh * (1.0 + 0.05 * np.sin(2 * np.pi * v / 2.2 + rng.uniform(0, 6)))   # 皮の縦じわ
        if cls == 3:
            hh = hh * (1.0 + 0.08 * np.sin(2 * np.pi * v / 1.3))                        # 木目
        k = len(objs)
        oid[sl][inside] = k
        height[sl][inside] = hh[inside] * (b * 0.5)
        occ[max(0, y0):y1, max(0, x0):x1] |= True
        spec = (spectrum_fn(cls, rng) if spectrum_fn else _object_spectrum(cls, rng, wet=wet, black_material=black_material))
        objs.append({"cls": cls, "spec": spec[:, 1] * _jitter(jrng, spectral_jitter),
                     "chroma": (CHROMA_JITTER * jrng.normal(), CHROMA_JITTER / 3.0 * jrng.normal()),
                     "gain": rng.uniform(0.9, 1.1)})
    # 被覆率と物体の番号(画素ごとに最多の物体)
    blocks = oid.reshape(h, SS, w, SS).transpose(0, 2, 1, 3).reshape(h, w, SS * SS)
    cov = (blocks >= 0).mean(axis=2)
    big = np.where(blocks >= 0, blocks, -1)
    pix_oid = np.full((h, w), -1)
    for kk in range(len(objs)):
        cnt = (big == kk).sum(axis=2)
        better = cnt > 0
        cur = np.where(pix_oid >= 0, (big == np.maximum(pix_oid, 0)[..., None]).sum(axis=2), 0)
        pix_oid = np.where(better & (cnt > cur), kk, pix_oid)
    # 陰影(Lambert、左上から)と影
    hp = height.reshape(h, SS, w, SS).mean(axis=(1, 3))
    gy, gx = np.gradient(ndi.gaussian_filter(hp, 0.7))
    nz = 1.0 / np.sqrt(1 + gx ** 2 + gy ** 2)
    L = np.array([-0.45, -0.55, 0.70])
    L = L / np.linalg.norm(L)
    lam = np.clip((-gx * L[0] - gy * L[1] + L[2]) * nz, 0, 1)
    g_obj = 0.22 + 0.78 * lam / L[2]
    shadow = ndi.shift((cov > 0.5).astype(float), (3.0, 2.5), order=1) > 0.5
    g_belt = np.where(shadow & (cov < 0.5), 0.55, 1.0) * (1.0 + 0.04 * ndi.gaussian_filter(rng.normal(0, 1, (h, w)), 1.2))
    tex = 1.0 + 0.05 * ndi.gaussian_filter(rng.normal(0, 1, (h, w)), 0.8)
    cls_map = np.where((cov >= 0.5) & (pix_oid >= 0), np.array([o["cls"] for o in objs] + [0])[pix_oid], 0)
    g_obj = g_obj * tex * np.where(pix_oid >= 0, np.array([o["gain"] for o in objs] + [1.0])[pix_oid], 1.0)
    # RGB(同じ陰影・同じ地合い)
    albedo = albedo or RGB_ALBEDO
    alb = np.array([_tint(albedo.get(o["cls"], BELT_RGB), *o["chroma"]) for o in objs] + [BELT_RGB])
    rgb = (cov[..., None] * g_obj[..., None] * alb[pix_oid] + (1 - cov[..., None]) * g_belt[..., None] * np.array(BELT_RGB))
    weave = 1.0 + 0.03 * np.sin(2 * np.pi * (np.arange(w)[None, :] + np.arange(h)[:, None]) / 3.0)
    rgb = rgb * np.where(cov[..., None] < 0.5, weave[..., None], 1.0)
    rgb = np.clip(rgb + rng.normal(0, 0.008, rgb.shape), 0, 1)
    return {"cov": cov, "oid": pix_oid, "cls": cls_map, "g_obj": g_obj, "g_belt": g_belt, "rgb": rgb, "objs": objs,
            "names": classes}


def capture(tray, cam="std", seed=0, temperature_k=None, exposure_s=EXPOSURE_S, white_temperature_k=None):
    """トレイを撮る(行ごとに反射率のキューブを組んで `hyperspectral_capture_cube` に渡す)→ 平場補正した反射率。"""
    kw = dict(CHAIN, exposure_s=exposure_s, **CAMS[cam])
    if temperature_k is not None:
        kw["source_temperature_k"] = temperature_k
    specs = np.stack([o["spec"] for o in tray["objs"]] + [np.full(WL.size, BELT_R)])
    oid = tray["oid"]
    h, w = oid.shape
    out = []
    for i, r0 in enumerate(range(0, h, 24)):
        sl = slice(r0, min(h, r0 + 24))
        cov = tray["cov"][sl][..., None]
        R = cov * tray["g_obj"][sl][..., None] * specs[oid[sl]] + (1 - cov) * tray["g_belt"][sl][..., None] * BELT_R
        out.append(SR.hyperspectral_capture_cube(R, WL, seed=seed * 1000 + i, read_noise_e=READ_E, **kw)["cube"])
    cube = np.concatenate(out, axis=0)
    wkw = dict(kw)
    if white_temperature_k is not None:
        wkw["source_temperature_k"] = white_temperature_k
    white = SR.hyperspectral_band_weights(WL, **wkw).sum(axis=1)          # 白板(R = 1)の電子数
    return cube / white


def unit(X):
    return X / np.maximum(np.linalg.norm(X, axis=-1, keepdims=True), 1e-12)


def library(tray, Rhat, ncls):
    """訓練用トレイの内側の画素(被覆 0.95 以上・陰影 0.4 以上)から、クラスごとの単位スペクトルの平均。"""
    lib = []
    for c in range(ncls):
        m = (tray["cls"] == c) & ((tray["cov"] > 0.95) | (c == 0)) & ((tray["g_obj"] > 0.4) | (c == 0))
        if c == 0:
            m &= tray["cov"] < 0.05
        lib.append(unit(unit(Rhat[m]).mean(axis=0)))
    return np.stack(lib)


def sam_classify(Rhat, lib, bands=None):
    """SAM の最近傍。全帯域は `spec_angle_mapper`(キューブの op)、帯域の部分集合(k = 3 は `color` と
    同じ形なので op が拒む)は同じ式 arccos(x̂·l̂) を numpy で。"""
    if bands is None:
        ang = np.stack([SP.spec_angle_mapper(Rhat, lib[k]) for k in range(len(lib))], axis=-1)
    else:
        ang = np.arccos(np.clip(unit(Rhat[..., bands]) @ unit(lib[:, bands]).T, -1.0, 1.0))
    return np.argmin(ang, axis=-1), ang


def roc(pos, neg):
    """ROC と AUC(Mann–Whitney、同点は 1/2)。"""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    s = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    o = np.argsort(-s, kind="mergesort")
    s, y = s[o], y[o]
    tp, fp = np.cumsum(y), np.cumsum(1 - y)
    keep = np.r_[np.diff(s) != 0, True]
    tpr = np.r_[0, tp[keep] / pos.size]
    fpr = np.r_[0, fp[keep] / neg.size]
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    r = np.empty(allv.size)
    sv = allv[order]
    i = 0
    while i < sv.size:
        j = i
        while j + 1 < sv.size and sv[j + 1] == sv[i]:
            j += 1
        r[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    auc = (r[:pos.size].sum() - pos.size * (pos.size + 1) / 2) / (pos.size * neg.size)
    return fpr, tpr, float(auc)


def interior(tray):
    """採点に使う画素: 境界の混合画素(被覆 0.2〜0.8)を除く。"""
    return (tray["cov"] > 0.8) | (tray["cov"] < 0.2)


# --------------------------------------------------------------------------- #
# 2. RGB では分からない                                                         #
# --------------------------------------------------------------------------- #
def chapter_rgb_vs_hsi():
    print("\n2. 仁と同じ色の殻・木片・樹脂片: RGB と ハイパースペクトルで同じ真値の ROC")
    train = make_tray(101, h=240, w=360)                # 訓練用は常に大きいトレイ(閾値の分位点に仁の個体を足りさせる)
    lib = {cam: library(train, capture(train, cam, seed=1), len(FOOD)) for cam in CAMS}
    n_test = 1 if REDUCED else 3
    tests = [make_tray(200 + i) for i in range(n_test)]
    caps = {cam: [capture(t, cam, seed=2 + i) for i, t in enumerate(tests)] for cam in CAMS}
    # RGB の度合: 仁の平均色との角(色相・彩度。明るさに不変 —— SAM と同じ土俵)
    kern_rgb = unit(np.mean([unit(train["rgb"][(train["cls"] == 1) & (train["cov"] > 0.95)]).mean(axis=0)], axis=0))
    res = {}
    for name in ("rgb", "std", "ext"):
        pos, neg, pos_o, neg_o = [], [], [], []
        for i, t in enumerate(tests):
            if name == "rgb":
                score = np.degrees(np.arccos(np.clip(unit(t["rgb"]) @ kern_rgb, -1, 1)))
            else:
                score = np.degrees(SP.spec_angle_mapper(caps[name][i], lib[name][1]))
            m = interior(t)
            sc = np.isin(t["cls"], SAME_COLOUR) & m
            pos.append(score[sc])
            neg.append(score[(t["cls"] == 1) & m])
            for k, o in enumerate(t["objs"]):
                px = (t["oid"] == k) & (t["cov"] > 0.8)
                if not px.any():
                    continue
                (pos_o if o["cls"] in SAME_COLOUR else neg_o if o["cls"] == 1 else []).append(float(np.median(score[px])))
        fpr, tpr, auc = roc(np.concatenate(pos), np.concatenate(neg))
        _, _, auc_o = roc(pos_o, neg_o)
        res[name] = {"fpr": fpr, "tpr": tpr, "auc": auc, "auc_obj": auc_o, "n_obj": (len(pos_o), len(neg_o))}
        NUMBERS["auc_" + name] = auc
        NUMBERS["auc_obj_" + name] = auc_o
    gate("★RGB は同色の異物を見分けられない: 画素の ROC の AUC %.2f(0.5 = 当て推量、0.25〜0.75 の内)" % res["rgb"]["auc"],
         abs(res["rgb"]["auc"] - 0.5) < 0.25, "物体ごと(中央値)%.2f、異物 %d 個・仁 %d 個" % ((res["rgb"]["auc_obj"],) + res["rgb"]["n_obj"]))
    gate("★ハイパースペクトル(標準 InGaAs)は同じ真値で AUC %.4f(物体ごと %.3f)" % (res["std"]["auc"], res["std"]["auc_obj"]),
         res["std"]["auc"] > 0.99 and res["std"]["auc_obj"] >= 0.99)
    gate("拡張 InGaAs(2.5 µm まで)も AUC %.4f" % res["ext"]["auc"], res["ext"]["auc"] > 0.99)
    # AUC の自己検算: Mann–Whitney と台形則は同じ数
    for name in ("rgb", "std"):
        trap = float(np.trapezoid(res[name]["tpr"], res[name]["fpr"]))
        gate("ROC の面積(台形則)= Mann–Whitney の U/(n₁n₂)(%s、1e-9)" % name, abs(trap - res[name]["auc"]) < 1e-9,
             "%.6f vs %.6f" % (trap, res[name]["auc"]))
    # 混同行列(標準 InGaAs、全クラス)
    conf = np.zeros((len(FOOD), len(FOOD)), dtype=int)
    for i, t in enumerate(tests):
        pred, _ = sam_classify(caps["std"][i], lib["std"])
        m = interior(t)
        np.add.at(conf, (t["cls"][m], pred[m]), 1)
    recall = conf.diagonal() / np.maximum(conf.sum(axis=1), 1)
    NUMBERS.update({"recall_%d" % c: float(recall[c]) for c in range(len(FOOD))})
    print("   混同行列(行 = 真値): " + " | ".join(FOOD[i] + " " + ",".join(str(v) for v in conf[i]) for i in range(len(FOOD))))
    print("   標準 InGaAs のクラス別再現率: " + "、".join("%s %.3f" % (FOOD[c], recall[c]) for c in range(len(FOOD))))
    plant = (conf[2, 2] + conf[2, 3] + conf[3, 2] + conf[3, 3]) / max(conf[2:4].sum(), 1)
    sw_ = (conf[2, 3] + conf[3, 2]) / max(conf[2:4].sum(), 1)
    NUMBERS.update({"plant_recall": float(plant), "shell_wood_swap": float(sw_)})
    gate("混同行列(標準 InGaAs、境界を除く画素): 仁・PE・PP・黒い樹脂の再現率と、殻 + 木片を 1 つの「植物片」にした再現率がどれも 0.95 以上",
         all(recall[c] >= 0.95 for c in (1, 4, 5, 6)) and plant >= 0.95,
         "仁 %.3f / 植物片 %.3f / PE %.3f / PP %.3f / 黒 %.3f" % (recall[1], plant, recall[4], recall[5], recall[6]))
    print("   ★所見: 殻と木片は同じリグノセルロース(成分の比と水分が違うだけ)で、互いの取り違えが植物片の %.1f %% —— "
          "仁からは分かれるが、殻と木片を分ける必要があるなら帯の物理がもう 1 つ要る" % (sw_ * 100))
    # 排出の閾値(学習する数はこの 1 つ): 訓練用トレイで、仁の角の 99.5 % 点 q_k と同色の異物の 0.5 % 点 q_f の
    # 幾何平均(間が空いていれば余裕の真ん中)。★初版は q_k だけで決め、試験のトレイで粒径・含水率の端の仁を
    # 丸ごと排出した(画素の分位点は仁の「個体」のばらつきを数えていない、2026-10-15 に図で見つけた)。
    at = np.degrees(SP.spec_angle_mapper(capture(train, "std", seed=1), lib["std"][1]))
    qk = float(np.quantile(at[(train["cls"] == 1) & interior(train)], 0.995))
    qf = float(np.quantile(at[np.isin(train["cls"], SAME_COLOUR) & interior(train)], 0.005))
    thr = math.sqrt(qk * qf) if qf > qk else qk
    NUMBERS.update({"thr_deg": thr, "thr_qk": qk, "thr_qf": qf})
    print("   排出の閾値: 訓練用トレイの仁の 99.5 %% 点 %.2f° と異物の 0.5 %% 点 %.2f° の幾何平均 = %.2f°" % (qk, qf, thr))
    # 物体ごとの判定(選別機は物体ごとに弾く): ベルトでない画素の連結成分、その角の中央値 > 閾値で排出
    ok_f = ok_k = n_f = n_k = 0
    for i, t in enumerate(tests):
        comp = object_decisions(caps["std"][i], lib["std"], thr)
        for lab_, rej, truth in comp_truth(comp, t):
            if truth in FOREIGN:
                n_f += 1
                ok_f += int(rej)
            elif truth == 1:
                n_k += 1
                ok_k += int(not rej)
    NUMBERS.update({"obj_foreign_hit": ok_f, "obj_foreign_n": n_f, "obj_kernel_false": n_k - ok_k, "obj_kernel_n": n_k})
    gate("★物体ごとの判定(標準 InGaAs、連結成分の角の中央値 > %.2f°): 異物 %d 個中 %d 個を排出、仁 %d 個中 %d 個を誤排出"
         % (thr, n_f, ok_f, n_k, n_k - ok_k), ok_f == n_f and (n_k - ok_k) <= max(1, n_k // 50))
    return {"train": train, "lib": lib, "tests": tests, "caps": caps, "roc": res, "conf": conf, "kern_rgb": kern_rgb,
            "thr": thr}


def object_decisions(Rhat, lib, thr):
    """真値を使わない物体の判定: SAM でベルト以外の画素 → 連結成分 → 仁の平均との角の中央値で排出。"""
    pred, _ = sam_classify(Rhat, lib)
    ang = np.degrees(SP.spec_angle_mapper(Rhat, lib[1]))
    lab, n = ndi.label(pred != 0)
    med = ndi.median(ang, lab, index=np.arange(1, n + 1)) if n else np.zeros(0)
    size = ndi.sum(np.ones_like(ang), lab, index=np.arange(1, n + 1)) if n else np.zeros(0)
    rej = np.zeros(n + 1, dtype=bool)
    rej[1:] = (np.asarray(med) > thr) & (np.asarray(size) >= 6)     # 6 画素未満の成分(境界のかけら)は弾かない
    return {"label": lab, "n": n, "reject": rej}


def comp_truth(comp, tray):
    """連結成分ごとに (番号, 排出したか, 真値のクラス(成分の画素で最多の物体のクラス))。"""
    lab = comp["label"]
    out = []
    for k in range(1, comp["n"] + 1):
        c = tray["cls"][lab == k]
        c = c[c > 0]
        if c.size < 6:
            continue
        out.append((k, bool(comp["reject"][k]), int(np.bincount(c).argmax())))
    return out


# --------------------------------------------------------------------------- #
# 3. 何帯域で足りるか                                                            #
# --------------------------------------------------------------------------- #
MERGE = np.array([0, 1, 2, 2, 4, 5, 6])          # 殻と木片を 1 つの「植物片」に(3 → 2)
EVAL_CLASSES = (0, 1, 2, 4, 5, 6)


def balanced_recall(pred, tray, m=None):
    """クラスごとの再現率の平均(殻と木片は植物片にまとめる)。画素数の多い仁に精度が引っ張られないように。"""
    m = interior(tray) if m is None else m
    t, p = MERGE[tray["cls"][m]], MERGE[pred[m]]
    rec = [float((p[t == c] == c).mean()) for c in EVAL_CLASSES if np.any(t == c)]
    return float(np.mean(rec))


def _logfeat(R):
    return np.log(np.clip(R, 1e-4, None))


def lda_fit(X, y, ridge=1e-6):
    """等事前確率の線形判別(共通の共分散、Mahalanobis の最近傍)。X は (N, k) の log 反射率。"""
    cls = np.unique(y)
    mu = np.stack([X[y == c].mean(axis=0) for c in cls])
    D = X - mu[np.searchsorted(cls, y)]
    S = D.T @ D / max(len(X) - len(cls), 1)
    S += np.eye(S.shape[0]) * ridge * np.trace(S) / S.shape[0]
    return cls, mu, np.linalg.inv(S)


def lda_predict(model, X):
    cls, mu, Si = model
    flat = X.reshape(-1, X.shape[-1])
    d = np.stack([np.einsum("ij,jk,ik->i", flat - m, Si, flat - m) for m in mu], axis=1)
    return cls[np.argmin(d, axis=1)].reshape(X.shape[:-1])


def chapter_bands(ctx):
    print("\n3. 帯域の選択(Fisher 比 + 前向き選択): マルチスペクトルで何帯域あれば足りるか")
    train, tests = ctx["train"], ctx["tests"]
    out = {}
    m = interior(train) & ((train["cov"] > 0.8) | (train["cov"] < 0.05))
    # ★クラスごとに同じ画素数で選ぶ: Fisher の Sb = Σ n_k (μ_k − μ)² は画素の多いクラス(ベルト・仁)に
    #   引っ張られ、少ない樹脂片どうし(PE と PP)を分ける帯域を選ばなくなる(2026-10-15 の初回で実測)。
    rs = np.random.default_rng(5)
    n_each = min(int((m & (train["cls"] == c)).sum()) for c in range(len(FOOD)))
    keep = np.zeros_like(m)
    for c in range(len(FOOD)):
        idx = np.flatnonzero((m & (train["cls"] == c)).ravel())
        keep.ravel()[rs.choice(idx, n_each, replace=False)] = True
    m = keep
    lab = np.where(m, train["cls"], -1)
    for cam in CAMS:
        Ft = _logfeat(capture(train, cam, seed=1))
        # ★log 反射率で選ぶ: 画素ごとの明るさ(陰影)は全帯に共通の足し算になり、多変量の J はその方向を
        #   クラス内のばらつきとして割り引く(1 帯域だけでは明るさと材質を分けられない —— k = 1 が弱いのはそのため)
        sel = SP.spec_band_selection_fisher(Ft, lab, n_select=6)
        centers = np.asarray(CAMS[cam]["band_centers_nm"])
        ytr = train["cls"][m]
        accs = []
        for k in range(1, 7):
            b = sel["selected"][:k]
            model = lda_fit(Ft[m][:, b], ytr)
            accs.append(float(np.mean([balanced_recall(lda_predict(model, _logfeat(ctx["caps"][cam][i])[..., b]), t)
                                       for i, t in enumerate(tests)])))
        full = float(np.mean([balanced_recall(sam_classify(ctx["caps"][cam][i], ctx["lib"][cam])[0], t)
                              for i, t in enumerate(tests)]))
        out[cam] = {"fisher": sel["fisher"], "selected": sel["selected"], "centers": centers, "acc": accs,
                    "full": full, "crit": sel["criterion"]}
        NUMBERS.update({"bacc_%s_k%d" % (cam, k): a for k, a in zip(range(1, 7), accs)})
        NUMBERS["bacc_%s_full" % cam] = full
        print("   %s: クラスごとに %d 画素、選んだ帯域 %s nm、1〜6 帯域(LDA)のクラス平均再現率 %s、全帯域の SAM %.4f"
              % (CAM_LABEL[cam], n_each, ", ".join("%.0f" % centers[x] for x in sel["selected"]),
                 " / ".join("%.3f" % a for a in accs), full))
    gate("前向き選択の基準 J は帯域を足すほど増える(単調)", all(np.all(np.diff(o["crit"]) >= -1e-9) for o in out.values()))
    s = out["std"]
    k_ok = next((k for k, a in zip(range(1, 7), s["acc"]) if a >= s["full"] - 0.01), None)
    NUMBERS["k_enough_std"] = float(k_ok or 0)
    gate("★標準 InGaAs: Fisher で選んだ %s 帯域の LDA で、全 71 帯域の SAM(%.3f)と 1 %% 以内 —— マルチスペクトルで足りる"
         % (k_ok, s["full"]), k_ok is not None and k_ok <= 6, "1〜6 帯域 " + " / ".join("%.3f" % a for a in s["acc"]))
    gate("1 帯域だけでは足りない(明るさと材質が分けられない): 1 帯域 %.3f < 3 帯域 %.3f" % (s["acc"][0], s["acc"][2]),
         s["acc"][0] < s["acc"][2] - 0.05)
    return out


# --------------------------------------------------------------------------- #
# 4. 何で壊れるか                                                                #
# --------------------------------------------------------------------------- #
def _foreign_rates(Rhat, tray, lib, thr):
    """仁の誤排出率(仁の画素で角 > 閾値)と異物の検出率(同色の異物の画素で角 > 閾値)。"""
    ang = np.degrees(SP.spec_angle_mapper(Rhat, lib[1]))
    m = interior(tray)
    k = (tray["cls"] == 1) & m
    f = np.isin(tray["cls"], SAME_COLOUR) & m
    return float((ang[k] > thr).mean()), float((ang[f] > thr).mean()), ang


def chapter_failures(ctx):
    print("\n4. 何で壊れるか: 濡れ・ランプの色温度のずれ・光子の数(搬送速度)・影")
    lib = ctx["lib"]["std"]
    train = ctx["train"]
    thr = ctx["thr"]
    sw = make_tray(300, h=H // 2 if not REDUCED else H, w=W // 2 if not REDUCED else W)
    out = {"thr": thr}
    # 濡れ: 仁の含水率(表面の水)を 4.5 % → 30 %
    wets = [0.045, 0.08, 0.12, 0.2, 0.3] if not REDUCED else [0.045, 0.2]
    rows = []
    for wv in wets:
        t = make_tray(300, h=sw["cov"].shape[0], w=sw["cov"].shape[1], wet=wv)
        fr, det, _ = _foreign_rates(capture(t, "std", seed=5), t, lib, thr)
        rows.append((wv, fr, det))
    out["wet"] = rows
    NUMBERS.update({"wet_fr_%g" % r[0]: r[1] for r in rows})
    gate("★濡れ: 仁の含水率 %.0f %% で誤排出 %.1f %%(乾いた %.1f %% から)—— 水の 1.45 µm 帯がライブラリの仁から外す"
         % (rows[-1][0] * 100, rows[-1][1] * 100, rows[0][1] * 100), rows[-1][1] > 5 * max(rows[0][1], 0.002),
         " / ".join("%.0f%% → %.1f%%" % (r[0] * 100, r[1] * 100) for r in rows))
    # ランプの色温度のずれ(白板は 3000 K で取った後、ランプが T に)
    temps = [3000.0, 2900.0, 2800.0, 2600.0, 2400.0] if not REDUCED else [3000.0, 2600.0]
    rows = []
    for T in temps:
        fr, det, ang = _foreign_rates(capture(sw, "std", seed=6, temperature_k=T, white_temperature_k=3000.0), sw, lib, thr)
        rows.append((T, fr, det, float(np.median(ang[(sw["cls"] == 1) & interior(sw)]))))
    out["drift"] = rows
    NUMBERS.update({"drift_fr_%d" % r[0]: r[1] for r in rows})
    gate("ランプの色温度が白板の後で %.0f K 下がると仁の角の中央値 %.2f° → %.2f°、誤排出 %.1f %%(白板を取り直せば戻る)"
         % (3000 - temps[-1], rows[0][3], rows[-1][3], rows[-1][1] * 100), rows[-1][3] > rows[0][3] and rows[-1][1] > rows[0][1],
         " / ".join("%.0f K → %.1f%%" % (r[0], r[1] * 100) for r in rows))
    fr_fix, _, _ = _foreign_rates(capture(sw, "std", seed=6, temperature_k=temps[-1], white_temperature_k=temps[-1]), sw, lib, thr)
    NUMBERS["drift_fixed_fr"] = fr_fix
    gate("同じ %.0f K でも白板を同じランプで取り直すと誤排出 %.1f %%(ずれの正体は平場補正の分母)" % (temps[-1], fr_fix * 100),
         fr_fix < 0.5 * max(rows[-1][1], 1e-9) or fr_fix < 0.01)
    # 光子の数: 露光(= 画素の長さ / 速度)を振る
    speeds = [2.0, 20.0, 100.0, 200.0, 400.0, 800.0, 1500.0] if not REDUCED else [2.0, 400.0]
    rows = []
    for v in speeds:
        e = MM_PX * 1e-3 / v
        R = capture(sw, "std", seed=7, exposure_s=e)
        fr, det, _ = _foreign_rates(R, sw, lib, thr)
        white = SR.hyperspectral_band_weights(WL, **dict(CHAIN, exposure_s=e, **CAMS["std"])).sum(axis=1)
        rows.append((v, float(np.median(white)), fr, det))
    out["speed"] = rows
    print("   搬送速度(露光 = 0.5 mm / 速度): " + " / ".join("%.0f m/s(白板 %.1e e)→ 誤排出 %.1f %%・検出 %.3f" % (r[0], r[1], r[2] * 100, r[3]) for r in rows))
    NUMBERS.update({"speed_fr_%g" % r[0]: r[2] for r in rows})
    NUMBERS.update({"speed_det_%g" % r[0]: r[3] for r in rows})
    gate("光子の数: 2 m/s(白板 %.1e 電子/帯)では誤排出 %.2f %%・検出 %.3f。光子が 1/%.0f(%.0f m/s 相当)で誤排出 %.1f %%"
         % (rows[0][1], rows[0][2] * 100, rows[0][3], rows[0][1] / rows[-1][1], rows[-1][0], rows[-1][2] * 100),
         rows[-1][2] > rows[0][2])
    # 影: 陰影の暗い画素ほど角が散る(SAM は明るさに不変、雑音は不変でない)
    _, _, ang = _foreign_rates(capture(sw, "std", seed=8), sw, lib, thr)
    dev = np.full(ang.shape, np.nan)
    for kk, o in enumerate(sw["objs"]):
        px = (sw["oid"] == kk) & (sw["cov"] > 0.95)
        if o["cls"] == 1 and px.sum() > 10:
            dev[px] = ang[px] - np.median(ang[px])                  # 個体差を除いた、画素ごとの雑音の角
    k = np.isfinite(dev)
    dark, bright = k & (sw["g_obj"] < 0.5), k & (sw["g_obj"] > 0.95)
    out["shadow"] = (float(np.std(dev[dark])) if dark.sum() > 20 else float("nan"), float(np.std(dev[bright])))
    NUMBERS.update({"shadow_std_dark": out["shadow"][0], "shadow_std_bright": out["shadow"][1]})
    gate("影: 個体差を引いた画素の角の揺れは、暗い面(陰影 < 0.5)が明るい面(> 0.95)より大きい(%.3f° vs %.3f°)—— SAM は明るさに不変でも雑音は不変でない"
         % out["shadow"], dark.sum() > 20 and out["shadow"][0] > 1.2 * out["shadow"][1])
    # モデルに無いばらつき(逆犯罪の検査): 場面の物体のスペクトルに、ライブラリが知らない滑らかなゆがみを足す
    amps = [0.01, 0.03, 0.06, 0.1, 0.2] if not REDUCED else [0.01, 0.1]
    rows = []
    for a in amps:
        t = make_tray(300, h=sw["cov"].shape[0], w=sw["cov"].shape[1], spectral_jitter=a)
        R = capture(t, "std", seed=9)
        fr, det, ang = _foreign_rates(R, t, lib, thr)
        k = (t["cls"] == 1) & interior(t)
        f = np.isin(t["cls"], SAME_COLOUR) & interior(t)
        _, _, auc = roc(ang[f], ang[k])
        rows.append((a, fr, det, auc, balanced_recall(sam_classify(R, ctx["lib"]["std"])[0], t)))
    out["jitter"] = rows
    NUMBERS.update({"jit_auc_%g" % r[0]: r[3] for r in rows})
    NUMBERS.update({"jit_fr_%g" % r[0]: r[1] for r in rows})
    NUMBERS.update({"jit_bacc_%g" % r[0]: r[4] for r in rows})
    print("   モデルに無いばらつき(反射率に 1 + a·滑らかな多項式): " + " / ".join(
        "a %.0f %% → AUC %.4f・誤排出 %.1f %%・クラス平均再現率 %.3f" % (r[0] * 100, r[3], r[1] * 100, r[4]) for r in rows))
    gate("★逆犯罪の検査: ライブラリが知らないスペクトルのゆがみ %.0f %% で誤排出 %.1f %%(1 %% では %.1f %%)—— 場面とライブラリが同じモデルだから当たっている分がある"
         % (rows[-1][0] * 100, rows[-1][1] * 100, rows[0][1] * 100), rows[-1][1] > rows[0][1])
    out["sw"] = sw
    return out


# --------------------------------------------------------------------------- #
# 5. 黒い樹脂                                                                   #
# --------------------------------------------------------------------------- #
def chapter_black():
    print("\n5. 黒い樹脂(カーボンブラック): 帯の形が消え、材質が分からない —— 何 wt % から?")
    kw = dict(wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    cam = dict(CHAIN, exposure_s=EXPOSURE_S, **CAMS["ext"])

    def view(m, cb):
        c = SR.hyperspectral_capture(SR.spectral_reflectance_from_material(m, carbon_black_fraction=cb, thickness_mm=None, **kw),
                                     read_noise_e=READ_E, **cam)
        return c["electrons"] / c["white_electrons"], c["noise_e"] / c["white_electrons"]

    def ang(a, b):
        return math.degrees(math.acos(float(np.clip(unit(a) @ unit(b), -1, 1))))

    loads = np.array([0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.03])
    rows = []
    for cb in loads:
        (pp, npp), (pe, _) = view("PP", cb), view("PE", cb)
        # 1 画素の雑音が作る角の目安: 雑音ベクトルの大きさ / 信号ベクトルの大きさ(小角近似)
        rows.append((cb, ang(pp, pe), math.degrees(float(np.linalg.norm(npp) / np.linalg.norm(pp))), float(pp.mean())))
    out = np.array(rows)
    cross = next((r[0] for r in rows if r[1] < r[2]), None)
    NUMBERS.update({"ang_white_pp_pe": rows[0][1], "cb_crossover": float(cross if cross is not None else -1)})
    NUMBERS.update({"ang_pp_pe_cb%g" % (r[0] * 100): r[1] for r in rows})
    NUMBERS.update({"noise_ang_cb%g" % (r[0] * 100): r[2] for r in rows})
    for r in rows:
        print("   カーボンブラック %.1f wt %%: 平均反射率 %.3f、PP と PE の角 %.2f°、1 画素の雑音の角 %.2f°" % (r[0] * 100, r[3], r[1], r[2]))
    gate("★白い PP と PE は %.1f° 離れる。カーボンブラックを増やすと角は単調に縮み、%.1f wt %% で 1 画素の雑音の角を下回る(材質が分からない)"
         % (rows[0][1], (cross or 0) * 100), cross is not None and 0.001 <= cross <= 0.03 and bool(np.all(np.diff(out[:, 1]) < 0)))
    i2 = int(np.argmin(np.abs(loads - 0.02)))
    n_pp = MT.nir_model_info("PP")["n_nir"]
    gate("黒い樹脂(2 wt %%)の反射は %.3f(白の 1/%.0f)で、ほぼ鏡面の Fresnel(n %.2f → %.3f)だけ"
         % (rows[i2][3], rows[0][3] / rows[i2][3], n_pp, ((n_pp - 1) / (n_pp + 1)) ** 2), rows[i2][3] < 0.08)
    cb = MT.carbon_black_absorption(0.02, 900.0, 2500.0, 321)
    a1100 = _at(cb, 1100.0)
    gate("カーボンブラック 2 wt %% の α(1100 nm) = MAC·ρ·w = 7.5 × (550/1100) m²/g × 10⁶ g/m³ × 0.02 = 75 /mm(1e-9)"
         " —— PP の最も強い C-H の帯(%.1f /mm)の %.0f 倍" % (max(b[2] for b in MT.nir_model_info("PP")["bands"]),
                                                            a1100 / max(b[2] for b in MT.nir_model_info("PP")["bands"])),
         abs(a1100 - 75.0) < 1e-9 * 75.0, "%.6f /mm" % a1100)
    sp = {m: SR.spectral_reflectance_from_material(m, thickness_mm=None, **kw) for m in ("PP", "PE")}
    bk = {m: SR.spectral_reflectance_from_material(m, carbon_black_fraction=0.02, thickness_mm=None, **kw) for m in ("PP", "PE")}
    return sp, bk, out


# --------------------------------------------------------------------------- #
# 6. リサイクルの破片                                                            #
# --------------------------------------------------------------------------- #
REC = ["ベルト", "PET", "PP", "PE", "PS", "黒 PP"]
REC_RGB = {1: (0.80, 0.80, 0.78), 2: (0.80, 0.79, 0.78), 3: (0.79, 0.80, 0.78), 4: (0.80, 0.80, 0.79), 5: (0.04, 0.04, 0.04)}


def _rec_spectrum(cls, rng):
    m = {1: "PET", 2: "PP", 3: "PE", 4: "PS", 5: "PP"}[cls]
    return SR.spectral_reflectance_from_material(m, particle_um=rng.uniform(350, 700), thickness_mm=rng.uniform(0.4, 1.0),
                                                 background_reflectance=BELT_R, carbon_black_fraction=0.02 if cls == 5 else 0.0,
                                                 wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)


def make_flakes(seed):
    """白い樹脂の破片(PET/PP/PE/PS、RGB は同じ白)と黒い PP。`make_tray` の形と陰影をそのまま使う。"""
    scale = (H * W) / (240 * 360)
    n = max(3, int(round(9 * scale)))
    return make_tray(seed, counts={1: n, 2: n, 3: n, 4: n, 5: max(1, n // 3)}, classes=REC,
                     sizes={c: (11, 8) for c in range(1, 6)}, spectrum_fn=_rec_spectrum, albedo=REC_RGB,
                     shape_kind=4)                               # 全クラス同じ形(平らな破片)


def chapter_recycling():
    print("\n6. リサイクル: 白い PET / PP / PE / PS の破片(RGB は同じ白)を標準と拡張の InGaAs で")
    train, test = make_flakes(501), make_flakes(502)
    out = {}
    for cam in CAMS:
        lib = library(train, capture(train, cam, seed=21), len(REC))
        R = capture(test, cam, seed=22)
        pred, _ = sam_classify(R, lib)
        m = interior(test)
        conf = np.zeros((len(REC), len(REC)), dtype=int)
        np.add.at(conf, (test["cls"][m], pred[m]), 1)
        rec = conf.diagonal() / np.maximum(conf.sum(axis=1), 1)
        out[cam] = {"R": R, "pred": pred, "conf": conf, "recall": rec}
        NUMBERS.update({"rec_%s_%d" % (cam, c): float(rec[c]) for c in range(1, 6)})
        print("   %s: 再現率 " % CAM_LABEL[cam] + "、".join("%s %.3f" % (REC[c], rec[c]) for c in range(1, 6)))
    s, e = out["std"]["recall"], out["ext"]["recall"]
    gate("白い 4 樹脂は標準 InGaAs でも再現率 0.95 以上(1.2 µm の 2 次倍音と 1.65〜1.7 µm の肩で分かれる)",
         min(s[1:5]) >= 0.95, " / ".join("%.3f" % v for v in s[1:5]))
    gate("拡張 InGaAs(2.3 µm の結合音まで)でも白い 4 樹脂は 0.95 以上", min(e[1:5]) >= 0.95, " / ".join("%.3f" % v for v in e[1:5]))
    out["test"] = test
    return out


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _to8(x):
    return np.clip(x, 0, 1)


def _srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)


def _label(img, text, fs_=13):
    out = np.ones((img.shape[0] + 26, img.shape[1], 3))
    out[26:] = img if img.ndim == 3 else img[..., None]
    return np.asarray(fs.text_box(out, text, (4, 3), anchor="lt", font_size=fs_))


def _up(img, k=2):
    return np.kron(img, np.ones((k, k, 1))) if img.ndim == 3 else np.kron(img, np.ones((k, k)))


CLASS_COLOURS = np.array([(0.15, 0.16, 0.18), (0.80, 0.62, 0.35), (0.90, 0.20, 0.15), (0.95, 0.55, 0.05),
                          (0.10, 0.65, 0.95), (0.55, 0.30, 0.90), (1.0, 1.0, 1.0)])


def _outline(img, tray, classes):
    """真値の異物の輪郭を白い線で(画像の上に)。"""
    out = img.copy()
    fm = np.isin(tray["cls"], classes)
    edge = fm & ~ndi.binary_erosion(fm, iterations=1)
    edge = ndi.binary_dilation(edge)
    out[edge] = (1.0, 1.0, 0.2)
    return out


POLY_COLOURS = np.array([(0.12, 0.12, 0.14), (0.55, 0.30, 0.90), (1.0, 1.0, 1.0), (0.90, 0.20, 0.15), (0.95, 0.55, 0.05),
                         (0.30, 0.80, 0.30), (0.10, 0.65, 0.95)])
PORK_COLOURS = np.array([(211, 244, 255), (250, 128, 114), (255, 212, 221), (76, 76, 76), (0, 255, 0), (0, 76, 116),
                         (119, 95, 236), (201, 0, 55), (168, 199, 157), (10, 117, 173), (223, 116, 255), (255, 255, 0),
                         (53, 136, 119)]) / 255.0
SOURCE_POLY = ("出典: E. Arbash ら, Polymers Hyperspectral Imaging, RODARE (HZDR), doi:10.14278/rodare.3390, CC BY 4.0。"
               "改変: 試験ヘッダの fwhm を 360 帯に切り詰め、1100〜2400 nm を切り出し、連続体除去。")
SOURCE_PORK = ("出典: V. G. Ghimpeteanu, H. Rajani, J. Quintana, R. Garcia, A Hyperspectral Image Dataset for Identifying "
               "Foreign Objects on Pork Belly, Zenodo, doi:10.5281/zenodo.17242553, CC BY 4.0。改変: val の 20x16 パッチを "
               "ファイル名の位置へ並べ直した(画像の一部)。")


def _stretch3(c3):
    lo = np.percentile(c3, 1, axis=(0, 1))
    hi = np.percentile(c3, 99.5, axis=(0, 1))
    return np.clip((c3 - lo) / np.maximum(hi - lo, 1e-9), 0, 1)


def _bands_rgb(cube, wl, nms):
    return _stretch3(np.stack([cube[..., int(np.argmin(np.abs(wl - x)))] for x in nms], -1))


def make_real_figures(rp, rk):
    if rp is not None:
        full, wlf, gt = rp["full"], rp["wl_full"], rp["gt"]
        fc = _bands_rgb(full, wlf, (2300.0, 1730.0, 1210.0))
        gimg = POLY_COLOURS[gt]
        pimg = np.where((gt > 0)[..., None], POLY_COLOURS[rp["pred"]], fc * 0.35)
        wrong = (gt > 0) & (rp["pred"] != gt) & rp["te"]
        pimg[wrong] = pimg[wrong] * 0.4 + 0.6 * np.array([1.0, 1.0, 0.2])
        k = 6
        legend = "PP 紫 / 黒 白 / PVC 赤 / PET 橙 / ABS 緑 / PE 青"
        figs.save("real_polymer_flakes", np.concatenate(
            [_label(_up(fc, k), "実画像(偽色 2300 / 1730 / 1210 nm)", 12), _label(_up(gimg, k), "正解マスク  " + legend, 12),
             _label(_up(pimg, k), "連続体除去 + SAM(右半分で採点、黄 = 誤り)", 12)], axis=1),
                  caption="実データ: 破砕した樹脂片(0.3〜4 cm)を 400〜2500 nm の分光カメラで撮った場面(46 x 92 px、1100〜2400 nm)。左半分の画素のクラス平均で"
                          "学び、右半分を採点: クラス平均の再現率 %.3f(生の反射率の SAM は %.3f)。" % (NUMBERS["poly_sam_bacc"], NUMBERS["poly_sam_raw_bacc"])
                          + SOURCE_POLY)
        wl = rp["wl"]
        ser = []
        for c, name in ((1, "PP"), (4, "PET"), (6, "PE")):
            real = rp["depth"][(gt == c)].mean(0)
            ser.append(("実測 " + name, wl, real))
        for c, name in ((1, "PP"), (4, "PET"), (6, "PE")):
            ser.append(("材料表 " + name, wl, rp["phys"][c]))
        figs.save_plot("real_vs_model_band_depth", ser, xlabel="波長 [nm]", ylabel="帯の深さ 1 − R/包絡", xlim=(1100, 2400),
                       colors=["emphasis", "right", "wrong", "emphasis", "right", "wrong"], styles=[None] * 3 + ["dashed"] * 3,
                       size=(760, 400), title="実測の帯の深さと、材料表の物理モデル",
                       caption="実線: 実データの PP / PET / PE の画素の平均(連続体除去)。破線: この PoC の材料表(吸収帯 + Kubelka–Munk)。"
                               "谷の位置は合い、深さと幅は合わない(模型の強さは推定)。物理モデルだけをライブラリにした 3 種の再現率 %.3f、別撮影の基準試料 %.3f。"
                               % (NUMBERS["poly_acc3_phys"], NUMBERS["poly_acc3_ref"]) + SOURCE_POLY)
        conf = rp["conf"]
        rows = [[POLY_CLASSES[i + 1]] + ["%d" % v for v in conf[i]] + ["%.3f" % (conf[i, i] / max(conf[i].sum(), 1))] for i in range(6)]
        figs.save_table("real_polymer_confusion", ["真値 \\ 判定"] + POLY_CLASSES[1:] + ["再現率"], rows,
                        title="実データの混同行列(樹脂 6 種、連続体除去 + SAM、右半分)", caption=SOURCE_POLY)
    if rk is not None:
        z = rk["z"]
        cap = rk["test_caps"][0]
        cube, lab = z["cube_" + cap], z["lab_" + cap]
        wl = rk["wl"]
        cov = lab >= -1
        fc = _bands_rgb(cube, wl, (1650.0, 1450.0, 1210.0)) * cov[..., None]
        limg = np.where((lab >= 0)[..., None], PORK_COLOURS[np.clip(lab, 0, 12)], 0.08)
        lib, present = rk["lib"], np.array(rk["present"])
        X = cube.reshape(-1, cube.shape[-1]).astype(np.float64)
        ang = np.arccos(np.clip(unit(X) @ lib.T, -1, 1))
        neg = np.isin(present, PORK_NEG)
        score = (ang[:, neg].min(-1) - ang[:, ~neg].min(-1)).reshape(lab.shape)
        plda = lda_predict(rk["lda"], np.log(np.clip(cube.astype(np.float64), 1e-4, None)))
        alarm = (plda < 10) & cov
        _ = score
        grey = np.repeat(fc.mean(-1, keepdims=True), 3, -1) * 0.6
        aimg = np.where(alarm[..., None], np.array([1.0, 0.15, 0.75]), grey)
        figs.save("real_pork_belly", np.concatenate(
            [_label(_up(fc, 2), "実画像(偽色 1650 / 1450 / 1210 nm)", 12), _label(_up(limg, 2), "正解ラベル(記録の色)", 12),
             _label(_up(aimg, 2), "LDA(全 184 帯)が異物と判定した画素", 12)], axis=1),
                  caption="実データ: 豚バラのラインの上の異物(InGaAs ラインスキャン分光カメラ、0.47 mm/px)。学びは別の 2 回の撮影、ここは採点用の撮影。"
                          "LDA(log 反射率、全帯)の画素の検出率 %.3f・誤警報 %.4f(SAM は AUC %.3f・誤警報 %.3f)。val のパッチを元の位置に並べ直した画像。"
                          % (NUMBERS["pork_lda_det"], NUMBERS["pork_lda_fa"], NUMBERS["pork_auc"], NUMBERS["pork_false_alarm"]) + SOURCE_PORK)
        fpr, tpr, auc = rk["roc"]
        figs.save_plot("real_pork_roc", [("SAM  AUC %.3f" % auc, fpr, tpr), ("当て推量", np.array([0.0, 1.0]), np.array([0.0, 1.0]))],
                       xlabel="誤警報率(肉・脂・ベルトを異物と判定)", ylabel="検出率(異物)", xlim=(0, 1), ylim=(0, 1.02),
                       colors=["emphasis", "reference"], styles=[None, "dashed"], aspect="equal", size=(520, 520),
                       title="実データ(豚バラ)の ROC", caption="度合 = 陰性(肉・脂・ベルト)のライブラリへの最小角 − 異物のライブラリへの最小角。" + SOURCE_PORK)
        conf = rk["conf"]
        idx = [c for c in range(13) if conf[c].sum() > 0]
        rows = [[PORK_CLASSES[i]] + ["%d" % conf[i, j] for j in idx] + ["%.3f" % (conf[i, i] / max(conf[i].sum(), 1))] for i in idx]
        figs.save_table("real_pork_confusion", ["真値 \\ 判定"] + [PORK_CLASSES[j] for j in idx] + ["再現率"], rows,
                        title="実データの混同行列(豚バラ、LDA 全帯、採点用の撮影)", caption=SOURCE_PORK)


def make_figures(phys, ctx, bands, fails, black, recyc):
    qs, qe_ = phys
    t = ctx["tests"][0]
    Rs = ctx["caps"]["std"][0]
    cs = np.asarray(CAMS["std"]["band_centers_nm"])
    rgb = _srgb(t["rgb"])
    b1210 = int(np.argmin(np.abs(cs - 1210.0)))
    b1450 = int(np.argmin(np.abs(cs - 1450.0)))
    single = Rs[..., b1210] / np.percentile(Rs[..., b1210], 99.5)
    sel = bands["std"]["selected"][:3]
    fc = np.stack([Rs[..., b] for b in sel], axis=-1)
    fc = (fc - np.percentile(fc, 1, axis=(0, 1))) / (np.percentile(fc, 99.5, axis=(0, 1)) - np.percentile(fc, 1, axis=(0, 1)))
    pred, _ = sam_classify(Rs, ctx["lib"]["std"])
    cmap = CLASS_COLOURS[pred] * np.clip(Rs.mean(axis=-1) / np.percentile(Rs.mean(axis=-1), 99), 0.35, 1)[..., None]
    ang = np.degrees(SP.spec_angle_mapper(Rs, ctx["lib"]["std"][1]))
    comp = object_decisions(Rs, ctx["lib"]["std"], ctx["thr"])
    reject = comp["reject"][comp["label"]]                            # 物体ごとに弾く(選別機の空気噴射の単位)
    grey = np.repeat((0.30 * rgb.mean(axis=-1, keepdims=True) + 0.05), 3, axis=-1)
    hot = np.array([1.0, 0.15, 0.75])
    glow_img = np.where(reject[..., None], 0.25 * grey + 0.75 * hot * (0.55 + 0.45 * np.clip(Rs.mean(-1, keepdims=True) / 0.6, 0, 1)), grey)
    n_foreign = sum(1 for o in t["objs"] if o["cls"] in FOREIGN)
    n_kern = sum(1 for o in t["objs"] if o["cls"] == 1)
    hero = np.concatenate([_label(_up(rgb), "RGB(人の目・カラーカメラ): 仁と割れた仁 %d 個に異物が %d 個 —— どれか分かりますか" % (n_kern, n_foreign)),
                           _label(_up(np.clip(glow_img, 0, 1)), "ハイパースペクトル(0.95〜1.65 µm): 弾く物体だけが光る")], axis=1)
    legend = "  ".join(FOOD[1:])
    figs.save("tray_rgb_vs_hyperspectral", hero,
              caption="同じトレイ。左は RGB(異物の殻・木片・茶色の PE / PP 片は仁と同じ色に合わせ、割れた仁も混ぜて形でも分からないようにした。黒い樹脂だけは黒)。右は 0.95〜1.65 µm の 71 帯域で、"
                      "ベルトでない画素の連結成分ごとに、仁の平均スペクトルとの角(SAM)の中央値が %.2f° を超えた物体を光らせた。画素の ROC の AUC は RGB %.2f、ハイパースペクトル %.4f(同じ真値)。"
                      % (ctx["thr"], NUMBERS["auc_rgb"], NUMBERS["auc_std"]))
    panels = np.concatenate([
        np.concatenate([_label(_up(rgb), "RGB"), _label(_up(np.repeat(np.clip(single, 0, 1)[..., None], 3, -1)), "1210 nm の 1 帯域(脂質の C-H 2 次倍音)")], axis=1),
        np.concatenate([_label(_up(np.clip(fc, 0, 1)), "偽色: Fisher で選んだ 3 帯域 " + " / ".join("%.0f" % cs[b] for b in sel) + " nm"),
                        _label(_up(_outline(cmap, t, FOREIGN)), "分類(SAM)  " + legend + "、黄 = 真値の異物")], axis=1)], axis=0)
    figs.save("four_views_of_one_tray", panels,
              caption="RGB / 1 帯域 / 偽色 / 分類の 4 枚。色: 仁 = 茶、殻 = 赤、木片 = 橙、PE = 青、PP = 紫、黒い樹脂 = 白、ベルト = 黒。黄色の線は真値の異物の輪郭。")
    # スペクトル
    kw = dict(wl_min_nm=900.0, wl_max_nm=2500.0, n_points=321)
    ser = [(n, WL, SR.spectral_reflectance_from_material(m, **kw)[:, 1]) for n, m in
           (("仁(アーモンド型)", "NUT_KERNEL"), ("殻", "NUT_SHELL"), ("木片", "WOOD"), ("PE", "PE"), ("PP", "PP"))]
    inr = lambda q: q[(q[:, 0] >= 900.0) & (q[:, 0] <= 2500.0)]
    ser += [("InGaAs 標準の QE", inr(qs)[:, 0], inr(qs)[:, 1]), ("InGaAs 拡張の QE", inr(qe_)[:, 0], inr(qe_)[:, 1])]
    figs.save_plot("spectra_and_sensors", ser, xlabel="波長 [nm]", ylabel="反射率 / 量子効率", xlim=(900, 2500),
                   styles=[None] * 5 + ["dashed", "dotted"], size=(760, 420), ylim=(0, 1.02),
                   title="材料表から作った反射スペクトルと、InGaAs の感度",
                   caption="仁は脂質の C-H(1210 / 1730 / 2310 nm)と水(1450 / 1940 nm)、殻・木片はセルロースの O-H(1490 / 2100 nm)、樹脂は鋭い C-H の谷。"
                           "標準の InGaAs は 1.7 µm で切れ、樹脂の主な谷(1.7 µm の 1 次倍音と 2.3 µm の結合音)は拡張品でないと見えない。帯の幅と強さは推定(材料表の注)。")
    roc_ = ctx["roc"]
    figs.save_plot("roc_rgb_vs_hyperspectral",
                   [("RGB  AUC %.2f" % roc_["rgb"]["auc"], roc_["rgb"]["fpr"], roc_["rgb"]["tpr"]),
                    ("標準 InGaAs  AUC %.4f" % roc_["std"]["auc"], roc_["std"]["fpr"], roc_["std"]["tpr"]),
                    ("拡張 InGaAs  AUC %.4f" % roc_["ext"]["auc"], roc_["ext"]["fpr"], roc_["ext"]["tpr"]),
                    ("当て推量", np.array([0.0, 1.0]), np.array([0.0, 1.0]))],
                   xlabel="誤排出率(仁を異物と判定)", ylabel="検出率(同色の異物)", xlim=(0, 1), ylim=(0, 1.02),
                   colors=["wrong", "emphasis", "right", "reference"], styles=[None, None, None, "dashed"], aspect="equal",
                   title="同じ真値の ROC: RGB と ハイパースペクトル", size=(520, 520),
                   caption="異物の度合 = 仁の平均との角(RGB は色の角、ハイパースペクトルはスペクトルの角)。境界の混合画素を除く。黒い樹脂は RGB でも見えるので除いた(同色の異物だけ)。")
    conf = ctx["conf"]
    rows = [[FOOD[i]] + ["%d" % v for v in conf[i]] + ["%.3f" % (conf[i, i] / max(conf[i].sum(), 1))] for i in range(len(FOOD))]
    figs.save_table("confusion_food_tray", ["真値 \\ 判定"] + FOOD + ["再現率"], rows, title="混同行列(標準 InGaAs、SAM、境界を除く画素)",
                    caption="行 = 真値、列 = 判定。ライブラリは別の種(シード)の訓練用トレイのクラス平均。")
    ser = []
    for cam in CAMS:
        b = bands[cam]
        ser.append(("Fisher 比 " + ("標準" if cam == "std" else "拡張"), b["centers"], b["fisher"] / b["fisher"].max()))
    figs.save_plot("fisher_ratio_by_band", ser, xlabel="帯域の中心 [nm]", ylabel="Fisher 比(最大で規格化)", xlim=(950, 2450),
                   title="どの帯域が異物を分けるか(Fisher 比)",
                   caption="選んだ帯域(前向き選択の順): 標準 " + ", ".join("%.0f" % bands["std"]["centers"][i] for i in bands["std"]["selected"])
                           + " nm / 拡張 " + ", ".join("%.0f" % bands["ext"]["centers"][i] for i in bands["ext"]["selected"]) + " nm。")
    ks = list(range(1, 7))
    figs.save_plot("accuracy_vs_band_count",
                   [("標準 InGaAs(LDA)", np.array(ks, float), np.array(bands["std"]["acc"])),
                    ("拡張 InGaAs(LDA)", np.array(ks, float), np.array(bands["ext"]["acc"])),
                    ("標準・全 71 帯の SAM", np.array([1.0, 6.0]), np.full(2, bands["std"]["full"])),
                    ("拡張・全 146 帯の SAM", np.array([1.0, 6.0]), np.full(2, bands["ext"]["full"]))],
                   xlabel="帯域の数", ylabel="クラス平均の再現率", kinds=["line", "line", "line", "line"],
                   styles=[None, None, "dashed", "dotted"], colors=["emphasis", "right", "emphasis", "right"],
                   title="マルチスペクトルで何帯域あれば足りるか",
                   caption="Fisher 比 + 前向き選択で選んだ k 帯域の log 反射率に線形判別(LDA)。殻と木片は「植物片」にまとめ、ベルト・仁・植物片・PE・PP・黒の再現率を平均。破線は全帯域の SAM。")
    wet, drift, speed = fails["wet"], fails["drift"], fails["speed"]
    figs.save_plot("failure_wet_and_drift",
                   [("仁の含水率 [%] → 誤排出 [%]", np.array([r[0] * 100 for r in wet]), np.array([r[1] * 100 for r in wet])),
                    ("ランプの低下 [×10 K] → 誤排出 [%]", np.array([(3000 - r[0]) / 10 for r in drift]), np.array([r[1] * 100 for r in drift]))],
                   xlabel="濡れ(含水率 %) / ランプの色温度の低下(×10 K)", ylabel="仁の誤排出率 [%]", kinds=["line", "line"],
                   colors=["wrong", "emphasis"], title="壊れ方: 濡れと白板の後のランプのずれ",
                   caption="閾値は訓練用トレイの仁の 99.5 %% 点(%.2f°)で固定。濡れは水の 1.45 µm 帯が仁のスペクトルを動かす。ランプのずれは平場補正の分母のずれ —— 白板を取り直せば戻る(%.1f %%)。"
                           % (fails["thr"], NUMBERS["drift_fixed_fr"] * 100))
    figs.save_plot("failure_photons",
                   [("誤排出 [%]", np.log10([r[1] for r in speed]), np.array([r[2] * 100 for r in speed])),
                    ("見逃し [%]", np.log10([r[1] for r in speed]), np.array([(1 - r[3]) * 100 for r in speed]))],
                   xlabel="log10(白板の電子数 / 帯)", ylabel="[%]", kinds=["line", "line"], colors=["wrong", "emphasis"],
                   title="光子の数(搬送速度)で壊れる所", caption="露光 = 画素の長さ 0.5 mm / 搬送速度。点は左から "
                   + "、".join("%.0f m/s" % r[0] for r in speed[::-1]) + "(右端が 2 m/s)。")
    sp, bk, bl = black
    ser = [("白い PP", WL, sp["PP"][:, 1]), ("白い PE", WL, sp["PE"][:, 1]), ("黒い PP(2 wt %)", WL, bk["PP"][:, 1]),
           ("黒い PE(2 wt %)", WL, bk["PE"][:, 1])]
    figs.save_plot("black_plastic_spectra", ser, xlabel="波長 [nm]", ylabel="反射率", xlim=(900, 2500), ylim=(0, 1),
                   colors=["emphasis", "right", "emphasis", "right"], styles=[None, None, "dashed", "dashed"],
                   title="黒い樹脂: カーボンブラックが帯の形を消す",
                   caption="白い PP と PE は %.1f° 離れる。カーボンブラック 2 wt %% では %.2f° に縮み、1 画素の雑音の角 %.2f° に埋もれる —— 黒い樹脂を NIR で選別できない業界の既知の限界(中赤外・ラマン・LIBS が代替)。"
                           % (NUMBERS["ang_white_pp_pe"], NUMBERS["ang_pp_pe_cb2"], NUMBERS["noise_ang_cb2"]))
    figs.save_plot("black_plastic_loading", [("PP と PE の角", bl[:, 0] * 100, bl[:, 1]), ("1 画素の雑音の角", bl[:, 0] * 100, bl[:, 2])],
                   xlabel="カーボンブラック [wt %]", ylabel="角 [°]", colors=["emphasis", "wrong"], styles=[None, "dashed"],
                   title="何 wt % から材質が分からなくなるか",
                   caption="拡張 InGaAs、2 m/s。角が雑音の線を下回った所(%.1f wt %%)から、PP と PE を 1 画素では分けられない。画素を N 個平均すれば雑音の角は 1/√N で下がる —— 原理の壁は帯の形そのものが消える高い wt %% の側。"
                           % (NUMBERS["cb_crossover"] * 100))
    tt = recyc["test"]
    rows_img = []
    for cam in CAMS:
        o = recyc[cam]
        cmapr = np.array([(0.15, 0.16, 0.18), (0.95, 0.55, 0.05), (0.55, 0.30, 0.90), (0.10, 0.65, 0.95), (0.90, 0.20, 0.15),
                          (1.0, 1.0, 1.0)])[o["pred"]]
        txt = "%s  再現率 PET %.2f / PP %.2f / PE %.2f / PS %.2f" % ((("標準" if cam == "std" else "拡張"),) + tuple(o["recall"][1:5]))
        rows_img.append(_label(_up(cmapr), txt, fs_=12))
    figs.save("recycling_flakes", np.concatenate([_label(_up(_srgb(tt["rgb"])), "RGB: 白い破片は全部同じ白"), rows_img[0], rows_img[1]], axis=1),
              caption="白い PET(橙)/ PP(紫)/ PE(青)/ PS(赤)と黒い PP(白)の破片。左が RGB、中が標準 InGaAs、右が拡張 InGaAs の SAM の分類。")
    # 帯域を掃く GIF
    frames = []
    step = 2 if not REDUCED else 8
    lo, hi = np.percentile(Rs, 1), np.percentile(Rs, 99.5)
    for bi in range(0, len(cs), step):
        img = np.clip((Rs[..., bi] - lo) / (hi - lo), 0, 1)
        img = _outline(np.repeat(img[..., None], 3, -1), t, FOREIGN)
        frames.append(_label(img, "%.0f nm  (黄 = 真値の異物)" % cs[bi], fs_=12))
    figs.save_gif("band_sweep", frames, fps=6.0,
                  caption="0.95〜1.65 µm を 20 nm おきに掃く。1.2 µm 付近で樹脂片が明るく、1.45 µm(水)で殻と木片が暗く沈む —— 1 帯域では分からない異物が、帯域を動かすと順に浮かぶ。")
    _ = (b1450, ang, fails)


def main():
    t0 = time.time()
    print("PoC 見た目が同じ異物をハイパースペクトルで選別する(予算 %s、トレイ %d x %d px、%.1f mm/px)"
          % ("reduced" if REDUCED else "full", H, W, MM_PX))
    real_poly = chapter_real_polymers()
    real_pork = chapter_real_pork()
    phys = chapter_physics()
    ctx = chapter_rgb_vs_hsi()
    bands = chapter_bands(ctx)
    fails = chapter_failures(ctx)
    black = chapter_black()
    recyc = chapter_recycling()
    if not REDUCED and figs.target_dir() is not None:
        make_real_figures(real_poly, real_pork)
        make_figures(phys, ctx, bands, fails, black, recyc)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
