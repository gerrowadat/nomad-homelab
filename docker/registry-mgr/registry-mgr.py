import os
import hcl
from enum import Enum
from absl import app
from dxf import DXF
from absl import flags
from absl import logging

FLAGS = flags.FLAGS

flags.DEFINE_string('hcl_base', '', 'Base directory for HCL job specs.')
flags.DEFINE_string('local_docker_registry',
                    'docker-registry.home.andvari.net:5000',
                    'Address host:port of local docker registry.')
flags.DEFINE_string('remote_docker_registry',
                    'hub.docker.com:5000',
                    'Address host:port of remote docker registry.')


def get_mentioned_images_in_file(filename):
    with open(filename) as fp:
        cf = hcl.load(fp)

    images = []

    if 'job' not in cf:
        logging.warning('%s contains no jobs' % (filename))
        return []

    logging.info('Checking jobs in %s' % (filename))

    for j in cf['job']:
        if 'group' not in cf['job'][j]:
            logging.warning('%s contains no groups' % (filename))
            continue
        for g in cf['job'][j]['group']:
            if 'task' not in cf['job'][j]['group'][g]:
                logging.warning('%s has job with no tasks' % (filename))
                continue
            # Check for mutiple tasks.
            if isinstance(cf['job'][j]['group'][g]['task'], list):
                all_tasks = cf['job'][j]['group'][g]['task']
            else:
                all_tasks = [cf['job'][j]['group'][g]['task']]
            for t in all_tasks:
                task_name = [x for x in t.keys()][0]
                task_driver = t[task_name]['driver']
                if task_driver == 'docker':
                    image = t[task_name]['config']['image']
                    images.append(image)

    return images


def get_mentioned_images_in_dir(hcl_base):
    images = []
    logging.info('Checking %s' % (hcl_base, ))
    for root, dirs, files in os.walk(hcl_base):
        for f in [x for x in files if x.endswith('hcl')]:
            images.extend(get_mentioned_images_in_file(os.path.join(root, f)))
    return images


class ImageStatus(Enum):
    OK = 1
    MISSING = 2
    NO_VERSION = 3


def get_image_info(img):
    registry = FLAGS.remote_docker_registry
    if img.startswith(FLAGS.local_docker_registry):
        registry = FLAGS.local_docker_registry
        img = img[len(FLAGS.local_docker_registry)+1:]
    if ':' in img:
        (img_name, img_version) = img.split(':')
    else:
        img_name = img
        img_version = 'latest'

    return (registry, img_name, img_version)


def get_local_img_status(img):
    (registry, img_name, img_version) = get_image_info(img)
    dxf = DXF(FLAGS.local_docker_registry, img_name)
    try:
        aliases = dxf.list_aliases()
    except Exception:
        return ImageStatus.MISSING

    if img_version not in aliases:
        return ImageStatus.NO_VERSION
    else:
        return ImageStatus.OK


def main(argv):
    if len(argv) < 2:
        logging.error('No verb specified. Try "check_files"')
        return

    if argv[1] == 'list_images':
        if FLAGS.hcl_base == '':
            logging.error('must specify --hcl_base')
            return
        all_mentioned = get_mentioned_images_in_dir(FLAGS.hcl_base)
        logging.info('Docker images mentioned in all files: ')
        print('\n'.join(all_mentioned))

    elif argv[1] == 'check_local_registry':
        if FLAGS.hcl_base == '':
            logging.error('must specify --hcl_base')
            return

        all_mentioned = get_mentioned_images_in_dir(FLAGS.hcl_base)

        print('Status of local docker images:')

        for img in all_mentioned:
            status = get_local_img_status(img)
            print('[%s]\t%s' % (status, img))

    elif argv[1] == 'get_missing_versions':
        if FLAGS.hcl_base == '':
            logging.error('must specify --hcl_base')
            return

        all_mentioned = get_mentioned_images_in_dir(FLAGS.hcl_base)

        for img in all_mentioned:
            (registry, img_name, img_version) = get_image_info(img)
            status = get_local_img_status(img)
            if status == ImageStatus.NO_VERSION:
                if registry == FLAGS.remote_docker_registry:
                    print('# push %s to %s' % (
                        img, FLAGS.local_docker_registry))

                    print('docker pull %s:%s' % (img_name, img_version))

                    print('docker tag %s:%s %s/%s:%s' % (
                        img_name,
                        img_version,
                        FLAGS.local_docker_registry,
                        img_name,
                        img_version))

                    print('docker push %s/%s:%s' % (
                        FLAGS.local_docker_registry,
                        img_name,
                        img_version))

                elif registry == FLAGS.local_docker_registry:
                    print('# missing %s, please build and push' % (img))
                else:
                    print('# not sure what to do about %s' % (img))
    else:
        print('Unknown verb: %s' % (argv[1]))


if __name__ == '__main__':
    app.run(main)
