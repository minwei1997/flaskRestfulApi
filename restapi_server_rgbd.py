from flask import Flask, jsonify
from flask import make_response
from flask import request
from flask import abort
import pyrealsense2 as rs
import numpy as np
import os
import cv2
import time
import json
app = Flask(__name__)
# =================================================================
# Parameters
# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
# ==================================================================
# testing data
tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]
# 這邊是註冊方法 假如要trigger任何action的話 也可以藉由get
# =====================================================================
# get all tasks
@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_all_task():
    return jsonify({'task': tasks})
# ======================================================================
# 獲得特定的task
@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, tasks))
    print(task)
    if len(task) == 0:
        abort(404)
    return jsonify({'task': task[0]})
# ===============================================================================
# post 方法實作 負責接收PXI的資料
@app.route('/todo/api/v1.0/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201
# ===============================================================================
# post Get 6dof的資料
# 收取任何從PXI的資料
# Data receiver 這邊主要都是用
"""
這個route主要負責的是接收從PXI端來的資料
可以用request的json屬性去讀取裡面的資料
"""
@app.route('/todo/api/v1.0/data/send6dof', methods=['POST'])
def create_6dof():
    print(request.json)
    if not request.json or not '6dof' in request.json:
        abort(400)
    six_degreeOfFreedom=request.json['6dof']
    # 要處理json格式 要先將json string轉成 json
    # 這樣就可以轉成dict
    six_degreeOfFreedom=json.loads(six_degreeOfFreedom)
    print(six_degreeOfFreedom)
    # print("J1: ",six_degreeOfFreedom['J1'])
    # print("J2: ",six_degreeOfFreedom['J2'])
    # print("J3: ",six_degreeOfFreedom['J3'])
    # print("J4: ",six_degreeOfFreedom['J4'])
    # print("J5: ",six_degreeOfFreedom['J5'])
    # print("J6: ",six_degreeOfFreedom['J6'])
    # time.sleep(5)
    return jsonify({'msg': "Success"}), 201
# ==============================================================================
# Put Delete 方法實作 這邊可用可不用
@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, tasks))
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})

@app.route('/todo/api/v1.0/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = list(filter(lambda t: t['id'] == task_id, tasks))
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify({'result': True})
# ============================================================================
# 控制器希望PC這邊做甚麼事情
# Action controller
# 純粹希望pc端坐事情的 可以使用action name傳遞 注意後面的/不能夠省略
@app.route('/todo/api/v1.0/actions/<string:action_name>/', methods=['GET'])
def take_action(action_name):
    global pipeline,config
    print("url: '/todo/api/v1.0/actions/<string:action_name>'")
    if action_name==None:
        abort(404)
    # 新增action name即可
    # In order to turn on the stream in the code you need to let labview to control it through URL
    # finishing stream can use the same way to complete it.
    elif action_name=="start_stream":
        pipeline.start(config)
        return jsonify({'msg': "start stream"})
    elif action_name=="finish_stream":
        pipeline.stop()
        return jsonify({'msg': "finish stream"})
    elif action_name=="sayhi":
        return jsonify({'msg': "Hello"})
    else:
        abort(404)
"""
這裡面的寫法必須注意的事情有：
1.要進來這個route就是必須傳遞parameter，否則會走上面那個路徑
labview端就不需要傳參數給action parameter
2.新增方法的話只要新增elif的條件判斷即可，action parameter就是對應的參數
"""
@app.route('/todo/api/v1.0/actions/<string:action_name>/<string:action_parameter>', methods=['GET'])
def take_action_with_parameter(action_name,action_parameter):
    global pipeline,config
    # 基本上 裡面可以用來處理任何邏輯運算 以及需要執行甚麼動作
    print(action_name,action_parameter)
    # pipeline.start(config)

    if action_name==None:
        abort(404)
    # 假如有其他action需要parameter 則加入其他elif條件即可
    elif(action_name=='takepic'):
        # 這邊的action parameter就是folder name
        folder_name=action_parameter
        if os.path.isdir(folder_name):
            print("The photo is saving in: /",folder_name)
        else:
            os.makedirs(folder_name)
        # Take picture setting up
        # ====================================
        # replace by rgbd setting up
        # while True:
        #     ret, frame = cap.read()
        #     if ret==True:
        #         cv2.imwrite(folder_name+"/"+"frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".png",frame)
        #         break

        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if color_frame:
                color_image = np.asanyarray(color_frame.get_data())
                cv2.imwrite(folder_name+"/"+"frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg",color_image)
                # pipeline.stop()
                break
                
        return jsonify({'msg': "Success"})
    
    elif(action_name=="others"):
        return jsonify({'msg': action_name+action_parameter})
    else:
        abort(404)

# ==============================================================================
# router 最後都希望可以放入 errorhandler處理404的狀況
@app.errorhandler(404)
def error_handler(error):
    return make_response(jsonify({'msg': 'Failed'}), 404)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=12345,debug = True)