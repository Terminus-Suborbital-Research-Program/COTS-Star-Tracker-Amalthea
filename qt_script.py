import sys
#from os import path
import os
from PyQt6.QtWidgets import (QApplication, QLabel, QWidget, QMainWindow, QPushButton, 
                            QGridLayout, QSlider, QRadioButton, QButtonGroup, QVBoxLayout, QHBoxLayout, QProgressBar,
                            QLineEdit, QTextEdit, QPlainTextEdit)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QProcess
from threading import Thread
from vmbpy import *
from cam import *
from enum import Enum, auto
from pathlib import Path

class Main_window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera United Multi-tool")

        # Image setup
        im_path = r"images" #r"C:\Users\Ethan\Desktop\Terminus\camera_script\charucotest2" 
        images = []
        if os.path.exists(im_path):
            for image in os.listdir(im_path):
                images.append(os.path.join(im_path, image))
        self.image_label = QLabel()
        if images:
            self.pixmap = QPixmap(images[0]).scaled(648,486) #864, 648
        else:
            self.pixmap = QPixmap()
        self.image_label.setPixmap(self.pixmap) 

        
        # Thread Setup
        self.cam_streamer_thread = CameraStreamer()
        self.cam_streamer_thread.frame_ready.connect(self.update_image)
        self.cam_streamer_thread.file_increment.connect(self.update_file_count_label)

        # Make Q Timer Which controls:
        # File Count update ( Because files can be in the directory ind)
        # File Save Interval (flag signal is sent over to cam thread)

        self.cam_streamer_thread.file_save_enabled_update.connect(self.cam_streamer_thread.file_save_enabled_update_func)


        ## Script Manager - Manage state and lifetime of script processes
        self.script_manager = ScriptManager()
        self.script_manager.script_process.readyReadStandardOutput.connect(self.script_manager.script_output)

        self.script_manager.text_send.connect(self.update_script_text)


        self.Qtimer = QTimer()
        self.Qtimer.timeout.connect(self.trigger_file_save)
        self.Qtimer.start(1000)

        self.file_count = len(images)

        self.load_stylesheet()

        self.setup_graphics()

        self.cam_streamer_thread.start()
        self.cam_streamer_thread.frame_num_update.emit(self.file_count)

    def update_script_text(self, stdout):
        self.output.appendPlainText(stdout)

    def trigger_file_save(self):
        if hasattr(self, 'cam_streamer_thread'):
            self.cam_streamer_thread.file_save_time_trigger_update.emit(True)

    def update_timer(self, milliseconds):
        self.save_time_value_label.setText(str(milliseconds))
        self.Qtimer.setInterval(milliseconds)
    
    def update_image(self, frame):
        self.pixmap =  QPixmap.fromImage(QImage(frame.data, frame.shape[1], frame.shape[0], 
                 QImage.Format.Format_Grayscale8)).scaled(648,486,Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(self.pixmap)

    def update_exposure_label(self, value):
        self.exposure_value_label.setText(str(value))

    def update_gain_label(self, value):
        self.gain_value_label.setText(str(value))

    def update_gamma_label(self, value):
        self.gamma_value_label.setText(str(value/10))

    def update_inc_exposure_label(self, value):
        self.exposure_inc_value_label.setText(str(value))

    def update_inc_gain_label(self, value):
        self.gain_inc_value_label.setText(str(value))

    def update_inc_gamma_label(self, value):
        self.gamma_inc_value_label.setText(str(value))
    
    def update_file_count_label(self, increment):
        self.file_count += increment
        self.file_count_label.setText(f"File Count: {self.file_count}")

    def update_burst_amount_label(self, amount):
        self.burst_amount_value_label.setText(str(amount))

    def update_mode(self):
        if self.trigger_radio.isChecked():
            self.trigger.setEnabled(True)  
        else:
            self.trigger.setEnabled(False)  

        if self.script_run.isEnabled():
            self.script_run.setEnabled(False)  

    def file_sav_dir_update_proccess(self):
        new_dir = self.file_dir_input.text().strip()
        if os.path.exists(new_dir):
            self.file_count = len(os.listdir(new_dir))
        else:
            self.file_count = 0
        self.file_count_label.setText(f"File Count: {self.file_count}")
        
        if new_dir:
            self.cam_streamer_thread.file_save_dir_update.emit(new_dir)
            self.cam_streamer_thread.frame_num_update.emit(self.file_count)

    def closeEvent(self, event):
        self.cam_streamer_thread.stop()
        event.accept()
        super().closeEvent(event)

    def load_stylesheet(self):
        """Load and apply stylesheet from the file."""
        with open("style.qss", "r") as f:
            stylesheet = f.read()
            self.setStyleSheet(stylesheet)

    def setup_graphics(self):
        layout = QGridLayout()

        # Sliders setup
        vbox_container = QWidget()
        vbox_layout = QVBoxLayout()
        vbox_container.setLayout(vbox_layout)

        # Exposure slider
        self.exposure_label = QLabel("Exposure:")
        self.exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self.exposure_value_label = QLabel("20000")
        self.exposure_slider.setMinimum(13)
        self.exposure_slider.setMaximum(481193)
        self.exposure_slider.setValue(20000)
        self.exposure_slider.valueChanged.connect(lambda value: self.cam_streamer_thread.exp_adj(increment=0, incr_up=(value > 0), set=value) )
        self.exposure_slider.valueChanged.connect(self.update_exposure_label)
        exposure_layout = QHBoxLayout()
        exposure_layout.addWidget(self.exposure_label)
        exposure_layout.addWidget(self.exposure_slider)
        exposure_layout.addWidget(self.exposure_value_label)

        # Gain slider
        self.gain_label = QLabel("Gain:")
        self.gain_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_value_label = QLabel("1")
        self.gain_slider.setMinimum(0)
        self.gain_slider.setMaximum(24)
        self.gain_slider.setValue(1)
        self.gain_slider.valueChanged.connect(lambda value: self.cam_streamer_thread.gain_adj(increment=0, incr_up=(value > 0), set=value) )
        self.gain_slider.valueChanged.connect(self.update_gain_label) 
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(self.gain_label)
        gain_layout.addWidget(self.gain_slider)
        gain_layout.addWidget(self.gain_value_label)

        # Gamma slider
        self.gamma_label = QLabel("Gamma:")
        self.gamma_slider = QSlider(Qt.Orientation.Horizontal)
        self.gamma_value_label = QLabel("0.60")
        self.gamma_slider.setMinimum(40)
        self.gamma_slider.setMaximum(240)
        self.gamma_slider.setValue(60)
        self.gamma_slider.valueChanged.connect(lambda value: self.cam_streamer_thread.gamma_adj(increment=0, incr_up=(value > 0), set=(value/100)) )
        self.gamma_slider.valueChanged.connect(self.update_gamma_label) 
        gamma_layout = QHBoxLayout()
        gamma_layout.addWidget(self.gamma_label)
        gamma_layout.addWidget(self.gamma_slider)
        gamma_layout.addWidget(self.gamma_value_label)

        vbox_layout.addLayout(exposure_layout)
        vbox_layout.addLayout(gain_layout)
        vbox_layout.addLayout(gamma_layout)

         # Exposure inc slider
        self.exposure_inc_label = QLabel("Exposure Increment:")
        self.exposure_inc_slider = QSlider(Qt.Orientation.Horizontal)
        self.exposure_inc_value_label = QLabel("0")
        self.exposure_inc_slider.setMinimum(-10000)
        self.exposure_inc_slider.setMaximum(10000)
        self.exposure_inc_slider.setValue(0)
        self.exposure_inc_slider.valueChanged.connect(self.update_inc_exposure_label)
        self.exposure_inc_slider.valueChanged.connect(lambda inc: self.cam_streamer_thread.exposure_inc_update.emit(inc))

        exposure_inc_layout = QHBoxLayout()
        exposure_inc_layout.addWidget(self.exposure_inc_label)
        exposure_inc_layout.addWidget(self.exposure_inc_slider)
        exposure_inc_layout.addWidget(self.exposure_inc_value_label)
        

        # Gain inc slider
        self.gain_inc_label = QLabel("Gain Increment:")
        self.gain_inc_slider = QSlider(Qt.Orientation.Horizontal)
        self.gain_inc_value_label = QLabel("0")
        self.gain_inc_slider.setMinimum(-24)
        self.gain_inc_slider.setMaximum(24)
        self.gain_inc_slider.setValue(0)
        self.gain_inc_slider.valueChanged.connect(self.update_inc_gain_label)
        self.gain_inc_slider.valueChanged.connect(lambda inc: self.cam_streamer_thread.gain_inc_update.emit(inc))

        gain_inc_layout = QHBoxLayout()
        gain_inc_layout.addWidget(self.gain_inc_label)
        gain_inc_layout.addWidget(self.gain_inc_slider)
        gain_inc_layout.addWidget(self.gain_inc_value_label)

        # Gamma inc slider
        self.gamma_inc_label = QLabel("Gamma Increment:")
        self.gamma_inc_slider = QSlider(Qt.Orientation.Horizontal)
        self.gamma_inc_value_label = QLabel("0")
        self.gamma_inc_slider.setMinimum(-100)
        self.gamma_inc_slider.setMaximum(100)
        self.gamma_inc_slider.setValue(0)
        self.gamma_inc_slider.valueChanged.connect(self.update_inc_gamma_label)
        self.gamma_inc_slider.valueChanged.connect(lambda inc: self.cam_streamer_thread.gamma_inc_update.emit(inc))

        gamma_inc_layout = QHBoxLayout()
        gamma_inc_layout.addWidget(self.gamma_inc_label)
        gamma_inc_layout.addWidget(self.gamma_inc_slider)
        gamma_inc_layout.addWidget(self.gamma_inc_value_label)

        inc_vbox_container = QWidget()
        inc_vbox_layout = QVBoxLayout()
        inc_vbox_container.setLayout(inc_vbox_layout)

        inc_vbox_layout.addLayout(exposure_inc_layout)
        inc_vbox_layout.addLayout(gain_inc_layout)
        inc_vbox_layout.addLayout(gamma_inc_layout)
        inc_vbox_layout.setSpacing(0)  
        inc_vbox_layout.setContentsMargins(0, 0, 0, 0)

        # save time slider
        self.save_time_label = QLabel("Millis:")
        self.save_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.save_time_value_label = QLabel("1000")
        self.save_time_slider.setMinimum(0)
        self.save_time_slider.setMaximum(10000)
        self.save_time_slider.setValue(1000)
        self.save_time_slider.valueChanged.connect(self.update_timer)


        self.burst_amount_label = QLabel("Burst Amount:")
        self.burst_amount_slider = QSlider(Qt.Orientation.Horizontal)
        self.burst_amount_value_label = QLabel("1")
        self.burst_amount_slider.setMinimum(1)
        self.burst_amount_slider.setMaximum(30)
        self.burst_amount_slider.setValue(1)
        self.burst_amount_slider.valueChanged.connect(self.update_burst_amount_label)
        self.burst_amount_slider.valueChanged.connect(lambda amount: self.cam_streamer_thread.burst_amount_update.emit(amount))
        

        burst_amount_layout = QHBoxLayout()
        burst_amount_layout.addWidget(self.burst_amount_label)
        burst_amount_layout.addWidget(self.burst_amount_slider)
        burst_amount_layout.addWidget(self.burst_amount_value_label)

        save_time_layout = QHBoxLayout()
        save_time_layout.addWidget(self.save_time_label)
        save_time_layout.addWidget(self.save_time_slider)
        save_time_layout.addWidget(self.save_time_value_label)

        capture_layout = QVBoxLayout()
        capture_layout.addLayout(burst_amount_layout)
        capture_layout.addLayout(save_time_layout)
       

        self.auto_increment_radio = QRadioButton("Auto Increment")
        self.auto_radio = QRadioButton("Auto")
        self.trigger_radio = QRadioButton("Trigger")

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.auto_increment_radio)
        self.mode_group.addButton(self.auto_radio)
        self.mode_group.addButton(self.trigger_radio)

        # Set the default checked button to auto_increment
        self.auto_radio.setChecked(True)

        self.auto_increment_radio.toggled.connect(self.update_mode)
        self.auto_increment_radio.toggled.connect(lambda checked: self.cam_streamer_thread.auto_inc_mode_update.emit(checked))

        self.auto_radio.toggled.connect(self.update_mode)
        self.auto_radio.toggled.connect(lambda checked: self.cam_streamer_thread.auto_mode_update.emit(checked))

        self.trigger_radio.toggled.connect(self.update_mode)
        self.trigger_radio.toggled.connect(lambda checked: self.cam_streamer_thread.trigger_mode_update.emit(checked))

        # Trigger button (Initially disabled)
        self.trigger = QPushButton("Trigger")
        self.trigger.setEnabled(False)  
        self.trigger.clicked.connect(lambda pressed: self.cam_streamer_thread.trigger_update.emit(pressed))
        

        
        self.file_save_button = QRadioButton("Enable File Saving")
        self.file_save_button.toggled.connect(lambda checked: self.cam_streamer_thread.file_save_enabled_update.emit(checked))

        button_layout = QVBoxLayout()
        button_layout.setSpacing(0)  
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.file_save_button)
        button_layout.addWidget(self.auto_increment_radio)
        button_layout.addWidget(self.auto_radio)
        button_layout.addWidget(self.trigger_radio)
        button_layout.addWidget(self.trigger)
        


        file_save_layout = QVBoxLayout()
        file_save_layout.setSpacing(0) 
        file_save_layout.setContentsMargins(0, 0, 0, 0) 


        self.file_dir_input = QLineEdit()
        self.file_dir_input.setPlaceholderText(r"images/")

        self.file_dir_button = QPushButton("Change Save Location")
        self.file_dir_button.clicked.connect(self.file_sav_dir_update_proccess)
        self.file_count_label = QLabel(f"File Count: {self.file_count}")

        # Script Run Button
        self.script_run = QPushButton("Run Script")
        self.script_run.clicked.connect(self.script_manager.run_script)
        # self.script_run.setEnabled(False)  ## Remove later
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)

        file_save_layout.addWidget(self.script_run)
        file_save_layout.addWidget(self.output) ##
        file_save_layout.addWidget(self.file_count_label)
        file_save_layout.addWidget(self.file_dir_input)
        file_save_layout.addWidget(self.file_dir_button)

        # Adding image and sliders to the main grid layout
        layout.addWidget(self.image_label, 0, 0, 2, 3)
        layout.addWidget(vbox_container, 3, 0, 1, 3)
        layout.addWidget(inc_vbox_container,0,3,1,3)

        # Add button layout to grid
        layout.addLayout(button_layout, 3, 3, 1, 3) 
        layout.addLayout(file_save_layout, 2, 3, 1, 3)
        layout.addLayout(capture_layout,1,3,1,3)

        # Set up the main widget
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.show()

class ScriptType(Enum):
        TETRA = auto()
        STARCAT = auto()
        STARTRACK = auto()

class ScriptManager(QObject):

    text_send = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.script_process = QProcess()

        self.script_state = ScriptType.TETRA

        

        self.config = {
            'image_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\external\New_trip', #r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\external\New_trip' # test'
            'tetra_script_path': r'py_src\tools\camera_calibration\tetra\run_tetra_cal_scripting.py',
            'star_catalog_creator_path':  r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\py_src\tools\star_catalog_creator_scripting.py',
            'image_proccessing_script_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\examples\process_image_set_scripting.py',
            'graphics': "False",
            'image_file_extension': '.jpg', # .tiff
            'calibration_file_name': 'default',
            'data_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\data'
        }
    
    def run_script(self):
        # This should be passed in from the GUI where these values can be customzied in later implementations
        self.solves = []
        self.solve_rate = ""
        self.rms = ""
        self.tetra_cal()

       
    

    def script_output(self):
        data = self.script_process.readAllStandardOutput()
        output = bytes(data).decode("utf8")

        for stdout in output.splitlines():
            print(stdout)
            self.text_send.emit(stdout)

            match self.script_state:

                case ScriptType.TETRA:
                    if stdout.startswith("Success:"):
                        success_file_path = stdout.split(":", 1)[1].strip()
                        print(f"Cleaned Line:{success_file_path}")
                        file_name = Path(success_file_path)
                        self.solves.append(file_name.name)
                    elif stdout.startswith("Solve Rate:"):
                        self.solve_rate = stdout.split(":", 1)[1].strip()
                    elif stdout.startswith("RMS:"):
                        self.rms = stdout.split(":", 1)[1].strip()

                    if 'If you are satisfied with the results' in stdout:
                            # Determine file save
                            [os.unlink(f"{self.config['image_path']}\{image}") for image in os.listdir(self.config['image_path']) if image not in self.solves]
                            self.solves.clear()

                            if (float(self.solve_rate) > 0.5) and (float(self.rms) < 1.0): ## Add in 
                                self.script_process.write(f"{self.config['calibration_file_name']}\n".encode()) 
                                self.script_state = ScriptType.STARCAT
                                time.sleep(1.0)
                                self.script_end()

                                self.star_cat()
                            else:
                                self.script_process.write('no\n'.encode())
                                self.tetra_cal()

                            

                case ScriptType.STARCAT:
                    if '...catalog creation complete' in stdout:
                        self.script_end()
                        self.script_state = ScriptType.STARTRACK
                        self.star_track()


                case ScriptType.STARTRACK:
                    if 'THE END' in stdout:
                        [os.unlink(f"{self.config['data_path']}\{image}") for image in os.listdir(self.config['data_path']) if self.config['image_file_extension'] in image]
                        self.script_end()

                        
                
    def tetra_cal(self):
        self.script_process.start("python", [   "-u",
                                                self.config['tetra_script_path'], 
                                                self.config['image_path'], 
                                                self.config['image_file_extension']])

    def star_cat(self):
        self.script_process.start("python", [ "-u",
                                                 self.config['star_catalog_creator_path'],
                                                 self.config['calibration_file_name']
                                                ])

    def star_track(self,):
        [shutil.copy(f"{self.config['image_path']}\{image}", self.config['data_path']) for image in os.listdir(self.config['image_path'])]
        calibration_file_path = r'{}\cam_config\{}.json'.format(self.config['data_path'], self.config['calibration_file_name'])
        self.script_process.start("python", [ "-u",
                                                 self.config['image_proccessing_script_path'],
                                                 calibration_file_path,
                                                 self.config['image_file_extension'],
                                                 self.config['graphics']
                                                ])
        
    def script_end(self):
        self.script_process.terminate()
        if not self.script_process.waitForFinished(3000): 
            self.script_process.kill() 
            self.script_process.waitForFinished()
            
       

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main_window()
    sys.exit(app.exec())
