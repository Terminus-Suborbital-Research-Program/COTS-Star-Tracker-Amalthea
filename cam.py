
from queue import Queue
import sys
from typing import Optional
import time
from vmbpy import *
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer, pyqtSlot
import os
import cv2
import shutil



def get_camera(camera_id: Optional[str]) -> Camera:
    with VmbSystem.get_instance() as vmb:
        if camera_id:
            try:
                return vmb.get_camera_by_id(camera_id)

            except VmbCameraError:
                abort('Failed to access Camera \'{}\'. Abort.'.format(camera_id))

        else:
            cams = vmb.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')

            return cams[0]
        
def setup_camera(cam: Camera):
    with cam:
        # Enable auto exposure time setting if camera supports it
        try:
            cam.ExposureAuto.set('Continuous')

        except (AttributeError, VmbFeatureError):
            pass

        # Enable white balancing if camera supports it
        try:
            cam.BalanceWhiteAuto.set('Continuous')

        except (AttributeError, VmbFeatureError):
            pass

        # Try to adjust GeV packet size. This Feature is only available for GigE - Cameras.
        try:
            stream = cam.get_streams()[0]
            stream.GVSPAdjustPacketSize.run()
            while not stream.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VmbFeatureError):
            pass
        
def print_usage():
    print('Usage:')
    print('    python asynchronous_grab_opencv.py [camera_id]')
    print('    python asynchronous_grab_opencv.py [/h] [-h]')
    print()
    print('Parameters:')
    print('    camera_id   ID of the camera to use (using first camera if not specified)')
    print()

def abort( reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')

    if usage:
        print_usage()

    sys.exit(return_code)

def parse_args() -> Optional[str]:
        args = sys.argv[1:]
        argc = len(args)

        for arg in args:
            if arg in ('/h', '-h'):
                print_usage()
                sys.exit(0)

        if argc > 1:
            abort(reason="Invalid number of arguments. Abort.", return_code=2, usage=True)

        return None if argc == 0 else args[0]

"""
class Handler:
    def __init__(self):
        self.display_queue = Queue(3)

        self.display_format = PixelFormat.Mono12


    def get_image(self):
        return self.display_queue.get(True)

    def __call__(self, cam: Camera, stream: Stream, frame: Frame):
        if frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            # Convert frame if it is not already the correct format
            if frame.get_pixel_format() == self.display_format :
                display = frame
            else:
                # This creates a copy of the frame. The original `frame` object can be requeued
                # safely while `display` is used
                display = frame.convert_pixel_format(self.display_format )

            self.display_queue.put(display.as_opencv_image(), True)

        cam.queue_frame(frame)
"""
class Handler:
    def __init__(self):
        self.display_queue = Queue(3)

        self.opencv_display_format = PixelFormat.Mono8


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


class CameraStreamer(QThread):
    frame_ready = pyqtSignal(object)
    file_increment = pyqtSignal(int)

    file_save_dir_update = pyqtSignal(str)
    file_save_enabled_update = pyqtSignal(bool)
    file_save_time_trigger_update= pyqtSignal(bool)

    auto_mode_update = pyqtSignal(bool)
    auto_inc_mode_update = pyqtSignal(bool)
    trigger_mode_update = pyqtSignal(bool)

    trigger_update = pyqtSignal(bool)

    exposure_inc_update = pyqtSignal(int)
    gamma_inc_update = pyqtSignal(int)
    gain_inc_update = pyqtSignal(int)

    burst_amount_update = pyqtSignal(int)

    frame_num_update = pyqtSignal(int)


    def __init__(self):
        super().__init__()
        self.cam_id = parse_args()
        self.running = False
        self.handler = Handler()
        self.cam = None

        
                # This is asynchronous aqcuisition mode

        self.exposure_inc = 0
        self.gamma_inc = 0
        self.gain_inc = 0



        # Corresponding to flags and signals
        """ Flags """
        self.file_save_dir = r"images"
        self.file_save_enabled = False
        self.file_save_time_trigger = False
        self.auto_mode = True  ## Check later to make sure auto mode 
        self.auto_inc_mode = False
        self.trigger_mode = False

        self.trigger = False
        self.inc_trigger = False

        
        
        """ Signals """
        self.file_save_enabled_update.connect(self.file_save_enabled_update_func)
        self.file_save_dir_update.connect(self.file_save_dir_update_func)
        self.file_save_time_trigger_update.connect(self.file_save_time_trigger_func)
        

        self.auto_mode_update.connect(self.auto_mode_update_func)
        self.auto_inc_mode_update.connect(self.auto_inc_mode_update_func)
        self.trigger_mode_update.connect(self.trigger_mode_update_func)
        self.trigger_update.connect(self.trigger_update_func)

        self.exposure_inc_update.connect(self.exposure_inc_update_func)
        self.gamma_inc_update.connect(self.gamma_inc_update_func)
        self.gain_inc_update.connect(self.gain_inc_update_func)

        self.burst_amount_update.connect(self.burst_amount_update_func)
        self.frame_num_update.connect(self.frame_num_update_func)


        """Values for File Naming"""
        self.current_exposure = 0
        self.current_gamma = 0
        self.current_gain = 0

        self.burst_amount = 1

        self.frame_num = 0
    
    def run(self):
        with VmbSystem.get_instance():
            with get_camera(self.cam_id) as cam:
                self.cam = cam
                ## May remove setup
                self.cam.ExposureAuto.set('Off')
                self.cam.GainAuto.set('Off')
                self.cam.DeviceLinkThroughputLimit.set(self.cam.DeviceLinkThroughputLimit.get_range()[1])
                self.cam.set_pixel_format(PixelFormat.Mono12)
                #self.cam.set_pixel_format(PixelFormat.Mono8)
                self.running = True
                # This is asynchronous aqcuisition mode

                self.exp_adj(set=20000)
                self.gain_adj(set=1)
                self.gamma_adj(set=0.60)

                self.current_exposure = self.cam.ExposureTime.get()
                self.current_gain = self.cam.Gain.get()
                self.current_gamma = round(self.cam.Gamma.get(),2)
                
                # Play around with buffer count later
                self.cam.start_streaming(handler=self.handler, buffer_count=3)
                while self.running:
                    frame = self.handler.get_image()

                    if self.file_save_enabled and self.file_save_time_trigger and (self.auto_inc_mode or self.auto_mode):
                        self.frame_num += 1
                        file_path = f"{self.file_save_dir}/{self.current_exposure}ms_{self.current_gain}d_{self.current_gamma}g_im-{self.frame_num}.tiff"
                        cv2.imwrite(file_path,frame)
                        self.file_increment.emit(1)
                        self.file_save_time_trigger = False
                        
                        
                    elif self.trigger:
                        # frame = self.handler.get_image()
                        # self.frame_num += 1
                        # file_path = f"{self.file_save_dir}/{self.current_exposure}ms_{self.current_gain}d_{self.current_gamma}g_im-{self.frame_num}.tiff"
                        # cv2.imwrite(file_path,frame)
                        # self.file_increment.emit(1)
                        for i in range(self.burst_amount):
                            frame = self.handler.get_image()
                            self.frame_num += 1
                            if self.burst_amount == 1:
                               file_path = f"{self.file_save_dir}/{self.current_exposure}ms_{self.current_gain}d_{self.current_gamma}g_im-{self.frame_num}.tiff"
                            else:
                               file_path = f"{self.file_save_dir}/BURST_{self.current_exposure}ms_{self.current_gain}d_{self.current_gamma}g_im-{self.frame_num}.tiff"
                            cv2.imwrite(file_path,frame)
                            self.file_increment.emit(1)
                        self.trigger = False
                    
                    if self.auto_inc_mode and self.inc_trigger:
                        print("entered inc mode")
                        self.exp_adj(increment=self.exposure_inc)
                        self.gain_adj(increment=self.gain_inc)
                        self.gamma_adj(increment=self.gamma_inc)
                        self.inc_trigger = False
                    

                    self.frame_ready.emit(frame)
                    
                    
                self.cam.stop_streaming()

    @pyqtSlot(int)
    def frame_num_update_func(self, val):
        self.frame_num = val
        print(f"frame_num = {self.frame_num}")

    @pyqtSlot(int)
    def burst_amount_update_func(self, val):
        self.burst_amount = val
        print(f"burst_amount = {self.burst_amount}")

    @pyqtSlot(int)
    def exposure_inc_update_func(self, val):
        self.exposure_inc = val
        print(f"exposure inc {self.exposure_inc}")

    @pyqtSlot(int)
    def gain_inc_update_func(self, val):
        self.gain_inc = val
        print(f"gain inc {self.gain_inc}")

    @pyqtSlot(int)
    def gamma_inc_update_func(self, val):
        self.gamma_inc = val
        print(f"gamma inc {self.gamma_inc}")

    @pyqtSlot(bool)
    def trigger_update_func(self, val):
        print(f"Trigger pressed")
        self.trigger = True

    @pyqtSlot(bool)
    def trigger_mode_update_func(self, val):
        print(f"Trigger mode {val}")
        self.trigger_mode = val

    @pyqtSlot(bool)
    def auto_mode_update_func(self, val):
        print(f"Auto_Mode{val}")
        self.auto_mode = val

    @pyqtSlot(bool)
    def auto_inc_mode_update_func(self, val):
        print(f"Auto_Increment_Mode{val}")
        self.auto_inc_mode = val
    
    @pyqtSlot(bool)
    def file_save_enabled_update_func(self, val):
        print(f"Save_Enabled_Mode{val}")
        self.file_save_enabled = val

    @pyqtSlot(bool)
    def file_save_time_trigger_func(self, bool):
        self.inc_trigger = bool
        self.file_save_time_trigger = bool

    @pyqtSlot(str)
    def file_save_dir_update_func(self, val):
        # Must calculate new 
        print(f"New_File_Dir: {val}")
        if not os.path.exists(val):
            os.mkdir(val)

        self.file_save_dir = r'{}'.format(val)

    @pyqtSlot(float)
    def gamma_adj(self, increment: float = 0, incr_up: bool = True, set: int = -1):
        # Gamma adjust
        # set: If set is greater than -1, set the camera value to the set value, otherwise increment
        # incr_up: if true, increment upwards, false, increment downwards
        # increment: Amount of incrementation
        if self.cam:
            try:
                gamma = self.cam.Gamma

                if set == -1:
                    update = gamma.get() + increment
                    if 0.40 <= update <= 2.40:
                        # Set current value + increment if within bounds
                        gamma.set(update)
                elif 0.40 <= set <= 2.40:
                    # Bounded set
                    gamma.set(set)
                
                self.current_gamma = round(self.cam.Gamma.get(),2)
                
            except Exception as e:
                print(f"Gamma Adjust Exception{e}")
    
    @pyqtSlot(int)
    def gain_adj(self, increment: float = 0, incr_up: bool = True, set: int = -1):
        # Gain adjust
        # set: If set is greater than -1, set the camera value to the set value, otherwise increment
        # incr_up: if true, increment upwards, false, increment downwards
        # increment: Amount of incrementation

        if self.cam:
            try:
                gain = self.cam.Gain
                # Normal value is around 0
                if set == -1:
                    update = gain.get() + increment
                    if 0 <= update <= 24.1:
                        # Set current value + increment if within bounds
                        gain.set(update)
                elif 0 <= set <= 24.1:
                    # Bounded set
                    gain.set(set)

                self.current_gain = self.cam.Gain.get()
            except Exception as e:
                print(f"Gain Adjust Exception{e}")
        
    @pyqtSlot(int)
    def exp_adj(self, increment: float = 0, incr_up: bool = True, set: int = -1):
        # Exposure adjust. 
        # set: If set is greater than -1, set the camera value to the set value, otherwise increment
        # incr_up: if true, increment upwards, false, increment downwards
        # increment: Amount of incrementation

        if self.cam:
            try:
                # Normal value is 5000 us
                exposure_time = self.cam.ExposureTime
                # Normal value is around 0
                if set == -1:
                    update = exposure_time.get() + increment
                    if 12.957 <= update <= 849046.296:
                        # Set current value + increment if within bounds
                        exposure_time.set(update)
                elif 12.957 <= set <= 849046.296:
                    # Bounded set
                    exposure_time.set(set)

                self.current_exposure = self.cam.ExposureTime.get()
                
            except Exception as e:
                print(f"Exposure Adjust Exception{e}")

        

    def stop(self):
        self.running = False