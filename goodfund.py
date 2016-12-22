from PyQt5.QtWidgets import QApplication
import sys
import gf_ui

app = QApplication(sys.argv)

w = gf_ui.GF_MainWindow()
w.show()

app.exec_()

