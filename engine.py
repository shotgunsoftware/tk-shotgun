"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Implements the Shotgun Engine in Tank, e.g the client side script runner foundation which handles
incoming Tank Action Requests.

"""

from tank.platform import Engine
import tank
import cgi
import sys
import os



class ShotgunEngine(Engine):
    """
    An engine for Shotgun. This is normally called via the tank engine.    
    """
        
    def init_engine(self):
        self._has_ui = False
        self._qt_application = None
                
    @property
    def has_ui(self):
        return self._has_ui
                
    ##########################################################################################
    # logging interfaces

    def log_debug(self, msg):
        if self.get_setting("debug_logging", False):
            msg = cgi.escape(str(msg))
            sys.stdout.write("<b>DEBUG</b>: %s\n" % msg)
    
    def log_info(self, msg):
        # note - do not escape info messages
        # allow these to use html for formatting purposes
        sys.stdout.write("%s\n" % msg)
        
    def log_warning(self, msg):
        # note - do not escape warning messages
        # allow these to use html for formatting purposes

        # note: java bridge only captures stdout, not stderr
        msg = cgi.escape(str(msg))
        sys.stdout.write("<b>WARNING:</b> %s\n" % msg)
    
    def log_error(self, msg):
        # note: java bridge only captures stdout, not stderr
        # make sure we escape html so that all content shows up in shotgun
        msg = cgi.escape(str(msg))
        sys.stdout.write("<b>ERROR:</b> %s\n" % msg)

    
    ##########################################################################################
    # pyside / qt
    
    def _define_qt_base(self):
        """
        check for pyside then pyqt
        """
        
        
        base = {"qt_core": None, "qt_gui": None, "dialog_base": None}
        self._has_ui = False
        
        if not self._has_ui:
            try:
                from PySide import QtCore, QtGui

                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPySide(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()
                
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPySide
                self._has_ui = True
            except:
                self.log_debug("Found PySide install present in %s." % QtGui.__file__)
        
        if not self._has_ui:
            try:
                from PyQt4 import QtCore, QtGui
                
                # a simple dialog proxy that pushes the window forward
                class ProxyDialogPyQt(QtGui.QDialog):
                    def show(self):
                        QtGui.QDialog.show(self)
                        self.activateWindow()
                        self.raise_()
                
                
                # hot patch the library to make it work with pyside code
                QtCore.Signal = QtCore.pyqtSignal                
                base["qt_core"] = QtCore
                base["qt_gui"] = QtGui
                base["dialog_base"] = ProxyDialogPyQt
                self._has_ui = True
            except:
                self.log_debug("Found PyQt install present in %s." % QtGui.__file__)
        
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
        from tank.platform.qt import QtCore, QtGui
        
        
        
        if not self._has_ui:
            self.log_error("Cannot show dialog! No QT support appears to exist in this enging. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system.")
        
        start_app_loop = False
        if self._qt_application is None:
            QtGui.QApplication.setStyle("cleanlooks")
            self._qt_application = QtGui.QApplication([])
            css_file = os.path.join(self.disk_location, "resources", "dark.css")
            f = open(css_file)
            css = f.read()
            f.close()
            self._qt_application.setStyleSheet(css)        
            start_app_loop = True
            
        obj = Engine.show_dialog(self, title, bundle, widget_class, *args, **kwargs)

        if start_app_loop:
            self._qt_application.exec_()
            # this is a bit weird - we are not returning the dialog object because
            # at this point the application has already exited
            return None
        
        else:
            # a dialog was called by a signal or slot
            # in the qt message world. return its handle
            return obj
    
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
        from tank.platform.qt import QtCore, QtGui
        
        if not self._has_ui:
            self.log_error("Cannot show dialog! No QT support appears to exist in this enging. "
                           "In order for the shell engine to run UI based apps, either pyside "
                           "or PyQt needs to be installed in your system.")

        if self._qt_application is None:
            # no Qapp is running - meaning there are no other dialogs
            # this is a chicken and egg thing - need to handle this dialog
            # as a non-modal becuase of dialog.exec() and app.exec()
            return self.show_dialog(title, bundle, widget_class, *args, **kwargs)
        else:
            # qt is running! Just use std base class implementation
            return Engine.show_modal(self, title, bundle, widget_class, *args, **kwargs)

