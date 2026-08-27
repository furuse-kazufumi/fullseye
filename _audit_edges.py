import numpy as np, edges3d as E
from scipy.ndimage import gaussian_laplace

print("=== edges3d adversarial ===")

# 1. gradient3d multi-axis linear field: vol = 3z+5y+7x -> grad (3,5,7)
D,H,W=12,12,12
zz,yy,xx=np.indices((D,H,W),dtype=float)
vol=3*zz+5*yy+7*xx
gmag,gvec=E.gradient3d(vol,sigma=0.0)
inner=(slice(1,-1),)*3
print("grad interior mean gvec:",gvec[inner].reshape(-1,3).mean(0),"(expect [3,5,7])")

# 2. LoG exact-zero grid point => crossing MISSED?
# Build 1D profile where LoG is exactly zero at a voxel.
# Use antisymmetric ramp so LoG crosses zero on a grid point.
v=np.zeros((8,8,16))
for i in range(16):
    v[:,:,i]=(i-7.5)   # linear ramp in x; LoG ~ 0 everywhere (linear) -> flat, skip
# Instead craft L directly is hard; test practical step:
v2=np.zeros((24,24,24)); v2[:,:,12:]=1.0
L=gaussian_laplace(v2,sigma=1.5,mode="nearest")
# how many grid voxels have L exactly 0?
print("exact-zero LoG voxels in step:",int((L==0).sum()))

# 3. NMS thinness on a DIAGONAL bright plane (normal along (0,1,1)/sqrt2)
n=40
zz,yy,xx=np.indices((n,n,n),dtype=float)
# signed distance to a plane through center with normal (0,1,1)
s=((yy-20)+(xx-20))/np.sqrt(2)
vol=(s>=0).astype(float)   # step across diagonal plane
gmag,_=E.gradient3d(vol,sigma=1.0)
edges=E.canny3d(vol,0.1*gmag.max(),0.3*gmag.max(),sigma=1.0)
thick=(gmag>=0.1*gmag.max())
print(f"diagonal plane: edges={edges.sum()} thick={thick.sum()} ratio={edges.sum()/thick.sum():.3f}")
# thickness along normal: sample a line through center along (0,1,1)
# count edge voxels within a central sub-region per slice
mid=edges[20]  # a z-slice (D,H)=(y,x)? edges shape (n,n,n) index [z,y,x]
# along the anti-diagonal check thickness
cnt=[]
for yv in range(5,35):
    row=edges[20,yv,:]
    if row.any(): cnt.append(int(row.sum()))
print("diagonal edge per-row counts (y=5..34) sample:",cnt[:10],"... max",max(cnt) if cnt else 0)

# 4. canny3d thin 1-voxel bright SHEET (plane of thickness 1). Two gradients close together.
vol=np.zeros((20,20,20)); vol[:, :, 10]=1.0   # single bright plane at x=10
gmag,_=E.gradient3d(vol,sigma=1.0)
edges=E.canny3d(vol,0.1*gmag.max(),0.3*gmag.max(),sigma=1.0)
line=edges[10,10,:]
print("thin sheet edges on x-line:",np.where(line)[0],"(bright plane at x=10)")

# 5. link_edges labels.max()==n when empty
lab,nn=E.link_edges(np.zeros((4,4,4),bool))
print("empty link_edges n=",nn,"labels.max=",lab.max())

# 6. edge_points dtype and roundtrip on random mask
m=np.zeros((5,5,5),bool); m[1,2,3]=True; m[4,0,0]=True
pts=E.edge_points(m); print("edge_points:",pts.tolist())
