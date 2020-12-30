VERSION = '096'

WEATHER_1 = [1, 3, 6, 8]
WEATHER_2 = [4, 14]
WEATHER_3 = [10, 14]
WEATHER_4 = [1, 8, 14]


class Suites:

    def __init__(self):
        self._suites = dict()
        self._aliases = dict()
        pass

    def add(self, suite_name, *args, **kwargs):
        assert suite_name not in self._suites, '%s is already registered!' % suite_name

        town = None

        if 'Town01' in suite_name:
            town = 'Town01'
        elif 'Town02' in suite_name:
            town = 'Town02'
        else:
            raise Exception('No town specified: %s.' % suite_name)

        benchmark = 'carla100' if 'NoCrash' in suite_name else 'corl2017'
        suite = None

        if 'Turn' in suite_name:
            suite = 'turn'
        elif 'Straight' in suite_name:
            suite = 'straight'
        elif 'Full' in suite_name:
            suite = 'full'
        elif 'NoCrash' in suite_name:
            suite = 'nocrash'
        else:
            raise Exception('No suite specified: %s.' % suite_name)

        kwargs['town'] = town
        kwargs['poses_txt'] = '%s/%s/%s_%s.txt' % (benchmark, VERSION, suite, town)
        kwargs['col_is_failure'] = 'NoCrash' in suite_name

        self._suites[suite_name] = (args, kwargs)

    def add_alias(self, town, alias_arr):
        self._aliases[town] = alias_arr

    def get_suites(self, suite_name):
        if suite_name.lower() in self._aliases:
            return self._aliases[suite_name]

        raise ValueError("suite name doesn't exist in aliases")





