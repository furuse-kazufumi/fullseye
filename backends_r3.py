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

def _make(recipe):
    # Vetted, agent-verified one-line recipes over our own libraries. Compiled once;
    # everything lives in `globals` so nested lambdas/comprehensions resolve np/v/a/b.
    code = compile(recipe, "<recipe>", "eval")

    def fn(v, a, b):
        try:
            g = dict(_NS)
            g.update(v=v, a=float(a), b=float(b))
            return eval(code, g)
        except Exception:
            return v
    return fn


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
  "recipe": "float(np.mean(mahotas.features.pftas((np.clip(v,0,1)*255).astype(np.uint8))))",
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
  "recipe": "(lambda x,t:(lambda r:1.0-(r-r.min())/(np.ptp(r)+1e-12))(mahotas.template_match(x,t)))(np.clip(v,0,1).astype(float), np.clip(v,0,1).astype(float)[v.shape[0]//2-3-int(a*8):v.shape[0]//2+4+int(a*8), v.shape[1]//2-3-int(a*8):v.shape[1]//2+4+int(a*8)])",
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
  "recipe": "(lambda c: np.clip(pywt.waverec2([c[0]]+[tuple(pywt.threshold_firm(d,0.03+0.2*a,0.15+0.4*b) for d in lvl) for lvl in c[1:]],'sym4')[:v.shape[0],:v.shape[1]],0,1))(pywt.wavedec2(np.clip(v,0,1),'sym4',level=2))",
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
  "recipe": "float(len(cv2.BRISK_create(thresh=int(10+60*a)).detect((np.clip(v,0,1)*255).astype(np.uint8),None)))",
  "cat": "features"
 },
 "xcv3_agast_count": {
  "in": "image",
  "out": "feature",
  "recipe": "float(len(cv2.AgastFeatureDetector_create(threshold=int(5+40*a)).detect((np.clip(v,0,1)*255).astype(np.uint8),None)))",
  "cat": "features"
 },
 "xcv3_lsd_count": {
  "in": "image",
  "out": "feature",
  "recipe": "float(0 if (l:=cv2.createLineSegmentDetector().detect((np.clip(v,0,1)*255).astype(np.uint8))[0]) is None else len(l))",
  "cat": "features"
 }
}



def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []
    for name, r in RECIPES.items():
        try:
            fn = _make(r["recipe"])
        except Exception:
            continue
        out.append(Op(name, r.get("cat") or "extra", "", r["in"], r["out"], fn))
    return out
