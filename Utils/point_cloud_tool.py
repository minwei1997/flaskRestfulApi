from PIL import Image
import open3d as o3d
from matplotlib import pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import cv2
from sklearn.decomposition import PCA
from scipy.spatial.transform import Rotation as R

# ====================================================
# 座標轉換功能
"""
Quaterion格式:(x,y,z,qx,qy,qz,qw) as list
Transformation matrix: 4x4 as list
ex:
[
    1 0 0 1,
    0 1 0 2,
    0 0 1 3,
    0 0 0 1
]
"""
def quaterion_to_tfMatrix(quaterion):
    if(len(quaterion)!=7):
        raise Exception("Make sure your format can fit what we provide.")
    t_matrix=np.zeros((4,4))
    translation_vector=np.array(quaterion[:3])
    r = R.from_quat(quaterion[3:])
    r_matrix=r.as_dcm()
    t_matrix[0:3,0:3]=r_matrix
    t_matrix[0:3,3]=translation_vector.T
    t_matrix[3,:]=np.array([0,0,0,1])
    return t_matrix
# ====================================================
# Join map function
# ====================================================
"""
這邊傳入pose_list,color_list,depth_list
pose_list: must be transformation matrix type.
color_list: rgb image
depth_list: depth image
這邊的color & depth 不能是numpy array 一定要是用Image這個套件讀取出來的格式才行
"""
def join_map(pose_list,color_list,depth_list,camera):
    if(len(pose_list)!=len(color_list) or len(pose_list)!=len(depth_list)):
        raise Exception("Color and depth image do not have the same resolution, or the number of photos do not match the num of pose!")
    points=[]
    # print(len(pose_list))
    for i in range(len(pose_list)):
        rgb = color_list[i]
        depth = depth_list[i]
        # 這邊的v=480 u=640
        for v in range(rgb.size[1]):
            for u in range(rgb.size[0]):
                color = rgb.getpixel((u,v))
                Z = depth.getpixel((u,v)) * camera.scalingfactor
                if Z==0: continue
                X = (u - camera.cx) * Z / camera.fx
                Y = (v - camera.cy) * Z / camera.fy
                # 這個地方注意是做作標轉換的地方
                # ======================================
                point_in_camera=np.array([X,Y,Z,1])
                world_point=pose_list[i].dot(point_in_camera)
                # ======================================
                points.append("%f %f %f %d %d %d 0\n"%(world_point[0],world_point[1],world_point[2],color[0],color[1],color[2]))
    return points

# ====================================================
# 將color 跟 depth map轉成 points
# 將color mask depth 轉成 partial point cloud
# ====================================================
'''
這邊要記得傳入camera的config才能夠計算
傳入的file是指 filename
todo:
這邊可能會加入如何計算join map 可以參考join_map.py的文件
'''
def color_and_depth_to_ply(rgb_file,depth_file,camera):
    depth = Image.open(depth_file)
    rgb = Image.open(rgb_file)
    if rgb.size != depth.size:
        raise Exception("Color and depth image do not have the same resolution.")
    if rgb.mode != "RGB":
        raise Exception("Color image is not in RGB format")
    if depth.mode != "I":
        raise Exception("Depth image is not in intensity format")
    print(depth.size)

    points = []
    #if the size of photo is (480,640) in opencv, then its size would be (640,480) in PIL 
    for v in range(rgb.size[1]):
        for u in range(rgb.size[0]):
            color = rgb.getpixel((u,v))
            # scaling factor can transform the unit from minimeter to meter
            Z = depth.getpixel((u,v)) * camera.scalingfactor
            if Z==0: continue
            X = (u - camera.cx) * Z / camera.fx
            Y = (v - camera.cy) * Z / camera.fy
            points.append("%f %f %f %d %d %d 0\n"%(X,Y,Z,color[0],color[1],color[2]))
    return points
"""
Mask+depth+color to partial point cloud
讀入都是numpy array的值(因為是從realsense讀過來的)
這裡因為depth是從nparray過來的所以mode上會從原本的I變成是I;16 也因此跟上面純粹用Image.open的結果不一樣
return:
list(for saving)),nparray(for dealing with data)
"""
def mask_to_partial_pointcloud(color,depth,mask,camera):
    color_img = Image.fromarray(color.astype('uint8'), 'RGB')
    depth_img = Image.fromarray(depth)
    mask_img = Image.fromarray(mask)
    if color_img.size != depth_img.size:
        raise Exception("Color and depth image do not have the same resolution.")
    if color_img.mode != "RGB":
        raise Exception("Color image is not in RGB format")
    if depth_img.mode != "I;16":
        raise Exception("Depth image is not in intensity format")
    # gray image 0-255
    if mask_img.mode != "L":
        raise Exception("Depth image is not in gray image format")
    points = []
    xyz_points=[]
    #if the size of photo is (480,640) in opencv, then its size would be (640,480) in PIL 
    for v in range(color_img.size[1]):
        for u in range(color_img.size[0]):
            color = color_img.getpixel((u,v))
            # scaling factor can transform the unit from minimeter to meter
            Z = depth_img.getpixel((u,v)) * camera.scalingfactor
            # mask==0 或者z==0 都是略過
            if Z==0 or mask_img.getpixel((u,v))==0: continue
            X = (u - camera.cx) * Z / camera.fx
            Y = (v - camera.cy) * Z / camera.fy
            xyz_points.append([X,Y,Z])
            points.append("%f %f %f %d %d %d 0\n"%(X,Y,Z,color[0],color[1],color[2]))
    return points,np.array(xyz_points)
"""
Mask版本的join map
MaskRCNN出來的Mask存成list
pose_list: must be transformation matrix type.
color_list: rgb image
depth_list: depth image
mask_list: mask image
======================================================
傳進去的List都需要用Image的套件去開才行
但因為是用realsense讀入，所以都是走opencv的格式 要轉成
color=cv2.imread('./dataset/color.png')
# brg to rgb
color=color[...,::-1]
depth=cv2.imread('./dataset/depth.png',cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
mask=cv2.imread('./dataset/mask.png',cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
color_img = Image.fromarray(color.astype('uint8'), 'RGB')
depth_img = Image.fromarray(depth)
mask_img = Image.fromarray(mask)
======================================================
Return ply type points,points(np type)
"""
def join_map_with_mask(pose_list,color_list,depth_list,mask_list,camera):
    if(len(pose_list)!=len(color_list) or len(pose_list)!=len(depth_list) or len(pose_list)!=len(mask_list)):
        raise Exception("Color and depth image do not have the same resolution, or the number of photos do not match the num of pose!")
    points=[]
    xyz_points=[]
    # print(len(pose_list))
    for i in range(len(pose_list)):
        rgb = color_list[i]
        depth = depth_list[i]
        # 這邊的v=480 u=640
        for v in range(rgb.size[1]):
            for u in range(rgb.size[0]):
                color = rgb.getpixel((u,v))
                Z = depth.getpixel((u,v)) * camera.scalingfactor
                if Z==0 or mask_list[i].getpixel((u,v))==0: continue
                X = (u - camera.cx) * Z / camera.fx
                Y = (v - camera.cy) * Z / camera.fy
                # 這個地方注意是做作標轉換的地方
                # ======================================
                point_in_camera=np.array([X,Y,Z,1])
                world_point=pose_list[i].dot(point_in_camera)
                # ======================================
                xyz_points.append([world_point[0],world_point[1],world_point[2]])
                points.append("%f %f %f %d %d %d 0\n"%(world_point[0],world_point[1],world_point[2],color[0],color[1],color[2]))
    return points,np.array(xyz_points)
# ==========================================================
# Saving/read pc, basic manipulation to pc
# ==========================================================
"""
這裡可以寫一些簡單的數據處理 跟 處理顯示
"""
# 存points 變成點雲文件
def savePoints_to_ply(dirname,filename,points):
    file = open(dirname+'/'+filename,"w")
    file.write('''ply
        format ascii 1.0
        element vertex %d
        property float x
        property float y
        property float z
        property uchar red
        property uchar green
        property uchar blue
        property uchar alpha
        end_header
        %s
        '''%(len(points),"".join(points)))
    file.close()
def show_ply_file(dirname,filename):
    pcd = o3d.io.read_point_cloud(dirname+"/"+filename)
    o3d.visualization.draw_geometries([pcd])

# 從ply 檔案得到所有點
def get_ply_file_points(dirname,filename):
    pcd = o3d.io.read_point_cloud(dirname+"/"+filename)
    # print(pcd)
    points=np.asarray(pcd.points)
    return points
# 上面的point cloud傳入的是numpy
# 這邊傳入純粹就是x,y,z的值
"""
input: numpy or list
output: x,y,z的平均
"""
def get_centroid_from_pc(points):
    if(type(points)==list):
        points=np.array(points)
        points_mean=np.mean(points,axis=0)
    else:
        points_mean=np.mean(points,axis=0)
    return points_mean[0],points_mean[1],points_mean[2]
"""
input:
xyz_points:numpy
"""
def show_centriod(xyz_points,title_name):
    x_mean,y_mean,z_mean=get_centroid_from_pc(xyz_points)
    ax = plt.subplot(111, projection='3d')  # 创建一个三维的绘图工程
    #  将数据点分成三部分画，在颜色上有区分度
    ax.scatter(xyz_points[:,0], xyz_points[:,1], xyz_points[:,2], c='b',s=1)  # 绘制数据点
    ax.scatter(x_mean, y_mean, z_mean, c='r',s=10)
    ax.set_zlabel('Z')  # 坐标轴
    ax.set_ylabel('Y')
    ax.set_xlabel('X')
    plt.title(title_name)
    plt.show()
"""
Normalizing the point cloud into the unit sphere
refer to pointnet
"""
def normalize_point_cloud(points):
    centroid = np.mean(points, axis=0)
    points -= centroid
    furthest_distance = np.max(np.sqrt(np.sum(abs(points)**2,axis=-1)))
    points /= furthest_distance
    return points
# ===========================================================
# Downsizing function list
# ===========================================================
"""
這邊提供兩種方式一種是voxel的方式 voxel size越大代表取的量越少
參數method傳入字典的格式:
注意這邊傳入的是open3d point cloud的形式 is_show參數選擇要不要看差異
假如是要傳入numpy形式 要先轉成open3d的形式
input:
numpy or open3d point cloud
output:
open3d::pointcloud
ex:
function={
    'method':'voxel',
    'voxel_size':0.02
}
or
function={
    'method':'uniform',
    'every_k_points':5
}
"""
def point_cloud_down_sample_from_file(dirname,filename,function={}):
    if len(function)<2:
        raise SystemExit('You should pass the third parameter as dict')
    pcd = o3d.io.read_point_cloud(dirname+"/"+filename)
    if(function['method']=='voxel'):
        down_pcd = pcd.voxel_down_sample(voxel_size=function['voxel_size'])
    elif(function['method']=='uniform'):
        down_pcd = pcd.uniform_down_sample(every_k_points=function['every_k_points'])
    else:
        raise SystemExit('Make sure the name of method is correct!!!')
    return down_pcd
def point_cloud_down_sample_from_pc(cloud,function={}):
    if len(function)<2:
        raise SystemExit('You should pass the third parameter as dict')
    if(type(cloud).__module__==np.__name__):
        print("你傳入numpy array形式")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(cloud)
        if(function['method']=='voxel'):
            down_pcd = pcd.voxel_down_sample(voxel_size=function['voxel_size'])
        elif(function['method']=='uniform'):
            down_pcd = pcd.uniform_down_sample(every_k_points=function['every_k_points'])
        else:
            raise SystemExit('Make sure the name of method is correct!!!')
    else:
        if(function['method']=='voxel'):
            down_pcd = cloud.voxel_down_sample(voxel_size=function['voxel_size'])
        elif(function['method']=='uniform'):
            down_pcd = cloud.uniform_down_sample(every_k_points=function['every_k_points'])
    return down_pcd
# ===========================================================
# Outlier removal function
# ===========================================================
"""
Statistical outlier removal
Radius outlier removal
注意這邊傳入的是open3d point cloud的形式 is_show參數選擇要不要看差異
假如是要傳入numpy形式 要先轉成open3d的形式
ex:
function={
    'method':'statistical',
    'nb_neighbors':20,
    'std_ratio':2.0
}
or
function={
    'method':'radius',
    'nb_points':16,
    'radius':0.05
}
"""
def display_inlier_outlier(cloud, ind,is_show):
    inlier_cloud = cloud.select_down_sample(ind)
    outlier_cloud = cloud.select_down_sample(ind, invert=True)

    if(is_show):
        outlier_cloud.paint_uniform_color([1, 0, 0])
        inlier_cloud.paint_uniform_color([0.8, 0.8, 0.8])
        o3d.visualization.draw_geometries([inlier_cloud, outlier_cloud])
    return inlier_cloud
"""
這邊的removal 用到的是open3d裡面的outlier removal 所以
return 的形式會是pcd的object
因此要把點取出來的話要用np.asarray(pc_after_removal.points)
將points的array用np的方式取出來
output:
open3d:pointcloud
"""
def point_cloud_outlier_removal(cloud,is_show=False,function={}):
    if len(function)==0:
        raise SystemExit('You should pass the third parameter as dict')
    if(type(cloud).__module__==np.__name__):
        print("你傳入numpy array形式")
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(cloud)      
        if(function['method']=='statistical'):
            cl, ind = pcd.remove_statistical_outlier(nb_neighbors=function['nb_neighbors'],std_ratio=function['std_ratio'])
        elif(function['method']=='radius'):
            cl, ind = pcd.remove_radius_outlier(nb_points=function['nb_points'], radius=function['radius'])

        pc_after_removal=display_inlier_outlier(pcd, ind,is_show)
    # 傳入open3d 的point cloud 形式
    else:
        if(function['method']=='statistical'):
            cl, ind = cloud.remove_statistical_outlier(nb_neighbors=function['nb_neighbors'],std_ratio=function['std_ratio'])
        elif(function['method']=='radius'):
            cl, ind = cloud.remove_radius_outlier(nb_points=function['nb_points'], radius=function['radius'])
        pc_after_removal=display_inlier_outlier(cloud, ind,is_show)
    return pc_after_removal
# ===========================================================
# The tool to analyze the shape of the point cloud
# ===========================================================
"""
cal_pca's parameters
point_cloud: numpy array type
is_show: initially False to display the result of the point cloud and show the vectors in figure.
desired_num_of_feature: we set up as three because we analyze the shape of point cloud,
which contains three dimensions (x,y,z).
return:
first: principal axes of pointcloud
second: 
singular values.
"""
def cal_pca(point_cloud,is_show=False,desired_num_of_feature=3,title="pca demo"):
    pca = PCA(n_components=desired_num_of_feature)
    pca.fit(point_cloud)
    # print("Principal vectors: ",pca.components_)
    # print("Singular values: ",pca.explained_variance_)
    if is_show:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlabel('X Label(unit:m)')
        ax.set_ylabel('Y Label(unit:m)')
        ax.set_zlabel('Z Label(unit:m)')
        plt.title(title)
        ax.scatter(point_cloud[:,0], point_cloud[:,1], point_cloud[:,2], c='y',s=1)
        xm,ym,zm=get_centroid_from_pc(point_cloud)
        ax.scatter(xm, ym, zm, c='r',s=10)
        print("*"*30)
        print("z 向量 %f ,%f ,%f" % (pca.components_[2,0],pca.components_[2,1],pca.components_[2,2]))
        if(np.inner(pca.components_[2,:],[0,0,1])>0):
            print("pca_z向量與z方向同向，需要對x軸旋轉180度")
            pca.components_[2,:]=-pca.components_[2,:]
            # r = R.from_euler('x',180, degrees=True)
            # r_b_o=R.from_dcm(pca.components_.T)
            # r3=r_b_o*r
            # pca.components_=r3.as_dcm().T
        # 求出x,y的外積,應該為z 看是否與第三軸同向確認是否為正確
        x_axis_matrix=np.outer(pca.components_[1,:],pca.components_[2,:])
        x_axis=np.asarray([x_axis_matrix[1,2]-x_axis_matrix[2,1],x_axis_matrix[2,0]-x_axis_matrix[0,2],x_axis_matrix[0,1]-x_axis_matrix[1,0]])
        print("*"*30)
        print("外積計算的x軸為:")
        print(x_axis)

        # 確認pca_x與經由外積(y,z)計算的x同向
        if(np.allclose(pca.components_[0,:],x_axis)):
            print("pca_x與外積(y,z)計算的x同向")
        else:
            # 反向，將不重要的x軸轉向
            print("x方向不正確，需替換成正確的項")
            pca.components_[0,:]=x_axis
        if(np.inner(pca.components_[0,:],[1,0,0])<0):
            # 希望夾爪朝前，這樣末端點就不需要轉太多
            print("pca_x向量與x方向反向，需要對x軸旋轉180度")
            r = R.from_euler('z',180, degrees=True)
            r_b_o=R.from_dcm(pca.components_.T)
            r3=r_b_o*r
            pca.components_=r3.as_dcm().T   
        discount=1
        print("*"*30)
        for length, vector in zip(pca.explained_variance_, pca.components_):
            ax.quiver(xm,ym,zm,vector[0],vector[1],vector[2], length=discount)
            discount/=3

        plt.show()
    return pca.components_,pca.explained_variance_
# ==========================================================
# Manipulation of point cloud
# ==========================================================
"""
Rotation point cloud through z-axis：
Jitter point cloud：
Adding some noise into point cloud.
"""
def rotate_point_cloud_z(point_cloud):
    """ Randomly rotate the point clouds to augument the dataset
        rotation is per shape based along up direction
        Input:
          Nx3 array, point clouds
        Return:
          Nx3 array, point clouds
    """
    rotated_data = np.zeros(point_cloud.shape, dtype=np.float32)
    rotation_angle = np.random.uniform() * 2 * np.pi
    cosval = np.cos(rotation_angle)
    sinval = np.sin(rotation_angle)
    rotation_matrix = np.array([[cosval, sinval, 0],
                                [-sinval, cosval, 0],
                                [0, 0, 1]])
    rotated_data = np.dot(point_cloud.reshape((-1, 3)), rotation_matrix)
    return rotated_data
def jitter_point_cloud(point_cloud, sigma=0.01, clip=0.05):
    """ Randomly jitter points. jittering is per point.
        Input:
          Nx3 array, point clouds
        Return:
          Nx3 array, jittered batch of point clouds
    """
    N, C = point_cloud.shape
    assert(clip > 0)
    jittered_data = np.clip(sigma * np.random.randn(N, C), -1*clip, clip)
    jittered_data += point_cloud
    return jittered_data
# ====================================
# Furthest point sampling algorithm
# ====================================
"""
Furthest point sampling:
這個function 會盡可能的分散選取特定數量的point cloud
"""
def calc_distances(p0, points):
    return ((p0 - points)**2).sum(axis=1)
def furthest_point_sampling(pts, K):
    N,C=pts.shape
    farthest_pts = np.zeros((K, C))
    farthest_pts[0] = pts[np.random.randint(len(pts))]
    distances = calc_distances(farthest_pts[0], pts)
    for i in range(1, K):
        farthest_pts[i] = pts[np.argmax(distances)]
        distances = np.minimum(distances, calc_distances(farthest_pts[i], pts))
    return farthest_pts