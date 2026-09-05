"""Cross-library round 3 (mahotas / PyWavelets / SimpleITK / skimage / cv2).

Distinctive operators mined by a per-library agent workflow and VERIFIED to run by
those agents; each recommendation is a one-line recipe over a gray float64 [0,1]
array `v` and knobs `a`,`b`. They are compiled here in a controlled namespace
(numpy + the libraries + a safe builtin subset), wrapped exception-safe, and
RE-VERIFIED by the functional gate before counting. Recipes are our own vetted
data (embedded below), not untrusted input. Prefixes: xmh_/xwt_/xsitk_/xsk3_/xcv3_.
"""
from __future__ import annotations

import numpy as np

_NS = {"np": np}
for _m, _a in (("mahotas", "mahotas"), ("mahotas.features", None), ("mahotas.thresholding", None),
               ("pywt", "pywt"), ("SimpleITK", "SimpleITK"), ("SimpleITK", "sitk"), ("cv2", "cv2")):
    try:
        _mod = __import__(_m, fromlist=["x"]) if "." in _m else __import__(_m)
        if _a:
            _NS[_a] = _mod
    except Exception:
        pass
try:
    import skimage
    _NS["skimage"] = skimage
    from skimage import (filters, morphology, feature, segmentation, restoration,
                         transform, exposure, measure, util)
    _NS.update(filters=filters, morphology=morphology, feature=feature, segmentation=segmentation,
               restoration=restoration, transform=transform, exposure=exposure, measure=measure, util=util)
except Exception:
    pass
try:
    from scipy import ndimage
    import scipy
    _NS.update(ndimage=ndimage, scipy=scipy)
except Exception:
    pass

def _make(recipe, out_sort=None):
    # Vetted, agent-verified one-line recipes over our own libraries. Compiled once;
    # everything lives in `globals` so nested lambdas/comprehensions resolve np/v/a/b.
    from backend_safe import sanitize
    code = compile(recipe, "<recipe>", "eval")

    def fn(v, a, b):
        # ★2026-09-05 まで ``except Exception: out = None`` で**握り潰していた**。
        # 登録時に外側へ ``backend_safe.guard`` が掛かるが、内側で例外を消すと外側は
        # 何も見ない —— strict mode でも例外が出ず、台帳にも残らない。
        # 2026-09-02 の「24 族中 1 族しか台帳に届いていなかった」監査の**取りこぼし**
        # (Fable の敵対レビューが 5 族目として指摘)。例外はそのまま外へ出す:
        # 外側の guard が記録し、sort に合う値へ落とし、strict なら再送出する。
        g = dict(_NS)
        g.update(v=v, a=float(a), b=float(b))
        return sanitize(eval(code, g), v, out_sort)
    return fn


def _make_raw(recipe):
    """例外を**そのまま投げる**評価器。登録ゲート専用。

    ``_make`` が返す関数は fail-soft で、レシピが必ず例外を投げても
    ``sanitize(None, ...)`` が sort として妥当な値(feature なら ``0.0``)を返す。
    そのため ``_gate`` へ渡すと **どんな壊れたレシピも合格してしまう** ――
    「動く op だけ登録する」と謳いながら、構造上ひとつも落とせなかった。

    2026-09-02 実測: ``xcv3_brisk_count`` / ``xcv3_agast_count`` は cv2 5.0.0 で
    ``cv2.BRISK_create`` / ``cv2.AgastFeatureDetector_create`` が
    ``cv2.xfeatures2d`` へ移動したため 36/36 で ``AttributeError`` になっていたが、
    どちらも登録され、あらゆる画像に対して ``0.0`` を返し続けていた
    (対照: ``xcv_orb_count`` は同条件で 8〜365)。
    """
    code = compile(recipe, "<recipe>", "eval")

    def raw(v, a, b):
        g = dict(_NS)
        g.update(v=v, a=float(a), b=float(b))
        return eval(code, g)
    return raw


RECIPES = {
 "xmh_zernike": {
  "in": "image",
  "out": "feature",
  "recipe": "float(np.sum(mahotas.features.zernike_moments((np.clip(v,0,1)*255).astype(np.uint8), radius=max(4,min(v.shape)//2), degree=int(6+a*6))))",
  "cat": "texture/shape-feature"
 },
 "xmh_pftas": {
  "in": "image",
  "out": "feature",
  # PFTAS は 54 次元。**平均を取ると情報が消える**: 総和が「退化していない
  # 正規化ヒストグラム群の個数」という整数になるので、平均は 整数/54 しか
  # 取れない。2026-09-02 実測、12 通りの絵(4 サイズ x 3 内容)で相異なる値は
  # わずか **2 個**(0.09259 と 0.11111)= 事実上の定数だった。
  # 分散にすると 54 次元の分布の広がりが残り、絵ごとに変わる。
  "recipe": "float(np.var(mahotas.features.pftas((np.clip(v,0,1)*255).astype(np.uint8))))",
  "cat": "texture-feature"
 },
 "xmh_bernsen": {
  "in": "image",
  "out": "region",
  "recipe": "mahotas.thresholding.bernsen((np.clip(v,0,1)*255).astype(np.uint8), int(3+a*12), int(5+b*50)).astype(np.float64)",
  "cat": "segmentation"
 },
 "xmh_majority": {
  "in": "region",
  "out": "region",
  "recipe": "mahotas.majority_filter((v>0.5), 2*int(1+a*4)+1).astype(np.float64)",
  "cat": "region-morphology"
 },
 "xmh_haar": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda h:(h-h.min())/(np.ptp(h)+1e-12))(mahotas.haar(np.clip(v[:2*(v.shape[0]//2),:2*(v.shape[1]//2)],0,1).astype(float)))",
  "cat": "transform"
 },
 "xmh_daubechies": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda h:(h-h.min())/(np.ptp(h)+1e-12))(mahotas.daubechies(np.clip(v[:2*(v.shape[0]//2),:2*(v.shape[1]//2)],0,1).astype(float), ['D2','D4','D6','D8'][int(a*3.999)]))",
  "cat": "transform"
 },
 "xmh_soft": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(mahotas.thresholding.soft_threshold(np.clip(v,0,1).astype(float), a*0.5),0,1)",
  "cat": "intensity-transform"
 },
 "xmh_bwperim": {
  "in": "region",
  "out": "region",
  "recipe": "mahotas.bwperim(v>0.5, n=(8 if b>0.5 else 4)).astype(np.float64)",
  "cat": "region-transform"
 },
 "xmh_regmin": {
  "in": "image",
  "out": "region",
  "recipe": "mahotas.regmin(mahotas.gaussian_filter(np.clip(v,0,1).astype(float), 0.15+a*3.0)).astype(np.float64)",
  "cat": "morphology/markers"
 },
 "xmh_selfmatch": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda x,t:(lambda r:1.0-(r-r.min())/(np.ptp(r)+1e-12))(mahotas.template_match(x,t)))(np.clip(v,0,1).astype(float), np.ascontiguousarray(np.clip(v,0,1).astype(float)[v.shape[0]//2-3-int(a*8):v.shape[0]//2+4+int(a*8), v.shape[1]//2-3-int(a*8):v.shape[1]//2+4+int(a*8)]))",
  "cat": "self-similarity"
 },
 "xwt_subband_tile": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda c:(lambda t:(t-t.min())/(t.max()-t.min()+1e-12))(np.block([[c[0],c[1][0]],[c[1][1],c[1][2]]])))(pywt.dwt2(np.clip(v,0,1),'haar'))",
  "cat": "frequency"
 },
 "xwt_visushrink": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda c: np.clip(pywt.waverec2([c[0]]+[tuple(pywt.threshold(d,0.05+0.5*a,'soft') for d in lvl) for lvl in c[1:]],'db4')[:v.shape[0],:v.shape[1]],0,1))(pywt.wavedec2(np.clip(v,0,1),'db4',level=2))",
  "cat": "smoothing"
 },
 "xwt_firm_denoise": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda c: np.clip(pywt.waverec2([c[0]]+[tuple(pywt.threshold_firm(d,0.03+0.2*a,max(0.03+0.2*a+1e-6,0.15+0.4*b)) for d in lvl) for lvl in c[1:]],'sym4')[:v.shape[0],:v.shape[1]],0,1))(pywt.wavedec2(np.clip(v,0,1),'sym4',level=2))",
  "cat": "smoothing"
 },
 "xwt_detail_energy": {
  "in": "image",
  "out": "feature",
  "recipe": "(lambda c: np.float64(sum(float(np.mean(d**2)) for lvl in c[1:] for d in lvl)/(sum(float(np.mean(d**2)) for lvl in c[1:] for d in lvl)+float(np.mean(c[0]**2))+1e-12)))(pywt.wavedec2(np.clip(v,0,1),'db2',level=3))",
  "cat": "features"
 },
 "xwt_hf_reconstruct": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda c:(lambda x:(x-x.min())/(x.max()-x.min()+1e-12))(pywt.waverec2([np.zeros_like(c[0])]+list(c[1:]),'db2')[:v.shape[0],:v.shape[1]]))(pywt.wavedec2(np.clip(v,0,1),'db2',level=2))",
  "cat": "edges"
 },
 "xwt_lf_reconstruct": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda c: np.clip(pywt.waverec2([c[0]]+[tuple(np.zeros_like(d) for d in lvl) for lvl in c[1:]],'db2')[:v.shape[0],:v.shape[1]],0,1))(pywt.wavedec2(np.clip(v,0,1),'db2',level=1+int(a*3)))",
  "cat": "smoothing"
 },
 "xwt_directional_detail": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda cH,cV,cD:(lambda d:np.clip(np.kron(np.abs(d)/(np.abs(d).max()+1e-12),np.ones((2,2)))[:v.shape[0],:v.shape[1]],0,1))([cH,cV,cD][min(2,int(b*3))]))(*pywt.dwt2(np.clip(v,0,1),'db2')[1])",
  "cat": "edges"
 },
 "xwt_packet_entropy": {
  "in": "image",
  "out": "feature",
  "recipe": "(lambda nodes:(lambda e:(lambda p:np.float64(float(-np.sum(p*np.log2(p+1e-12))/np.log2(len(p)))))(e/(e.sum()+1e-12)))(np.array([float(np.sum(n.data**2)) for n in nodes])))(pywt.WaveletPacket2D(np.clip(v,0,1),'db1',maxlevel=2).get_level(2))",
  "cat": "features"
 },
 "xwt_mra_component": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda comps:(lambda d:(d-d.min())/(d.max()-d.min()+1e-12))(sum(comps[min(len(comps)-1,1+int(a*(len(comps)-1)))])))(pywt.mra2(np.clip(v,0,1),'db2',level=3))",
  "cat": "frequency"
 },
 "xsitk_curvature_flow": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.CurvatureFlow(sitk.GetImageFromArray(v.astype('float32')),0.0625,1+int(a*8))),0,1)",
  "cat": ""
 },
 "xsitk_minmax_curv_flow": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.MinMaxCurvatureFlow(sitk.GetImageFromArray(v.astype('float32')),0.0625,1+int(a*8),1+int(b*2))),0,1)",
  "cat": ""
 },
 "xsitk_curv_aniso_diff": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.CurvatureAnisotropicDiffusion(sitk.GetImageFromArray(v.astype('float32')),0.0625,0.5+4.5*a,1,1+int(b*8))),0,1)",
  "cat": ""
 },
 "xsitk_laplacian_sharpen": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda r: np.clip((r-r.min())/((r.max()-r.min())+1e-8),0,1))(sitk.GetArrayFromImage(sitk.LaplacianSharpening(sitk.GetImageFromArray(v.astype('float32')))))",
  "cat": ""
 },
 "xsitk_grayscale_fillhole": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.GrayscaleFillhole(sitk.GetImageFromArray(v.astype('float32')))),0,1)",
  "cat": ""
 },
 "xsitk_grayscale_grindpeak": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.GrayscaleGrindPeak(sitk.GetImageFromArray(v.astype('float32')))),0,1)",
  "cat": ""
 },
 "xsitk_opening_by_recon": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.OpeningByReconstruction(sitk.GetImageFromArray(v.astype('float32')),[1+int(a*4)]*2)),0,1)",
  "cat": ""
 },
 "xsitk_closing_by_recon": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(sitk.GetArrayFromImage(sitk.ClosingByReconstruction(sitk.GetImageFromArray(v.astype('float32')),[1+int(a*4)]*2)),0,1)",
  "cat": ""
 },
 "xsitk_signed_maurer_dist": {
  "in": "region",
  "out": "image",
  "recipe": "(lambda d: np.clip(0.5+0.5*np.tanh(d/(1.0+9.0*a)),0,1))(sitk.GetArrayFromImage(sitk.SignedMaurerDistanceMap(sitk.GetImageFromArray((np.asarray(v)>0.5).astype('uint8')),False,False,False)))",
  "cat": ""
 },
 "xsitk_connected_threshold": {
  "in": "image",
  "out": "region",
  "recipe": "np.asarray(sitk.GetArrayFromImage(sitk.ConnectedThreshold(sitk.GetImageFromArray(v.astype('float32')),[(int(v.shape[1]//2),int(v.shape[0]//2))],float(v[v.shape[0]//2,v.shape[1]//2]-(0.1+0.3*a)),float(v[v.shape[0]//2,v.shape[1]//2]+(0.1+0.3*b)),1)),np.float64)",
  "cat": ""
 },
 "xsitk_confidence_connected": {
  "in": "image",
  "out": "region",
  "recipe": "np.asarray(sitk.GetArrayFromImage(sitk.ConfidenceConnected(sitk.GetImageFromArray(v.astype('float32')),[(int(v.shape[1]//2),int(v.shape[0]//2))],1+int(a*5),1.0+3.0*b,2,1)),np.float64)",
  "cat": ""
 },
 "xsitk_maxentropy_thresh": {
  "in": "image",
  "out": "region",
  "recipe": "np.asarray(sitk.GetArrayFromImage(sitk.MaximumEntropyThreshold(sitk.GetImageFromArray(v.astype('float32')),1,0,int(64+192*a))),np.float64)",
  "cat": ""
 },
 "xsitk_moments_thresh": {
  "in": "image",
  "out": "region",
  "recipe": "np.asarray(sitk.GetArrayFromImage(sitk.MomentsThreshold(sitk.GetImageFromArray(v.astype('float32')),1,0,int(64+192*a))),np.float64)",
  "cat": ""
 },
 "xsitk_huang_thresh": {
  "in": "image",
  "out": "region",
  "recipe": "np.asarray(sitk.GetArrayFromImage(sitk.HuangThreshold(sitk.GetImageFromArray(v.astype('float32')),1,0,int(64+192*a))),np.float64)",
  "cat": ""
 },
 "xsk3_rank_otsu": {
  "in": "image",
  "out": "region",
  "recipe": "((np.clip(v,0,1)*255).astype(np.uint8) > filters.rank.otsu((np.clip(v,0,1)*255).astype(np.uint8), morphology.disk(2+int(a*8)))).astype(np.float64)",
  "cat": "segmentation"
 },
 "xsk3_rank_majority": {
  "in": "region",
  "out": "region",
  "recipe": "(filters.rank.majority((np.asarray(v)>0.5).astype(np.uint8), morphology.disk(1+int(a*3)))>0).astype(np.float64)",
  "cat": "region"
 },
 "xsk3_rank_subtract_mean": {
  "in": "image",
  "out": "image",
  "recipe": "filters.rank.subtract_mean((np.clip(v,0,1)*255).astype(np.uint8), morphology.disk(1+int(a*4))).astype(np.float64)/255",
  "cat": "gray"
 },
 "xsk3_rank_equalize": {
  "in": "image",
  "out": "image",
  "recipe": "filters.rank.equalize((np.clip(v,0,1)*255).astype(np.uint8), morphology.disk(2+int(a*8))).astype(np.float64)/255",
  "cat": "gray"
 },
 "xsk3_rank_mean_bilateral": {
  "in": "image",
  "out": "image",
  "recipe": "filters.rank.mean_bilateral((np.clip(v,0,1)*255).astype(np.uint8), morphology.disk(2+int(a*6)), s0=int(10+40*a), s1=int(10+40*b)).astype(np.float64)/255",
  "cat": "smoothing"
 },
 "xsk3_h_minima": {
  "in": "image",
  "out": "region",
  "recipe": "morphology.h_minima(np.clip(v,0,1), 0.05+0.3*a).astype(np.float64)",
  "cat": "segmentation"
 },
 "xsk3_area_closing": {
  "in": "image",
  "out": "image",
  "recipe": "morphology.area_closing(np.clip(v,0,1), area_threshold=int(16+a*100))",
  "cat": "morphology"
 },
 "xsk3_diameter_closing": {
  "in": "image",
  "out": "image",
  "recipe": "morphology.diameter_closing(np.clip(v,0,1), diameter_threshold=4+int(a*30))",
  "cat": "morphology"
 },
 "xsk3_corner_moravec": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda r: r/(float(np.max(np.abs(r))) or 1.0))(feature.corner_moravec(np.clip(v,0,1), window_size=1+2*int(a*2)).astype(np.float64))",
  "cat": "edges"
 },
 "xsk3_corner_fast": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda r: r/(float(np.max(np.abs(r))) or 1.0))(feature.corner_fast(np.clip(v,0,1), n=9+int(a*3), threshold=0.05+0.2*b).astype(np.float64))",
  "cat": "edges"
 },
 "xsk3_integral_image": {
  "in": "image",
  "out": "image",
  "recipe": "(lambda r: r/(float(np.max(r)) or 1.0))(transform.integral_image(np.clip(v,0,1)).astype(np.float64))",
  "cat": "gray"
 },
 "xsk3_threshold_local_median": {
  "in": "image",
  "out": "region",
  "recipe": "(np.clip(v,0,1) > filters.threshold_local(np.clip(v,0,1), block_size=2*int(a*6)+3, method='median')).astype(np.float64)",
  "cat": "segmentation"
 },
 "xsk3_is_low_contrast": {
  "in": "image",
  "out": "feature",
  "recipe": "np.float64(float(exposure.is_low_contrast(np.clip(v,0,1), fraction_threshold=0.05+0.4*a)))",
  "cat": "features"
 },
 "xsk3_estimate_sigma": {
  "in": "image",
  "out": "feature",
  "recipe": "np.float64(min(1.0, float(restoration.estimate_sigma(np.clip(v,0,1)))*5))",
  "cat": "features"
 },
 "xsk3_peak_local_max": {
  "in": "image",
  "out": "region",
  "recipe": "(lambda c,z: (np.add.at(z,(c[:,0],c[:,1]),1.0), z)[1])(feature.peak_local_max(np.clip(v,0,1), min_distance=int(2+a*8)), np.zeros(np.asarray(v).shape))",
  "cat": "segmentation"
 },
 "xcv3_denoise_tvl1": {
  "in": "image",
  "out": "image",
  "recipe": "(cv2.denoise_TVL1([(np.clip(v,0,1)*255).astype(np.uint8)],(r:=(np.clip(v,0,1)*255).astype(np.uint8).copy()),0.3+2.7*a,int(10+40*b)) or r).astype(np.float64)/255",
  "cat": "smoothing"
 },
 "xcv3_inpaint_ns": {
  "in": "image",
  "out": "image",
  "recipe": "cv2.inpaint((np.clip(v,0,1)*255).astype(np.uint8),(((np.clip(v,0,1)*255).astype(np.uint8)>235)|((np.clip(v,0,1)*255).astype(np.uint8)<20)).astype(np.uint8)*255,3,cv2.INPAINT_NS).astype(np.float64)/255",
  "cat": "restoration"
 },
 "xcv3_pyr_laplacian": {
  "in": "image",
  "out": "image",
  "recipe": "np.clip(v+(0.5+2.5*a)*(v-cv2.pyrUp(cv2.pyrDown(v),dstsize=v.shape[::-1])),0,1)",
  "cat": "smoothing"
 },
 "xcv3_gray_hu1": {
  "in": "image",
  "out": "feature",
  "recipe": "float(min(1.0,cv2.HuMoments(cv2.moments(np.clip(v,0,1)))[0,0]))",
  "cat": "features"
 },
 "xcv3_sift_count": {
  "in": "image",
  "out": "feature",
  "recipe": "float(len(cv2.SIFT_create(nfeatures=int(50+450*a)).detect((np.clip(v,0,1)*255).astype(np.uint8),None)))",
  "cat": "features"
 },
 "xcv3_brisk_count": {
  "in": "image",
  "out": "feature",
  # cv2 5.0.0 で BRISK は cv2.xfeatures2d へ移った。旧配置も残る環境があるので両対応。
  "recipe": "float(len((getattr(cv2,'BRISK_create',None) or cv2.xfeatures2d.BRISK_create)(thresh=int(10+60*a)).detect((np.clip(v,0,1)*255).astype(np.uint8),None)))",
  "cat": "features"
 },
 "xcv3_agast_count": {
  "in": "image",
  "out": "feature",
  # AGAST も同じく cv2.xfeatures2d へ移動(cv2 5.0.0 実測)。両対応にする。
  "recipe": "float(len((getattr(cv2,'AgastFeatureDetector_create',None) or cv2.xfeatures2d.AgastFeatureDetector_create)(threshold=int(5+40*a)).detect((np.clip(v,0,1)*255).astype(np.uint8),None)))",
  "cat": "features"
 },
 "xcv3_lsd_count": {
  "in": "image",
  "out": "feature",
  "recipe": "float(0 if (l:=cv2.createLineSegmentDetector().detect((np.clip(v,0,1)*255).astype(np.uint8))[0]) is None else len(l))",
  "cat": "features"
 }
}



def _gate(fn, in_sort, out_sort, raw=None):
    """Fail-closed: only ops that run and return the declared sort enter the registry.

    *raw* を渡すと、**sanitize を通す前のレシピ**を先に実行する。これが要点で、
    ``fn`` だけを見るゲートは何も落とせない —— ``_make`` の fail-soft が例外を
    ``sanitize(None, ...)`` に化かし、feature なら ``0.0``、image なら入力由来の
    配列という「sort としては妥当な値」を返すため、**必ず合格する**。
    生レシピを先に叩いて初めて「そもそも動かない」を判定できる。
    """
    n = 24
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    img = np.clip(xx / n * 0.6 + 0.2, 0, 1)
    img[(yy - 8) ** 2 + (xx - 8) ** 2 < 12] = 0.9
    base = img if in_sort == "image" else (img > 0.5).astype(np.float64)
    if raw is not None:
        try:
            raw(base.copy(), 0.5, 0.4)
        except Exception:
            return False                 # レシピ自体が動かない(環境依存も含む)
    try:
        o = fn(base.copy(), 0.5, 0.4)
    except Exception:
        return False
    if out_sort == "feature":
        return np.size(o) > 0 and np.isfinite(float(np.asarray(o).reshape(-1)[0]))
    if not (isinstance(o, np.ndarray) and o.ndim == 2 and np.all(np.isfinite(o))):
        return False
    if out_sort == "region":
        return o.min() >= 0 and o.max() <= 1
    return True


#: lambda 相当の op の説明(RECIPES は generic な factory ``_make`` が返す共有の
#: ``fn`` を全 op で使い回すため、docstring を ``fn`` に書いても 56 本すべてが
#: 同じ文言になってしまい個別の説明にならない ―― DOCS 表がその唯一の置き場。
#: ops.py の登録ループが ``fn.__doc__`` の代わりにここを ``Op.doc`` へ積む。
DOCS = {
 "xmh_zernike": (
     "ツェルニケモーメント(Zernike moments、``mahotas.features.zernike_moments``)の総和。"
     "単位円に写した画像の回転不変な形状/濃淡分布の特徴を 1 個の実数に潰して返す。\n\n"
     "半径は画像の短辺の半分に固定。``a`` は次数(degree、6〜12 の整数)を振る —— "
     "次数を上げるほど高次のモーメントまで加算され値が変わる。``b`` は未使用。"
     "モーメント成分ごとの符号や大きさの分布は総和で相殺・情報が失われるため、"
     "形状の指紋として使うには弱い。個々の成分が要る場合は "
     "``mahotas.features.zernike_moments`` を直接呼ぶこと。"
 ),
 "xmh_pftas": (
     "PFTAS(parameter-free threshold adjacency statistics、"
     "``mahotas.features.pftas``)54 次元特徴ベクトルの分散。隣接画素の濃淡関係を"
     "パラメータ無しの閾値で数えたヒストグラム群をまとめたテクスチャ特徴。\n\n"
     "``a``, ``b`` は未使用。2026-09-02 実測: 54 次元の平均を使うと、正規化"
     "ヒストグラムの性質上ほぼ整数/54 の値しか取らず、12 通りの画像(4 サイズ x "
     "3 内容)で相異なる値がわずか 2 個(事実上の定数)だった。分散にすると分布の"
     "広がりが残り画像ごとに変化するため、ここでは分散を採用している。"
 ),
 "xmh_bernsen": (
     "Bernsen 局所二値化(``mahotas.thresholding.bernsen``)。近傍の最大輝度と"
     "最小輝度の中間値をローカル閾値とし、コントラストが低い領域だけ大域しきい値に"
     "フォールバックする。\n\n"
     "``a`` は近傍半径(3〜15 px)、``b`` はコントラスト閾値(5〜55。これを下回る"
     "低コントラスト域はグローバル閾値 128 で代用)を振る。濃淡ムラのある照明下"
     "でのエッジ二値化に向く。"
 ),
 "xmh_majority": (
     "多数決フィルタ(``mahotas.majority_filter``)。二値領域に対し、正方近傍内で "
     "1 が過半数を占める画素だけを 1 に残す平滑化。孤立ノイズの除去や領域境界の"
     "ギザギザ均しに使う。\n\n"
     "``a`` は窓サイズ(``2*int(1+a*4)+1`` で 3〜17 の奇数)を振る。``b`` は未使用。"
 ),
 "xmh_haar": (
     "Haar ウェーブレット変換(``mahotas.haar``)。画像を偶数サイズに切り詰めてから"
     "変換し、結果の係数配列(近似/水平/垂直/対角の各サブバンドが元画像と同じ"
     "大きさの配列に詰め込まれた、Matlab 風の in-place レイアウト)をそのまま "
     "min-max 正規化して画像として見せる。\n\n"
     "分解レベルは 1 段固定。``a``, ``b`` は未使用。値そのものは復元可能な画像では"
     "なく係数の可視化であることに注意。"
 ),
 "xmh_daubechies": (
     "Daubechies ウェーブレット変換(``mahotas.daubechies``)。xmh_haar と同じ配置"
     "(1 段、係数を元画像サイズの配列に詰めて min-max 正規化)で、基底を "
     "Daubechies 系に変えたもの。\n\n"
     "``a`` はウェーブレットの種類を ``D2``/``D4``/``D6``/``D8`` の 4 択で切り替える"
     "(タップ数が増えるほど滑らかで長いフィルタになる)。``b`` は未使用。"
 ),
 "xmh_soft": (
     "ソフト閾値処理(``mahotas.thresholding.soft_threshold``、シュリンケージ)。"
     "閾値未満の絶対値を持つ画素を 0 に潰し、それ以外は閾値分だけ 0 に近づける。"
     "ウェーブレット/スパース信号のノイズ除去でよく使う処理を画素値に直接適用する。\n\n"
     "``a`` は閾値(``a*0.5`` で 0〜0.5)を振る。``b`` は未使用。"
 ),
 "xmh_bwperim": (
     "領域の輪郭抽出(``mahotas.bwperim``)。二値領域から、背景と接する境界画素"
     "だけを残した 1 画素幅の輪郭を作る。\n\n"
     "``b`` が 0.5 より大きいと 8 連結、そうでなければ 4 連結で境界を判定する。"
     "``a`` は未使用。"
 ),
 "xmh_regmin": (
     "領域極小点の抽出(``mahotas.regmin``)。ガウシアン平滑化した画像に対し、"
     "局所的に最も暗い谷を領域としてマークする。分水嶺分割(watershed)のマーカー"
     "生成に使う典型的な前処理。\n\n"
     "``a`` は平滑化の強さ(σ、0.15〜3.15)を振る —— 大きくするほど微小なノイズ谷"
     "が消え、大きな谷だけが残る。``b`` は未使用。"
 ),
 "xmh_selfmatch": (
     "自己相似マップ(``mahotas.template_match`` による自己テンプレートマッチング)。"
     "画像中心から切り出した小さなパッチを画像全体に対してテンプレートマッチング"
     "し、パッチに似た場所ほど 1 に近い値になるよう正規化して返す。\n\n"
     "``a`` はパッチの半径(3+8 px 相当)を振る —— 大きくするほど広い範囲の類似度"
     "になる。``b`` は未使用。周期的なテクスチャや繰り返しパターンの検出に使える。"
 ),
 "xwt_subband_tile": (
     "1 段ウェーブレット分解(``pywt.dwt2``、Haar)の 4 サブバンド(近似 cA・水平 "
     "cH・垂直 cV・対角 cD)を 2x2 に敷き詰めて 1 枚の画像にし、min-max 正規化"
     "したもの。ウェーブレットピラミッド表示そのもの。\n\n"
     "``a``, ``b`` は未使用(分解は 1 段固定)。左上が低周波成分、右下が高周波"
     "成分になる。"
 ),
 "xwt_visushrink": (
     "VisuShrink 風のウェーブレットノイズ除去。``db4`` で 2 段分解し、各段の詳細"
     "係数をソフト閾値処理してから逆変換で再構成する(VisuShrink はこの閾値を"
     "ノイズ量から自動決定する手法だが、ここでは ``a`` で直接与える簡略版)。\n\n"
     "``a`` は閾値(``0.05+0.5*a`` で 0.05〜0.55)を振る —— 大きいほど強く平滑化"
     "されディテールが失われる。``b`` は未使用。出力は元画像サイズに切り詰めて "
     "[0,1] にクリップ。"
 ),
 "xwt_firm_denoise": (
     "ファーム閾値処理(firm/semisoft thresholding、``pywt.threshold_firm``)による"
     "ウェーブレットノイズ除去。ソフト閾値とハード閾値の中間の特性を持ち、``sym4`` "
     "で 2 段分解した各詳細係数に適用してから再構成する。\n\n"
     "``a`` は下側閾値(0.03〜0.23)、``b`` は上側閾値(下側+ε 以上、0.15〜0.55)を"
     "振る —— 下側未満は 0、上側以上はそのまま、中間は緩やかに減衰させる。"
     "xwt_visushrink よりディテールの急な打ち切りを避けたい場合に向く。"
 ),
 "xwt_detail_energy": (
     "ウェーブレット詳細成分のエネルギー比。``db2`` で 3 段分解し、全詳細係数"
     "(各段の水平/垂直/対角)の二乗平均の合計を、それに近似成分の二乗平均を足した"
     "全エネルギーで割った値を返す —— 高周波(テクスチャ/ノイズ/エッジ)が画像全体"
     "に占める割合の指標で、値域はおおむね [0,1)。\n\n"
     "``a``, ``b`` は未使用。値が大きいほどざらついた/エッジの多い画像、小さい"
     "ほど滑らかな画像であることを示す。"
 ),
 "xwt_hf_reconstruct": (
     "高周波再構成画像。``db2`` で 2 段分解し、近似係数(低周波成分)だけを 0 に"
     "潰してから逆変換で再構成する —— 結果はハイパスフィルタをかけたような、"
     "エッジとテクスチャだけが残る画像になる。再構成後に min-max 正規化する。\n\n"
     "``a``, ``b`` は未使用。"
 ),
 "xwt_lf_reconstruct": (
     "低周波再構成画像。``db2`` で分解し、全ての詳細係数を 0 に潰して近似成分"
     "だけから逆変換で再構成する —— ガウシアンぼかしに近い、多段ウェーブレットに"
     "よる平滑化画像になる。\n\n"
     "``a`` は分解段数(``1+int(a*3)`` で 1〜4 段)を振る —— 段数を増やすほど強く"
     "ぼける。``b`` は未使用。出力は [0,1] にクリップ。"
 ),
 "xwt_directional_detail": (
     "方向別エッジ検出。1 段の ``db2`` 分解から水平(cH)・垂直(cV)・対角(cD)の"
     "いずれか 1 つの詳細サブバンドを選び、絶対値を正規化してから元の解像度まで"
     "ブロック拡大(``kron`` で 2x2 複製)して返す。\n\n"
     "``b`` でどの方向を見るか選ぶ(``min(2,int(b*3))`` で cH→cV→cD の 3 択)。"
     "``a`` は未使用。サブバンドは元画像の半分の解像度なのでブロック状に拡大"
     "されることに注意(滑らかな拡大ではない)。"
 ),
 "xwt_packet_entropy": (
     "ウェーブレットパケットのエネルギー分散度(Shannon エントロピー)。``db1`` で"
     "深さ 2 のウェーブレットパケット分解を行い、16 個の葉サブバンドそれぞれの"
     "エネルギー(係数二乗和)を正規化した分布とみなし、そのシャノンエントロピーを "
     "``log2(16)`` で割って [0,1] に正規化する。\n\n"
     "``a``, ``b`` は未使用。値が 1 に近いほどエネルギーが全周波数帯に均等に分散"
     "(テクスチャが複雑)、0 に近いほど特定の帯域に集中(単純なパターンや平坦な"
     "領域)していることを示す。"
 ),
 "xwt_mra_component": (
     "多重解像度解析(MRA、``pywt.mra2``)の 1 段分の詳細成分。``db2`` で 3 段の "
     "MRA 分解を行うと、各段の水平/垂直/対角成分が元画像と同じ解像度の画像として"
     "得られる(通常のウェーブレット分解と違い縮小されない)。ここではそのうち "
     "1 段を選び、水平+垂直+対角を足し合わせた合成ディテール画像を min-max "
     "正規化して返す。\n\n"
     "``a`` はどの段を見るか(1〜3 段目、``min(3,1+int(a*3))``。近似成分[0 段目]"
     "は選ばれない)を振る。``b`` は未使用。段が大きいほど粗いスケールのディテール"
     "になる。"
 ),
 "xsitk_curvature_flow": (
     "曲率流平滑化(SimpleITK ``CurvatureFlow``)。等高線の曲率に比例した速度で"
     "画像をぼかす非線形拡散で、直線的なエッジは保たれやすく、丸まった細部から"
     "先に消えていく。\n\n"
     "``a`` は反復回数(``1+int(a*8)`` で 1〜9 回)を振る —— 増やすほど強く平滑化"
     "される。時間刻みは 0.0625 固定。``b`` は未使用。出力は [0,1] にクリップ。"
 ),
 "xsitk_minmax_curv_flow": (
     "Min/Max 曲率流平滑化(SimpleITK ``MinMaxCurvatureFlow``)。xsitk_curvature_flow "
     "と同じ曲率流に、近傍のミニマム/マキシマムに基づく判定を加えて小さな穴や"
     "スペックルノイズを埋めながら平滑化する変種。\n\n"
     "``a`` は反復回数(1〜9 回)、``b`` はステンシル半径(``1+int(b*2)`` で 1〜3、"
     "判定に使う近傍の広さ)を振る。時間刻みは 0.0625 固定。出力は [0,1] に"
     "クリップ。"
 ),
 "xsitk_curv_aniso_diff": (
     "曲率異方性拡散(SimpleITK ``CurvatureAnisotropicDiffusion``)。Perona-Malik "
     "型の異方性拡散の一種で、エッジ(勾配が大きい場所)では拡散を抑え、平坦な"
     "場所ではよく拡散させることでエッジを保ったまま平滑化する。\n\n"
     "``a`` は伝導度パラメータ(conductance、``0.5+4.5*a`` で 0.5〜5.0。大きい"
     "ほどエッジ判定が緩くなり強く拡散する)、``b`` は反復回数(1〜9 回)を振る。"
     "時間刻みは 0.0625 固定。出力は [0,1] にクリップ。"
 ),
 "xsitk_laplacian_sharpen": (
     "ラプラシアン鮮鋭化(SimpleITK ``LaplacianSharpening``)。画像からラプラシアン"
     "(2 階微分)を引くことでエッジを強調するアンシャープマスクの一種。結果を "
     "min-max 正規化して返す。\n\n"
     "パラメータは無く、``a``, ``b`` は未使用。"
 ),
 "xsitk_grayscale_fillhole": (
     "グレースケール穴埋め(SimpleITK ``GrayscaleFillhole``)。モルフォロジー"
     "再構成により、画像の暗い孔(周囲より暗い局所的な窪み)を周囲の明るさまで"
     "埋める。二値の穴埋めのグレースケール版で、しみ抜きや欠損補完の前処理に使う。"
     "\n\n"
     "パラメータは無く、``a``, ``b`` は未使用。出力は [0,1] にクリップ。"
 ),
 "xsitk_grayscale_grindpeak": (
     "グレースケール山削り(SimpleITK ``GrayscaleGrindPeak``、xsitk_grayscale_fillhole "
     "の双対)。モルフォロジー再構成により、周囲より明るい局所的な山(ピーク)を"
     "周囲の高さまで削り落とす。ハイライトのスパイク除去に使う。\n\n"
     "パラメータは無く、``a``, ``b`` は未使用。出力は [0,1] にクリップ。"
 ),
 "xsitk_opening_by_recon": (
     "再構成によるオープニング(SimpleITK ``OpeningByReconstruction``)。通常の"
     "グレースケールオープニング(収縮→膨張)と異なり、収縮後の膨張をマスク付き"
     "再構成で行うため、残った領域の輪郭を歪めずに小さな明るい突起だけを除去"
     "できる。\n\n"
     "``a`` は構造要素の半径(``1+int(a*4)`` で両軸とも 1〜5)を振る。``b`` は"
     "未使用。出力は [0,1] にクリップ。"
 ),
 "xsitk_closing_by_recon": (
     "再構成によるクロージング(SimpleITK ``ClosingByReconstruction``、"
     "xsitk_opening_by_recon の双対)。膨張後の収縮をマスク付き再構成で行い、"
     "輪郭を保ったまま小さな暗い窪みだけを埋める。\n\n"
     "``a`` は構造要素の半径(1〜5)を振る。``b`` は未使用。出力は [0,1] に"
     "クリップ。"
 ),
 "xsitk_signed_maurer_dist": (
     "符号付き距離マップ(SimpleITK ``SignedMaurerDistanceMap``)を tanh で "
     "[0,1] に押し込んだもの。二値領域の境界からの距離(内側/外側とも)を、"
     "境界付近ほど 0.5 から離れる連続値の画像として表す。\n\n"
     "``a`` は tanh のスケール(``1.0+9.0*a`` で 1〜10。大きいほど遷移が緩やかで"
     "広い範囲がグレーになる)を振る。``b`` は未使用。距離を画素座標のスケール"
     "で解釈する点、符号(内側/外側どちらが正か)は SimpleITK のデフォルト規約に"
     "従う点に注意。"
 ),
 "xsitk_connected_threshold": (
     "連結閾値領域拡張(SimpleITK ``ConnectedThreshold``、region growing)。画像"
     "中心の画素を種(シード)にし、その画素値を中心とした強度区間内で中心と"
     "連結している画素だけを領域として拡張する。\n\n"
     "``a`` は下限マージン(``0.1+0.3*a``)、``b`` は上限マージン(``0.1+0.3*b``)"
     "を振る —— 区間は [中心値-下限, 中心値+上限]。画像中心付近に対象があること"
     "を前提とした op。"
 ),
 "xsitk_confidence_connected": (
     "信頼区間連結領域拡張(SimpleITK ``ConfidenceConnected``)。画像中心を種にし、"
     "現在の領域内の平均・標準偏差から「平均 ± multiplier * 標準偏差」の区間を"
     "作り、それを反復的に更新しながら連結領域を広げていく(xsitk_connected_threshold "
     "より統計的な閾値の決め方)。\n\n"
     "``a`` は反復回数(``1+int(a*5)`` で 1〜6)、``b`` は標準偏差の倍率"
     "(``1.0+3.0*b`` で 1〜4)を振る。初期近傍半径は 2 固定。画像中心付近に"
     "対象があることを前提とした op。"
 ),
 "xsitk_maxentropy_thresh": (
     "最大エントロピー法による二値化(SimpleITK ``MaximumEntropyThreshold``、"
     "Kapur の方法)。ヒストグラムを前景/背景の 2 クラスに分けたときのエントロピー"
     "和が最大になる閾値を選ぶ大域二値化。\n\n"
     "``a`` はヒストグラムのビン数(``int(64+192*a)`` で 64〜256)を振る —— 粗い"
     "ほど閾値が安定するが微妙な階調差は無視される。``b`` は未使用。"
 ),
 "xsitk_moments_thresh": (
     "モーメント保存法による二値化(SimpleITK ``MomentsThreshold``、Tsai の方法)。"
     "二値化後のヒストグラムの統計モーメント(平均・分散など)が元のヒストグラム"
     "のものと一致するように閾値を選ぶ。\n\n"
     "``a`` はヒストグラムのビン数(64〜256)を振る。``b`` は未使用。"
     "xsitk_maxentropy_thresh・xsitk_huang_thresh とは閾値選択の基準が異なる"
     "だけで、同じ入出力形。"
 ),
 "xsitk_huang_thresh": (
     "Huang のファジィエントロピー法による二値化(SimpleITK ``HuangThreshold``)。"
     "ファジィ集合として見た前景/背景のあいまいさ(ファジィエントロピー)が最小に"
     "なる閾値を選ぶ。\n\n"
     "``a`` はヒストグラムのビン数(64〜256)を振る。``b`` は未使用。"
     "xsitk_maxentropy_thresh・xsitk_moments_thresh の姉妹 op。"
 ),
 "xsk3_rank_otsu": (
     "局所大津二値化(skimage ``filters.rank.otsu``)。近傍円盤内だけで大津の"
     "判別分析法(Otsu's method)の閾値を求め、画素値がその局所閾値を上回るかで"
     "二値化する —— 大域大津と違い、照明ムラのある画像でも局所的に妥当な閾値が"
     "選べる。\n\n"
     "``a`` は円盤半径(``2+int(a*8)`` で 2〜10)を振る。``b`` は未使用。"
 ),
 "xsk3_rank_majority": (
     "局所多数決フィルタ(skimage ``filters.rank.majority``)。xmh_majority と"
     "同じ多数決平滑化の skimage 版で、円盤近傍内で過半数の画素が 1 なら 1 に"
     "する。\n\n"
     "``a`` は円盤半径(``1+int(a*3)`` で 1〜4)を振る。``b`` は未使用。"
 ),
 "xsk3_rank_subtract_mean": (
     "局所平均差分(skimage ``filters.rank.subtract_mean``)。各画素からその円盤"
     "近傍の平均輝度を引いた差分を返す。skimage の実装はアンダーフロー防止の"
     "ため差分を 1/2 に縮小しレンジ中央へシフトする仕様になっている。大域的な"
     "明暗ムラを打ち消しローカルコントラストを強調する。\n\n"
     "``a`` は円盤半径(``1+int(a*4)`` で 1〜5)を振る。``b`` は未使用。8bit 量子化"
     "を経由するため元の float64 精度は失われる。"
 ),
 "xsk3_rank_equalize": (
     "局所ヒストグラム均等化(skimage ``filters.rank.equalize``)。円盤近傍ごとに"
     "ヒストグラム均等化を行う適応的コントラスト強調で、大域的な ``equalize`` op "
     "より局所的な明暗ムラに強い。\n\n"
     "``a`` は円盤半径(``2+int(a*8)`` で 2〜10)を振る —— 大きいほど大域的な"
     "均等化に近づく。``b`` は未使用。"
 ),
 "xsk3_rank_mean_bilateral": (
     "局所バイラテラル平均(skimage ``filters.rank.mean_bilateral``)。円盤近傍の"
     "うち、中心画素の値から下方 ``s0``〜上方 ``s1`` の範囲に収まる画素だけを"
     "平均する、エッジ保存型の平滑化。\n\n"
     "``a`` は円盤半径(``2+int(a*6)`` で 2〜8)と下方許容幅 ``s0``"
     "(``int(10+40*a)`` で 10〜50)の両方を兼ねる。``b`` は上方許容幅 ``s1``"
     "(``int(10+40*b)`` で 10〜50)を振る。"
 ),
 "xsk3_h_minima": (
     "h-極小変換(skimage ``morphology.h_minima``)。深さが ``h`` 未満の浅い谷"
     "(局所極小)を平坦化してから残った極小点を二値マークする —— xmh_regmin と"
     "似た谷を拾う処理だが、深さでノイズ由来の浅い谷を明示的に除外できる。\n\n"
     "``a`` は深さしきい値 ``h``(``0.05+0.3*a`` で 0.05〜0.35)を振る。``b`` は"
     "未使用。"
 ),
 "xsk3_area_closing": (
     "面積クロージング(skimage ``morphology.area_closing``)。面積が閾値未満の"
     "暗い領域(窪み)だけを埋める、サイズベースのモルフォロジー演算 —— 通常の"
     "クロージングと違い構造要素の形状ではなく連結成分の面積で対象を選ぶ。\n\n"
     "``a`` は面積閾値(``int(16+a*100)`` で 16〜116 画素)を振る。``b`` は未使用。"
 ),
 "xsk3_diameter_closing": (
     "直径クロージング(skimage ``morphology.diameter_closing``)。xsk3_area_closing "
     "の面積の代わりに、連結成分の外接矩形の対角線長(直径)で対象を選ぶ"
     "クロージング —— 細長い構造には直径基準、丸い構造には面積基準が向く、と"
     "使い分けられる。\n\n"
     "``a`` は直径閾値(``4+int(a*30)`` で 4〜34 画素)を振る。``b`` は未使用。"
 ),
 "xsk3_corner_moravec": (
     "Moravec コーナー検出(skimage ``feature.corner_moravec``)。各画素を中心と"
     "した小窓を上下左右斜めにずらしたときの画素値差の最小値をコーナー強度と"
     "する、最も古典的なコーナー検出の一つ(Harris/Shi-Tomasi の前身)。結果は"
     "最大絶対値で正規化。\n\n"
     "``a`` は窓サイズ(``1+2*int(a*2)`` で 1・3・5 のいずれか)を振る。``b`` は"
     "未使用。方向依存の格子模様に弱いという Moravec 法自体の既知の弱点を"
     "引き継ぐ。"
 ),
 "xsk3_corner_fast": (
     "FAST コーナー検出(skimage ``feature.corner_fast``)。中心画素の周囲の円周"
     "上の画素と比較し、連続して明るい/暗い画素が一定数以上続く場所をコーナー"
     "として検出する高速な手法。結果は最大絶対値で正規化した応答マップ。\n\n"
     "``a`` は連続画素数のしきい値 ``n``(``9+int(a*3)`` で 9〜12)、``b`` は輝度差"
     "のしきい値(``0.05+0.2*b`` で 0.05〜0.25)を振る。"
 ),
 "xsk3_integral_image": (
     "積分画像(summed-area table、skimage ``transform.integral_image``)。原点"
     "から各画素までの累積和を格納した画像で、任意矩形領域の合計をたった 4 点の"
     "参照で計算できるようにする、Haar 特徴量や矩形フィルタの高速化に使う古典的な"
     "下ごしらえ。最大値で正規化して表示用に潰している。\n\n"
     "``a``, ``b`` は未使用。値そのものは単調非減少で、右下に行くほど明るくなる"
     "見た目になる(画像としての意味は薄く、内部データ構造の可視化に近い)。"
 ),
 "xsk3_threshold_local_median": (
     "局所中央値適応的二値化(skimage ``filters.threshold_local`` の "
     "``method='median'``)。ブロックごとの中央値を局所閾値とし、画素値がそれを"
     "上回るかで二値化する。局所平均を使う版よりも外れ値(ノイズ画素)に強い。"
     "\n\n"
     "``a`` はブロックサイズ(``2*int(a*6)+3`` で 3〜15 の奇数)を振る。``b`` は"
     "未使用。"
 ),
 "xsk3_is_low_contrast": (
     "低コントラスト画像判定(skimage ``exposure.is_low_contrast``)。画像の輝度"
     "レンジが取りうる全レンジの ``fraction_threshold`` 未満しか使っていないかを"
     "判定する真偽値を、0.0/1.0 の feature として返す。\n\n"
     "``a`` は判定基準の割合(``0.05+0.4*a`` で 0.05〜0.45)を振る —— 大きくする"
     "ほど低コントラストと判定されやすくなる。``b`` は未使用。露出不足/白飛びの"
     "自動検知に使える。"
 ),
 "xsk3_estimate_sigma": (
     "ノイズ標準偏差の推定(skimage ``restoration.estimate_sigma``、ウェーブレット"
     "係数の中央絶対偏差(MAD)に基づく Donoho の推定量)。推定値を 5 倍したのち "
     "1.0 で頭打ちにして feature として返す。\n\n"
     "``a``, ``b`` は未使用。デノイズ強度(例えば閾値処理のパラメータ)を画像"
     "ごとに自動決定したい場合の目安に使える。"
 ),
 "xsk3_peak_local_max": (
     "局所極大点マップ(skimage ``feature.peak_local_max``)。互いに "
     "``min_distance`` 画素以上離れた局所輝度極大の座標を検出し、その座標だけを "
     "1 にした疎な二値画像(1 画素ずつの点で、面としての領域ではない)を返す。"
     "\n\n"
     "``a`` は最小距離(``2+int(a*8)`` で 2〜10)を振る —— 大きくするほど検出"
     "される点が減り、より支配的なピークだけが残る。``b`` は未使用。"
 ),
 "xcv3_denoise_tvl1": (
     "全変動 L1 ノイズ除去(OpenCV ``cv2.denoise_TVL1``、Primal-Dual アルゴリズム)。"
     "エッジを保ちながらノイズを除去する全変動最小化に基づく手法で、通常の"
     "ガウシアン平滑化よりエッジがシャープに残る。\n\n"
     "``a`` は正則化項の重み ``lambda``(``0.3+2.7*a`` で 0.3〜3.0。小さいほど"
     "強く平滑化される)、``b`` は反復回数(``int(10+40*b)`` で 10〜50)を振る。"
     "8bit 量子化を経由するため入力の float64 精度は失われる。"
 ),
 "xcv3_inpaint_ns": (
     "Navier-Stokes 法によるインペインティング(OpenCV ``cv2.inpaint``、"
     "``INPAINT_NS``)。周辺画素から流体力学的に情報を伝搬させて欠損領域を埋める"
     "修復アルゴリズム。\n\n"
     "このレシピはマスクを外部から受け取らず、画像自身の中で輝度が 235 超"
     "(白飛び)または 20 未満(黒つぶれ)の画素を自動的に欠損とみなして半径 3 px "
     "でインペイントする。``a``, ``b`` は未使用。任意のマスクで穴埋めしたい"
     "用途には使えない点に注意。"
 ),
 "xcv3_pyr_laplacian": (
     "ラプラシアンピラミッドによる鮮鋭化。``pyrDown`` で縮小してから ``pyrUp`` "
     "で戻した画像(低周波成分)を元画像から引いた差分(ラプラシアンピラミッドの "
     "1 層、バンドパス成分に相当)を、元画像に加算して強調するアンシャープ"
     "マスクの一種。\n\n"
     "``a`` は強調係数(``0.5+2.5*a`` で 0.5〜3.0)を振る —— 大きいほど強く"
     "シャープになる(オーバーシュートも増える)。``b`` は未使用。結果は [0,1] "
     "にクリップ。"
 ),
 "xcv3_gray_hu1": (
     "グレースケール画像の第 1 Hu 不変モーメント(OpenCV "
     "``cv2.HuMoments(cv2.moments(...))[0,0]``)。画像を二値形状ではなく濃淡"
     "そのものを質量分布とみなしたときの、回転・拡大縮小・平行移動に不変な"
     "広がり具合を表す特徴量(2 次の中心モーメントに基づく)。1.0 で頭打ち。\n\n"
     "``a``, ``b`` は未使用。二値領域の形状記述に使う通常の Hu モーメントとは"
     "異なり、濃淡値をそのまま重みとして使う点に注意。"
 ),
 "xcv3_sift_count": (
     "SIFT 特徴点数(OpenCV ``cv2.SIFT_create().detect``)。画像から検出された"
     "スケール不変特徴点(SIFT keypoints)の個数を feature として返す —— テクス"
     "チャの複雑さ/マッチングに使える特徴点の豊富さの指標になる。\n\n"
     "``a`` は検出上限数 ``nfeatures``(``int(50+450*a)`` で 50〜500)を振る —— "
     "上限に達するまでは実際の検出数がそのまま返るので、上限に張り付いていない"
     "か確認が要る。``b`` は未使用。"
 ),
 "xcv3_brisk_count": (
     "BRISK 特徴点数(OpenCV BRISK 検出器)。二値記述子ベースの高速特徴点検出器"
     "で検出されたキーポイント数を feature として返す。\n\n"
     "``a`` は検出閾値 ``thresh``(``int(10+60*a)`` で 10〜70。高いほど検出数が"
     "減る)を振る。``b`` は未使用。実装注記: cv2 5.0.0 で ``BRISK_create`` が "
     "``cv2.xfeatures2d`` に移動したため、両方の場所を ``getattr`` で試す互換"
     "コードになっている。"
 ),
 "xcv3_agast_count": (
     "AGAST 特徴点数(OpenCV AGAST 検出器、FAST の適応的木構造版)。検出された"
     "キーポイント数を feature として返す。\n\n"
     "``a`` は検出閾値(``int(5+40*a)`` で 5〜45。高いほど検出数が減る)を振る。"
     "``b`` は未使用。実装注記: cv2 5.0.0 で ``AgastFeatureDetector_create`` が "
     "``cv2.xfeatures2d`` に移動したため、両方の場所を ``getattr`` で試す互換"
     "コードになっている(xcv3_brisk_count と同じ事情)。"
 ),
 "xcv3_lsd_count": (
     "検出直線分の本数(OpenCV ``cv2.createLineSegmentDetector`` による Line "
     "Segment Detector、LSD)。画像中から検出された直線セグメントの本数を "
     "feature として返す(検出 0 件のとき ``None`` が返る実装のため、その場合"
     "は 0 として扱う)。\n\n"
     "``a``, ``b`` は未使用。エッジの直線的な構造の多さ(建築物、部品の輪郭など)"
     "を数える指標になる。"
 ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    for name, r in RECIPES.items():
        try:
            fn = _make(r["recipe"], r.get("out"))
            raw = _make_raw(r["recipe"])
        except Exception:
            continue
        if _gate(fn, r["in"], r["out"], raw):            # drop non-functional recipes (env-dependent)
            out.append(Op(name, r.get("cat") or "extra", "", r["in"], r["out"], fn))
    build.dropped = [n for n in RECIPES if n not in {o.name for o in out}]
    return out


build.dropped = []
