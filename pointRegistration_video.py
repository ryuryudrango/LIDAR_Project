import statistics
from time import time
from matplotlib import animation
from numpy.lib.utils import source
import pandas as pd
import open3d as o3
import numpy as np
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pyautogui
import time

import chair_parameter as param
import read_video_csv as vd

# 複数点
# http://www.open3d.org/docs/0.13.0/tutorial/pipelines/multiway_registration.html
# Global registartion
# http://www.open3d.org/docs/0.13.0/tutorial/pipelines/global_registration.html


def calc_distance(inputFrame):
    return (inputFrame["X"] ** 2 + inputFrame["Y"] ** 2 + inputFrame["Z"] ** 2) ** 0.5


def distance_cut(sourceData, dist_data, dist_threshold):
    distance_cut = sourceData.iloc[
        np.nonzero((dist_data < dist_threshold).values)[0], :
    ]
    # distance_cut = distance_cut.iloc[np.nonzero((distance_cut["Z"] < 0.8).values)[0], :]
    # preprocessed_data = distance_cut.iloc[
    #     np.nonzero((distance_cut["Z"] > z_threshold).values)[0], :
    # ]

    return distance_cut


# rotation and remove unnecessary data
def source_preprocess(
    sourceData,
    trans_init_z,
    trans_init_x,
    trans_init_y,
    x_min,
    x_max,
    y_min,
    y_max,
    z_max,
    z_min,
    z_adjust,
    trans_carib,
    outlier,
):
    source = o3.geometry.PointCloud()  # generate point_cloud
    sourceMatrix = np.array([sourceData["X"], sourceData["Y"], sourceData["Z"]])

    # ここから回転 and cut
    sourceMatrix = np.dot(trans_init_z, sourceMatrix)
    sourceMatrix = np.dot(trans_init_x, sourceMatrix)
    sourceMatrix = np.dot(trans_init_y, sourceMatrix)

    medX = statistics.median(sourceMatrix[0])
    medY = statistics.median(sourceMatrix[1])
    medZ = statistics.median(sourceMatrix[2])

    if medX < 0:
        sourceMatrix[0] = sourceMatrix[0] + 2
    if medY < 0:
        sourceMatrix[1] = sourceMatrix[1] + 3.5
    # if medZ < 0.1:
    #     sourceMatrix[2] = sourceMatrix[2] + 0.2
    sourceMatrix[2] = sourceMatrix[2] + z_adjust

    sourceMatrix = np.where(
        (sourceMatrix[0] > x_min) & (sourceMatrix[0] < x_max), sourceMatrix, outlier
    )
    sourceMatrix = np.where(
        (sourceMatrix[1] > y_min) & (sourceMatrix[1] < y_max), sourceMatrix, outlier
    )
    sourceMatrix = np.where(
        (sourceMatrix[2] > z_min) & (sourceMatrix[2] < z_max), sourceMatrix, outlier
    )
    # axisで行か列かを指定できる
    sourceMatrix = sourceMatrix[:, np.all(sourceMatrix != outlier, axis=0)]
    # medX = statistics.median(sourceMatrix[0])
    # medY = statistics.median(sourceMatrix[1])
    # medZ = statistics.median(sourceMatrix[2])
    # sourceMatrix[0] = sourceMatrix[0] - medX
    # sourceMatrix[1] = sourceMatrix[1] - medY
    # sourceMatrix[2] = sourceMatrix[2] - medZ

    sourceMatrix = sourceMatrix.T

    source.points = o3.utility.Vector3dVector(sourceMatrix)
    # source.transform(trans_carib)

    return source


def preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    pcd_down = pcd.voxel_down_sample(voxel_size)

    radius_normal = voxel_size * 2
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_down.estimate_normals(
        o3.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30)
    )
    return pcd_down


def prepare_dataset(voxel_size, num, time_arr):
    print(":: Load two point clouds and disturb initial pose.")
    print("Loading files")

    # sources = pcds = np.zeros(((50, 4)), dtype=o3.cpu.pybind.geometry.PointCloud)
    sources = []  # 初期化は分けないと同じものを指すことになる
    pcds = []
    # print(len(time_arr))
    dist_threshold = 10  # 距離の閾値(原点から遠すぎるものを排除？)
    for m in range(len(time_arr)):
        source_time = []
        pcd_time = []
        for i in range(4):
            # read the data
            sourceData = pd.read_csv(
                vd.readData_multi[num] % str(i) + time_arr[m] + ".csv"
            )

            # remove outliers which are further away then 10 meters
            dist_sourceData = calc_distance(sourceData)  # 原点からの距離を計算

            # print(sourceData(dist_sourceData>20))
            sourceData = distance_cut(sourceData, dist_sourceData, dist_threshold)
            # print(sourceData)

            # source data
            # print("Transforming source data")
            source = source_preprocess(
                sourceData,
                param.transarray_z[i],
                param.transarray_x[i],
                param.transarray_y[i],
                param.x_min,
                param.x_max,
                param.y_min,
                param.y_max,
                param.z_max,
                param.z_min[i],
                param.z_adjust[i],
                param.trans_carib[i],
                param.outlier,
            )

            # print(":: Downsample with a voxel size %.3f." % voxel_size)
            pcd_down = source.voxel_down_sample(voxel_size)

            ##この4行入れたらicp_reguration_errorが出なくなった？
            radius_normal = voxel_size * 2
            # print(":: Estimate normal with search radius %.3f." % radius_normal)
            pcd_down.estimate_normals(
                o3.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30)
            )

            source_time.append(source)
            pcd_time.append(pcd_down)
            # pcds[i][m] = pcd_down
        # print(source_time)
        # print(pcd_time)
        sources.append(source_time)
        # print(len(sources))
        pcds.append(pcd_time)
    # print(sources)
    # print(le(pcds))
    return sources, pcds


def pairwise_registration(source, target):
    print("Apply point-to-plane ICP")
    icp_coarse = o3.pipelines.registration.registration_icp(
        source,
        target,
        max_correspondence_distance_coarse,
        np.identity(4),
        o3.pipelines.registration.TransformationEstimationPointToPlane(),
    )
    icp_fine = o3.pipelines.registration.registration_icp(
        source,
        target,
        max_correspondence_distance_fine,
        icp_coarse.transformation,
        o3.pipelines.registration.TransformationEstimationPointToPlane(),
    )
    transformation_icp = icp_fine.transformation
    information_icp = (
        o3.pipelines.registration.get_information_matrix_from_point_clouds(
            source, target, max_correspondence_distance_fine, icp_fine.transformation
        )
    )
    return transformation_icp, information_icp


def preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    pcd_down = pcd.voxel_down_sample(voxel_size)

    radius_normal = voxel_size * 2
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_down.estimate_normals(
        o3.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30)
    )

    radius_feature = voxel_size * 5
    print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = o3.pipelines.registration.compute_fpfh_feature(
        pcd_down, o3.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100)
    )
    return pcd_down, pcd_fpfh


def full_registration(
    pcds, max_correspondence_distance_coarse, max_correspondence_distance_fine
):
    pose_graph = o3.pipelines.registration.PoseGraph()
    odometry = np.identity(4)
    pose_graph.nodes.append(o3.pipelines.registration.PoseGraphNode(odometry))
    n_pcds = len(pcds)

    for source_id in range(n_pcds):
        for target_id in range(source_id + 1, n_pcds):
            transformation_icp, information_icp = pairwise_registration(
                pcds[source_id], pcds[target_id]
            )
            print("Build o3d.pipelines.registration.PoseGraph")
            if target_id == source_id + 1:  # odometry case
                odometry = np.dot(transformation_icp, odometry)
                pose_graph.nodes.append(
                    o3.pipelines.registration.PoseGraphNode(np.linalg.inv(odometry))
                    # 逆行列を求めている
                )
                pose_graph.edges.append(
                    o3.pipelines.registration.PoseGraphEdge(
                        source_id,
                        target_id,
                        transformation_icp,
                        information_icp,
                        uncertain=False,
                    )
                )
            else:  # loop closure case
                pose_graph.edges.append(
                    o3.pipelines.registration.PoseGraphEdge(
                        source_id,
                        target_id,
                        transformation_icp,
                        information_icp,
                        uncertain=True,
                    )
                )
    # draw_registration_result(so, ta, res_ran.transformation)
    return pose_graph


def execute_global_registration(
    source_down, target_down, source_fpfh, target_fpfh, voxel_size
):
    distance_threshold = voxel_size * 1.5
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    result = o3.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down,
        target_down,
        source_fpfh,
        target_fpfh,
        True,
        distance_threshold,
        o3.pipelines.registration.TransformationEstimationPointToPoint(False),
        3,
        [
            o3.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                distance_threshold
            ),
        ],
        o3.pipelines.registration.RANSACConvergenceCriteria(100000, 0.999),
    )
    return result


def get_time(path):
    files = os.listdir(path)
    files.sort()
    files = files[:timestep]
    timestamp_arr = []
    for word in files:
        a = word.rsplit("_", 1)
        b = a[1].split(".", 1)
        c = b[0]
        # c = int(c)
        timestamp_arr.append(c)
        # print(type(c))
    # print(timestamp_arr)
    # print(len(timestamp_arr))
    return timestamp_arr


def plot(pcds_array, i):
    # グラフの枠を作成
    fig = plt.figure()
    ax = Axes3D(fig)

    # X,Y,Z軸にラベルを設定
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    col = np.arange(30)

    # X,Y,Z軸にラベルを設定
    ax.set_zlim(-0.4, 0.8)
    ax.view_init(elev=30, azim=45)
    # .plotで描画
    ax.scatter(
        pcds_array[i][0],
        pcds_array[i][1],
        pcds_array[i][2],
        marker="o",
        linestyle="None",
        c=np.arange(len(pcds_array[i][2])),
        cmap="ocean",
    )
    # print(pcds_array[i][2])

    # # 最後に.show()を書いてグラフ表示
    plt.show()
    time.sleep(0.1)
    pyautogui.press(["q"])
    # plt.clf()


if __name__ == "__main__":
    agentNum = 4
    timestep = 50
    path = "datasets_lidar/spinningCrane"
    time_arr = get_time(path)
    # print(time_arr)
    # print(len(time_arr))

    voxel_size = 0.05  # means 5cm for the dataset
    # 0→spinningCrane,1→oscillating
    n = 0
    sources, pcds_down = prepare_dataset(voxel_size, n, time_arr)
    prepare_dataset(voxel_size, n, time_arr)

    # 入力の点群を準備したやつ表示
    # print("\npcd_downsは\n")
    # print(len(pcds_down))
    # for pcd in pcds_down:
    # o3.visualization.draw_geometries(
    #     pcd,
    #     zoom=0.5559,
    #     front=[-0.5452, -0.836, -0.2011],
    #     lookat=[0, 0, 0],
    #     up=[-0.2779, -0.282, 0.1556],
    # )

    # 　　 # 一旦まだ
    #     # # 6
    #     print("Optimizing PoseGraph ...")
    #     option = o3.pipelines.registration.GlobalOptimizationOption(
    #         max_correspondence_distance=max_correspondence_distance_fine,
    #         edge_prune_threshold=0.25,
    #         reference_node=0,
    #     )
    #     with o3.utility.VerbosityContextManager(o3.utility.VerbosityLevel.Debug) as cm:
    #         o3.pipelines.registration.global_optimization(
    #             pose_graph,
    #             o3.pipelines.registration.GlobalOptimizationLevenbergMarquardt(),
    #             o3.pipelines.registration.GlobalOptimizationConvergenceCriteria(),
    #             option,
    #         )

    # # 7
    pcd_combined_down = any

    print("Transform points and display")
    pcds_array = []
    i = 0
    for pcd in pcds_down:  # 50回
        pcd_combined = o3.geometry.PointCloud()
        # print(pcd)
        for point_id in range(len(pcd)):  # 4回
            # print(pose_graph.edges[point_id])
            pcd[point_id].transform(param.trans_carib[point_id])
            pcd_combined += pcd[point_id]

        pcd_combined_down = pcd_combined.voxel_down_sample(voxel_size=voxel_size)
        # o3.io.write_point_cloud("multiway_registration.pcd", pcd_combined_down)
        # o3.visualization.draw_geometries(
        #     [pcd_combined_down],
        #     width=1920,
        #     height=720,
        #     left=50,
        #     top=50,
        #     point_show_normal=False,
        #     mesh_show_wireframe=False,
        #     mesh_show_back_face=False,
        #     zoom=0.6559,
        #     front=[-0.5452, -0.736, -0.3011],
        #     lookat=[0, 0, 0],
        #     up=[-0.2779, -0.282, 0.2556],
        # )
        pcd_array = []
        X = []
        Y = []
        Z = []
        # print(len(pcds_down))
        for x in pcd_combined_down.points:
            # pcd_array.append(x)
            X.append(x[0])
            Y.append(x[1])
            Z.append(x[2])
        pcd_array = [X, Y, Z]
        # print(len(pcd_array))
        pcds_array.append(pcd_array)

    print(len(pcds_array))
    print(len(pcds_array[0]))

    # print(type(pcd_combined_down))
    print(type(pcd_combined_down.points))
    # print(type(pcd_combined_down.points[0]))
    # print(pcd_combined_down.points[0])
    # print(len(pcd_combined_down.points))
    print(pcds_array[49][0] == X)

    for index in range(len(pcds_array)):
        plot(pcds_array, index)
    # # ここからアニメ
    # # ANIMATION FUNCTION
    # def func(num):
    #     # NOTE: there is no .set_data() for 3 dim data...
    #     return ax.plot(
    #         dataSet[num][1],
    #         dataSet[num][2],
    #         dataSet[num][3],
    #         marker="o",
    #         linestyle="None",
    #     )

    # # THE DATA POINTS
    # dataSet = pcds_array
    # numDataPoints = len(pcds_array)

    # # GET SOME MATPLOTLIB OBJECTS
    # fig = plt.figure()
    # ax = Axes3D(fig)

    # # NOTE: Can't pass empty arrays into 3d version of plot()
    # # line = plt.plot(dataSet[][0], dataSet[1], dataSet[2], lw=2, c="g")[0]  # For line plot

    # # AXES PROPERTIES]
    # # ax.set_xlim3d([limit0, limit1])
    # ax.set_xlabel("X(t)")
    # ax.set_ylabel("Y(t)")
    # ax.set_zlabel("time")
    # ax.set_title("Trajectory of electron for E vector along [120]")

    # # Creating the Animation object
    # line_ani = animation.FuncAnimation(
    #     fig, func, frames=50, fargs=(dataSet), interval=50, blit=False
    # )
    # # line_ani.save(r'AnimationNew.mp4')

    # plt.show()
