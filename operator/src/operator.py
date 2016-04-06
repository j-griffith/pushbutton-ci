#!/usr/bin/env python

import json
import logging
import os
import pika
import playbook_utils
import random_name
import shade
import sys
import time

cloud = None
logging.basicConfig(filename='operator.log', level=logging.INFO)


def _verify_vars():
    for key in ['image_id', 'flavor_id',
                'cloud_name', 'key_name',
                'localconf', 'upload_script',
                'results_dir', 'web_server_address',
                'publish_dir']:
        if not os.environ.get(key, None):
            logging.error('Missing env variable: %s' % key)
            sys.exit(1)
    return True


def create_instance(name=None, image=None, flavor=None, auto_ip=True):
    if not name:
        name = random_name.generate()
    image = os.environ.get('image_id', image)
    flavor = os.environ.get('flavor_id', flavor)

    logging.info('Creating server with the following params, name: %s, image: %s, '
                 'flavor: %s, auto_ip: %s, key_name: %s' %
                 (name, image, flavor, auto_ip, os.environ.get('key_name')))
    server = cloud.create_server(name,
                                image=image,
                                flavor=flavor,
                                auto_ip=auto_ip,
                                key_name=os.environ.get('key_name'),
                                wait=True)
    return server

def callback(ch, method, properties, body):
    logging.info('Received event: %s' % body)
    payload = json.loads(body)
    patchset_ref = payload['patchSet']['ref']
    ref_name = patchset_ref.replace('/', '-')
    instance = create_instance(name=ref_name,
                               image=os.environ.get('image_id'),
                               flavor=os.environ.get('flavor_id'),
                               auto_ip=os.environ.get('auto_ip', True))

    use_floating_ip = os.environ.get('use_floating_ip', True)
    use_floating_ip = True
    results_dir = os.environ.get('results_dir')
    results_dir += '/%s' % ref_name
    ansible_logdir = results_dir + ('/%s' % 'ansible_logs')

    (stackit_success, output) = playbook_utils.stackit(
        cloud,
        instance,
        os.environ.get('localconf'),
        branch=os.environ.get('devstack_branch',
                              'master'),
        cinder_branch=patchset_ref,
        use_floating_ip=use_floating_ip,
        ansible_log_dir=ansible_logdir)
    logging.info('Output from stackit: %s', output)

    if stackit_success:
        (tempest_success, output) = (
            playbook_utils.run_tempest(cloud,
                                       instance,
                                       use_floating_ip=use_floating_ip,
                                       ansible_log_dir=ansible_logdir))

    (bundle_success, output) = (
        playbook_utils.gather_logs(cloud,
                                   instance,
                                   os.environ.get('upload_script'),
                                   use_floating_ip=use_floating_ip,
                                   ansible_log_dir=ansible_logdir))
    logging.info('Output from gather_logs: %s', output)
    publish_location = os.environ.get('publish_dir') + '/' + ref_name
    playbook_utils.publish_results(os.environ.get('web_server_ip'),
                                   publish_location,
                                   results_dir)

    logging.info('Published logs, task completed')
    ch.basic_ack(delivery_tag=method.delivery_tag)

if __name__ == '__main__':
    if not _verify_vars():
        logging.error('Missing required variable from vars.yaml file')
        sys.exit(1)

    shade.simple_logging(debug=True)
    cloud = shade.openstack_cloud(cloud=(
        os.environ.get('cloud_name', 'envvars')))

    reconnect = 6
    while reconnect:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='rabbit'))
            channel = connection.channel()
            channel.queue_declare(queue='task_queue', durable=True)
            reconnect = 0
        except pika.exceptions.ConnectionClosed as ex:
            logging.warning('Connection to RMQ failed, '
                            'remaining attempts: %s' %
                            reconnect)
            reconnect -= 1
            time.sleep(10)
            if reconnect < 1:
                raise(ex)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(callback,
                          queue='task_queue')
    channel.start_consuming()
