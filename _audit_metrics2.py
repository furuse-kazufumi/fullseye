import numpy as np, metrics3d as M
np.seterr(all='ignore')

print("=== metrics3d shape/robustness ===")
# 1. voxel_iou with DIFFERENT shapes -> broadcasting?
a=np.ones((10,10,10)); b=np.ones((8,8,8))
try:
    print("voxel_iou diff shape:",M.voxel_iou(a,b))
except Exception as e:
    print("voxel_iou diff shape raised:",type(e).__name__, str(e)[:60])

# broadcastable mismatch (silent wrong answer)
a=np.ones((10,1,10)); b=np.ones((1,10,10))
try:
    print("voxel_iou broadcastable (10,1,10)vs(1,10,10):",M.voxel_iou(a,b))
except Exception as e:
    print("raised:",type(e).__name__)

# 2. voxel_dice different total vs identical
a=np.zeros((4,4,4)); a[:2]=1
b=np.zeros((4,4,4)); b[:2]=1
print("dice identical (expect 1):",M.voxel_dice(a,b))

# 3. normal_consistency with orthogonal normals (expect 0) and antiparallel (expect 1)
p=np.array([[0.,0,0],[1,0,0]])
na=np.array([[1.,0,0],[1,0,0]])
nb=np.array([[0.,1,0],[-1,0,0]])   # first orthogonal(cos0), second antiparallel(|cos|=1)
print("normal_consistency mix (expect mean(0,1)=0.5):",M.normal_consistency(p,na,p,nb))

# 4. pose_error with reflection (improper rotation, det=-1)
Ref=np.diag([1.0,1,-1])  # reflection
rot,tr=M.pose_error(np.eye(3),np.zeros(3),Ref,np.zeros(3))
print("pose_error vs reflection (det=-1): rot=",rot,"(arccos of (trace-1)/2, trace=1 ->0deg?!)")
print("  trace(Ref)=",np.trace(Ref),"-> cos=(1-1)/2=0 -> 90deg. actual:",rot)

# 5. single-point clouds chamfer
print("chamfer single pts (0,0,0)-(1,0,0):",M.chamfer_distance(np.array([[0.,0,0]]),np.array([[1.,0,0]])))
