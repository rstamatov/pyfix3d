from PyQt5 import QtWidgets, QtGui
import numpy as np
import pptk
import win32gui, win32con
import sys

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(widget)
        self.setCentralWidget(widget)

        self.cloudpoint = np.random.rand(100, 3)
        self.v = pptk.viewer(self.cloudpoint)
        hwnd = win32gui.FindWindowEx(0, 0, None, "viewer")
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.window = QtGui.QWindow.fromWinId(hwnd)    
        self.windowcontainer = self.createWindowContainer(self.window, widget)

        layout.addWidget(self.windowcontainer, 0, 0)

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("fusion")
    form = MainWindow()
    form.setWindowTitle('PPTK Embed')
    form.setGeometry(100, 100, 600, 500)
    form.show()
    sys.exit(app.exec_())
