"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Implements the Shotgun Engine in Tank, e.g the client side script runner foundation which handles
incoming Tank Action Requests.

"""

from tank.platform import Engine
import tank
import sys


class ShotgunEngine(Engine):
    """
    An engine for Shotgun. This is normally called via the scripts/shotgun/run_action script,
    which sets up an instance of the Shotgun engine + apps.
    
    Note that all apps running in this engine are assumed to have a method named 
    run_shotgun_action. This is what the run_action script will look for an execute.
    
    """
        
    def init_engine(self):
        pass
                
    ##########################################################################################
    # logging interfaces

    def log_debug(self, msg):
        if self.get_setting("debug_logging", False):
            sys.stdout.write("DEBUG: %s\n" % msg)
    
    def log_info(self, msg):
        sys.stdout.write("%s\n" % msg)
        
    def log_warning(self, msg):
        # note: java bridge only captures stdout, not stderr
        sys.stdout.write("WARNING: %s\n" % msg)
    
    def log_error(self, msg):
        # note: java bridge only captures stdout, not stderr
        sys.stdout.write("ERROR: %s\n" % msg)

    ##########################################################################################
    # support for Shotgun actions
    
    def get_actions(self):
        res = []

        for (cmd_name, cmd_params) in self.commands.items():
            entry = [
                cmd_name,
                cmd_params["properties"]["title"],
                ",".join(cmd_params["properties"]["entity_types"]),
                ",".join(cmd_params["properties"]["deny_permissions"]),
                ",".join(cmd_params["properties"]["deny_platforms"]),
                str(cmd_params["properties"]["supports_multiple_selection"])
            ]
            
            res.append("$".join(entry))

        return "\n".join(res)
    
