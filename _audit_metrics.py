import numpy as np, metrics3d as M

print("=== metrics3d adversarial ===")

# 1. Empty input behavior
try:
    r = M.chamfer_distance(np.zeros((0,3)), np.random.rand(5,3))
    print("chamfer empty a:", r)
except Exception as e:
    print("chamfer empty a raised:", type(e).__name__, e)

# 2. squared chamfer closed form: two single points at distance d
a = np.array([[0.,0,0]]); b = np.array([[3.,4,0]])  # dist 5
print("chamfer unsquared (expect 5):", M.chamfer_distance(a,b))
print("chamfer squared (expect 25):", M.chamfer_distance(a,b,squared=True))

# 3. accuracy strict-< boundary: point exactly at tau
a = np.array([[0.,0,0]]); b = np.array([[1.,0,0]])  # dist exactly 1
print("accuracy tau=1.0 (dist==tau, strict< -> 0):", M.accuracy(a,b,1.0))
print("accuracy tau=1.0000001 -> 1:", M.accuracy(a,b,1.0000001))

# 4. pose_error with improper/noisy rotation and reflection
# Known: 90 deg about x
th=np.radians(90)
Rx=np.array([[1,0,0],[0,np.cos(th),-np.sin(th)],[0,np.sin(th),np.cos(th)]])
print("pose_error rot (expect 90):", M.pose_error(np.eye(3),np.zeros(3),Rx,np.zeros(3))[0])

# 5. voxel_iou with iso and negative/float volumes
a=np.array([[[0.6]]]); b=np.array([[[0.4]]])
print("voxel_iou 0.6 vs 0.4 iso .5 (expect union1 inter0 ->0):", M.voxel_iou(a,b))

# 6. fscore harmonic when one is zero
a=np.array([[0.,0,0]]); b=np.array([[100.,0,0]])
print("fscore far (expect 0,0,0):", M.fscore(a,b,tau=0.1))

# 7. rmse mismatch shape
try:
    M.rmse_correspondence(np.zeros((3,3)), np.zeros((4,3)))
except ValueError as e:
    print("rmse shape mismatch raises ValueError OK")

# 8. hausdorff empty
try:
    print("hausdorff empty:", M.hausdorff_distance(np.zeros((0,3)), np.ones((3,3))))
except Exception as e:
    print("hausdorff empty raised:", type(e).__name__)
