from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel
import base64, gui.frame

class ImageButton(QLabel):

    def __init__(self, parent, name):
        QLabel.__init__(self, parent)
        self.parent = parent
        self.setMouseTracking(True)
        self.count = 0
        self.normal = QPixmap(gui.frame.resource_path('resources/%s/normal.png' % name))
        self.hover = QPixmap(gui.frame.resource_path('resources/%s/hover.png' % name))
        self.depressed = QPixmap(gui.frame.resource_path('resources/%s/depressed.png' % name))
        self.isHovering = False
        self.isDepressed = False
        self.enabled = True
        self.setPixmap(self.normal)
        self.resize(self.normal.size())
        self.setStyleSheet('background:transparent;')

    def SetHoverBitmap(self, bitmap):
        self.hover = bitmap

    def SetDepressedBitmap(self, bitmap):
        self.depressed = bitmap

    def enterEvent(self, event):
        self.isHovering = True
        if self.hover and not self.isDepressed and self.enabled:
            self.setPixmap(self.hover)
            self.repaint()

    def leaveEvent(self, event):
        self.isHovering = False
        if not self.isDepressed:
            self.setPixmap(self.normal)
            self.repaint()

    def mousePressEvent(self, event):
        if not self.enabled:
            return
        self.isDepressed = True
        if self.depressed:
            self.setPixmap(self.depressed)

    def mouseReleaseEvent(self, event):
        if not self.enabled:
            self.setPixmap(self.normal)
            self.repaint()
            return
        self.isDepressed = False
        if self.isHovering and self.hover:
            self.setPixmap(self.hover)
            self.repaint()
        else:
            self.setPixmap(self.normal)
            self.repaint()
        if self.enabled:
            self.Clicked()

    def Clicked(self):
        pass


class XButton(ImageButton):

    def __init__(self, parent):
        ImageButton.__init__(self, parent, 'XButton')

    def Clicked(self):
        self.parent.frame.close()


class MButton(ImageButton):

    def __init__(self, parent):
        ImageButton.__init__(self, parent, 'MButton')

    def Clicked(self):
        self.setPixmap(self.normal)
        self.repaint()
        self.parent.frame.setWindowState(Qt.WindowMinimized)


import localizer

class GoButton(ImageButton):

    def __init__(self, parent):
        ImageButton.__init__(self, parent, 'GoButton')

    def Clicked(self):
        credentials = (
         self.parent.ubox.text(), self.parent.pbox.text())
        self.parent.output.put(credentials, block=True, timeout=1.0)
        self.parent.SetLoginControlsEditable(False)
