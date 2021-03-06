#!/usr/bin/python
# -*- coding: ascii -*-
"""
ooooooooooo        oooo oooo                     ooooo                .o8
`888'    `8        `888 `888                     `888'               "888
 888      .ooooo.   888  888   .ooooo.   .oooo.o  888        .oooo.   888oooo.
 888ooo8 d88' `88b  888  888  d88' `88b d88(  "8  888       `P  )88b  d88' `88b
 888   " 888ooo888  888  888  888ooo888 `"Y88b.   888        .oP"888  888   888
 888     888    .o  888  888  888    .o o.  )88b  888     o d8(  888  888   888
o888o    `Y8bod8P' o888oo888o `Y8bod8P' 8""888P' o888ooood8 `Y888""8o `Y8bod8P'

@summary
@author:       Sigve Karolius
@organization  Department of Chemical Engineering, NTNU, Norway
@contact       sigve.karolius@ntnu.no
@license       Free (GPL.v3) !!! Distributed as-is !!!
@requires      Python 2.7.x or higher
@since         2017-06-16
@version       0.1

"""

#from PyQt5.QtCore import (QTimer, pyqtSignal, QThread, QObject, pyqtProperty,
#                         Qt, pyqtSlot)
#from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QWidget, QDialog)
#from PyQt5.QtGui import QIcon, QPixmap

from PyQt4.QtCore import (QTimer, pyqtSignal, QThread, QObject, pyqtProperty,
                         Qt, pyqtSlot)

from PyQt4.QtGui import (QIcon, QPixmap, QApplication, QMainWindow, QWidget,
                         QAction, QDialog, QMessageBox)


from felleslab.communication import AdaptorBaseClass
from collections import defaultdict, deque
from time import sleep, time
from serial import SerialException


try:
    _encoding = QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


# Parent Widget class ------------------------------------------------------- #
class QFellesWidgetBaseClass(QWidget):
    """
    @brief     Base class for **all** FellesLab widgets
    """

    newSample = pyqtSignal(str)
    getSample = pyqtSignal(float, name="PerformSampling")

    meta = { "type": "Dummy",
             "name": "Top",
             "unit": "[C]",
             "channel" : 0,
             "portname" : "/dev/ttyUSB0",
             "slaveaddress": 1,
             "baudrate" : 19200,
    }
    _slave = None

    ___refs___ = []
    ___ports___ = defaultdict(list)

    def __init__(self, parent=None):
        """
        """
        super(QFellesWidgetBaseClass, self).__init__(parent)
        self.__class__.___refs___.append(self)
        self._id = hex(id(self))
        self.events = [ ]

        if parent:
            parent.parent().initialiseSlaves.connect(self.setSlave)

        self.initUi(parent)                         # Initialise user interface
        self.show()                          # Display Widget in User Interface

    def initUi(self, parent=None):
        """
        @brief  Method instantiating widget in the UI
        """
        raise NotImplementedError("You idiot...")

    def closeEvent(self, event=None):
        print("- - - -")

    @pyqtSlot(str, int)
    def setSlave(self, portname=None, slaveaddress=None):
        """
        @param  portname      str (optional)  RS485 connection port
        @param  slaveaddress  int (optional)  Address of unit in the network
        """
        if self._slave:
            self.slave = self.__class__._slave(**self.meta)
            self.__class__.___ports___[str(self.meta["portname"])].append(self._id)
            self.getSample.connect(self.setSample)
            self.onInit()

    def onInit(self):
        pass

    @pyqtSlot()
    def setSample(self):
        raise NotImplementedError("You idiot...")

    def onEvent(self):
        for event in self.events:
            event.emit()

    @pyqtProperty(str)
    def portname(self):
        return self.meta["portname"]

    @portname.setter
    def baudrate(self, string):
        self.meta["portname"] = string

    @pyqtProperty(int)
    def channel(self):
        return self.meta["channel"]

    @channel.setter
    def channel(self, val):
        self.meta["channel"] = val

    @pyqtProperty(int)
    def baudrate(self):
        return self.meta["baudrate"]

    @baudrate.setter
    def baudrate(self, string):
        self.meta["baudrate"] = string

    @classmethod
    def findWidget(cls, _id):
        """
        @brief   Locate a widget based on the _id
        """
        for obj in cls.___refs___:
            if obj._id != _id:
                continue
            return obj

    @classmethod
    def findWidgetsAttachedToPort(cls, portname):
        """
        @brief   Locate a widget based on the _id
        """
        return [cls.findWidget(_id) for _id in cls.___ports___[portname]]



# Thread class -------------------------------------------------------------- #
class FellesThread(QThread):
    RATE = 0.1

    def __init__ (self, port):
        super(FellesThread, self).__init__()
        print("Initialising sampling thread for port %s" %port)
        self.widgets = QFellesWidgetBaseClass.findWidgetsAttachedToPort(port)

        self.portname = port
        self.daemon = True                              # Use a daemonic thread

        self._data = defaultdict(dict)
        self.events = []

        self.started = time()                                  # Set Start time
        self.start()                                             # Start Thread

    def sample(self, timestamp):
        """
        @brief     Loop over all slaves obtaining MVs
        @param   timestamp  float  (required)   Time when sampling is performed 
        """
        for widget in self.widgets:
            try:
                widget.getSample.emit(timestamp)

            except IOError as e:
                print("Failed to read measurement:\n\t\t\t\t %s" %(e))

            except SerialException as e:
                print("Serial Exception")
                raise e

            except ValueError as e:
                print("Value Error")
                raise e

            except Exception as e:
                print("Exception")
                raise e

    def event(self, timestamp):
        """
        @brief     Perform events, such as control actions or user actions
        """
        for widget in self.widgets:
            try:
                widget.onEvent()
            except Exception as e:
                print e

    def run(self):
        """
        @brief     Method performing the sampling (executed by `self.start()`).
        """
        while True:
            dt = time() - self.started
            self.sample(dt)                  # Perform sampling for all widgets
            self.event(dt)                                      # Handle events
            sleep(0.5)                                  # Put Thread "to sleep"
        print("Thread is dying")

# Gui class ----------------------------------------------------------------- #
class FellesGui(QMainWindow):
    """
    """
    initialiseSlaves = pyqtSignal()
    quit_sampling = pyqtSignal()
    closing = pyqtSignal()

    def __init__(self, Ui_MainWindow, timeout=1000):
        super(FellesGui, self).__init__()

        self.setAttribute(Qt.WA_DeleteOnClose)

        exitAction = QAction('Quit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Quit application')
        print("Push 'Ctrl+Q' to quit the application")
        exitAction.triggered.connect(self.close)

        # Create Widget for the purpose of updating the widgets periodically
        #self.timer = QTimer()
        #self.timer.timeout.connect(self.paintEvent)
        #self.timer.start(timeout)

        # --> Instantiate UI  !!! This is where the widgets are initiated !!!
        self.buildUi(Ui_MainWindow)

        # --> Setup the Menu Bar
        fileMenu = self.menuBar().addMenu('&File')
        fileMenu.addAction(exitAction)

        # --> Order widgets to connect to their slaves
        self.initialiseSlaves.emit()

        # -->  Initialise "Threads" performing the sampling
        ports = QFellesWidgetBaseClass.___ports___.keys()
        self.sampling_threads = [ FellesThread(port) for port in ports ]

        #self.statusBar().showMessage.connect(FellesThread.sample_failed)
        self.statusBar().showMessage('Idling...')

    def buildUi(self, Ui_MainWindow):
        self.statusBar().showMessage('Initialising Modules')
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    def closeEvent(self, event):
        """ Method executed when application is closed
        """
        txt   = "Are you sure to quit?"
        reply = QMessageBox.question(self, 'Message', txt,
                                   QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

"""
        # option #1
        # if you want to trigger a cleanup specifically when
        # this widget is closed, as opposed to destroyed
        print(dir(self.layout().widget))
        for i in xrange(self.layout().count()):
            item = self.layout.itemAt(i)
            widget = item.widget()       
            if widget:
                print("----")
                try:
                    widget.close()
                except:
                    pass
        #print(dir(event))
        # Or Option #3 - emit a custom signal
        self.closing.emit()

        super(FellesGui, self).closeEvent(event)
        event.accept()

#    def paintEvent(self, event=None, *args):
#        pass
"""

def run_gui(Ui_MainWindow):
    """ Function launching a application
    """
    import sys
    app = QApplication(sys.argv)
    myapp = FellesGui(Ui_MainWindow)
    myapp.show()
    return sys.exit(app.exec_())


# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: #
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    myapp = FellesGui()
    myapp.show()
    sys.exit(app.exec_())
