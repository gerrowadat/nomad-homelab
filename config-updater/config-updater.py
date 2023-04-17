import os
import iso8601
import datetime
import nomad
from absl import app
from absl import flags
from absl import logging

FLAGS = flags.FLAGS

flags.DEFINE_string('nomad_host', 'localhost', 'nomad host to talk to')
flags.DEFINE_string('nomad_job', '', 'nomad job to operate on.')
flags.DEFINE_string('nomad_task', '', 'nomad task to operate on.')
flags.DEFINE_string('nomad_local_config', '', 'name of configfile accessed locally')


class ConfigUpdaterError(Exception):
    pass


class ConfigUpdaterUsageError(ConfigUpdaterError):
    pass


class ConfigUpdater(object):
    def __init__(self, nomadobj, job_name, task_name, local_config, rate_limit_secs=60):
        self._n = nomadobj
        self._jobname = job_name
        self._taskname = task_name
        self._localconf = local_config
        self._last_reload = 0
        self._rate_limit_secs = rate_limit_secs
        self._Validate()

    @property
    def last_reload(self):
        return self._last_reload

    @property
    def local_config_age(self):
        return int(os.path.getmtime(self._localconf))

    def NeedsReload(self):
        task = self._GetTask()
        lastload_str = task['LastRestart'] or task['StartedAt']
        lastload = iso8601.parse_date(lastload_str)
        logging.info('Task last restarted at %s' % (lastload.strftime('%Y-%m-%d %H:%M:%S')))
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(self._localconf))
        logging.info('%s last modified at %s' % (self._localconf, mtime.strftime('%Y-%m-%d %H:%M:%S')))
        print(task)

    def _Validate(self):
        if self._jobname not in self._n.jobs:
            raise ConfigUpdaterUsageError('no such nomad job: %s' % (self._jobname))
        task = self._GetTask()
        if not task:
            raise ConfigUpdaterUsageError('no such task: %s' % (self._taskname))
        if not os.path.isfile(self._localconf):
            raise ConfigUpdaterUsageError('no such file: %s' % (self._localconf))


    def _GetTask(self):
        allocs = self._GetRunningAllocs()
        task = None
        for t in allocs:
            ts = t['TaskStates']
            if self._taskname in ts:
                if ts[self._taskname]['State'] == 'running':
                    return ts[self._taskname]
                else:
                    logging.info('Found non-running %s task: %s' % (
                        self._taskname, ts[self._taskname]))
        return None

    def _GetRunningAllocs(self):
        j_id = self._n.jobs[self._jobname]['ID']
        return [a for a in self._n.job.get_allocations(j_id) if a['ClientStatus'] == 'running']






def main(argv):
    n = nomad.Nomad(FLAGS.nomad_host)

    cu = ConfigUpdater(n, FLAGS.nomad_job, FLAGS.nomad_task, FLAGS.nomad_local_config)

    print(cu.NeedsReload())



if __name__ == '__main__':
    app.run(main)
