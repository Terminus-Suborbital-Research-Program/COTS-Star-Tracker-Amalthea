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

opencv_display_format = PixelFormat.Mono12p #PixelFormat.Bgr8


class Handler:
    def __init__(self):
        self.display_queue = Queue(10)

    def get_image(self):
        return self.display_queue.get(True)

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            # Convert frame if it is not already the correct format
            if frame.get_pixel_format() == opencv_display_format:
                display = frame
            else:
                # This creates a copy of the frame. The original `frame` object can be requeued
                # safely while `display` is used
                display = frame.convert_pixel_format(opencv_display_format)

            self.display_queue.put(display.as_opencv_image(), True)

        cam.queue_frame(frame)

SD_PATH = "temp" # sys.argv[1]


def cam_write(handler):
    frame = handler.get_image()
    print("Frame can be acquired")
    file_path = f"{SD_PATH}/{time.time()}.tiff"
    cv2.imwrite(file_path,frame)

# Time between picutre takes
# Directory to save in 
with VmbSystem.get_instance():
    with get_camera() as cam:
        handler = Handler()
        cam.ExposureAuto.set('Off')
        cam.GainAuto.set('Off')
        # cam.DeviceLinkThroughputLimit.set(cam.DeviceLinkThroughputLimit.get_range()[1])
        # print(cam.get_pixel_format())
        #cam.set_pixel_format(PixelFormat.Mono12p)
        cam.start_streaming(handler=handler, buffer_count=3)
        ## Testing - benchmark time to take an image
        start_time = time.time()
        cam_write(handler)
        capture_offset = time.time() - start_time
        ##
        # Capture interval- seconds floating
        # capture_interval = sys.argv[2] - capture_offset

        capture_interval = 1 - capture_offset
        while True:
            cam_write(handler)
            time.sleep(capture_interval)





        


