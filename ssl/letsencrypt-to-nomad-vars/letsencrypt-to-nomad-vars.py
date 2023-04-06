import os

import nomad

from absl import app
from absl import flags
from absl import logging

FLAGS = flags.FLAGS

# no token via flags, dummy. Set NOMAD_TOKEN.
flags.DEFINE_string('nomad_server', 'localhost', 'nomad server to talk to')
flags.DEFINE_boolean('nomad_ssl', False, 'use SSL to talk to nomad?')
flags.DEFINE_boolean('nomad_ssl_verify', False, 'verify nomad SSL cert?')

flags.DEFINE_string('letsencrypt_base',
                    '/etc/letsencrypt',
                    'base path for LE certificates')

flags.DEFINE_string('nomad_var_base',
                    'ssl_certs/',
                    'base path for nomad variables')

flags.DEFINE_string('export_cert', None, 'certificate to export')


class SSLCert(object):
    def __init__(self, path):
        # path is to where the fullchain.pem/privkey.pem are.
        self._path = path
        self._name = os.path.basename(path)

    def __str__(self):
        return '[SSL cert %s at %s]' % (self.name, self.path)

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return self._path

    @property
    def privkey(self):
        with open(self._path + '/privkey.pem') as f:
            return str(f.read())

    @property
    def chain(self):
        with open(self._path + '/fullchain.pem') as f:
            return str(f.read())


class LEFiles(object):
    def __init__(self, path):
        self._path = path
        if not os.path.isdir(path):
            raise ValueError('--letsencrypt_base (%s) not found.' % (path, ))
        self._seen_certs = self._FindCerts(self._path)

    @property
    def certs(self):
        return self._seen_certs

    def _FindCerts(self, path):
        all_dirs = [f for f in os.scandir(path + '/live') if f.is_dir()]
        all_certs = []
        for d in all_dirs:
            if os.path.exists(
                    d.path + '/fullchain.pem') and os.path.exists(
                        d.path + '/privkey.pem'):
                all_certs.append(SSLCert(d.path))
        return all_certs


def main(argv):
    le = LEFiles(FLAGS.letsencrypt_base)

    cert_choices = [x.name for x in le.certs]
    if FLAGS.export_cert is None:
        logging.error(
            '--export_cert is required (valid choices: %s)' % (
                ', '.join(cert_choices)))
        return

    if FLAGS.export_cert not in cert_choices:
        logging.error('Invalid --export_cert (valid choices: %s)' % (
            ', '.join(cert_choices)))
        return

    n = nomad.Nomad(
        host=FLAGS.nomad_server,
        secure=FLAGS.nomad_ssl,
        verify=FLAGS.nomad_ssl_verify)

    # Nomad doesn't like periods in variables because Reasons I Guess.
    nomad_var = FLAGS.nomad_var_base + FLAGS.export_cert.replace('.', '_')

    logging.info('Checking for existing nomad var: %s' % (nomad_var, ))

    cert = [x for x in le.certs if x.name == FLAGS.export_cert][0]
    existing_var = None

    try:
        existing_var = n.variables[nomad_var]
    except nomad.api.exceptions.URLNotAuthorizedNomadException as e:
        logging.error('Nomad said: %s' % (str(e)))
        logging.error('Set NOMAD_TOKEN to a valid token able to set variables.')
        return
    except KeyError:
        logging.info('%s is not a nomad variable, proceeding...' % (nomad_var))

    if existing_var:
        logging.info('Existing variable found, checking update...')
        data = n.variable.get_variable(nomad_var)
        needs_update = True
        for key in ('privkey', 'chain'):
            if data['Items'][key] == getattr(cert, key):
                logging.info('%s:%s unchanged' % (nomad_var, key, ))
                needs_update = False
        if not needs_update:
            logging.info('Variable does not need update.')
            return

    items = {
        'privkey': cert.privkey,
        'chain': cert.chain
    }

    payload = {
        'Path': nomad_var,
        'Items': items
    }

    try:
        n.variable.create_variable(nomad_var, payload)
    except Exception as e:
        logging.error('Nomad Error: %s' % (str(e)))
        return

    logging.info('New variable added: %s' % (n.variables[nomad_var]))


if __name__ == '__main__':
    app.run(main)
