from tifffile import imread, imsave
import numpy as np
#import matplotlib.colors
import time

import threading
from pynput import mouse

#from visualizer_gui import *
from mouse_business import *

# with Python 3.7: downloaded from https://github.com/mhammond/pywin32/releases
#from win32.win32gui import FindWindow, GetWindowRect

import os
import sys
#import matplotlib.pyplot as plt
from visualizer_gui import *
from visualizer_3d import *
#from PyQt5 import QtWidgets, QtGui
#from form import *

visualizer = Visualizer_3D()

visualizer.add_data()
visualizer.delete_temp_files()

jerry = MouseBusiness(visualizer)

#app = QtWidgets.QApplication(sys.argv)
#app.setStyle("fusion")
"""
form = MainWindow()
form.setWindowTitle('Pyfix3d')
form.setGeometry(100, 100, 900, 1200)
form.show()
"""


gui = VisualizerGui(visualizer)
#form.embed_gui()

# Collect events until released

with mouse.Listener(
        on_move = jerry.on_move,
        on_click = jerry.on_click,
        on_scroll = jerry.on_scroll) as listener:
           
    gui.run_loop()

listener.join()

sys.exit(app.exec_())
exit()


