#!/usr/bin/env python

# Copyright (c) 2017 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""Spawn NPCs into the simulation"""

import sys
import time

try:
    sys.path.append('../carla/carla.egg')
except IndexError:
    pass

import carla

from carla import VehicleLightState as vls

import logging
import random


class SpawnAgentHelper:

    def spawn(self, safe = False, number_of_vehicles = 20, number_of_walkers = 50):

        logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

        self.vehicles_list = []
        self.walkers_list = []
        self.all_id = []
        self.client = carla.Client('127.0.0.1', 2000)
        self.client.set_timeout(10.0)
        self.synchronous_master = False

        hybrid = False
        self.sync = False
        car_lights_on = False
        filterv = 'vehicle.*'
        filterw = 'walker.pedestrian.*'


        try:
            self.world = self.client.get_world()

            traffic_manager = self.client.get_trafficmanager(8000)
            traffic_manager.set_global_distance_to_leading_vehicle(2.0)
            if hybrid:
                traffic_manager.set_hybrid_physics_mode(True)

            if self.sync:
                settings = self.world.get_settings()
                traffic_manager.set_synchronous_mode(True)
                if not settings.synchronous_mode:
                    self.synchronous_master = True
                    settings.synchronous_mode = True
                    settings.fixed_delta_seconds = 0.05
                    self.world.apply_settings(settings)
                else:
                    self.synchronous_master = False

            blueprints = self.world.get_blueprint_library().filter(filterv)
            blueprintsWalkers = self.world.get_blueprint_library().filter(filterw)

            if safe:
                blueprints = [x for x in blueprints if int(x.get_attribute('number_of_wheels')) == 4]
                blueprints = [x for x in blueprints if not x.id.endswith('isetta')]
                blueprints = [x for x in blueprints if not x.id.endswith('carlacola')]
                blueprints = [x for x in blueprints if not x.id.endswith('cybertruck')]
                blueprints = [x for x in blueprints if not x.id.endswith('t2')]

            spawn_points = self.world.get_map().get_spawn_points()
            number_of_spawn_points = len(spawn_points)

            if number_of_vehicles < number_of_spawn_points:
                random.shuffle(spawn_points)
            elif number_of_vehicles > number_of_spawn_points:
                msg = 'requested %d vehicles, but could only find %d spawn points'
                logging.warning(msg, number_of_vehicles, number_of_spawn_points)
                number_of_vehicles = number_of_spawn_points

            # @todo cannot import these directly.
            SpawnActor = carla.command.SpawnActor
            SetAutopilot = carla.command.SetAutopilot
            SetVehicleLightState = carla.command.SetVehicleLightState
            FutureActor = carla.command.FutureActor

            # --------------
            # Spawn vehicles
            # --------------
            batch = []
            for n, transform in enumerate(spawn_points):
                if n >= number_of_vehicles:
                    break
                blueprint = random.choice(blueprints)
                if blueprint.has_attribute('color'):
                    color = random.choice(blueprint.get_attribute('color').recommended_values)
                    blueprint.set_attribute('color', color)
                if blueprint.has_attribute('driver_id'):
                    driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                    blueprint.set_attribute('driver_id', driver_id)
                blueprint.set_attribute('role_name', 'autopilot')

                # prepare the light state of the cars to spawn
                light_state = vls.NONE
                if car_lights_on:
                    light_state = vls.Position | vls.LowBeam | vls.LowBeam

                # spawn the cars and set their autopilot and light state all together
                batch.append(SpawnActor(blueprint, transform)
                             .then(SetAutopilot(FutureActor, True, traffic_manager.get_port()))
                             .then(SetVehicleLightState(FutureActor, light_state)))

            for response in self.client.apply_batch_sync(batch, self.synchronous_master):
                if response.error:
                    logging.error(response.error)
                else:
                    self.vehicles_list.append(response.actor_id)

            # -------------
            # Spawn Walkers
            # -------------
            # some settings
            percentagePedestriansRunning = 0.0  # how many pedestrians will run
            percentagePedestriansCrossing = 0.0  # how many pedestrians will walk through the road
            # 1. take all the random locations to spawn
            spawn_points = []
            for i in range(number_of_walkers):
                spawn_point = carla.Transform()
                loc = self.world.get_random_location_from_navigation()
                if (loc != None):
                    spawn_point.location = loc
                    spawn_points.append(spawn_point)
            # 2. we spawn the walker object
            batch = []
            walker_speed = []
            for spawn_point in spawn_points:
                walker_bp = random.choice(blueprintsWalkers)
                # set as not invincible
                if walker_bp.has_attribute('is_invincible'):
                    walker_bp.set_attribute('is_invincible', 'false')
                # set the max speed
                if walker_bp.has_attribute('speed'):
                    if (random.random() > percentagePedestriansRunning):
                        # walking
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
                    else:
                        # running
                        walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])
                else:
                    print("Walker has no speed")
                    walker_speed.append(0.0)
                batch.append(SpawnActor(walker_bp, spawn_point))
            results = self.client.apply_batch_sync(batch, True)
            walker_speed2 = []
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    self.walkers_list.append({"id": results[i].actor_id})
                    walker_speed2.append(walker_speed[i])
            walker_speed = walker_speed2
            # 3. we spawn the walker controller
            batch = []
            walker_controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
            for i in range(len(self.walkers_list)):
                batch.append(SpawnActor(walker_controller_bp, carla.Transform(), self.walkers_list[i]["id"]))
            results = self.client.apply_batch_sync(batch, True)
            for i in range(len(results)):
                if results[i].error:
                    logging.error(results[i].error)
                else:
                    self.walkers_list[i]["con"] = results[i].actor_id
            # 4. we put altogether the walkers and controllers id to get the objects from their id
            for i in range(len(self.walkers_list)):
                self.all_id.append(self.walkers_list[i]["con"])
                self.all_id.append(self.walkers_list[i]["id"])
            self.all_actors = self.world.get_actors(self.all_id)

            # wait for a tick to ensure client receives the last transform of the walkers we have just created
            if not self.sync or not self.synchronous_master:
                self.world.wait_for_tick()
            else:
                self.world.tick()

            # 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
            # set how many pedestrians can cross the road
            self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
            for i in range(0, len(self.all_id), 2):
                # start walker
                self.all_actors[i].start()
                # set walk to random point
                self.all_actors[i].go_to_location(self.world.get_random_location_from_navigation())
                # max speed
                self.all_actors[i].set_max_speed(float(walker_speed[int(i / 2)]))

            print('spawned %d vehicles and %d walkers, press Ctrl+C to exit.' % (len(self.vehicles_list), len(self.walkers_list)))

            # example of how to use parameters
            traffic_manager.global_percentage_speed_difference(30.0)

            while True:
                if self.sync and self.synchronous_master:
                    self.world.tick()
                else:
                    self.world.wait_for_tick()

        finally:
            pass

    def destroy(self):
        if self.sync and self.synchronous_master:
            settings = self.world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            self.world.apply_settings(settings)

        print('\ndestroying %d vehicles' % len(self.vehicles_list))
        self.client.apply_batch([carla.command.DestroyActor(x) for x in self.vehicles_list])

        # stop walker controllers (list is [controller, actor, controller, actor ...])
        for i in range(0, len(self.all_id), 2):
            self.all_actors[i].stop()

        print('\ndestroying %d walkers' % len(self.walkers_list))
        self.client.apply_batch([carla.command.DestroyActor(x) for x in self.all_id])

        time.sleep(0.5)

if __name__ == '__main__':
    spawnAgentHelper = SpawnAgentHelper()
    try:
        spawnAgentHelper.spawn()
        print('spawned %d vehicles, press Ctrl+C to exit.')

        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        pass
    finally:
        spawnAgentHelper.destroy()
        print('\ndone.')