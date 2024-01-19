try:
    # new location for sip
    # https://www.riverbankcomputing.com/static/Docs/PyQt5/incompatibilities.html#pyqt-v5-11
    from PyQt5 import sip
except ImportError:
    import sip

from PyQt5 import QtWidgets, QtGui
import numpy as np
import pptk
import win32gui, win32con
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QGridLayout(self.widget)
        self.setCentralWidget(self.widget)

        hwnd = win32gui.FindWindowEx(0, 0, None, "viewer")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.window = QtGui.QWindow.fromWinId(hwnd)    
        self.windowcontainer = self.createWindowContainer(self.window, self.widget) 

        self.layout.addWidget(self.windowcontainer, 0, 0, 3, 1)

    def embed_gui(self):
        hwnd = win32gui.FindWindowEx(0, 0, None, "Realtime shell command output")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.window2 = QtGui.QWindow.fromWinId(hwnd)
        self.windowcontainer2 = self.createWindowContainer(self.window2, self.widget)
        self.layout.addWidget(self.windowcontainer2, 3, 0, 1, 1)
        
    def embed_plot(self):
        hwnd = win32gui.FindWindowEx(0, 0, None, "Figure 1")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.window3 = QtGui.QWindow.fromWinId(hwnd)
        self.windowcontainer3 = self.createWindowContainer(self.window3, self.widget)
        self.layout.addWidget(self.windowcontainer3, 0, 1, 3, 1)
        
    
