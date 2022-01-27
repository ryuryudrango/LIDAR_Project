import statistics
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
import open3d as o3
import math
import chair_parameter as param


def calc_distance(inputFrame):
    return (inputFrame["X"] ** 2 + inputFrame["Y"] ** 2 + inputFrame["Z"] ** 2) ** 0.5


m = 3
# 0→boxBinBrikets,1→box1,2→box2,3→chair,4→crane,5→rubbishBin,
# 6→rubbishBin_bricks,7→two_Bricks
sourceData = pd.read_csv(param.readData_multi[3] % str(m))

## remove outliers which are further away then 10 meters
dist_targetData = calc_distance(sourceData)

dist_threshold = 20  # 閾値
sourceData = sourceData.iloc[
    np.nonzero((dist_targetData < dist_threshold).values)[0], :
]

# target data
sourceMatrix = np.array([sourceData["X"], sourceData["Y"], sourceData["Z"]])
# print(type(targetMatrix))
# print((targetMatrix))


# rotate
sourceMatrix = np.dot(param.transarray_z[m], sourceMatrix)
sourceMatrix = np.dot(param.transarray_x[m], sourceMatrix)
sourceMatrix = np.dot(param.transarray_y[m], sourceMatrix)

medX = statistics.median(sourceMatrix[0])
medY = statistics.median(sourceMatrix[1])
medZ = statistics.median(sourceMatrix[2])
print("中央値は\n")
print(medX)
print(medY)
print(medZ)
print("\n")

if medX < 0:
    sourceMatrix[0] = sourceMatrix[0] + 2
if medY < 0:
    sourceMatrix[1] = sourceMatrix[1] + 3.5
if medZ < 0.1:
    sourceMatrix[2] = sourceMatrix[2] + 0.2


# 整理
sourceMatrix = np.where(
    (sourceMatrix[0] > param.x_min) & (sourceMatrix[0] < param.x_max),
    sourceMatrix,
    param.outlier,
)
sourceMatrix = np.where(
    (sourceMatrix[1] > param.y_min) & (sourceMatrix[1] < param.y_max),
    sourceMatrix,
    param.outlier,
)
sourceMatrix = np.where(
    (sourceMatrix[2] > param.z_min[m]) & (sourceMatrix[2] < param.z_max),
    sourceMatrix,
    param.outlier,
)

sourceMatrix = sourceMatrix[:, np.all(sourceMatrix != param.outlier, axis=0)]

sourceMatrix = sourceMatrix.T

# 3D散布図でプロットするデータを生成する為にnumpyを使用
X = sourceMatrix[:, 0]  # 自然数の配列
Y = sourceMatrix[:, 1]  # 特に意味のない正弦
Z = sourceMatrix[:, 2]  # 特に意味のない正弦
# print(X)

# グラフの枠を作成
fig = plt.figure()
ax = Axes3D(fig)

# X,Y,Z軸にラベルを設定
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

# .plotで描画
ax.plot(X, Y, Z, marker="o", linestyle="None")

# # 最後に.show()を書いてグラフ表示
plt.show()
