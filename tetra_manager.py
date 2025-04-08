import sys
#from os import path
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer, QProcess
from enum import Enum, auto
from pathlib import Path
import shutil
import time

class ScriptType(Enum):
        TETRA = auto()
        STARCAT = auto()
        STARTRACK = auto()

class ScriptManager(QObject):

    def __init__(self):
        super().__init__()

        self.script_process = QProcess()

        self.script_state = ScriptType.TETRA

         # Connect process signals
        self.script_process.readyReadStandardOutput.connect(self.script_output)

        

        self.config = {
            'image_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\external\New_trip', 
            'tetra_script_path': r'py_src\tools\camera_calibration\tetra\run_tetra_cal_scripting.py',
            'star_catalog_creator_path':  r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\py_src\tools\star_catalog_creator_scripting.py',
            'image_proccessing_script_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\examples\process_image_set_scripting.py',
            'graphics': "False",
            'image_file_extension': '.jpg', # .tiff
            'calibration_file_name': 'default',
            'data_path': r'C:\Users\Ethan\Desktop\COTS-Star-Tracker-Amalthea\data'
        }
    
    def run_script(self):
        # self.file_dir_input.text().strip()

        # This should be passed in from the GUI where these values can be customzied in later implementations
        self.solves = []
        self.solve_rate = ""
        self.rms = ""
        self.tetra_cal()

       
    

    def script_output(self):
        data = self.script_process.readAllStandardOutput()
        output = bytes(data).decode("utf8")
        # print(f"Entry: {stdout}")
        # self.output.appendPlainText(stdout) Worry about GUI display later
        for stdout in output.splitlines():
            print(stdout)
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

                            if (float(self.solve_rate) > 0.5) and (float(self.rms) < 1.0): ## Change this to 0.5 later
                                self.script_process.write(f"{self.config['calibration_file_name']}\n".encode()) #.encode()
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
    from PyQt6.QtCore import QCoreApplication
    
    app = QCoreApplication(sys.argv)
    
    manager = ScriptManager()
    manager.run_script()
    
    sys.exit(app.exec())
            
       