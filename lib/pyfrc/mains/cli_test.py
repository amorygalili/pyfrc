
import os
import inspect

from os.path import abspath, dirname, exists, join

import pytest

from ..test_support import pytest_plugin

# TODO: setting the plugins so that the end user can invoke py.test directly
# could be a useful thing. Will have to consider that later.

#
# main test class
#
class PyFrcTest(object):
    """
        Executes unit tests on the robot code using a special py.test plugin
    """
    
    def __init__(self, parser=None):
        if parser:
            parser.add_argument('--coverage-mode', default=False, action='store_true',
                                help='This flag is passed when trying to determine coverage')
            parser.add_argument('pytest_args', nargs='*',
                                help="To pass args to pytest, specify --, then the args")
    
    def run(self, options, robot_class, **static_options):
        # wrapper around run_test that sets the appropriate mode
        
        from .. import config
        config.mode = 'test'
        config.coverage_mode = options.coverage_mode
        
        return self.run_test(options.pytest_args, robot_class, **static_options)
        
    def run_test(self, pytest_args, robot_class, **static_options):
    
        # find test directory, change current directory so py.test can find the tests
        # -> assume that tests reside in tests or ../tests
        robot_file = abspath(inspect.getfile(robot_class))
        robot_path = dirname(robot_file)
        test_directory = None
        
        try_dirs = [join(robot_path, 'tests'), abspath(join(robot_path, '..', 'tests'))]
        
        for d in try_dirs:
            if exists(d):
                test_directory = d
                break
        
        if test_directory is None:
            print("Cannot run robot tests, as test directory was not found. Looked for tests at:")
            for d in try_dirs:
                print('- %s' % d)
            return 1
        
        os.chdir(test_directory)
        
        return pytest.main(pytest_args,
                           plugins=[pytest_plugin.PyFrcPlugin(robot_class,
                                                              robot_file,
                                                              robot_path)])


