from PyQt5.QtCore import QUrl, QTimer, Qt
from PyQt5.QtGui import QDesktopServices, QPixmap, QIcon
from PyQt5.QtWidgets import QLabel, QMainWindow, QProgressBar, QLineEdit, QMessageBox, QInputDialog
#No web engine support yet
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from gui.buttons import *
from launcher import messagetypes, localizer, settings
import json, webbrowser, base64, sys, os, traceback
import http.client as httplib
LAUNCHER_CSS = '\nQProgressBar\n{\n    color: white;\n}\nQMainWindow\n{\n    background: transparent;\n    font-family: Arial;\n}\n'
LINEEDIT_CSS = '\nQLineEdit {\n    font-size: 13px;\n    border: none;\n    background-color: #181818;\n    color: white;\n}\n'
LABEL_CSS = '\nQLabel\n{\n    color:white;\n    font-size: 13px;\n}\n'

def resource_path(filename):
    #Intended for local installs and snap applications
    if os.getenv("TTR_LAUNCHER_RESOURCES") is not None:
        print(os.path.join(os.getenv("TTR_LAUNCHER_RESOURCES"), filename))
        return os.path.join(os.getenv("TTR_LAUNCHER_RESOURCES"), filename)
    print(os.path.join(".", filename))
    return os.path.join(".", filename) #A default path

#Hack to open in system browser
class WebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url,  _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True

class HtmlView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        QWebEngineView.__init__(self, *args, **kwargs)
        self.setPage(WebEnginePage(self))
        s = QWebEngineSettings.globalSettings()
        s.setAttribute(QWebEngineSettings.ShowScrollBars, False)


class LauncherPanel(QLabel):
    LAUNCHER_DATA_CHECK_INTERVAL = 100

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)
        self.setMouseTracking(True)
        self.resize(900, 680)
        self.frame = parent
        self.xButton = XButton(self)
        self.xButton.move(740, 49)
        bg = QPixmap(resource_path('resources/Background.png'))
        self.setPixmap(bg)
        self.newsTitle = QLabel(self)
        self.newsTitle.move(180, 140)
        self.newsTitle.resize(100, 100)
        self.newsTitle.setStyleSheet(LABEL_CSS)
        self.newsTitle.setText('<h1>News</h1>')
        self.newsTitle.mouseReleaseEvent = self.mouseReleaseEvent
        self.news = HtmlView(self)
        self.news.move(67, 215)
        self.news.resize(300, 120)
        self.news.setUrl(QUrl('https://toontownrewritten.com/news/launcher'))
        self.news.setAttribute(Qt.WA_TranslucentBackground)
        self.news.setStyleSheet('background:transparent')
        page = self.news.page()
        page.setBackgroundColor(Qt.transparent)
        #TODO: Need to draw surlee in front of the qtwebengine
        #surlee = QPixmap(resource_path('resources/Surlee.png'))
        #self.surlee = QLabel(self)
        #self.surlee.resize(213, 302)
        #self.surlee.move(206, 98)
        #self.surlee.setPixmap(surlee)
        #self.surlee.show()
        #self.surlee.raise_()
        #page.stackUnder(self.surlee)
        self.label = QLabel(self)
        self.label.move(548, 140)
        self.label.resize(187, 75)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.label.mouseReleaseEvent = self.mouseReleaseEvent
        self.label.setStyleSheet(LABEL_CSS)
        self.label.setWordWrap(True)
        self.progress = QProgressBar(self)
        self.progress.resize(175, 15)
        self.progress.move(548, 200)
        self.progress.setRange(0, 100)
        self.mButton = MButton(self)
        self.mButton.move(685, 49)
        self.ubox = QLineEdit(self)
        self.ubox.move(515, 323)
        self.ubox.resize(214, 29)
        self.ubox.setStyleSheet(LINEEDIT_CSS)
        self.pbox = QLineEdit(self)
        self.pbox.move(515, 364)
        self.pbox.resize(214, 29)
        self.pbox.setStyleSheet(LINEEDIT_CSS)
        self.pbox.setEchoMode(QLineEdit.Password)
        self.goButton = GoButton(self)
        self.goButton.move(747, 345)
        self.dragging = False
        self.ubox.returnPressed.connect(self.OnEnterPressed)
        self.pbox.returnPressed.connect(self.OnEnterPressed)
        timer = QTimer(self)
        timer.setInterval(self.LAUNCHER_DATA_CHECK_INTERVAL)
        timer.timeout.connect(self.PollInput)
        timer.start()
        self.versionLabel = QLabel(self)
        self.versionLabel.move(100, 130)
        self.versionLabel.resize(200, 23)
        self.versionLabel.setStyleSheet(LABEL_CSS)
        self.versionLabel.mouseReleaseEvent = self.mouseReleaseEvent
        version = 'dev'
        if settings.Version is not None:
            version = settings.Version
        self.versionLabel.setText(localizer.GUI_VersionLabel % version)
        self.versionLabel.show()
        sys.excepthook = self.handleException
        self.show()
        self.progress.hide()
        #self.surlee.show()
        return

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.lastMousePos = event.globalPos()
        self.dragging = True

    def mouseMoveEvent(self, event):
        if self.dragging:
            mousePos = event.globalPos()
            mouseDelta = mousePos - self.lastMousePos
            self.parentWidget().move(self.parentWidget().pos() + mouseDelta)
            self.lastMousePos = mousePos

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self.dragging = False

    def leaveEvent(self, event):
        self.dragging = False

    def PollInput(self):
        try:
            self.HandleInput(self.input.get(block=False))
        #lol
        except:
            pass

    def HandleInput(self, data):
        if type(data) == tuple and len(data) > 0:
            msg = data[0]
        else:
            if type(data) == int:
                msg = data
        if msg == messagetypes.LAUNCHER_ERROR:
            details = data[1]
            box = QMessageBox(QMessageBox.Critical, localizer.GUI_Error, data[1], QMessageBox.Ok, parent=self).exec_()
            if len(data) > 2 and data[2]:
                self.frame.close()
            self.SetLoginControlsEditable(True)
        else:
            if msg == messagetypes.LAUNCHER_VERSION_UPDATE:
                version = data[1]
                changelog = data[2]
                url = data[3]
                QMessageBox(QMessageBox.Critical, localizer.LauncherUpdateHeader, localizer.LauncherUpdateAvailabile % (version, changelog), QMessageBox.Ok, parent=self).exec_()
                webbrowser.open(url)
                self.frame.close()
            else:
                if msg == messagetypes.LAUNCHER_REQUEST_TFA:
                    dlg = QInputDialog(parent=self)
                    dlg.setLabelText(data[1])
                    dlg.setWindowTitle(localizer.GUI_TFA)
                    dlg.setWhatsThis(localizer.GUI_TFAWhatsThis)
                    dlg.resize(360, 130)
                    ok = dlg.exec_()
                    if ok:
                        val = dlg.textValue()
                        self.output.put(str(val), block=True, timeout=1.0)
                    else:
                        self.output.put(None, block=True, timeout=1.0)
                        self.SetLoginControlsEditable(True)
                else:
                    if msg == messagetypes.LAUNCHER_STATUS:
                        self.SetStatusLabel(data[1])
                    else:
                        if msg == messagetypes.LAUNCHER_PROGRESS:
                            pcent = int(data[1])
                            if pcent == -1:
                                self.progress.hide()
                            else:
                                self.progress.show()
                                self.progress.setValue(pcent)
                        else:
                            if msg == messagetypes.LAUNCHER_PLAY_RETRY:
                                dlg = QMessageBox(QMessageBox.Question, localizer.GUI_CrashedTitle, localizer.GUI_CrashedQuestion, QMessageBox.No | QMessageBox.Yes, parent=self)
                                dlg.setDefaultButton(QMessageBox.Yes)
                                val = dlg.exec_()
                                if val == QMessageBox.Yes:
                                    self.output.put(True, block=True, timeout=1.0)
                                else:
                                    self.frame.close()
                            else:
                                if msg == messagetypes.LAUNCHER_ENABLE_CONTROLS:
                                    self.SetLoginControlsEditable(True)
                                else:
                                    if msg == messagetypes.LAUNCHER_CLEAR_PASSWORD:
                                        self.pbox.setText('')
                                    else:
                                        if msg == messagetypes.LAUNCHER_HIDE:
                                            self.frame.hide()
                                        else:
                                            if msg == messagetypes.LAUNCHER_SHOW:
                                                self.frame.show()
                                            else:
                                                if msg == messagetypes.LAUNCHER_EXIT:
                                                    self.frame.close()
        return

    def OnEnterPressed(self):
        self.goButton.Clicked()

    def SetLoginControlsEditable(self, areEditable):
        self.ubox.setDisabled(not areEditable)
        self.pbox.setDisabled(not areEditable)
        self.goButton.enabled = areEditable
        if areEditable:
            self.progress.hide()
            self.SetStatusLabel('')

    def SetStatusLabel(self, text):
        self.label.setText("<p style='line-height: 25px;'>%s</p>" % text)

    def handleException(self, eType, value, trace):
        with open('crash.txt', 'w') as (f):
            f.write('%s: %s\n' % (eType.__name__, value))
            traceback.print_tb(trace, None, f)
        self.input.put((messagetypes.LAUNCHER_ERROR, localizer.ERR_UnknownTraceback, True))
        return


class LauncherFrame(QMainWindow):

    def __init__(self, title, input, output):
        QMainWindow.__init__(self, parent=None, flags=Qt.FramelessWindowHint)
        self.setWindowTitle(title)
        self.resize(900, 680)
        window_icon = QIcon()
        #icons = [
        # 48, 64, 128, 256]
        #for icon_size in icons:
        #    window_icon.addFile(resource_path('resources/icons/watch-icon-%d' % icon_size))
        window_icon.addFile(resource_path('resources/icons/eyes'))
        
        self.setWindowIcon(window_icon)
        self.setStyleSheet(LAUNCHER_CSS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.panel = LauncherPanel(self)
        self.panel.output = output
        self.panel.input = input
        self.show()
        return
