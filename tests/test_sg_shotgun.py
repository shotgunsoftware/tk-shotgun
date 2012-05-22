"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------
"""
import os

from tank_test.tank_test_base import TankTestBase, setUpModule
import tank
from engine import ShotgunEngine


class ShotgunEngineTestBase(TankTestBase):
    def setUp(self):
        super(ShotgunEngineTestBase, self).setUp()

        # set up a project 
        self.setup_standard_config()
        # set up project data
        self.sequence = {"type":"Sequence", "id":6, "name": "Seq"}
        self.seq_path = os.path.join(self.project_root, "sequences", "Seq")
        self.add_production_path(self.seq_path, self.sequence)

        self.shot = {"type":"Shot", "id":2, "name":"shot_2"}
        self.shot_path = os.path.join(self.seq_path, "shot_2")
        self.add_production_path(self.shot_path, self.shot)

        self.step = {"type":"Step", "id":3, "name":"step_name"}
        self.step_path = os.path.join(self.shot_path, "step_name")
        self.add_production_path(self.step_path, self.step)

        # add work path
        work_path = os.path.join(self.step_path, "work")
        os.mkdir(work_path)

        self.cfg_folder = os.path.join(self.project_config, "engines", "sg_shotgun")
        self.engine = self.start_engine(project_root=self.project_root,
                                        entity = self.shot,
                                        step = self.step)

    def start_engine(self, **kws):
        """
        Instantiates an engine with a context reflecting context
        related keywords passed.
        """
        ctx = tank.system.Context(**kws)
        return ShotgunEngine(ctx)


class TestShotgunEngine(ShotgunEngineTestBase):

    def test_engine(self):
        self.assertIsInstance(self.engine, tank.system.engine.Engine)
