import math
import threading
import time

import numpy as np
import torch
from utils.augmentations import letterbox
from models.common import DetectMultiBackend
from utils.general import (cv2, non_max_suppression, scale_boxes, xyxy2xywh)
from utils.plots import Annotator
from utils.torch_utils import smart_inference_mode

from ScreenShot import screenshot
from SendInput import *

import pynput.mouse
# from pynput.mouse import Listener
from pynput import keyboard

is_x2_pressed = False
is_esc = False

def on_press(key):
    global is_x2_pressed
    global is_esc     
    if key == keyboard.Key.ctrl_l:
        print('开始瞄准')
        is_x2_pressed = True
    if key == keyboard.Key.esc:
        print('程序已退出')
        is_esc = True
        return False  # 停止键盘监听器

def on_release(key):
    global is_x2_pressed
    if key == keyboard.Key.alt_l:
        is_x2_pressed = False
        print('瞄准取消')

def KeyBoardListen():
    # 设置键盘监听器
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


@smart_inference_mode()
def run():
    global is_x2_pressed
    global is_esc
    # Load model
    device = torch.device('cpu')
    model = DetectMultiBackend(weights='./weights/yolov5n.pt', device=device, dnn=False, data=False, fp16=False)

    # 读取图片
    while True:
        im = screenshot()

        im0 = im

        # 处理图片
        im = letterbox(im, (640, 640), stride=32, auto=True)[0]  # padded resize
        im = im.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
        im = np.ascontiguousarray(im)  # contiguous
        im = torch.from_numpy(im).to(model.device)
        im = im.half() if model.fp16 else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim

        # 推理
        pred = model(im, augment=False, visualize=False)
        # 非极大值抑制
        pred = non_max_suppression(pred, conf_thres=0.6, iou_thres=0.45, classes=0, max_det=1000)

        # 处理推理内容
        for i, det in enumerate(pred):
            # 画框
            annotator = Annotator(im0, line_width=2)
            if len(det):
                distance_list = []
                target_list = []
                # 将转换后的图片画框结果转换成原图上的结果
                det[:, :4] = scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()
                for *xyxy, conf, cls in reversed(det):  # 处理推理出来每个目标的信息
                    # 将xyxy(左上角+右下角)格式转为xywh(中心点+宽长)格式，并除上w，h做归一化，转化为列表再保存
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4))).view(-1).tolist()  # normalized xywh

                    X = xywh[0] - 320
                    Y = xywh[1] - 320

                    distance = math.sqrt(X ** 2 + Y ** 2)
                    xywh.append(distance)
                    annotator.box_label(xyxy, label=f'[{int(cls)}Distance:{round(distance, 2)}]',
                                        color=(34, 139, 34),
                                        txt_color=(0, 191, 255))

                    distance_list.append(distance)
                    target_list.append(xywh)

                target_info = target_list[distance_list.index(min(distance_list))]

                if is_x2_pressed:
                    mouse_xy(int(target_info[0] - 320), int(target_info[1] - 320))
                    time.sleep(0.003)  # 主动睡眠，防止推理过快,鼠标移动相同的两次

            im0 = annotator.result()
            if is_esc:
                return
            cv2.imshow('window', im0)
            cv2.waitKey(1)


if __name__ == "__main__":
    threading.Thread(target=KeyBoardListen).start()
    run()
