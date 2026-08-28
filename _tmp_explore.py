# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, r"C:\dev\projects\imgevolve")
import numpy as np
import match3d as M

N = 40
zz, yy, xx = np.mgrid[0:N, 0:N, 0:N].astype(np.float64)

# ---- polynomial field: sobel & hessian exact ----
a, b, c = 0.7, -1.3, 0.4
al, be, ga = 0.11, -0.23, 0.17
de, ep, ze = 0.05, -0.09, 0.13
f = (a*zz + b*yy + c*xx
     + 0.5*(al*zz**2 + be*yy**2 + ga*xx**2)
     + de*zz*yy + ep*zz*xx + ze*yy*xx)

gz, gy, gx = M.sobel3d(f)
gz = gz[0,0].numpy(); gy = gy[0,0].numpy(); gx = gx[0,0].numpy()
# analytic gradient
Az = a + al*zz + de*yy + ep*xx
Ay = b + be*yy + de*zz + ze*xx
Ax = c + ga*xx + ep*zz + ze*yy
sl = slice(3, N-3)
print("sobel gz/32 vs analytic max err:",
      np.max(np.abs(gz[sl,sl,sl]/32 - Az[sl,sl,sl])))
print("sobel gy/32 err:", np.max(np.abs(gy[sl,sl,sl]/32 - Ay[sl,sl,sl])))
print("sobel gx/32 err:", np.max(np.abs(gx[sl,sl,sl]/32 - Ax[sl,sl,sl])))

fzz,fyy,fxx,fzy,fzx,fyx = [h.numpy() for h in M.hessian3d(f)]
print("hess fzz err:", np.max(np.abs(fzz[sl,sl,sl]-al)))
print("hess fyy err:", np.max(np.abs(fyy[sl,sl,sl]-be)))
print("hess fxx err:", np.max(np.abs(fxx[sl,sl,sl]-ga)))
print("hess fzy err:", np.max(np.abs(fzy[sl,sl,sl]-de)))
print("hess fzx err:", np.max(np.abs(fzx[sl,sl,sl]-ep)))
print("hess fyx err:", np.max(np.abs(fyx[sl,sl,sl]-ze)))

# ---- Gaussian ball: curvature ----
cz=cy=cx=(N-1)/2.0
r = np.sqrt((zz-cz)**2+(yy-cy)**2+(xx-cx)**2)
sigma=6.0
blob = np.exp(-r**2/(2*sigma**2))
S, curv, mask, gmag = [t.numpy() for t in M.curvature_maps(blob, mc=1e-4)]
shell = (r>4.5)&(r<7.5)&(mask>0.5)
print("shell voxels:", shell.sum())
print("S median on shell:", np.median(S[shell]), "min", np.percentile(S[shell],10))
print("curvedness median:", np.median(curv[shell]), "expected 1/r for r in shell ~", 1/np.median(r[shell]))
print("curv vs 1/r rel err median:", np.median(np.abs(curv[shell]-1/r[shell])/(1/r[shell])))

# ---- EDT from center seed ----
seed = np.zeros((N,N,N), bool)
seed[int(round(cz)), int(round(cy)), int(round(cx))] = True
edt = M.edt_jfa(seed).numpy()
r_from_seed = np.sqrt((zz-round(cz))**2+(yy-round(cy))**2+(xx-round(cx))**2)
print("EDT max err vs analytic euclid:", np.max(np.abs(edt - r_from_seed)))
cheb = np.maximum.reduce([np.abs(zz-round(cz)),np.abs(yy-round(cy)),np.abs(xx-round(cx))])
print("EDT vs chebyshev max diff:", np.max(np.abs(edt-cheb)))

# ---- black-hat: dark cavity ----
vol = np.ones((N,N,N), np.float32)
# small dark cube cavity size 1 (single voxel) interior
hz,hy,hx = 12,25,17
hole = np.zeros((N,N,N), bool)
hole[hz,hy,hx]=True
vol[hole]=0.0
bh = M.morph_blackhat3d(vol, r=1)
print("blackhat at hole:", bh[hz,hy,hx], "max elsewhere:", bh[~hole].max())
print("blackhat allclose hole mask:", np.allclose(bh, hole.astype(np.float32)))
# hole-free null
bh0 = M.morph_blackhat3d(np.ones((N,N,N),np.float32), r=1)
print("blackhat hole-free max:", np.abs(bh0).max())
# top-hat on same (should be ~0, dark structure not caught by white top-hat)
th = M.morph_tophat3d(vol, r=1)
print("tophat on dark-hole vol max:", np.abs(th).max())
print("DONE")
