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
        """
        Constructor
        """
        # the has_ui flag indicates that there is an active QApplicaton
        # running and that UI code can be rendered.
        self._has_ui = False

        # the has_qt flag indicates that the QT subsystem is present and can be started 
        self._has_qt = False

        # indicates that apps have tried to launch UI dialogs
        self._has_received_ui_creation_requests = False
        
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
        Initialization
        """
        # if debug logging is turned on in the settings for this app, make sure
        # that the logger accepts the debug stream
        if self.get_setting("debug_logging", False):
            self._log.setLevel(logging.DEBUG)

    def post_app_init(self):
        """
        Initialization that runs after all apps and the QT abstractions have been loaded.
        """
        if self._has_ui:
            # make sure we have a dark theme
            self._initialize_dark_look_and_feel()

    @property
    def has_ui(self):
        """
        Indicates that a QT application and event loop is running
        """
        return self._has_ui

    @property
    def context_change_allowed(self):
        """
        Whether this engine allows on-the-fly context changes.

        :rtype: bool
        """
        return True
                
    def has_received_ui_creation_requests(self):
        """
        Returns true if one or more windows have been requested
        via the show_dialog methods
        """
        return self._has_received_ui_creation_requests

    @property
    def host_info(self):
        """
        :returns: A {"name": application name, "version": application version} 
                  dictionary with information about the application hosting this
                  engine.
        """
        version = self.shotgun.info().get("version") or ["unknown"]
        return {"name": "Shotgun", "version": ".".join([str(x) for x in version])}

    ##########################################################################################
    # command handling

    def execute_command(self, cmd_key):
        """
        Executes a given command.
        """
        cb = self.commands[cmd_key]["callback"]

        if not self._has_qt or self._has_ui:
            # there are two different cases where we can just launch the callback:

            # - A QApplication is already running and there is nothing
            #   we need to do in order to initialize anything further.
            #   this is akin to the case of executing a command in a DCC
            #   which already has got a running UI environment
            #
            # - QT is not available at all. In this case we can also
            #   execute the command directly, and in the case where
            #   the command launches show_dialog() or show_modal(),
            #   we'll catch those and will display an error message
            return cb()

        else:
            # We have QT but no QApplication running. Start it
            # and kick off the commmand.
            self.__setup_ui(cb)

    def execute_old_style_command(self, cmd_key, entity_type, entity_ids):
        """
        Executes an old style shotgun specific command. Old style commands 
        are assumed to not use a UI.

        Note: This is part of a legacy pathway.
        """
        cb = self.commands[cmd_key]["callback"]
        
        if not self._has_qt or self._has_ui:
            # there are two different cases where we can just launch the callback:

            # - A QApplication is already running and there is nothing
            #   we need to do in order to initialize anything further.
            #   this is akin to the case of executing a command in a DCC
            #   which already has got a running UI environment
            #
            # - QT is not available at all. In this case we can also
            #   execute the command directly, and in the case where
            #   the command launches show_dialog() or show_modal(),
            #   we'll catch those and will display an error message
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

        # We need to clear Qt library paths on Linux if KDE is the active environment.
        # This resolves issues with mismatched Qt libraries between the OS and the
        # application being launched if it is a DCC that comes with a bundled Qt.
        if sys.platform == "linux2" and os.environ.get("KDE_FULL_SESSION") is not None:
            QtGui.QApplication.setLibraryPaths([])

        # start up our QApp now
        qt_application = QtGui.QApplication([])        
        qt_application.setWindowIcon(QtGui.QIcon(self.icon_256))

        # make sure we have a dark theme
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
    # PySide / QT
    
    def _define_qt_base(self):
        """
        Define the QT environment.
        """
        base = super(ShotgunEngine, self)._define_qt_base()

        if not base["qt_gui"]:
            self._has_qt = False

            # proxy class used when QT does not exist on the system.
            # this will raise an exception when any QT code tries to use it
            class QTProxy(object):
                def __getattr__(self, name):
                    raise tank.TankError(
                        "The Shotgun Toolkit App you are trying to execute requires a full QT "
                        "environment in order to render its UI. A valid PySide2/PySide/PyQt "
                        "installation could not be found in your python system path."
                    )

            base = {"qt_core": QTProxy(), "qt_gui": QTProxy(), "dialog_base": None}

        else:
            self._has_qt = True
            QtCore = base["qt_core"]
            QtGui = base["qt_gui"]

            # tell QT4 to interpret C strings as utf-8
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
                    return QtGui.QDialog.exec_(self)

            base["dialog_base"] = ProxyDialogPyQt

            # also figure out if qt is already running
            if QtGui.QApplication.instance():
                self._has_ui = True

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
        self._has_received_ui_creation_requests = True
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
        self._has_received_ui_creation_requests = True
        return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)



