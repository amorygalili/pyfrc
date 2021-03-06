
import argparse
import inspect
import subprocess
import sys

class PyFrcProfiler:
    """
        Wraps other commands by running them via the built in cProfile module.
        Use this to profile your program and figure out where you're spending
        a lot of time (note that cProfile only profiles the main thread)
    """

    def __init__(self, parser):
        parser.add_argument('args', nargs=argparse.REMAINDER,
                            help='Arguments to pass to robot.py')

    def run(self, options, robot_class, **static_options):

        from .. import config
        config.mode = 'profiler'

        try:
            import cProfile
        except ImportError:
            print("Error importing cProfile module for profiling, your python interpreter may not support profiling\n", file=sys.stderr)
            return 1
        
        if len(options.args) == 0:
            print("ERROR: Profiler command requires arguments to run other commands")
            return 1
        
        file_location = inspect.getfile(robot_class)
    
        # construct the arguments to run the profiler
        args = [sys.executable, '-m', 'cProfile', '-s', 'tottime', file_location] + options.args
        
        return subprocess.call(args)
