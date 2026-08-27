import numpy as np, edges3d as E
from scipy.ndimage import gaussian_laplace
np.seterr(all='ignore')

print("=== SDF sphere: surface through grid points ===")
n=48; c=23.5; R=15.0
zz,yy,xx=np.indices((n,n,n),dtype=float)
r=np.sqrt((zz-c)**2+(yy-c)**2+(xx-c)**2)
sdf=r-R   # signed distance: 0 on the sphere surface (negative inside)
# count voxels where sdf is ~exactly on surface
zc=E.log_zero_crossings(sdf,sigma=1.5)
print("SDF sphere crossings:",int(zc.sum()))
# how many surface voxels does it recover vs a shell reference
shell=(np.abs(sdf)<1.0)
from scipy.ndimage import binary_dilation
covered=shell & binary_dilation(zc,iterations=1)
print("shell coverage by crossings:",covered.sum()/max(1,shell.sum()))

print("\n=== controlled: crossing exactly on grid vs half-grid ===")
for center in [16.0, 16.5]:
    N=32
    xr=np.arange(N,dtype=float)
    prof=np.tanh((xr-center)*0.7)   # smooth signed field, zero at 'center'
    v=np.zeros((8,8,N)); v[:]=prof[None,None,:]
    L=gaussian_laplace(v,sigma=1.5,mode="nearest")
    zc=E.log_zero_crossings(v,sigma=1.5)
    on_grid = (center==round(center))
    # find x positions of crossings
    xs=np.unique(np.argwhere(zc)[:,2]) if zc.any() else []
    print(f"center={center} (on-grid={on_grid}): crossings total={int(zc.sum())} xs={list(xs)} "
          f"min|L| near center={np.abs(L[:,:,int(round(center))]).max():.2e}")
