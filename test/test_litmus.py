import re
import os
import sys
import time
import shutil
import tarfile
import tempfile
import unittest
import subprocess

testdir = os.path.abspath(os.path.dirname(__file__))
litmus_dist = os.path.join(testdir, 'litmus-0.13')
sys.path.insert(0, os.path.join(testdir, '..'))

import pywebdav.server.server

# Run davserver
user = 'test'
password = 'pass'
port = 38028


class Test(unittest.TestCase):
    def setUp(self):

        self.rundir = tempfile.mkdtemp()
        self._ensure_litmus()
        shutil.copyfile(
            os.path.join(litmus_dist, "htdocs", "foo"),
            os.path.join(self.rundir, "foo"))


    def _ensure_litmus(self):
        self.litmus = os.path.join(litmus_dist, 'litmus')
        if not os.path.exists(self.litmus):
            print('Compiling litmus test suite')

            if os.path.exists(litmus_dist):
                shutil.rmtree(litmus_dist)
            with tarfile.open(litmus_dist + '.tar.gz') as tf:
                tf.extractall(path=testdir)
            ret = subprocess.call(['sh', './configure'], cwd=litmus_dist)
            assert ret == 0
            ret = subprocess.call(['make'], cwd=litmus_dist)
            assert ret == 0
            litmus = os.path.join(litmus_dist, 'litmus')
            assert os.path.exists(self.litmus)

    def tearDown(self):
        print("Cleaning up tempdir")
        shutil.rmtree(self.rundir)

    def test_run_litmus(self):

        result = []
        errors = []
        proc = None
        try:
            print('Starting davserver')
            davserver_cmd = [sys.executable, os.path.join(testdir, '..', 'pywebdav', 'server', 'server.py'), '-D',
                             self.rundir, '-u', user, '-p', password, '-H', 'localhost', '--port', str(port)]
            self.davserver_proc = subprocess.Popen(davserver_cmd)
            # Ensure davserver has time to startup
            time.sleep(1)

            # Run Litmus
            print('Running litmus')
            try:
                ret = subprocess.run(
                        [self.litmus, "-k", 'http://localhost:%d' % port, user, password],
                        capture_output=True,
                        check=True,
                        env=dict(
                            TESTROOT=litmus_dist,
                            HTDOCS=self.rundir
                        )
                    )
                results = ret.stdout
            except subprocess.CalledProcessError as ex:
                results = ex.output
            lines = results.decode("latin-1").split('\n')
            assert len(lines), "No litmus output"
            for line in lines:
                line = line.split('\r')[-1]
                result.append(line)
                if len(re.findall('^ *\d+\.', line)):
                    if not line.endswith('pass'):
                        errors.append(line)

        finally:
            print('\n'.join(result))

            print('Stopping davserver')
            self.davserver_proc.kill()
        assert len(errors) == 0, "\n".join(errors)


    def test_run_litmus_noauth(self):

        result = []
        errors = []
        proc = None
        try:
            print('Starting davserver')
            davserver_cmd = [sys.executable, os.path.join(testdir, '..', 'pywebdav', 'server', 'server.py'), '-D',
                             self.rundir, '-n', '-H', 'localhost', '--port', str(port)]
            self.davserver_proc = subprocess.Popen(davserver_cmd)
            # Ensure davserver has time to startup
            time.sleep(1)

            # Run Litmus
            print('Running litmus')
            try:
                ret = subprocess.run(
                        [self.litmus, "-k", 'http://localhost:%d' % port],
                        capture_output=True,
                        check=True,
                        env=dict(
                            TESTROOT=litmus_dist,
                            HTDOCS=self.rundir
                        )
                    )
                results = ret.stdout
            except subprocess.CalledProcessError as ex:
                results = ex.output
            lines = results.decode("latin-1").split('\n')
            assert len(lines), "No litmus output"
            for line in lines:
                line = line.split('\r')[-1]
                result.append(line)
                if len(re.findall('^ *\d+\.', line)):
                    if not line.endswith('pass'):
                        errors.append(line)

        finally:
            print('\n'.join(result))

            print('Stopping davserver')
            self.davserver_proc.kill()
        assert len(errors) == 0, "\n".join(errors)
