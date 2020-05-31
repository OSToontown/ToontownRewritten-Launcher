#! /usr/bin/env python3
from launcher import TTRLauncher
from gui.frame import LauncherFrame
from PyQt5.QtWidgets import QApplication
import multiprocessing
from launcher import localizer, messagetypes
import traceback
import sys
import os

class Process(multiprocessing.Process):
    pass

def run_launcher(guiToLauncher, launcherToGui):        
    launcher = TTRLauncher(input=guiToLauncher, output=launcherToGui)
    try:
        launcher.start()
    except: 
        # We caught an exception! Let's write info to crash.txt and tell the GUI process.
        eType, value, trace = sys.exc_info()
        with open('crash.txt', 'w') as f:
            f.write('%s: %s\n' % (eType.__name__, value))
            traceback.print_tb(trace, None, f)
        launcherToGui.put((messagetypes.LAUNCHER_ERROR, localizer.ERR_UnknownTraceback, True))


if __name__ == '__main__': # Needed for multiprocessing to not fail horrifically. Don't try to remove.
    multiprocessing.freeze_support() # Needed on Windows for PyInstaller...

    guiToLauncher = multiprocessing.Queue()
    launcherToGui = multiprocessing.Queue()

    launcherProcess = Process(target=run_launcher, name="Launcher-Thread", args=(guiToLauncher, launcherToGui))
    launcherProcess.daemon = True
    launcherProcess.start()

    app = QApplication(sys.argv)
    frame = LauncherFrame(localizer.GUI_WindowTitle, launcherToGui, guiToLauncher)
    sys.exit(app.exec_())
