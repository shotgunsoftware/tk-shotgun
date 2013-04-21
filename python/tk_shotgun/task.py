"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------
"""
import tank
import os
import sys
import threading

from tank.platform.qt import QtCore, QtGui

class Task(QtCore.QObject):
    """
    This is a wrapper class which allows us to run tank commands
    inside the QT universe. This approach is handy when an engine needs
    to start up a qt event loop as part of its initailization.
    """
    finished = QtCore.Signal()

    def __init__(self, engine, callback):
        QtCore.QObject.__init__(self)        
        self._callback = callback
        self._engine = engine
        
    def run_command(self):
        # execute the callback
        self._callback()

        # broadcast that we have finished this command
        if not self._engine.has_received_ui_creation_requests():
            # while the app has been doing its thing, no UIs were
            # created (at least not any tank UIs) - assume it is a 
            # console style app and that the end of its callback
            # execution means that it is complete and that we should return 
            self.finished.emit()
        