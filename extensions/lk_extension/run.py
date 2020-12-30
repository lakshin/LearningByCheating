import sys
from os import path

try:
    sys.path.insert(0, '../..')
    sys.path.append('../../carla/carla.egg')
    sys.path.append('../../PythonAPI')
except IndexError:
    pass

import carla
from pathlib import Path

from extensions.suites import Suites, WEATHER_1, WEATHER_2
from extensions.lbc_extender import LBCExtender


class Runner:

    def __init__(self):
        self.suites = Suites()
        self.client = carla.Client('127.0.0.1', 2000)
        self.client.set_timeout(10.0)
        self.model_path = '../../ckpts/image/model-10.th'

        self.register_suites()
        self.register_alias()

    def run(self, suite_name, max_count=3):
        for suite_name in self.suites.get_suites(suite_name):
            lbc_extender = LBCExtender(carla_client=self.client, model_path=Path(self.model_path),
                                       suite_name=suite_name)
            gen = lbc_extender.run(max_count, show=True)
            controls = next(gen, None)
            while True:
                try:
                    next(gen)
                    controls = gen.send(controls)
                except StopIteration:
                    break

    def register_suites(self):
        # self.suites.add('FullTown01-v1', n_vehicles=20, n_pedestrians=20, weathers=WEATHER_1)
        # self.suites.add('FullTown01-v2', n_vehicles=20, n_pedestrians=20, weathers=WEATHER_2)
        self.suites.add('FullTown02-v1', n_vehicles=20, n_pedestrians=20, weathers=WEATHER_1)
        self.suites.add('FullTown02-v2', n_vehicles=20, n_pedestrians=20, weathers=WEATHER_2)

    def register_alias(self):
        # suite_arr = ['FullTown01-v1', 'FullTown01-v2']
        #self.suites.add_alias('town1', suite_arr)
        suite_arr = ['FullTown02-v1', 'FullTown02-v2']
        self.suites.add_alias('town2', suite_arr)


if __name__ == '__main__':
    Runner().run('town2', 1)
