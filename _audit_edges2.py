import numpy as np, edges3d as E
from scipy.ndimage import gaussian_laplace, binary_erosion, binary_dilation

print("=== LoG step thickness ===")
v=np.zeros((24,24,24)); v[:,:,12:]=1.0
zc=E.log_zero_crossings(v,sigma=1.5)
# per (z,y) line along x, how many crossings?
counts=zc.sum(axis=2)
print("LoG per-x-line crossing counts unique:",np.unique(counts))
xs=np.argwhere(zc)[:,2]
print("crossing x positions unique:",np.unique(xs))

print("\n=== exact-zero-at-grid-point gap scenario ===")
# antisymmetric step so LoG is antisymmetric about integer boundary -> L exactly 0 on that plane
N=32
v=np.zeros((N,N,N))
xax=np.arange(N)
prof=np.sign(xax-16.0)   # -1 for x<16, 0 at x==16, +1 for x>16
v[:]=prof[None,None,:]
L=gaussian_laplace(v,sigma=2.0,mode="nearest")
print("min|L| at plane x=16:",np.abs(L[:,:,16]).max(), "exact zeros at x=16:",int((L[:,:,16]==0).sum()))
zc=E.log_zero_crossings(v,sigma=2.0)
print("crossings near x=16? column sums x=14..18:",[int(zc[:,:,k].sum()) for k in range(14,19)])
print("total crossings:",int(zc.sum()))
# Is the boundary detected at all on each (y,z) line?
lines_with_edge=(zc.sum(axis=2)>0).mean()
print("fraction of (z,y) lines with >=1 crossing:",lines_with_edge)

print("\n=== canny on sphere shell (curved boundary) ===")
n=48; c=24; rad=14
zz,yy,xx=np.indices((n,n,n),dtype=float)
r=np.sqrt((zz-c)**2+(yy-c)**2+(xx-c)**2)
vol=(r<=rad).astype(float)
gmag,_=E.gradient3d(vol,sigma=1.2)
edges=E.canny3d(vol,0.1*gmag.max(),0.3*gmag.max(),sigma=1.2)
block=vol>0.5
surface=block & ~binary_erosion(block)
covered=surface & binary_dilation(edges,iterations=2)
print("sphere recall:",covered.sum()/surface.sum())
interior=binary_erosion(block,iterations=3)
print("sphere interior edge rate:",edges[interior].mean())
print("edges total:",int(edges.sum()),"thick:",int((gmag>=0.1*gmag.max()).sum()))
