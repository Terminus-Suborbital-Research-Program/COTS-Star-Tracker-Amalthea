from vmbpy import *
import cv2
import sys
import time
from queue import Queue

from aenum import Enum, NoAlias


### Implement with CamState as a struct or touple of all state specific data
# (Time limit (range[-1]), range, )

class CamState(Enum):
    _settings_ = NoAlias

    FIRST_SET = {
        "images": 50,
        "range": range(120,180)
    }
    SECOND_SET = {
        "images": 80,
        "range": range(180, 240)
    }
    THIRD_SET = {
        "images": 80,
        "range": range(240, 600)
    }
    END = {

    }

def get_camera() -> Camera:
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()

        if not cams:
            print("No Cam Detected. Exiting")
            sys.exit(1)


        return cams[0]

opencv_display_format = PixelFormat.Bgr8


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

    

# POWER_ON_T_ESTIMATE_SEC = -120                            frame = self.handler.get_image()


SD_PATH = "temp"


def get_t_time(times):
    return int((time.time() + times[1])  - times[0])

def cam_write(handler, cam_state, times):
    for i in range (cam_state.value["images"]):
        t_time = get_t_time(times)
        # Hold until we get to the new time range if we finished the previous set early
        while t_time < cam_state.value["range"][0]:
            time.sleep(1)
            t_time = get_t_time(times)
        # Take a picture
        if t_time in cam_state.value["range"]:
            frame = handler.get_image()
            file_path = f"{SD_PATH}/{t_time}.tiff"
            cv2.imwrite(file_path,frame)
        
        # Break if we can't finish taking pictures in this time range
        elif t_time > cam_state.value["range"][-1]:
            break




        

with VmbSystem.get_instance():
    with get_camera() as cam:
        handler = Handler()
        cam.ExposureAuto.set('Off')
        cam.GainAuto.set('Off')
        # cam.DeviceLinkThroughputLimit.set(cam.DeviceLinkThroughputLimit.get_range()[1])
        #cam.set_pixel_format(PixelFormat.Mono12p)
        cam.start_streaming(handler=handler, buffer_count=3)
        ## Testing
        start_t_time = time.time()
        t_time_init = 120 #sys.argv[1]

        times = (start_t_time, t_time_init)

        state = CamState.FIRST_SET

        while True:
            match state:
                case CamState.FIRST_SET:
                    cam_write(handler, state, times)
                    state = CamState.SECOND_SET
                case CamState.SECOND_SET:
                    cam_write(handler, state, times)
                    state = CamState.THIRD_SET
                case CamState.THIRD_SET:
                    cam_write(handler, state, times)
                    state = CamState.END
                case CamState.END:
                    print("Done")
                    sys.exit(0)

        


