# -*- coding: utf-8 -*-
"""Batch 2 (photometric): smoothing / gray / arithmetic / color / Image /
augmentation / Tools / restoration."""
import numpy as np
from scipy import ndimage

from fops_lib import ai, sample, skdata, rgb, to_u8, annotate, grid, record, run_jobs

import fullseye
import unified as u
import filters_freq as ffq
from backends_inverse import _motion_psf


# ---------------------------------------------------------------- N1 smoothing
def demo_smoothing():
    noise_a = 0.20
    inputs = [
        ("skimage 同梱 camera", skdata("camera")),
        ("AI 生成: 歯車", ai("gears")),
        ("AI 生成: 果物", ai("fruits")),
    ]
    rows = []
    for name, img in inputs:
        noisy = np.asarray(fullseye.apply(img, "add_noise_white", noise_a, 0.5))
        g = np.asarray(fullseye.apply(noisy, "cv_gaussian", 0.6, 0.5))
        ad = np.asarray(fullseye.apply(noisy, "anisotropic_diffusion", 0.9, 0.5))
        rows.append([
            (f"入力(雑音付き): {name}", rgb(noisy)),
            ("cv_gaussian(エッジも一緒にボケる)", rgb(g)),
            ("anisotropic_diffusion(エッジ保存平滑化)", rgb(ad)),
        ])
    grid(rows, "fops_smoothing.png")
    record({
        "category": "smoothing(48 op)", "file": "fops_smoothing.png", "kind": "新規",
        "caption": "図: smoothing の実処理例 — 同じ雑音入力に対し、ガウス平滑化は輪郭ごとぼかすが、anisotropic_diffusion(異方性拡散)はエッジをまたがずに拡散するため輪郭を保ったまま雑音だけをならす(Fullseye 実出力)。入力は skimage camera+AI 生成画像(Gemini)2 種。",
        "ops": "add_noise_white(a=0.20) / cv_gaussian(a=0.6) / anisotropic_diffusion(a=0.9,b=0.5)",
        "inputs": "3 種", "params": "全入力共通(固定)",
        "result": "3/3 でエッジ保存の差を確認",
    })


# ---------------------------------------------------------------- N2 gray
def demo_gray():
    inputs = [
        ("AI 生成: 薄暗い工房(照明ムラ)", ai("dark_workshop")),
        ("skimage 同梱 moon(低コントラスト)", skdata("moon")),
        ("AI 生成: 果物を露出不足化(×0.3)", np.clip(ai("fruits") * 0.3, 0, 1)),
    ]
    rows = []
    for name, img in inputs:
        eq = np.asarray(fullseye.apply(img, "equ_histo_image", 0.5, 0.5))
        cl = np.asarray(fullseye.apply(img, "clahe", 0.5, 0.5))
        rows.append([
            (f"入力: {name}", rgb(img)),
            ("equ_histo_image(大域: ムラ/ノイズ増幅)", rgb(eq)),
            ("clahe(局所適応: 破綻せず陰影回復)", rgb(cl)),
        ])
    grid(rows, "fops_gray.png")
    record({
        "category": "gray(40 op)", "file": "fops_gray.png", "kind": "新規",
        "caption": "図: gray の実処理例 — 照明ムラ・低コントラストの入力では大域ヒストグラム均等化が破綻(明部の白飛び・ノイズ増幅)しやすいのに対し、clahe(コントラスト制限付き局所適応均等化)は局所ごとに階調を回復する(Fullseye 実出力)。入力は AI 生成(Gemini)2 種+skimage moon(NASA 撮影の月面)。",
        "ops": "equ_histo_image / clahe(a=0.5)",
        "inputs": "3 種(露出不足入力は AI 画像を×0.3 で暗くした合成)", "params": "全入力共通(固定)",
        "result": "3/3 で clahe 側が破綻なく階調回復",
    })


# ---------------------------------------------------------------- N3 arithmetic
def hdr_scene(size=384):
    """Bright lamp + deep shadow with a hidden checker pattern in the dark."""
    yy, xx = np.mgrid[0:size, 0:size]
    img = 0.02 + 0.9 * np.exp(-((yy - 80) ** 2 + (xx - 300) ** 2) / (2 * 70.0 ** 2))
    checker = (((yy // 24) + (xx // 24)) % 2) * 0.015
    img += np.where((yy > 220) & (xx < 220), checker + 0.01, 0.0)
    return np.clip(img, 0, 1)


def demo_arithmetic():
    inputs = [
        ("AI 生成: 薄暗い工房", np.clip(ai("dark_workshop") ** 1.5, 0, 1)),
        ("合成: 強光源+暗部の隠しパターン", hdr_scene()),
        ("skimage 同梱 camera を露出不足化(×0.15)", np.clip(skdata("camera") * 0.15, 0, 1)),
    ]
    rows = []
    for name, img in inputs:
        lin = np.clip(img * 5.0, 0, 1)
        lg = np.asarray(fullseye.apply(img, "log_image", 0.9, 0.5))
        lg = lg / (lg.max() + 1e-9)
        rows.append([
            (f"入力(暗部つぶれ): {name}", rgb(img)),
            ("線形ゲイン ×5(参考: 明部が白飛び)", rgb(lin)),
            ("log_image(対数トーン: 暗部復元+白飛びなし)", rgb(lg)),
        ])
    grid(rows, "fops_arithmetic.png")
    record({
        "category": "arithmetic(10 op)", "file": "fops_arithmetic.png", "kind": "新規",
        "caption": "図: arithmetic の実処理例 — 暗部がつぶれた画像は線形ゲインでは明部が先に白飛びするが、log_image(対数変換)は暗部を持ち上げつつ明部を圧縮するので両立する(Fullseye 実出力)。入力は AI 生成(Gemini)・自前合成・skimage camera 減光の 3 種。",
        "ops": "log_image(a=0.9)、比較列は線形ゲイン×5(numpy、参考)",
        "inputs": "3 種", "params": "全入力共通(固定)",
        "result": "3/3 で暗部復元と白飛び回避を両立(合成入力では暗部の隠しパターンが可視化)",
    })


# ---------------------------------------------------------------- N4 color
def color_patches(size=384):
    """Red vs green patches with equal luminance (0.5) on gray bg."""
    img = np.full((size, size, 3), 0.5)
    from PIL import Image, ImageDraw
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([30, 40, 140, 150], fill=1)
    d.rectangle([220, 60, 340, 170], fill=2)
    d.ellipse([60, 230, 180, 350], fill=2)
    d.rectangle([230, 240, 350, 340], fill=1)
    mm = np.asarray(m)
    # exactly equal luminance red / green (Rec.601 Y = 0.485 for both)
    img[mm == 1] = (0.80, 0.35, 0.3535)   # red,   Y=0.4850
    img[mm == 2] = (0.33, 0.60, 0.2990)   # green, Y=0.4850
    return img


def red_mask_hsv(color_img):
    hsv = np.asarray(fullseye.apply(color_img, "trans_from_rgb", 0.0, 0.5, coerce=False))
    h, s = hsv[..., 0], hsv[..., 1]
    return ((h < 0.045) | (h > 0.62)) & (s > 0.35)


def demo_color():
    inputs = [
        ("AI 生成: ボトルキャップ", ai("bottle_caps", color=True)),
        ("AI 生成: 果物", ai("fruits", color=True)),
        ("合成: 等輝度の赤/緑パッチ", color_patches()),
    ]
    rows = []
    for name, img in inputs:
        gray_i = np.asarray(fullseye.apply(img, "rgb1_to_gray", 0.5, 0.5, coerce=False))
        naive = np.asarray(fullseye.apply(gray_i, "otsu"))
        mask = red_mask_hsv(img)
        over = rgb(img).copy()
        over[~mask] = (over[~mask] * 0.25).astype(np.uint8)
        rows.append([
            (f"入力: {name}", rgb(img)),
            ("rgb1_to_gray+otsu(輝度では赤を選べない)", rgb(naive)),
            ("trans_from_rgb(HSV)→H で赤だけ抽出", over),
        ])
    grid(rows, "fops_color.png")
    record({
        "category": "color(8 op)", "file": "fops_color.png", "kind": "新規",
        "caption": "図: color の実処理例 — 「赤い物だけ選ぶ」は輝度画像では原理的に不可能(等輝度なら二値化で区別できない)だが、trans_from_rgb で HSV に変換し H(色相)チャネルを閾値処理すれば照明の明暗によらず色で選べる(Fullseye 実出力)。入力は AI 生成画像(Gemini)2 種+等輝度の自前合成 1 種。",
        "ops": "rgb1_to_gray+otsu(比較列) / trans_from_rgb(a=0 → HSV) + H∈赤域・S>0.35 の固定閾値",
        "inputs": "3 種", "params": "全入力共通(固定)",
        "result": "3/3 で赤領域のみ抽出(合成入力は輝度差ゼロでも分離できることの証明)",
    })


# ---------------------------------------------------------------- N5 Image
def demo_image():
    inputs = [
        ("skimage 同梱 retina(眼底)", skdata("retina", color=True)),
        ("AI 生成: 果物", ai("fruits", color=True)),
        ("AI 生成: 基板", ai("pcb", color=True)),
    ]
    rows = []
    for name, img in inputs:
        r, g, b = u.image.decompose3(img)
        rows.append([
            (f"入力: {name}", rgb(img)),
            ("decompose3 → R", rgb(r)),
            ("decompose3 → G", rgb(g)),
            ("decompose3 → B", rgb(b)),
        ])
    grid(rows, "fops_image_chapter.png", cell_w=228)
    record({
        "category": "Image(59 op)", "file": "fops_image_chapter.png", "kind": "新規",
        "caption": "図: Image の実処理例 — decompose3 でカラー画像を R/G/B チャネルに分解。チャネルごとに写る情報が違う(眼底では血管と背景のコントラスト配分がチャネルで大きく変わる)(Fullseye 実出力)。入力は scikit-image 同梱 retina+AI 生成画像(Gemini)2 種。診断用途ではなく画像処理デモ。",
        "ops": "decompose3",
        "inputs": "3 種", "params": "パラメータなし",
        "result": "3/3 でチャネル間の情報差を確認",
    })


# ---------------------------------------------------------------- N6 augmentation
def demo_augmentation():
    inputs = [
        ("skimage 同梱 camera", skdata("camera")),
        ("AI 生成: 道路", ai("road")),
        ("AI 生成: 部品トレイ", ai("parts_tray")),
    ]
    rows = []
    for name, img in inputs:
        sn = np.asarray(fullseye.apply(img, "aug_shot_noise", 0.6, 0.5))
        mb = np.asarray(fullseye.apply(img, "aug_motion_blur", 0.6, 0.25))
        vg = np.asarray(fullseye.apply(img, "aug_vignette", 0.7, 0.5))
        rows.append([
            (f"原画像: {name}", rgb(img)),
            ("aug_shot_noise(暗所センサ)", rgb(sn)),
            ("aug_motion_blur(ブレ)", rgb(mb)),
            ("aug_vignette(周辺減光)", rgb(vg)),
        ])
    grid(rows, "fops_augmentation.png", cell_w=228)
    record({
        "category": "augmentation(10 op)", "file": "fops_augmentation.png", "kind": "新規",
        "caption": "図: augmentation の実処理例 — 1 枚の画像から撮像の悪条件(ショットノイズ・モーションブラー・周辺減光)を物理モデルで再現生成し、学習データを増やす op 群(Fullseye 実出力)。入力は skimage camera+AI 生成画像(Gemini)2 種。",
        "ops": "aug_shot_noise(a=0.6) / aug_motion_blur(a=0.6,b=0.25) / aug_vignette(a=0.7)",
        "inputs": "3 種", "params": "全入力共通(固定)",
        "result": "3/3 で三つの劣化を再現",
    })


# ---------------------------------------------------------------- N7 Tools
def dropout_mask(shape, kind, seed=0):
    rng = np.random.default_rng(seed)
    m = np.zeros(shape, bool)
    if kind == "stripes":            # satellite data dropout lines
        for c in rng.integers(0, shape[1] - 8, 7):
            m[:, c:c + rng.integers(3, 9)] = True
    elif kind == "holes":
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
        for _ in range(9):
            cy, cx_ = rng.uniform(30, shape[0] - 30, 2)
            r = rng.uniform(12, 26)
            m |= (yy - cy) ** 2 + (xx - cx_) ** 2 < r ** 2
    else:                            # scratches
        from PIL import Image, ImageDraw
        im = Image.new("1", shape[::-1], 0)
        d = ImageDraw.Draw(im)
        for _ in range(6):
            x0, x1 = rng.uniform(0, shape[1], 2)
            y0, y1 = rng.uniform(0, shape[0], 2)
            d.line([x0, y0, x1, y1], fill=1, width=5)
        m = np.asarray(im, bool)
    return m


def demo_tools():
    inputs = [
        ("NASA/JPL: 火星の砂丘+走査線欠損", "mars", "stripes"),
        ("skimage camera+円形欠損", "camera", "holes"),
        ("AI 生成: 彫像+擦り傷欠損", "statue", "scratch"),
    ]
    rows = []
    for name, src, kind in inputs:
        if src == "mars":
            from PIL import Image
            import os
            im = Image.open(r"C:\dev\projects\imgevolve\studio_assets\sample_sources_ai\mars_dunes.jpg").convert("L")
            s = min(im.size)
            im = im.crop((0, 0, s, s)).resize((384, 384), Image.LANCZOS)
            img = np.asarray(im).astype(np.float64) / 255.0
        elif src == "camera":
            img = skdata("camera")
        else:
            img = ai("statue")
        m = dropout_mask(img.shape, kind)
        damaged = img.copy()
        damaged[m] = 0.0
        naive = damaged.copy()
        naive[m] = img[~m].mean()
        filled = np.asarray(u.tools.interpolate_scattered_data_image(damaged, m, "linear"))
        dam_view = rgb(damaged).copy()
        dam_view[m] = (200, 40, 40)
        rows.append([
            (f"入力(赤=欠損): {name}", dam_view),
            ("平均値で埋める(のっぺり)", rgb(naive)),
            ("interpolate_scattered_data_image(散布補間)", rgb(filled)),
        ])
    grid(rows, "fops_tools.png")
    record({
        "category": "Tools(82 op)", "file": "fops_tools.png", "kind": "新規",
        "caption": "図: Tools の実処理例 — 欠損画素(衛星画像の走査線抜け・キズ)は定数で埋めると継ぎ目が残るが、interpolate_scattered_data_image は残存画素の散布データ補間で滑らかに埋める(Fullseye 実出力)。入力は NASA/JPL-Caltech の火星砂丘(HiRISE, PIA18244, パブリックドメイン)・skimage camera・AI 生成画像(Gemini)。欠損は 3 種とも人工的に付与。",
        "ops": "interpolate_scattered_data_image(method=linear)、比較列は平均値埋め(参考)",
        "inputs": "3 種(欠損形状も 3 種: 走査線/円形/擦り傷)", "params": "全入力共通(固定)",
        "result": "3/3 で滑らかに復元",
    })


# ---------------------------------------------------------------- N8 restoration
def demo_restoration():
    L, ang = 9, 0.0
    a_knob = (L - 3) / 10.0          # iv_motion_deblur: length = 3 + round(a*10)
    b_knob = ang / 180.0
    psf = _motion_psf(L, ang)
    inputs = [
        ("skimage 同梱 page(文字)", skdata("page")),
        ("AI 生成: 基板", ai("pcb")),
        ("skimage 同梱 camera", skdata("camera")),
    ]
    rows = []
    for name, img in inputs:
        blurred = np.clip(ffq.convol_fft(img, psf), 0, 1)
        us = np.asarray(fullseye.apply(blurred, "unsharp", 0.8, 0.5))
        deb = np.asarray(fullseye.apply(blurred, "iv_motion_deblur", a_knob, b_knob))
        rows.append([
            (f"入力(横ブレ L={L}px): {name}", rgb(blurred)),
            ("unsharp(輪郭強調では戻らない)", rgb(us)),
            ("iv_motion_deblur(Wiener 逆畳み込み)", rgb(deb)),
        ])
    grid(rows, "fops_restoration.png")
    record({
        "category": "restoration(12 op)", "file": "fops_restoration.png", "kind": "新規",
        "caption": "図: restoration の実処理例 — モーションブラーは畳み込みなので、輪郭強調(unsharp)では復元できず、ブラー PSF を仮定した iv_motion_deblur(Wiener 逆畳み込み)で初めて文字が読めるまで戻る(Fullseye 実出力)。ブレは線形モーション PSF(L=9px, 0°)を畳み込んで付与(convol_fft)。入力は skimage page/camera+AI 生成画像(Gemini)。",
        "ops": "convol_fft+_motion_psf(L=9,0°)でブレ付与 / unsharp(a=0.8, 比較列) / iv_motion_deblur(a=0.6,b=0.0 → L=9,θ=0°)",
        "inputs": "3 種", "params": "全入力共通(固定・PSF 既知の条件)",
        "result": "3/3 で復元(PSF 既知が前提である旨は本文どおり)",
    })


if __name__ == "__main__":
    run_jobs([
        ("smoothing", demo_smoothing),
        ("gray", demo_gray),
        ("arithmetic", demo_arithmetic),
        ("color", demo_color),
        ("image", demo_image),
        ("augmentation", demo_augmentation),
        ("tools", demo_tools),
        ("restoration", demo_restoration),
    ])
