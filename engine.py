# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Implements the Shotgun Engine in Tank, e.g the client side script runner foundation which handles
incoming Tank Action Requests.

"""

from tank.platform import Engine
import tank
import sys
import os
import logging



class ShotgunEngine(Engine):
    """
    An engine for Shotgun. This is normally called via the tank engine.    
    """
        
    def __init__(self, *args, **kwargs):
        # passthrough so we can init stuff
        
        # the has_ui flag indicates that there is an active QApplicaton running and that UI
        # code can be rendered.
        self._has_ui = False
        
        # the has_qt flag indicates that the QT subsystem is present and can be started 
        self._has_qt = False
        
        self._ui_created = False
        
        # set up a very basic logger, assuming it will be overridden
        self._log = logging.getLogger("tank.tk-shotgun")
        self._log.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        formatter = logging.Formatter()
        ch.setFormatter(formatter)
        self._log.addHandler(ch)
        
        # see if someone is passing a logger to us inside tk.log
        if len(args) > 0 and isinstance(args[0], tank.Tank):
            if hasattr(args[0], "log"):
                # there is a tank.log on the API instance.
                # hook this up with our logging
                self._log = args[0].log

        super(ShotgunEngine, self).__init__(*args, **kwargs)
        
    def init_engine(self):
        """
        Init.
        """
        # if debug logging is turned on in the settings for this app, make sure
        # that the logger accepts the debug stream
        if self.get_setting("debug_logging", False):
            self._log.setLevel(logging.DEBUG)
        
                
    @property
    def has_ui(self):
        return self._has_ui
                
    def has_received_ui_creation_requests(self):
        """
        returns true if one or more windows have been requested
        via the show_dialog methods
        """
        return self._ui_created
                
    ##########################################################################################
    # command handling

    def execute_command(self, cmd_key):
        """
        Executes a given command.
        """
        cb = self.commands[cmd_key]["callback"]
        
        if not self._has_qt:
            # QT not available - just run the command straight
            return cb()
        
        else:
            # start the UI
            self.__setup_ui(cb)

    def execute_old_style_command(self, cmd_key, entity_type, entity_ids):
        """
        Executes an old style shotgun specific command. Old style commands 
        are assumed to not use a UI.
        """
        cb = self.commands[cmd_key]["callback"]
        
        if not self._has_qt:
            # QT not available - just run the command straight
            return cb(entity_type, entity_ids)
        
        else:
            # wrap the callback
            cb_wrapped = lambda et=entity_type, ids=entity_ids: cb(et, ids)    
            # start the UI
            self.__setup_ui(cb_wrapped)

    def __setup_ui(self, callback):
        """
        Starts a QApplication and initializes the UI.
        """
        from tank.platform.qt import QtCore, QtGui
        
        # we got QT capabilities. Start a QT app and fire the command into the app
        tk_shotgun = self.import_module("tk_shotgun")
                
        t = tk_shotgun.Task(self, callback)
        
        # start up our QApp now
        qt_application = QtGui.QApplication([])        
        qt_application.setWindowIcon(QtGui.QIcon(self.icon_256))
        self._initialize_dark_look_and_feel()

        # now we have a working UI!
        self._has_ui = True        
        
        # when the QApp starts, initialize our task code 
        QtCore.QTimer.singleShot(0, t.run_command)
           
        # and ask the main app to exit when the task emits its finished signal
        t.finished.connect(qt_application.quit)
           
        # start the application loop. This will block the process until the task
        # has completed - this is either triggered by a main window closing or
        # byt the finished signal being called from the task class above.
        qt_application.exec_()


                
    ##########################################################################################
    # logging interfaces

    # make sure every line of the logging output starts with some sort of 
    # <html> tags (e.g. first char is <) - the shotgun code looks for this
    # and will remove any other output. 

    def log_debug(self, msg):
        if self.get_setting("debug_logging", False):
            self._log.debug(msg)
    
    def log_info(self, msg):
        self._log.info(msg)
        
    def log_warning(self, msg):
        self._log.warning(msg)

    def log_error(self, msg):
        self._log.error(msg)

    
    ##########################################################################################
    # pyside / qt
    
    def _define_qt_base(self):
        """
        check for pyside then pyqt
        """
        
        # proxy class used when QT does not exist on the system.
        # this will raise an exception when any QT code tries to use it
        class QTProxy(object):                        
            def __getattr__(self, name):
                raise tank.TankError("Looks like you are trying to run a Sgtk App that uses a QT "
                                     "based UI, however the Shotgun engine could not find a PyQt "
                                     "or PySide installation in your python system path. We " 
                                     "recommend that you install PySide if you want to "
                                     "run UI applications from within Shotgun.")
        
        base = {"qt_core": QTProxy(), "qt_gui": QTProxy(), "dialog_base": None}
        
        self._has_qt = False
        
        if not self._has_qt:
            try:
                from PySide import QtCore, QtGui
                import PySide

                # Some old versions of PySide don't include version information
                # so add something here so that we can use PySide.__version__ 
                # later without having to check!
                if not hasattr(PySide, "__version__"):
                    PySide.__version__ = "<unknown>"

                # tell QT to interpret C strings as utf-8
                utf8 = QtCore.QTextCodec.codecForName("utf-8")
                QtCore.QTextCodec.setCodecForCStrings(utf8)

                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPySide(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()

                    def exec_(self):
                        self.activateWindow()
                        self.raise_()
                        # the trick of activating + raising does not seem to be enough for
                        # modal dialogs. So force put them on top as well.
                        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
                        return QtGui.QDialog.exec_(self)
                        
                
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPySide
                self.log_debug("Successfully initialized PySide '%s' located in %s." 
                               % (PySide.__version__, PySide.__file__))
                self._has_qt = True
            except ImportError:
                pass
            except Exception, e:
                self.log_warning("Error setting up pyside. Pyside based UI support will not "
                                 "be available: %s" % e)
        
        if not self._has_qt:
            try:
                from PyQt4 import QtCore, QtGui
                import PyQt4
                
                # tell QT to interpret C strings as utf-8
                utf8 = QtCore.QTextCodec.codecForName("utf-8")
                QtCore.QTextCodec.setCodecForCStrings(utf8)                
                
                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPyQt(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()
                
                    def exec_(self):
                        self.activateWindow()
                        self.raise_()
                        # the trick of activating + raising does not seem to be enough for
                        # modal dialogs. So force put them on top as well.                        
                        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
                        QtGui.QDialog.exec_(self)
                
                
                # hot patch the library to make it work with pyside code
                QtCore.Signal = QtCore.pyqtSignal     
                QtCore.Slot = QtCore.pyqtSlot
                QtCore.Property = QtCore.pyqtProperty           
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPyQt
                self.log_debug("Successfully initialized PyQt '%s' located in %s." 
                               % (QtCore.PYQT_VERSION_STR, PyQt4.__file__))
                self._has_qt = True
            except ImportError:
                pass
            except Exception, e:
                self.log_warning("Error setting up PyQt. PyQt based UI support will not "
                                 "be available: %s" % e)
        
        return base
        
        
    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine. 
        The engine will attempt to parent the dialog nicely to the host application.
        
        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.
        
        Additional parameters specified will be passed through to the widget_class constructor.
        
        :returns: the created widget_class instance
        """
        if not self._has_qt:
            self.log_error("Cannot show dialog %s! No QT support appears to exist in this engine. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system." % title)
            return
        
        self._ui_created = True
        
        return Engine.show_dialog(self, title, bundle, widget_class, *args, **kwargs)    
    
    def show_modal(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a modal dialog window in a way suitable for this engine. The engine will attempt to
        integrate it as seamlessly as possible into the host application. This call is blocking 
        until the user closes the dialog.
        
        :param title: The title of the window
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.
        
        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: (a standard QT dialog status return code, the created widget_class instance)
        """
        if not self._has_qt:
            self.log_error("Cannot show dialog %s! No QT support appears to exist in this engine. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system." % title)
            return

        self._ui_created = True
        
        return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)



