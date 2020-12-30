import torch
import tqdm
import pandas as pd

from benchmark import make_suite
import bird_view.utils.bz_utils as bzu
from bird_view.models import image
import bird_view.utils.carla_utils as cu
from benchmark.run_benchmark import _paint


class LBCExtender:

    def __init__(self, carla_client, model_path, suite_name, seed=2019, port=2000, big_cam=False):
        self.client = carla_client
        self.model_path = model_path
        self.seed = seed
        self.suite_name = suite_name
        self.port = port
        self.big_cam = big_cam

        self.__init_directories(model_path, suite_name)

    # public methods

    def run(self, max_count, show=False, resume=False):
        with make_suite(self.suite_name, port=self.port, big_cam=self.big_cam, client=self.client) as env:

            summary = list()
            if self.summary_csv.exists() and resume:
                summary = pd.read_csv(self.summary_csv)
            else:
                summary = pd.DataFrame()

            for weather, (start, target), run_name in self.__get_env_tasks(env, max_count):

                self.__init_env(env, start, target, weather)
                agent = self.__create_agent(env)

                diagnostics = list()
                while env.tick():
                    observations = env.get_observations()
                    inital_control = agent.run_step(observations)
                    yield inital_control
                    control = yield
                    #yield
                    diagnostic = env.apply_control(control)

                    _paint(observations, control, diagnostic, agent.debug, env, show)

                    diagnostic.pop('viz_img')
                    diagnostics.append(diagnostic)

                    if env.is_failure() or env.is_success():
                        result = self.__env_result(env, weather, start, target)
                        break

                summary = summary.append(result, ignore_index=True)

                diagnostics_csv = str(self.diagnostics_dir / ('%s.csv' % run_name))

                # Do this every timestep just in case.
                pd.DataFrame(summary).to_csv(self.summary_csv, index=False)
                pd.DataFrame(diagnostics).to_csv(diagnostics_csv, index=False)


    #private methods

    def __create_agent(self, env):
        agent_maker = self.__get_agent_maker()

        agent = agent_maker()

        return agent

    # def __dispose_env(self):
    #     self._env.__exit__()

    def __init_directories(self, model_path, suite_name):
        self.log_dir = self.model_path.parent
        self.benchmark_dir = self.log_dir / 'benchmark' / model_path.stem / ('%s_seed%d' % (suite_name, self.seed))
        self.summary_csv = self.benchmark_dir / 'summary.csv'
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        self.diagnostics_dir = self.benchmark_dir / 'diagnostics'
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)

    def __init_env(self, env, start, target, weather):
        env.seed = self.seed
        env.init(start=start, target=target, weather=cu.PRESET_WEATHERS[weather])

    def __get_agent_maker(self):
        config = bzu.load_json(str(self.log_dir / 'config.json'))

        model_class, agent_class = (image.ImagePolicyModelSS, image.ImageAgent)

        model = model_class(**config['model_args'])
        model.load_state_dict(torch.load(str(self.model_path)))
        model.eval()

        agent_args = config.get('agent_args', dict())
        agent_args['model'] = model

        return lambda: agent_class(**agent_args)

    def __init_video(self, run_name):
        bzu.init_video(save_dir=str(self.benchmark_dir / 'videos'), save_path=run_name)

    def __get_env_tasks(self, env, count):
        num_run = 0
        for weather, (start, target), run_name in tqdm.tqdm(env.all_tasks, total=count):
            num_run += 1

            if num_run > count:
                break

            self.__init_video(run_name)
            yield weather, (start, target), run_name

    def __env_result(self, env, weather, start, target):
        return {'weather': weather, 'start': start, 'target': target, 'success': env.is_success(),
                't': env._tick, 'total_lights_ran': env.traffic_tracker.total_lights_ran,
                'total_lights': env.traffic_tracker.total_lights, 'collided': env.collided}

