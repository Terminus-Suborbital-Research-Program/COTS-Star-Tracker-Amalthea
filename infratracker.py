from vmbpy import *

import sys
import time
from aenum import Enum, NoAlias

class CamState(Enum):
    _settings_ = NoAlias

    FIRST_SET = 50
    WAIT = 0
    SECOND_SET = 80
    THIRD_SET = 80



def get_camera(hello) -> Camera:
    with VmbSystem.get_instance() as vmb:
        cams = vmb.get_all_cameras()

        if not cams:
            abort('No Cameras accessible. Abort.')

            return cams[0]


class Handler:
    def __init__(self):
        self.display_queue = Queue(3)

        self.opencv_display_format = PixelFormat.Mono12
        # self.opencv_display_format = PixelFormat.Mono8


    def get_image(self):
        return self.display_queue.get(True)

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            # print('{} acquired {}'.format(cam, frame), flush=True)

            # Convert frame if it is not already the correct format
            if frame.get_pixel_format() == self.opencv_display_format :
                display = frame
            else:
                # This creates a copy of the frame. The original `frame` object can be requeued
                # safely while `display` is used
                display = frame.convert_pixel_format(self.opencv_display_format )

            self.display_queue.put(display.as_opencv_image(), True)

        cam.queue_frame(frame)

def cam_setup(cam):
    cam.ExposureAuto.set('Off')
    cam.GainAuto.set('Off')
    cam.DeviceLinkThroughputLimit.set(self.cam.DeviceLinkThroughputLimit.get_range()[1])
    cam.set_pixel_format(PixelFormat.Mono12)
    cam.start_streaming(handler=self.handler, buffer_count=3)

# POWER_ON_T_ESTIMATE_SEC = -120                            frame = self.handler.get_image()


SD_PATH = "temp"


def get_t_time(start_time):
    time.time() + start_time

# Take the specifed 
def cam_write(handler, cam_state, start_t_time, time_limit):
    for i in range (cam_state.value):
        t_time = get_t_time(start_t_time)
        if t_time > time_limit:
            break

        frame = handler.get_image()
        cv2.imwrite(f"SD_PATH/{t_time}",frame)
        # Decide based on testing whether this needs to run as fast as physically possible or just sleep
        # time.sleep(1)

        


with VmbSystem.get_instance():
    with get_camera() as cam:
        cam_setup(cam)
        cam.start_streaming(handler=handler, buffer_count=3)

        start_t_time = sys.argv[1] + time.time()

        state = CamState.FIRST_SET

        while True:
            t_time = get_t_time(start_t_time)
            if t_time in range(120,180) and state == CamState.FIRST_SET:
                cam_write(handler, state, start_t_time, time_limit=180)
                state = CamState.SECOND_SET
            elif t_time in range(180, 240) and state == CamState.SECOND_SET:
                cam_write(handler, state, start_t_time, time_limit=240)
                state = CamState.THIRD_SET
            elif t_time in range(240, 600) and state == CamState.THIRD_SET:
                cam_write(handler, state, start_t_time, time_limit=600)
                break
            time.sleep(1)

        ## May remove setuptime_limit=180

        


