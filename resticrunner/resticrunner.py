import os
import enum
import time
import shlex
import cherrypy
import threading
import subprocess
import configparser
from absl import app
from absl import flags
from absl import logging
from datetime import datetime

FLAGS = flags.FLAGS

flags.DEFINE_string('config_inifile',
                    'resticrunner.ini',
                    'Config file for jobs')
flags.DEFINE_list('restic_jobs',
                  [],
                  'list of restic jobs to run')
flags.DEFINE_string('http_server_address',
                    '127.0.0.1',
                    'address to run http service on')
flags.DEFINE_integer('http_port',
                     8901,
                     'http port to listen on')


class ResticRunnerError(Exception):
    pass


class ResticRunnerInternalError(ResticRunnerError):
    pass


class ResticRunnerConfigError(ResticRunnerError):
    pass


class ResticJobConfig(object):

    def __init__(self, jobname):
        self._jobname = jobname
        self._required_config_keys = ['repository',
                                      'repo_password',
                                      'local_dir',
                                      'interval_hrs']
        self._optional_config_keys = ['sshkeyfile',
                                      'restic_extra_args',
                                      'ssh_extra_args']

        self._c = self._get_config_keys()

        for key in self._required_config_keys:
            setattr(self, key, self._c[key])
        for key in self._optional_config_keys:
            setattr(self, key, self._c[key])

        logging.info('Confgured Job %s from %s' % (self.jobname,
                                                   FLAGS.config_inifile))

    @property
    def jobname(self):
        return self._jobname

    def _get_config_keys(self):
        configkeys = {}
        c = configparser.ConfigParser()
        c.read(FLAGS.config_inifile)
        if self.jobname not in c.sections():
            raise ResticRunnerConfigError(
                'no section in %s: %s' % (FLAGS.config_inifile, self.jobname))
        for key in self._required_config_keys:
            if key not in c[self.jobname]:
                raise ResticRunnerConfigError(
                    'missing %s key in %s job config' % (key,
                                                         self.jobname))
            configkeys[key] = c[self.jobname][key]
        for key in self._optional_config_keys:
            configkeys[key] = c[self.jobname].get(key)

        return configkeys


class ResticJobRunnerStatus(enum.Enum):
    BUILDING = 1
    READY = 2
    RUNNING = 3
    WAITING = 4
    FAILED = 5
    COMPLETED = 6


class ResticJobRunner(threading.Thread):
    def __init__(self, job_config):
        self._status = ResticJobRunnerStatus.BUILDING
        self._last_run = 0
        self._cf = job_config
        self._cmd = self._build_cmd()
        self._env = self._build_env()
        self.stopping = False
        self._change_status(ResticJobRunnerStatus.READY)
        threading.Thread.__init__(self,
                                  name='restic_%s' % (job_config.jobname))

    @property
    def status(self):
        return self._status.name

    @property
    def last_run(self):
        return self._last_run

    @property
    def cmd(self):
        return self._cmd

    @property
    def env(self):
        return self._env

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    def _change_status(self, new_state):
        if new_state not in ResticJobRunnerStatus:
            raise ResticRunnerInternalError(
                'invalid new state: %s' % (new_state))
        logging.info('%s state change: %s -> %s' % (
            self._cf.jobname,
            self._status.name,
            new_state.name))
        self._status = ResticJobRunnerStatus(new_state)

    def __str__(self):
        ret = 'Restic Job Runner\n'
        ret += ' - Cmd: %s\n' % (self._cmd)
        ret += ' - Env:\n'
        for e in self._env:
            ret += '    - %s: %s\n' % (e, self._env[e])
        return ret

    def _build_cmd(self):
        cmd = 'restic '

        # restic_extra_args
        if self._cf.restic_extra_args is not None:
            extra_args = self._cf.restic_extra_args.split()
        else:
            extra_args = []
        # specify the ssh key if present.
        if self._cf.sshkeyfile is not None:
            # Determine the hostname from the repo.
            repo_parts = self._cf.repository.split(':')
            if len(repo_parts) != 3:
                raise ResticRunnerConfigError(
                    'invalid-looking sftp repo: %s' % (
                        self._cf.repository))
            sftp_command = 'ssh %s %s -i %s -s sftp' % (self._cf.ssh_extra_args or ""
                                                        repo_parts[1],
                                                        self._cf.sshkeyfile)
            extra_args.extend(['-o',
                               'sftp.command="%s"' % (sftp_command)])

        for a in extra_args:
            cmd += (' ' + a)

        cmd += (' backup ' + self._cf.local_dir)

        return cmd

    def _build_env(self):
        env = {
            'RESTIC_REPOSITORY': self._cf.repository,
            'RESTIC_PASSWORD': self._cf.repo_password
        }
        return env

    def run(self):
        while True:
            if self.stopping:
                return
            if self._status == ResticJobRunnerStatus.FAILED:
                logging.info('Job %s previously failed, ignoring.',
                             self._cf.jobname)
            else:
                if self._status == ResticJobRunnerStatus.COMPLETED:
                    logging.info('Preparing to re-run %s...', self._cf.jobname)
                    self._change_status(ResticJobRunnerStatus.READY)
                self._run_inner()
            sleep_secs = int(self._cf.interval_hrs) * 60 * 60
            logging.info('[%s] Sleeping for %s hours...',
                         self._cf.jobname, self._cf.interval_hrs)
            if self.stopping:
                return

            slept = 0
            while slept < sleep_secs:
                time.sleep(5)
                slept += 5
                if self.stopping:
                    return

    def _run_inner(self):
        if self._status != ResticJobRunnerStatus.READY:
            raise ResticRunnerInternalError('Runner is not READY')

        self._change_status(ResticJobRunnerStatus.RUNNING)
        logging.info('Executing restic command %s', self._cmd)
        my_env = os.environ
        my_env.update(self._env)
        p = subprocess.Popen(shlex.split(self._cmd),
                             env=my_env,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             text=True)
        self._change_status(ResticJobRunnerStatus.WAITING)

        while True:
            out, err = p.communicate()
            if out:
                outlines = out.split('\n')
                for line in outlines:
                    logging.info('[%s] [stdout] %s', self._cf.jobname, line)
            if err:
                errlines = err.split('\n')
                for line in errlines:
                    logging.info('[%s] [stderr] %s', self._cf.jobname, line)

            if p.poll() is not None:
                break

        returncode = p.poll()
        if returncode != 0:
            logging.error('Restic process returned status %d', returncode)
            self._change_status(ResticJobRunnerStatus.FAILED)
        else:
            self._change_status(ResticJobRunnerStatus.COMPLETED)
        self._last_run = time.time()


class ResticJob(object):
    def __init__(self, jobname):
        self._jobname = jobname
        self._c = ResticJobConfig(jobname)
        self._r = ResticJobRunner(self._c)

    @property
    def jobname(self):
        return self._jobname

    @property
    def config(self):
        return self._c

    @property
    def runner(self):
        return self._r

    def stop_runner(self):
        logging.info('Asking %s runner thread to stop' % (self.jobname))
        self._r.stopping = True
        self._r.join()


class ResticStatusServer(object):
    def __init__(self, jobs):
        self._jobs = jobs

    def _preamble(self):
        return ('<html><head><title>Restic Job Status</title>'
                '</head><body>')

    def _closing(self):
        return '</body></html>'

    @cherrypy.expose
    def show(self, jobname=None):
        ret = self._preamble()
        jobs = self._jobs

        if jobname not in jobs:
            ret += 'Unknown job %s...' % (jobname[:20])
        else:
            content = 'Command line: %s<br/>' % (
                jobs[jobname].runner.cmd)
            content += 'Environment:<br/>'
            for e in jobs[jobname].runner.env:
                if e in ['RESTIC_PASSWORD']:
                    value = '<i>REDACTED</i>'
                else:
                    value = jobs[jobname].runner.env[e]
                content += ' - %s : %s<br/>' % (e, value)

            content = content.replace('\n', '<br/>')
            ret += content

        ret += self._closing()

        return ret

    @cherrypy.expose
    def index(self):
        ret = self._preamble()

        content = ('<table border=1><tr><td><b>name</b></td>'
                   '<td><b>status</b></td><td>last run</td>'
                   '<td>link</td></b></tr>')

        for j in self._jobs.values():
            if j.runner.last_run == 0:
                last_run = 'never'
            else:
                last_run = str(datetime.fromtimestamp(j.runner.last_run))
            show_link = '<a href="/show?jobname=%s">show</a>' % (j.jobname)
            content += ('<tr><td>%s</td><td>%s</td>'
                        '<td>%s</td><td>%s</td></tr>') % (j.jobname,
                                                          j.runner.status,
                                                          last_run,
                                                          show_link)
        ret += content
        ret += self._closing()

        return ret


def main(argv):
    jobs = {}
    for jobname in FLAGS.restic_jobs:
        jobs[jobname] = ResticJob(jobname)

    for j in jobs:
        logging.info('Kicking off %s...', j)
        jobs[j].runner.start()

    cherrypy.config.update(
        {'server.socket_host': FLAGS.http_server_address,
         'server.socket_port': FLAGS.http_port})

    # When Cherrypy is stopping, stop our restic worker threads.
    def _stop_restic_threads():
        for j in jobs:
            jobs[j].stop_runner()
    cherrypy.engine.subscribe('stop', _stop_restic_threads)

    logging.info('Starting web server on %s:%s' % (FLAGS.http_server_address,
                                                   FLAGS.http_port))

    cherrypy.quickstart(ResticStatusServer(jobs), '/')


if __name__ == '__main__':
    app.run(main)
