#!/usr/bin/env python3

from vmbpy import *
import cv2
import sys
import time
from queue import Queue

from aenum import Enum, NoAlias


def get_camera() -> Camera:
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()

        if not cams:
            print("No Cam Detected. Exiting")
            sys.exit(1)


        return cams[0]

opencv_display_format = PixelFormat.Mono16


class Handler:
    def __init__(self):
        self.display_queue = Queue(10)

    def get_image(self):
        return self.display_queue.get(True)

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            display = frame.convert_pixel_format(opencv_display_format)

            self.display_queue.put(display.as_opencv_image(), True)

        cam.queue_frame(frame)

SD_PATH = sys.argv[1]


def cam_write(handler):
    frame = handler.get_image()
    file_path = f"{SD_PATH}/{time.time()}.tiff"
    cv2.imwrite(file_path,frame)

with VmbSystem.get_instance() as vmb:
    with get_camera() as cam:
        cam.set_pixel_format(PixelFormat.Mono12p)   
        # cam.ExposureAuto.set('Off')
        # cam.GainAuto.set('Off')     

        handler = Handler()
        
        cam.start_streaming(handler=handler, buffer_count=3)
        ## benchmark time to take an image
        start_time = time.time()
        cam_write(handler)
        capture_offset = time.time() - start_time
        
        # Capture interval- seconds to take a single image
        capture_interval = float(sys.argv[2]) - capture_offset
        while True:
            cam_write(handler)
            time.sleep(capture_interval)





        


