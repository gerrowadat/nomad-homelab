import enum
import time
import configparser
from absl import app
from absl import flags
from absl import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

FLAGS = flags.FLAGS

flags.DEFINE_string('config_inifile',
                    'resticrunner.ini',
                    'Config file for jobs')
flags.DEFINE_list('restic_jobs',
                  [],
                  'list of restic jobs to run')
flags.DEFINE_string('http_server_address',
                    'localhost',
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
                                      'restic_extra_args']

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


class ResticJobRunner(object):
    def __init__(self, job_config):
        self._status = ResticJobRunnerStatus.BUILDING
        self._last_run = 0
        self._cf = job_config
        self._cmd = self._build_cmd()
        self._env = self._build_env()
        self._change_status(ResticJobRunnerStatus.READY)

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
        cmd = ['restic']

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
            sftp_command = 'ssh %s -i %s -s sftp' % (repo_parts[1],
                                                     self._cf.sshkeyfile)
            extra_args.extend(['-o',
                               'sftp.command=\'%s\'' % (sftp_command)])

        cmd.extend(extra_args)

        cmd.extend(['backup', self._cf.local_dir])

        return cmd

    def _build_env(self):
        env = {
            'RESTIC_REPOSITORY': self._cf.repository,
            'RESTIC_PASSWORD': self._cf.repo_password
        }
        return env


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


class ResticStatusServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        self._jobs = kwargs['restic_jobs']
        del kwargs['restic_jobs']
        HTTPServer.__init__(self, *args, **kwargs)


class ResticStatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self._serve_root()
        elif self.path.startswith('/show'):
            self._serve_show()

    def _preamble(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(('<html><head><title>Restic Job Status</title>'
                                '</head>'), 'utf-8'))
        self.wfile.write(bytes('<body>', 'utf-8'))

    def _closing(self):
        self.wfile.write(bytes("</body></html>", "utf-8"))

    def _serve_show(self):
        self._preamble()
        jobs = self.server._jobs

        jobname = self.path[6:]

        if jobname not in jobs:
            self.wfile.write(
                bytes('Unknown job %s...' % (jobname[:20]), 'utf-8'))
        else:
            content = 'Command line: %s<br/>' % (
                ' '.join(jobs[jobname].runner.cmd))
            content += 'Environment:<br/>'
            for e in jobs[jobname].runner.env:
                if e in ['RESTIC_PASSWORD']:
                    value = '<i>REDACTED</i>'
                else:
                    value = jobs[jobname].runner.env[e]
                content += ' - %s : %s<br/>' % (e, value)

            content = content.replace('\n', '<br/>')
            self.wfile.write(bytes(content, 'utf-8'))

        self._closing()

    def _serve_root(self):
        jobs = self.server._jobs
        self._preamble()

        content = ('<table border=1><tr><td><b>name</b></td>'
                   '<td><b>status</b></td><td>last run</td>'
                   '<td>link</td></b></tr>')

        for j in jobs.values():
            if j.runner.last_run == 0:
                last_run = 'never'
            else:
                last_run = time.time(j.runner.last_run)
            show_link = '<a href="/show/%s">show</a>' % (j.jobname)
            content += ('<tr><td>%s</td><td>%s</td>'
                        '<td>%s</td><td>%s</td></tr>') % (j.jobname,
                                                          j.runner.status,
                                                          last_run,
                                                          show_link)
        self.wfile.write(bytes(content, 'utf-8'))

        self._closing()


def main(argv):
    jobs = {}
    for jobname in FLAGS.restic_jobs:
        jobs[jobname] = ResticJob(jobname)

    ws = ResticStatusServer((FLAGS.http_server_address, FLAGS.http_port),
                            ResticStatusHandler,
                            restic_jobs=jobs)
    logging.info('Starting web server on %s:%s' % (FLAGS.http_server_address,
                                                   FLAGS.http_port))

    ws.serve_forever()
    ws.server_close()


if __name__ == '__main__':
    app.run(main)
