#!/usr/bin/env python

import time

import json
import logging
import os
import paramiko
import pika

logging.basicConfig(filename='/src/handler.log', level=logging.INFO)

fake_event = {'comment': 'Patch Set 1:\n\nrun solidfire', 'eventCreatedOn': 1459898186,
              'author': {'username': 'john-griffith',
                         'name': 'John Griffith',
                         'email': 'john.griffith8@gmail.com'},
              'patchSet': {'kind': 'REWORK', 'sizeInsertions': 0,
                           'createdOn': 1459898166, 'author': {'username': 'john-griffith',
                                                               'name': 'John Griffith',
                                                               'email': 'john.griffith8@gmail.com'},
                           'number': '1', 'isDraft': False, 'sizeDeletions': 0,
                           'parents': ['281ddeb03f02e1b58e54760b840cc33eee12e8f3'],
                           'uploader': {'username': 'john-griffith', 'name': 'John Griffith',
                                        'email': 'john.griffith8@gmail.com'},
                           'ref': 'refs/changes/68/301968/1', 'revision': '5890edb9f2cc1b38d2d545ef97fd718576064af3'},
              'type': 'comment-added', 'change': {'status': 'NEW',
                                                  'project': 'openstack/cinder',
                                                  'url': 'https://review.openstack.org/301968',
                                                  'commitMessage': 'Dummy patch to debug SolidFire CI\n\nChange-Id: I8ca985f2cc598aba435b8c0874097ec35ed0f7fb\n',
                                                  'number': '301968', 'topic': 'sfci_testpatch',
                                                  'branch': 'master', 'owner': {'username': 'john-griffith',
                                                                                'name': 'John Griffith', 'email': 'john.griffith8@gmail.com'},
                                                  'id': 'I8ca985f2cc598aba435b8c0874097ec35ed0f7fb', 'subject': 'Dummy patch to debug SolidFire CI'}}

reconnect = 6
while reconnect:
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
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

logging.info('Issuing fake_event')
loop_counter = 0
channel.basic_publish(
    exchange='',
    routing_key='task_queue',
    body=json.dumps(fake_event),
    properties=pika.BasicProperties(
        delivery_mode=2,))
