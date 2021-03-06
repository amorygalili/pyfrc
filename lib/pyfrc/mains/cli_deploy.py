
import inspect
import os

import shutil
import tempfile

from os.path import abspath, basename, dirname, exists, join, splitext

from ..robotpy import installer


def relpath(path):
    '''Path helper, gives you a path relative to this file'''
    return os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), path))
    
class PyFrcDeploy:
    """
        Uploads your robot code to the robot and executes it immediately
    """
    
    def __init__(self, parser):
        ''' :type parser: argparse.ArgumentParser '''
        parser.add_argument('--skip-tests', action='store_true', default=False,
                            help="If specified, don't run tests before uploading code to robot (DANGEROUS)")
        
        parser.add_argument('--debug', action='store_true', default=False,
                            help="If specified, runs the code in debug mode (which only currently enables verbose logging)")
        
        parser.add_argument('--nonstandard', action='store_true', default=False,
                            help="When specified, allows you to deploy code in a file that isn't called robot.py")
    
    def run(self, options, robot_class, **static_options):
        
        from .. import config
        config.mode = 'upload'
        
        # run the test suite before uploading
        if not options.skip_tests:
            from .cli_test import PyFrcTest
            
            tester = PyFrcTest()
            
            retval = tester.run_test([], robot_class, ignore_missing_test=True)
            if retval != 0:
                print("Your robot tests failed, aborting upload. Use --skip-tests if you want to upload anyways")
                return retval
        
        # upload all files in the robot.py source directory
        robot_file = abspath(inspect.getfile(robot_class))
        robot_path = dirname(robot_file)
        robot_filename = basename(robot_file)
        cfg_filename = join(robot_path, '.deploy_cfg')
        
        if not options.nonstandard and robot_filename != 'robot.py':
            print("ERROR: Your robot code must be in a file called robot.py (launched from %s)!" % robot_filename)
            print()
            print("If you really want to do this, then specify the --nonstandard argument")
            return 1
        
        # This probably should be configurable... oh well
        
        deploy_dir = '/home/lvuser'
        py_deploy_dir = '%s/py' % deploy_dir
        
        if options.debug:
            deployed_cmd = '/usr/local/frc/bin/netconsole-host /usr/local/bin/python3 %s/%s -v run' % (py_deploy_dir, robot_filename) 
            deployed_cmd_fname = 'robotDebugCommand'
            extra_cmd = 'touch /tmp/frcdebug; chown lvuser:ni /tmp/frcdebug'
        else:
            deployed_cmd = '/usr/local/frc/bin/netconsole-host /usr/local/bin/python3 -O %s/%s run' % (py_deploy_dir, robot_filename)
            deployed_cmd_fname = 'robotCommand'
            extra_cmd = ''
        
        sshcmd = "/bin/bash -ce '" + \
                 '[ -d %(py_deploy_dir)s ] && rm -rf %(py_deploy_dir)s; ' + \
                 'echo "%(cmd)s" > %(deploy_dir)s/%(cmd_fname)s; ' + \
                 '%(extra_cmd)s' + \
                 "'"
              
        sshcmd %= {
            'deploy_dir': deploy_dir,
            'py_deploy_dir': py_deploy_dir,
            'cmd': deployed_cmd,
            'cmd_fname': deployed_cmd_fname,
            'extra_cmd': extra_cmd
        }
        
        try:
            controller = installer.SshController(cfg_filename)
            
            # Housekeeping first
            controller.ssh(sshcmd) 
            
            # Copy the files over, copy to a temporary directory first
            # -> this is inefficient, but it's easier in sftp
            tmp_dir = tempfile.mkdtemp()
            py_tmp_dir = join(tmp_dir, 'py')
                    
            try:
                self._copy_to_tmpdir(py_tmp_dir, robot_path)
                controller.sftp(py_tmp_dir, deploy_dir)
            finally:
                shutil.rmtree(tmp_dir)
            
            # Restart the robot code and we're done!
            sshcmd = "/bin/bash -ce '" + \
                     '. /etc/profile.d/natinst-path.sh; ' + \
                     'chown -R lvuser:ni %s; ' + \
                     '/usr/local/frc/bin/frcKillRobot.sh -t -r' + \
                     "'"
            
            sshcmd %= (py_deploy_dir)
            
            controller.ssh(sshcmd)
            controller.close()
            
        except installer.Error as e:
            print("ERROR: %s" % e)
            return 1
        
        return 0

    def _copy_to_tmpdir(self, tmp_dir, robot_path):
        
        upload_files = []
        
        for root, dirs, files in os.walk(robot_path):
            
            prefix = root[len(robot_path)+1:]
            os.mkdir(join(tmp_dir, prefix))
            
            # skip .svn, .git, .hg, etc directories
            for d in dirs[:]:
                if d.startswith('.') or d == '__pycache__':
                    dirs.remove(d)
                    
            # skip .pyc files
            for filename in files:
                
                r, ext = splitext(filename)
                if ext == 'pyc' or r.startswith('.'):
                    continue
                
                shutil.copy(join(root, filename), join(tmp_dir, prefix, filename))
        
        return upload_files
